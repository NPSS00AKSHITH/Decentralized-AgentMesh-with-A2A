import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

from .executor import MedicalAgentExecutor
from lib.utils.logging_config import setup_logging
from lib.utils.postgres_task_store import PostgresTaskStore
from lib.utils.middleware import JWTMiddleware

logger = setup_logging("medical-main")

skill_medical = AgentSkill(
    id="handle_medical_incident",
    name="Medical Incident Response",
    description="Coordinate ambulances.",
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    tags=["medical", "ambulance"]
)

card = AgentCard(
    name="medical-agent",
    description="Medical response coordinator.",
    version="1.0.0",
    url=f"http://{os.getenv('SERVICE_HOST', 'medical-agent')}:{os.getenv('PORT', '9005')}/a2a",
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill_medical],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"]
)

handler = DefaultRequestHandler(
    agent_executor=MedicalAgentExecutor(),
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
        service_name="medical-agent",
        port=int(os.getenv("PORT", 9005)),
        tags=["medical", "health", "a2a"]
    )
    try:
        yield
    finally:
        # Shutdown
        await registry.deregister_service("medical-agent")
        await registry.close()

app = FastAPI(title="DDMS Medical Agent", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/a2a", a2a_app)
app.mount("/.well-known", a2a_app)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "role": "medical", "mode": "official-a2a-sdk"}

@app.get("/.well-known/agent.json")
async def agent_card_endpoint():
    """Serve the agent card for A2A discovery."""
    return card.model_dump(by_alias=True, exclude_none=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 9005)))
