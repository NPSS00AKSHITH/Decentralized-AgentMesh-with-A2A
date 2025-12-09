import os
import sys

# Standardize path handling
# sys.path.append(...) 

from google.adk.agents import LlmAgent
from lib.utils.logging_config import setup_logging
from lib.utils.env_utils import ensure_env_vars
from .prompt import IOT_SENSOR_AGENT_INSTRUCTIONS
from . import tools

logger = setup_logging("iot-sensor-brain")
ensure_env_vars(["GEMINI_API_KEY", "GEMINI_MODEL"], logger=logger)

def create_iot_sensor_agent(name: str = "iot_sensor_agent") -> LlmAgent:
    return LlmAgent(
        name=name,
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        description="Environmental monitoring agent.",
        instruction=IOT_SENSOR_AGENT_INSTRUCTIONS,
        tools=[
            # Domain tools
            tools.read_sensor_data,
            tools.read_environmental_sensors,
            tools.trigger_alarm,
            tools.confirm_task,
            # Delegation tools
            tools.delegate_to_fire,
            tools.delegate_to_utility
        ]
    )

iot_sensor_agent = create_iot_sensor_agent()
agent = iot_sensor_agent