import os
import logging
from typing import Iterable, Dict, Mapping

def ensure_env_vars(
    required_vars: Iterable[str],
    defaults: Mapping[str, str] | None = None,
    logger: logging.Logger | None = None,
) -> Dict[str, str]:
    """
    Validates that required environment variables are set.
    Raises RuntimeError if critical variables are missing.
    """
    defaults = defaults or {}
    resolved: Dict[str, str] = {}
    missing: list[str] = []

    for var in required_vars:
        value = os.getenv(var)
        if value:
            resolved[var] = value
            continue

        if var in defaults:
            value = defaults[var]
            os.environ.setdefault(var, value)
            resolved[var] = value
            if logger:
                logger.warning(f"Env var {var} missing; using default: {value}")
        else:
            missing.append(var)

    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")

    return resolved