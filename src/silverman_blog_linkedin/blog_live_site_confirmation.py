"""HTTP live-site confirmation after successful Git publication."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from silverman_blog_linkedin.blog_live_site_confirmation_config import (
    LiveSiteConfirmationSettings,
    load_live_site_confirmation_settings,
)
from silverman_blog_linkedin.campaign_lifecycle import write_campaign_metadata
from silverman_blog_linkedin.run_metadata import utc_now_iso

logger = logging.getLogger(__name__)

BLOG_LIVE_SITE_CONFIRMATION_DISABLED = "blog_live_site_confirmation_disabled"
BLOG_LIVE_SITE_CONFIRMATION_GIT_REQUIRED = "blog_live_site_confirmation_git_required"
BLOG_LIVE_SITE_CONFIRMATION_INVALID_URL = "blog_live_site_confirmation_invalid_url"
BLOG_LIVE_SITE_CONFIRMATION_UNREACHABLE = "blog_live_site_confirmation_unreachable"

LIVE_SITE_RECOVERY_MESSAGE = (
    "Remote Git publication completed but live-site confirmation did not succeed. "
    "Retry with live_site_confirmation after GitHub Pages propagation or verify manually."
)

_MAX_REDIRECTS = 5


@dataclass(frozen=True)
class HttpProbeResponse:
    status_code: int
    body: str
    final_url: str


class HttpProbeClient(Protocol):
    def get(self, url: str, *, timeout: float) -> HttpProbeResponse: ...


@dataclass
class StdlibHttpProbeClient:
    """Production HTTP probe client using urllib."""

    def get(self, url: str, *, timeout: float) -> HttpProbeResponse:
        current_url = url
        for _ in range(_MAX_REDIRECTS + 1):
            request = Request(
                current_url,
                headers={"User-Agent": "silverman-blog-linkedin-live-site-probe/1.0"},
                method="GET",
            )
            try:
                with urlopen(request, timeout=timeout) as response:
                    body_bytes = response.read()
                    body = body_bytes.decode("utf-8", errors="replace")
                    final_url = response.geturl()
                    return HttpProbeResponse(
                        status_code=response.status,
                        body=body,
                        final_url=final_url,
                    )
            except HTTPError as exc:
                if exc.code in {301, 302, 303, 307, 308}:
                    location = exc.headers.get("Location")
                    if not location:
                        return HttpProbeResponse(
                            status_code=exc.code,
                            body="",
                            final_url=current_url,
                        )
                    current_url = location
                    continue
                try:
                    body = exc.read().decode("utf-8", errors="replace")
                except Exception:
                    body = ""
                return HttpProbeResponse(
                    status_code=exc.code,
                    body=body,
                    final_url=current_url,
                )
            except URLError:
                raise
        return HttpProbeResponse(status_code=0, body="", final_url=current_url)


@dataclass
class FakeHttpProbeClient:
    """Injectable HTTP probe client for tests."""

    responses: list[HttpProbeResponse | Exception] = field(default_factory=list)
    calls: list[tuple[str, float]] = field(default_factory=list)
    call_index: int = 0

    def get(self, url: str, *, timeout: float) -> HttpProbeResponse:
        self.calls.append((url, timeout))
        if self.call_index >= len(self.responses):
            raise URLError("no more fake responses")
        response = self.responses[self.call_index]
        self.call_index += 1
        if isinstance(response, Exception):
            raise response
        return response


@dataclass
class LiveSiteConfirmationResult:
    status: str
    blog_live_site_publication: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata_written: bool = False
    metadata_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "blog_live_site_publication": self.blog_live_site_publication,
            "errors": self.errors,
            "metadata_written": self.metadata_written,
            "metadata_error_code": self.metadata_error_code,
        }


def _git_push_evidence(campaign: dict[str, Any]) -> dict[str, Any] | None:
    prior = campaign.get("blog_git_publication") or {}
    if prior.get("status") in {"pushed", "already_published"}:
        return prior
    return None


def _git_push_evidence_from_result(blog_git_publication: dict[str, Any]) -> bool:
    return blog_git_publication.get("status") in {"pushed", "already_published"}


def _validate_source_public_url(
    source_public_url: str,
    settings: LiveSiteConfirmationSettings,
) -> str | None:
    parsed = urlparse(source_public_url)
    if parsed.scheme not in {"http", "https"}:
        return BLOG_LIVE_SITE_CONFIRMATION_INVALID_URL
    host = parsed.netloc.strip().lower()
    if host.startswith("www."):
        host = host[4:]
    if host != settings.allowed_host:
        return BLOG_LIVE_SITE_CONFIRMATION_INVALID_URL
    return None


def _matching_prior_live_confirmation(
    campaign: dict[str, Any],
    *,
    source_public_url: str,
    commit_sha: str | None,
) -> dict[str, Any] | None:
    prior = campaign.get("blog_live_site_publication") or {}
    if prior.get("status") != "confirmed":
        return None
    if prior.get("source_public_url") != source_public_url:
        return None
    if commit_sha and prior.get("commit_sha") and prior.get("commit_sha") != commit_sha:
        return None
    return prior


def _probe_succeeded(response: HttpProbeResponse, *, public_slug: str) -> bool:
    return response.status_code == 200 and public_slug in response.body


def confirm_blog_live_site_publication(
    base_path: Any,
    *,
    campaign_id: str,
    campaign: dict[str, Any],
    source_public_url: str,
    public_slug: str,
    blog_git_publication: dict[str, Any] | None = None,
    settings: LiveSiteConfirmationSettings | None = None,
    http_client: HttpProbeClient | None = None,
    environ: dict[str, str] | None = None,
    sleep_fn: Any = time.sleep,
) -> LiveSiteConfirmationResult:
    """HTTP-probe source_public_url after successful Git publication."""
    config = settings or load_live_site_confirmation_settings(environ)
    client = http_client or StdlibHttpProbeClient()

    if not config.confirmation_enabled:
        return LiveSiteConfirmationResult(
            status="failed",
            blog_live_site_publication={
                "status": "failed",
                "error_code": BLOG_LIVE_SITE_CONFIRMATION_DISABLED,
            },
            errors=[BLOG_LIVE_SITE_CONFIRMATION_DISABLED],
        )

    git_evidence = blog_git_publication if blog_git_publication else _git_push_evidence(campaign)
    if not git_evidence or not _git_push_evidence_from_result(git_evidence):
        return LiveSiteConfirmationResult(
            status="failed",
            blog_live_site_publication={
                "status": "failed",
                "error_code": BLOG_LIVE_SITE_CONFIRMATION_GIT_REQUIRED,
            },
            errors=[BLOG_LIVE_SITE_CONFIRMATION_GIT_REQUIRED],
        )

    commit_sha = git_evidence.get("commit_sha")
    prior = _matching_prior_live_confirmation(
        campaign,
        source_public_url=source_public_url,
        commit_sha=commit_sha,
    )
    if prior is not None:
        blog_live_site_publication = dict(prior)
        blog_live_site_publication["status"] = "already_confirmed"
        return LiveSiteConfirmationResult(
            status="completed",
            blog_live_site_publication=blog_live_site_publication,
            errors=[],
        )

    invalid_url = _validate_source_public_url(source_public_url, config)
    if invalid_url is not None:
        blog_live_site_publication = {
            "status": "failed",
            "source_public_url": source_public_url,
            "error_code": invalid_url,
        }
        campaign["blog_live_site_publication"] = blog_live_site_publication
        metadata_written, metadata_error_code = _persist_campaign(
            base_path, campaign_id, campaign
        )
        return LiveSiteConfirmationResult(
            status="failed",
            blog_live_site_publication=blog_live_site_publication,
            errors=[invalid_url],
            metadata_written=metadata_written,
            metadata_error_code=metadata_error_code,
        )

    attempts = 0
    last_status: int | None = None
    last_final_url: str | None = None
    for attempt in range(1, config.probe_max_attempts + 1):
        attempts = attempt
        try:
            response = client.get(
                source_public_url,
                timeout=float(config.probe_timeout_seconds),
            )
            last_status = response.status_code
            last_final_url = response.final_url
            if _probe_succeeded(response, public_slug=public_slug):
                confirmed_at = utc_now_iso()
                blog_live_site_publication = {
                    "status": "confirmed",
                    "source_public_url": source_public_url,
                    "http_status": response.status_code,
                    "final_url": response.final_url,
                    "attempts": attempts,
                    "confirmed_at": confirmed_at,
                    "commit_sha": commit_sha,
                    "error_code": None,
                }
                campaign["blog_live_site_publication"] = blog_live_site_publication
                metadata_written, metadata_error_code = _persist_campaign(
                    base_path, campaign_id, campaign
                )
                return LiveSiteConfirmationResult(
                    status="completed",
                    blog_live_site_publication=blog_live_site_publication,
                    metadata_written=metadata_written,
                    metadata_error_code=metadata_error_code,
                )
        except URLError as exc:
            logger.warning(
                "live-site probe attempt %s failed for campaign %s: %s",
                attempt,
                campaign_id,
                type(exc).__name__,
            )
        if attempt < config.probe_max_attempts:
            sleep_fn(float(config.probe_retry_delay_seconds))

    blog_live_site_publication = {
        "status": "failed",
        "source_public_url": source_public_url,
        "http_status": last_status,
        "final_url": last_final_url,
        "attempts": attempts,
        "commit_sha": commit_sha,
        "error_code": BLOG_LIVE_SITE_CONFIRMATION_UNREACHABLE,
    }
    campaign["blog_live_site_publication"] = blog_live_site_publication
    metadata_written, metadata_error_code = _persist_campaign(
        base_path, campaign_id, campaign
    )
    errors = [BLOG_LIVE_SITE_CONFIRMATION_UNREACHABLE, LIVE_SITE_RECOVERY_MESSAGE]
    return LiveSiteConfirmationResult(
        status="failed",
        blog_live_site_publication=blog_live_site_publication,
        errors=errors,
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )


def _persist_campaign(
    base_path: Any,
    campaign_id: str,
    campaign: dict[str, Any],
) -> tuple[bool, str | None]:
    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    if not write_result.written:
        return False, write_result.error_code
    return True, None


def merge_live_site_confirmation_into_publish_result(
    result: Any,
    live_result: LiveSiteConfirmationResult,
    *,
    git_push_succeeded: bool,
) -> None:
    """Apply live-site confirmation outcome onto a BlogPublishResult."""
    result.blog_live_site_publication = dict(live_result.blog_live_site_publication)
    if live_result.errors:
        result.errors = list(dict.fromkeys([*result.errors, *live_result.errors]))
    if not live_result.metadata_written and live_result.metadata_error_code:
        if live_result.metadata_error_code not in result.errors:
            result.errors.append(live_result.metadata_error_code)

    if live_result.status == "completed":
        if result.status == "completed":
            result.status = "completed"
        return

    if git_push_succeeded:
        result.status = "partial"
    elif result.status == "completed":
        result.status = "failed"
