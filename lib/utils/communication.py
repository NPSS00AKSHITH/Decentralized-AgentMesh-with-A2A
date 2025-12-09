import asyncio
import logging
import uuid
import json
import time
import os
import httpx
import asyncpg
from typing import Dict, Any, List, Optional, Tuple
from a2a.client import A2AClient
from a2a.types import Message, Role, TextPart, MessageSendParams, SendMessageRequest
from lib.consul.registry import ConsulRegistry
from lib.utils.security import SecurityManager
from lib.utils.logging_config import correlation_id_var

logger = logging.getLogger("communication-utils")


class DynamicTokenAuth(httpx.Auth):
    """
    Custom httpx Auth class that generates a fresh JWT for each request.
    This ensures tokens are valid and properly scoped for the target agent.
    """
    def __init__(self, security: 'SecurityManager', source_agent: str, target_agent: str):
        self.security = security
        self.source_agent = source_agent
        self.target_agent = target_agent

    def auth_flow(self, request):
        # Generate a fresh token for each request
        correlation_id = str(uuid.uuid4())
        token = self.security.generate_token(
            source_agent=self.source_agent,
            target_agent=self.target_agent,
            correlation_id=correlation_id
        )
        request.headers["Authorization"] = f"Bearer {token}"
        yield request


# --- Circuit Breaker Configuration ---
CIRCUIT_FAILURE_THRESHOLD = 3     # Number of failures before opening circuit
CIRCUIT_RESET_TIMEOUT = 60.0      # Seconds before attempting to close circuit
CIRCUIT_HALF_OPEN_MAX = 1         # Max requests to allow in half-open state


class CircuitBreaker:
    """
    Simple circuit breaker for agent communication.
    States: CLOSED (normal), OPEN (blocking), HALF_OPEN (testing)
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"
    
    def __init__(self):
        # agent_name -> (state, failure_count, last_failure_time, half_open_attempts)
        self._circuits: Dict[str, Tuple[str, int, float, int]] = {}
    
    def get_state(self, agent_name: str) -> str:
        if agent_name not in self._circuits:
            return self.CLOSED
        
        state, failures, last_failure, _ = self._circuits[agent_name]
        
        # Check if we should transition from OPEN to HALF_OPEN
        if state == self.OPEN and (time.time() - last_failure) > CIRCUIT_RESET_TIMEOUT:
            self._circuits[agent_name] = (self.HALF_OPEN, failures, last_failure, 0)
            return self.HALF_OPEN
        
        return state
    
    def record_success(self, agent_name: str):
        """Record a successful call - resets the circuit to CLOSED."""
        self._circuits[agent_name] = (self.CLOSED, 0, 0.0, 0)
        logger.debug(f"Circuit CLOSED for {agent_name} after success")
    
    def record_failure(self, agent_name: str):
        """Record a failed call - may open the circuit."""
        if agent_name not in self._circuits:
            self._circuits[agent_name] = (self.CLOSED, 1, time.time(), 0)
            return
        
        state, failures, _, half_open_attempts = self._circuits[agent_name]
        new_failures = failures + 1
        
        if state == self.HALF_OPEN:
            # Failed during half-open test - go back to OPEN
            self._circuits[agent_name] = (self.OPEN, new_failures, time.time(), 0)
            logger.warning(f"Circuit OPEN for {agent_name} after half-open failure")
        elif new_failures >= CIRCUIT_FAILURE_THRESHOLD:
            # Threshold exceeded - open the circuit
            self._circuits[agent_name] = (self.OPEN, new_failures, time.time(), 0)
            logger.warning(f"Circuit OPEN for {agent_name} after {new_failures} failures")
        else:
            self._circuits[agent_name] = (self.CLOSED, new_failures, time.time(), 0)
    
    def allow_request(self, agent_name: str) -> bool:
        """Check if a request should be allowed through."""
        state = self.get_state(agent_name)
        
        if state == self.CLOSED:
            return True
        elif state == self.OPEN:
            return False
        else:  # HALF_OPEN
            _, failures, last_failure, attempts = self._circuits[agent_name]
            if attempts < CIRCUIT_HALF_OPEN_MAX:
                self._circuits[agent_name] = (self.HALF_OPEN, failures, last_failure, attempts + 1)
                return True
            return False


# Global circuit breaker instance
_circuit_breaker = CircuitBreaker()


class GlobalA2AClient:
    """
    Singleton client manager for A2A inter-agent communication.
    Uses httpx.AsyncClient with the deprecated (but functional) A2AClient wrapper.
    Features: Exponential backoff, circuit breaker, configurable timeouts.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalA2AClient, cls).__new__(cls)
            cls._instance.security = SecurityManager()
            cls._instance.consul = ConsulRegistry()
            # Cache keys: f"{source}->{target}" to support unique HTTP clients per pair
            cls._instance._httpx_clients = {} 
            cls._instance._a2a_clients = {}
            cls._instance._pending_handshakes = {}  # Legacy: still used for in-process resolution
            cls._instance._db_pool = None
        return cls._instance

    async def _get_db_pool(self):
        """Get or create a shared asyncpg connection pool for handshake state."""
        if self._db_pool is None:
            dsn = os.getenv("DATABASE_URL")
            if not dsn:
                logger.warning("DATABASE_URL not set. DB-backed handshakes disabled.")
                return None
            try:
                self._db_pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
                async with self._db_pool.acquire() as conn:
                    # Ensure handshakes table exists
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS handshakes (
                            cid TEXT PRIMARY KEY,
                            status TEXT NOT NULL DEFAULT 'PENDING',
                            result JSONB,
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    
                    # Create delegation_logs table for detailed telemetry
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS delegation_logs (
                            id SERIAL PRIMARY KEY,
                            correlation_id TEXT NOT NULL,
                            source_agent TEXT NOT NULL,
                            target_agent TEXT NOT NULL,
                            request_text TEXT,
                            incident_id TEXT,
                            
                            -- Timing
                            started_at TIMESTAMP DEFAULT NOW(),
                            completed_at TIMESTAMP,
                            duration_ms INTEGER,
                            
                            -- Tool Tracking
                            tools_called JSONB DEFAULT '[]',
                            tool_results JSONB DEFAULT '[]',
                            
                            -- LLM Token Tracking
                            prompt_tokens INTEGER DEFAULT 0,
                            completion_tokens INTEGER DEFAULT 0,
                            total_tokens INTEGER DEFAULT 0,
                            
                            -- Final Response
                            final_response TEXT,
                            status TEXT DEFAULT 'PENDING',
                            
                            created_at TIMESTAMP DEFAULT NOW()
                        )
                    """)
                    
                    # Add incident_id column if table already exists (migration)
                    await conn.execute("""
                        DO $$ 
                        BEGIN 
                            ALTER TABLE delegation_logs ADD COLUMN IF NOT EXISTS incident_id TEXT;
                        EXCEPTION WHEN duplicate_column THEN NULL;
                        END $$;
                    """)
                    
                    # Create indexes for faster queries
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_delegation_logs_cid 
                        ON delegation_logs(correlation_id)
                    """)
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_delegation_logs_created 
                        ON delegation_logs(created_at)
                    """)
                    await conn.execute("""
                        CREATE INDEX IF NOT EXISTS idx_delegation_logs_incident 
                        ON delegation_logs(incident_id, target_agent)
                    """)
                    
                    # Auto-cleanup: Delete logs older than 7 days
                    await conn.execute("""
                        DELETE FROM delegation_logs 
                        WHERE created_at < NOW() - INTERVAL '7 days'
                    """)
                    
                logger.info("Database pool initialized (handshakes + delegation_logs).")
            except Exception as e:
                logger.error(f"Failed to initialize DB pool: {e}")
                return None
        return self._db_pool

    async def _create_handshake_record(self, cid: str):
        """Insert a PENDING handshake record into the database."""
        pool = await self._get_db_pool()
        if not pool:
            return False
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "INSERT INTO handshakes (cid, status) VALUES ($1, 'PENDING') ON CONFLICT (cid) DO UPDATE SET status = 'PENDING', result = NULL",
                    cid
                )
            return True
        except Exception as e:
            logger.error(f"Failed to create handshake record {cid}: {e}")
            return False

    async def _poll_handshake_result(self, cid: str, timeout: int) -> Optional[Dict[str, Any]]:
        """Poll the database for handshake completion."""
        pool = await self._get_db_pool()
        if not pool:
            return None
        
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            try:
                async with pool.acquire() as conn:
                    row = await conn.fetchrow(
                        "SELECT status, result FROM handshakes WHERE cid = $1",
                        cid
                    )
                    if row and row['status'] == 'COMPLETED':
                        result = row['result']
                        # Cleanup the record
                        await conn.execute("DELETE FROM handshakes WHERE cid = $1", cid)
                        return json.loads(result) if isinstance(result, str) else result
            except Exception as e:
                logger.warning(f"DB poll error for {cid}: {e}")
            
            await asyncio.sleep(1)  # Poll every 1 second
        
        # Timeout - cleanup
        try:
            async with pool.acquire() as conn:
                await conn.execute("DELETE FROM handshakes WHERE cid = $1", cid)
        except:
            pass
        return None

    async def _update_handshake_record(self, cid: str, result: Dict[str, Any]):
        """Update a handshake record to COMPLETED with the result."""
        pool = await self._get_db_pool()
        if not pool:
            return
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    "UPDATE handshakes SET status = 'COMPLETED', result = $2 WHERE cid = $1",
                    cid, json.dumps(result)
                )
            logger.info(f"Handshake {cid} marked COMPLETED in DB.")
        except Exception as e:
            logger.error(f"Failed to update handshake record {cid}: {e}")

    # =========================================================================
    # DELEGATION TELEMETRY METHODS
    # =========================================================================
    
    async def create_delegation_log(
        self, 
        cid: str, 
        source_agent: str, 
        target_agent: str, 
        request_text: str,
        incident_id: str = None
    ) -> bool:
        """Create a new delegation log entry when delegation starts."""
        pool = await self._get_db_pool()
        if not pool:
            return False
        try:
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO delegation_logs 
                    (correlation_id, source_agent, target_agent, request_text, incident_id, status)
                    VALUES ($1, $2, $3, $4, $5, 'PENDING')
                """, cid, source_agent, target_agent, request_text, incident_id)
            logger.info(f"Delegation log created: {source_agent} -> {target_agent}" + (f" (incident: {incident_id})" if incident_id else ""))
            return True
        except Exception as e:
            logger.error(f"Failed to create delegation log: {e}")
            return False
    
    async def update_delegation_log(
        self,
        cid: str,
        tools_called: List[str] = None,
        tool_results: List[Dict] = None,
        final_response: str = None,
        duration_ms: int = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        status: str = "COMPLETED"
    ) -> bool:
        """Update delegation log with results, timing, and token usage."""
        pool = await self._get_db_pool()
        if not pool:
            return False
        try:
            async with pool.acquire() as conn:
                await conn.execute("""
                    UPDATE delegation_logs SET
                        completed_at = NOW(),
                        duration_ms = $2,
                        tools_called = $3,
                        tool_results = $4,
                        final_response = $5,
                        prompt_tokens = $6,
                        completion_tokens = $7,
                        total_tokens = $8,
                        status = $9
                    WHERE correlation_id = $1
                """, 
                    cid,
                    duration_ms,
                    json.dumps(tools_called or []),
                    json.dumps(tool_results or []),
                    final_response,
                    prompt_tokens,
                    completion_tokens,
                    prompt_tokens + completion_tokens,
                    status
                )
            logger.info(f"Delegation log updated: {cid} ({status})")
            return True
        except Exception as e:
            logger.error(f"Failed to update delegation log: {e}")
            return False
    
    async def get_delegation_log(self, cid: str) -> Optional[Dict[str, Any]]:
        """Retrieve delegation log details for a correlation ID."""
        pool = await self._get_db_pool()
        if not pool:
            return None
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT * FROM delegation_logs WHERE correlation_id = $1
                """, cid)
                if row:
                    return dict(row)
        except Exception as e:
            logger.error(f"Failed to get delegation log: {e}")
        return None

    async def check_delegation_exists(
        self,
        incident_id: str,
        target_agent: str,
        max_age_seconds: int = 300
    ) -> Optional[Dict[str, Any]]:
        """
        Check if another agent already delegated to target for this incident.
        
        Args:
            incident_id: The incident identifier (e.g., RUSHIKONDA_FIRE_MEDICAL_001)
            target_agent: Name of the target agent being delegated to
            max_age_seconds: How far back to look (default 5 minutes)
            
        Returns:
            Dict with delegation info if found, None otherwise
        """
        if not incident_id:
            return None
            
        pool = await self._get_db_pool()
        if not pool:
            return None
            
        target_agent = self._normalize_name(target_agent)
        
        try:
            async with pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT source_agent, target_agent, incident_id, created_at, status
                    FROM delegation_logs 
                    WHERE incident_id = $1 
                      AND target_agent = $2
                      AND created_at > NOW() - INTERVAL '1 second' * $3
                      AND status IN ('PENDING', 'COMPLETED')
                    ORDER BY created_at DESC
                    LIMIT 1
                """, incident_id, target_agent, max_age_seconds)
                
                if row:
                    logger.info(f"Delegation exists: {row['source_agent']} -> {target_agent} for {incident_id}")
                    return dict(row)
        except Exception as e:
            logger.error(f"Failed to check delegation existence: {e}")
        return None

    def _normalize_name(self, name: str) -> str:
        return name.replace("_", "-")

    def _get_port_offset(self, name: str) -> int:
        # A2A servers run on 900x ports (via start_a2a_servers.bat)
        # ADK web servers run on 800x ports (via adk web / start_agents.bat)
        # Using A2A ports for inter-agent communication
        offsets = {
            "human-intake-agent": 9001, "dispatch-agent": 9002, "fire-chief-agent": 9003,
            "civic-alert-agent": 9004, "medical-agent": 9005, "police-chief-agent": 9006,
            "utility-agent": 9007, "iot-sensor-agent": 9008, "camera-agent": 9009
        }
        return offsets.get(name, 9000)

    async def get_client(self, source_agent: str, target_agent: str, timeout: float = 30.0) -> A2AClient:
        """
        Returns a cached A2A client for the Source->Target pair.
        Uses httpx.AsyncClient as the transport layer.
        """
        source_agent = self._normalize_name(source_agent)
        target_agent = self._normalize_name(target_agent)
        client_key = f"{source_agent}->{target_agent}"

        if client_key not in self._a2a_clients:
            # 1. Resolve URL via Consul
            url = await self.consul.get_service_url(target_agent)
            if not url:
                 logger.warning(f"Consul resolution failed for {target_agent}. Using localhost fallback.")
                 port = self._get_port_offset(target_agent)
                 # A2A endpoints are mounted at /a2a/ (trailing slash required)
                 url = f"http://localhost:{port}/a2a/"
            elif not url.endswith("/a2a/"):
                # Ensure the URL has the /a2a/ path with trailing slash
                url = url.rstrip("/") + "/a2a/"
            
            # 2. Create httpx.AsyncClient for this pair with JWT authentication
            # Enable follow_redirects to handle any 307 redirects from the server
            auth = DynamicTokenAuth(self.security, source_agent, target_agent)
            httpx_client = httpx.AsyncClient(
                base_url=url,
                auth=auth,
                timeout=timeout,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            self._httpx_clients[client_key] = httpx_client
            
            # 3. Create A2AClient wrapper with the httpx client
            # A2AClient requires (httpx_client, agent_card=None, url=None)
            self._a2a_clients[client_key] = A2AClient(
                httpx_client=httpx_client,
                url=url  # Pass URL since we don't have the AgentCard
            )
            logger.info(f"Created new A2A client: {client_key} -> {url}")
            
        return self._a2a_clients[client_key]

    async def check_agent_health(self, target_agent: str, timeout: float = 5.0) -> bool:
        """Pre-flight health check for an agent."""
        target_agent = self._normalize_name(target_agent)
        port = self._get_port_offset(target_agent)
        url = f"http://localhost:{port}/health"
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    return data.get("status") in ("active", "healthy")
        except Exception as e:
            logger.debug(f"Health check failed for {target_agent}: {e}")
        return False

    async def send_message(
        self, 
        source_agent: str, 
        target_agent: str, 
        message_text: str, 
        correlation_id: Optional[str] = None, 
        retries: int = 3, 
        timeout: float = 30.0,
        context_id: Optional[str] = None,
        check_health: bool = False
    ) -> Dict[str, Any]:
        """
        Send a message to target agent with exponential backoff and circuit breaker.
        
        Args:
            source_agent: Name of the sending agent
            target_agent: Name of the receiving agent
            message_text: Message content
            correlation_id: Optional correlation ID for tracking
            retries: Number of retry attempts (default 3)
            timeout: Request timeout in seconds (default 30)
            context_id: Optional context ID for message threading
            check_health: If True, perform health check before sending
        """
        target_agent = self._normalize_name(target_agent)
        source_agent = self._normalize_name(source_agent)
        
        # Circuit breaker check
        if not _circuit_breaker.allow_request(target_agent):
            logger.warning(f"Circuit OPEN for {target_agent} - request blocked")
            return {"status": "circuit_open", "agent": target_agent, "error": "Circuit breaker is open"}
        
        # Optional health check
        if check_health:
            if not await self.check_agent_health(target_agent):
                logger.warning(f"Health check failed for {target_agent}")
                _circuit_breaker.record_failure(target_agent)
                return {"status": "unhealthy", "agent": target_agent}
        
        # Ensure context var is set for correlation tracking
        token = correlation_id_var.set(correlation_id or "A2A")
        
        try:
            for attempt in range(retries + 1):
                try:
                    client = await self.get_client(source_agent, target_agent, timeout)
                    
                    # Build A2A message using the SDK types
                    # messageId is required by the a2a-sdk
                    msg_obj = Message(
                        messageId=str(uuid.uuid4()),
                        role=Role.user,
                        parts=[TextPart(text=message_text)],
                        contextId=context_id  # Note: camelCase in the SDK
                    )
                    
                    metadata = {"correlation_id": correlation_id} if correlation_id else {}
                    params = MessageSendParams(message=msg_obj, metadata=metadata)
                    request = SendMessageRequest(id=str(uuid.uuid4()), method="message/send", params=params)
                    
                    response = await client.send_message(request=request)
                    
                    # Record success for circuit breaker
                    _circuit_breaker.record_success(target_agent)
                    
                    return {"status": "delivered", "agent": target_agent, "response": response}

                except Exception as e:
                    logger.warning(f"Attempt {attempt+1}/{retries+1} failed for {target_agent}: {e}")
                    
                    # Record failure for circuit breaker
                    _circuit_breaker.record_failure(target_agent)
                    
                    # Invalidate cache to force re-resolution on next attempt
                    client_key = f"{source_agent}->{target_agent}"
                    if client_key in self._a2a_clients:
                        # Close the httpx client
                        if client_key in self._httpx_clients:
                            try:
                                await self._httpx_clients[client_key].aclose()
                            except:
                                pass
                            del self._httpx_clients[client_key]
                        del self._a2a_clients[client_key]
                    self.consul.invalidate_cache(target_agent)
                    
                    if attempt == retries:
                        raise e
                    
                    # Exponential backoff: 1s, 2s, 4s, 8s... capped at 32s
                    backoff = min(32, 2 ** attempt)
                    logger.info(f"Retrying {target_agent} in {backoff}s...")
                    await asyncio.sleep(backoff)
        finally:
            correlation_id_var.reset(token)

    async def send_request_with_handshake(
        self, 
        source_agent: str, 
        target_agent: str, 
        payload: Dict[str, Any], 
        correlation_id: Optional[str] = None, 
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Send a handshake request and wait for response.
        Uses database-backed polling for cross-process communication.
        
        Args:
            timeout: Timeout in seconds (default 30)
        """
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        # Circuit breaker check before initiating handshake
        target_agent = self._normalize_name(target_agent)
        if not _circuit_breaker.allow_request(target_agent):
            logger.warning(f"Circuit OPEN for {target_agent} - handshake blocked")
            raise Exception(f"Circuit breaker OPEN for {target_agent}")
        
        # Try DB-backed handshake first
        db_available = await self._create_handshake_record(correlation_id)
        
        # Also create in-memory future as fallback for same-process resolution
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending_handshakes[correlation_id] = future

        try:
            message_content = json.dumps({
                "type": "HANDSHAKE_REQUEST",
                "source": source_agent,
                "payload": payload,
                "correlation_id": correlation_id
            })
            
            await self.send_message(source_agent, target_agent, message_content, correlation_id)
            logger.info(f"Handshake Initiated: Waiting for {target_agent} (cid={correlation_id}, db={db_available})")
            
            if db_available:
                # Use DB polling for cross-process communication
                logger.info(f"Polling DB for handshake completion: {correlation_id}")
                result = await self._poll_handshake_result(correlation_id, timeout)
                if result:
                    _circuit_breaker.record_success(target_agent)
                    self._pending_handshakes.pop(correlation_id, None)
                    return result
                else:
                    raise asyncio.TimeoutError()
            else:
                # Fallback to in-memory future (same-process only)
                result = await asyncio.wait_for(future, timeout=timeout)
                _circuit_breaker.record_success(target_agent)
                return result
            
        except asyncio.TimeoutError:
            logger.error(f"Handshake TIMEOUT with {target_agent}")
            _circuit_breaker.record_failure(target_agent)
            self._pending_handshakes.pop(correlation_id, None)
            raise Exception(f"Agent {target_agent} did not respond within {timeout}s")
        except Exception as e:
            _circuit_breaker.record_failure(target_agent)
            self._pending_handshakes.pop(correlation_id, None)
            raise e

    def resolve_handshake(self, correlation_id: str, result: Dict[str, Any]):
        """Resolve a handshake by updating both in-memory future and database record."""
        # 1. Try in-memory resolution (same-process)
        if correlation_id in self._pending_handshakes:
            future = self._pending_handshakes[correlation_id]
            if not future.done():
                future.set_result(result)
            del self._pending_handshakes[correlation_id]
            logger.info(f"Handshake {correlation_id} resolved in-memory.")
        
        # 2. Always update DB for cross-process resolution
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._update_handshake_record(correlation_id, result))
        except RuntimeError:
            # No running event loop - this can happen in sync contexts
            logger.warning(f"Could not update DB for handshake {correlation_id} - no event loop.")

    async def broadcast(self, source_agent: str, agents: List[str], message_text: str) -> Dict[str, Any]:
        """Broadcast message to multiple agents in parallel."""
        tasks = [self.failover_call(source_agent, agent, message_text) for agent in agents]
        results = await asyncio.gather(*tasks)
        return {agent: result for agent, result in zip(agents, results)}

    async def failover_call(self, source_agent: str, agent_name: str, message_text: str) -> Dict[str, Any]:
        """Single message attempt with failover handling."""
        try:
            return await self.send_message(source_agent, agent_name, message_text, retries=1)
        except Exception:
            return {"status": "unreachable", "agent": agent_name}

    def get_circuit_status(self) -> Dict[str, str]:
        """Get current circuit breaker status for all agents."""
        return {agent: _circuit_breaker.get_state(agent) for agent in _circuit_breaker._circuits}


class GlobalClientProxy:
    def __init__(self): self._impl = None
    def __getattr__(self, name):
        if self._impl is None: self._impl = GlobalA2AClient()
        return getattr(self._impl, name)

global_client = GlobalClientProxy()