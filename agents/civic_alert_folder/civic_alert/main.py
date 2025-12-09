import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

from .executor import CivicAlertExecutor
from lib.utils.logging_config import setup_logging
from lib.utils.postgres_task_store import PostgresTaskStore
from lib.utils.middleware import JWTMiddleware

logger = setup_logging("civic-alert-main")

skill_broadcast = AgentSkill(
    id="broadcast_alert",
    name="Public Warning Broadcast",
    description="Disseminate emergency warnings.",
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    tags=["alert", "broadcast"]
)

card = AgentCard(
    name="civic-alert-agent",
    description="Public notification system.",
    version="1.0.0",
    url=f"http://{os.getenv('SERVICE_HOST', 'civic-alert-agent')}:{os.getenv('PORT', '9004')}/a2a",
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill_broadcast],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"]
)

handler = DefaultRequestHandler(
    agent_executor=CivicAlertExecutor(),
    task_store=PostgresTaskStore(dsn=os.getenv("DATABASE_URL"))
)

a2a_app = A2AStarletteApplication(agent_card=card, http_handler=handler).build()
a2a_app.add_middleware(JWTMiddleware, expected_audience=card.name)

from contextlib import asynccontextmanager
from lib.consul.registry import ConsulRegistry

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    registry = ConsulRegistry()
    await registry.register_service(
        service_name="civic-alert-agent",
        port=int(os.getenv("PORT", 9004)),
        tags=["alert", "broadcast", "a2a"]
    )
    yield
    # Shutdown
    await registry.deregister_service("civic-alert-agent")
    await registry.close()

app = FastAPI(title="DDMS Civic Alert Agent", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/a2a", a2a_app)
app.mount("/.well-known", a2a_app)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "role": "civic_alert", "mode": "official-a2a-sdk"}

@app.get("/.well-known/agent.json")
async def agent_card_endpoint():
    """Serve the agent card for A2A discovery."""
    return card.model_dump(by_alias=True, exclude_none=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 9004)))
