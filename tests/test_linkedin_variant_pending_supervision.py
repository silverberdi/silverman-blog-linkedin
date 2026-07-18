"""Behavioral tests for US-038–US-040 LinkedIn variant supervision console."""

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
    DRAFT_ARTIFACT_MISSING,
    console_assets_dir,
    console_build_dir,
    console_html_path,
    get_pending_linkedin_variant_supervision,
    load_console_static_texts,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

CAMPAIGN_ID = "flow-a-2026-07-18-supervision-console"
PENDING_API = "/flow-a/linkedin-variants/pending-supervision"
CONSOLE_PATH = "/flow-a/console/linkedin-variant-supervision"
CONSOLE_ASSETS_PREFIX = "/flow-a/console/linkedin-variant-supervision/assets"
CORRECT_PATH = "/correct-linkedin-variant"
DEFER_PATH = "/defer-linkedin-variant"
CANCEL_PATH = "/cancel-linkedin-publication"

# Patterns that must never appear in console source or built static assets.
_SECRET_LIKE_PATTERNS = (
    re.compile(r"CHANGE_ME", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9]{8,}\b"),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]{12,}"),
    re.compile(r"X-API-Key\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
    re.compile(r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]", re.IGNORECASE),
)

# Browser storage APIs must not hold secrets (US-040A: in-memory only).
_BROWSER_STORAGE_PATTERNS = (
    re.compile(r"sessionStorage"),
    re.compile(r"localStorage"),
)


def _console_bundle_text() -> str:
    """Concatenate built console HTML/JS/CSS for contract assertions."""
    parts = [text for _, text in load_console_static_texts()]
    assert parts, "Vite console build artifacts missing; run npm run build"
    return "\n".join(parts)


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
        "linkedin-posts/generated",
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


def _write_draft(
    base: Path,
    campaign_id: str,
    variant_id: str,
    content: str = "Draft body for supervision.\n",
) -> Path:
    path = base / "linkedin-posts/generated" / campaign_id / f"{variant_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
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
                    "auto_queue_eligible": False,
                    "reason": "operator_choice",
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
    _write_draft(
        supervision_base,
        CAMPAIGN_ID,
        "hiring-manager",
        "Hiring manager draft.\n",
    )
    _write_draft(
        supervision_base,
        CAMPAIGN_ID,
        "engineering-leadership",
        "Engineering leadership draft.\n",
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
    assert first["draft_content"] == "Hiring manager draft.\n"
    second = result.variants[1].to_dict()
    assert second["operator_supervision_last_action"] == "defer"
    assert second["auto_queue_eligible"] is False
    assert second["operator_supervision_reason"] == "operator_choice"
    assert second["draft_content"] == "Engineering leadership draft.\n"
    assert result.integration_failures == []


def test_integration_failures_include_failed_siblings_of_pending_campaign(
    supervision_base: Path,
):
    _write_campaign(
        supervision_base,
        variants=[
            _variant("engineering-leadership"),
            _variant(
                "executive-recruiter",
                publish_state="failed",
                linkedin_publication={
                    "last_error_code": "linkedin_publish_api_error",
                    "last_failed_at": "2026-07-18T12:00:00Z",
                    "retryable": True,
                    "http_status": 503,
                },
            ),
            _variant("hiring-manager", publish_state="queued"),
        ],
    )
    _write_draft(supervision_base, CAMPAIGN_ID, "engineering-leadership")
    _write_calendar(supervision_base, [])

    result = get_pending_linkedin_variant_supervision(supervision_base)

    assert len(result.variants) == 1
    assert result.variants[0].variant_id == "engineering-leadership"
    assert len(result.integration_failures) == 1
    failure = result.integration_failures[0].to_dict()
    assert failure == {
        "campaign_id": CAMPAIGN_ID,
        "variant_id": "executive-recruiter",
        "publish_state": "failed",
        "last_error_code": "linkedin_publish_api_error",
        "http_status": 503,
    }


def test_failed_only_campaign_does_not_populate_integration_failures(
    supervision_base: Path,
):
    """Failed siblings are only surfaced when the campaign also has pending rows."""
    _write_campaign(
        supervision_base,
        variants=[
            _variant(
                "executive-recruiter",
                publish_state="failed",
                linkedin_publication={
                    "last_error_code": "linkedin_publish_api_error",
                    "last_failed_at": "2026-07-18T12:00:00Z",
                    "retryable": True,
                    "http_status": 500,
                },
            ),
        ],
    )
    _write_calendar(supervision_base, [])

    result = get_pending_linkedin_variant_supervision(supervision_base)

    assert result.variants == []
    assert result.integration_failures == []


def test_missing_draft_still_lists_pending_row_with_null_content(
    supervision_base: Path,
):
    _write_campaign(
        supervision_base,
        variants=[_variant("engineering-leadership")],
    )
    _write_calendar(supervision_base, [])

    result = get_pending_linkedin_variant_supervision(supervision_base)

    assert result.status == "partial"
    assert len(result.variants) == 1
    assert result.variants[0].draft_content is None
    assert any(
        issue.reason == DRAFT_ARTIFACT_MISSING
        and issue.identifier == f"{CAMPAIGN_ID}:engineering-leadership"
        for issue in result.issues
    )


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
    _write_draft(supervision_base, CAMPAIGN_ID, "engineering-leadership")
    calendar_path = supervision_base / "editorial-calendar/calendar.json"
    assert not calendar_path.exists()

    result = get_pending_linkedin_variant_supervision(supervision_base)

    assert result.status == "partial"
    assert len(result.variants) == 1
    row = result.variants[0]
    assert row.variant_id == "engineering-leadership"
    assert row.calendar_item_id is None
    assert row.draft_content is not None
    assert any(
        issue.reason == CALENDAR_FILE_NOT_FOUND for issue in result.issues
    )


def test_calendar_invalid_still_lists_pending_variants(supervision_base: Path):
    _write_campaign(
        supervision_base,
        variants=[_variant("engineering-leadership")],
    )
    _write_draft(supervision_base, CAMPAIGN_ID, "engineering-leadership")
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
    _write_draft(supervision_base, good_id, "engineering-leadership")
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
    _write_draft(supervision_base, CAMPAIGN_ID, "engineering-leadership")
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
    _write_draft(supervision_base, CAMPAIGN_ID, "engineering-leadership")
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
    _write_draft(supervision_base, CAMPAIGN_ID, "engineering-leadership")
    calendar_path = _write_calendar(
        supervision_base,
        [_calendar_item("cal-1", campaign_id=CAMPAIGN_ID)],
    )
    before = _snapshot_tree(supervision_base)

    first = get_pending_linkedin_variant_supervision(supervision_base)
    second = get_pending_linkedin_variant_supervision(supervision_base)
    after = _snapshot_tree(supervision_base)

    assert before == after
    assert (
        campaign_path.read_bytes()
        == before[str(campaign_path.relative_to(supervision_base))][0]
    )
    assert (
        calendar_path.read_bytes()
        == before[str(calendar_path.relative_to(supervision_base))][0]
    )
    assert first.to_dict()["variants"] == second.to_dict()["variants"]
    assert first.to_dict()["issues"] == second.to_dict()["issues"]
    assert first.to_dict()["integration_failures"] == second.to_dict()[
        "integration_failures"
    ]


def test_http_pending_supervision_auth_and_payload(supervision_base: Path):
    _write_campaign(
        supervision_base,
        variants=[
            _variant("engineering-leadership"),
            _variant(
                "executive-recruiter",
                publish_state="failed",
                linkedin_publication={
                    "last_error_code": "linkedin_publish_token_invalid",
                    "last_failed_at": "2026-07-18T11:00:00Z",
                    "retryable": False,
                    "http_status": 401,
                },
            ),
        ],
    )
    _write_draft(
        supervision_base,
        CAMPAIGN_ID,
        "engineering-leadership",
        "HTTP draft body.\n",
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
    assert row["draft_content"] == "HTTP draft body.\n"
    assert "operator_supervision_reason" in row
    assert len(payload["integration_failures"]) == 1
    assert payload["integration_failures"][0]["variant_id"] == "executive-recruiter"
    assert payload["integration_failures"][0]["last_error_code"] == (
        "linkedin_publish_token_invalid"
    )
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
    assert "US-040" in body
    assert CONSOLE_ASSETS_PREFIX in body
    assert "/assets/" in body

    # Same-origin hashed assets must resolve (no path traversal outside build dir).
    asset_refs = re.findall(
        rf'{re.escape(CONSOLE_ASSETS_PREFIX)}/[^"\']+',
        body,
    )
    assert asset_refs, "expected Vite asset URLs under the console assets prefix"
    for href in asset_refs:
        asset_resp = client.get(href)
        assert asset_resp.status_code == 200, href

    bundle = _console_bundle_text()
    assert PENDING_API in bundle
    assert CORRECT_PATH in bundle
    assert DEFER_PATH in bundle
    assert CANCEL_PATH in bundle
    assert "not LinkedIn API published" in bundle
    assert "flow_a_complete" in bundle
    assert "edit-dry-run" in bundle
    assert "schedule-dry-run" in bundle
    assert "cancel-dry-run" in bundle
    assert "linkedin_supervision_variant_not_pending" in bundle
    assert "linkedin_supervision_defer_time_invalid" in bundle
    assert "linkedin_publish_cancel_not_allowed" in bundle
    assert "integration_failures" in bundle
    assert "Cancel remains US-040" not in bundle
    assert "actions not available" not in bundle.lower()
    # Assets must not escape the build directory via .. traversal.
    traversal = client.get(f"{CONSOLE_ASSETS_PREFIX}/../index.html")
    assert traversal.status_code in {404, 400, 403}


def test_console_action_contract_wiring_in_static_html():
    """Story 3 + US-040C: edit/cancel + shared schedule editor → US-017 / calendar APIs."""
    bundle = _console_bundle_text()
    assert CORRECT_PATH in bundle
    assert DEFER_PATH in bundle
    assert CANCEL_PATH in bundle
    assert "/editorial-calendar/update-item-schedule" in bundle
    assert "edit-dry-run" in bundle
    assert "schedule-dry-run" in bundle
    assert "cancel-dry-run" in bundle
    assert "draft_content" in bundle
    assert "new_scheduled_at_utc" in bundle
    assert "validated (dry-run, no mutation)" in bundle
    assert "persisted (real write)" in bundle
    assert "Schedule edit does not call LinkedIn publication API" in bundle
    assert "not strategy-driven auto-queue eligible" in bundle or (
        "not auto-queue eligible" in bundle
    )
    assert 'data-action="edit"' in bundle or "data-action" in bundle
    assert "linkedin_publish_cancel_not_allowed" in bundle
    assert "linkedin_supervision_idempotency_conflict" in bundle
    assert "Unauthorized (401)" in bundle
    # Cancel wires only to existing US-017 cancel POST (no parallel mutation route).
    assert CANCEL_PATH in bundle
    assert "/flow-a/console/cancel" not in bundle
    assert "POST /flow-a/" not in bundle
    # US-040A: no browser storage for secrets.
    for pattern in _BROWSER_STORAGE_PATTERNS:
        assert pattern.search(bundle) is None, pattern.pattern
    # Legacy monolithic HTML must not remain as a second SoT.
    legacy = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "silverman_blog_linkedin"
        / "static"
        / "linkedin_variant_supervision_console.html"
    )
    assert not legacy.exists()
    assert console_html_path().is_file()
    assert console_assets_dir().is_dir()
    assert console_build_dir().is_dir()


def test_real_cancel_via_existing_endpoint_removes_pending_row(
    supervision_base: Path,
):
    """Console cancel SoT is POST /cancel-linkedin-publication; row leaves pending list."""
    _write_campaign(
        supervision_base,
        variants=[
            _variant("engineering-leadership"),
            _variant("hiring-manager"),
        ],
    )
    _write_draft(supervision_base, CAMPAIGN_ID, "engineering-leadership")
    _write_draft(supervision_base, CAMPAIGN_ID, "hiring-manager")
    _write_calendar(supervision_base, [])
    client = TestClient(create_app(make_settings(supervision_base)))

    before = client.get(PENDING_API, headers=auth_header()).json()
    assert {row["variant_id"] for row in before["variants"]} == {
        "engineering-leadership",
        "hiring-manager",
    }

    cancel = client.post(
        CANCEL_PATH,
        headers=auth_header(),
        json={
            "campaign_id": CAMPAIGN_ID,
            "variant": "engineering-leadership",
            "dry_run": False,
            "reason": "operator_choice",
            "idempotency_key": "console-cancel-test-1",
        },
    )
    assert cancel.status_code == 200
    cancel_payload = cancel.json()
    assert cancel_payload["status"] == "completed"
    assert cancel_payload["dry_run"] is False

    after = client.get(PENDING_API, headers=auth_header()).json()
    assert [row["variant_id"] for row in after["variants"]] == ["hiring-manager"]


def test_cancel_dry_run_default_does_not_remove_pending_row(
    supervision_base: Path,
):
    _write_campaign(
        supervision_base,
        variants=[_variant("engineering-leadership")],
    )
    _write_draft(supervision_base, CAMPAIGN_ID, "engineering-leadership")
    _write_calendar(supervision_base, [])
    client = TestClient(create_app(make_settings(supervision_base)))

    # Omit dry_run — request model default is true (matches console default on).
    response = client.post(
        CANCEL_PATH,
        headers=auth_header(),
        json={
            "campaign_id": CAMPAIGN_ID,
            "variant": "engineering-leadership",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["dry_run"] is True

    pending = client.get(PENDING_API, headers=auth_header()).json()
    assert len(pending["variants"]) == 1
    assert pending["variants"][0]["variant_id"] == "engineering-leadership"


def test_cancel_not_allowed_and_auth_failure_codes_surface(
    supervision_base: Path,
):
    _write_campaign(
        supervision_base,
        variants=[
            _variant("engineering-leadership", publish_state="published"),
        ],
    )
    _write_calendar(supervision_base, [])
    client = TestClient(create_app(make_settings(supervision_base)))

    unauth = client.post(
        CANCEL_PATH,
        json={
            "campaign_id": CAMPAIGN_ID,
            "variant": "engineering-leadership",
            "dry_run": False,
        },
    )
    assert unauth.status_code == 401

    denied = client.post(
        CANCEL_PATH,
        headers=auth_header(),
        json={
            "campaign_id": CAMPAIGN_ID,
            "variant": "engineering-leadership",
            "dry_run": True,
        },
    )
    assert denied.status_code == 200
    denied_payload = denied.json()
    assert denied_payload["status"] == "failed"
    assert "linkedin_publish_cancel_not_allowed" in denied_payload["errors"]

    bundle = _console_bundle_text()
    assert "linkedin_publish_cancel_not_allowed" in bundle
    assert "Unauthorized (401)" in bundle


def test_static_html_secrets_audit_fails_on_secret_like_patterns():
    texts = load_console_static_texts()
    assert texts, "Vite console build artifacts missing; run npm run build"
    path = console_html_path()
    assert path.is_file()
    for asset_path, content in texts:
        for pattern in _SECRET_LIKE_PATTERNS:
            match = pattern.search(content)
            assert match is None, (
                f"secret-like pattern {pattern.pattern!r} found in {asset_path}: "
                f"{match.group(0)!r}"
            )
        for pattern in _BROWSER_STORAGE_PATTERNS:
            match = pattern.search(content)
            assert match is None, (
                f"browser storage API {pattern.pattern!r} found in {asset_path}"
            )

    # Frontend source audit (excluding node_modules / built output).
    frontend_root = (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "linkedin-variant-supervision-console"
        / "src"
    )
    assert frontend_root.is_dir()
    for src_path in sorted(frontend_root.rglob("*")):
        if not src_path.is_file():
            continue
        if src_path.suffix.lower() not in {".ts", ".tsx", ".css", ".html"}:
            continue
        content = src_path.read_text(encoding="utf-8")
        for pattern in _SECRET_LIKE_PATTERNS:
            match = pattern.search(content)
            assert match is None, (
                f"secret-like pattern {pattern.pattern!r} found in {src_path}: "
                f"{match.group(0)!r}"
            )


def test_static_html_secrets_audit_detects_injected_placeholder(tmp_path: Path):
    """Guardrail: the audit patterns themselves catch CHANGE_ME-style leaks."""
    polluted = "const key = 'CHANGE_ME';\n"
    assert any(pattern.search(polluted) for pattern in _SECRET_LIKE_PATTERNS)
