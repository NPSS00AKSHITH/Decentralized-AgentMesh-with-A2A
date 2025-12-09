import logging
import httpx
import random
from typing import Dict, Any, List, Optional

logger = logging.getLogger("adk-real-maps-tool")

class RealMapsTool:
    """
    Real implementation of ADK Maps Tool using OpenStreetMap (OSM) services.
    - Geocoding: Nominatim
    - Routing: OSRM
    - Places: Overpass API (simulated via local heuristics for reliability)
    """
    
    def __init__(self):
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        self.osrm_url = "http://router.project-osrm.org/route/v1/driving"
        self.headers = {"User-Agent": "ADK-Disaster-Management-System/1.0"}
        
        # Cache to prevent rate limiting and improve speed
        self._cache = {}
        
        # Fallback hardcoded locations for demo reliability if API fails
        self._fallback_locations = {
            "maddilapalem": {"lat": 17.729, "lng": 83.317, "display_name": "Maddilapalem, Visakhapatnam"},
            "gajuwaka": {"lat": 17.690, "lng": 83.210, "display_name": "Gajuwaka, Visakhapatnam"},
            "mvp colony": {"lat": 17.740, "lng": 83.330, "display_name": "MVP Colony, Visakhapatnam"},
            "jagadamba": {"lat": 17.710, "lng": 83.300, "display_name": "Jagadamba Centre, Visakhapatnam"},
            "rushikonda": {"lat": 17.780, "lng": 83.380, "display_name": "Rushikonda, Visakhapatnam"},
            "fire station hq": {"lat": 17.730, "lng": 83.318, "display_name": "Fire Station HQ, Visakhapatnam"},
            "general hospital": {"lat": 17.742, "lng": 83.332, "display_name": "General Hospital, Visakhapatnam"},
        }

    async def lookup_location(self, query: str) -> Dict[str, Any]:
        """
        Geocodes a location name to coordinates.
        """
        query_key = query.lower().strip()
        
        # 1. Check Cache
        if query_key in self._cache:
            return self._cache[query_key]
            
        # 2. Check Fallbacks (Fast Path)
        if query_key in self._fallback_locations:
            logger.info(f"Maps Lookup (Fallback Hit): {query}")
            result = {
                "name": query,
                **self._fallback_locations[query_key],
                "status": "found",
                "source": "internal_db"
            }
            self._cache[query_key] = result
            return result

        # 3. Call Nominatim API
        logger.info(f"Maps Lookup (API): {query}")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    self.nominatim_url, 
                    params={"q": query, "format": "json", "limit": 1},
                    headers=self.headers,
                    timeout=5.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data:
                        loc = data[0]
                        result = {
                            "name": query,
                            "lat": float(loc["lat"]),
                            "lng": float(loc["lon"]),
                            "display_name": loc["display_name"],
                            "status": "found",
                            "source": "osm_nominatim"
                        }
                        self._cache[query_key] = result
                        return result
        except Exception as e:
            logger.error(f"Nominatim API failed: {e}")

        # 4. Not Found / Error
        return {"name": query, "status": "not_found", "error": "Location could not be resolved"}

    async def get_route(self, origin: str, destination: str) -> Dict[str, Any]:
        """
        Calculates route between two locations.
        """
        # Resolve both locations first
        origin_data = await self.lookup_location(origin)
        dest_data = await self.lookup_location(destination)
        
        if origin_data.get("status") != "found" or dest_data.get("status") != "found":
            return {"error": "Could not resolve origin or destination"}
            
        coords = f"{origin_data['lng']},{origin_data['lat']};{dest_data['lng']},{dest_data['lat']}"
        
        logger.info(f"Calculating Route (OSRM): {origin} -> {destination}")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.osrm_url}/{coords}",
                    params={"overview": "false"},
                    timeout=5.0
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == "Ok" and data.get("routes"):
                        route = data["routes"][0]
                        duration_mins = int(route["duration"] / 60)
                        distance_km = round(route["distance"] / 1000, 1)
                        
                        return {
                            "origin": origin,
                            "destination": destination,
                            "distance_km": distance_km,
                            "duration_mins": duration_mins,
                            "traffic_condition": "Live (OSRM)",
                            "source": "osrm"
                        }
        except Exception as e:
            logger.error(f"OSRM API failed: {e}")
            
        # Fallback: Haversine-like estimation
        return self._estimate_route_fallback(origin, destination, origin_data, dest_data)

    def _estimate_route_fallback(self, origin, destination, origin_data, dest_data):
        # Simple Euclidean distance approximation for fallback
        lat1, lon1 = origin_data['lat'], origin_data['lng']
        lat2, lon2 = dest_data['lat'], dest_data['lng']
        
        # Rough conversion: 1 deg lat ~ 111km
        d_lat = (lat2 - lat1) * 111
        d_lon = (lon2 - lon1) * 111 * 0.9 # approx for this latitude
        
        dist_km = (d_lat**2 + d_lon**2)**0.5
        duration_mins = int((dist_km / 40) * 60) # assume 40km/h avg speed
        
        logger.warning(f"Using Fallback Route Estimation for {origin} -> {destination}")
        
        return {
            "origin": origin,
            "destination": destination,
            "distance_km": round(dist_km, 1),
            "duration_mins": duration_mins,
            "traffic_condition": "Estimated (Fallback)",
            "source": "fallback_estimation"
        }

    async def find_nearest_resource(self, resource_type: str, location: str) -> Dict[str, Any]:
        """
        Finds nearest resource. 
        For this demo, we use a predefined list of resources but calculate real distances.
        """
        loc_data = await self.lookup_location(location)
        if loc_data.get("status") != "found":
            return {"error": f"Could not resolve location {location}"}
            
        # Predefined resources (simulating a database)
        resources_db = {
            "fire_station": ["Fire Station HQ", "Gajuwaka Fire Station"],
            "hospital": ["General Hospital", "Apollo Hospital Ramnagar"],
            "utility_hub": ["Maddilapalem Substation", "Gajuwaka Power Grid"]
        }
        
        candidates = resources_db.get(resource_type, [])
        if not candidates:
            return {"error": f"No resources of type {resource_type} known"}
            
        best_resource = None
        min_duration = float('inf')
        
        for resource_name in candidates:
            route = await self.get_route(location, resource_name)
            if route and "duration_mins" in route:
                if route["duration_mins"] < min_duration:
                    min_duration = route["duration_mins"]
                    best_resource = {
                        "resource_type": resource_type,
                        "nearest_unit": {"id": resource_name, "location": resource_name},
                        "distance_km": route["distance_km"],
                        "eta_mins": route["duration_mins"]
                    }
                    
        if best_resource:
            return best_resource
        return {"error": "Could not calculate routes to resources"}

# Singleton
real_maps_tool = RealMapsTool()
