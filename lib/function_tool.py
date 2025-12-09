import functools
from typing import Callable, Any

class function_tool:
    """
    Decorator to mark a function as a tool for the agent.
    """
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        
        # Attach metadata to the wrapper
        wrapper.tool_name = self.name
        wrapper.tool_description = self.description
        
        # Also attach to the original function just in case
        func.tool_name = self.name
        func.tool_description = self.description
        
        return wrapper
