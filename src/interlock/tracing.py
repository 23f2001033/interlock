"""neatlogs setup. Every Interlock run is traced; call init_tracing() once per process."""

import atexit
import os

import neatlogs
from dotenv import load_dotenv

_initialized = False


def init_tracing(workflow_name: str = "interlock", tags: list[str] | None = None) -> bool:
    """Initialise neatlogs. Returns False (spans still created, not exported) if no key is set."""
    global _initialized
    if _initialized:
        return True
    load_dotenv()
    api_key = os.environ.get("NEATLOGS_API_KEY") or os.environ.get("NEATLOG_API_KEY")
    neatlogs.init(
        api_key=api_key,
        workflow_name=workflow_name,
        instrumentations=["openai"],
        tags=tags or [],
    )
    atexit.register(shutdown_tracing)
    _initialized = True
    return api_key is not None


def shutdown_tracing() -> None:
    try:
        neatlogs.flush()
        neatlogs.shutdown()
    except Exception:
        pass
