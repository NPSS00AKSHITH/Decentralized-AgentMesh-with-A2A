# File: agents/human_intake_folder/human_intake/main.py

import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.types import AgentCard, AgentSkill, AgentCapabilities

from .executor import HumanIntakeAgentExecutor
from lib.utils.postgres_task_store import PostgresTaskStore
from lib.utils.middleware import JWTMiddleware
from lib.utils.logging_config import setup_logging
from lib.consul.registry import ConsulRegistry

logger = setup_logging("human-intake-main")

# 1. Define Identity & Skills
skill_intake = AgentSkill(
    id="emergency_intake",
    name="Emergency Intake",
    description="Process emergency calls and route to dispatch.",
    input_modes=["text/plain"],
    output_modes=["text/plain"],
    tags=["intake", "911", "emergency"]
)

card = AgentCard(
    name="human-intake-agent",
    description="Human Intake agent for the DDMS mesh.",
    version="1.0.0",
    url=f"http://{os.getenv('SERVICE_HOST', 'human-intake-agent')}:{os.getenv('PORT', '9001')}/a2a",
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill_intake],
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"]
)

# 2. Wire the Executor
handler = DefaultRequestHandler(
    agent_executor=HumanIntakeAgentExecutor(),
    task_store=PostgresTaskStore(dsn=os.getenv("DATABASE_URL"))
)

# 3. Create the A2A App
a2a_app = A2AStarletteApplication(
    agent_card=card,
    http_handler=handler
).build()

a2a_app.add_middleware(JWTMiddleware, expected_audience=card.name)

# 4. Define Lifecycle (Startup/Shutdown Logic)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Phase
    logger.info("Initializing Service...")
    
    # [FIX] Connect to Database Task Store
    try:
        await handler.task_store.connect()
        logger.info("Task Store connected successfully.")
    except Exception as e:
        logger.error(f"CRITICAL: Failed to connect to Task Store: {e}")

    # Register with Consul
    registry = ConsulRegistry()
    await registry.register_service(
        service_name="human-intake-agent",
        port=int(os.getenv("PORT", 9001)),
        tags=["intake", "911", "emergency", "a2a"]
    )
    
    try:
        yield
    finally:
        # Shutdown Phase
        logger.info("Shutting down service...")
        await registry.deregister_service("human-intake-agent")
        await registry.close()
        
        # [FIX] Close Database Pool
        if handler.task_store.pool:
            await handler.task_store.pool.close()
            logger.info("Task Store connection closed.")

# 5. Mount to FastAPI
app = FastAPI(title="DDMS Human Intake Agent", lifespan=lifespan)

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
    # Improved health check to report DB status
    db_status = "connected" if handler.task_store.pool else "disconnected"
    status_code = "active" if db_status == "connected" else "unhealthy"
    
    return {
        "status": status_code, 
        "mode": "official-a2a-sdk", 
        "role": "human_intake",
        "db_connection": db_status
    }

@app.get("/.well-known/agent.json")
async def agent_card_endpoint():
    """Serve the agent card for A2A discovery."""
    return card.model_dump(by_alias=True, exclude_none=True)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 9001)))