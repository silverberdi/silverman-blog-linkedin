"""LinkedIn REST Posts API client for personal-profile text posts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from silverman_blog_linkedin.linkedin_config import LinkedInPublicationSettings

LINKEDIN_POSTS_URL = "https://api.linkedin.com/rest/posts"
RESTLI_PROTOCOL_VERSION = "2.0.0"


class HttpClientProtocol(Protocol):
    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        headers: dict[str, str],
    ) -> httpx.Response: ...


@dataclass(frozen=True)
class LinkedInPostResult:
    post_urn: str | None
    error_code: str | None
    http_status: int | None = None
    retryable: bool = False


def build_commentary(*, variant_text: str, blog_url: str) -> str:
    """Build LinkedIn post commentary from variant text and blog URL."""
    text = variant_text.strip()
    url = blog_url.strip()
    if url in text:
        return text
    if text:
        return f"{text}\n\n{url}"
    return url


def build_text_post_payload(
    *,
    member_urn: str,
    commentary: str,
) -> dict[str, Any]:
    """Build LinkedIn REST Posts API payload for a text-only personal post."""
    return {
        "author": member_urn,
        "commentary": commentary,
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }


def _map_http_status(status_code: int) -> tuple[str, bool]:
    if status_code == 401:
        return "linkedin_publish_token_invalid", False
    if status_code == 403:
        return "linkedin_publish_insufficient_permission", False
    if status_code in (400, 422):
        return "linkedin_publish_content_invalid", False
    if status_code == 429:
        return "linkedin_publish_api_error", True
    if status_code >= 500:
        return "linkedin_publish_api_error", True
    return "linkedin_publish_api_error", False


def create_member_text_post(
    settings: LinkedInPublicationSettings,
    *,
    commentary: str,
    client: HttpClientProtocol | None = None,
) -> LinkedInPostResult:
    """Create a personal-profile text post via LinkedIn REST Posts API."""
    payload = build_text_post_payload(
        member_urn=settings.member_urn,
        commentary=commentary,
    )
    headers = {
        "Authorization": f"Bearer {settings.access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": RESTLI_PROTOCOL_VERSION,
        "Linkedin-Version": settings.api_version,
    }

    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=30.0)

    try:
        response = client.post(LINKEDIN_POSTS_URL, json=payload, headers=headers)
    except httpx.HTTPError:
        return LinkedInPostResult(
            post_urn=None,
            error_code="linkedin_publish_api_error",
            http_status=None,
            retryable=True,
        )
    finally:
        if owns_client and isinstance(client, httpx.Client):
            client.close()

    if response.status_code == 201:
        post_urn = response.headers.get("x-restli-id") or response.headers.get(
            "X-RestLi-Id"
        )
        if not post_urn:
            return LinkedInPostResult(
                post_urn=None,
                error_code="linkedin_publish_api_error",
                http_status=201,
                retryable=True,
            )
        return LinkedInPostResult(
            post_urn=post_urn,
            error_code=None,
            http_status=201,
            retryable=False,
        )

    error_code, retryable = _map_http_status(response.status_code)
    return LinkedInPostResult(
        post_urn=None,
        error_code=error_code,
        http_status=response.status_code,
        retryable=retryable,
    )
