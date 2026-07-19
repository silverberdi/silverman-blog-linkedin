"""Tests for editorial calendar database/memory store (BL-031 / US-041)."""

from __future__ import annotations

from pathlib import Path

import pytest

from silverman_blog_linkedin.editorial_calendar_import import import_calendar_from_legacy_file
from silverman_blog_linkedin.editorial_calendar_plan import (
    CALENDAR_COMPLETION_CONCURRENT_UPDATE,
    calendar_fingerprint,
    load_calendar,
    save_calendar_atomic,
)
from silverman_blog_linkedin.editorial_calendar_store import (
    CALENDAR_STORE_NOT_CONFIGURED,
    MemoryCalendarStore,
    canonical_calendar_digest,
    create_calendar_store_from_url,
    reset_calendar_store_for_tests,
)
from tests.conftest import create_full_layout, seed_editorial_calendar, write_and_seed_calendar


def _item() -> dict:
    return {
        "item_id": "item-1",
        "title": "Sample",
        "status": "scheduled",
        "due_at_utc": "2026-07-01T14:00:00Z",
        "source_folder": "blog-posts/ready",
        "flow_type": "flow_a_ready_blog_post",
        "content_mode": "user_provided_approved_blog",
        "target_audience": "executive-recruiter",
        "topic_theme": "architecture",
        "source_relative_path": "blog-posts/ready/post.md",
    }


def _calendar(items: list[dict] | None = None) -> dict:
    return {
        "schema_version": "1",
        "updated_at_utc": "2026-07-09T20:00:00Z",
        "items": items if items is not None else [_item()],
    }


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    (base / "blog-posts" / "ready" / "post.md").write_text("# Sample\n", encoding="utf-8")
    return base


def test_round_trip_save_load(editorial_base: Path):
    write_and_seed_calendar(editorial_base, _calendar())
    loaded, errors = load_calendar(editorial_base)
    assert errors == []
    assert loaded is not None
    assert loaded["items"][0]["item_id"] == "item-1"
    fp = calendar_fingerprint(editorial_base)
    assert fp is not None
    assert len(fp) == 64


def test_validation_reject_on_save(editorial_base: Path):
    errors = save_calendar_atomic(editorial_base, {"schema_version": "1"})
    assert errors


def test_concurrent_update(editorial_base: Path):
    write_and_seed_calendar(editorial_base, _calendar())
    loaded, _ = load_calendar(editorial_base)
    assert loaded is not None
    fp = calendar_fingerprint(editorial_base)
    bumped = _calendar()
    bumped["items"][0]["title"] = "Other"
    seed_editorial_calendar(bumped)
    loaded["items"][0]["status"] = "completed"
    errors = save_calendar_atomic(editorial_base, loaded, expected_fingerprint=fp)
    assert errors == [CALENDAR_COMPLETION_CONCURRENT_UPDATE]


def test_import_empty_db_from_file(editorial_base: Path):
    path = editorial_base / "editorial-calendar" / "calendar.json"
    path.write_text(
        __import__("json").dumps(_calendar(), indent=2) + "\n", encoding="utf-8"
    )
    # Fresh empty memory store
    reset_calendar_store_for_tests(MemoryCalendarStore())
    result = import_calendar_from_legacy_file(editorial_base)
    assert result["status"] == "imported"
    assert result["item_count"] == 1


def test_import_refuses_non_empty(editorial_base: Path):
    write_and_seed_calendar(editorial_base, _calendar())
    path = editorial_base / "editorial-calendar" / "calendar.json"
    path.write_text(
        __import__("json").dumps(_calendar(), indent=2) + "\n", encoding="utf-8"
    )
    result = import_calendar_from_legacy_file(editorial_base)
    assert result["status"] == "refused"


def test_unconfigured_store_fail_closed(monkeypatch: pytest.MonkeyPatch, editorial_base: Path):
    monkeypatch.delenv("SILVERMAN_CALENDAR_DATABASE_URL", raising=False)
    reset_calendar_store_for_tests(None)
    calendar, errors = load_calendar(editorial_base)
    assert calendar is None
    assert CALENDAR_STORE_NOT_CONFIGURED in errors


def test_postgres_url_must_target_canonical_name():
    with pytest.raises(ValueError, match="silverman_linkedin_db"):
        create_calendar_store_from_url("postgresql://u:p@localhost:5432/other_db")


def test_canonical_digest_stable():
    a = canonical_calendar_digest(_calendar())
    b = canonical_calendar_digest(_calendar())
    assert a == b
    assert len(a) == 64
