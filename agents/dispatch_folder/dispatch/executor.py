import logging
import asyncio
import json 
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import TaskState, TaskStatusUpdateEvent, TaskStatus
from a2a.utils import new_agent_text_message
from google.adk.runners import InMemoryRunner
from lib.utils.retry import get_global_rate_limiter, RateLimitRetryRunner
from google.genai import types

from .dispatch_agent import dispatch_agent
from lib.utils.logging_config import correlation_id_var
from lib.utils.communication import GlobalA2AClient

logger = logging.getLogger("dispatch-executor")
a2a = GlobalA2AClient()

class DispatchExecutor(AgentExecutor):
    def __init__(self):
        # Single shared runner instance for all requests
        self.runner = InMemoryRunner(dispatch_agent)
        self.rate_limiter = get_global_rate_limiter()
        self.retry_runner = RateLimitRetryRunner(self.runner)
        self.created_sessions = set()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        if not context.message.parts:
            return

        part = context.message.parts[0]
        try:
            # Handle Pydantic RootModel wrappers if present
            if hasattr(part, "root"):
                part = part.root

            if hasattr(part, "text"):
                user_query = part.text
            elif isinstance(part, dict):
                user_query = part.get("text", str(part))
            else:
                user_query = str(part)

            # Fallback: If user_query looks like a Pydantic repr (e.g. root=TextPart(...))
            if "root=TextPart" in user_query or "kind='text'" in user_query:
                import re
                match = re.search(r"text=(['\"])(.*?)\1", user_query, re.DOTALL)
                if match:
                    extracted = match.group(2)
                    extracted = extracted.replace(r"\'", "'").replace(r'\"', '"')
                    user_query = extracted
                    logger.info(f"Recovered text from repr: {user_query[:50]}...")
        except Exception:
            user_query = "Status Check"

        correlation_id = context.metadata.get("correlation_id", "UNKNOWN")
        token = correlation_id_var.set(correlation_id)
        logger.info(f"Processing: {user_query[:50]}...", extra={"correlation_id": correlation_id})

        try:
            final_query_text = user_query
            try:
                data = json.loads(user_query)
                if isinstance(data, dict):
                    msg_type = data.get("type")
                    
                    if msg_type == "HANDSHAKE_RESULT":
                        cid = data.get("correlation_id")
                        logger.info(f"Resolving Handshake {cid}")
                        a2a.resolve_handshake(cid, data)
                        return 

                    elif msg_type == "HANDSHAKE_REQUEST":
                        payload = data.get("payload", {})
                        source = data.get("source", "Unknown")
                        final_query_text = (
                            f"SYSTEM ALERT: Incoming Priority Request from {source}.\n"
                            f"DATA: {json.dumps(payload, indent=2)}\n"
                            "INSTRUCTION: Execute the necessary action immediately. "
                            "Then, you MUST call your confirmation tool (e.g., 'confirm_receipt' or 'confirm_incident') "
                            "to notify the sender."
                        )
            except json.JSONDecodeError:
                pass

            if context.task_id:
                 await event_queue.enqueue_event(TaskStatusUpdateEvent(
                     contextId=context.context_id, taskId=context.task_id,
                     status=TaskStatus(state=TaskState.working), final=False
                 ))

            session_id = context.context_id
            
            # Create session if not exists using the shared runner
            # IMPORTANT: Use runner's app_name to match internal lookup
            if session_id not in self.created_sessions:
                await self.runner.session_service.create_session(
                    app_name=self.runner.app_name,
                    user_id="system",
                    session_id=session_id
                )
                self.created_sessions.add(session_id)
            
            content = types.Content(role="user", parts=[types.Part.from_text(text=final_query_text)])
            
            # Proactive rate limiting - wait if needed before API call
            await self.rate_limiter.acquire()
            
            final_text = ""
            delegation_results = []  # Track delegation responses
            
            async for event in self.retry_runner.run_async(user_id="system", session_id=session_id, new_message=content):
                if hasattr(event, 'content') and event.content and event.content.parts:
                    for part in event.content.parts:
                        if hasattr(part, 'text') and part.text:
                            final_text = part.text
                        # Track function responses (delegation results)
                        if hasattr(part, 'function_response') and part.function_response:
                            try:
                                resp = part.function_response
                                func_name = getattr(resp, 'name', 'unknown')
                                result = getattr(resp, 'response', {})
                                if 'delegate' in func_name or 'assign' in func_name:
                                    delegation_results.append({
                                        'tool': func_name,
                                        'result': result
                                    })
                            except Exception:
                                pass

            # Handle empty LLM response - synthesize from delegation results
            if not final_text:
                logger.warning("LLM returned empty response - synthesizing from tool results")
                if delegation_results:
                    # Build response from delegation results
                    response_parts = ["📞 **Dispatch Response:**\n"]
                    for dr in delegation_results:
                        tool = dr.get('tool', '')
                        result = dr.get('result', {})
                        if isinstance(result, dict):
                            status = result.get('status', 'unknown')
                            target = result.get('delegated_to', result.get('notified_agents', ''))
                            resp_msg = result.get('response', result.get('message', ''))
                            
                            if 'fire' in tool.lower():
                                response_parts.append(f"\n🔥 **Fire Response** (via {target}):\n{resp_msg or status}")
                            elif 'medical' in tool.lower():
                                response_parts.append(f"\n🏥 **Medical Response** (via {target}):\n{resp_msg or status}")
                            elif 'police' in tool.lower():
                                response_parts.append(f"\n🚔 **Police Response** (via {target}):\n{resp_msg or status}")
                            elif 'utility' in tool.lower():
                                response_parts.append(f"\n⚡ **Utility Response** (via {target}):\n{resp_msg or status}")
                            elif 'commander' in tool.lower():
                                lead = result.get('lead_agency', '')
                                response_parts.append(f"\n👨‍✈️ **Incident Commander:** {lead}")
                    
                    final_text = "\n".join(response_parts) + "\n\n✅ Emergency services responding."
                else:
                    final_text = "I acknowledge your request but was unable to generate a complete response. Please retry or contact a human operator."

            await event_queue.enqueue_event(new_agent_text_message(
                text=str(final_text),
                context_id=context.context_id
            ))
            
            if context.task_id:
                await event_queue.enqueue_event(TaskStatusUpdateEvent(
                    contextId=context.context_id, taskId=context.task_id,
                    status=TaskStatus(state=TaskState.completed), final=True
                ))
            
        except Exception as e:
            logger.error(f"Executor failed: {e}", exc_info=True)
            if context.task_id:
                try:
                    await event_queue.enqueue_event(TaskStatusUpdateEvent(
                        contextId=context.context_id, taskId=context.task_id,
                        status=TaskStatus(state=TaskState.failed), final=True
                    ))
                except: pass
        finally:
            correlation_id_var.reset(token)

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass