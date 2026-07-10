"""Flow A operational queue configuration."""

from __future__ import annotations

import os

ENV_FLOW_A_PROCESSING_STALE_SECONDS = "SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS"
DEFAULT_FLOW_A_PROCESSING_STALE_SECONDS = 3600
MIN_FLOW_A_PROCESSING_STALE_SECONDS = 60
FLOW_A_PROCESSING_STALE_SECONDS_INVALID = "flow_a_processing_stale_seconds_invalid"


class FlowAConfigurationError(ValueError):
    """Raised when Flow A configuration is missing or invalid."""

    def __init__(self, message: str, *, error_code: str) -> None:
        super().__init__(message)
        self.error_code = error_code


def load_flow_a_processing_stale_seconds(
    environ: dict[str, str] | None = None,
) -> int:
    """Load and validate SILVERMAN_FLOW_A_PROCESSING_STALE_SECONDS."""
    env = os.environ if environ is None else environ
    raw = env.get(
        ENV_FLOW_A_PROCESSING_STALE_SECONDS,
        str(DEFAULT_FLOW_A_PROCESSING_STALE_SECONDS),
    ).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise FlowAConfigurationError(
            f"{ENV_FLOW_A_PROCESSING_STALE_SECONDS} must be a positive integer, got {raw!r}",
            error_code=FLOW_A_PROCESSING_STALE_SECONDS_INVALID,
        ) from exc

    if value < MIN_FLOW_A_PROCESSING_STALE_SECONDS:
        raise FlowAConfigurationError(
            f"{ENV_FLOW_A_PROCESSING_STALE_SECONDS} must be at least "
            f"{MIN_FLOW_A_PROCESSING_STALE_SECONDS}, got {value}",
            error_code=FLOW_A_PROCESSING_STALE_SECONDS_INVALID,
        )

    return value
