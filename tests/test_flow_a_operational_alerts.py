"""Behavioral tests for Flow A operational alerts (US-028 / US-029 / US-030)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.flow_a_operational_alerts import (
    ALERT_BLOG_PUBLICATION_FAILURE,
    ALERT_FAILED_N8N_WORKFLOW,
    ALERT_IMAGE_GENERATION_FAILURE,
    ALERT_ITEM_MOVED_TO_ERROR,
    ALERT_LINKEDIN_TOKEN_OR_PUBLICATION_FAILURE,
    ALERT_PARTIAL_CALENDAR_EXECUTION,
    ALERT_STALE_CAMPAIGN,
    ALERT_UNHEALTHY_WORKER,
    ALL_ALERT_TYPES,
    EMISSION_STATUS_ALREADY_EMITTED,
    EMISSION_STATUS_DISABLED,
    EMISSION_STATUS_EMITTED,
    EMISSION_STATUS_MISCONFIGURED,
    EMISSION_STATUS_NOT_REQUESTED,
    LEDGER_FILENAME,
    LEDGER_RELATIVE_DIR,
    ORCHESTRATION_FAILURES_FILENAME,
    ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED,
    SEVERITY_ERROR,
    SEVERITY_WARNING,
    evaluate_flow_a_operational_alerts,
    report_orchestration_failure,
)
from silverman_blog_linkedin.flow_a_operational_alerts_config import (
    ENV_OPERATIONAL_ALERTS_ENABLED,
    ENV_OPERATIONAL_ALERTS_WEBHOOK_URL,
    load_flow_a_operational_alerts_settings,
)
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.paths import EXPECTED_FOLDERS
from tests.conftest import auth_header, make_settings, write_and_seed_calendar

NOW = "2026-07-17T12:00:00Z"
CAMPAIGN_ERROR = "flow-a-2026-07-17-alerts-error"
CAMPAIGN_COMFYUI = "flow-a-2026-07-17-alerts-comfyui"
CAMPAIGN_BLOG = "flow-a-2026-07-17-alerts-blog"
CAMPAIGN_PREVIEW = "flow-a-2026-07-17-alerts-preview"
CAMPAIGN_LINKEDIN = "flow-a-2026-07-17-alerts-linkedin"
CAMPAIGN_STALE = "flow-a-2026-07-17-alerts-stale"
WEBHOOK_URL = "https://hooks.example.test/flow-a-alerts"
WORKFLOW_ID = "silvermanFlowAPublish01"


@pytest.fixture
def alerts_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    for relative in EXPECTED_FOLDERS:
        (base / relative).mkdir(parents=True, exist_ok=True)
    # Empty calendar store (autouse memory fixture) is valid SoT.
    return base


@pytest.fixture
def degraded_alerts_base(tmp_path: Path) -> Path:
    """Editorial layout missing required folders (folders_ready=false)."""
    base = tmp_path / "editorial-degraded"
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


def _write_run(
    base: Path,
    run_id: str,
    *,
    status: str = "failed",
    errors: list[str] | None = None,
    **extra: object,
) -> Path:
    payload = {
        "run_id": run_id,
        "trigger": "POST /publish-blog-post",
        "status": status,
        "started_at": "2026-07-17T10:00:00Z",
        "completed_at": "2026-07-17T10:01:00Z",
        **extra,
    }
    if errors is not None:
        payload["errors"] = errors
    return _write_json(base / "metadata/runs" / f"{run_id}.json", payload)


def _write_campaign(
    base: Path,
    campaign_id: str,
    *,
    state: str = "error",
    source_status: dict | None = None,
    errors: list[str] | None = None,
    variants: object = None,
    **extra: object,
) -> Path:
    payload: dict[str, object] = {
        "campaign_id": campaign_id,
        "flow": "flow_a",
        "state": state,
        "updated_at": "2026-07-17T10:00:00Z",
        "source_file_status": source_status
        or {
            "location": "error",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
        },
        "variants": [] if variants is None else variants,
        **extra,
    }
    if errors is not None:
        payload["errors"] = errors
    return _write_json(
        base / "metadata/campaigns" / f"{campaign_id}.json",
        payload,
    )


def _write_calendar(base: Path, items: list[dict]) -> Path:
    from tests.conftest import write_and_seed_calendar

    return write_and_seed_calendar(
        base,
        {
            "schema_version": "1",
            "updated_at_utc": "2026-07-17T09:00:00Z",
            "items": items,
        },
    )


def _calendar_item(
    item_id: str,
    *,
    status: str = "scheduled",
    due_at_utc: str = "2026-07-17T11:00:00Z",
    campaign_id: str | None = None,
    title: str | None = None,
) -> dict:
    item = {
        "item_id": item_id,
        "title": title if title is not None else f"Item {item_id}",
        "status": status,
        "due_at_utc": due_at_utc,
        "source_folder": "blog-posts/ready",
        "source_relative_path": f"blog-posts/ready/{item_id}.md",
        "flow_type": "flow_a_ready_blog_post",
        "content_mode": "user_provided_approved_blog",
        "target_audience": "executive-recruiter",
        "topic_theme": "architecture",
    }
    if campaign_id is not None:
        item["campaign_id"] = campaign_id
    return item


def _snapshot_tree(base: Path) -> dict[str, tuple[bytes, int]]:
    return {
        str(path.relative_to(base)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def _alerts_by_type(body: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for alert in body["alerts"]:
        grouped.setdefault(alert["alert_type"], []).append(alert)
    return grouped


def test_config_helpers_fail_closed(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(ENV_OPERATIONAL_ALERTS_ENABLED, raising=False)
    monkeypatch.delenv(ENV_OPERATIONAL_ALERTS_WEBHOOK_URL, raising=False)
    settings = load_flow_a_operational_alerts_settings({})
    assert settings.enabled is False
    assert settings.webhook_configured is False
    assert settings.emission_ready is False

    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_ENABLED, "true")
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_WEBHOOK_URL, "not-a-url")
    settings = load_flow_a_operational_alerts_settings()
    assert settings.enabled is True
    assert settings.webhook_configured is False
    assert settings.emission_ready is False

    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_WEBHOOK_URL, WEBHOOK_URL)
    settings = load_flow_a_operational_alerts_settings()
    assert settings.emission_ready is True


def test_item_moved_to_error_alert(alerts_base: Path):
    _write_campaign(
        alerts_base,
        CAMPAIGN_ERROR,
        source_status={
            "location": "error",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
            "last_error": {"error_code": "validation_failed"},
        },
    )
    result = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    body = result.to_dict()
    by_type = _alerts_by_type(body)
    assert len(by_type[ALERT_ITEM_MOVED_TO_ERROR]) == 1
    alert = by_type[ALERT_ITEM_MOVED_TO_ERROR][0]
    assert alert["campaign_id"] == CAMPAIGN_ERROR
    assert alert["severity"] == "error"
    assert alert["fingerprint"].startswith(f"{ALERT_ITEM_MOVED_TO_ERROR}:")
    assert "campaign_id=" in alert["summary"]
    assert body["summary"]["counts"][ALERT_ITEM_MOVED_TO_ERROR] == 1


def test_image_generation_failure_alert(alerts_base: Path):
    _write_campaign(
        alerts_base,
        CAMPAIGN_COMFYUI,
        state="error",
        source_status={
            "location": "error",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
        },
        errors=["blog_image_generation_comfyui_failed"],
    )
    _write_run(
        alerts_base,
        "run-comfyui-failed",
        errors=["comfyui_connection_refused"],
    )
    result = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    body = result.to_dict()
    by_type = _alerts_by_type(body)
    image_alerts = by_type[ALERT_IMAGE_GENERATION_FAILURE]
    assert len(image_alerts) == 2
    campaign_alert = next(a for a in image_alerts if a.get("campaign_id"))
    run_alert = next(a for a in image_alerts if a.get("run_id"))
    assert campaign_alert["dependency"] == "comfyui"
    assert campaign_alert["error_codes"] == [
        "blog_image_generation_comfyui_failed"
    ]
    assert run_alert["dependency"] == "comfyui"
    assert run_alert["error_codes"] == ["comfyui_connection_refused"]


def test_blog_publication_failure_alert(alerts_base: Path):
    _write_campaign(
        alerts_base,
        CAMPAIGN_BLOG,
        state="error",
        source_status={
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
            "last_error": {"error_code": "blog_git_publication_push_failed"},
        },
        errors=["blog_publish_handoff_failed"],
    )
    result = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    body = result.to_dict()
    by_type = _alerts_by_type(body)
    alerts = by_type[ALERT_BLOG_PUBLICATION_FAILURE]
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["dependency"] == "github_pages_checkout"
    assert alert["error_codes"] == [
        "blog_git_publication_push_failed",
        "blog_publish_handoff_failed",
    ]
    assert ALERT_ITEM_MOVED_TO_ERROR not in by_type


def test_preview_checkout_codes_excluded_from_blog_and_linkedin_alerts(
    alerts_base: Path,
):
    _write_campaign(
        alerts_base,
        CAMPAIGN_PREVIEW,
        state="error",
        source_status={
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "no_action",
        },
        variants=[
            {
                "variant": "executive-recruiter",
                "publish_state": "failed",
                "linkedin_publication": {
                    "last_error_code": (
                        "linkedin_article_preview_public_repo_not_configured"
                    )
                },
            },
            {
                "variant": "technical-architect",
                "publish_state": "failed",
                "linkedin_publication": {
                    "last_error_code": (
                        "linkedin_preview_validation_checkout_missing"
                    )
                },
            },
        ],
    )
    # Force dependency collection via failed/blocked path.
    _write_campaign(
        alerts_base,
        "flow-a-2026-07-17-alerts-preview-blocked",
        state="error",
        source_status={
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
            "last_error": {
                "error_code": "linkedin_article_preview_public_repo_not_configured"
            },
        },
        errors=["linkedin_preview_validation_checkout_missing"],
    )
    result = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    body = result.to_dict()
    alert_types = {alert["alert_type"] for alert in body["alerts"]}
    assert ALERT_BLOG_PUBLICATION_FAILURE not in alert_types
    assert ALERT_LINKEDIN_TOKEN_OR_PUBLICATION_FAILURE not in alert_types
    assert ALERT_UNHEALTHY_WORKER not in alert_types
    assert ALERT_FAILED_N8N_WORKFLOW not in alert_types


def test_http_auth_invalid_now_determinism_and_safe_output(alerts_base: Path):
    _write_campaign(
        alerts_base,
        CAMPAIGN_COMFYUI,
        errors=["blog_image_generation_comfyui_failed"],
        source_status={
            "location": "error",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
            "last_error": {"error_code": "blog_image_generation_comfyui_failed"},
        },
        api_key="NEVER-RETURN-THIS",
        authorization="Bearer NEVER-RETURN-THIS",
        markdown_content="NEVER-RETURN-BODY",
        webhook_url=WEBHOOK_URL,
    )
    client = TestClient(create_app(make_settings(alerts_base)))

    with patch(
        "silverman_blog_linkedin.main.evaluate_flow_a_operational_alerts"
    ) as evaluate:
        assert (
            client.post("/flow-a/operational-alerts/evaluate").status_code
            == 401
        )
        evaluate.assert_not_called()

    invalid = client.post(
        "/flow-a/operational-alerts/evaluate",
        headers=auth_header(),
        json={"now_utc": "2026-07-17T12:00:00+00:00"},
    )
    assert invalid.status_code == 422

    first = client.post(
        "/flow-a/operational-alerts/evaluate",
        headers=auth_header(),
        json={"now_utc": NOW},
    )
    second = client.post(
        "/flow-a/operational-alerts/evaluate",
        headers=auth_header(),
        json={"now_utc": NOW, "emit": False},
    )
    assert first.status_code == 200
    assert first.content == second.content
    body = first.json()
    assert set(body) == {
        "status",
        "observed_at_utc",
        "alerts",
        "summary",
        "data_issues",
        "emission",
    }
    assert body["emission"]["status"] == EMISSION_STATUS_NOT_REQUESTED
    assert body["alerts"] == sorted(
        body["alerts"],
        key=lambda item: (item["alert_type"], item["fingerprint"]),
    )
    serialized = json.dumps(body)
    assert "NEVER-RETURN-THIS" not in serialized
    assert "NEVER-RETURN-BODY" not in serialized
    assert WEBHOOK_URL not in serialized
    assert str(alerts_base) not in serialized


def test_evaluate_only_zero_lifecycle_mutation(alerts_base: Path):
    _write_campaign(
        alerts_base,
        CAMPAIGN_ERROR,
        errors=["blog_image_generation_comfyui_failed"],
    )
    _write_run(alerts_base, "run-ok", status="completed")
    before = _snapshot_tree(alerts_base)
    with (
        patch("subprocess.run") as git_or_shell,
        patch("httpx.request") as external_http,
        patch("httpx.Client") as http_client_cls,
    ):
        result = evaluate_flow_a_operational_alerts(
            alerts_base, now_utc=NOW, emit=False
        )
    git_or_shell.assert_not_called()
    external_http.assert_not_called()
    http_client_cls.assert_not_called()
    assert result.emission.status == EMISSION_STATUS_NOT_REQUESTED
    assert _snapshot_tree(alerts_base) == before
    assert not (alerts_base / LEDGER_RELATIVE_DIR / LEDGER_FILENAME).exists()


def test_emit_fail_closed_when_disabled(
    alerts_base: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_ENABLED, "false")
    monkeypatch.delenv(ENV_OPERATIONAL_ALERTS_WEBHOOK_URL, raising=False)
    _write_campaign(alerts_base, CAMPAIGN_ERROR)
    before = _snapshot_tree(alerts_base)
    mock_client = MagicMock()
    result = evaluate_flow_a_operational_alerts(
        alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    mock_client.post.assert_not_called()
    assert result.emission.status == EMISSION_STATUS_DISABLED
    assert result.alerts
    assert _snapshot_tree(alerts_base) == before


def test_emit_fail_closed_when_misconfigured(
    alerts_base: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_ENABLED, "true")
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_WEBHOOK_URL, "")
    _write_campaign(alerts_base, CAMPAIGN_ERROR)
    before = _snapshot_tree(alerts_base)
    mock_client = MagicMock()
    result = evaluate_flow_a_operational_alerts(
        alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    mock_client.post.assert_not_called()
    assert result.emission.status == EMISSION_STATUS_MISCONFIGURED
    assert _snapshot_tree(alerts_base) == before


def test_successful_emit_writes_ledger_and_skips_reemit(
    alerts_base: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_ENABLED, "true")
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_WEBHOOK_URL, WEBHOOK_URL)
    _write_campaign(
        alerts_base,
        CAMPAIGN_ERROR,
        source_status={
            "location": "error",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
        },
    )
    campaign_path = alerts_base / "metadata/campaigns" / f"{CAMPAIGN_ERROR}.json"
    campaign_before = campaign_path.read_bytes()

    mock_client = MagicMock()
    mock_client.post.return_value = httpx.Response(200, json={"ok": True})

    first = evaluate_flow_a_operational_alerts(
        alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    assert first.emission.status == EMISSION_STATUS_EMITTED
    assert first.emission.emitted_fingerprints
    assert mock_client.post.call_count == len(first.alerts)
    posted = mock_client.post.call_args
    assert posted.args[0] == WEBHOOK_URL
    webhook_body = posted.kwargs["json"]
    assert "alert" in webhook_body
    assert WEBHOOK_URL not in json.dumps(webhook_body)

    ledger_path = alerts_base / LEDGER_RELATIVE_DIR / LEDGER_FILENAME
    assert ledger_path.is_file()
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    assert ledger["version"] == 1
    for fingerprint in first.emission.emitted_fingerprints:
        assert fingerprint in ledger["entries"]

    assert campaign_path.read_bytes() == campaign_before

    mock_client.reset_mock()
    second = evaluate_flow_a_operational_alerts(
        alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    mock_client.post.assert_not_called()
    assert second.emission.status == EMISSION_STATUS_ALREADY_EMITTED
    assert set(second.emission.already_emitted_fingerprints) == set(
        first.emission.emitted_fingerprints
    )
    assert second.emission.emitted_fingerprints == []


def test_failed_webhook_does_not_write_ledger(
    alerts_base: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_ENABLED, "true")
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_WEBHOOK_URL, WEBHOOK_URL)
    _write_campaign(alerts_base, CAMPAIGN_ERROR)
    mock_client = MagicMock()
    mock_client.post.return_value = httpx.Response(500, text="nope")
    result = evaluate_flow_a_operational_alerts(
        alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    assert result.emission.failed_fingerprints
    assert result.emission.emitted_fingerprints == []
    assert not (alerts_base / LEDGER_RELATIVE_DIR / LEDGER_FILENAME).exists()


def test_partial_calendar_execution_alert(alerts_base: Path):
    secret_title = "SECRET-CALENDAR-TITLE-NEVER-RETURN"
    _write_calendar(
        alerts_base,
        [
            _calendar_item(
                "delayed-item-1",
                status="scheduled",
                due_at_utc="2026-07-17T10:00:00Z",
                campaign_id=CAMPAIGN_ERROR,
                title=secret_title,
            ),
            _calendar_item(
                "future-item",
                status="scheduled",
                due_at_utc="2026-07-17T13:00:00Z",
                title="Future title",
            ),
        ],
    )
    result = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    body = result.to_dict()
    by_type = _alerts_by_type(body)
    alerts = by_type[ALERT_PARTIAL_CALENDAR_EXECUTION]
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["calendar_item_id"] == "delayed-item-1"
    assert alert["campaign_id"] == CAMPAIGN_ERROR
    assert alert["severity"] == SEVERITY_WARNING
    assert alert["error_codes"] == ["calendar_item_past_due"]
    assert alert["fingerprint"].startswith(f"{ALERT_PARTIAL_CALENDAR_EXECUTION}:")
    assert "title" not in alert
    serialized = json.dumps(body)
    assert secret_title not in serialized
    assert body["summary"]["counts"][ALERT_PARTIAL_CALENDAR_EXECUTION] == 1


def test_linkedin_token_or_publication_failure_from_dependency_and_progress(
    alerts_base: Path,
):
    _write_campaign(
        alerts_base,
        CAMPAIGN_LINKEDIN,
        state="error",
        source_status={
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
            "last_error": {"error_code": "linkedin_oauth_refresh_failed"},
        },
        errors=["linkedin_oauth_refresh_failed"],
        variants=[
            {
                "variant": "executive-recruiter",
                "publish_state": "failed",
                "linkedin_publication": {
                    "last_error_code": "linkedin_publish_token_invalid"
                },
            },
            {
                "variant": "technical-architect",
                "publish_state": "failed",
                "linkedin_publication": {
                    "last_error_code": "linkedin_publish_api_error"
                },
            },
        ],
    )
    _write_run(
        alerts_base,
        "run-linkedin-failed",
        errors=["linkedin_publish_api_error"],
    )
    result = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    body = result.to_dict()
    by_type = _alerts_by_type(body)
    linkedin_alerts = by_type[ALERT_LINKEDIN_TOKEN_OR_PUBLICATION_FAILURE]
    assert len(linkedin_alerts) == 2
    campaign_alert = next(a for a in linkedin_alerts if a.get("campaign_id"))
    run_alert = next(a for a in linkedin_alerts if a.get("run_id"))
    assert campaign_alert["dependency"] == "linkedin"
    assert campaign_alert["severity"] == SEVERITY_ERROR
    assert campaign_alert["error_codes"] == [
        "linkedin_oauth_refresh_failed",
        "linkedin_publish_api_error",
        "linkedin_publish_token_invalid",
    ]
    assert run_alert["dependency"] == "linkedin"
    assert run_alert["error_codes"] == ["linkedin_publish_api_error"]


def test_stale_campaign_alert(alerts_base: Path):
    _write_campaign(
        alerts_base,
        CAMPAIGN_STALE,
        state="validated",
        source_status={
            "location": "queued",
            "execution_state": "stale",
            "recovery_classification": "requeue_required",
        },
    )
    result = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    body = result.to_dict()
    by_type = _alerts_by_type(body)
    alerts = by_type[ALERT_STALE_CAMPAIGN]
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["campaign_id"] == CAMPAIGN_STALE
    assert alert["severity"] == SEVERITY_WARNING
    assert "execution_state_stale" in alert["error_codes"]
    assert body["summary"]["counts"][ALERT_STALE_CAMPAIGN] == 1


def test_eight_type_summary_counts_and_us028_us029_coexistence(alerts_base: Path):
    _write_campaign(
        alerts_base,
        CAMPAIGN_ERROR,
        source_status={
            "location": "error",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
            "last_error": {"error_code": "validation_failed"},
        },
        errors=["blog_image_generation_comfyui_failed"],
    )
    _write_campaign(
        alerts_base,
        CAMPAIGN_BLOG,
        state="error",
        source_status={
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
            "last_error": {"error_code": "blog_git_publication_push_failed"},
        },
        errors=["blog_publish_handoff_failed"],
    )
    _write_campaign(
        alerts_base,
        CAMPAIGN_LINKEDIN,
        state="error",
        source_status={
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "manual_intervention_required",
            "last_error": {"error_code": "linkedin_publish_api_error"},
        },
        errors=["linkedin_publish_api_error"],
    )
    _write_campaign(
        alerts_base,
        CAMPAIGN_STALE,
        state="validated",
        source_status={
            "location": "queued",
            "execution_state": "stale",
            "recovery_classification": "requeue_required",
        },
    )
    _write_calendar(
        alerts_base,
        [
            _calendar_item(
                "delayed-coexist",
                status="due",
                due_at_utc="2026-07-17T09:00:00Z",
                title="DO-NOT-ECHO-TITLE",
            )
        ],
    )
    before = _snapshot_tree(alerts_base)
    result = evaluate_flow_a_operational_alerts(
        alerts_base, now_utc=NOW, emit=False
    )
    body = result.to_dict()
    counts = body["summary"]["counts"]
    assert set(counts) == set(ALL_ALERT_TYPES)
    assert len(ALL_ALERT_TYPES) == 8
    assert counts[ALERT_ITEM_MOVED_TO_ERROR] >= 1
    assert counts[ALERT_IMAGE_GENERATION_FAILURE] >= 1
    assert counts[ALERT_BLOG_PUBLICATION_FAILURE] >= 1
    assert counts[ALERT_PARTIAL_CALENDAR_EXECUTION] == 1
    assert counts[ALERT_LINKEDIN_TOKEN_OR_PUBLICATION_FAILURE] >= 1
    assert counts[ALERT_STALE_CAMPAIGN] == 1
    assert counts[ALERT_UNHEALTHY_WORKER] == 0
    assert counts[ALERT_FAILED_N8N_WORKFLOW] == 0
    assert body["summary"]["total"] == sum(counts.values())
    alert_types = {alert["alert_type"] for alert in body["alerts"]}
    assert ALERT_UNHEALTHY_WORKER not in alert_types
    assert ALERT_FAILED_N8N_WORKFLOW not in alert_types
    assert "DO-NOT-ECHO-TITLE" not in json.dumps(body)
    assert _snapshot_tree(alerts_base) == before
    assert not (alerts_base / LEDGER_RELATIVE_DIR / LEDGER_FILENAME).exists()


def test_us029_emit_fail_closed_and_idempotent_ledger(
    alerts_base: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_ENABLED, "false")
    _write_campaign(
        alerts_base,
        CAMPAIGN_STALE,
        state="validated",
        source_status={
            "location": "queued",
            "execution_state": "stale",
            "recovery_classification": "requeue_required",
        },
    )
    _write_calendar(
        alerts_base,
        [
            _calendar_item(
                "delayed-emit",
                status="scheduled",
                due_at_utc="2026-07-17T10:00:00Z",
            )
        ],
    )
    before = _snapshot_tree(alerts_base)
    mock_client = MagicMock()
    disabled = evaluate_flow_a_operational_alerts(
        alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    mock_client.post.assert_not_called()
    assert disabled.emission.status == EMISSION_STATUS_DISABLED
    assert any(
        a.alert_type == ALERT_PARTIAL_CALENDAR_EXECUTION for a in disabled.alerts
    )
    assert any(a.alert_type == ALERT_STALE_CAMPAIGN for a in disabled.alerts)
    assert _snapshot_tree(alerts_base) == before

    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_ENABLED, "true")
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_WEBHOOK_URL, WEBHOOK_URL)
    mock_client.post.return_value = httpx.Response(200, json={"ok": True})
    first = evaluate_flow_a_operational_alerts(
        alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    assert first.emission.status == EMISSION_STATUS_EMITTED
    us029_fingerprints = {
        a.fingerprint
        for a in first.alerts
        if a.alert_type
        in {
            ALERT_PARTIAL_CALENDAR_EXECUTION,
            ALERT_STALE_CAMPAIGN,
        }
    }
    assert us029_fingerprints
    assert us029_fingerprints <= set(first.emission.emitted_fingerprints)

    mock_client.reset_mock()
    second = evaluate_flow_a_operational_alerts(
        alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    mock_client.post.assert_not_called()
    assert second.emission.status == EMISSION_STATUS_ALREADY_EMITTED
    assert us029_fingerprints <= set(second.emission.already_emitted_fingerprints)


def test_unhealthy_worker_alert_when_folders_not_ready(degraded_alerts_base: Path):
    with (
        patch("httpx.request") as external_http,
        patch("httpx.Client") as http_client_cls,
        patch(
            "silverman_blog_linkedin.flow_a_operational_alerts.validate_folders",
            wraps=__import__(
                "silverman_blog_linkedin.paths", fromlist=["validate_folders"]
            ).validate_folders,
        ) as validate_folders_mock,
    ):
        result = evaluate_flow_a_operational_alerts(
            degraded_alerts_base, now_utc=NOW, emit=False
        )
    validate_folders_mock.assert_called()
    external_http.assert_not_called()
    http_client_cls.assert_not_called()
    body = result.to_dict()
    by_type = _alerts_by_type(body)
    assert len(by_type[ALERT_UNHEALTHY_WORKER]) == 1
    alert = by_type[ALERT_UNHEALTHY_WORKER][0]
    assert alert["severity"] == SEVERITY_ERROR
    assert alert["error_codes"] == sorted(alert["error_codes"])
    assert "editorial_folder_not_ready:metadata/backups" in alert["error_codes"]
    assert "editorial_folder_not_ready:prompts" in alert["error_codes"]
    assert alert["fingerprint"].startswith(
        f"{ALERT_UNHEALTHY_WORKER}:folders_not_ready:"
    )
    assert "campaign_id" not in alert
    assert str(degraded_alerts_base) not in json.dumps(body)
    assert body["summary"]["counts"][ALERT_UNHEALTHY_WORKER] == 1


def test_healthy_folders_produce_no_unhealthy_worker(alerts_base: Path):
    result = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    body = result.to_dict()
    assert ALERT_UNHEALTHY_WORKER not in _alerts_by_type(body)
    assert body["summary"]["counts"][ALERT_UNHEALTHY_WORKER] == 0


def test_failed_n8n_workflow_after_report_not_from_failed_run_alone(
    alerts_base: Path,
):
    _write_run(
        alerts_base,
        "run-failed-alone",
        status="failed",
        errors=["blog_image_generation_comfyui_failed"],
    )
    before_report = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    before_body = before_report.to_dict()
    assert ALERT_FAILED_N8N_WORKFLOW not in _alerts_by_type(before_body)
    assert before_body["summary"]["counts"][ALERT_FAILED_N8N_WORKFLOW] == 0

    report = report_orchestration_failure(
        alerts_base,
        workflow_id=WORKFLOW_ID,
        reason_code=ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED,
        observed_at_utc=NOW,
        execution_id="exec-123",
    )
    assert report.created is True
    store_path = alerts_base / LEDGER_RELATIVE_DIR / ORCHESTRATION_FAILURES_FILENAME
    assert store_path.is_file()
    assert not (alerts_base / LEDGER_RELATIVE_DIR / LEDGER_FILENAME).exists()

    after = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    body = after.to_dict()
    by_type = _alerts_by_type(body)
    alerts = by_type[ALERT_FAILED_N8N_WORKFLOW]
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert["workflow_id"] == WORKFLOW_ID
    assert alert["execution_id"] == "exec-123"
    assert alert["error_codes"] == [ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED]
    assert alert["severity"] == SEVERITY_ERROR
    assert alert["fingerprint"] == (
        f"{ALERT_FAILED_N8N_WORKFLOW}:{WORKFLOW_ID}:"
        f"{ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED}:exec-123"
    )
    assert body["summary"]["counts"][ALERT_FAILED_N8N_WORKFLOW] == 1


def test_report_orchestration_failure_http_auth_validation_idempotency(
    alerts_base: Path,
):
    client = TestClient(create_app(make_settings(alerts_base)))
    campaign_path = alerts_base / "metadata/campaigns"
    campaign_before = _snapshot_tree(alerts_base)

    with patch(
        "silverman_blog_linkedin.main.report_orchestration_failure"
    ) as report:
        assert (
            client.post(
                "/flow-a/operational-alerts/report-orchestration-failure",
                json={
                    "workflow_id": WORKFLOW_ID,
                    "reason_code": ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED,
                },
            ).status_code
            == 401
        )
        report.assert_not_called()

    invalid_reason = client.post(
        "/flow-a/operational-alerts/report-orchestration-failure",
        headers=auth_header(),
        json={
            "workflow_id": WORKFLOW_ID,
            "reason_code": "not_allowlisted",
        },
    )
    assert invalid_reason.status_code == 422

    invalid_observed = client.post(
        "/flow-a/operational-alerts/report-orchestration-failure",
        headers=auth_header(),
        json={
            "workflow_id": WORKFLOW_ID,
            "reason_code": ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED,
            "observed_at_utc": "2026-07-17T12:00:00+00:00",
        },
    )
    assert invalid_observed.status_code == 422

    payload = {
        "workflow_id": WORKFLOW_ID,
        "reason_code": ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED,
        "observed_at_utc": NOW,
        "execution_id": "exec-http-1",
        "node_name": "HTTP-Request",
        "api_key": "NEVER-PERSIST-THIS",
    }
    # extra=forbid should reject secrets-shaped extra fields
    forbidden_extra = client.post(
        "/flow-a/operational-alerts/report-orchestration-failure",
        headers=auth_header(),
        json=payload,
    )
    assert forbidden_extra.status_code == 422

    safe_payload = {
        "workflow_id": WORKFLOW_ID,
        "reason_code": ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED,
        "observed_at_utc": NOW,
        "execution_id": "exec-http-1",
        "node_name": "HTTP-Request",
    }
    first = client.post(
        "/flow-a/operational-alerts/report-orchestration-failure",
        headers=auth_header(),
        json=safe_payload,
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["created"] is True
    assert first_body["workflow_id"] == WORKFLOW_ID
    assert "fingerprint" in first_body

    second = client.post(
        "/flow-a/operational-alerts/report-orchestration-failure",
        headers=auth_header(),
        json=safe_payload,
    )
    assert second.status_code == 200
    assert second.json()["created"] is False
    assert second.json()["fingerprint"] == first_body["fingerprint"]

    store = json.loads(
        (
            alerts_base / LEDGER_RELATIVE_DIR / ORCHESTRATION_FAILURES_FILENAME
        ).read_text(encoding="utf-8")
    )
    assert len(store["entries"]) == 1
    assert not (alerts_base / LEDGER_RELATIVE_DIR / LEDGER_FILENAME).exists()
    # Lifecycle campaign/run folders unchanged aside from orchestration-failures store
    after = _snapshot_tree(alerts_base)
    for relative, meta in campaign_before.items():
        if relative.startswith("metadata/operational-alerts/"):
            continue
        assert after[relative] == meta
    assert list(campaign_path.iterdir()) == []


def test_us030_emit_fail_closed_and_idempotent_ledger(
    degraded_alerts_base: Path, monkeypatch: pytest.MonkeyPatch
):
    report_orchestration_failure(
        degraded_alerts_base,
        workflow_id=WORKFLOW_ID,
        reason_code=ORCHESTRATION_REASON_N8N_WORKFLOW_FAILED,
        observed_at_utc=NOW,
        execution_id="exec-emit-1",
    )
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_ENABLED, "false")
    mock_client = MagicMock()
    disabled = evaluate_flow_a_operational_alerts(
        degraded_alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    mock_client.post.assert_not_called()
    assert disabled.emission.status == EMISSION_STATUS_DISABLED
    us030_types = {
        a.alert_type
        for a in disabled.alerts
        if a.alert_type in {ALERT_UNHEALTHY_WORKER, ALERT_FAILED_N8N_WORKFLOW}
    }
    assert us030_types == {ALERT_UNHEALTHY_WORKER, ALERT_FAILED_N8N_WORKFLOW}

    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_ENABLED, "true")
    monkeypatch.setenv(ENV_OPERATIONAL_ALERTS_WEBHOOK_URL, WEBHOOK_URL)
    mock_client.post.return_value = httpx.Response(200, json={"ok": True})
    first = evaluate_flow_a_operational_alerts(
        degraded_alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    assert first.emission.status == EMISSION_STATUS_EMITTED
    us030_fingerprints = {
        a.fingerprint
        for a in first.alerts
        if a.alert_type in {ALERT_UNHEALTHY_WORKER, ALERT_FAILED_N8N_WORKFLOW}
    }
    assert us030_fingerprints
    assert us030_fingerprints <= set(first.emission.emitted_fingerprints)
    campaign_files = list((degraded_alerts_base / "metadata/campaigns").iterdir())
    assert campaign_files == []

    mock_client.reset_mock()
    second = evaluate_flow_a_operational_alerts(
        degraded_alerts_base,
        now_utc=NOW,
        emit=True,
        http_client=mock_client,
    )
    mock_client.post.assert_not_called()
    assert second.emission.status == EMISSION_STATUS_ALREADY_EMITTED
    assert us030_fingerprints <= set(second.emission.already_emitted_fingerprints)


def test_evaluate_does_not_http_loopback_to_health(alerts_base: Path):
    with patch(
        "silverman_blog_linkedin.main.validate_folders"
    ) as health_route_validate:
        # evaluate uses paths.validate_folders via alerts module, not main route
        result = evaluate_flow_a_operational_alerts(alerts_base, now_utc=NOW)
    health_route_validate.assert_not_called()
    assert result.summary["counts"][ALERT_UNHEALTHY_WORKER] == 0
    assert result.summary["counts"][ALERT_FAILED_N8N_WORKFLOW] == 0
