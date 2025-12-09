import os
import asyncio
import random
from typing import Dict, Any, List
from lib.utils.logging_config import setup_logging, correlation_id_var
from lib.function_tool import function_tool
from lib.utils.communication import global_client

logger = setup_logging("camera-tools")

def get_cid():
    return correlation_id_var.get() or "UNKNOWN"


# =============================================================================
# CAMERA AGENT'S DOMAIN TOOLS
# =============================================================================

@function_tool(name="analyze_feed", description="Analyzes video feed from a specific camera ID.")
async def analyze_feed(camera_id: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"ANALYZING FEED: {camera_id}", extra={"correlation_id": cid})
    await asyncio.sleep(1)
    
    events = []
    if random.random() < 0.3:
        events.append("Smoke Detected")
    if random.random() < 0.1:
        events.append("Crowd Gathering")
        
    return {
        "camera_id": camera_id,
        "status": "online",
        "detected_events": events,
        "timestamp": "2025-12-03T17:00:00Z"
    }


@function_tool(name="detect_fire", description="Runs specialized fire detection algorithm on a feed.")
async def detect_fire(location: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"FIRE DETECTION: Scanning {location}", extra={"correlation_id": cid})
    confidence = random.uniform(0.0, 1.0)
    is_fire = confidence > 0.8
    
    return {
        "location": location,
        "fire_detected": is_fire,
        "confidence": round(confidence, 2),
        "action_required": "Use delegate_to_fire tool if fire confirmed" if is_fire else None
    }


@function_tool(name="detect_fight", description="Runs fight detection algorithm on a camera feed to identify altercations or violence.")
async def detect_fight(location: str) -> Dict[str, Any]:
    """Detects fights/altercations at a location."""
    cid = get_cid()
    logger.info(f"FIGHT DETECTION: Scanning {location}", extra={"correlation_id": cid})
    await asyncio.sleep(0.5)
    
    confidence = random.uniform(0.5, 1.0)  # Higher base confidence for demo
    is_fight = confidence > 0.7
    
    return {
        "location": location,
        "fight_detected": is_fight,
        "confidence": round(confidence, 2),
        "severity": "HIGH" if confidence > 0.9 else "MEDIUM" if confidence > 0.8 else "LOW",
        "action_required": "Use delegate_to_police tool for police response" if is_fight else None
    }


@function_tool(name="detect_crowd_rush", description="Runs crowd analysis algorithm to detect dangerous crowd surges or stampede conditions.")
async def detect_crowd_rush(location: str) -> Dict[str, Any]:
    """Detects crowd rush/stampede conditions at a location."""
    cid = get_cid()
    logger.info(f"CROWD RUSH DETECTION: Scanning {location}", extra={"correlation_id": cid})
    await asyncio.sleep(0.5)
    
    density = random.randint(50, 200)  # People per area unit
    is_dangerous = density > 120
    
    return {
        "location": location,
        "crowd_density": density,
        "dangerous_conditions": is_dangerous,
        "risk_level": "CRITICAL" if density > 180 else "HIGH" if density > 150 else "MEDIUM" if density > 120 else "LOW",
        "action_required": "Use delegate_to_police tool for crowd control" if is_dangerous else None
    }


@function_tool(name="broadcast_hazard", description="Broadcasts a confirmed visual hazard to all relevant commanders.")
async def broadcast_hazard(hazard_type: str, location: str) -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"BROADCASTING HAZARD: {hazard_type} at {location}", extra={"correlation_id": cid})
    try:
        # Broadcast to Fire, Police, and Dispatch
        targets = ["fire-chief-agent", "police-chief-agent", "dispatch-agent"]
        await global_client.broadcast(
            source_agent="camera-agent",
            agents=targets,
            message_text=f"VISUAL ALERT: {hazard_type} confirmed at {location}."
        )
        return {"status": "broadcast_sent", "targets": targets}
    except Exception as e:
        logger.error(f"Broadcast failed: {e}")
        return {"status": "failed", "error": str(e)}


@function_tool(name="confirm_task", description="Confirms receipt and execution of a priority task.")
async def confirm_task(status: str = "completed", message: str = "Task executed.", target_agent: str = "dispatch-agent") -> Dict[str, Any]:
    cid = get_cid()
    logger.info(f"CONFIRMING: {status} to {target_agent}", extra={"correlation_id": cid})
    try:
        import json
        payload = json.dumps({"type": "HANDSHAKE_RESULT", "correlation_id": cid, "status": status, "message": message})
        await global_client.send_message(source_agent="camera-agent", target_agent=target_agent, message_text=payload, correlation_id=cid)
        return {"status": "sent", "target": target_agent}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# =============================================================================
# DELEGATION TOOLS (Delegate to Specialist Agents)
# =============================================================================

from lib.tools.delegation_tool import (
    delegate_to_fire_from_camera as delegate_to_fire,
    delegate_to_police_from_camera as delegate_to_police
)