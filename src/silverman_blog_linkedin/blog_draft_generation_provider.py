"""Provider-pluggable seam for Flow B blog draft text generation (US-079).

v1 ships DeepSeek only. Unsupported providers fail closed. API keys MUST NEVER
appear in results or error payloads.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Protocol

import httpx

from silverman_blog_linkedin.deepseek_client import generate_linkedin_draft_content
from silverman_blog_linkedin.deepseek_config import DeepSeekSettings

PROVIDER_DEEPSEEK = "deepseek"
DEFAULT_BLOG_DRAFT_PROVIDER = PROVIDER_DEEPSEEK
ENV_BLOG_DRAFT_PROVIDER = "SILVERMAN_FLOW_B_BLOG_DRAFT_PROVIDER"

# Blog drafts need more tokens than LinkedIn variant defaults (1024).
BLOG_DRAFT_MIN_MAX_OUTPUT_TOKENS = 4096

ERROR_PROVIDER_UNSUPPORTED = "draft_provider_unsupported"
ERROR_PROVIDER_NOT_CONFIGURED = "draft_config_invalid"


@dataclass(frozen=True)
class BlogDraftProviderResult:
    """Raw provider response — orchestration validates Markdown and anti-AI rules."""

    content: str | None
    error_code: str | None
    provider: str


class BlogDraftGenerationProvider(Protocol):
    """Pluggable blog-draft client; Flow B orchestration stays provider-agnostic."""

    @property
    def name(self) -> str: ...

    def generate_blog_draft(
        self,
        messages: list[dict[str, str]],
    ) -> BlogDraftProviderResult: ...


@dataclass(frozen=True)
class DeepSeekBlogDraftGenerationProvider:
    """DeepSeek chat-completions adapter for Flow B blog Markdown drafts."""

    settings: DeepSeekSettings
    client: httpx.Client | None = None

    @property
    def name(self) -> str:
        return PROVIDER_DEEPSEEK

    def generate_blog_draft(
        self,
        messages: list[dict[str, str]],
    ) -> BlogDraftProviderResult:
        if not self.settings.is_configured:
            return BlogDraftProviderResult(
                content=None,
                error_code="deepseek_api_key_missing",
                provider=self.name,
            )
        effective = self.settings
        if effective.max_output_tokens < BLOG_DRAFT_MIN_MAX_OUTPUT_TOKENS:
            effective = replace(
                effective,
                max_output_tokens=BLOG_DRAFT_MIN_MAX_OUTPUT_TOKENS,
            )
        generation = generate_linkedin_draft_content(
            effective,
            messages,
            client=self.client,
        )
        return BlogDraftProviderResult(
            content=generation.content,
            error_code=generation.error_code,
            provider=self.name,
        )


def create_blog_draft_provider(
    name: str | None = None,
    *,
    settings: DeepSeekSettings | None = None,
    client: httpx.Client | None = None,
) -> BlogDraftGenerationProvider:
    """Factory: DeepSeek only in v1; unknown names fail closed via UnsupportedProvider."""
    selected = (name or DEFAULT_BLOG_DRAFT_PROVIDER).strip().lower()
    if selected != PROVIDER_DEEPSEEK:
        return _UnsupportedBlogDraftProvider(selected)
    if settings is None:
        return _UnsupportedBlogDraftProvider(
            PROVIDER_DEEPSEEK,
            error_code=ERROR_PROVIDER_NOT_CONFIGURED,
        )
    return DeepSeekBlogDraftGenerationProvider(settings=settings, client=client)


@dataclass(frozen=True)
class _UnsupportedBlogDraftProvider:
    requested: str
    error_code: str = ERROR_PROVIDER_UNSUPPORTED

    @property
    def name(self) -> str:
        return self.requested or "unknown"

    def generate_blog_draft(
        self,
        messages: list[dict[str, str]],
    ) -> BlogDraftProviderResult:
        del messages
        return BlogDraftProviderResult(
            content=None,
            error_code=self.error_code,
            provider=self.name,
        )
