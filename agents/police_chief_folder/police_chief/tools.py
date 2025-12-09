import os
import asyncio
from typing import Dict, Any, List
from lib.utils.logging_config import setup_logging, correlation_id_var
from lib.function_tool import function_tool
from lib.utils.communication import global_client
from lib.tools.real_maps_tool import real_maps_tool
from lib.utils.pushover import notify_police_dispatch

logger = setup_logging("police-chief-tools")

def get_cid():
    return correlation_id_var.get() or "UNKNOWN"


# =============================================================================
# POLICE CHIEF AGENT'S DOMAIN TOOLS
# =============================================================================

@function_tool(name="deploy_swat", description="Deploys SWAT teams to a high-risk location.")
async def deploy_swat(location: str, threat_level: str = "High") -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"SWAT DEPLOYMENT: {location} [Threat: {threat_level}]", extra={"correlation_id": cid})
    
    loc_data = await real_maps_tool.lookup_location(location)
    
    # Send Pushover notification
    await notify_police_dispatch(
        location=location,
        unit_type="SWAT Team",
        threat_level=threat_level
    )
    
    return {
        "status": "swat_en_route",
        "message": f"Notified police dispatch, deploying SWAT to {location}",
        "location": location,
        "coordinates": loc_data,
        "units": "Team-Alpha, Team-Bravo",
        "eta_minutes": 5
    }


@function_tool(name="cordon_area", description="Establishes a secure perimeter/cordon around a location.")
async def cordon_area(location: str, radius_meters: int) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"CORDON AREA: {location} (Radius: {radius_meters}m)", extra={"correlation_id": cid})
    
    try:
        loc_data = await real_maps_tool.lookup_location(location)
        
        return {
            "status": "cordon_established",
            "location": location,
            "radius": radius_meters,
            "coordinates": loc_data
        }
    except Exception as e:
        logger.error(f"Cordon setup failed: {e}")
        return {"status": "failed", "error": str(e)}


@function_tool(name="broadcast_via_pa_system", description="Broadcasts a message via local PA systems (Police/Street).")
async def broadcast_via_pa_system(location: str, message: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"PA BROADCAST: '{message}' at {location}", extra={"correlation_id": cid})
    
    return {
        "status": "broadcast_active",
        "location": location,
        "message": message,
        "device": "Vehicle PA + Street Speakers"
    }


@function_tool(name="trigger_civic_alert", description="Triggers a wide-area civic alert via the Civic Alert Agent.")
async def trigger_civic_alert(location: str, message: str, severity: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"TRIGGERING CIVIC ALERT: {message}", extra={"correlation_id": cid})
    
    try:
        response = await global_client.send_message(
            source_agent="police-chief-agent",
            target_agent="civic-alert-agent",
            message_text=f"POLICE EMERGENCY: {message}. Location: {location}. Severity: {severity}",
            correlation_id=cid
        )
        return {"status": "alert_requested", "civic_response": response}
    except Exception as e:
        logger.error(f"Failed to contact civic-alert-agent: {e}")
        return {"status": "failed", "error": str(e)}


@function_tool(name="emergency_public_broadcast", description="Emergency PA broadcast when Civic Alert is unavailable. Sends Pushover notification.")
async def emergency_public_broadcast(location: str, message: str, severity: str = "HIGH") -> Dict[str, Any]:
    """
    Emergency PA broadcast as Civic Alert failover.
    This tool sends a Pushover notification and activates Police PA systems.
    Use this when Civic Alert Agent is down or unresponsive.
    """
    cid = get_cid()
    logger.info(f"EMERGENCY PA BROADCAST: {message} at {location}", extra={"correlation_id": cid})
    
    from lib.utils.pushover import notify_pa_broadcast
    
    try:
        # Send Pushover notification
        notification = await notify_pa_broadcast(
            message=message,
            location=location,
            source_agent="police-chief-agent"
        )
        
        # Simulate PA system activation
        await asyncio.sleep(0.5)
        
        return {
            "status": "broadcast_active",
            "message": f"Emergency PA broadcast active: {message}",
            "location": location,
            "severity": severity,
            "channels": ["police_pa_vehicles", "street_speakers", "mobile_alert"],
            "pushover_status": notification.get("status", "unknown"),
            "failover_reason": "Civic Alert Agent unavailable"
        }
    except Exception as e:
        logger.error(f"Emergency broadcast failed: {e}", extra={"correlation_id": cid})
        return {"status": "failed", "error": str(e)}


@function_tool(name="confirm_support_request", description="Sends a structured confirmation back to the requesting agent.")
async def confirm_support_request(
    target_agent: str, 
    status: str = "accepted", 
    details: str = "Request received."
) -> Dict[str, Any]:
    cid = get_cid()
    
    # Normalize agent name (handle LLM variations like "fire_chief" -> "fire-chief-agent")
    normalized_target = target_agent.replace("_", "-")
    if not normalized_target.endswith("-agent"):
        normalized_target = f"{normalized_target}-agent"
    
    logger.info(f"CONFIRMING SUPPORT to {normalized_target}: {status}", extra={"correlation_id": cid})
    
    try:
        import json
        message_payload = json.dumps({
            "type": "HANDSHAKE_RESULT",
            "status": status,
            "details": details,
            "correlation_id": cid
        })

        await global_client.send_message(
            source_agent="police-chief-agent",
            target_agent=normalized_target,
            message_text=message_payload,
            correlation_id=cid
        )
        return {"status": "confirmation_sent", "target": normalized_target}
    except Exception as e:
        logger.error(f"Failed to send confirmation: {e}")
        return {"status": "failed", "error": str(e)}


# =============================================================================
# DELEGATION TOOLS (Delegate to Specialist Agents)
# =============================================================================

from lib.tools.delegation_tool import (
    delegate_to_fire_from_police as delegate_to_fire,
    delegate_to_medical_from_police as delegate_to_medical,
    delegate_to_utility_from_police as delegate_to_utility
)