import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

from .executor import CameraAgentExecutor
from lib.utils.postgres_task_store import PostgresTaskStore
from lib.utils.middleware import JWTMiddleware
from lib.utils.logging_config import setup_logging

logger = setup_logging("camera-main")

# 1. Define Identity & Skills
skill_scan = AgentSkill(
    id="scan_area",
    name="Scan Area",
    description="Analyze camera feeds for hazards like fire or flood.",
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    tags=["perception", "vision", "hazard"]
)

card = AgentCard(
    name="camera-agent",
    description="Optical perception agent for the DDMS mesh.",
    version="1.0.0",
    url=f"http://{os.getenv('SERVICE_HOST', 'camera-agent')}:{os.getenv('PORT', '9009')}/a2a",
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill_scan],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"]
)

# 2. Wire the Executor
handler = DefaultRequestHandler(
    agent_executor=CameraAgentExecutor(),
    task_store=PostgresTaskStore(dsn=os.getenv("DATABASE_URL"))
)

# 3. Create the A2A App
a2a_app = A2AStarletteApplication(
    agent_card=card,
    http_handler=handler
).build()

a2a_app.add_middleware(JWTMiddleware, expected_audience=card.name)

from contextlib import asynccontextmanager
from lib.consul.registry import ConsulRegistry

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    registry = ConsulRegistry()
    await registry.register_service(
        service_name="camera-agent",
        port=int(os.getenv("PORT", 9009)),
        tags=["perception", "vision", "hazard", "a2a"]
    )
    yield
    # Shutdown
    await registry.deregister_service("camera-agent")
    await registry.close()

# 4. Mount to FastAPI
app = FastAPI(title="DDMS Camera Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/a2a", a2a_app)
app.mount("/.well-known", a2a_app)

@app.get("/health")
async def health_check():
    return {"status": "active", "mode": "official-a2a-sdk", "role": "camera"}

@app.get("/.well-known/agent.json")
async def agent_card_endpoint():
    """Serve the agent card for A2A discovery."""
    return card.model_dump(by_alias=True, exclude_none=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 9009)))
