"""US-080: Flow B pending-approval list / detail / approve / reject."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.flow_b_blog_draft_approval import (
    ERROR_DRAFT_ALREADY_REJECTED,
    ERROR_PATH_TRAVERSAL,
    STATUS_APPROVED,
    STATUS_PENDING_APPROVAL,
    STATUS_REJECTED,
    approve_pending_approval_draft,
    list_pending_approval_drafts,
    reject_pending_approval_draft,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

LIST_PATH = "/flow-b/pending-approval-drafts"
GENERATE_PATH = "/flow-b/generate-blog-drafts"
DISCOVER_PATH = "/flow-b/discover-topics"
GAPS_PATH = "/flow-b/calendar-gaps"
SETTINGS_PATH = "/flow-b/gap-operator-settings"


def _editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    for relative in (
        "blog-posts/ready",
        "blog-posts/pending-approval",
        "blog-posts/processed",
        "metadata/campaigns",
        "metadata/runs",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    return base


def _write_package(
    base: Path,
    *,
    slug: str,
    status: str = STATUS_PENDING_APPROVAL,
    title: str = "Authority thesis title",
    extra: dict[str, Any] | None = None,
) -> None:
    pending = base / "blog-posts" / "pending-approval"
    md = pending / f"{slug}.md"
    png = pending / f"{slug}.png"
    meta = pending / f"{slug}.flow-b.json"
    md.write_text(
        f"---\ntitle: {title}\n---\n\n# {title}\n\nBody for operator review.\n",
        encoding="utf-8",
    )
    png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    payload: dict[str, Any] = {
        "flow": "flow_b",
        "status": status,
        "topic_id": f"topic-{slug}",
        "thesis": "Operators need clear authority framing",
        "referent_positioning": "Senior architect referent",
        "rationale": "Positions for leadership conversations",
        "generated_at_utc": "2026-07-19T12:00:00Z",
        "provider": "deepseek",
        "slug": slug,
        "blog_relative_path": f"blog-posts/pending-approval/{slug}.md",
        "image_relative_path": f"blog-posts/pending-approval/{slug}.png",
        "image_status": "generated",
        "anti_ai_status": "passed",
        "target_week": "2026-W30",
        "empty_days": ["2026-07-20", "2026-07-22"],
    }
    if extra:
        payload.update(extra)
    meta.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _snapshot_ready(base: Path) -> set[str]:
    ready = base / "blog-posts" / "ready"
    if not ready.is_dir():
        return set()
    return {p.name for p in ready.iterdir()}


def test_list_empty_folder_ok(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    result = list_pending_approval_drafts(base)
    assert result.status == "ok"
    assert result.drafts == []
    assert result.to_dict()["count"] == 0


def test_list_includes_discovery_and_gap_fields(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="draft-one")
    result = list_pending_approval_drafts(base)
    assert len(result.drafts) == 1
    item = result.drafts[0]
    assert item.draft_id == "draft-one"
    assert item.title == "Authority thesis title"
    assert item.topic_id == "topic-draft-one"
    assert item.thesis
    assert item.referent_positioning
    assert item.rationale
    assert item.status == STATUS_PENDING_APPROVAL
    assert item.target_week == "2026-W30"
    assert item.empty_days == ["2026-07-20", "2026-07-22"]
    assert item.image_url == "/flow-b/pending-approval-drafts/draft-one/image"


def test_default_list_excludes_rejected(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="keep-me")
    _write_package(base, slug="rejected-me", status=STATUS_REJECTED)
    result = list_pending_approval_drafts(base)
    ids = {d.draft_id for d in result.drafts}
    assert ids == {"keep-me"}
    filtered = list_pending_approval_drafts(base, status_filter=STATUS_REJECTED)
    assert len(filtered.drafts) == 1
    assert filtered.drafts[0].status == STATUS_REJECTED


def test_approve_updates_sidecar_no_ready_writes(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="to-approve")
    before = _snapshot_ready(base)
    result = approve_pending_approval_draft(base, "to-approve", approved_by="silverio")
    assert result.status == STATUS_APPROVED
    assert result.promoted is False
    assert result.promotion_pending is True
    assert result.operator_note
    sidecar = json.loads(
        (base / "blog-posts/pending-approval/to-approve.flow-b.json").read_text(
            encoding="utf-8"
        )
    )
    assert sidecar["status"] == STATUS_APPROVED
    assert sidecar["approved_by"] == "silverio"
    assert "approved_at_utc" in sidecar
    assert (base / "blog-posts/pending-approval/to-approve.md").is_file()
    assert (base / "blog-posts/pending-approval/to-approve.png").is_file()
    assert _snapshot_ready(base) == before


def test_reject_updates_sidecar_no_ready_writes(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="to-reject")
    before = _snapshot_ready(base)
    result = reject_pending_approval_draft(
        base, "to-reject", rejection_reason="Off-voice"
    )
    assert result.status == STATUS_REJECTED
    assert result.promoted is False
    sidecar = json.loads(
        (base / "blog-posts/pending-approval/to-reject.flow-b.json").read_text(
            encoding="utf-8"
        )
    )
    assert sidecar["status"] == STATUS_REJECTED
    assert sidecar["rejection_reason"] == "Off-voice"
    assert _snapshot_ready(base) == before
    default = list_pending_approval_drafts(base)
    assert default.drafts == []


def test_approve_rejected_fails_closed(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="already-rejected", status=STATUS_REJECTED)
    result = approve_pending_approval_draft(base, "already-rejected")
    assert result.status == "failed"
    assert result.error_code == ERROR_DRAFT_ALREADY_REJECTED


def test_reject_can_supersede_approved(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="was-approved", status=STATUS_APPROVED)
    result = reject_pending_approval_draft(base, "was-approved")
    assert result.status == STATUS_REJECTED
    sidecar = json.loads(
        (base / "blog-posts/pending-approval/was-approved.flow-b.json").read_text(
            encoding="utf-8"
        )
    )
    assert sidecar["status"] == STATUS_REJECTED
    assert "approved_at_utc" not in sidecar


def test_dry_run_does_not_mutate(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="dry-approve")
    before = (base / "blog-posts/pending-approval/dry-approve.flow-b.json").read_text(
        encoding="utf-8"
    )
    result = approve_pending_approval_draft(base, "dry-approve", dry_run=True)
    assert result.status == STATUS_APPROVED
    assert result.dry_run is True
    after = (base / "blog-posts/pending-approval/dry-approve.flow-b.json").read_text(
        encoding="utf-8"
    )
    assert after == before


def test_path_traversal_rejected(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    result = approve_pending_approval_draft(base, "../ready/secret")
    assert result.status == "failed"
    assert result.error_code in {ERROR_PATH_TRAVERSAL, "draft_id_invalid"}


def test_http_auth_required(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    client = TestClient(create_app(make_settings(base)))
    assert client.get(LIST_PATH).status_code == 401
    assert client.get(f"{LIST_PATH}/x").status_code == 401
    assert client.get(f"{LIST_PATH}/x/image").status_code == 401
    assert client.post(f"{LIST_PATH}/x/approve", json={}).status_code == 401
    assert client.post(f"{LIST_PATH}/x/reject", json={}).status_code == 401
    assert client.post(f"{LIST_PATH}/x/promote", json={}).status_code == 401


def test_http_list_detail_image_approve_reject(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="http-draft")
    client = TestClient(create_app(make_settings(base)))
    headers = auth_header()

    listed = client.get(LIST_PATH, headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert body["count"] == 1
    assert body["drafts"][0]["thesis"]
    assert body["drafts"][0]["target_week"] == "2026-W30"

    detail = client.get(f"{LIST_PATH}/http-draft", headers=headers)
    assert detail.status_code == 200
    assert "Body for operator review" in detail.json()["body_markdown"]

    image = client.get(f"{LIST_PATH}/http-draft/image", headers=headers)
    assert image.status_code == 200
    assert image.headers["content-type"].startswith("image/png")
    assert image.content.startswith(b"\x89PNG")

    ready_before = _snapshot_ready(base)
    approve = client.post(
        f"{LIST_PATH}/http-draft/approve",
        headers=headers,
        json={"dry_run": False, "approved_by": "operator"},
    )
    assert approve.status_code == 200
    assert approve.json()["status"] == STATUS_APPROVED
    assert approve.json()["promoted"] is False
    assert approve.json()["promotion_pending"] is True
    assert _snapshot_ready(base) == ready_before

    reject = client.post(
        f"{LIST_PATH}/http-draft/reject",
        headers=headers,
        json={"dry_run": False, "rejection_reason": "No"},
    )
    assert reject.status_code == 200
    assert reject.json()["status"] == STATUS_REJECTED
    assert _snapshot_ready(base) == ready_before

    listed_after = client.get(LIST_PATH, headers=headers)
    assert listed_after.json()["count"] == 0


def test_http_missing_draft_fails_closed(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        f"{LIST_PATH}/missing-draft/approve",
        headers=auth_header(),
        json={},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "draft_not_found"


def test_http_traversal_fails_closed(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    client = TestClient(create_app(make_settings(base)))
    response = client.get(
        f"{LIST_PATH}/../ready/escape",
        headers=auth_header(),
    )
    assert response.status_code in {404, 422}


def test_openapi_exposes_routes_and_leaves_prior_contracts(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    app = create_app(make_settings(base))
    paths = {route.path for route in app.routes}
    assert LIST_PATH in paths
    assert f"{LIST_PATH}/{{draft_id}}" in paths
    assert f"{LIST_PATH}/{{draft_id}}/image" in paths
    assert f"{LIST_PATH}/{{draft_id}}/approve" in paths
    assert f"{LIST_PATH}/{{draft_id}}/reject" in paths
    assert f"{LIST_PATH}/{{draft_id}}/promote" in paths
    assert GENERATE_PATH in paths
    assert DISCOVER_PATH in paths
    assert GAPS_PATH in paths
    assert SETTINGS_PATH in paths
    # Promote uses pending-approval-drafts path (US-081); gap-trigger is US-082 and MAY exist
    assert "/flow-b/promote-blog-draft" not in paths


def test_no_flow_a_or_linkedin_publish_imports() -> None:
    import silverman_blog_linkedin.flow_b_blog_draft_approval as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "publish_blog_post" not in source
    assert "schedule_linkedin_distribution" not in source
    assert "publish_linkedin" not in source
    assert "complete_flow_a_ready_path" not in source


def test_approve_does_not_call_flow_a(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="guarded")

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Flow A / LinkedIn publish must not be called")

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.publish_blog_post", boom, raising=False
    )
    result = approve_pending_approval_draft(base, "guarded")
    assert result.status == STATUS_APPROVED
