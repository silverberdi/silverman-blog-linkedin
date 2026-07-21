"""US-049: Editorial content backlog store, HTTP API, and Flow B independence."""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.editorial_content_backlog import (
    ERROR_STATUS_INVALID,
    ERROR_STORE_UNAVAILABLE,
    ERROR_TOPIC_REQUIRED,
    create_backlog_item,
    get_backlog_item,
    list_backlog_items,
    update_backlog_item,
    validate_backlog_write_document,
)
from silverman_blog_linkedin.editorial_content_backlog_store import (
    MemoryEditorialContentBacklogStore,
)
from silverman_blog_linkedin.flow_b_calendar_gap_trigger import (
    STATUS_NOOP_DISABLED,
    run_flow_b_gap_trigger,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings import save_gap_operator_settings
from silverman_blog_linkedin.flow_b_topic_discovery import (
    STATUS_TOPICS_DISCOVERED,
    discover_flow_b_topics,
)
from silverman_blog_linkedin.linkedin_config import (
    ENV_PUBLICATION_ENABLED,
    load_linkedin_publication_settings,
)
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.topic_discovery_provider import (
    PROVIDER_DEEPSEEK,
    DiscoveryProviderResult,
)
from tests.conftest import auth_header, create_full_layout, make_settings

BACKLOG_PATH = "/editorial/content-backlog"
SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "silverman_blog_linkedin"

VALID_ITEM = {
    "topic": "Domain-first API boundaries",
    "audience": "Senior engineering leaders",
    "objective": "Show practical trade-offs for remote Solutions Architect roles",
    "format": "both",
    "priority": "high",
    "status": "idea",
    "target_date": "2026-08-01",
    "linkedin_derivatives": [
        {
            "audience_hint": "hiring managers",
            "format_hint": "short practical post",
            "notes": "Link back to the blog after review",
        }
    ],
}

VALID_SETTINGS = {
    "operator_timezone": "America/Chicago",
    "gap_trigger_enabled": False,
    "gap_scan_mode": "next_week",
    "weekly_run_local_day": "friday",
    "weekly_run_local_time": "15:00",
    "min_lead_days": 5,
    "gap_posts_threshold": 0,
    "max_drafts_per_weekly_run": 2,
    "density_max_per_local_day": 2,
}

MINI_CANON = """\
## 2 Brand Positioning {#brand-positioning}

Lead with domain-first design. Referent, not news aggregator.

## 5 Content Pillars {#content-pillars}

Software architecture. Engineering leadership. AI-assisted SDLC.

## 6 Topic Boundaries {#topic-boundaries}

Allowed: architecture decisions with trade-offs.
Forbidden: news commentary and tool-vs-tool hot takes.

## 14 Flow A vs Flow B {#flow-a-vs-flow-b}

Career objective ≥ ~USD 7,000; discovery as referent not news spreader.
"""


class _StubProvider:
    def __init__(self, content: str) -> None:
        self._content = content
        self.calls: list[Any] = []

    @property
    def name(self) -> str:
        return PROVIDER_DEEPSEEK

    def discover_topics(
        self, messages: list[dict[str, str]], *, count: int
    ) -> DiscoveryProviderResult:
        self.calls.append((messages, count))
        return DiscoveryProviderResult(
            content=self._content,
            error_code=None,
            provider=PROVIDER_DEEPSEEK,
        )


def _topics_json(n: int = 1) -> str:
    topics = []
    for i in range(n):
        topics.append(
            {
                "thesis": f"Domain boundaries before ORM choices {i}",
                "referent_positioning": (
                    "Shows senior architecture judgment under delivery pressure"
                ),
                "rationale": "Durable authority theme; not a news chase",
                "pillar_hints": ["Domain-first design"],
                "topic_id": f"topic-domain-boundaries-{i}",
            }
        )
    import json

    return json.dumps({"topics": topics})


def _assert_no_secrets(body: dict[str, Any]) -> None:
    blob = str(body).lower()
    for needle in ("password", "api_key", "secret", "bearer ", "postgresql://"):
        assert needle not in blob


def _editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    return base


def _write_canon(tmp_path: Path) -> Path:
    canon = tmp_path / "authority-brief.md"
    canon.write_text(MINI_CANON, encoding="utf-8")
    return canon


def test_memory_create_list_get_update_round_trip(
    isolate_editorial_content_backlog_store: MemoryEditorialContentBacklogStore,
) -> None:
    created, errors = create_backlog_item(VALID_ITEM)
    assert errors == []
    assert created is not None
    item_id = created.item["item_id"]
    assert created.item["row_version"] == 1
    assert created.item["linkedin_derivatives"][0]["audience_hint"] == "hiring managers"

    listed, list_errors = list_backlog_items()
    assert list_errors == []
    assert len(listed) == 1
    assert listed[0].item["item_id"] == item_id

    got, get_errors = get_backlog_item(item_id)
    assert get_errors == []
    assert got is not None
    assert got.item["topic"] == VALID_ITEM["topic"]

    updated, update_errors = update_backlog_item(
        item_id,
        {**VALID_ITEM, "status": "planned", "priority": "medium"},
        expected_row_version=1,
    )
    assert update_errors == []
    assert updated is not None
    assert updated.item["status"] == "planned"
    assert updated.item["priority"] == "medium"
    assert updated.item["row_version"] == 2


def test_empty_list_is_success_not_failure(
    isolate_editorial_content_backlog_store: MemoryEditorialContentBacklogStore,
) -> None:
    items, errors = list_backlog_items()
    assert errors == []
    assert items == []


def test_missing_topic_rejected_without_partial_persist(
    isolate_editorial_content_backlog_store: MemoryEditorialContentBacklogStore,
) -> None:
    snapshot, errors = create_backlog_item({**VALID_ITEM, "topic": "  "})
    assert snapshot is None
    assert any(e["code"] == ERROR_TOPIC_REQUIRED for e in errors)
    items, _ = list_backlog_items()
    assert items == []


def test_invalid_status_and_target_date_rejected() -> None:
    status_errors = validate_backlog_write_document({**VALID_ITEM, "status": "queued"})
    assert any(e["code"] == ERROR_STATUS_INVALID for e in status_errors)

    date_errors = validate_backlog_write_document(
        {**VALID_ITEM, "target_date": "2026/08/01"}
    )
    assert any(e["field"] == "target_date" for e in date_errors)


def test_create_without_dependency_fields_succeeds(
    isolate_editorial_content_backlog_store: MemoryEditorialContentBacklogStore,
) -> None:
    """Dependencies and ranks are optional; empty deps + default rank are valid."""
    snapshot, errors = create_backlog_item(VALID_ITEM)
    assert errors == []
    assert snapshot is not None
    body = snapshot.to_response_dict()
    assert body["depends_on_item_ids"] == []
    assert isinstance(body["queue_rank"], int)
    assert body["queue_rank"] >= 0


def test_dependency_round_trip_and_empty_deps(
    isolate_editorial_content_backlog_store: MemoryEditorialContentBacklogStore,
) -> None:
    base, errors = create_backlog_item({**VALID_ITEM, "topic": "Foundation topic"})
    assert errors == []
    assert base is not None
    base_id = base.item["item_id"]

    dependent, dep_errors = create_backlog_item(
        {
            **VALID_ITEM,
            "topic": "Follow-on topic",
            "depends_on_item_ids": [base_id],
        }
    )
    assert dep_errors == []
    assert dependent is not None
    assert dependent.item["depends_on_item_ids"] == [base_id]

    empty_deps, empty_errors = create_backlog_item(
        {**VALID_ITEM, "topic": "Independent", "depends_on_item_ids": []}
    )
    assert empty_errors == []
    assert empty_deps is not None
    assert empty_deps.item["depends_on_item_ids"] == []


def test_dangling_self_and_cycle_deps_rejected(
    isolate_editorial_content_backlog_store: MemoryEditorialContentBacklogStore,
) -> None:
    from silverman_blog_linkedin.editorial_content_backlog import (
        ERROR_DEPENDENCY_CYCLE,
        ERROR_DEPENDENCY_NOT_FOUND,
        ERROR_DEPENDENCY_SELF,
    )

    a, _ = create_backlog_item({**VALID_ITEM, "topic": "A"})
    b, _ = create_backlog_item({**VALID_ITEM, "topic": "B"})
    assert a is not None and b is not None
    a_id = a.item["item_id"]
    b_id = b.item["item_id"]

    dangling, dang_errors = create_backlog_item(
        {
            **VALID_ITEM,
            "topic": "Dangling",
            "depends_on_item_ids": ["missing-id-xyz"],
        }
    )
    assert dangling is None
    assert any(e["code"] == ERROR_DEPENDENCY_NOT_FOUND for e in dang_errors)

    self_dep, self_errors = update_backlog_item(
        a_id,
        {**VALID_ITEM, "topic": "A", "depends_on_item_ids": [a_id]},
        expected_row_version=1,
    )
    assert self_dep is None
    assert any(e["code"] == ERROR_DEPENDENCY_SELF for e in self_errors)
    unchanged, _ = get_backlog_item(a_id)
    assert unchanged is not None
    assert unchanged.item["depends_on_item_ids"] == []

    updated_b, b_errors = update_backlog_item(
        b_id,
        {**VALID_ITEM, "topic": "B", "depends_on_item_ids": [a_id]},
        expected_row_version=1,
    )
    assert b_errors == []
    assert updated_b is not None

    cycle, cycle_errors = update_backlog_item(
        a_id,
        {**VALID_ITEM, "topic": "A", "depends_on_item_ids": [b_id]},
        expected_row_version=1,
    )
    assert cycle is None
    assert any(e["code"] == ERROR_DEPENDENCY_CYCLE for e in cycle_errors)
    still_a, _ = get_backlog_item(a_id)
    assert still_a is not None
    assert still_a.item["depends_on_item_ids"] == []


def test_priority_and_queue_rank_update_and_list_order(
    isolate_editorial_content_backlog_store: MemoryEditorialContentBacklogStore,
) -> None:
    from silverman_blog_linkedin.editorial_content_backlog import (
        ERROR_QUEUE_RANK_INVALID,
        reorder_backlog_items,
    )

    first, _ = create_backlog_item({**VALID_ITEM, "topic": "First", "priority": "low"})
    second, _ = create_backlog_item(
        {**VALID_ITEM, "topic": "Second", "priority": "high"}
    )
    assert first is not None and second is not None

    listed, list_errors = list_backlog_items()
    assert list_errors == []
    assert [row.item["topic"] for row in listed] == ["First", "Second"]
    assert listed[0].item["queue_rank"] < listed[1].item["queue_rank"]

    updated, update_errors = update_backlog_item(
        second.item["item_id"],
        {
            **VALID_ITEM,
            "topic": "Second",
            "priority": "medium",
            "queue_rank": 0,
            "depends_on_item_ids": [],
        },
        expected_row_version=1,
    )
    assert update_errors == []
    assert updated is not None
    assert updated.item["priority"] == "medium"
    assert updated.item["queue_rank"] == 0

    reordered_list, reorder_errors = reorder_backlog_items(
        [second.item["item_id"], first.item["item_id"]]
    )
    assert reorder_errors == []
    assert reordered_list is not None
    assert [row.item["topic"] for row in reordered_list] == ["Second", "First"]
    assert reordered_list[0].item["queue_rank"] == 0
    assert reordered_list[1].item["queue_rank"] == 1

    bad_rank = validate_backlog_write_document({**VALID_ITEM, "queue_rank": -1})
    assert any(e["code"] == ERROR_QUEUE_RANK_INVALID for e in bad_rank)


def test_http_list_requires_auth(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    assert client.get(BACKLOG_PATH).status_code == 401


def test_http_empty_list_success(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get(BACKLOG_PATH, headers=auth_header())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["items"] == []
    assert body["count"] == 0
    _assert_no_secrets(body)


def test_http_create_get_update_round_trip(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    created = client.post(BACKLOG_PATH, headers=auth_header(), json=VALID_ITEM)
    assert created.status_code == 200
    body = created.json()
    item_id = body["item_id"]
    assert body["topic"] == VALID_ITEM["topic"]
    assert body["row_version"] == 1
    assert len(body["linkedin_derivatives"]) == 1
    _assert_no_secrets(body)

    detail = client.get(f"{BACKLOG_PATH}/{item_id}", headers=auth_header())
    assert detail.status_code == 200
    assert detail.json()["item_id"] == item_id

    updated = client.put(
        f"{BACKLOG_PATH}/{item_id}",
        headers=auth_header(),
        json={
            **VALID_ITEM,
            "status": "in_progress",
            "expected_row_version": 1,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["row_version"] == 2

    listed = client.get(BACKLOG_PATH, headers=auth_header())
    assert listed.status_code == 200
    assert listed.json()["count"] == 1


def test_http_validation_422_no_partial(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    seed = client.post(BACKLOG_PATH, headers=auth_header(), json=VALID_ITEM)
    assert seed.status_code == 200

    bad = client.post(
        BACKLOG_PATH,
        headers=auth_header(),
        json={**VALID_ITEM, "status": "not-a-status"},
    )
    assert bad.status_code == 422
    assert any(
        e.get("code") == ERROR_STATUS_INVALID
        for e in bad.json()["detail"]["errors"]
    )

    listed = client.get(BACKLOG_PATH, headers=auth_header())
    assert listed.json()["count"] == 1


def test_http_store_unavailable_distinct_from_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _BrokenStore(MemoryEditorialContentBacklogStore):
        def list_items(self, **kwargs: Any):  # type: ignore[no-untyped-def]
            return [], [ERROR_STORE_UNAVAILABLE]

    from silverman_blog_linkedin.editorial_content_backlog_store import (
        reset_editorial_content_backlog_store_for_tests,
    )

    reset_editorial_content_backlog_store_for_tests(_BrokenStore())
    client = TestClient(create_app(make_settings(tmp_path)))
    response = client.get(BACKLOG_PATH, headers=auth_header())
    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["errors"][0]["code"] == ERROR_STORE_UNAVAILABLE
    assert "items" not in body or body.get("items") is None
    _assert_no_secrets(body)


def test_create_does_not_enable_linkedin_or_write_packages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_PUBLICATION_ENABLED, "false")
    before = load_linkedin_publication_settings().settings.publication_enabled
    assert before is False

    base = _editorial_base(tmp_path)
    client = TestClient(create_app(make_settings(base)))
    response = client.post(BACKLOG_PATH, headers=auth_header(), json=VALID_ITEM)
    assert response.status_code == 200

    assert os.environ.get(ENV_PUBLICATION_ENABLED) == "false"
    after = load_linkedin_publication_settings().settings.publication_enabled
    assert after is False

    review = base / "linkedin-posts" / "review"
    approved = base / "linkedin-posts" / "approved"
    published = base / "linkedin-posts" / "published"
    for folder in (review, approved, published):
        if folder.exists():
            assert list(folder.iterdir()) == []


def test_no_discovery_seed_routes(tmp_path: Path) -> None:
    app = create_app(make_settings(tmp_path))
    paths = {getattr(route, "path", None) for route in app.routes}
    assert BACKLOG_PATH in paths
    assert f"{BACKLOG_PATH}/reorder" in paths
    forbidden = {
        "/editorial/content-backlog/dependencies",
        "/editorial/content-backlog/reprioritize",
        "/flow-b/discover-topics/from-backlog",
        "/flow-b/seed-from-backlog",
    }
    assert not (paths & forbidden)


def test_http_dependency_and_reorder(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(tmp_path)))
    a = client.post(
        BACKLOG_PATH,
        headers=auth_header(),
        json={**VALID_ITEM, "topic": "A"},
    )
    b = client.post(
        BACKLOG_PATH,
        headers=auth_header(),
        json={**VALID_ITEM, "topic": "B"},
    )
    assert a.status_code == 200 and b.status_code == 200
    a_id = a.json()["item_id"]
    b_id = b.json()["item_id"]
    assert a.json()["depends_on_item_ids"] == []
    assert isinstance(a.json()["queue_rank"], int)

    linked = client.put(
        f"{BACKLOG_PATH}/{b_id}",
        headers=auth_header(),
        json={
            **VALID_ITEM,
            "topic": "B",
            "depends_on_item_ids": [a_id],
            "expected_row_version": 1,
        },
    )
    assert linked.status_code == 200
    assert linked.json()["depends_on_item_ids"] == [a_id]

    cycle = client.put(
        f"{BACKLOG_PATH}/{a_id}",
        headers=auth_header(),
        json={
            **VALID_ITEM,
            "topic": "A",
            "depends_on_item_ids": [b_id],
            "expected_row_version": 1,
        },
    )
    assert cycle.status_code == 422
    assert any(
        e.get("code") == "dependency_cycle"
        for e in cycle.json()["detail"]["errors"]
    )

    reordered = client.put(
        f"{BACKLOG_PATH}/reorder",
        headers=auth_header(),
        json={"ordered_item_ids": [b_id, a_id]},
    )
    assert reordered.status_code == 200
    topics = [row["topic"] for row in reordered.json()["items"]]
    assert topics[:2] == ["B", "A"]
    _assert_no_secrets(reordered.json())

    unknown = client.put(
        f"{BACKLOG_PATH}/reorder",
        headers=auth_header(),
        json={"ordered_item_ids": [a_id, "missing-id"]},
    )
    assert unknown.status_code == 404


def test_http_create_does_not_enable_linkedin_on_deps(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_PUBLICATION_ENABLED, "false")
    base = _editorial_base(tmp_path)
    client = TestClient(create_app(make_settings(base)))
    first = client.post(
        BACKLOG_PATH, headers=auth_header(), json={**VALID_ITEM, "topic": "A"}
    )
    assert first.status_code == 200
    second = client.post(
        BACKLOG_PATH,
        headers=auth_header(),
        json={
            **VALID_ITEM,
            "topic": "B",
            "depends_on_item_ids": [first.json()["item_id"]],
        },
    )
    assert second.status_code == 200
    assert os.environ.get(ENV_PUBLICATION_ENABLED) == "false"
    review = base / "linkedin-posts" / "review"
    if review.exists():
        assert list(review.iterdir()) == []


def test_flow_b_modules_do_not_import_backlog() -> None:
    """Hard independence: discovery / draft / gap-trigger must not import backlog."""
    modules = (
        "flow_b_topic_discovery.py",
        "flow_b_blog_draft_generation.py",
        "flow_b_calendar_gap_trigger.py",
    )
    for name in modules:
        tree = ast.parse((SRC_ROOT / name).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        assert not any("editorial_content_backlog" in mod for mod in imported), name


def test_discovery_succeeds_with_empty_backlog(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    items, errors = list_backlog_items()
    assert errors == []
    assert items == []

    stub = _StubProvider(_topics_json(1))
    result = discover_flow_b_topics(
        base,
        count=1,
        provider=stub,
        canon_path=canon,
    )
    assert result.status == STATUS_TOPICS_DISCOVERED
    assert result.error_code != "backlog_required"
    assert "backlog" not in (result.error_code or "").lower()


def test_gap_trigger_noop_with_empty_backlog(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    save_gap_operator_settings(VALID_SETTINGS)
    items, errors = list_backlog_items()
    assert errors == []
    assert items == []

    result = run_flow_b_gap_trigger(
        base,
        now_utc="2026-07-17T20:00:00Z",
        environ={"SILVERMAN_OPERATOR_TIMEZONE": "America/Chicago"},
    )
    assert result.status == STATUS_NOOP_DISABLED
    assert result.error_code != "backlog_required"
    assert "backlog" not in str(getattr(result, "error_code", "") or "").lower()


def test_flow_b_independence_with_unused_deps_and_ranks(
    isolate_editorial_content_backlog_store: MemoryEditorialContentBacklogStore,
    tmp_path: Path,
) -> None:
    """Backlog items with deps/ranks must not be required by discovery or gap-trigger."""
    first, _ = create_backlog_item({**VALID_ITEM, "topic": "A", "priority": "high"})
    second, _ = create_backlog_item(
        {
            **VALID_ITEM,
            "topic": "B",
            "depends_on_item_ids": [first.item["item_id"]] if first else [],
            "priority": "low",
        }
    )
    assert first is not None and second is not None
    assert second.item["depends_on_item_ids"] == [first.item["item_id"]]

    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    stub = _StubProvider(_topics_json(1))
    discovery = discover_flow_b_topics(
        base,
        count=1,
        provider=stub,
        canon_path=canon,
    )
    assert discovery.status == STATUS_TOPICS_DISCOVERED
    assert "backlog" not in (discovery.error_code or "").lower()

    save_gap_operator_settings(VALID_SETTINGS)
    gap = run_flow_b_gap_trigger(
        base,
        now_utc="2026-07-17T20:00:00Z",
        environ={"SILVERMAN_OPERATOR_TIMEZONE": "America/Chicago"},
    )
    assert gap.status == STATUS_NOOP_DISABLED
    assert "backlog" not in str(getattr(gap, "error_code", "") or "").lower()
