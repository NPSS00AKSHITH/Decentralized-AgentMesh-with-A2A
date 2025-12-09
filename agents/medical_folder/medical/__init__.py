import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from .medical_agent import medical_agent as root_agent
from .medical_agent import agent
