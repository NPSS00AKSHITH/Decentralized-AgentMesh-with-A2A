"""
Agent Delegation Tool
=====================
Provides a reusable tool for delegating tasks to specialist agents.
Instead of calling tools on behalf of another agent, we send a natural language
request and let the target agent's LLM decide which tools to use.

Now includes telemetry logging to PostgreSQL for:
- Tools used by target agent
- Execution timing
- LLM token usage
- Incident-level deduplication to prevent redundant API calls
"""
import asyncio
import json
import logging
import re
import time
from typing import Dict, Any, Callable, Optional

from lib.utils.logging_config import setup_logging, correlation_id_var
from lib.function_tool import function_tool
from lib.utils.communication import global_client

logger = setup_logging("delegation-tool")


def get_cid() -> str:
    return correlation_id_var.get() or "UNKNOWN"


def extract_incident_id(text: str) -> Optional[str]:
    """
    Extract incident ID from text using common patterns.
    Looks for patterns like:
      - "Incident ID: ABC_123"
      - "incident_id: ABC_123"
      - "for ABC_123_456"
    """
    if not text:
        return None
    
    # Pattern 1: Explicit "Incident ID:" label
    match = re.search(r'[Ii]ncident\s*[Ii][Dd][:=]\s*([A-Z0-9_-]+)', text)
    if match:
        return match.group(1)
    
    # Pattern 2: All-caps identifier with underscores (e.g., RUSHIKONDA_FIRE_MEDICAL_001)
    match = re.search(r'\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+){2,})\b', text)
    if match:
        return match.group(1)
    
    return None


def create_delegation_tool(
    source_agent: str,
    target_agent: str,
    target_description: str
) -> Callable:
    """
    Factory function to create a delegation tool for a specific agent pair.
    
    Args:
        source_agent: Name of the agent using this tool (e.g., "fire-chief-agent")
        target_agent: Name of the agent to delegate to (e.g., "medical-agent")
        target_description: Human-readable description of what the target handles
        
    Returns:
        An async function decorated as a tool that can be added to an agent
    """
    tool_name = f"delegate_to_{target_agent.replace('-agent', '').replace('-', '_')}"
    tool_description = f"Delegates a task to the {target_description}. Send a natural language request describing what you need, and the {target_description} will use their specialized tools to handle it and return the result."
    
    @function_tool(name=tool_name, description=tool_description)
    async def delegate_to_agent(request: str) -> Dict[str, Any]:
        """
        Delegate a task to a specialist agent using natural language.
        
        Args:
            request: Natural language description of what you need the agent to do.
                     Be specific about location, quantities, priorities, etc.
                     
        Returns:
            The response from the target agent after they process your request
            using their specialized tools, including telemetry data.
        """
        cid = get_cid()
        start_time = time.time()
        
        # Extract incident ID for deduplication
        incident_id = extract_incident_id(request)
        
        # Check if another agent already delegated to this target for the same incident
        if incident_id:
            existing = await global_client.check_delegation_exists(incident_id, target_agent)
            if existing:
                logger.info(
                    f"SKIP DELEGATION: {target_agent} already contacted for {incident_id} by {existing['source_agent']}",
                    extra={"correlation_id": cid}
                )
                return {
                    "status": "already_handled",
                    "delegated_to": target_agent,
                    "handled_by": existing['source_agent'],
                    "incident_id": incident_id,
                    "message": f"{target_agent} was already contacted for incident {incident_id} by {existing['source_agent']}. No duplicate action needed."
                }
        
        logger.info(
            f"DELEGATING to {target_agent}: {request[:80]}...", 
            extra={"correlation_id": cid}
        )
        
        # Log delegation start to database (with incident_id)
        await global_client.create_delegation_log(
            cid=cid,
            source_agent=source_agent,
            target_agent=target_agent,
            request_text=request,
            incident_id=incident_id
        )

        
        try:
            # Send delegation request - target agent's LLM will process this
            response = await global_client.send_request_with_handshake(
                source_agent=source_agent,
                target_agent=target_agent,
                payload={
                    "type": "DELEGATION_REQUEST",
                    "request": request,
                    "source": source_agent,
                    "requires_response": True
                },
                correlation_id=cid,
                timeout=60  # Increased timeout for LLM processing
            )
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Extract telemetry from response if available
            tools_called = []
            tool_results = []
            prompt_tokens = 0
            completion_tokens = 0
            final_response = ""
            
            if isinstance(response, dict):
                tools_called = response.get("tools_called", [])
                tool_results = response.get("tool_results", [])
                prompt_tokens = response.get("prompt_tokens", 0)
                completion_tokens = response.get("completion_tokens", 0)
                final_response = response.get("message", response.get("result", str(response)))
            else:
                final_response = str(response)
            
            # Update delegation log with results
            await global_client.update_delegation_log(
                cid=cid,
                tools_called=tools_called,
                tool_results=tool_results,
                final_response=final_response,
                duration_ms=duration_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                status="COMPLETED"
            )
            
            logger.info(
                f"DELEGATION COMPLETE from {target_agent} in {duration_ms}ms", 
                extra={"correlation_id": cid}
            )
            
            # Build rich response with telemetry
            result = {
                "status": "delegated",
                "delegated_to": target_agent,
                "response": final_response,
                "telemetry": {
                    "duration_ms": duration_ms,
                    "tools_called": tools_called,
                    "tokens": {
                        "prompt": prompt_tokens,
                        "completion": completion_tokens,
                        "total": prompt_tokens + completion_tokens
                    }
                }
            }
            
            return result
                
        except asyncio.TimeoutError:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log failure
            await global_client.update_delegation_log(
                cid=cid,
                duration_ms=duration_ms,
                status="TIMEOUT"
            )
            
            logger.error(f"DELEGATION TIMEOUT: {target_agent} did not respond", extra={"correlation_id": cid})
            return {
                "status": "timeout",
                "delegated_to": target_agent,
                "error": f"{target_agent} did not respond within timeout.",
                "telemetry": {"duration_ms": duration_ms}
            }
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_str = str(e)
            
            # Check if this is a connection failure that warrants failover
            is_connection_failure = "503" in error_str or "connection" in error_str.lower() or "timeout" in error_str.lower()
            
            # Define failover mappings - who can act as backup for whom
            failover_agents = {
                "medical-agent": "police-chief-agent",       # Police can coordinate basic medical response
                "civic-alert-agent": "police-chief-agent",   # Police has emergency_public_broadcast
                "fire-chief-agent": "police-chief-agent",    # Police can coordinate basic fire response
                "utility-agent": "fire-chief-agent",         # Fire Chief can handle utility emergencies
                "police-chief-agent": "fire-chief-agent",    # Fire Chief can handle security incidents
            }
            
            failover_target = failover_agents.get(target_agent)
            
            # Attempt failover if applicable
            if is_connection_failure and failover_target:
                logger.warning(
                    f"FAILOVER: {target_agent} unreachable, trying {failover_target}",
                    extra={"correlation_id": cid}
                )
                
                try:
                    # Try the failover agent
                    failover_response = await global_client.send_request_with_handshake(
                        source_agent=source_agent,
                        target_agent=failover_target,
                        payload={
                            "type": "DELEGATION_REQUEST",
                            "request": f"[FAILOVER from {target_agent}] {request}",
                            "source": source_agent,
                            "requires_response": True,
                            "is_failover": True,
                            "original_target": target_agent
                        },
                        correlation_id=cid,
                        timeout=60
                    )
                    
                    failover_duration_ms = int((time.time() - start_time) * 1000)
                    final_response = ""
                    if isinstance(failover_response, dict):
                        final_response = failover_response.get("message", str(failover_response))
                    else:
                        final_response = str(failover_response)
                    
                    # Log successful failover
                    await global_client.update_delegation_log(
                        cid=cid,
                        duration_ms=failover_duration_ms,
                        final_response=f"[FAILOVER to {failover_target}] {final_response}",
                        status="FAILOVER_SUCCESS"
                    )
                    
                    logger.info(
                        f"FAILOVER SUCCESS: {failover_target} handled request for {target_agent}",
                        extra={"correlation_id": cid}
                    )
                    
                    return {
                        "status": "failover",
                        "original_target": target_agent,
                        "handled_by": failover_target,
                        "response": final_response,
                        "message": f"{target_agent} was unreachable. {failover_target} handled the request.",
                        "telemetry": {"duration_ms": failover_duration_ms}
                    }
                    
                except Exception as failover_error:
                    logger.error(
                        f"FAILOVER FAILED: {failover_target} also unreachable: {failover_error}",
                        extra={"correlation_id": cid}
                    )
                    # Continue to log original failure below
            
            # Log failure
            await global_client.update_delegation_log(
                cid=cid,
                duration_ms=duration_ms,
                final_response=str(e),
                status="FAILED"
            )
            
            logger.error(f"DELEGATION FAILED to {target_agent}: {e}", extra={"correlation_id": cid})
            return {
                "status": "failed",
                "delegated_to": target_agent,
                "error": str(e),
                "telemetry": {"duration_ms": duration_ms}
            }
    
    # Preserve the tool name and description for the returned function
    delegate_to_agent.__name__ = tool_name
    delegate_to_agent._tool_name = tool_name
    delegate_to_agent._tool_description = tool_description
    
    return delegate_to_agent


# Pre-built delegation tools for common agent pairs
# Fire Chief can delegate to:
delegate_to_medical = create_delegation_tool(
    source_agent="fire-chief-agent",
    target_agent="medical-agent",
    target_description="Medical Agent for casualty triage, ambulance dispatch, and hospital coordination"
)

delegate_to_utility = create_delegation_tool(
    source_agent="fire-chief-agent",
    target_agent="utility-agent", 
    target_description="Utility Agent for power shutdowns, gas isolation, and water pressure management"
)

# Medical Agent can delegate to:
delegate_to_fire_chief = create_delegation_tool(
    source_agent="medical-agent",
    target_agent="fire-chief-agent",
    target_description="Fire Chief Agent for fire suppression, rescue operations, and hazmat response"
)

delegate_to_utility_from_medical = create_delegation_tool(
    source_agent="medical-agent",
    target_agent="utility-agent",
    target_description="Utility Agent for infrastructure safety during medical operations"
)

# Utility Agent can delegate to:
delegate_to_fire_chief_from_utility = create_delegation_tool(
    source_agent="utility-agent",
    target_agent="fire-chief-agent",
    target_description="Fire Chief Agent for fire and hazmat emergencies related to infrastructure failures"
)

delegate_to_medical_from_utility = create_delegation_tool(
    source_agent="utility-agent",
    target_agent="medical-agent",
    target_description="Medical Agent for injuries caused by infrastructure incidents"
)

# Police Chief can delegate to:
delegate_to_fire_from_police = create_delegation_tool(
    source_agent="police-chief-agent",
    target_agent="fire-chief-agent",
    target_description="Fire Chief Agent for fire, hazmat, and rescue operations"
)

delegate_to_medical_from_police = create_delegation_tool(
    source_agent="police-chief-agent",
    target_agent="medical-agent",
    target_description="Medical Agent for casualties and ambulance dispatch"
)

delegate_to_utility_from_police = create_delegation_tool(
    source_agent="police-chief-agent",
    target_agent="utility-agent",
    target_description="Utility Agent for power/gas shutoffs during police operations"
)

# Dispatch can delegate to all specialists:
delegate_to_fire_from_dispatch = create_delegation_tool(
    source_agent="dispatch-agent",
    target_agent="fire-chief-agent",
    target_description="Fire Chief Agent for fire emergencies and rescue"
)

delegate_to_medical_from_dispatch = create_delegation_tool(
    source_agent="dispatch-agent",
    target_agent="medical-agent",
    target_description="Medical Agent for medical emergencies"
)

delegate_to_police_from_dispatch = create_delegation_tool(
    source_agent="dispatch-agent",
    target_agent="police-chief-agent",
    target_description="Police Chief Agent for law enforcement and security"
)

delegate_to_utility_from_dispatch = create_delegation_tool(
    source_agent="dispatch-agent",
    target_agent="utility-agent",
    target_description="Utility Agent for infrastructure emergencies"
)

# Camera can delegate to:
delegate_to_fire_from_camera = create_delegation_tool(
    source_agent="camera-agent",
    target_agent="fire-chief-agent",
    target_description="Fire Chief Agent when visual fire detection is confirmed"
)

# IoT Sensor can delegate to:
delegate_to_fire_from_iot = create_delegation_tool(
    source_agent="iot-sensor-agent",
    target_agent="fire-chief-agent",
    target_description="Fire Chief Agent for fire/smoke sensor alerts"
)

delegate_to_utility_from_iot = create_delegation_tool(
    source_agent="iot-sensor-agent",
    target_agent="utility-agent",
    target_description="Utility Agent for infrastructure sensor alerts"
)

# Camera can delegate to Police (for fights/crowds):
delegate_to_police_from_camera = create_delegation_tool(
    source_agent="camera-agent",
    target_agent="police-chief-agent",
    target_description="Police Chief Agent for fight detection, crowd control, and security incidents"
)

# Utility can delegate to Civic Alert (for outage broadcasts):
delegate_to_civic_alert_from_utility = create_delegation_tool(
    source_agent="utility-agent",
    target_agent="civic-alert-agent",
    target_description="Civic Alert Agent for public outage notifications and broadcasts"
)

# Utility can delegate to Police as Civic Alert failover:
delegate_to_police_from_utility = create_delegation_tool(
    source_agent="utility-agent",
    target_agent="police-chief-agent",
    target_description="Police Chief Agent for emergency PA broadcasts when Civic Alert is unavailable"
)

# Fire Chief can delegate to Police as Civic Alert failover:
delegate_to_police_from_fire = create_delegation_tool(
    source_agent="fire-chief-agent",
    target_agent="police-chief-agent",
    target_description="Police Chief Agent for emergency PA broadcasts when Civic Alert is unavailable"
)

# Medical can delegate to Police as Civic Alert failover:
delegate_to_police_from_medical = create_delegation_tool(
    source_agent="medical-agent",
    target_agent="police-chief-agent",
    target_description="Police Chief Agent for emergency PA broadcasts when Civic Alert is unavailable"
)

# =============================================================================
# GENERAL POLICE DELEGATION (for security/crowd control, not just failover)
# =============================================================================

# Fire Chief can delegate to Police for security/crowd/cordon needs:
delegate_to_police_general_from_fire = create_delegation_tool(
    source_agent="fire-chief-agent",
    target_agent="police-chief-agent",
    target_description="Police Chief Agent for perimeter security, crowd control, traffic management, and cordon operations"
)

# Medical can delegate to Police for security needs:
delegate_to_police_general_from_medical = create_delegation_tool(
    source_agent="medical-agent",
    target_agent="police-chief-agent",
    target_description="Police Chief Agent for scene security, crowd control, and traffic management during medical operations"
)
