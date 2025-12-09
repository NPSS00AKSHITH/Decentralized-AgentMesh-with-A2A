import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from google.adk.agents import LlmAgent
from lib.utils.logging_config import setup_logging
from lib.utils.env_utils import ensure_env_vars
from .prompt import FIRE_CHIEF_INSTRUCTIONS
from . import tools

logger = setup_logging("fire-chief-brain")
ensure_env_vars(["GEMINI_API_KEY", "GEMINI_MODEL"], logger=logger)

FIRE_AGENT_NAME = os.getenv("SERVICE_NAME", "fire_agent")

def create_fire_chief_agent(name: str = FIRE_AGENT_NAME) -> LlmAgent:
    return LlmAgent(
        name=name,
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        description="Fire chief agent: handles fire emergencies and delegates to medical/utility/police specialists.",
        instruction=FIRE_CHIEF_INSTRUCTIONS,
        tools=[
            # Domain tools (Fire Chief's specialty)
            tools.fire_map_lookup,
            tools.deploy_units,
            tools.estimate_fire_severity,
            tools.trigger_civic_alert,
            tools.confirm_incident,
            # Delegation tools (delegate to specialists)
            tools.delegate_to_medical,
            tools.delegate_to_utility,
            tools.delegate_to_police,
        ]
    )

fire_chief_agent = create_fire_chief_agent()
agent = fire_chief_agent