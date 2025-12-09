import os
import asyncio
import random
from typing import Dict, Any
from lib.utils.logging_config import setup_logging, correlation_id_var
from lib.function_tool import function_tool
from lib.utils.communication import global_client
from lib.utils.pushover import notify_sensor_alert

logger = setup_logging("iot-sensor-tools")

def get_cid():
    return correlation_id_var.get() or "UNKNOWN"


# =============================================================================
# IOT SENSOR AGENT'S DOMAIN TOOLS
# =============================================================================

@function_tool(name="read_sensor_data", description="Reads current environmental data from sensors in a zone.")
async def read_sensor_data(zone: str, sensor_type: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"READING SENSOR: {sensor_type} in {zone}", extra={"correlation_id": cid})
    
    await asyncio.sleep(0.1)
    
    value = 0.0
    status = "NORMAL"
    
    if sensor_type == "temperature":
        value = random.uniform(20.0, 45.0)
        if value > 40: status = "CRITICAL"
    elif sensor_type == "smoke":
        value = random.uniform(0.0, 100.0)
        if value > 50: status = "CRITICAL"
    elif sensor_type == "seismic":
        value = random.uniform(0.0, 9.0)
        if value > 4.0: status = "CRITICAL"
        
    return {
        "zone": zone, 
        "sensor_type": sensor_type, 
        "value": round(value, 2), 
        "status": status,
        "timestamp": "2025-12-03T18:00:00Z"
    }


@function_tool(name="read_environmental_sensors", description="Reads composite environmental data (smoke, temp, seismic).")
async def read_environmental_sensors(zone: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"READING ENV SENSORS: {zone}", extra={"correlation_id": cid})
    
    await asyncio.sleep(0.1)
    
    temp = round(random.uniform(20.0, 50.0), 1)
    smoke = round(random.uniform(0, 150), 0)
    seismic = round(random.uniform(0, 3.0), 2)
    
    status = "NORMAL"
    if temp > 45 or smoke > 80 or seismic > 2.0:
        status = "CRITICAL"
        
    return {
        "zone": zone,
        "readings": {
            "temperature_c": temp, 
            "smoke_ppm": smoke, 
            "seismic_richter": seismic
        },
        "status": status,
        "timestamp": "2025-12-03T18:00:00Z"
    }


@function_tool(name="trigger_alarm", description="Triggers the physical alarm and alerts the network.")
async def trigger_alarm(zone: str, alarm_type: str, severity: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"TRIGGERING ALARM: {alarm_type} in {zone}", extra={"correlation_id": cid})
    
    # Send Pushover notification
    await notify_sensor_alert(zone=zone, sensor_type=alarm_type, status=severity)
    
    return {
        "status": "alarm_active", 
        "zone": zone,
        "message": f"Notified control center, alarm triggered for {alarm_type} in {zone}",
        "hardware_response": "Siren Activated"
    }


@function_tool(name="confirm_task", description="Confirms receipt and execution of a priority task.")
async def confirm_task(status: str = "completed", message: str = "Task executed.", target_agent: str = "dispatch-agent") -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"CONFIRMING: {status} to {target_agent}", extra={"correlation_id": cid})
    try:
        import json
        payload = json.dumps({"type": "HANDSHAKE_RESULT", "correlation_id": cid, "status": status, "message": message})
        await global_client.send_message(source_agent="iot-sensor-agent", target_agent=target_agent, message_text=payload, correlation_id=cid)
        return {"status": "sent", "target": target_agent}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =============================================================================
# DELEGATION TOOLS (Delegate to Specialist Agents)
# =============================================================================

from lib.tools.delegation_tool import (
    delegate_to_fire_from_iot as delegate_to_fire,
    delegate_to_utility_from_iot as delegate_to_utility
)