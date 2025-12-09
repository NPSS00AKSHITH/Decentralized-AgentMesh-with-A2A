import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from .fire_chief_agent import fire_chief_agent as root_agent
from .fire_chief_agent import agent
