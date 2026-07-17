"""Flow A operational-alerts configuration loaded at request time."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

ENV_OPERATIONAL_ALERTS_ENABLED = "SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED"
ENV_OPERATIONAL_ALERTS_WEBHOOK_URL = "SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_WEBHOOK_URL"


@dataclass(frozen=True)
class FlowAOperationalAlertsSettings:
    enabled: bool
    webhook_url: str

    @property
    def has_webhook_url(self) -> bool:
        return bool(self.webhook_url.strip())

    @property
    def webhook_configured(self) -> bool:
        return self.has_webhook_url and _is_valid_webhook_url(self.webhook_url)

    @property
    def emission_ready(self) -> bool:
        return self.enabled and self.webhook_configured


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _is_valid_webhook_url(raw: str) -> bool:
    """Accept only absolute http(s) URLs with a network location."""
    try:
        parsed = urlparse(raw.strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    if not parsed.netloc:
        return False
    return True


def load_flow_a_operational_alerts_settings(
    environ: dict[str, str] | None = None,
) -> FlowAOperationalAlertsSettings:
    """Load operational-alerts settings; fail closed when unset."""
    env = os.environ if environ is None else environ
    enabled = _parse_bool(env.get(ENV_OPERATIONAL_ALERTS_ENABLED, ""))
    webhook_url = env.get(ENV_OPERATIONAL_ALERTS_WEBHOOK_URL, "").strip()
    return FlowAOperationalAlertsSettings(
        enabled=enabled,
        webhook_url=webhook_url,
    )
