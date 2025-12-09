import httpx
import logging
from typing import Optional, Tuple

logger = logging.getLogger("lib.map_tools")
logger.setLevel(logging.INFO)

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "ddms-agent/1.0 (dev@localhost)"

async def _get_json(url: str, params: dict, timeout: float = 6.0) -> Optional[dict]:
    headers = {"User-Agent": USER_AGENT}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(url, params=params, headers=headers)
            r.raise_for_status()
            return r.json()
    except Exception as e:
        logger.exception("Nominatim call failed: %s", e)
        return None

async def geocode(address: str) -> Optional[Tuple[float, float]]:
    if not address:
        return None
    url = f"{NOMINATIM_BASE}/search"
    params = {"q": address, "format": "json", "limit": 1}
    data = await _get_json(url, params)
    if not data:
        return None
    try:
        lat = float(data[0]["lat"])
        lon = float(data[0]["lon"])
        logger.info("Geocoded %s -> (%s,%s)", address, lat, lon)
        return lat, lon
    except Exception:
        return None

async def reverse_geocode(lat: float, lon: float) -> Optional[dict]:
    url = f"{NOMINATIM_BASE}/reverse"
    params = {"lat": lat, "lon": lon, "format": "json"}
    data = await _get_json(url, params)
    if not data:
        return None
    return {"display_name": data.get("display_name"), "address": data.get("address")}
