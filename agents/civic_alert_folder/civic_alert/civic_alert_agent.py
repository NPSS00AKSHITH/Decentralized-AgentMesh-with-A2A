import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from google.adk.agents import LlmAgent
from lib.utils.logging_config import setup_logging
from lib.utils.env_utils import ensure_env_vars
from .prompt import CIVIC_ALERT_INSTRUCTIONS
from . import tools

logger = setup_logging("civic-alert-brain")
ensure_env_vars(["GEMINI_API_KEY", "GEMINI_MODEL"], logger=logger)

def create_civic_alert_agent(name: str = "civic_alert_agent") -> LlmAgent:
    return LlmAgent(
        name=name,
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        description="Public notification specialist.",
        instruction=CIVIC_ALERT_INSTRUCTIONS,
        tools=[
            tools.broadcast_alert,
            tools.activate_sirens,
            tools.confirm_task  # Task confirmation for dispatcher
        ]
    )

civic_alert_agent = create_civic_alert_agent()
agent = civic_alert_agent