"""Hidden filesystem artifact filtering for editorial scanners."""

from __future__ import annotations

HIDDEN_ARTIFACT_REASON = "hidden_artifact"


def is_hidden_artifact_basename(name: str) -> bool:
    """Return True for macOS junk and direct dotfile children under ready/ or queued/."""
    if name == ".DS_Store":
        return True
    if name.startswith("._"):
        return True
    if name.startswith("."):
        return True
    return False
