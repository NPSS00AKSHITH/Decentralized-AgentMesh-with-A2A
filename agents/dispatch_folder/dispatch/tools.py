import asyncio
from typing import Dict, Any
from lib.utils.logging_config import setup_logging, correlation_id_var
from lib.function_tool import function_tool
from lib.utils.communication import global_client

logger = setup_logging("dispatch-tools")

def get_cid():
    return correlation_id_var.get() or "UNKNOWN"


# =============================================================================
# DISPATCH AGENT'S DOMAIN TOOLS
# =============================================================================

@function_tool(name="assign_incident_commander", description="Designates a lead agency for a multi-agency incident.")
async def assign_incident_commander(incident_id: str, lead_agency: str, involved_agencies: list[str] = None) -> Dict[str, Any]:
    """
    Assigns incident commander and notifies ONLY the relevant agencies.
    
    Args:
        incident_id: Unique incident identifier
        lead_agency: The agency taking command (e.g., "Fire Department")
        involved_agencies: List of agencies involved (e.g., ["fire", "medical"])
                          If not provided, only the lead agency is notified.
    """
    cid = get_cid()
    logger.info(f"ASSIGNING COMMANDER: {lead_agency} for {incident_id}", extra={"correlation_id": cid})
    
    # Map agency types to agent names
    agency_map = {
        "fire": "fire-chief-agent",
        "medical": "medical-agent",
        "police": "police-chief-agent",
        "utility": "utility-agent"
    }
    
    # Determine which agents to notify
    if involved_agencies:
        # Only notify specified agencies
        agents_to_notify = [agency_map[a.lower()] for a in involved_agencies if a.lower() in agency_map]
    else:
        # Fallback: only notify based on lead agency
        lead_lower = lead_agency.lower()
        if "fire" in lead_lower:
            agents_to_notify = ["fire-chief-agent"]
        elif "medical" in lead_lower or "hospital" in lead_lower:
            agents_to_notify = ["medical-agent"]
        elif "police" in lead_lower:
            agents_to_notify = ["police-chief-agent"]
        else:
            agents_to_notify = ["fire-chief-agent"]  # Default to fire
    
    # Broadcast only to relevant agencies
    if agents_to_notify:
        await global_client.broadcast(
            source_agent="dispatch-agent",
            agents=agents_to_notify,
            message_text=f"COMMAND UPDATE: {lead_agency} is now Incident Commander for {incident_id}."
        )
    
    return {
        "status": "commander_assigned",
        "incident_id": incident_id,
        "lead_agency": lead_agency,
        "notified_agents": agents_to_notify
    }


@function_tool(name="confirm_receipt", description="Confirms receipt of a message or request from another agent.")
async def confirm_receipt(
    target_agent: str, 
    status: str = "received", 
    message: str = "Acknowledged."
) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"CONFIRMING RECEIPT to {target_agent}: {status}", extra={"correlation_id": cid})
    
    try:
        import json
        payload = json.dumps({
            "type": "HANDSHAKE_RESULT",
            "correlation_id": cid,
            "status": status,
            "message": message
        })
        
        await global_client.send_message(
            source_agent="dispatch-agent",
            target_agent=target_agent,
            message_text=payload,
            correlation_id=cid
        )
        return {"status": "confirmation_sent", "target": target_agent}
    except Exception as e:
        logger.error(f"Failed to send confirmation: {e}")
        return {"status": "failed", "error": str(e)}


# =============================================================================
# DELEGATION TOOLS (Delegate to Specialist Agents)
# =============================================================================

from lib.tools.delegation_tool import (
    delegate_to_fire_from_dispatch as delegate_to_fire,
    delegate_to_medical_from_dispatch as delegate_to_medical,
    delegate_to_police_from_dispatch as delegate_to_police,
    delegate_to_utility_from_dispatch as delegate_to_utility
)