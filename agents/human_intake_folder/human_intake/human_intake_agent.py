import os
import sys

# Standardize path handling
# sys.path.append(...) 

from google.adk.agents import LlmAgent
from lib.utils.logging_config import setup_logging
from lib.utils.env_utils import ensure_env_vars
from .prompt import HUMAN_INTAKE_AGENT_INSTRUCTIONS
from . import tools

logger = setup_logging("human-intake-brain")
ensure_env_vars(["GEMINI_API_KEY", "GEMINI_MODEL"], logger=logger)

def create_human_intake_agent(name: str = "human_intake_agent") -> LlmAgent:
    return LlmAgent(
        name=name,
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        description="Emergency call intake agent.",
        instruction=HUMAN_INTAKE_AGENT_INSTRUCTIONS,
        tools=[
            # Domain tools
            tools.process_report,
            tools.log_and_route_call,
            tools.calm_caller,
            tools.confirm_task,
            # Failover delegation tools (bypass Dispatch if down)
            tools.delegate_to_fire,
            tools.delegate_to_medical,
            tools.delegate_to_police,
            tools.delegate_to_utility
        ]
    )

human_intake_agent = create_human_intake_agent()
agent = human_intake_agent