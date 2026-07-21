"""Behavioral tests for US-089 cadence-conflict replan."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.campaign_lifecycle import (
    read_campaign_metadata,
    write_campaign_metadata,
)
from silverman_blog_linkedin.linkedin_cadence_replan import (
    LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT,
    OUTCOME_MOVED,
    OUTCOME_SKIPPED_NOT_CONFLICTED,
    SUPERVISION_ACTION_REPLAN_CADENCE,
    replan_linkedin_cadence_conflicts,
)
from silverman_blog_linkedin.linkedin_publication_flow import (
    CADENCE_MINIMUM_INTERVAL,
    PUBLISH_STATE_PENDING,
    PUBLISH_STATE_QUEUED,
    project_cadence_conflict_at,
)
from silverman_blog_linkedin.linkedin_schedule_feasibility import (
    CADENCE_MINIMUM_INTERVAL as SCHEDULE_CADENCE_INTERVAL,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings
from tests.test_linkedin_publication import (
    CANONICAL_CAMPAIGN_ID,
    SECOND_VARIANT,
    TARGET_VARIANT,
    _distribution_scheduled_campaign,
    _queue_variant,
    _setup_metadata_campaigns,
    _update_variant,
)


CONFLICTED_SCHEDULE = "2026-07-07T14:00:00Z"
FEASIBLE_SIBLING_SCHEDULE = "2026-07-12T15:00:00Z"
PUBLISHED_AT = "2026-07-06T12:00:00Z"  # +72h → 2026-07-09T12:00:00Z


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    _setup_metadata_campaigns(tmp_path)
    (tmp_path / "linkedin-posts").mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.fixture
def scheduled_base(editorial_base: Path) -> Path:
    _distribution_scheduled_campaign(editorial_base)
    return editorial_base


def _inject_published_sibling(
    base: Path,
    *,
    published_at: str = PUBLISHED_AT,
    variant: str = "prior-published-sibling",
) -> None:
    campaign = read_campaign_metadata(base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    variants = list(campaign.get("variants") or [])
    variants.append(
        {
            "variant": variant,
            "audience": "senior practitioners",
            "tone": "executive",
            "campaign_id": CANONICAL_CAMPAIGN_ID,
            "source_content_sha256": campaign["source_content_sha256"],
            "derivative_content_sha256": "a" * 64,
            "artifact_relative_path": (
                f"linkedin-posts/generated/{CANONICAL_CAMPAIGN_ID}/{variant}.md"
            ),
            "idempotency_key": f"prior-{variant}",
            "generated_at": "2026-07-01T12:00:00Z",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "publish_state": "published",
            "published_at": published_at,
            "scheduled_at_utc": published_at,
            "linkedin_post_urn": "urn:li:share:us089-cadence-fixture",
        }
    )
    campaign["variants"] = variants
    write_campaign_metadata(base, CANONICAL_CAMPAIGN_ID, campaign)


def _seed_conflict_and_feasible_sibling(base: Path) -> None:
    """Conflicted TARGET + feasible SECOND under same published evidence."""
    _inject_published_sibling(base)
    _update_variant(
        base,
        TARGET_VARIANT,
        scheduled_at_utc=CONFLICTED_SCHEDULE,
        publish_state=PUBLISH_STATE_PENDING,
    )
    _update_variant(
        base,
        SECOND_VARIANT,
        scheduled_at_utc=FEASIBLE_SIBLING_SCHEDULE,
        publish_state=PUBLISH_STATE_PENDING,
    )


def _open_density():
    return patch(
        "silverman_blog_linkedin.linkedin_schedule_feasibility.evaluate_local_day_density",
        return_value=type(
            "R",
            (),
            {
                "ok": True,
                "others_on_day": 0,
                "errors": [],
                "target_local_day": None,
                "resolved_timezone": "America/Bogota",
            },
        )(),
    )


def test_us089_conflicted_pending_shifts_forward(scheduled_base: Path, monkeypatch):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "America/Bogota")
    _seed_conflict_and_feasible_sibling(scheduled_base)

    before = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert before is not None
    conflict_dt = datetime.strptime(
        CONFLICTED_SCHEDULE, "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    assert project_cadence_conflict_at(
        before, evaluation_at=conflict_dt
    ).cadence_conflict

    with _open_density():
        result = replan_linkedin_cadence_conflicts(
            scheduled_base,
            dry_run=False,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            environ=os.environ,
        )

    assert result.status == "completed"
    assert result.metadata_written is True
    moved = next(
        t
        for t in result.targets
        if t.variant_id == TARGET_VARIANT and t.outcome == OUTCOME_MOVED
    )
    assert moved.previous_scheduled_at_utc == CONFLICTED_SCHEDULE
    assert moved.proposed_scheduled_at_utc is not None
    assert moved.proposed_scheduled_at_utc != CONFLICTED_SCHEDULE
    new_dt = datetime.strptime(
        moved.proposed_scheduled_at_utc, "%Y-%m-%dT%H:%M:%SZ"
    ).replace(tzinfo=timezone.utc)
    assert new_dt >= datetime(2026, 7, 9, 12, 0, tzinfo=timezone.utc)

    stored = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert stored is not None
    entry = next(v for v in stored["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["scheduled_at_utc"] == moved.proposed_scheduled_at_utc
    assert entry["publish_state"] == PUBLISH_STATE_PENDING
    supervision = entry["operator_supervision"]
    assert supervision["last_action"] == SUPERVISION_ACTION_REPLAN_CADENCE
    assert any(
        isinstance(h, dict) and h.get("action") == SUPERVISION_ACTION_REPLAN_CADENCE
        for h in supervision.get("deferral_history") or []
    )


def test_us089_feasible_sibling_not_needlessly_moved(scheduled_base: Path, monkeypatch):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "America/Bogota")
    _seed_conflict_and_feasible_sibling(scheduled_base)

    with _open_density():
        result = replan_linkedin_cadence_conflicts(
            scheduled_base,
            dry_run=False,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            environ=os.environ,
        )

    assert result.status == "completed"
    moved_ids = {t.variant_id for t in result.targets if t.outcome == OUTCOME_MOVED}
    assert TARGET_VARIANT in moved_ids
    assert SECOND_VARIANT not in moved_ids

    stored = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert stored is not None
    sibling = next(v for v in stored["variants"] if v["variant"] == SECOND_VARIANT)
    assert sibling["scheduled_at_utc"] == FEASIBLE_SIBLING_SCHEDULE


def test_us089_queued_keeps_queued_and_aligns_publish_after(
    scheduled_base: Path, monkeypatch
):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "America/Bogota")
    _inject_published_sibling(scheduled_base)
    _update_variant(
        scheduled_base,
        TARGET_VARIANT,
        scheduled_at_utc=CONFLICTED_SCHEDULE,
        publish_state=PUBLISH_STATE_PENDING,
    )
    _queue_variant(
        scheduled_base,
        variant=TARGET_VARIANT,
        publish_after_utc=CONFLICTED_SCHEDULE,
    )
    _update_variant(
        scheduled_base,
        TARGET_VARIANT,
        scheduled_at_utc=CONFLICTED_SCHEDULE,
        publish_after_utc=CONFLICTED_SCHEDULE,
    )

    before = next(
        v
        for v in read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)["variants"]
        if v["variant"] == TARGET_VARIANT
    )
    assert before["publish_state"] == PUBLISH_STATE_QUEUED

    with _open_density():
        result = replan_linkedin_cadence_conflicts(
            scheduled_base,
            dry_run=False,
            targets=[
                {
                    "campaign_id": CANONICAL_CAMPAIGN_ID,
                    "variant_id": TARGET_VARIANT,
                }
            ],
            environ=os.environ,
        )

    assert result.status == "completed"
    entry = next(
        v
        for v in read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)["variants"]
        if v["variant"] == TARGET_VARIANT
    )
    assert entry["publish_state"] == PUBLISH_STATE_QUEUED
    assert entry["scheduled_at_utc"] != CONFLICTED_SCHEDULE
    assert entry["publish_after_utc"] == entry["scheduled_at_utc"]


def test_us089_dry_run_default_does_not_mutate(scheduled_base: Path, monkeypatch):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "America/Bogota")
    _seed_conflict_and_feasible_sibling(scheduled_base)
    before = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert before is not None
    before_blob = json.dumps(before, sort_keys=True)

    with _open_density():
        # Omit dry_run → default true
        result = replan_linkedin_cadence_conflicts(
            scheduled_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            environ=os.environ,
        )

    assert result.status == "completed"
    assert result.dry_run is True
    assert result.metadata_written is False
    assert any(t.outcome == OUTCOME_MOVED for t in result.targets)

    after = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert after is not None
    assert json.dumps(after, sort_keys=True) == before_blob


def test_us089_horizon_fail_closed_no_silent_keep(scheduled_base: Path, monkeypatch):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "UTC")
    _seed_conflict_and_feasible_sibling(scheduled_base)

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
        result = replan_linkedin_cadence_conflicts(
            scheduled_base,
            dry_run=False,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            environ=os.environ,
        )

    assert result.status == "failed"
    assert LINKEDIN_SCHEDULE_NO_FEASIBLE_SLOT in result.errors
    assert result.metadata_written is False
    stored = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert stored is not None
    entry = next(v for v in stored["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["scheduled_at_utc"] == CONFLICTED_SCHEDULE


def test_us089_selection_parity_and_no_publish_or_enablement(
    scheduled_base: Path, monkeypatch
):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "America/Bogota")
    monkeypatch.setenv("SILVERMAN_LINKEDIN_PUBLICATION_ENABLED", "false")
    assert CADENCE_MINIMUM_INTERVAL == SCHEDULE_CADENCE_INTERVAL
    _seed_conflict_and_feasible_sibling(scheduled_base)

    with _open_density():
        with patch("httpx.Client.post") as mock_post:
            result = replan_linkedin_cadence_conflicts(
                scheduled_base,
                dry_run=False,
                campaign_id=CANONICAL_CAMPAIGN_ID,
                environ=dict(os.environ),
            )
            mock_post.assert_not_called()

    assert result.status == "completed"
    assert os.environ.get("SILVERMAN_LINKEDIN_PUBLICATION_ENABLED") == "false"

    # Density-full alone must not select when cadence is clear.
    _update_variant(
        scheduled_base,
        TARGET_VARIANT,
        scheduled_at_utc=FEASIBLE_SIBLING_SCHEDULE,
        publish_state=PUBLISH_STATE_PENDING,
    )
    # Remove published evidence so no cadence conflict remains.
    campaign = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert campaign is not None
    campaign["variants"] = [
        v
        for v in campaign["variants"]
        if v.get("variant") != "prior-published-sibling"
    ]
    write_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID, campaign)

    with _open_density():
        empty = replan_linkedin_cadence_conflicts(
            scheduled_base,
            dry_run=True,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            environ=os.environ,
        )
    assert empty.status == "completed"
    assert not any(t.outcome == OUTCOME_MOVED for t in empty.targets)


def test_us089_explicit_target_skips_non_conflict(scheduled_base: Path, monkeypatch):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "America/Bogota")
    _seed_conflict_and_feasible_sibling(scheduled_base)

    with _open_density():
        result = replan_linkedin_cadence_conflicts(
            scheduled_base,
            dry_run=True,
            targets=[
                {
                    "campaign_id": CANONICAL_CAMPAIGN_ID,
                    "variant_id": SECOND_VARIANT,
                }
            ],
            environ=os.environ,
        )

    assert result.status == "completed"
    assert len(result.targets) == 1
    assert result.targets[0].outcome == OUTCOME_SKIPPED_NOT_CONFLICTED
    assert result.targets[0].previous_scheduled_at_utc == FEASIBLE_SIBLING_SCHEDULE


def test_us089_http_requires_auth_and_dry_run_default(scheduled_base: Path, monkeypatch):
    monkeypatch.setenv("SILVERMAN_OPERATOR_TIMEZONE", "America/Bogota")
    _seed_conflict_and_feasible_sibling(scheduled_base)
    client = TestClient(create_app(make_settings(scheduled_base)))

    unauth = client.post("/replan-linkedin-cadence-conflicts", json={})
    assert unauth.status_code == 401
    stored = read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)
    assert stored is not None
    entry = next(v for v in stored["variants"] if v["variant"] == TARGET_VARIANT)
    assert entry["scheduled_at_utc"] == CONFLICTED_SCHEDULE

    with _open_density():
        preview = client.post(
            "/replan-linkedin-cadence-conflicts",
            headers=auth_header(),
            json={"campaign_id": CANONICAL_CAMPAIGN_ID},
        )
    assert preview.status_code == 200
    body = preview.json()
    assert body["dry_run"] is True
    assert body["metadata_written"] is False
    assert body["status"] == "completed"
    assert any(
        t["variant_id"] == TARGET_VARIANT and t["outcome"] == OUTCOME_MOVED
        for t in body["targets"]
    )

    entry_after = next(
        v
        for v in read_campaign_metadata(scheduled_base, CANONICAL_CAMPAIGN_ID)["variants"]
        if v["variant"] == TARGET_VARIANT
    )
    assert entry_after["scheduled_at_utc"] == CONFLICTED_SCHEDULE

    with _open_density():
        real = client.post(
            "/replan-linkedin-cadence-conflicts",
            headers=auth_header(),
            json={"campaign_id": CANONICAL_CAMPAIGN_ID, "dry_run": False},
        )
    assert real.status_code == 200
    real_body = real.json()
    assert real_body["status"] == "completed"
    assert real_body["dry_run"] is False
    assert real_body["metadata_written"] is True
