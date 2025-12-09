import os
import sys

# Standardize path handling
# sys.path.append(...) 

from google.adk.agents import LlmAgent
from lib.utils.logging_config import setup_logging
from lib.utils.env_utils import ensure_env_vars
from .prompt import DISPATCH_AGENT_INSTRUCTIONS
from . import tools

logger = setup_logging("dispatch-brain")
ensure_env_vars(["GEMINI_API_KEY", "GEMINI_MODEL"], logger=logger)

def create_dispatch_agent(name: str = "dispatch_agent") -> LlmAgent:
    return LlmAgent(
        name=name,
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        description="Incident router and classifier.",
        instruction=DISPATCH_AGENT_INSTRUCTIONS,
        tools=[
            # Domain tools
            tools.assign_incident_commander,
            tools.confirm_receipt,
            # Delegation tools
            tools.delegate_to_fire,
            tools.delegate_to_medical,
            tools.delegate_to_police,
            tools.delegate_to_utility
        ]
    )

dispatch_agent = create_dispatch_agent()
agent = dispatch_agent