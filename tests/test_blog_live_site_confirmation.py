"""Tests for live-site confirmation after Git publication."""

from __future__ import annotations

from pathlib import Path
from urllib.error import URLError

import pytest

from silverman_blog_linkedin.blog_live_site_confirmation import (
    BLOG_LIVE_SITE_CONFIRMATION_DISABLED,
    BLOG_LIVE_SITE_CONFIRMATION_GIT_REQUIRED,
    BLOG_LIVE_SITE_CONFIRMATION_INVALID_URL,
    BLOG_LIVE_SITE_CONFIRMATION_UNREACHABLE,
    FakeHttpProbeClient,
    HttpProbeResponse,
    confirm_blog_live_site_publication,
)
from silverman_blog_linkedin.blog_live_site_confirmation_config import (
    LiveSiteConfirmationSettings,
)
from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    FLOW_A,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_BLOG_PUBLISHED,
    STATE_VALIDATED,
    build_initial_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)

PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLICATION_DATE = "2026-07-06"
CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
SOURCE_URL = f"https://silverman.pro/{PUBLICATION_DATE}/{PUBLIC_SLUG}/"


def _enabled_settings() -> LiveSiteConfirmationSettings:
    return LiveSiteConfirmationSettings(
        confirmation_enabled=True,
        probe_timeout_seconds=10,
        probe_max_attempts=5,
        probe_retry_delay_seconds=0,
        site_base_url="https://silverman.pro",
        allowed_host="silverman.pro",
    )


def _campaign(editorial_base: Path, **extra: object) -> dict:
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug="01-why-i-did-not-start-with-the-database",
        public_slug=PUBLIC_SLUG,
        source_relative_path="blog-posts/ready/01-why-i-did-not-start-with-the-database.md",
        image_relative_path="blog-posts/ready/01-why-i-did-not-start-with-the-database.png",
        source_content="hash-source",
        publication_date=PUBLICATION_DATE,
    )
    transition_state(campaign, STATE_VALIDATED, reason="validated", actor=ACTOR_WORKER)
    transition_state(
        campaign, STATE_BLOG_PUBLISH_PENDING, reason="publish pending", actor=ACTOR_WORKER
    )
    transition_state(campaign, STATE_BLOG_PUBLISHED, reason="published", actor=ACTOR_WORKER)
    campaign["source_public_url"] = SOURCE_URL
    campaign["blog_git_publication"] = {
        "status": "pushed",
        "commit_sha": "abc123",
        "remote": "origin",
        "branch": "main",
    }
    campaign.update(extra)
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)
    return campaign


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    (base / "metadata/campaigns").mkdir(parents=True)
    return base


def test_disabled_guard_no_http_calls(editorial_base: Path) -> None:
    campaign = _campaign(editorial_base)
    client = FakeHttpProbeClient()
    result = confirm_blog_live_site_publication(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        source_public_url=SOURCE_URL,
        public_slug=PUBLIC_SLUG,
        settings=LiveSiteConfirmationSettings(
            confirmation_enabled=False,
            probe_timeout_seconds=10,
            probe_max_attempts=5,
            probe_retry_delay_seconds=2,
            site_base_url="https://silverman.pro",
            allowed_host="silverman.pro",
        ),
        http_client=client,
    )
    assert result.status == "failed"
    assert BLOG_LIVE_SITE_CONFIRMATION_DISABLED in result.errors
    assert client.calls == []


def test_git_required_without_push_evidence(editorial_base: Path) -> None:
    campaign = _campaign(editorial_base)
    campaign.pop("blog_git_publication")
    client = FakeHttpProbeClient()
    result = confirm_blog_live_site_publication(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        source_public_url=SOURCE_URL,
        public_slug=PUBLIC_SLUG,
        settings=_enabled_settings(),
        http_client=client,
    )
    assert BLOG_LIVE_SITE_CONFIRMATION_GIT_REQUIRED in result.errors
    assert client.calls == []


def test_successful_confirmation(editorial_base: Path) -> None:
    campaign = _campaign(editorial_base)
    client = FakeHttpProbeClient(
        responses=[
            HttpProbeResponse(
                status_code=200,
                body=f"<html>{PUBLIC_SLUG}</html>",
                final_url=SOURCE_URL,
            )
        ]
    )
    result = confirm_blog_live_site_publication(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        source_public_url=SOURCE_URL,
        public_slug=PUBLIC_SLUG,
        settings=_enabled_settings(),
        http_client=client,
        sleep_fn=lambda _seconds: None,
    )
    assert result.status == "completed"
    assert result.blog_live_site_publication["status"] == "confirmed"
    assert result.blog_live_site_publication["attempts"] == 1
    assert client.calls == [(SOURCE_URL, 10.0)]


def test_retry_then_success(editorial_base: Path) -> None:
    campaign = _campaign(editorial_base)
    client = FakeHttpProbeClient(
        responses=[
            HttpProbeResponse(status_code=503, body="", final_url=SOURCE_URL),
            HttpProbeResponse(
                status_code=200,
                body=PUBLIC_SLUG,
                final_url=SOURCE_URL,
            ),
        ]
    )
    result = confirm_blog_live_site_publication(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        source_public_url=SOURCE_URL,
        public_slug=PUBLIC_SLUG,
        settings=_enabled_settings(),
        http_client=client,
        sleep_fn=lambda _seconds: None,
    )
    assert result.status == "completed"
    assert result.blog_live_site_publication["attempts"] == 2
    assert len(client.calls) == 2


def test_exhausted_retries_fail(editorial_base: Path) -> None:
    campaign = _campaign(editorial_base)
    client = FakeHttpProbeClient(
        responses=[
            HttpProbeResponse(status_code=404, body="missing", final_url=SOURCE_URL),
            HttpProbeResponse(status_code=404, body="missing", final_url=SOURCE_URL),
        ]
    )
    settings = LiveSiteConfirmationSettings(
        confirmation_enabled=True,
        probe_timeout_seconds=10,
        probe_max_attempts=2,
        probe_retry_delay_seconds=0,
        site_base_url="https://silverman.pro",
        allowed_host="silverman.pro",
    )
    result = confirm_blog_live_site_publication(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        source_public_url=SOURCE_URL,
        public_slug=PUBLIC_SLUG,
        settings=settings,
        http_client=client,
        sleep_fn=lambda _seconds: None,
    )
    assert result.status == "failed"
    assert BLOG_LIVE_SITE_CONFIRMATION_UNREACHABLE in result.errors
    assert result.blog_live_site_publication["status"] == "failed"


def test_already_confirmed_without_new_http(editorial_base: Path) -> None:
    campaign = _campaign(
        editorial_base,
        blog_live_site_publication={
            "status": "confirmed",
            "source_public_url": SOURCE_URL,
            "commit_sha": "abc123",
            "http_status": 200,
            "final_url": SOURCE_URL,
            "attempts": 1,
        },
    )
    client = FakeHttpProbeClient()
    result = confirm_blog_live_site_publication(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        source_public_url=SOURCE_URL,
        public_slug=PUBLIC_SLUG,
        settings=_enabled_settings(),
        http_client=client,
    )
    assert result.status == "completed"
    assert result.blog_live_site_publication["status"] == "already_confirmed"
    assert client.calls == []


def test_invalid_host_blocked(editorial_base: Path) -> None:
    campaign = _campaign(editorial_base)
    client = FakeHttpProbeClient()
    result = confirm_blog_live_site_publication(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        source_public_url="https://evil.example/post/",
        public_slug=PUBLIC_SLUG,
        settings=_enabled_settings(),
        http_client=client,
    )
    assert BLOG_LIVE_SITE_CONFIRMATION_INVALID_URL in result.errors
    assert client.calls == []


def test_network_error_retries(editorial_base: Path) -> None:
    campaign = _campaign(editorial_base)
    client = FakeHttpProbeClient(
        responses=[
            URLError("timeout"),
            HttpProbeResponse(status_code=200, body=PUBLIC_SLUG, final_url=SOURCE_URL),
        ]
    )
    result = confirm_blog_live_site_publication(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        source_public_url=SOURCE_URL,
        public_slug=PUBLIC_SLUG,
        settings=_enabled_settings(),
        http_client=client,
        sleep_fn=lambda _seconds: None,
    )
    assert result.status == "completed"
    assert result.blog_live_site_publication["attempts"] == 2
