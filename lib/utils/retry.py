"""
Retry utilities for handling rate limits (429 errors) from Gemini API.
"""
import asyncio
import random
import logging
import time
from functools import wraps
from typing import TypeVar, AsyncIterator, Any

logger = logging.getLogger("retry-utils")


class FileLockRateLimiter:
    """
    Cross-process token bucket rate limiter using file locking.
    Uses a JSON file to share state between multiple agent processes.
    """
    
    def __init__(self, requests_per_minute: int = 8):
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.max_tokens = float(requests_per_minute)
        
        # Determine paths relative to project root
        # lib/utils/retry.py -> lib/utils -> lib -> root
        import pathlib
        self.root_dir = pathlib.Path(__file__).parent.parent.parent
        self.data_dir = self.root_dir / "data"
        self.state_file = self.data_dir / "ratelimit_state.json"
        self.lock_file = self.data_dir / "ratelimit.lock"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Initialize state file if new
        if not self.state_file.exists():
            self._write_state({"tokens": self.max_tokens, "last_update": time.time()})

    def _acquire_lock(self, timeout: float = 10.0) -> bool:
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # O_CREAT | O_EXCL ensures atomic creation
                import os
                fd = os.open(str(self.lock_file), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.close(fd)
                return True
            except FileExistsError:
                # Check for stale lock
                try:
                    stats = self.lock_file.stat()
                    if time.time() - stats.st_mtime > 5.0:  # 5 seconds stale
                        logger.warning("Removing stale rate limit lock")
                        try:
                            self.lock_file.unlink()
                        except FileNotFoundError:
                            pass
                except FileNotFoundError:
                    pass
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Lock error: {e}")
                time.sleep(0.1)
        return False

    def _release_lock(self):
        try:
            self.lock_file.unlink()
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Unlock error: {e}")

    def _read_state(self) -> dict:
        try:
            import json
            if self.state_file.exists():
                with open(self.state_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read rate limit state: {e}")
        return {"tokens": self.max_tokens, "last_update": time.time()}

    def _write_state(self, state: dict):
        try:
            import json
            with open(self.state_file, "w") as f:
                json.dump(state, f)
        except Exception as e:
            logger.error(f"Failed to write rate limit state: {e}")

    async def acquire(self) -> float:
        """
        Wait for a token to become available. Returns wait time in seconds.
        Call this before making an API request.
        """
        while True:
            if not self._acquire_lock():
                logger.warning("Could not acquire rate limit lock, proceeding carefully")
                await asyncio.sleep(1)
                continue

            try:
                state = self._read_state()
                tokens = float(state.get("tokens", self.max_tokens))
                last_update = float(state.get("last_update", time.time()))
                
                now = time.time()
                elapsed = now - last_update
                
                # Refill
                new_tokens = min(self.max_tokens, tokens + elapsed * self.rate)
                
                wait_time = 0.0
                
                if new_tokens >= 1.0:
                    # Consume
                    state["tokens"] = new_tokens - 1.0
                    state["last_update"] = now
                    self._write_state(state)
                    # Success
                else:
                    # Wait
                    wait_time = (1.0 - new_tokens) / self.rate
                    # Update state just to record the refill so far (optional but good for precision)
                    state["tokens"] = new_tokens
                    state["last_update"] = now
                    self._write_state(state)
            finally:
                self._release_lock()

            if wait_time <= 0:
                return 0.0
            
            # Wait outside lock
            if wait_time > 0:
                # Add a tiny buffer to ensure we are over the line next time
                logger.info(f"Rate limiting: global wait {wait_time:.2f}s")
                await asyncio.sleep(wait_time + 0.1)
                # Loop back to try acquire again


# Global singleton
_global_rate_limiter: FileLockRateLimiter | None = None


def get_global_rate_limiter(requests_per_minute: int = 8) -> FileLockRateLimiter:
    """
    Get the global rate limiter singleton.
    Shared across all processes via file locking.
    """
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = FileLockRateLimiter(requests_per_minute)
        logger.info(f"Created global file-based rate limiter: {requests_per_minute} RPM")
    return _global_rate_limiter

# Rate limit error codes/messages to catch
RATE_LIMIT_INDICATORS = ["429", "TooManyRequests", "RESOURCE_EXHAUSTED", "rate limit", "quota"]


def is_rate_limit_error(error: Exception) -> bool:
    """Check if an exception is a rate limit error."""
    error_str = str(error).lower()
    return any(indicator.lower() in error_str for indicator in RATE_LIMIT_INDICATORS)


async def retry_with_backoff(
    async_gen_func,
    max_retries: int = 5,
    base_delay: float = 2.0,
    max_delay: float = 60.0,
    jitter: float = 0.5
) -> AsyncIterator[Any]:
    """
    Wraps an async generator function with retry logic and exponential backoff.
    
    Args:
        async_gen_func: A callable that returns an async generator
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay cap in seconds
        jitter: Random jitter factor (0-1) to add to delays
    
    Yields:
        Items from the async generator
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            async for item in async_gen_func():
                yield item
            return  # Success - exit the retry loop
        except Exception as e:
            last_error = e
            
            if not is_rate_limit_error(e):
                # Not a rate limit error, re-raise immediately
                raise
            
            if attempt >= max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded for rate limit error")
                raise
            
            # Calculate delay with exponential backoff + jitter
            delay = min(base_delay * (2 ** attempt), max_delay)
            jitter_amount = delay * jitter * random.random()
            total_delay = delay + jitter_amount
            
            logger.warning(
                f"Rate limit hit (attempt {attempt + 1}/{max_retries + 1}). "
                f"Retrying in {total_delay:.1f}s... Error: {str(e)[:100]}"
            )
            
            await asyncio.sleep(total_delay)
    
    # Should not reach here, but just in case
    if last_error:
        raise last_error


class RateLimitRetryRunner:
    """
    A wrapper around InMemoryRunner that adds retry logic for rate limits.
    
    IMPORTANT: On each retry, we use a fresh session ID to prevent duplicate
    messages from accumulating in the session history. The ADK's InMemoryRunner
    adds new_message to the session each time run_async() is called, so retrying
    with the same session would cause N copies of the message to be sent.
    """
    
    def __init__(self, runner, max_retries: int = 5, base_delay: float = 2.0):
        self.runner = runner
        self.max_retries = max_retries
        self.base_delay = base_delay
    
    @property
    def app_name(self):
        return self.runner.app_name
    
    @property
    def session_service(self):
        return self.runner.session_service
    
    async def run_async(self, user_id: str, session_id: str, new_message) -> AsyncIterator[Any]:
        """
        Wrapper for runner.run_async with retry logic.
        Uses a unique session ID for each attempt to prevent message duplication.
        """
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            # Generate unique session ID for each attempt to avoid message accumulation
            attempt_session_id = session_id if attempt == 0 else f"{session_id}_retry_{attempt}"
            
            try:
                # Create session for retry attempts (first attempt session is created by executor)
                if attempt > 0:
                    try:
                        await self.session_service.create_session(
                            app_name=self.app_name,
                            user_id=user_id,
                            session_id=attempt_session_id
                        )
                    except Exception as e:
                        logger.debug(f"Session create for retry attempt {attempt}: {e}")
                
                async for event in self.runner.run_async(
                    user_id=user_id,
                    session_id=attempt_session_id,
                    new_message=new_message
                ):
                    yield event
                return  # Success - exit the retry loop
                
            except Exception as e:
                last_error = e
                
                if not is_rate_limit_error(e):
                    # Not a rate limit error, re-raise immediately
                    raise
                
                if attempt >= self.max_retries:
                    logger.error(f"Max retries ({self.max_retries}) exceeded for rate limit error")
                    raise
                
                # Calculate delay with exponential backoff + jitter
                import random
                delay = min(self.base_delay * (2 ** attempt), 60.0)
                jitter_amount = delay * 0.5 * random.random()
                total_delay = delay + jitter_amount
                
                logger.warning(
                    f"Rate limit hit (attempt {attempt + 1}/{self.max_retries + 1}). "
                    f"Retrying in {total_delay:.1f}s with fresh session..."
                )
                
                await asyncio.sleep(total_delay)
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error
