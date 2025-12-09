import logging
import asyncio
from typing import Dict, Any

from lib.utils.logging_config import setup_logging, correlation_id_var
from lib.function_tool import function_tool
from lib.utils.communication import global_client
from lib.tools.real_maps_tool import real_maps_tool
from lib.utils.pushover import notify_fire_station

logger = setup_logging("fire-chief-tools")

def get_cid():
    return correlation_id_var.get() or "UNKNOWN"


# =============================================================================
# FIRE CHIEF'S DOMAIN TOOLS (Own Specialty)
# =============================================================================

@function_tool(name="fire_map_lookup", description="Geocodes an address to get coordinates.")
async def fire_map_lookup(address: str) -> Dict[str, Any]:
    logger.info(f"MAP LOOKUP: {address}", extra={"correlation_id": get_cid()})
    return await real_maps_tool.lookup_location(address)


@function_tool(name="deploy_units", description="Deploys fire units to a location.")
async def deploy_units(location: str, unit_type: str = "engine", count: int = 1) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"DEPLOYING: {count} x {unit_type} to {location}", extra={"correlation_id": cid})
    
    route_info = await real_maps_tool.find_nearest_resource("fire_station", location)
    eta_minutes = route_info.get("duration_minutes", 12) if isinstance(route_info, dict) else 12
    
    # Send Pushover notification to fire station
    notification = await notify_fire_station(
        location=location,
        units=count,
        unit_type=unit_type,
        eta_minutes=eta_minutes
    )
    
    return {
        "status": "deployed",
        "message": f"Notified fire station, sending {count} {unit_type}(s) to {location}",
        "location": location,
        "units_dispatched": count,
        "type": unit_type,
        "eta_minutes": eta_minutes
    }


@function_tool(name="estimate_fire_severity", description="Estimates fire severity based on description.")
async def estimate_fire_severity(description: str) -> Dict[str, Any]:
    severity = "low"
    desc_lower = description.lower()
    if any(x in desc_lower for x in ["explosion", "huge", "massive", "trapped", "chemical"]):
        severity = "critical"
    elif "smoke" in desc_lower or "flame" in desc_lower:
        severity = "medium"
    return {"severity": severity}


@function_tool(name="trigger_civic_alert", description="Triggers civic alert with Police PA fallback.")
async def trigger_civic_alert(message: str, region: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"TRIGGERING ALERT: {message}", extra={"correlation_id": cid})
    
    # 1. Try Digital Broadcast (Civic Alert Agent)
    try:
        await global_client.send_message(
            source_agent="fire-chief-agent",
            target_agent="civic-alert-agent",
            message_text=f"EMERGENCY ALERT: {message} in {region}",
            correlation_id=cid
        )
        return {"status": "digital_alert_sent", "method": "civic_alert_agent"}
    
    except Exception as e:
        logger.warning(f"Digital Alert Failed: {e}. Switching to ANALOG FALLBACK.", extra={"correlation_id": cid})
        
        # 2. Fallback to Police PA System
        try:
            await global_client.send_request_with_handshake(
                source_agent="fire-chief-agent",
                target_agent="police-chief-agent",
                payload={
                    "action": "broadcast_via_pa_system",
                    "location": region,
                    "message": f"FALLBACK ALERT: {message}",
                    "details": "Civic Alert System is DOWN. Requesting manual PA broadcast."
                },
                correlation_id=cid
            )
            return {"status": "analog_fallback_active", "method": "police_pa_system"}
        except Exception as e2:
            return {"status": "critical_failure", "error": "Both Digital and Analog channels failed."}


@function_tool(name="confirm_incident", description="Confirms receipt of an incident request.")
async def confirm_incident(
    status: str = "accepted", 
    message: str = "Units deploying.", 
    target_agent: str = "dispatch-agent"
) -> Dict[str, Any]:
    cid = get_cid()
    
    # Normalize agent name (handle LLM variations like "dispatch_agent" -> "dispatch-agent")
    normalized_target = target_agent.replace("_", "-")
    if not normalized_target.endswith("-agent"):
        normalized_target = f"{normalized_target}-agent"
    
    logger.info(f"CONFIRMING to {normalized_target}: {status}", extra={"correlation_id": cid})
    
    try:
        import json
        payload = json.dumps({
            "type": "HANDSHAKE_RESULT",
            "correlation_id": cid,
            "status": status,
            "message": message
        })
        
        await global_client.send_message(
            source_agent="fire-chief-agent",
            target_agent=normalized_target,
            message_text=payload,
            correlation_id=cid
        )
        return {"status": "confirmation_sent", "target": normalized_target}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


# =============================================================================
# DELEGATION TOOLS (Delegate to Specialist Agents)
# =============================================================================
# Instead of duplicating tools, we delegate to specialist agents and let their
# LLMs decide which tools to use.

from lib.tools.delegation_tool import (
    delegate_to_medical,
    delegate_to_utility,
    delegate_to_police_general_from_fire as delegate_to_police
)