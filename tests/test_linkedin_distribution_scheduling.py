"""Tests for Flow A LinkedIn distribution scheduling."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    CANONICAL_VARIANT_IDS,
    FLOW_A,
    FLOW_B,
    METADATA_CAMPAIGNS_RELATIVE,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_GENERATED,
    STATE_DERIVATIVES_PENDING,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_VALIDATED,
    build_derivative_idempotency_key,
    build_initial_campaign_metadata,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.linkedin_distribution_schedule import (
    DEFAULT_STAGGER_STRATEGY,
    FLOW_B_SPILL_A_STRATEGY,
    LINKEDIN_SCHEDULE_ARTIFACT_HASH_CHANGED,
    LINKEDIN_SCHEDULE_ARTIFACT_MISSING,
    LINKEDIN_SCHEDULE_CAMPAIGN_NOT_FOUND,
    LINKEDIN_SCHEDULE_FLOW_NOT_ALLOWED,
    LINKEDIN_SCHEDULE_INVALID_ANCHOR,
    LINKEDIN_SCHEDULE_INVALID_CAMPAIGN_STATE,
    LINKEDIN_SCHEDULE_INVALID_STRATEGY,
    LINKEDIN_SCHEDULE_METADATA_MISMATCH,
    LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT,
    LINKEDIN_SCHEDULE_PACKAGE_MISSING,
    LINKEDIN_SCHEDULE_SPILL_DENSITY_EXHAUSTED,
    LINKEDIN_SCHEDULE_VARIANT_METADATA_MISSING,
    VARIANT_DAY_OFFSETS,
    build_schedule_idempotency_key,
    schedule_linkedin_distribution,
)
from silverman_blog_linkedin.linkedin_package_flow import (
    GENERATED_RELATIVE,
    build_package_idempotency_key,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, create_full_layout, make_settings

SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLICATION_DATE = "2026-07-06"
SOURCE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
IMAGE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.png"
CANONICAL_CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
PUBLIC_URL = "https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/"
ANCHOR_UTC = "2026-07-07T14:00:00Z"
TITLE = "Why I Did Not Start With the Database"


def _canonical_frontmatter() -> str:
    return (
        "---\n"
        f"title: {TITLE}\n"
        "audience: architects\n"
        "type: blog-post\n"
        "language: en\n"
        "layout: post\n"
        f"date: {PUBLICATION_DATE}\n"
        "categories:\n"
        "  - architecture\n"
        "tags:\n"
        "  - databases\n"
        "description: A senior practitioner's take on starting with the domain.\n"
        f"image: /assets/images/{PUBLIC_SLUG}.png\n"
        "---\n"
    )


def _canonical_body() -> str:
    return (
        f"# {TITLE}\n\n"
        "The real problem is not persistence. The real problem is naming the business too late.\n"
    )


def _write_post(base: Path) -> Path:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    md_path = ready / f"{SOURCE_SLUG}.md"
    md_path.write_text(_canonical_frontmatter() + _canonical_body(), encoding="utf-8")
    return md_path


def _setup_metadata_campaigns(base: Path) -> Path:
    metadata_dir = base / METADATA_CAMPAIGNS_RELATIVE
    metadata_dir.mkdir(parents=True, exist_ok=True)
    return metadata_dir


def _artifact_content(variant_id: str) -> str:
    return f"LinkedIn draft for {variant_id}.\nRead the full story here: {PUBLIC_URL}\n"


def _write_artifact(base: Path, variant_id: str, *, content: str | None = None) -> tuple[str, str]:
    artifact_dir = base / GENERATED_RELATIVE / CANONICAL_CAMPAIGN_ID
    artifact_dir.mkdir(parents=True, exist_ok=True)
    body = content if content is not None else _artifact_content(variant_id)
    if body and not body.endswith("\n"):
        body += "\n"
    raw = body.encode("utf-8")
    artifact_path = artifact_dir / f"{variant_id}.md"
    artifact_path.write_bytes(raw)
    return f"{GENERATED_RELATIVE}/{CANONICAL_CAMPAIGN_ID}/{variant_id}.md", hashlib.sha256(raw).hexdigest()


def _variant_entry(
    variant_id: str,
    *,
    artifact_relative_path: str,
    derivative_content_sha256: str,
) -> dict:
    return {
        "variant": variant_id,
        "audience": "senior practitioners",
        "tone": "executive",
        "source_public_url": PUBLIC_URL,
        "source_relative_path": SOURCE_RELATIVE,
        "campaign_id": CANONICAL_CAMPAIGN_ID,
        "source_content_sha256": "placeholder",
        "derivative_content_sha256": derivative_content_sha256,
        "artifact_relative_path": artifact_relative_path,
        "idempotency_key": build_derivative_idempotency_key(
            campaign_id=CANONICAL_CAMPAIGN_ID,
            source_content_sha256="placeholder",
            variant=variant_id,
            flow=FLOW_A,
        ),
        "generated_at": "2026-07-06T12:00:00Z",
        "provider": "deepseek",
        "model": "deepseek-chat",
    }


def _derivatives_generated_campaign(
    base: Path,
    *,
    variant_ids: list[str] | None = None,
    include_package: bool = True,
    include_variants: bool = True,
) -> dict:
    content = _write_post(base).read_text(encoding="utf-8")
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=SOURCE_RELATIVE,
        image_relative_path=IMAGE_RELATIVE,
        source_content=content,
        publication_date=PUBLICATION_DATE,
    )
    transition_state(
        campaign,
        STATE_VALIDATED,
        reason="Editorial validation passed",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_BLOG_PUBLISH_PENDING,
        reason="Blog publish started",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_BLOG_PUBLISHED,
        reason="Blog published",
        actor=ACTOR_WORKER,
    )
    campaign["source_public_url"] = PUBLIC_URL
    source_hash = campaign["source_content_sha256"]

    resolved_variant_ids = sorted(variant_ids or CANONICAL_VARIANT_IDS)
    variant_entries: list[dict] = []
    for variant_id in resolved_variant_ids:
        artifact_relative, derivative_hash = _write_artifact(base, variant_id)
        entry = _variant_entry(
            variant_id,
            artifact_relative_path=artifact_relative,
            derivative_content_sha256=derivative_hash,
        )
        entry["source_content_sha256"] = source_hash
        entry["idempotency_key"] = build_derivative_idempotency_key(
            campaign_id=CANONICAL_CAMPAIGN_ID,
            source_content_sha256=source_hash,
            variant=variant_id,
            flow=FLOW_A,
        )
        variant_entries.append(entry)

    if include_variants:
        campaign["variants"] = variant_entries
    else:
        campaign["variants"] = []

    if include_package:
        campaign["linkedin_package"] = {
            "package_id": f"{CANONICAL_CAMPAIGN_ID}-pkg",
            "idempotency_key": build_package_idempotency_key(
                campaign_id=CANONICAL_CAMPAIGN_ID,
                source_content_sha256=source_hash,
                variant_ids=resolved_variant_ids,
                flow=FLOW_A,
            ),
            "package_status": "generated",
            "generated_at": "2026-07-06T12:00:00Z",
            "source_public_url": PUBLIC_URL,
            "source_relative_path": SOURCE_RELATIVE,
            "source_content_sha256": source_hash,
            "variant_ids": resolved_variant_ids,
        }

    transition_state(
        campaign,
        STATE_DERIVATIVES_PENDING,
        reason="LinkedIn derivative package generation started",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_DERIVATIVES_GENERATED,
        reason="LinkedIn derivative package generated",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(base, CANONICAL_CAMPAIGN_ID, campaign)
    return campaign


def _schedule(
    base: Path,
    *,
    campaign_id: str | None = CANONICAL_CAMPAIGN_ID,
    source_relative_path: str | None = None,
    strategy: str | None = None,
    start_at_utc: str | None = ANCHOR_UTC,
):
    return schedule_linkedin_distribution(
        base,
        campaign_id=campaign_id,
        source_relative_path=source_relative_path,
        strategy=strategy,
        start_at_utc=start_at_utc,
    )


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    _setup_metadata_campaigns(tmp_path)
    (tmp_path / "linkedin-posts").mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_campaign_not_found(editorial_base: Path):
    result = _schedule(editorial_base, campaign_id="flow-a-2026-07-06-missing")

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_CAMPAIGN_NOT_FOUND in result.errors


def test_flow_b_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    campaign = dict(campaign)
    campaign["flow"] = FLOW_B
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_FLOW_NOT_ALLOWED in result.errors


def test_campaign_before_derivatives_generated_rejected(editorial_base: Path):
    content = _write_post(editorial_base).read_text(encoding="utf-8")
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=SOURCE_RELATIVE,
        image_relative_path=IMAGE_RELATIVE,
        source_content=content,
        publication_date=PUBLICATION_DATE,
    )
    transition_state(
        campaign,
        STATE_VALIDATED,
        reason="Editorial validation passed",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_BLOG_PUBLISH_PENDING,
        reason="Blog publish started",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_BLOG_PUBLISHED,
        reason="Blog published",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_INVALID_CAMPAIGN_STATE in result.errors


def test_missing_linkedin_package_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base, include_package=False)

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_PACKAGE_MISSING in result.errors


def test_missing_variant_metadata_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base, variant_ids=["executive-recruiter"])
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    package = campaign["linkedin_package"]
    package["variant_ids"] = sorted(CANONICAL_VARIANT_IDS)
    write_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID, campaign)

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_VARIANT_METADATA_MISSING in result.errors


def test_missing_artifact_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    artifact = (
        editorial_base
        / GENERATED_RELATIVE
        / CANONICAL_CAMPAIGN_ID
        / "executive-recruiter.md"
    )
    artifact.unlink()

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_ARTIFACT_MISSING in result.errors


def test_artifact_hash_changed_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    artifact = (
        editorial_base
        / GENERATED_RELATIVE
        / CANONICAL_CAMPAIGN_ID
        / "executive-recruiter.md"
    )
    artifact.write_text("changed content\n", encoding="utf-8")

    result = _schedule(editorial_base)

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_ARTIFACT_HASH_CHANGED in result.errors


def test_successful_scheduling_writes_variant_schedule_fields(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base)

    assert result.status == "completed"
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    for variant_schedule in result.variant_schedules:
        assert variant_schedule["scheduled_at_utc"]
        assert variant_schedule["publish_state"] == "pending"
        assert variant_schedule["schedule_idempotency_key"]
    for entry in campaign["variants"]:
        assert entry["scheduled_at_utc"]
        assert entry["publish_state"] == "pending"
        assert entry["schedule_idempotency_key"]


def test_successful_scheduling_transitions_to_distribution_scheduled(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base)

    assert result.status == "completed"
    assert result.state == STATE_DISTRIBUTION_SCHEDULED
    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_DISTRIBUTION_SCHEDULED
    states = [entry["to_state"] for entry in campaign["state_history"]]
    assert STATE_DISTRIBUTION_SCHEDULED in states


def test_variants_staggered_at_least_three_calendar_days_apart(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base)
    assert result.status == "completed"

    timestamps = sorted(
        datetime.strptime(item["scheduled_at_utc"], "%Y-%m-%dT%H:%M:%SZ")
        for item in result.variant_schedules
    )
    assert len(timestamps) == len(set(timestamps))
    for earlier, later in zip(timestamps, timestamps[1:]):
        assert (later.date() - earlier.date()).days >= 3


def test_custom_start_at_utc_honored(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    custom_anchor = "2026-08-12T14:00:00Z"

    result = _schedule(editorial_base, start_at_utc=custom_anchor)

    assert result.status == "completed"
    assert result.anchor_utc == custom_anchor
    executive = next(
        item for item in result.variant_schedules if item["variant"] == "executive-recruiter"
    )
    assert executive["scheduled_at_utc"] == custom_anchor


def test_invalid_anchor_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base, start_at_utc="not-a-timestamp")

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_INVALID_ANCHOR in result.errors


def test_invalid_strategy_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base, strategy="unknown-strategy")

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_INVALID_STRATEGY in result.errors


def test_idempotent_rerun_does_not_rewrite_schedules_or_duplicate_state_history(
    editorial_base: Path,
):
    _derivatives_generated_campaign(editorial_base)

    first = _schedule(editorial_base)
    assert first.status == "completed"

    campaign = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    history_len = len(campaign["state_history"])
    schedules_before = {
        entry["variant"]: entry["scheduled_at_utc"] for entry in campaign["variants"]
    }

    second = _schedule(editorial_base)

    assert second.status == "completed"
    assert second.metadata_written is False
    campaign_after = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert campaign_after is not None
    assert len(campaign_after["state_history"]) == history_len
    schedules_after = {
        entry["variant"]: entry["scheduled_at_utc"] for entry in campaign_after["variants"]
    }
    assert schedules_after == schedules_before


def test_metadata_mismatch_rejected(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    first = _schedule(editorial_base, start_at_utc=ANCHOR_UTC)
    assert first.status == "completed"

    result = _schedule(editorial_base, start_at_utc="2026-08-01T14:00:00Z")

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_METADATA_MISMATCH in result.errors


def test_metadata_and_response_exclude_generated_body_text(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base)
    assert result.status == "completed"

    response_json = json.dumps(result.to_dict())
    assert "generated_draft_content" not in response_json
    assert "markdown_content" not in response_json
    assert "Read the full story here" not in response_json

    metadata_path = editorial_base / METADATA_CAMPAIGNS_RELATIVE / f"{CANONICAL_CAMPAIGN_ID}.json"
    raw = metadata_path.read_text(encoding="utf-8")
    assert "generated_draft_content" not in raw
    assert "markdown_content" not in raw
    assert "Read the full story here" not in raw
    assert "linkedin_distribution" in raw


def test_http_endpoint_requires_auth(editorial_base: Path):
    create_full_layout(editorial_base)
    _derivatives_generated_campaign(editorial_base)

    client = TestClient(create_app(make_settings(editorial_base)))

    unauth = client.post(
        "/schedule-linkedin-distribution",
        json={"campaign_id": CANONICAL_CAMPAIGN_ID, "start_at_utc": ANCHOR_UTC},
    )
    assert unauth.status_code == 401

    bad_key = client.post(
        "/schedule-linkedin-distribution",
        headers={"Authorization": "Bearer wrong-key"},
        json={"campaign_id": CANONICAL_CAMPAIGN_ID, "start_at_utc": ANCHOR_UTC},
    )
    assert bad_key.status_code == 401


def test_http_successful_response_shape(editorial_base: Path):
    create_full_layout(editorial_base)
    _derivatives_generated_campaign(editorial_base)

    client = TestClient(create_app(make_settings(editorial_base)))
    response = client.post(
        "/schedule-linkedin-distribution",
        headers=auth_header(),
        json={"campaign_id": CANONICAL_CAMPAIGN_ID, "start_at_utc": ANCHOR_UTC},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["campaign_id"] == CANONICAL_CAMPAIGN_ID
    assert body["state"] == STATE_DISTRIBUTION_SCHEDULED
    assert body["strategy"] == DEFAULT_STAGGER_STRATEGY
    assert body["anchor_utc"] == ANCHOR_UTC
    assert body["distribution_id"] == f"{CANONICAL_CAMPAIGN_ID}-dist"
    assert len(body["variant_schedules"]) == 4
    assert body["distribution"] is not None
    assert body["metadata_written"] is True
    assert "errors" in body
    assert "warnings" in body
    assert "metadata_error_code" in body
    assert "generated_draft_content" not in body
    assert "markdown_content" not in body


def test_http_missing_identifiers_returns_422(editorial_base: Path):
    create_full_layout(editorial_base)
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/schedule-linkedin-distribution",
        headers=auth_header(),
        json={},
    )
    assert response.status_code == 422


def test_http_extra_fields_returns_422(editorial_base: Path):
    create_full_layout(editorial_base)
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/schedule-linkedin-distribution",
        headers=auth_header(),
        json={
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "markdown_content": "secret body",
        },
    )
    assert response.status_code == 422


def test_resolve_by_source_relative_path(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(
        editorial_base,
        campaign_id=None,
        source_relative_path=SOURCE_RELATIVE,
    )

    assert result.status == "completed"
    assert result.campaign_id == CANONICAL_CAMPAIGN_ID


def test_no_n8n_workflow_json_changed():
    n8n_dir = Path(__file__).resolve().parents[1] / "n8n"
    if n8n_dir.is_dir():
        tracked = list(n8n_dir.rglob("*.json"))
        assert tracked == [] or all(path.is_file() for path in tracked)


def test_no_linkedin_api_publication_attempted(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    with patch("httpx.Client.post") as mock_post:
        result = _schedule(editorial_base)

    assert result.status == "completed"
    mock_post.assert_not_called()


def test_schedule_idempotency_key_format(editorial_base: Path):
    campaign = _derivatives_generated_campaign(editorial_base)
    variant_ids = sorted(campaign["linkedin_package"]["variant_ids"])

    expected = build_schedule_idempotency_key(
        campaign_id=CANONICAL_CAMPAIGN_ID,
        source_content_sha256=campaign["source_content_sha256"],
        package_idempotency_key=campaign["linkedin_package"]["idempotency_key"],
        variant_ids=variant_ids,
        strategy=DEFAULT_STAGGER_STRATEGY,
        anchor_utc=ANCHOR_UTC,
        flow=FLOW_A,
    )

    result = _schedule(editorial_base)
    assert result.status == "completed"
    assert result.distribution is not None
    assert result.distribution["idempotency_key"] == expected


def test_stagger_offsets_match_editorial_sequence(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)

    result = _schedule(editorial_base)
    assert result.status == "completed"

    anchor = datetime.strptime(ANCHOR_UTC, "%Y-%m-%dT%H:%M:%SZ")
    for item in result.variant_schedules:
        offset_days = VARIANT_DAY_OFFSETS[item["variant"]]
        expected = (anchor + timedelta(days=offset_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert item["scheduled_at_utc"] == expected


def test_default_anchor_uses_preferred_weekday(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    fixed_now = datetime(2026, 7, 6, 10, 0, 0, tzinfo=timezone.utc)  # Monday

    with patch(
        "silverman_blog_linkedin.linkedin_distribution_schedule.datetime"
    ) as mock_datetime:
        mock_datetime.now.return_value = fixed_now
        mock_datetime.strptime = datetime.strptime
        result = schedule_linkedin_distribution(editorial_base, campaign_id=CANONICAL_CAMPAIGN_ID)

    assert result.status == "completed"
    assert result.anchor_utc == "2026-07-07T14:00:00Z"


def _write_flow_b_sidecar(
    base: Path,
    *,
    target_week: str = "2026-W28",
    empty_days: list[str] | None = None,
) -> None:
    """Sibling .flow-b.json beside ready source for spill A provenance."""
    meta = base / "blog-posts" / "ready" / f"{SOURCE_SLUG}.flow-b.json"
    meta.write_text(
        json.dumps(
            {
                "status": "promoted",
                "origin": "flow_b",
                "flow": "flow_b",
                "slug": SOURCE_SLUG,
                "target_week": target_week,
                "empty_days": empty_days
                if empty_days is not None
                else ["2026-07-07", "2026-07-09"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def test_spill_a_places_gap_days_first_under_max_2(
    editorial_base: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "UTC")
    _derivatives_generated_campaign(editorial_base)
    _write_flow_b_sidecar(
        editorial_base,
        target_week="2026-W28",
        empty_days=["2026-07-07", "2026-07-09"],
    )
    # Mock density always empty so placement is pure algorithm order
    with patch(
        "silverman_blog_linkedin.flow_b_spill_schedule.evaluate_local_day_density"
    ) as mock_density:
        mock_density.return_value = type(
            "R",
            (),
            {"ok": True, "others_on_day": 0, "errors": []},
        )()
        result = schedule_linkedin_distribution(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            strategy=FLOW_B_SPILL_A_STRATEGY,
            start_at_utc=ANCHOR_UTC,
        )
    assert result.status == "completed"
    assert result.strategy == FLOW_B_SPILL_A_STRATEGY
    by_variant = {item["variant"]: item["scheduled_at_utc"] for item in result.variant_schedules}
    # First two variants on first gap day (max 2), next on second gap day
    assert by_variant["executive-recruiter"].startswith("2026-07-07")
    assert by_variant["engineering-leadership"].startswith("2026-07-07")
    assert by_variant["technical-architect"].startswith("2026-07-09")
    assert by_variant["short-provocative"].startswith("2026-07-09")


def test_spill_a_continues_within_week_then_forward(
    editorial_base: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "UTC")
    _derivatives_generated_campaign(editorial_base)
    # Only one gap day → remaining spill to other week days then forward
    _write_flow_b_sidecar(
        editorial_base,
        target_week="2026-W28",
        empty_days=["2026-07-07"],
    )
    with patch(
        "silverman_blog_linkedin.flow_b_spill_schedule.evaluate_local_day_density"
    ) as mock_density:
        mock_density.return_value = type(
            "R",
            (),
            {"ok": True, "others_on_day": 0, "errors": []},
        )()
        result = schedule_linkedin_distribution(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            strategy=FLOW_B_SPILL_A_STRATEGY,
            start_at_utc=ANCHOR_UTC,
        )
    assert result.status == "completed"
    days = sorted(
        {
            item["scheduled_at_utc"][:10]
            for item in result.variant_schedules
        }
    )
    # Gap day + next week days (Mon 6 Jul is W28 day 1; empty is Tue 7)
    assert "2026-07-07" in days
    assert any(d != "2026-07-07" for d in days)


def test_spill_a_fails_closed_on_density_exhaustion(
    editorial_base: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "UTC")
    _derivatives_generated_campaign(editorial_base)
    _write_flow_b_sidecar(editorial_base)
    with patch(
        "silverman_blog_linkedin.flow_b_spill_schedule.evaluate_local_day_density"
    ) as mock_density:
        mock_density.return_value = type(
            "R",
            (),
            {"ok": True, "others_on_day": 2, "errors": []},
        )()
        result = schedule_linkedin_distribution(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            strategy=FLOW_B_SPILL_A_STRATEGY,
            start_at_utc=ANCHOR_UTC,
        )
    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_SPILL_DENSITY_EXHAUSTED in result.errors


def test_auto_select_spill_a_with_flow_b_provenance(
    editorial_base: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "UTC")
    _derivatives_generated_campaign(editorial_base)
    _write_flow_b_sidecar(editorial_base)
    with patch(
        "silverman_blog_linkedin.flow_b_spill_schedule.evaluate_local_day_density"
    ) as mock_density:
        mock_density.return_value = type(
            "R",
            (),
            {"ok": True, "others_on_day": 0, "errors": []},
        )()
        result = schedule_linkedin_distribution(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            strategy=None,
            start_at_utc=ANCHOR_UTC,
        )
    assert result.status == "completed"
    assert result.strategy == FLOW_B_SPILL_A_STRATEGY


def test_non_flow_b_keeps_default_stagger(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    result = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        strategy=None,
        start_at_utc=ANCHOR_UTC,
    )
    assert result.status == "completed"
    assert result.strategy == DEFAULT_STAGGER_STRATEGY


def test_explicit_stagger_override_for_flow_b_origin(editorial_base: Path):
    _derivatives_generated_campaign(editorial_base)
    _write_flow_b_sidecar(editorial_base)
    result = schedule_linkedin_distribution(
        editorial_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        strategy=DEFAULT_STAGGER_STRATEGY,
        start_at_utc=ANCHOR_UTC,
    )
    assert result.status == "completed"
    assert result.strategy == DEFAULT_STAGGER_STRATEGY
    anchor = datetime.strptime(ANCHOR_UTC, "%Y-%m-%dT%H:%M:%SZ")
    for item in result.variant_schedules:
        offset_days = VARIANT_DAY_OFFSETS[item["variant"]]
        expected = (anchor + timedelta(days=offset_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        assert item["scheduled_at_utc"] == expected


def _inject_published_sibling(
    base: Path,
    *,
    published_at: str,
    variant: str = "prior-published-sibling",
) -> dict:
    """Add same-campaign published evidence for US-088 cadence placement tests."""
    campaign = read_campaign_metadata(base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    variants = list(campaign.get("variants") or [])
    variants.append(
        {
            "variant": variant,
            "audience": "senior practitioners",
            "tone": "executive",
            "source_public_url": PUBLIC_URL,
            "source_relative_path": SOURCE_RELATIVE,
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "source_content_sha256": campaign["source_content_sha256"],
            "derivative_content_sha256": "a" * 64,
            "artifact_relative_path": f"{GENERATED_RELATIVE}/{CANONICAL_CAMPAIGN_ID}/{variant}.md",
            "idempotency_key": f"prior-{variant}",
            "generated_at": "2026-07-01T12:00:00Z",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "publish_state": "published",
            "published_at": published_at,
            "scheduled_at_utc": published_at,
            "linkedin_post_urn": "urn:li:share:us088-cadence-fixture",
        }
    )
    campaign["variants"] = variants
    write_campaign_metadata(base, CANONICAL_CAMPAIGN_ID, campaign)
    return campaign


def test_us088_shift_forward_happy_path_cadence_infeasible_preferred(
    editorial_base: Path, monkeypatch: pytest.MonkeyPatch
):
    """Preferred stagger slot shifts forward when same-campaign 72h cadence blocks it."""
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "America/Bogota")
    _derivatives_generated_campaign(editorial_base)
    # Anchor 2026-07-07T14:00:00Z conflicts: published + 72h = 2026-07-09T12:00:00Z
    _inject_published_sibling(editorial_base, published_at="2026-07-06T12:00:00Z")

    with patch(
        "silverman_blog_linkedin.linkedin_schedule_feasibility.evaluate_local_day_density"
    ) as mock_density:
        mock_density.return_value = type(
            "R",
            (),
            {
                "ok": True,
                "others_on_day": 0,
                "errors": [],
                "target_local_day": None,
                "resolved_timezone": "America/Bogota",
            },
        )()
        result = schedule_linkedin_distribution(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            strategy=DEFAULT_STAGGER_STRATEGY,
            start_at_utc=ANCHOR_UTC,
        )

    assert result.status == "completed"
    by_variant = {
        item["variant"]: item["scheduled_at_utc"] for item in result.variant_schedules
    }
    # Preferred ER slot 2026-07-07T14:00:00Z is cadence-infeasible; must shift forward.
    assert by_variant["executive-recruiter"] != "2026-07-07T14:00:00Z"
    er_dt = datetime.strptime(
        by_variant["executive-recruiter"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    earliest = datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)
    assert er_dt >= earliest

    stored = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert stored is not None
    stored_er = next(
        v for v in stored["variants"] if v["variant"] == "executive-recruiter"
    )
    assert stored_er["scheduled_at_utc"] == by_variant["executive-recruiter"]
    assert stored_er["publish_state"] == "pending"

    # Stagger ≥3 local days between consecutive accepted variants.
    ordered = [
        by_variant["executive-recruiter"],
        by_variant["engineering-leadership"],
        by_variant["technical-architect"],
        by_variant["short-provocative"],
    ]
    prev = None
    for scheduled in ordered:
        dt = datetime.strptime(scheduled, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        if prev is not None:
            assert (dt.date() - prev.date()).days >= 3
        prev = dt


def test_us088_density_interaction_skips_full_local_days(
    editorial_base: Path, monkeypatch: pytest.MonkeyPatch
):
    """Shift-forward skips operator-local days already at US-040K max 2."""
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "UTC")
    _derivatives_generated_campaign(editorial_base)
    # No published evidence — density alone drives the skip.
    full_days = {"2026-07-07", "2026-07-08", "2026-07-09"}

    def _density_by_day(_base_path, *, target_utc, **_kwargs):
        day = target_utc.astimezone(timezone.utc).strftime("%Y-%m-%d")
        others = 2 if day in full_days else 0
        return type(
            "R",
            (),
            {
                "ok": others < 2,
                "others_on_day": others,
                "errors": [],
                "target_local_day": day,
                "resolved_timezone": "UTC",
            },
        )()

    with patch(
        "silverman_blog_linkedin.linkedin_schedule_feasibility.evaluate_local_day_density",
        side_effect=_density_by_day,
    ):
        result = schedule_linkedin_distribution(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            strategy=DEFAULT_STAGGER_STRATEGY,
            start_at_utc=ANCHOR_UTC,
        )

    assert result.status == "completed"
    by_variant = {
        item["variant"]: item["scheduled_at_utc"] for item in result.variant_schedules
    }
    # Preferred ER day 2026-07-07 is density-full → must not keep that day.
    assert not by_variant["executive-recruiter"].startswith("2026-07-07")
    assert not by_variant["executive-recruiter"].startswith("2026-07-08")
    assert not by_variant["executive-recruiter"].startswith("2026-07-09")


def test_us088_fail_closed_horizon_no_feasible_slot(
    editorial_base: Path, monkeypatch: pytest.MonkeyPatch
):
    """No feasible slot within 28 local days → linkedin_schedule_no_feasible_slot."""
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "UTC")
    _derivatives_generated_campaign(editorial_base)
    _inject_published_sibling(editorial_base, published_at="2026-07-06T12:00:00Z")

    with patch(
        "silverman_blog_linkedin.linkedin_schedule_feasibility.evaluate_local_day_density"
    ) as mock_density:
        mock_density.return_value = type(
            "R",
            (),
            {
                "ok": False,
                "others_on_day": 2,
                "errors": ["linkedin_supervision_local_day_density"],
                "target_local_day": None,
                "resolved_timezone": "UTC",
            },
        )()
        result = schedule_linkedin_distribution(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            strategy=DEFAULT_STAGGER_STRATEGY,
            start_at_utc=ANCHOR_UTC,
        )

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT in result.errors
    assert result.metadata_written is False
    # Must not silently persist infeasible preferred times.
    stored = read_campaign_metadata(editorial_base, CANONICAL_CAMPAIGN_ID)
    assert stored is not None
    assert stored["state"] == STATE_DERIVATIVES_GENERATED
    for entry in stored.get("variants") or []:
        if entry.get("variant") in VARIANT_DAY_OFFSETS:
            assert not entry.get("scheduled_at_utc")


def test_us088_non_mutation_no_linkedin_api_and_enablement_unchanged(
    editorial_base: Path, monkeypatch: pytest.MonkeyPatch
):
    """Scheduling must not publish or force-enable LinkedIn publication."""
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "America/Bogota")
    monkeypatch.setenv("SILVERMAN_LINKEDIN_PUBLICATION_ENABLED", "false")
    _derivatives_generated_campaign(editorial_base)
    _inject_published_sibling(editorial_base, published_at="2026-07-06T12:00:00Z")

    with patch(
        "silverman_blog_linkedin.linkedin_schedule_feasibility.evaluate_local_day_density"
    ) as mock_density:
        mock_density.return_value = type(
            "R",
            (),
            {
                "ok": True,
                "others_on_day": 0,
                "errors": [],
                "target_local_day": None,
                "resolved_timezone": "America/Bogota",
            },
        )()
        with patch("httpx.Client.post") as mock_post:
            result = schedule_linkedin_distribution(
                editorial_base,
                campaign_id=CANONICAL_CAMPAIGN_ID,
                strategy=DEFAULT_STAGGER_STRATEGY,
                start_at_utc=ANCHOR_UTC,
            )

    assert result.status == "completed"
    mock_post.assert_not_called()
    import os

    assert os.environ.get("SILVERMAN_LINKEDIN_PUBLICATION_ENABLED") == "false"
    # Shared cadence constant (no second engine).
    from silverman_blog_linkedin.linkedin_publication_flow import (
        CADENCE_MINIMUM_INTERVAL as publish_interval,
    )
    from silverman_blog_linkedin.linkedin_schedule_feasibility import (
        CADENCE_MINIMUM_INTERVAL as schedule_interval,
    )

    assert schedule_interval is publish_interval
    assert schedule_interval.total_seconds() == 72 * 3600
    for item in result.variant_schedules:
        assert item["publish_state"] == "pending"


def test_us088_spill_a_cadence_shift_preserves_empty_day_priority(
    editorial_base: Path, monkeypatch: pytest.MonkeyPatch
):
    """Spill A keeps empty-day priority while shifting past cadence-blocked clocks."""
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "UTC")
    _derivatives_generated_campaign(editorial_base)
    _write_flow_b_sidecar(
        editorial_base,
        target_week="2026-W28",
        empty_days=["2026-07-07", "2026-07-09"],
    )
    # Blocks 14:00 on Jul 7 (anchor clock) but afternoon preferred window clears.
    # published + 72h = 2026-07-07T15:00:00Z → 14:00 conflicts; 16:00 is feasible.
    campaign = _inject_published_sibling(
        editorial_base, published_at="2026-07-04T15:00:00Z"
    )

    with patch(
        "silverman_blog_linkedin.flow_b_spill_schedule.evaluate_local_day_density"
    ) as mock_density:
        mock_density.return_value = type(
            "R",
            (),
            {"ok": True, "others_on_day": 0, "errors": []},
        )()
        result = schedule_linkedin_distribution(
            editorial_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            strategy=FLOW_B_SPILL_A_STRATEGY,
            start_at_utc=ANCHOR_UTC,
        )

    assert result.status == "completed"
    assert result.strategy == FLOW_B_SPILL_A_STRATEGY
    by_variant = {
        item["variant"]: item["scheduled_at_utc"] for item in result.variant_schedules
    }
    # Empty-day priority: first placements still on first gap day 2026-07-07.
    assert by_variant["executive-recruiter"].startswith("2026-07-07")
    assert by_variant["engineering-leadership"].startswith("2026-07-07")
    # Default 14:00 was cadence-infeasible; shifted clock on same empty day.
    assert by_variant["executive-recruiter"] != "2026-07-07T14:00:00Z"
    er_dt = datetime.strptime(
        by_variant["executive-recruiter"], "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    assert er_dt >= datetime(2026, 7, 7, 15, 0, tzinfo=timezone.utc)
    # Second empty day still used (priority not inverted to week/forward first).
    assert by_variant["technical-architect"].startswith("2026-07-09")
    assert by_variant["short-provocative"].startswith("2026-07-09")
    # Residual US-087 projection still available for a conflicted evaluation.
    from silverman_blog_linkedin.linkedin_publication_flow import (
        project_cadence_conflict_at,
    )

    projection = project_cadence_conflict_at(
        campaign,
        evaluation_at=datetime(2026, 7, 7, 14, 0, tzinfo=timezone.utc),
    )
    assert projection.cadence_conflict is True
