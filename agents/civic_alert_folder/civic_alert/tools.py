import asyncio
from typing import Dict, Any
from lib.utils.logging_config import setup_logging, correlation_id_var
from lib.function_tool import function_tool
from lib.utils.communication import global_client
from lib.utils.pushover import notify_public_alert

logger = setup_logging("civic-alert-tools")

def get_cid():
    return correlation_id_var.get() or "UNKNOWN"


# =============================================================================
# CIVIC ALERT AGENT'S DOMAIN TOOLS
# =============================================================================

@function_tool(name="broadcast_alert", description="Broadcasts emergency message via digital channels.")
async def broadcast_alert(message: str, zone: str, severity: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"BROADCASTING: {message} to {zone} [Severity: {severity}]", extra={"correlation_id": cid})
    
    try:
        # Send Pushover notification
        await notify_public_alert(message=message, zone=zone, severity=severity)
        
        # Simulate Digital Signage Update
        await asyncio.sleep(0.5)
        
        return {
            "status": "broadcast_sent",
            "message": f"Notified public, alert broadcasted to {zone}",
            "channels": ["mobile", "digital_signage", "tv_override"],
            "zone": zone
        }
    except Exception as e:
        logger.error(f"Broadcast failed: {e}", extra={"correlation_id": cid})
        return {"status": "error", "error": str(e)}


@function_tool(name="activate_sirens", description="Activates physical siren network in a zone.")
async def activate_sirens(zone: str, duration_seconds: int = 60) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"SIRENS ACTIVE: {zone} for {duration_seconds}s", extra={"correlation_id": cid})
    
    await asyncio.sleep(1)
    
    return {
        "status": "sirens_active",
        "zone": zone,
        "duration": duration_seconds
    }


@function_tool(name="confirm_task", description="Confirms receipt and execution of a priority task.")
async def confirm_task(status: str = "completed", message: str = "Task executed.", target_agent: str = "dispatch-agent") -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"CONFIRMING: {status} to {target_agent}", extra={"correlation_id": cid})
    try:
        import json
        payload = json.dumps({"type": "HANDSHAKE_RESULT", "correlation_id": cid, "status": status, "message": message})
        await global_client.send_message(source_agent="civic-alert-agent", target_agent=target_agent, message_text=payload, correlation_id=cid)
        return {"status": "sent", "target": target_agent}
    except Exception as e:
        return {"status": "error", "error": str(e)}