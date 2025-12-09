import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

from .executor import PoliceChiefExecutor
from lib.utils.logging_config import setup_logging
from lib.utils.postgres_task_store import PostgresTaskStore
from lib.utils.middleware import JWTMiddleware

logger = setup_logging("police-chief-main")

skill_police = AgentSkill(
    id="manage_crowd_control",
    name="Crowd Control & Security",
    description="Manage riots and security.",
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    tags=["security", "police"]
)

card = AgentCard(
    name="police-chief-agent",
    description="Law enforcement commander.",
    version="1.0.0",
    url=f"http://{os.getenv('SERVICE_HOST', 'police-chief-agent')}:{os.getenv('PORT', '9006')}/a2a",
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill_police],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"]
)

handler = DefaultRequestHandler(
    agent_executor=PoliceChiefExecutor(),
    task_store=PostgresTaskStore(dsn=os.getenv("DATABASE_URL"))
)

a2a_app = A2AStarletteApplication(agent_card=card, http_handler=handler).build()
a2a_app.add_middleware(JWTMiddleware, expected_audience=card.name)

from contextlib import asynccontextmanager
from lib.consul.registry import ConsulRegistry

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing Service...")
    try:
        await handler.task_store.connect()
        logger.info("Task Store connected.")
    except Exception as e:
        logger.error(f"Failed to connect to Task Store: {e}")

    registry = ConsulRegistry()
    await registry.register_service(
        service_name="police-chief-agent",
        port=int(os.getenv("PORT", 9006)),
        tags=["police", "security", "a2a"]
    )
    try:
        yield
    finally:
        # Shutdown
        await registry.deregister_service("police-chief-agent")
        await registry.close()
        
        if handler.task_store.pool:
            await handler.task_store.pool.close()

app = FastAPI(title="DDMS Police Chief Agent", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.mount("/a2a", a2a_app)
app.mount("/.well-known", a2a_app)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "role": "police_chief", "mode": "official-a2a-sdk"}

@app.get("/.well-known/agent.json")
async def agent_card_endpoint():
    """Serve the agent card for A2A discovery."""
    return card.model_dump(by_alias=True, exclude_none=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 9006)))
