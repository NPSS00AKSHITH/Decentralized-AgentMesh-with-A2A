import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from google.adk.agents import LlmAgent
# FIX: Import from 'lib'
from lib.utils.logging_config import setup_logging
from lib.utils.env_utils import ensure_env_vars
from .prompt import CAMERA_AGENT_INSTRUCTIONS
from . import tools

logger = setup_logging("camera-brain")
ensure_env_vars(["GEMINI_API_KEY", "GEMINI_MODEL"], logger=logger)

def create_camera_agent(name: str = "camera_agent") -> LlmAgent:
    return LlmAgent(
        name=name,
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        description="Optical perception agent for surveillance and detection.",
        instruction=CAMERA_AGENT_INSTRUCTIONS,
        tools=[
            tools.analyze_feed,
            tools.detect_fire,
            tools.detect_fight,
            tools.detect_crowd_rush,
            tools.broadcast_hazard,
            tools.confirm_task,
            tools.delegate_to_fire,
            tools.delegate_to_police
        ]
    )

camera_agent = create_camera_agent()
agent = camera_agent