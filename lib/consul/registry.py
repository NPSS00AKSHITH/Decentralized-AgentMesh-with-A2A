import os
import socket
import logging
import httpx
from typing import Optional, List

logger = logging.getLogger("consul-registry")

class ConsulRegistry:
    def __init__(self):
        self.consul_host = os.getenv("CONSUL_HOST", "localhost")
        self.consul_port = int(os.getenv("CONSUL_PORT", "8500"))
        self.base_url = f"http://{self.consul_host}:{self.consul_port}"
        
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=2.0)
        self._cache = {}
        
        # Hardcoded map of Service Name -> Hostname : Port
        # Using localhost for local development with ADK web UI
        # ADK web servers run on 800x ports, A2A servers run on 900x ports
        self.static_mesh_map = {
            "human-intake-agent": ("localhost", 9001),
            "dispatch-agent": ("localhost", 9002),
            "fire-chief-agent": ("localhost", 9003),
            "civic-alert-agent": ("localhost", 9004),
            "medical-agent": ("localhost", 9005),
            "police-chief-agent": ("localhost", 9006),
            "utility-agent": ("localhost", 9007),
            "iot-sensor-agent": ("localhost", 9008),
            "camera-agent": ("localhost", 9009)
        }

    async def get_service_url(self, service_name: str) -> Optional[str]:
        # 1. Cache Check
        if service_name in self._cache:
            return self._cache[service_name]

        url = None
        
        # 2. Try Consul (skip if running locally without Consul)
        try:
            resp = await self.client.get(f"/v1/catalog/service/{service_name}")
            if resp.status_code == 200:
                services = resp.json()
                if services:
                    svc = services[0]
                    address = svc.get("ServiceAddress") or svc.get("Address")
                    port = svc.get("ServicePort")
                    url = f"http://{address}:{port}"
        except Exception:
            pass

        # 3. Localhost Fallback for local development
        if not url and service_name in self.static_mesh_map:
            host, port = self.static_mesh_map[service_name]
            url = f"http://{host}:{port}"
            logger.debug(f"Using localhost fallback for {service_name}: {url}")

        if url:
            self._cache[service_name] = url
            return url
            
        return None

    def invalidate_cache(self, service_name: str):
        if service_name in self._cache:
            del self._cache[service_name]

    async def register_service(self, service_name: str, port: int, tags: List[str] = None):
        """Register service with Consul (optional for local development)."""
        hostname = socket.gethostname()
        
        # Use localhost for local development
        address = "localhost"
        
        payload = {
            "ID": f"{service_name}-{hostname}",
            "Name": service_name,
            "Tags": tags or [],
            "Address": address, 
            "Port": port,
            "Check": {
                "HTTP": f"http://{address}:{port}/health",
                "Interval": "10s",
                "Timeout": "5s",
                "DeregisterCriticalServiceAfter": "1m"
            }
        }
        try:
            await self.client.put("/v1/agent/service/register", json=payload)
            logger.info(f"Registered {service_name} at {address}:{port}")
        except Exception as e:
            # Consul may not be running locally - this is fine
            logger.debug(f"Consul not available, using static routing: {e}")

    async def deregister_service(self, service_name: str):
        try:
            hostname = socket.gethostname()
            service_id = f"{service_name}-{hostname}"
            await self.client.put(f"/v1/agent/service/deregister/{service_id}")
        except Exception:
            pass

    async def close(self):
        await self.client.aclose()