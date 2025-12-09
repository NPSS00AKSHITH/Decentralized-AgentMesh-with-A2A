import os
import asyncio
from typing import Dict, Any, List
from lib.utils.logging_config import setup_logging, correlation_id_var
from lib.function_tool import function_tool
from lib.utils.communication import global_client
from lib.tools.real_maps_tool import real_maps_tool
from lib.utils.pushover import notify_utility_control

logger = setup_logging("utility-tools")

def get_cid():
    return correlation_id_var.get() or "UNKNOWN"


# =============================================================================
# UTILITY AGENT'S DOMAIN TOOLS (Own Specialty)
# =============================================================================

@function_tool(name="shutdown_power_grid", description="Cuts power to a specific zone to prevent electrical fires.")
async def shutdown_power_grid(zone: str, reason: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"POWER SHUTDOWN: {zone} due to {reason}", extra={"correlation_id": cid})
    
    await asyncio.sleep(1)
    affected_customers = 1500
    
    # Send Pushover notification to utility control center
    notification = await notify_utility_control(
        action="Power Grid SHUTDOWN",
        region=zone,
        details=f"Reason: {reason}. Affected: {affected_customers} customers."
    )
    
    return {
        "status": "shutdown_complete",
        "message": f"Notified power station, shutting down power grid in {zone}",
        "grid_id": f"GRID-{zone.upper()}",
        "affected_customers": affected_customers,
        "reason": reason
    }


@function_tool(name="cut_gas_supply", description="Isolates gas mains in a region to prevent explosions.")
async def cut_gas_supply(region: str, severity: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"GAS CUTOFF: {region} [Severity: {severity}]", extra={"correlation_id": cid})
    
    await asyncio.sleep(2)
    
    # Send Pushover notification to utility control center
    notification = await notify_utility_control(
        action="Gas Supply ISOLATED",
        region=region,
        details=f"Severity: {severity}. Pressure: 0 PSI. Valves closed."
    )
    
    return {
        "status": "valves_closed",
        "message": f"Notified gas station, isolating gas supply in {region}",
        "region": region,
        "pressure_reading": "0 PSI",
        "action_taken": "emergency_isolation"
    }


@function_tool(name="restore_water_pressure", description="Boosts water pressure for fire hydrants in a sector.")
async def restore_water_pressure(sector: str, target_psi: int = 80) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"WATER BOOST: {sector} to {target_psi} PSI", extra={"correlation_id": cid})
    
    return {
        "status": "pressure_boosted",
        "current_psi": target_psi,
        "sector": sector
    }


@function_tool(name="evaluate_infrastructure_risk", description="Checks risk levels for critical infrastructure near a location.")
async def evaluate_infrastructure_risk(location: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"RISK EVAL: {location}", extra={"correlation_id": cid})
    
    loc_data = await real_maps_tool.lookup_location(location)
    
    risk_level = "LOW"
    hazards = []
    
    if "industrial" in location.lower() or "factory" in location.lower():
        risk_level = "HIGH"
        hazards = ["Chemical Storage", "High Voltage Lines"]
    elif "market" in location.lower():
        risk_level = "MEDIUM"
        hazards = ["Dense Gas Lines"]
        
    return {
        "location": location,
        "risk_level": risk_level,
        "nearby_hazards": hazards,
        "coordinates": loc_data
    }


@function_tool(name="confirm_task", description="Confirms receipt and execution of a priority task.")
async def confirm_task(status: str = "completed", message: str = "Task executed.", target_agent: str = "dispatch-agent") -> Dict[str, Any]:
    cid = get_cid()
    
    # Normalize agent name (handle LLM variations like "dispatch_agent" -> "dispatch-agent")
    normalized_target = target_agent.replace("_", "-")
    if not normalized_target.endswith("-agent"):
        normalized_target = f"{normalized_target}-agent"
    
    logger.info(f"CONFIRMING: {status} to {normalized_target}", extra={"correlation_id": cid})
    try:
        import json
        payload = json.dumps({"type": "HANDSHAKE_RESULT", "correlation_id": cid, "status": status, "message": message})
        await global_client.send_message(source_agent="utility-agent", target_agent=normalized_target, message_text=payload, correlation_id=cid)
        return {"status": "sent", "target": normalized_target}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =============================================================================
# DELEGATION TOOLS (Delegate to Specialist Agents)
# =============================================================================

from lib.tools.delegation_tool import (
    delegate_to_fire_chief_from_utility as delegate_to_fire_chief,
    delegate_to_medical_from_utility as delegate_to_medical,
    delegate_to_civic_alert_from_utility as delegate_to_civic_alert,
    delegate_to_police_from_utility as delegate_to_police
)