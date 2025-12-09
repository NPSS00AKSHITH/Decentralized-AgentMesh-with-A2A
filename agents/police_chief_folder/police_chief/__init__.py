import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from .police_chief_agent import police_chief_agent as root_agent
from .police_chief_agent import agent
