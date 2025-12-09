import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from .camera_agent import camera_agent as root_agent
from .camera_agent import agent
