"""Behavioral tests for Flow A incomplete-campaign recovery (US-031)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.campaign_lifecycle import (
    CANONICAL_VARIANT_IDS,
    EXECUTION_STATE_IDLE,
    EXECUTION_STATE_PROCESSING,
    EXECUTION_STATE_STALE,
    PHYSICAL_MOVE_STATE_PARTIAL,
    RECOVERY_MANUAL_INTERVENTION_REQUIRED,
    RECOVERY_NO_ACTION,
    RECOVERY_REPAIR_REQUIRED,
    RECOVERY_REQUEUE_REQUIRED,
    RECOVERY_RETRYABLE,
    SOURCE_LOCATION_ERROR,
    SOURCE_LOCATION_QUEUED,
    SOURCE_LOCATION_READY,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_GENERATED,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    STATE_READY,
    STATE_VALIDATED,
    read_campaign_metadata,
)
from silverman_blog_linkedin.flow_a_incomplete_campaign_recovery import (
    REASON_ACTIVE_CLAIM,
    REASON_ALREADY_COMPLETE,
    REASON_CAMPAIGN_NOT_FOUND,
    REASON_REQUEUE_REQUIRED,
    REASON_REPAIR_AMBIGUOUS_LOCATION,
    REASON_REPAIR_INVENT_SUCCESS,
    derive_last_valid_stage,
    inspect_incomplete_campaign_recovery,
    repair_incomplete_campaign_recovery,
    resume_incomplete_campaign_recovery,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

CAMPAIGN_ID = "flow-a-2026-07-18-recovery-demo"
SOURCE_SLUG = "recovery-demo"
SOURCE_MARKDOWN = "# Recovery demo\n\nBody.\n"


@pytest.fixture
def recovery_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    for relative in (
        "metadata/runs",
        "metadata/campaigns",
        "editorial-calendar",
        "blog-posts/ready",
        "blog-posts/queued",
        "blog-posts/processed",
        "blog-posts/error",
        "linkedin-posts/review",
        "linkedin-posts/approved",
        "linkedin-posts/published",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    return base


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _source_hash(content: str = SOURCE_MARKDOWN) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _variant_entries(*, scheduled: bool = False) -> list[dict]:
    entries = []
    for variant_id in sorted(CANONICAL_VARIANT_IDS):
        entry = {
            "variant": variant_id,
            "artifact_relative_path": (
                f"linkedin-posts/review/{CAMPAIGN_ID}-{variant_id}.md"
            ),
            "derivative_content_sha256": f"hash-{variant_id}",
            "publish_state": "pending",
        }
        if scheduled:
            entry["scheduled_at_utc"] = "2026-07-20T12:00:00Z"
            entry["schedule_idempotency_key"] = f"sched-{variant_id}"
        entries.append(entry)
    return entries


def _write_campaign(
    base: Path,
    campaign_id: str = CAMPAIGN_ID,
    *,
    state: str = STATE_READY,
    source_status: dict | None = None,
    **extra: object,
) -> dict:
    payload: dict = {
        "campaign_id": campaign_id,
        "flow": "flow_a",
        "state": state,
        "source_slug": SOURCE_SLUG,
        "source_content_sha256": _source_hash(),
        "source_relative_path": f"blog-posts/ready/{SOURCE_SLUG}.md",
        "source_file_status": source_status
        or {
            "location": SOURCE_LOCATION_READY,
            "execution_state": EXECUTION_STATE_IDLE,
            "recovery_classification": RECOVERY_NO_ACTION,
            "physical_move_state": "none",
        },
        "variants": [],
        "state_history": [],
        **extra,
    }
    _write_json(base / "metadata/campaigns" / f"{campaign_id}.json", payload)
    return payload


def _snapshot_tree(base: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(base)): path.read_bytes()
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def _blog_published_fields() -> dict:
    return {
        "source_public_url": "https://example.com/posts/recovery-demo/",
        "blog_publish": {
            "status": "published",
            "idempotency_key": "blog:recovery-demo:recovery-demo:2026-07-18:abc",
        },
        "state_history": [
            {
                "to_state": STATE_VALIDATED,
                "from_state": STATE_READY,
                "at": "2026-07-18T10:00:00Z",
            },
            {
                "to_state": STATE_BLOG_PUBLISHED,
                "from_state": "blog_publish_pending",
                "at": "2026-07-18T10:05:00Z",
            },
        ],
    }


def _package_fields() -> dict:
    return {
        "linkedin_package": {
            "idempotency_key": "pkg-key",
            "variant_ids": sorted(CANONICAL_VARIANT_IDS),
        },
        "variants": _variant_entries(),
    }


def _schedule_fields() -> dict:
    blog = _blog_published_fields()
    package = _package_fields()
    return {
        **blog,
        **package,
        "linkedin_distribution": {
            "idempotency_key": "sched-key",
            "anchor_utc": "2026-07-20T12:00:00Z",
            "variant_ids": sorted(CANONICAL_VARIANT_IDS),
        },
        "variants": _variant_entries(scheduled=True),
        "state_history": [
            {"to_state": STATE_VALIDATED, "at": "2026-07-18T10:00:00Z"},
            {"to_state": STATE_BLOG_PUBLISHED, "at": "2026-07-18T10:05:00Z"},
            {"to_state": STATE_DERIVATIVES_GENERATED, "at": "2026-07-18T10:10:00Z"},
            {"to_state": STATE_DISTRIBUTION_SCHEDULED, "at": "2026-07-18T10:15:00Z"},
        ],
    }


def test_derive_ready_and_validated(recovery_base: Path):
    ready = _write_campaign(recovery_base, state=STATE_READY)
    assert derive_last_valid_stage(ready).last_valid_stage == STATE_READY

    validated = _write_campaign(
        recovery_base,
        state=STATE_VALIDATED,
        validation={"status": "passed"},
        state_history=[{"to_state": STATE_VALIDATED, "at": "2026-07-18T10:00:00Z"}],
    )
    result = derive_last_valid_stage(validated)
    assert result.ambiguous is False
    assert result.last_valid_stage == STATE_VALIDATED


def test_derive_blog_published_and_pending_excluded(recovery_base: Path):
    campaign = _write_campaign(
        recovery_base,
        state=STATE_BLOG_PUBLISHED,
        **_blog_published_fields(),
    )
    result = derive_last_valid_stage(campaign)
    assert result.last_valid_stage == STATE_BLOG_PUBLISHED

    pending = _write_campaign(
        recovery_base,
        "flow-a-2026-07-18-pending",
        state="blog_publish_pending",
        validation={"status": "passed"},
        state_history=[{"to_state": STATE_VALIDATED, "at": "2026-07-18T10:00:00Z"}],
    )
    pending_result = derive_last_valid_stage(pending)
    assert pending_result.last_valid_stage == STATE_VALIDATED
    assert pending_result.last_valid_stage != "blog_publish_pending"


def test_derive_derivatives_and_scheduled(recovery_base: Path):
    blog = _blog_published_fields()
    blog.pop("state_history", None)
    packaged = _write_campaign(
        recovery_base,
        state=STATE_DERIVATIVES_GENERATED,
        **blog,
        **_package_fields(),
        state_history=[
            {"to_state": STATE_VALIDATED, "at": "2026-07-18T10:00:00Z"},
            {"to_state": STATE_BLOG_PUBLISHED, "at": "2026-07-18T10:05:00Z"},
            {"to_state": STATE_DERIVATIVES_GENERATED, "at": "2026-07-18T10:10:00Z"},
        ],
    )
    assert (
        derive_last_valid_stage(packaged).last_valid_stage == STATE_DERIVATIVES_GENERATED
    )

    scheduled = _write_campaign(
        recovery_base,
        "flow-a-2026-07-18-scheduled",
        state=STATE_DISTRIBUTION_SCHEDULED,
        **_schedule_fields(),
    )
    assert (
        derive_last_valid_stage(scheduled).last_valid_stage
        == STATE_DISTRIBUTION_SCHEDULED
    )


def test_derive_ambiguous_publish_and_flow_a_complete(recovery_base: Path):
    ambiguous = _write_campaign(
        recovery_base,
        state=STATE_BLOG_PUBLISHED,
        blog_publish={"status": "failed"},
        state_history=[{"to_state": STATE_BLOG_PUBLISHED, "at": "2026-07-18T10:05:00Z"}],
    )
    result = derive_last_valid_stage(ambiguous)
    assert result.ambiguous is True

    complete = _write_campaign(
        recovery_base,
        "flow-a-2026-07-18-complete",
        state=STATE_FLOW_A_COMPLETE,
        **{k: v for k, v in _schedule_fields().items() if k != "state_history"},
        source_status={
            "location": "processed",
            "execution_state": EXECUTION_STATE_IDLE,
            "recovery_classification": RECOVERY_NO_ACTION,
            "physical_move_state": "completed",
        },
        processed_source_relative_path=f"blog-posts/processed/{SOURCE_SLUG}.md",
        state_history=[
            {"to_state": STATE_DISTRIBUTION_SCHEDULED, "at": "2026-07-18T10:15:00Z"},
            {"to_state": STATE_FLOW_A_COMPLETE, "at": "2026-07-18T10:20:00Z"},
        ],
    )
    complete_result = derive_last_valid_stage(complete)
    assert complete_result.ambiguous is False
    assert complete_result.last_valid_stage == STATE_FLOW_A_COMPLETE


def test_inspect_auth_401_and_not_found(recovery_base: Path):
    client = TestClient(create_app(make_settings(recovery_base)))
    assert (
        client.get(f"/flow-a/incomplete-campaign-recovery/{CAMPAIGN_ID}").status_code
        == 401
    )
    response = client.get(
        f"/flow-a/incomplete-campaign-recovery/{CAMPAIGN_ID}",
        headers=auth_header(),
    )
    assert response.status_code == 404
    body = response.json()["detail"]
    assert body["reason_code"] == REASON_CAMPAIGN_NOT_FOUND


def test_inspect_secret_exclusion_deterministic_and_byte_identical(recovery_base: Path):
    _write_campaign(
        recovery_base,
        state=STATE_BLOG_PUBLISHED,
        api_key="super-secret-token",
        markdown_content="# should not appear",
        draft_content="secret draft",
        **_blog_published_fields(),
    )
    (recovery_base / f"blog-posts/ready/{SOURCE_SLUG}.md").write_text(
        SOURCE_MARKDOWN, encoding="utf-8"
    )
    before = _snapshot_tree(recovery_base)
    client = TestClient(create_app(make_settings(recovery_base)))
    first = client.get(
        f"/flow-a/incomplete-campaign-recovery/{CAMPAIGN_ID}",
        headers=auth_header(),
    )
    second = client.get(
        f"/flow-a/incomplete-campaign-recovery/{CAMPAIGN_ID}",
        headers=auth_header(),
    )
    assert first.status_code == 200
    assert first.json() == second.json()
    payload = first.json()
    serialized = json.dumps(payload)
    assert "super-secret-token" not in serialized
    assert "should not appear" not in serialized
    assert "secret draft" not in serialized
    assert str(recovery_base.resolve()) not in serialized
    assert payload["last_valid_stage"] == STATE_BLOG_PUBLISHED
    assert payload["next_stage"] == "package"
    assert _snapshot_tree(recovery_base) == before

    service = inspect_incomplete_campaign_recovery(recovery_base, CAMPAIGN_ID)
    assert service.outcome == "ok"
    assert _snapshot_tree(recovery_base) == before


def test_resume_skips_published_and_scheduled_and_completed_noop(recovery_base: Path):
    _write_campaign(
        recovery_base,
        state=STATE_BLOG_PUBLISHED,
        source_status={
            "location": SOURCE_LOCATION_QUEUED,
            "execution_state": EXECUTION_STATE_IDLE,
            "recovery_classification": RECOVERY_RETRYABLE,
            "physical_move_state": "completed",
        },
        queued_source_relative_path=f"blog-posts/queued/{SOURCE_SLUG}.md",
        source_relative_path=f"blog-posts/queued/{SOURCE_SLUG}.md",
        **_blog_published_fields(),
    )
    (recovery_base / f"blog-posts/queued/{SOURCE_SLUG}.md").write_text(
        SOURCE_MARKDOWN, encoding="utf-8"
    )

    with (
        patch(
            "silverman_blog_linkedin.flow_a_incomplete_campaign_recovery.publish_blog_post"
        ) as publish,
        patch(
            "silverman_blog_linkedin.flow_a_incomplete_campaign_recovery.generate_linkedin_package"
        ) as package,
        patch(
            "silverman_blog_linkedin.flow_a_incomplete_campaign_recovery.schedule_linkedin_distribution"
        ) as schedule,
        patch(
            "silverman_blog_linkedin.flow_a_incomplete_campaign_recovery.complete_flow_a_source_lifecycle"
        ) as lifecycle,
    ):
        package.return_value.status = "completed"
        package.return_value.errors = []
        schedule.return_value.status = "completed"
        schedule.return_value.errors = []
        lifecycle.return_value.status = "completed"
        lifecycle.return_value.errors = []
        result = resume_incomplete_campaign_recovery(
            recovery_base, campaign_id=CAMPAIGN_ID
        )

    publish.assert_not_called()
    package.assert_called_once()
    schedule.assert_called_once()
    lifecycle.assert_called_once()
    assert result.outcome == "ok"
    skipped = [s for s in result.stages if s.stage == "publish"][0]
    assert skipped.intent == "skip_already_complete"

    scheduled_id = "flow-a-2026-07-18-already-sched"
    _write_campaign(
        recovery_base,
        scheduled_id,
        state=STATE_DISTRIBUTION_SCHEDULED,
        source_status={
            "location": SOURCE_LOCATION_QUEUED,
            "execution_state": EXECUTION_STATE_IDLE,
            "recovery_classification": RECOVERY_RETRYABLE,
            "physical_move_state": "completed",
        },
        queued_source_relative_path=f"blog-posts/queued/{SOURCE_SLUG}.md",
        **_schedule_fields(),
    )
    with (
        patch(
            "silverman_blog_linkedin.flow_a_incomplete_campaign_recovery.schedule_linkedin_distribution"
        ) as schedule2,
        patch(
            "silverman_blog_linkedin.flow_a_incomplete_campaign_recovery.complete_flow_a_source_lifecycle"
        ) as lifecycle2,
        patch(
            "silverman_blog_linkedin.flow_a_incomplete_campaign_recovery.publish_blog_post"
        ) as publish2,
        patch(
            "silverman_blog_linkedin.flow_a_incomplete_campaign_recovery.generate_linkedin_package"
        ) as package2,
    ):
        lifecycle2.return_value.status = "skipped"
        lifecycle2.return_value.errors = []
        result2 = resume_incomplete_campaign_recovery(
            recovery_base, campaign_id=scheduled_id
        )
    publish2.assert_not_called()
    package2.assert_not_called()
    schedule2.assert_not_called()
    lifecycle2.assert_called_once()
    assert result2.outcome == "ok"

    complete_id = "flow-a-2026-07-18-done"
    _write_campaign(
        recovery_base,
        complete_id,
        state=STATE_FLOW_A_COMPLETE,
        **{k: v for k, v in _schedule_fields().items() if k != "state_history"},
        source_status={
            "location": "processed",
            "execution_state": EXECUTION_STATE_IDLE,
            "recovery_classification": RECOVERY_NO_ACTION,
            "physical_move_state": "completed",
        },
        processed_source_relative_path=f"blog-posts/processed/{SOURCE_SLUG}.md",
        state_history=[
            {"to_state": STATE_DISTRIBUTION_SCHEDULED, "at": "2026-07-18T10:15:00Z"},
            {"to_state": STATE_FLOW_A_COMPLETE, "at": "2026-07-18T10:20:00Z"},
        ],
    )
    noop = resume_incomplete_campaign_recovery(
        recovery_base, campaign_id=complete_id
    )
    assert noop.outcome == "noop"
    assert noop.reason_code == REASON_ALREADY_COMPLETE


def test_resume_dry_run_zero_mutation_and_blocks(recovery_base: Path):
    _write_campaign(
        recovery_base,
        state=STATE_BLOG_PUBLISHED,
        source_status={
            "location": SOURCE_LOCATION_QUEUED,
            "execution_state": EXECUTION_STATE_IDLE,
            "recovery_classification": RECOVERY_RETRYABLE,
            "physical_move_state": "completed",
        },
        queued_source_relative_path=f"blog-posts/queued/{SOURCE_SLUG}.md",
        **_blog_published_fields(),
    )
    (recovery_base / f"blog-posts/queued/{SOURCE_SLUG}.md").write_text(
        SOURCE_MARKDOWN, encoding="utf-8"
    )
    before = _snapshot_tree(recovery_base)
    dry = resume_incomplete_campaign_recovery(
        recovery_base, campaign_id=CAMPAIGN_ID, dry_run=True
    )
    assert dry.dry_run is True
    assert dry.outcome == "ok"
    assert any(s.intent == "would_run" for s in dry.stages)
    assert _snapshot_tree(recovery_base) == before

    _write_campaign(
        recovery_base,
        "flow-a-2026-07-18-claimed",
        state=STATE_BLOG_PUBLISHED,
        source_status={
            "location": SOURCE_LOCATION_QUEUED,
            "execution_state": EXECUTION_STATE_PROCESSING,
            "recovery_classification": RECOVERY_MANUAL_INTERVENTION_REQUIRED,
            "physical_move_state": "completed",
            "last_progress_at": "2099-01-01T00:00:00Z",
        },
        **_blog_published_fields(),
    )
    blocked_claim = resume_incomplete_campaign_recovery(
        recovery_base, campaign_id="flow-a-2026-07-18-claimed"
    )
    assert blocked_claim.outcome == "blocked"
    assert blocked_claim.reason_code == REASON_ACTIVE_CLAIM
    assert (
        blocked_claim.recovery_classification
        == RECOVERY_MANUAL_INTERVENTION_REQUIRED
    )

    _write_campaign(
        recovery_base,
        "flow-a-2026-07-18-error",
        state=STATE_BLOG_PUBLISHED,
        source_status={
            "location": SOURCE_LOCATION_ERROR,
            "execution_state": EXECUTION_STATE_IDLE,
            "recovery_classification": RECOVERY_REQUEUE_REQUIRED,
            "physical_move_state": "completed",
        },
        error_source_relative_path=f"blog-posts/error/{SOURCE_SLUG}.md",
        **_blog_published_fields(),
    )
    blocked_error = resume_incomplete_campaign_recovery(
        recovery_base, campaign_id="flow-a-2026-07-18-error"
    )
    assert blocked_error.outcome == "blocked"
    assert blocked_error.reason_code == REASON_REQUEUE_REQUIRED
    assert blocked_error.recovery_classification == RECOVERY_REQUEUE_REQUIRED


def test_resume_partial_progress_on_mid_chain_failure(recovery_base: Path):
    _write_campaign(
        recovery_base,
        state=STATE_BLOG_PUBLISHED,
        source_status={
            "location": SOURCE_LOCATION_QUEUED,
            "execution_state": EXECUTION_STATE_IDLE,
            "recovery_classification": RECOVERY_RETRYABLE,
            "physical_move_state": "completed",
        },
        queued_source_relative_path=f"blog-posts/queued/{SOURCE_SLUG}.md",
        source_relative_path=f"blog-posts/queued/{SOURCE_SLUG}.md",
        **_blog_published_fields(),
    )
    (recovery_base / f"blog-posts/queued/{SOURCE_SLUG}.md").write_text(
        SOURCE_MARKDOWN, encoding="utf-8"
    )

    with (
        patch(
            "silverman_blog_linkedin.flow_a_incomplete_campaign_recovery.generate_linkedin_package"
        ) as package,
        patch(
            "silverman_blog_linkedin.flow_a_incomplete_campaign_recovery.schedule_linkedin_distribution"
        ) as schedule,
    ):
        package.return_value.status = "completed"
        package.return_value.errors = []
        schedule.return_value.status = "failed"
        schedule.return_value.errors = ["schedule_failed"]
        result = resume_incomplete_campaign_recovery(
            recovery_base, campaign_id=CAMPAIGN_ID
        )

    assert result.outcome == "partial"
    assert any(s.stage == "package" and s.status == "completed" for s in result.stages)
    assert any(s.stage == "schedule" and s.status == "failed" for s in result.stages)


def test_repair_location_sync_and_ambiguous_refusal(recovery_base: Path):
    _write_campaign(
        recovery_base,
        state=STATE_BLOG_PUBLISHED,
        source_status={
            "location": SOURCE_LOCATION_READY,
            "execution_state": EXECUTION_STATE_IDLE,
            "recovery_classification": RECOVERY_REPAIR_REQUIRED,
            "physical_move_state": "completed",
        },
        source_relative_path=f"blog-posts/ready/{SOURCE_SLUG}.md",
        **_blog_published_fields(),
    )
    queued = recovery_base / f"blog-posts/queued/{SOURCE_SLUG}.md"
    queued.write_text(SOURCE_MARKDOWN, encoding="utf-8")

    result = repair_incomplete_campaign_recovery(
        recovery_base,
        campaign_id=CAMPAIGN_ID,
        repair_action="sync_location_from_filesystem",
    )
    assert result.outcome == "ok"
    campaign = read_campaign_metadata(recovery_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_QUEUED
    assert campaign["blog_publish"]["status"] == "published"

    (recovery_base / f"blog-posts/ready/{SOURCE_SLUG}.md").write_text(
        SOURCE_MARKDOWN, encoding="utf-8"
    )
    ambiguous = repair_incomplete_campaign_recovery(
        recovery_base,
        campaign_id=CAMPAIGN_ID,
        repair_action="sync_location_from_filesystem",
    )
    assert ambiguous.outcome == "blocked"
    assert ambiguous.reason_code == REASON_REPAIR_AMBIGUOUS_LOCATION


def test_repair_invent_success_refused_stale_clear_partial_and_unknown_422(
    recovery_base: Path,
):
    _write_campaign(
        recovery_base,
        state=STATE_VALIDATED,
        validation={"status": "passed"},
        blog_publish={"status": "failed"},
        source_status={
            "location": SOURCE_LOCATION_QUEUED,
            "execution_state": EXECUTION_STATE_STALE,
            "recovery_classification": RECOVERY_RETRYABLE,
            "physical_move_state": PHYSICAL_MOVE_STATE_PARTIAL,
            "last_progress_at": "2020-01-01T00:00:00Z",
        },
        queued_source_relative_path=f"blog-posts/queued/{SOURCE_SLUG}.md",
        source_relative_path=f"blog-posts/queued/{SOURCE_SLUG}.md",
        original_image_relative_path=f"blog-posts/ready/{SOURCE_SLUG}.png",
        state_history=[{"to_state": STATE_VALIDATED, "at": "2026-07-18T10:00:00Z"}],
    )
    (recovery_base / f"blog-posts/queued/{SOURCE_SLUG}.md").write_text(
        SOURCE_MARKDOWN, encoding="utf-8"
    )
    (recovery_base / f"blog-posts/ready/{SOURCE_SLUG}.png").write_bytes(b"png")

    before_bp = read_campaign_metadata(recovery_base, CAMPAIGN_ID)["blog_publish"]
    clear = repair_incomplete_campaign_recovery(
        recovery_base,
        campaign_id=CAMPAIGN_ID,
        repair_action="clear_stale_execution_claim",
    )
    assert clear.outcome == "ok"
    after = read_campaign_metadata(recovery_base, CAMPAIGN_ID)
    assert after["source_file_status"]["execution_state"] == EXECUTION_STATE_IDLE
    assert after["blog_publish"] == before_bp

    after["source_file_status"]["physical_move_state"] = PHYSICAL_MOVE_STATE_PARTIAL
    after["source_file_status"]["execution_state"] = EXECUTION_STATE_IDLE
    _write_json(recovery_base / "metadata/campaigns" / f"{CAMPAIGN_ID}.json", after)
    (recovery_base / f"blog-posts/ready/{SOURCE_SLUG}.png").write_bytes(b"png")

    partial = repair_incomplete_campaign_recovery(
        recovery_base,
        campaign_id=CAMPAIGN_ID,
        repair_action="complete_partial_source_move",
    )
    assert partial.outcome in {"ok", "partial"}
    refreshed = read_campaign_metadata(recovery_base, CAMPAIGN_ID)
    assert refreshed["blog_publish"]["status"] == "failed"
    assert REASON_REPAIR_INVENT_SUCCESS.startswith("flow_a_recovery_repair_")

    client = TestClient(create_app(make_settings(recovery_base)))
    response = client.post(
        "/flow-a/incomplete-campaign-recovery/repair",
        headers=auth_header(),
        json={
            "campaign_id": CAMPAIGN_ID,
            "repair_action": "invent_blog_publish_success",
        },
    )
    assert response.status_code == 422


def test_operational_status_and_linkedin_routes_unchanged(recovery_base: Path):
    client = TestClient(create_app(make_settings(recovery_base)))
    status = client.get("/flow-a/operational-status", headers=auth_header())
    assert status.status_code == 200
    body = status.json()
    assert body["read_only"] is True
    assert "status" in body
    assert "campaigns" in body

    assert client.post("/queue-linkedin-publication", json={}).status_code == 401
    queued = client.post(
        "/queue-linkedin-publication",
        headers=auth_header(),
        json={},
    )
    assert queued.status_code == 422

    assert client.post("/publish-linkedin-due-variants", json={}).status_code == 401


def test_resume_http_validation_stop_after_stage(recovery_base: Path):
    _write_campaign(recovery_base, state=STATE_READY)
    client = TestClient(create_app(make_settings(recovery_base)))
    response = client.post(
        "/flow-a/incomplete-campaign-recovery/resume",
        headers=auth_header(),
        json={
            "campaign_id": CAMPAIGN_ID,
            "stop_after_stage": "not_a_milestone",
        },
    )
    assert response.status_code == 422
