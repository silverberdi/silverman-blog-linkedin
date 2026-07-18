"""Behavioral tests for US-038 pending LinkedIn variant supervision (read-only)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.linkedin_variant_pending_supervision import (
    CALENDAR_CAMPAIGN_AMBIGUOUS,
    CALENDAR_FILE_NOT_FOUND,
    CAMPAIGN_FILE_INVALID,
    console_html_path,
    get_pending_linkedin_variant_supervision,
    load_console_html,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

CAMPAIGN_ID = "flow-a-2026-07-18-supervision-console"
PENDING_API = "/flow-a/linkedin-variants/pending-supervision"
CONSOLE_PATH = "/flow-a/console/linkedin-variant-supervision"

# Patterns that must never appear in the committed console HTML asset.
_SECRET_LIKE_PATTERNS = (
    re.compile(r"CHANGE_ME", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9]{8,}\b"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{12,}"),
    re.compile(r"X-API-Key\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
)


@pytest.fixture
def supervision_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    for relative in (
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


def _variant(
    variant_id: str,
    *,
    publish_state: str = "pending",
    audience: str = "senior practitioners",
    scheduled_at_utc: str = "2026-07-20T14:00:00Z",
    **extra: object,
) -> dict:
    entry: dict[str, object] = {
        "variant": variant_id,
        "audience": audience,
        "publish_state": publish_state,
        "scheduled_at_utc": scheduled_at_utc,
        **extra,
    }
    return entry


def _write_campaign(
    base: Path,
    campaign_id: str = CAMPAIGN_ID,
    *,
    variants: list[dict] | None = None,
    flow: str = "flow_a",
    state: str = "distribution_scheduled",
) -> Path:
    payload = {
        "campaign_id": campaign_id,
        "flow": flow,
        "state": state,
        "updated_at": "2026-07-18T10:00:00Z",
        "source_file_status": {
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "no_action",
        },
        "variants": [] if variants is None else variants,
    }
    return _write_json(base / "metadata/campaigns" / f"{campaign_id}.json", payload)


def _write_calendar(base: Path, items: list[dict]) -> Path:
    return _write_json(
        base / "editorial-calendar/calendar.json",
        {
            "schema_version": "1",
            "updated_at_utc": "2026-07-18T09:00:00Z",
            "items": items,
        },
    )


def _calendar_item(
    item_id: str,
    *,
    campaign_id: str,
    due_at_utc: str = "2026-07-19T11:00:00Z",
    status: str = "scheduled",
) -> dict:
    return {
        "item_id": item_id,
        "title": f"Item {item_id}",
        "status": status,
        "due_at_utc": due_at_utc,
        "source_folder": "blog-posts/ready",
        "source_relative_path": f"blog-posts/ready/{item_id}.md",
        "flow_type": "flow_a_ready_blog_post",
        "content_mode": "user_provided_approved_blog",
        "target_audience": "executive-recruiter",
        "topic_theme": "architecture",
        "campaign_id": campaign_id,
    }


def _snapshot_tree(base: Path) -> dict[str, tuple[bytes, int]]:
    return {
        str(path.relative_to(base)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def test_pending_rows_include_required_fields_and_calendar_join(
    supervision_base: Path,
):
    _write_campaign(
        supervision_base,
        variants=[
            _variant(
                "engineering-leadership",
                scheduled_at_utc="2026-07-21T15:00:00Z",
                operator_supervision={
                    "last_action": "defer",
                    "auto_queue_eligible": True,
                },
            ),
            _variant(
                "executive-recruiter",
                publish_state="queued",
                scheduled_at_utc="2026-07-19T15:00:00Z",
            ),
            _variant(
                "hiring-manager",
                scheduled_at_utc="2026-07-20T12:00:00Z",
                audience="hiring managers",
            ),
        ],
    )
    _write_calendar(
        supervision_base,
        [_calendar_item("cal-item-1", campaign_id=CAMPAIGN_ID)],
    )

    result = get_pending_linkedin_variant_supervision(
        supervision_base,
        environ={"SILVERMAN_LINKEDIN_PUBLICATION_ENABLED": "true"},
    )

    assert result.status == "ok"
    assert result.read_only is True
    assert result.linkedin_publication_enabled is True
    assert len(result.variants) == 2
    assert [row.variant_id for row in result.variants] == [
        "hiring-manager",
        "engineering-leadership",
    ]
    first = result.variants[0].to_dict()
    assert first["campaign_id"] == CAMPAIGN_ID
    assert first["variant_id"] == "hiring-manager"
    assert first["audience"] == "hiring managers"
    assert first["scheduled_at_utc"] == "2026-07-20T12:00:00Z"
    assert first["publish_state"] == "pending"
    assert first["calendar_item_id"] == "cal-item-1"
    assert first["calendar_title"] == "Item cal-item-1"
    assert first["calendar_due_at_utc"] == "2026-07-19T11:00:00Z"
    assert first["calendar_status"] == "scheduled"
    second = result.variants[1].to_dict()
    assert second["operator_supervision_last_action"] == "defer"
    assert second["auto_queue_eligible"] is True


def test_empty_pending_set_is_success_not_failure(supervision_base: Path):
    _write_campaign(
        supervision_base,
        variants=[
            _variant("engineering-leadership", publish_state="published"),
            _variant("executive-recruiter", publish_state="cancelled"),
        ],
    )
    _write_calendar(supervision_base, [])

    result = get_pending_linkedin_variant_supervision(supervision_base)

    assert result.status == "ok"
    assert result.variants == []
    assert result.issues == []


def test_calendar_missing_still_lists_pending_variants(supervision_base: Path):
    _write_campaign(
        supervision_base,
        variants=[_variant("engineering-leadership")],
    )
    calendar_path = supervision_base / "editorial-calendar/calendar.json"
    assert not calendar_path.exists()

    result = get_pending_linkedin_variant_supervision(supervision_base)

    assert result.status == "partial"
    assert len(result.variants) == 1
    row = result.variants[0]
    assert row.variant_id == "engineering-leadership"
    assert row.calendar_item_id is None
    assert any(
        issue.reason == CALENDAR_FILE_NOT_FOUND for issue in result.issues
    )


def test_calendar_invalid_still_lists_pending_variants(supervision_base: Path):
    _write_campaign(
        supervision_base,
        variants=[_variant("engineering-leadership")],
    )
    (supervision_base / "editorial-calendar/calendar.json").write_text(
        "{not-json",
        encoding="utf-8",
    )

    result = get_pending_linkedin_variant_supervision(supervision_base)

    assert result.status == "partial"
    assert len(result.variants) == 1
    assert result.variants[0].calendar_item_id is None
    assert any(issue.source == "calendar" for issue in result.issues)


def test_partial_campaign_read_failure_keeps_other_pending_rows(
    supervision_base: Path,
):
    good_id = "flow-a-2026-07-18-good-campaign"
    bad_id = "flow-a-2026-07-18-bad-campaign"
    _write_campaign(
        supervision_base,
        good_id,
        variants=[_variant("engineering-leadership")],
    )
    (supervision_base / "metadata/campaigns" / f"{bad_id}.json").write_text(
        "{broken",
        encoding="utf-8",
    )
    _write_calendar(supervision_base, [])

    result = get_pending_linkedin_variant_supervision(supervision_base)

    assert result.status == "partial"
    assert len(result.variants) == 1
    assert result.variants[0].campaign_id == good_id
    assert any(
        issue.reason == CAMPAIGN_FILE_INVALID
        and issue.identifier == f"{bad_id}.json"
        for issue in result.issues
    )


def test_enablement_off_is_display_context_only(supervision_base: Path):
    _write_campaign(
        supervision_base,
        variants=[_variant("engineering-leadership")],
    )
    _write_calendar(supervision_base, [])

    result = get_pending_linkedin_variant_supervision(
        supervision_base,
        environ={"SILVERMAN_LINKEDIN_PUBLICATION_ENABLED": "false"},
    )

    assert result.linkedin_publication_enabled is False
    assert len(result.variants) == 1
    assert result.variants[0].publish_state == "pending"


def test_ambiguous_calendar_campaign_uses_first_item_id_and_flags_issue(
    supervision_base: Path,
):
    _write_campaign(
        supervision_base,
        variants=[_variant("engineering-leadership")],
    )
    _write_calendar(
        supervision_base,
        [
            _calendar_item("z-item", campaign_id=CAMPAIGN_ID),
            _calendar_item("a-item", campaign_id=CAMPAIGN_ID),
        ],
    )

    result = get_pending_linkedin_variant_supervision(supervision_base)

    assert result.variants[0].calendar_item_id == "a-item"
    assert any(
        issue.reason == CALENDAR_CAMPAIGN_AMBIGUOUS for issue in result.issues
    )


def test_read_path_does_not_mutate_campaign_or_calendar(supervision_base: Path):
    campaign_path = _write_campaign(
        supervision_base,
        variants=[_variant("engineering-leadership")],
    )
    calendar_path = _write_calendar(
        supervision_base,
        [_calendar_item("cal-1", campaign_id=CAMPAIGN_ID)],
    )
    before = _snapshot_tree(supervision_base)

    first = get_pending_linkedin_variant_supervision(supervision_base)
    second = get_pending_linkedin_variant_supervision(supervision_base)
    after = _snapshot_tree(supervision_base)

    assert before == after
    assert campaign_path.read_bytes() == before[str(campaign_path.relative_to(supervision_base))][0]
    assert calendar_path.read_bytes() == before[str(calendar_path.relative_to(supervision_base))][0]
    assert first.to_dict()["variants"] == second.to_dict()["variants"]
    assert first.to_dict()["issues"] == second.to_dict()["issues"]


def test_http_pending_supervision_auth_and_payload(supervision_base: Path):
    _write_campaign(
        supervision_base,
        variants=[_variant("engineering-leadership")],
    )
    _write_calendar(
        supervision_base,
        [_calendar_item("cal-1", campaign_id=CAMPAIGN_ID)],
    )
    client = TestClient(create_app(make_settings(supervision_base)))

    assert client.get(PENDING_API).status_code == 401

    response = client.get(PENDING_API, headers=auth_header())
    assert response.status_code == 200
    payload = response.json()
    assert payload["read_only"] is True
    assert len(payload["variants"]) == 1
    row = payload["variants"][0]
    assert row["campaign_id"] == CAMPAIGN_ID
    assert row["variant_id"] == "engineering-leadership"
    assert row["audience"] == "senior practitioners"
    assert row["scheduled_at_utc"] == "2026-07-20T14:00:00Z"
    assert row["publish_state"] == "pending"
    assert row["calendar_item_id"] == "cal-1"
    body_text = response.text
    assert "SILVERMAN_LINKEDIN_ACCESS_TOKEN" not in body_text
    assert "sk-" not in body_text


def test_console_html_served_at_fixed_path_without_auth(
    supervision_base: Path,
):
    client = TestClient(create_app(make_settings(supervision_base)))
    response = client.get(CONSOLE_PATH)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    body = response.text
    assert "LinkedIn variant supervision" in body
    assert PENDING_API in body
    assert "US-039" in body
    assert "US-040" in body
    assert "correct-linkedin-variant" not in body
    assert "defer-linkedin-variant" not in body
    assert "cancel-linkedin-publication" not in body
    assert "not LinkedIn API published" in body
    assert "flow_a_complete" in body


def test_static_html_secrets_audit_fails_on_secret_like_patterns():
    html = load_console_html()
    path = console_html_path()
    assert path.is_file()
    for pattern in _SECRET_LIKE_PATTERNS:
        match = pattern.search(html)
        assert match is None, (
            f"secret-like pattern {pattern.pattern!r} found in {path}: "
            f"{match.group(0)!r}"
        )


def test_static_html_secrets_audit_detects_injected_placeholder(tmp_path: Path):
    """Guardrail: the audit patterns themselves catch CHANGE_ME-style leaks."""
    polluted = "const key = 'CHANGE_ME';\n"
    assert any(pattern.search(polluted) for pattern in _SECRET_LIKE_PATTERNS)
