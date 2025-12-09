import os
import sys

from google.adk.agents import LlmAgent
from lib.utils.logging_config import setup_logging
from lib.utils.env_utils import ensure_env_vars
from .prompt import MEDICAL_AGENT_INSTRUCTIONS
from . import tools

logger = setup_logging("medical-brain")
ensure_env_vars(["GEMINI_API_KEY", "GEMINI_MODEL"], logger=logger)

def create_medical_agent(name: str = "medical_agent") -> LlmAgent:
    return LlmAgent(
        name=name,
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        description="Medical Agent: handles casualties, ambulance dispatch, and delegates to Fire/Utility/Police for other emergencies.",
        instruction=MEDICAL_AGENT_INSTRUCTIONS,
        tools=[
            # Domain tools (Medical specialty)
            tools.dispatch_ambulances,
            tools.triage_casualties,
            tools.prepare_medical_response,
            tools.confirm_support_request,
            tools.trigger_civic_alert,
            # Delegation tools (delegate to specialists)
            tools.delegate_to_fire_chief,
            tools.delegate_to_utility,
            tools.delegate_to_police,
        ]
    )

medical_agent = create_medical_agent()
agent = medical_agent