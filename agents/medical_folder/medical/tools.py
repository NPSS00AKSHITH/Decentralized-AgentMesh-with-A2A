import os
import asyncio
from typing import Dict, Any
from lib.utils.logging_config import setup_logging, correlation_id_var
from lib.function_tool import function_tool
from lib.utils.communication import global_client
from lib.tools.real_maps_tool import real_maps_tool
from lib.utils.pushover import notify_hospital

logger = setup_logging("medical-tools")

def get_cid():
    return correlation_id_var.get() or "UNKNOWN"


# =============================================================================
# MEDICAL AGENT'S DOMAIN TOOLS (Own Specialty)
# =============================================================================

@function_tool(name="dispatch_ambulances", description="Dispatches ambulances to a specific location.")
async def dispatch_ambulances(location: str, number_of_units: int) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"DISPATCHING AMBULANCES: {number_of_units} units to {location}", extra={"correlation_id": cid})
    
    try:
        loc_data = await real_maps_tool.lookup_location(location)
        if loc_data.get("status") != "found":
            return {"error": f"Location '{location}' not found."}

        await asyncio.sleep(1)
        eta_minutes = 8
        
        # Send Pushover notification to hospital
        notification = await notify_hospital(
            location=location,
            ambulances=number_of_units,
            eta_minutes=eta_minutes
        )
        
        return {
            "status": "dispatched",
            "message": f"Notified hospital, dispatching {number_of_units} ambulance(s) to {location}",
            "units": number_of_units,
            "location": location,
            "eta_minutes": eta_minutes
        }
    except Exception as e:
        logger.error(f"Dispatch failed: {e}")
        return {"status": "failed", "error": str(e)}


@function_tool(name="triage_casualties", description="Performs triage assessment at a location.")
async def triage_casualties(location: str, casualty_count: int) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"TRIAGE: Assessing {casualty_count} casualties at {location}", extra={"correlation_id": cid})
    
    critical = int(casualty_count * 0.2)
    serious = int(casualty_count * 0.4)
    minor = casualty_count - critical - serious
    
    return {
        "status": "triage_complete",
        "location": location,
        "breakdown": {
            "critical": critical,
            "serious": serious,
            "minor": minor
        }
    }


@function_tool(name="prepare_medical_response", description="Prepares hospital resources.")
async def prepare_medical_response(incident_type: str, severity: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"PREPARING RESPONSE: {incident_type} [Severity: {severity}]", extra={"correlation_id": cid})
    
    return {
        "status": "prepared",
        "trauma_teams_activated": 2 if severity == "High" else 1,
        "beds_reserved": 20 if severity == "High" else 5
    }


@function_tool(name="confirm_support_request", description="Confirms a support request from another agent.")
async def confirm_support_request(
    target_agent: str, 
    status: str = "accepted", 
    details: str = "Medical units dispatched."
) -> Dict[str, Any]:
    cid = get_cid()
    
    # Normalize agent name (handle LLM variations like "fire_chief" -> "fire-chief-agent")
    normalized_target = target_agent.replace("_", "-")
    if not normalized_target.endswith("-agent"):
        normalized_target = f"{normalized_target}-agent"
    
    logger.info(f"CONFIRMING REQUEST to {normalized_target}: {status}", extra={"correlation_id": cid})
    
    try:
        import json
        payload = json.dumps({
            "type": "HANDSHAKE_RESULT",
            "correlation_id": cid,
            "status": status,
            "details": details
        })
        
        await global_client.send_message(
            source_agent="medical-agent",
            target_agent=normalized_target,
            message_text=payload,
            correlation_id=cid
        )
        return {"status": "confirmation_sent", "target": normalized_target}
    except Exception as e:
        logger.error(f"Failed to send confirmation: {e}")
        return {"status": "failed", "error": str(e)}


@function_tool(name="trigger_civic_alert", description="Triggers a civic alert for medical emergencies.")
async def trigger_civic_alert(message: str, zone: str, severity: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"MEDICAL ALERT BROADCAST: {message} in {zone}", extra={"correlation_id": cid})
    try:
        response = await global_client.send_message(
            source_agent="medical-agent",
            target_agent="civic-alert-agent",
            message_text=f"MEDICAL ALERT: {message}. Zone: {zone}. Severity: {severity}",
            correlation_id=cid
        )
        return {"status": "alert_broadcasted", "details": response}
    except Exception as e:
        logger.error(f"Failed to trigger Civic Alert: {e}")
        return {"status": "error", "message": str(e)}


# =============================================================================
# DELEGATION TOOLS (Delegate to Specialist Agents)
# =============================================================================

from lib.tools.delegation_tool import (
    delegate_to_fire_chief,
    delegate_to_utility_from_medical as delegate_to_utility,
    delegate_to_police_general_from_medical as delegate_to_police
)