"""Provider-pluggable seam for Flow B AI topic discovery (US-078).

v1 ships DeepSeek only. Unsupported providers fail closed. API keys MUST NEVER
appear in results or error payloads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from silverman_blog_linkedin.deepseek_client import generate_linkedin_draft_content
from silverman_blog_linkedin.deepseek_config import DeepSeekSettings

PROVIDER_DEEPSEEK = "deepseek"
DEFAULT_TOPIC_DISCOVERY_PROVIDER = PROVIDER_DEEPSEEK
ENV_TOPIC_DISCOVERY_PROVIDER = "SILVERMAN_FLOW_B_TOPIC_DISCOVERY_PROVIDER"

ERROR_PROVIDER_UNSUPPORTED = "discovery_provider_unsupported"
ERROR_PROVIDER_NOT_CONFIGURED = "discovery_config_invalid"


@dataclass(frozen=True)
class DiscoveryProviderResult:
    """Raw provider response — orchestration parses and validates topics."""

    content: str | None
    error_code: str | None
    provider: str


class TopicDiscoveryProvider(Protocol):
    """Pluggable discovery client; Flow B orchestration stays provider-agnostic."""

    @property
    def name(self) -> str: ...

    def discover_topics(
        self,
        messages: list[dict[str, str]],
        *,
        count: int,
    ) -> DiscoveryProviderResult: ...


@dataclass(frozen=True)
class DeepSeekTopicDiscoveryProvider:
    """DeepSeek chat-completions adapter for topic discovery batches."""

    settings: DeepSeekSettings
    client: httpx.Client | None = None

    @property
    def name(self) -> str:
        return PROVIDER_DEEPSEEK

    def discover_topics(
        self,
        messages: list[dict[str, str]],
        *,
        count: int,
    ) -> DiscoveryProviderResult:
        del count  # count is encoded in the prompt; seam keeps signature stable
        if not self.settings.is_configured:
            return DiscoveryProviderResult(
                content=None,
                error_code="deepseek_api_key_missing",
                provider=self.name,
            )
        generation = generate_linkedin_draft_content(
            self.settings,
            messages,
            client=self.client,
        )
        return DiscoveryProviderResult(
            content=generation.content,
            error_code=generation.error_code,
            provider=self.name,
        )


def create_topic_discovery_provider(
    name: str | None = None,
    *,
    settings: DeepSeekSettings | None = None,
    client: httpx.Client | None = None,
) -> TopicDiscoveryProvider:
    """Factory: DeepSeek only in v1; unknown names fail closed via UnsupportedProvider."""
    selected = (name or DEFAULT_TOPIC_DISCOVERY_PROVIDER).strip().lower()
    if selected != PROVIDER_DEEPSEEK:
        return _UnsupportedTopicDiscoveryProvider(selected)
    if settings is None:
        return _UnsupportedTopicDiscoveryProvider(
            PROVIDER_DEEPSEEK,
            error_code=ERROR_PROVIDER_NOT_CONFIGURED,
        )
    return DeepSeekTopicDiscoveryProvider(settings=settings, client=client)


@dataclass(frozen=True)
class _UnsupportedTopicDiscoveryProvider:
    requested: str
    error_code: str = ERROR_PROVIDER_UNSUPPORTED

    @property
    def name(self) -> str:
        return self.requested or "unknown"

    def discover_topics(
        self,
        messages: list[dict[str, str]],
        *,
        count: int,
    ) -> DiscoveryProviderResult:
        del messages, count
        return DiscoveryProviderResult(
            content=None,
            error_code=self.error_code,
            provider=self.name,
        )
