"""
Pushover Push Notification Utility
===================================
Sends real push notifications to mobile devices via Pushover API.
Simulates actual dispatch messages to Fire Stations, Hospitals, and Utility Control.
"""
import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger("pushover")

# Pushover API endpoint
PUSHOVER_API_URL = "https://api.pushover.net/1/messages.json"


def _get_credentials():
    """Get Pushover credentials at runtime (after dotenv has loaded)."""
    return (
        os.getenv("PUSHOVER_API_KEY", ""),
        os.getenv("PUSHOVER_USER_KEY", "")
    )


async def send_pushover(
    title: str,
    message: str,
    priority: int = 1,
    sound: str = "siren",
    url: Optional[str] = None,
    url_title: Optional[str] = None
) -> dict:
    """
    Send a push notification via Pushover API.
    
    Args:
        title: Notification title
        message: Notification body with details
        priority: -2 (lowest) to 2 (emergency). 1 = high priority
        sound: Notification sound (siren, cosmic, gamelan, etc.)
        url: Optional URL to include
        url_title: Title for the URL
        
    Returns:
        dict with status and details
    """
    # Get credentials at runtime (not import time)
    api_key, user_key = _get_credentials()
    
    if not api_key or not user_key:
        logger.warning("Pushover credentials not configured. Skipping notification.")
        return {"status": "skipped", "reason": "No Pushover credentials"}
    
    payload = {
        "token": api_key,
        "user": user_key,
        "title": title,
        "message": message,
        "priority": priority,
        "sound": sound,
    }
    
    if url:
        payload["url"] = url
    if url_title:
        payload["url_title"] = url_title
    
    # For emergency priority (2), require acknowledgment
    if priority == 2:
        payload["retry"] = 60
        payload["expire"] = 3600
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(PUSHOVER_API_URL, data=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Pushover sent: {title}")
                return {"status": "sent", "title": title}
            else:
                logger.error(f"Pushover error: {response.status_code} - {response.text}")
                return {"status": "failed", "error": response.text}
    except Exception as e:
        logger.error(f"Pushover failed: {e}")
        return {"status": "error", "error": str(e)}


# =============================================================================
# DISPATCH MESSAGES - Simulating actual station dispatch
# =============================================================================

async def notify_fire_station(location: str, units: int, unit_type: str, eta_minutes: int = 12) -> dict:
    """Send dispatch command to fire station."""
    return await send_pushover(
        title="🔥 FIRE STATION DISPATCH",
        message=(
            f"DEPLOY {units} {unit_type.upper()}(S) TO:\n"
            f"📍 {location}\n\n"
            f"⏱️ Respond immediately\n"
            f"📞 DDMS Fire Chief Agent"
        ),
        priority=1,
        sound="siren"
    )


async def notify_hospital(location: str, ambulances: int, eta_minutes: int = 8) -> dict:
    """Send dispatch command to hospital/ambulance station."""
    return await send_pushover(
        title="🏥 HOSPITAL DISPATCH",
        message=(
            f"DISPATCH {ambulances} AMBULANCE(S) TO:\n"
            f"📍 {location}\n\n"
            f"🚨 Casualties reported - respond immediately\n"
            f"📞 DDMS Medical Agent"
        ),
        priority=1,
        sound="cosmic"
    )


async def notify_utility_control(action: str, region: str, details: str) -> dict:
    """Send command to utility control station (power/gas)."""
    return await send_pushover(
        title="⚡ UTILITY CONTROL COMMAND",
        message=(
            f"ACTION REQUIRED: {action}\n"
            f"📍 {region}\n\n"
            f"{details}\n"
            f"📞 DDMS Utility Agent"
        ),
        priority=1,
        sound="mechanical"
    )


async def notify_police_dispatch(location: str, unit_type: str, threat_level: str) -> dict:
    """Send dispatch command to police units."""
    return await send_pushover(
        title="🚔 POLICE DISPATCH",
        message=(
            f"DEPLOY {unit_type.upper()} TO:\n"
            f"📍 {location}\n\n"
            f"⚠️ Threat Level: {threat_level}\n"
            f"📞 DDMS Police Chief Agent"
        ),
        priority=1,
        sound="pushover"
    )


async def notify_public_alert(message: str, zone: str, severity: str) -> dict:
    """Send public civic alert notification."""
    return await send_pushover(
        title="📢 CIVIC ALERT BROADCAST",
        message=(
            f"PUBLIC ALERT: {message}\n"
            f"📍 Zone: {zone}\n"
            f"⚠️ Severity: {severity}\n\n"
            f"📞 DDMS Civic Alert Agent"
        ),
        priority=1 if severity.lower() != "critical" else 2,
        sound="echo"
    )


async def notify_sensor_alert(zone: str, sensor_type: str, status: str) -> dict:
    """Send critical sensor alert notification."""
    return await send_pushover(
        title="🔴 SENSOR ALERT",
        message=(
            f"CRITICAL READING DETECTED\n"
            f"📍 Zone: {zone}\n"
            f"📊 Sensor: {sensor_type}\n"
            f"⚠️ Status: {status}\n\n"
            f"📞 DDMS IoT Sensor Agent"
        ),
        priority=1,
        sound="alien"
    )


async def notify_emergency_report(incident_type: str, location: str, source: str) -> dict:
    """Send emergency report intake notification."""
    return await send_pushover(
        title="📞 EMERGENCY REPORT",
        message=(
            f"NEW INCIDENT REPORTED\n"
            f"🆘 Type: {incident_type}\n"
            f"📍 Location: {location}\n"
            f"📱 Source: {source}\n\n"
            f"📞 DDMS Human Intake Agent"
        ),
        priority=1,
        sound="bike"
    )


async def notify_pa_broadcast(message: str, location: str, source_agent: str = "police-chief-agent") -> dict:
    """Send emergency PA broadcast notification (Police Chief Civic Alert failover)."""
    return await send_pushover(
        title="🚨 EMERGENCY PA BROADCAST",
        message=(
            f"PUBLIC ANNOUNCEMENT ACTIVE\n"
            f"📢 Message: {message}\n"
            f"📍 Location: {location}\n\n"
            f"⚠️ Civic Alert Failover - Using Police PA System\n"
            f"📞 {source_agent.replace('-', ' ').title()}"
        ),
        priority=2,  # Emergency priority for PA broadcasts
        sound="siren"
    )
