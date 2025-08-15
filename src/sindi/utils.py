import os

# If set, disables all debug prints that go through `printer`.
_QUIET = os.environ.get("SINDI_QUIET", "").lower() in ("1", "true", "yes")

def set_quiet(enabled: bool) -> None:
    global _QUIET
    _QUIET = bool(enabled)

def printer(string, level: int = 0):
    """Print with indentation unless quiet mode is enabled."""
    if _QUIET:
        return
    print("  " * level + str(string))
