import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from google.adk.agents import LlmAgent
from lib.utils.logging_config import setup_logging
from lib.utils.env_utils import ensure_env_vars
from .prompt import POLICE_CHIEF_INSTRUCTIONS
from . import tools

logger = setup_logging("police-chief-brain")
ensure_env_vars(["GEMINI_API_KEY", "GEMINI_MODEL"], logger=logger)

def create_police_chief_agent(name: str = "police_chief_agent") -> LlmAgent:
    return LlmAgent(
        name=name,
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        description="Law enforcement commander with emergency broadcast capability.",
        instruction=POLICE_CHIEF_INSTRUCTIONS,
        tools=[
            # Domain tools
            tools.deploy_swat,
            tools.cordon_area,
            tools.broadcast_via_pa_system,
            tools.trigger_civic_alert,
            tools.emergency_public_broadcast,  # Civic Alert failover
            tools.confirm_support_request,
            # Delegation tools
            tools.delegate_to_fire,
            tools.delegate_to_medical,
            tools.delegate_to_utility
        ]
    )

police_chief_agent = create_police_chief_agent()
agent = police_chief_agent

