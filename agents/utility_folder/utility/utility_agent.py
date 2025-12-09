import os
import sys

from google.adk.agents import LlmAgent
from lib.utils.logging_config import setup_logging
from lib.utils.env_utils import ensure_env_vars
from .prompt import UTILITY_AGENT_INSTRUCTIONS
from . import tools

logger = setup_logging("utility-brain")
ensure_env_vars(["GEMINI_API_KEY", "GEMINI_MODEL"], logger=logger)

def create_utility_agent(name: str = "utility_agent") -> LlmAgent:
    return LlmAgent(
        name=name,
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        description="Utility Agent: manages infrastructure and delegates to Fire/Medical/Civic Alert/Police for emergencies.",
        instruction=UTILITY_AGENT_INSTRUCTIONS,
        tools=[
            # Domain tools (Utility specialty)
            tools.shutdown_power_grid,
            tools.cut_gas_supply,
            tools.restore_water_pressure,
            tools.evaluate_infrastructure_risk,
            tools.confirm_task,
            # Delegation tools (delegate to specialists)
            tools.delegate_to_fire_chief,
            tools.delegate_to_medical,
            tools.delegate_to_civic_alert,
            tools.delegate_to_police,
        ]
    )

utility_agent = create_utility_agent()
agent = utility_agent