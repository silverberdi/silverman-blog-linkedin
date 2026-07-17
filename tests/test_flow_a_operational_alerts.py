"""Behavioral tests for Flow A operational alerts (US-028)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.flow_a_operational_alerts import (
    ALERT_BLOG_PUBLICATION_FAILURE,
    ALERT_IMAGE_GENERATION_FAILURE,
    ALERT_ITEM_MOVED_TO_ERROR,
    EMISSION_STATUS_ALREADY_EMITTED,
    EMISSION_STATUS_DISABLED,
    EMISSION_STATUS_EMITTED,
    EMISSION_STATUS_MISCONFIGURED,
    EMISSION_STATUS_NOT_REQUESTED,
    LEDGER_FILENAME,
    LEDGER_RELATIVE_DIR,
    evaluate_flow_a_operational_alerts,
)
from silverman_blog_linkedin.flow_a_operational_alerts_config import (
    ENV_OPERATIONAL_ALERTS_ENABLED,
    ENV_OPERATIONAL_ALERTS_WEBHOOK_URL,
    load_flow_a_operational_alerts_settings,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

NOW = "2026-07-17T12:00:00Z"
CAMPAIGN_ERROR = "flow-a-2026-07-17-alerts-error"
CAMPAIGN_COMFYUI = "flow-a-2026-07-17-alerts-comfyui"
CAMPAIGN_BLOG = "flow-a-2026-07-17-alerts-blog"
CAMPAIGN_PREVIEW = "flow-a-2026-07-17-alerts-preview"
WEBHOOK_URL = "https://hooks.example.test/flow-a-alerts"


@pytest.fixture
def alerts_base(tmp_path: Path) -> Path:
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
    _write_json(
        base / "editorial-calendar/calendar.json",
        {"version": 1, "items": []},
    )
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


def test_preview_checkout_codes_excluded_and_no_us029_us030_types(
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
    forbidden = {
        "partial_calendar_execution",
        "linkedin_token_failure",
        "linkedin_publication_failure",
        "stale_campaign",
        "unhealthy_worker",
        "failed_n8n_workflow",
    }
    assert alert_types.isdisjoint(forbidden)


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
