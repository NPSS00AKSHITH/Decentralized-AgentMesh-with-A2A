import asyncio
from typing import Dict, Any
from lib.utils.logging_config import setup_logging, correlation_id_var
from lib.function_tool import function_tool
from lib.utils.communication import global_client
from lib.utils.pushover import notify_emergency_report

logger = setup_logging("human-intake-tools")

def get_cid():
    return correlation_id_var.get() or "UNKNOWN"


# =============================================================================
# HUMAN INTAKE AGENT'S DOMAIN TOOLS
# =============================================================================

@function_tool(name="process_report", description="Processes a raw text report from a human user.")
async def process_report(raw_text: str, source: str = "web_ui") -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"PROCESSING REPORT: '{raw_text}'", extra={"correlation_id": cid})
    
    await asyncio.sleep(0.1)
    
    return {
        "status": "processed", 
        "data": {
            "original": raw_text, 
            "extracted_intent": "emergency",
            "confidence": 0.95
        }
    }


@function_tool(name="log_and_route_call", description="Logs call details and forwards verified info to Dispatch.")
async def log_and_route_call(raw_transcript: str, incident_type: str, location: str, severity: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"LOG & ROUTE: {incident_type} at {location}", extra={"correlation_id": cid})
    
    call_id = f"CALL-{cid[:8]}"
    
    # Send Pushover notification
    await notify_emergency_report(
        incident_type=incident_type,
        location=location,
        source="911 Call"
    )
    
    try:
        response = await global_client.send_message(
            source_agent="human-intake-agent", 
            target_agent="dispatch-agent",
            message_text=f"INTAKE REPORT [{call_id}]: {incident_type} at {location}. Severity: {severity}. Raw: {raw_transcript}",
            correlation_id=cid
        )
        return {
            "status": "logged_and_routed", 
            "message": f"Notified dispatch, emergency report submitted for {incident_type} at {location}",
            "call_id": call_id, 
            "dispatch_response": response
        }
    except Exception as e:
        logger.error(f"Failed to route call: {e}")
        return {"status": "failed", "error": str(e)}


@function_tool(name="calm_caller", description="Provides a script to de-escalate a panicked caller.")
async def calm_caller(caller_emotional_state: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"CALMING CALLER: State={caller_emotional_state}", extra={"correlation_id": cid})
    
    script = "I understand this is difficult, but help is on the way. Take a deep breath."
    
    if "angry" in caller_emotional_state.lower():
        script = "I am listening. I want to help you. Please tell me exactly what you see."
    elif "crying" in caller_emotional_state.lower() or "panic" in caller_emotional_state.lower():
        script = "Stay with me. Focus on my voice. You are doing a great job."
        
    return {
        "action": "provide_script", 
        "script": script,
        "advice": "Speak slowly and clearly."
    }


@function_tool(name="confirm_task", description="Confirms receipt and execution of a priority task.")
async def confirm_task(status: str = "completed", message: str = "Task executed.", target_agent: str = "dispatch-agent") -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"CONFIRMING: {status} to {target_agent}", extra={"correlation_id": cid})
    try:
        import json
        payload = json.dumps({"type": "HANDSHAKE_RESULT", "correlation_id": cid, "status": status, "message": message})
        await global_client.send_message(source_agent="human-intake-agent", target_agent=target_agent, message_text=payload, correlation_id=cid)
        return {"status": "sent", "target": target_agent}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =============================================================================
# DELEGATION TOOLS (Failover - Bypass Dispatch if down)
# =============================================================================

from lib.tools.delegation_tool import (
    delegate_to_fire_from_dispatch as delegate_to_fire,
    delegate_to_medical_from_dispatch as delegate_to_medical,
    delegate_to_police_from_dispatch as delegate_to_police,
    delegate_to_utility_from_dispatch as delegate_to_utility
)