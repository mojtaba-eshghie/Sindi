import os
from contextlib import contextmanager

def _truthy(envvar: str) -> bool:
    val = os.environ.get(envvar, "")
    return val.strip().lower() in ("1", "true", "yes", "on")

# --- default: QUIET ---
# We are silent unless explicitly enabled via SINDI_DEBUG.
# SINDI_QUIET (if set truthy) always forces silence.
_QUIET = True
if _truthy("SINDI_DEBUG"):
    _QUIET = False
if _truthy("SINDI_QUIET"):
    _QUIET = True  # wins over SINDI_DEBUG if both are set

def set_quiet(enabled: bool) -> None:
    """Force quiet mode on/off programmatically."""
    global _QUIET
    _QUIET = bool(enabled)

def set_debug(enabled: bool) -> None:
    """Convenience wrapper: enable/disable debug logging."""
    set_quiet(not bool(enabled))

def printer(string, level: int = 0):
    """Print with indentation unless quiet mode is enabled."""
    if _QUIET:
        return
    print("  " * level + str(string))

@contextmanager
def debug_logging(enabled: bool = True):
    """Temporarily toggle debug logging within a 'with' block."""
    global _QUIET
    prev = _QUIET
    _QUIET = not bool(enabled)
    try:
        yield
    finally:
        _QUIET = prev
