"""US-081: Flow B promote pending-approval → ready/."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.flow_b_blog_draft_approval import (
    STATUS_APPROVED,
    STATUS_PENDING_APPROVAL,
    STATUS_REJECTED,
)
from silverman_blog_linkedin.flow_b_blog_draft_promotion import (
    ERROR_DRAFT_NOT_APPROVED,
    ERROR_DRAFT_PAIR_INCOMPLETE,
    ERROR_DRAFT_REJECTED,
    ERROR_READY_COLLISION,
    STATUS_PROMOTED,
    promote_pending_approval_draft,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

PROMOTE_PATH = "/flow-b/pending-approval-drafts/{draft_id}/promote"
LIST_PATH = "/flow-b/pending-approval-drafts"


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
    status: str = STATUS_APPROVED,
    with_png: bool = True,
    extra: dict[str, Any] | None = None,
) -> None:
    pending = base / "blog-posts" / "pending-approval"
    md = pending / f"{slug}.md"
    png = pending / f"{slug}.png"
    meta = pending / f"{slug}.flow-b.json"
    md.write_text(
        f"---\ntitle: Promote me\n---\n\n# Promote me\n\nBody.\n",
        encoding="utf-8",
    )
    if with_png:
        png.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    payload: dict[str, Any] = {
        "flow": "flow_b",
        "status": status,
        "topic_id": f"topic-{slug}",
        "thesis": "Authority thesis",
        "slug": slug,
        "blog_relative_path": f"blog-posts/pending-approval/{slug}.md",
        "image_relative_path": f"blog-posts/pending-approval/{slug}.png",
        "image_status": "generated" if with_png else "failed",
        "approved_at_utc": "2026-07-19T15:00:00Z",
        "approved_by": "silverio",
        "target_week": "2026-W30",
        "empty_days": ["2026-07-20", "2026-07-22"],
    }
    if extra:
        payload.update(extra)
    meta.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _snapshot(dir_path: Path) -> set[str]:
    if not dir_path.is_dir():
        return set()
    return {p.name for p in dir_path.iterdir() if p.is_file()}


def test_promote_moves_trio_with_metadata(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="promo-one")
    result = promote_pending_approval_draft(
        base, "promo-one", promoted_by="operator-a"
    )
    assert result.status == STATUS_PROMOTED
    assert result.promoted is True
    assert result.flow_a_eligible is True
    assert result.approved_at_utc == "2026-07-19T15:00:00Z"
    assert result.approved_by == "silverio"
    assert result.promoted_by == "operator-a"
    assert result.origin == "flow_b"
    assert result.target_week == "2026-W30"
    assert result.empty_days == ["2026-07-20", "2026-07-22"]

    ready = base / "blog-posts" / "ready"
    pending = base / "blog-posts" / "pending-approval"
    assert (ready / "promo-one.md").is_file()
    assert (ready / "promo-one.png").is_file()
    assert (ready / "promo-one.flow-b.json").is_file()
    assert not (pending / "promo-one.md").exists()
    assert not (pending / "promo-one.png").exists()
    assert not (pending / "promo-one.flow-b.json").exists()

    sidecar = json.loads((ready / "promo-one.flow-b.json").read_text(encoding="utf-8"))
    assert sidecar["status"] == STATUS_PROMOTED
    assert sidecar["origin"] == "flow_b"
    assert sidecar["blog_relative_path"] == "blog-posts/ready/promo-one.md"
    assert sidecar["approved_at_utc"] == "2026-07-19T15:00:00Z"
    assert sidecar["promoted_by"] == "operator-a"


def test_idempotent_re_promote(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="idem")
    first = promote_pending_approval_draft(base, "idem")
    assert first.status == STATUS_PROMOTED
    assert first.already_promoted is False
    second = promote_pending_approval_draft(base, "idem")
    assert second.status == STATUS_PROMOTED
    assert second.already_promoted is True
    assert second.promoted is True
    ready_files = _snapshot(base / "blog-posts" / "ready")
    assert ready_files == {"idem.md", "idem.png", "idem.flow-b.json"}


def test_reject_non_approved_and_rejected(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="pending", status=STATUS_PENDING_APPROVAL)
    pending_result = promote_pending_approval_draft(base, "pending")
    assert pending_result.status == "failed"
    assert pending_result.error_code == ERROR_DRAFT_NOT_APPROVED

    _write_package(base, slug="rej", status=STATUS_REJECTED)
    rejected = promote_pending_approval_draft(base, "rej")
    assert rejected.status == "failed"
    assert rejected.error_code == ERROR_DRAFT_REJECTED
    assert not (base / "blog-posts/ready/pending.md").exists()
    assert not (base / "blog-posts/ready/rej.md").exists()


def test_incomplete_pair_and_collision(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="no-png", with_png=False)
    incomplete = promote_pending_approval_draft(base, "no-png")
    assert incomplete.status == "failed"
    assert incomplete.error_code == ERROR_DRAFT_PAIR_INCOMPLETE
    assert not (base / "blog-posts/ready/no-png.md").exists()

    _write_package(base, slug="collide")
    (base / "blog-posts/ready/collide.md").write_text("existing\n", encoding="utf-8")
    collision = promote_pending_approval_draft(base, "collide")
    assert collision.status == "failed"
    assert collision.error_code == ERROR_READY_COLLISION
    assert (base / "blog-posts/pending-approval/collide.md").is_file()


def test_dry_run_no_move(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="dry")
    result = promote_pending_approval_draft(base, "dry", dry_run=True)
    assert result.status == STATUS_PROMOTED
    assert result.dry_run is True
    assert result.blog_relative_path == "blog-posts/ready/dry.md"
    assert (base / "blog-posts/pending-approval/dry.md").is_file()
    assert not (base / "blog-posts/ready/dry.md").exists()


def test_promote_does_not_invoke_flow_a(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="guarded")

    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("Flow A / LinkedIn / Git must not be called from promote")

    monkeypatch.setattr(
        "silverman_blog_linkedin.blog_publish_flow.publish_blog_post", boom
    )
    monkeypatch.setattr(
        "silverman_blog_linkedin.linkedin_package_flow.generate_linkedin_package",
        boom,
    )
    monkeypatch.setattr(
        "silverman_blog_linkedin.linkedin_distribution_schedule.schedule_linkedin_distribution",
        boom,
    )
    result = promote_pending_approval_draft(base, "guarded")
    assert result.status == STATUS_PROMOTED


def test_http_auth_and_promote_success(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="http-promo")
    client = TestClient(create_app(make_settings(base)))
    assert client.post(PROMOTE_PATH.format(draft_id="http-promo"), json={}).status_code == 401

    response = client.post(
        PROMOTE_PATH.format(draft_id="http-promo"),
        headers=auth_header(),
        json={"promoted_by": "ops", "dry_run": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == STATUS_PROMOTED
    assert body["promoted"] is True
    assert body["flow_a_eligible"] is True
    assert body["approved_by"] == "silverio"
    assert (base / "blog-posts/ready/http-promo.md").is_file()


def test_http_not_approved_fails_422(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _write_package(base, slug="still-pending", status=STATUS_PENDING_APPROVAL)
    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        PROMOTE_PATH.format(draft_id="still-pending"),
        headers=auth_header(),
        json={},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["error_code"] == ERROR_DRAFT_NOT_APPROVED


def test_openapi_exposes_promote(tmp_path: Path) -> None:
    app = create_app(make_settings(_editorial_base(tmp_path)))
    paths = {route.path for route in app.routes}
    assert "/flow-b/pending-approval-drafts/{draft_id}/promote" in paths
    # Gap-trigger is owned by US-082 and MAY exist.


def test_no_flow_a_imports_in_promote_module() -> None:
    import silverman_blog_linkedin.flow_b_blog_draft_promotion as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "publish_blog_post" not in source
    assert "schedule_linkedin_distribution" not in source
    assert "publish_linkedin" not in source
