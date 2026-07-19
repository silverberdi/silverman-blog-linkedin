"""Tests for Flow A calendar completion persistence."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from silverman_blog_linkedin.campaign_lifecycle import (
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_DERIVATIVES_GENERATED,
    STATE_FLOW_A_COMPLETE,
)
from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_COMPLETION_CONCURRENT_UPDATE,
    CALENDAR_COMPLETION_FACTS_CONFLICT,
    CALENDAR_COMPLETION_WRITE_FAILED,
    CALENDAR_ITEM_NOT_FOUND,
    CALENDAR_SCHEMA_INVALID,
    calendar_fingerprint,
    complete_flow_a_calendar_item,
    derive_flow_a_linkedin_completion_statuses,
    load_calendar,
    save_calendar_atomic,
    validate_calendar_document,
)
from tests.conftest import create_full_layout, inject_unvalidated_calendar, seed_editorial_calendar
from tests.test_editorial_calendar_flow_a_execute import (
    CAMPAIGN_ID,
    NOW_UTC,
    PAST_UTC,
    _base_calendar,
    _flow_a_item,
    _write_calendar,
    _write_flow_a_complete_campaign,
)


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    ready = base / "blog-posts" / "ready"
    (ready / "post.md").write_text("# Sample\n", encoding="utf-8")
    return base


def _completion_facts(**overrides) -> dict:
    facts = {
        "campaign_id": CAMPAIGN_ID,
        "completed_at_utc": "2026-07-10T12:00:00Z",
        "processed_source_relative_path": "blog-posts/processed/post.md",
        "flow_a_completion": {
            "campaign_state": "flow_a_complete",
            "execution_status": "executed",
            "source_lifecycle_status": "completed",
            "blog_publish_status": "completed",
            "public_url": "https://silverman.pro/post",
            "linkedin_package_status": "completed",
            "linkedin_distribution_status": "completed",
        },
    }
    facts.update(overrides)
    return facts


def test_save_calendar_atomic_updates_timestamp_and_preserves_other_items(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(item_id="due-flow-a"),
                _flow_a_item(item_id="other-item", due_at_utc="2026-12-01T14:00:00Z"),
            ]
        ),
    )
    calendar, _ = load_calendar(editorial_base)
    assert calendar is not None
    original_other = json.loads(json.dumps(calendar["items"][1]))

    calendar["items"][0]["status"] = "completed"
    errors = save_calendar_atomic(editorial_base, calendar)
    assert errors == []

    reloaded, load_errors = load_calendar(editorial_base)
    assert load_errors == []
    assert reloaded is not None
    assert reloaded["updated_at_utc"] != "2026-07-09T20:00:00Z"
    assert reloaded["items"][1] == original_other


def test_save_calendar_atomic_failure_leaves_original_intact(editorial_base: Path):
    path = _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    original = path.read_text(encoding="utf-8")
    invalid = _base_calendar(items=[_flow_a_item()])
    invalid["items"][0]["completed_at_utc"] = "not-a-timestamp"

    errors = save_calendar_atomic(editorial_base, invalid)
    assert CALENDAR_SCHEMA_INVALID in errors
    assert path.read_text(encoding="utf-8") == original


def test_complete_flow_a_calendar_item_sets_fields_and_preserves_notes(editorial_base: Path):
    calendar = _base_calendar(
        items=[
            _flow_a_item(
                notes="Immutable operator note.",
                source_relative_path="blog-posts/ready/post.md",
            )
        ]
    )
    result = complete_flow_a_calendar_item(
        calendar,
        item_id="due-flow-a",
        completion_facts=_completion_facts(),
    )
    assert result.requires_persist is True
    item = result.calendar["items"][0]
    assert item["status"] == "completed"
    assert item["source_relative_path"] == "blog-posts/ready/post.md"
    assert item["notes"] == "Immutable operator note."
    assert item["campaign_id"] == CAMPAIGN_ID
    assert item["processed_source_relative_path"] == "blog-posts/processed/post.md"


def test_complete_flow_a_calendar_item_missing_item(editorial_base: Path):
    calendar = _base_calendar(items=[_flow_a_item()])
    result = complete_flow_a_calendar_item(
        calendar,
        item_id="missing",
        completion_facts=_completion_facts(),
    )
    assert result.error_code == CALENDAR_ITEM_NOT_FOUND
    assert result.requires_persist is False


def test_completed_item_optional_fields_load(editorial_base: Path):
    item = _flow_a_item(status="completed")
    item.update(
        {
            "completed_at_utc": "2026-07-10T12:00:00Z",
            "processed_source_relative_path": "blog-posts/processed/post.md",
            "flow_a_completion": _completion_facts()["flow_a_completion"],
        }
    )
    _write_calendar(editorial_base, _base_calendar(items=[item]))
    calendar, errors = load_calendar(editorial_base)
    assert errors == []
    assert calendar is not None


def test_invalid_completed_at_utc_rejected(editorial_base: Path):
    item = _flow_a_item(status="completed")
    item["completed_at_utc"] = "2026-07-10T12:00:00"
    inject_unvalidated_calendar(_base_calendar(items=[item]))
    calendar, errors = load_calendar(editorial_base)
    assert calendar is None
    assert CALENDAR_SCHEMA_INVALID in errors


def test_equivalent_completed_item_is_no_op(editorial_base: Path):
    item = _flow_a_item(status="completed")
    item.update(
        {
            "campaign_id": CAMPAIGN_ID,
            "completed_at_utc": "2026-07-10T12:00:00Z",
            "processed_source_relative_path": "blog-posts/processed/post.md",
            "flow_a_completion": _completion_facts()["flow_a_completion"],
        }
    )
    calendar = _base_calendar(items=[item])
    result = complete_flow_a_calendar_item(
        calendar,
        item_id="due-flow-a",
        completion_facts=_completion_facts(),
    )
    assert result.requires_persist is False
    assert result.skipped_already_completed is True


def test_conflicting_terminal_facts_return_conflict(editorial_base: Path):
    item = _flow_a_item(status="completed")
    item.update(
        {
            "campaign_id": CAMPAIGN_ID,
            "completed_at_utc": "2026-07-10T12:00:00Z",
            "processed_source_relative_path": "blog-posts/processed/other.md",
            "flow_a_completion": _completion_facts()["flow_a_completion"],
        }
    )
    calendar = _base_calendar(items=[item])
    result = complete_flow_a_calendar_item(
        calendar,
        item_id="due-flow-a",
        completion_facts=_completion_facts(),
    )
    assert result.error_code == CALENDAR_COMPLETION_FACTS_CONFLICT
    assert result.requires_persist is False


def test_duplicate_item_ids_rejected(editorial_base: Path):
    calendar = _base_calendar(items=[_flow_a_item(), _flow_a_item(item_id="due-flow-a")])
    assert CALENDAR_SCHEMA_INVALID in validate_calendar_document(calendar)


def test_atomic_write_failure_preserves_original(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    before, _ = load_calendar(editorial_base)
    assert before is not None
    calendar = dict(before)
    calendar["items"] = list(before["items"])
    with patch(
        "silverman_blog_linkedin.editorial_calendar_store.MemoryCalendarStore.save",
        return_value=[CALENDAR_COMPLETION_WRITE_FAILED],
    ):
        errors = save_calendar_atomic(
            editorial_base,
            calendar,
            expected_fingerprint=calendar_fingerprint(editorial_base),
        )
    assert errors == [CALENDAR_COMPLETION_WRITE_FAILED]
    after, load_errors = load_calendar(editorial_base)
    assert load_errors == []
    assert after is not None
    assert after["items"][0]["status"] == "scheduled"


def test_save_calendar_atomic_succeeds_when_fingerprint_unchanged(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    calendar, _ = load_calendar(editorial_base)
    assert calendar is not None
    fingerprint = calendar_fingerprint(editorial_base)
    calendar["items"][0]["status"] = "completed"
    errors = save_calendar_atomic(
        editorial_base,
        calendar,
        expected_fingerprint=fingerprint,
    )
    assert errors == []


def test_concurrent_update_detected_when_calendar_changed_before_replace(editorial_base: Path):
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(),
                _flow_a_item(item_id="other-item", due_at_utc="2026-12-01T14:00:00Z"),
            ]
        ),
    )
    calendar, _ = load_calendar(editorial_base)
    assert calendar is not None
    fingerprint = calendar_fingerprint(editorial_base)
    calendar["items"][0]["status"] = "completed"

    external = _base_calendar(
        items=[
            _flow_a_item(),
            _flow_a_item(
                item_id="other-item",
                due_at_utc="2026-12-01T14:00:00Z",
            ),
        ]
    )
    external["items"][1]["title"] = "Externally modified title"
    seed_editorial_calendar(external)

    errors = save_calendar_atomic(
        editorial_base,
        calendar,
        expected_fingerprint=fingerprint,
    )
    assert errors == [CALENDAR_COMPLETION_CONCURRENT_UPDATE]
    reloaded, _ = load_calendar(editorial_base)
    assert reloaded is not None
    assert reloaded["items"][1]["title"] == "Externally modified title"
    assert reloaded["items"][0]["status"] == "scheduled"


def test_derive_linkedin_statuses_from_generated_package(editorial_base: Path):
    package_status, distribution_status = derive_flow_a_linkedin_completion_statuses(
        {
            "state": STATE_DERIVATIVES_GENERATED,
            "linkedin_package": {
                "package_id": "pkg-example",
                "package_status": "generated",
            },
        }
    )
    assert package_status == "completed"
    assert distribution_status is None


def test_derive_linkedin_statuses_from_distribution_metadata(editorial_base: Path):
    package_status, distribution_status = derive_flow_a_linkedin_completion_statuses(
        {
            "state": STATE_FLOW_A_COMPLETE,
            "linkedin_package": {
                "package_id": "pkg-example",
                "package_status": "generated",
            },
            "linkedin_distribution": {
                "distribution_id": "dist-example",
                "strategy": "stagger_48h",
            },
        }
    )
    assert package_status == "completed"
    assert distribution_status == "completed"


def test_derive_linkedin_statuses_from_variant_schedule_evidence(editorial_base: Path):
    package_status, distribution_status = derive_flow_a_linkedin_completion_statuses(
        {
            "state": STATE_DISTRIBUTION_SCHEDULED,
            "variants": [
                {
                    "variant": "executive",
                    "scheduled_at_utc": "2026-07-10T10:00:00Z",
                    "publish_state": "pending",
                }
            ],
        }
    )
    assert package_status is None
    assert distribution_status == "completed"


def test_derive_linkedin_statuses_before_package_and_schedule(editorial_base: Path):
    package_status, distribution_status = derive_flow_a_linkedin_completion_statuses(
        {"state": "blog_published"}
    )
    assert package_status is None
    assert distribution_status is None


def test_complete_flow_a_calendar_item_repairs_null_linkedin_summaries(editorial_base: Path):
    flow_a_completion = _completion_facts()["flow_a_completion"]
    flow_a_completion["linkedin_package_status"] = None
    flow_a_completion["linkedin_distribution_status"] = None
    item = _flow_a_item(status="completed")
    item.update(
        {
            "campaign_id": CAMPAIGN_ID,
            "completed_at_utc": "2026-07-10T12:00:00Z",
            "processed_source_relative_path": "blog-posts/processed/post.md",
            "flow_a_completion": flow_a_completion,
        }
    )
    calendar = _base_calendar(items=[item])
    result = complete_flow_a_calendar_item(
        calendar,
        item_id="due-flow-a",
        completion_facts=_completion_facts(),
    )
    assert result.requires_persist is True
    assert result.skipped_already_completed is False
    assert result.error_code is None
    repaired = result.calendar["items"][0]["flow_a_completion"]
    assert repaired["linkedin_package_status"] == "completed"
    assert repaired["linkedin_distribution_status"] == "completed"


def test_conflicting_non_null_linkedin_summaries_return_conflict(editorial_base: Path):
    flow_a_completion = _completion_facts()["flow_a_completion"]
    flow_a_completion["linkedin_package_status"] = "failed"
    item = _flow_a_item(status="completed")
    item.update(
        {
            "campaign_id": CAMPAIGN_ID,
            "completed_at_utc": "2026-07-10T12:00:00Z",
            "processed_source_relative_path": "blog-posts/processed/post.md",
            "flow_a_completion": flow_a_completion,
        }
    )
    calendar = _base_calendar(items=[item])
    result = complete_flow_a_calendar_item(
        calendar,
        item_id="due-flow-a",
        completion_facts=_completion_facts(),
    )
    assert result.error_code == CALENDAR_COMPLETION_FACTS_CONFLICT
    assert result.requires_persist is False


def test_concurrent_update_rejects_stale_fingerprint(editorial_base: Path):
    _write_calendar(editorial_base, _base_calendar(items=[_flow_a_item()]))
    calendar, _ = load_calendar(editorial_base)
    assert calendar is not None
    fingerprint = calendar_fingerprint(editorial_base)
    calendar["items"][0]["status"] = "completed"
    bumped = _base_calendar(items=[_flow_a_item()])
    bumped["items"][0]["title"] = "Changed externally"
    seed_editorial_calendar(bumped)

    errors = save_calendar_atomic(
        editorial_base,
        calendar,
        expected_fingerprint=fingerprint,
    )
    assert errors == [CALENDAR_COMPLETION_CONCURRENT_UPDATE]
