"""US-082: Flow B calendar gap trigger (orchestration + HTTP + n8n export)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from silverman_blog_linkedin.blog_draft_generation_provider import (
    PROVIDER_DEEPSEEK as DRAFT_PROVIDER,
    BlogDraftProviderResult,
)
from silverman_blog_linkedin.comfyui_client import FakeComfyUIClient
from silverman_blog_linkedin.flow_b_calendar_gap_trigger import (
    STATUS_NOOP_DISABLED,
    STATUS_NOOP_IDEMPOTENT,
    STATUS_NOOP_NO_GAP,
    STATUS_NOOP_OUTSIDE_WINDOW,
    STATUS_TRIGGERED,
    STATUS_WOULD_TRIGGER,
    operator_local_in_weekly_window,
    run_flow_b_gap_trigger,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings import (
    save_gap_operator_settings,
)
from silverman_blog_linkedin.flow_b_gap_trigger_batch_store import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_IN_PROGRESS,
    STALE_IN_PROGRESS_TTL,
    build_gap_trigger_idempotency_key,
    get_gap_trigger_batch_store,
)
from silverman_blog_linkedin.local_day_density import ENV_OPERATOR_TIMEZONE
from silverman_blog_linkedin.main import create_app
from silverman_blog_linkedin.topic_discovery_provider import (
    PROVIDER_DEEPSEEK,
    DiscoveryProviderResult,
)
from tests.conftest import auth_header, make_settings

TRIGGER_PATH = "/flow-b/gap-trigger"
N8N_EXPORT = (
    Path(__file__).resolve().parents[1]
    / "n8n"
    / "workflows"
    / "silverman-blog-linkedin-flow-b-gap-trigger.json"
)

# Friday 15:00 America/Chicago = 2026-07-17T20:00:00Z
NOW_FRIDAY_IN_WINDOW = "2026-07-17T20:00:00Z"
# Friday morning before 15:00 local
NOW_FRIDAY_BEFORE = "2026-07-17T18:00:00Z"  # 13:00 Chicago
# Thursday
NOW_THURSDAY = "2026-07-16T20:00:00Z"
TZ = "America/Chicago"

VALID_SETTINGS = {
    "operator_timezone": TZ,
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

## 7 Blog Post Rules {#blog-post-rules}

Require Markdown + image sibling pair. Practical senior tone.

## 11 Anti-AI-Writing Rules {#anti-ai-writing-rules}

No AI-sounding openings. Flow B generated content uses blocking rules.

## 14 Flow A vs Flow B {#flow-a-vs-flow-b}

Career objective ≥ ~USD 7,000; discovery as referent not news spreader.
"""

GOOD_MARKDOWN_A = """\
---
title: Domain boundaries before ORM choices
date: 2026-07-19
description: Why naming the business comes before picking a database.
image: placeholder.png
flow: flow_b
topic_id: topic-domain-boundaries
---

# Domain boundaries before ORM choices

Teams often reach for an ORM before they agree what the business event is.

The expensive mistake is committing to a schema while the domain language is still mush.
"""

GOOD_MARKDOWN_B = """\
---
title: Governance patterns for AI-assisted SDLC
date: 2026-07-19
description: Guardrails that keep delivery honest.
image: placeholder.png
flow: flow_b
topic_id: topic-ai-governance
---

# Governance patterns for AI-assisted SDLC

Delivery pressure pushes teams to accept AI output without a review contract.

I have watched merge velocity climb while accountability thinned — the fix is gated ownership, not more prompts.
"""


class _StubDiscoveryProvider:
    def __init__(self, *, content: str | None = None, error_code: str | None = None) -> None:
        self._content = content
        self._error_code = error_code
        self.calls: list[tuple[list[dict[str, str]], int]] = []

    @property
    def name(self) -> str:
        return PROVIDER_DEEPSEEK

    def discover_topics(
        self,
        messages: list[dict[str, str]],
        *,
        count: int,
    ) -> DiscoveryProviderResult:
        self.calls.append((messages, count))
        return DiscoveryProviderResult(
            content=self._content,
            error_code=self._error_code,
            provider=PROVIDER_DEEPSEEK,
        )


class _StubDraftProvider:
    def __init__(self, *, contents_by_call: list[str] | None = None) -> None:
        self._contents = list(contents_by_call or [])
        self.calls: list[list[dict[str, str]]] = []

    @property
    def name(self) -> str:
        return DRAFT_PROVIDER

    def generate_blog_draft(
        self,
        messages: list[dict[str, str]],
    ) -> BlogDraftProviderResult:
        self.calls.append(messages)
        content = self._contents.pop(0) if self._contents else GOOD_MARKDOWN_A
        return BlogDraftProviderResult(
            content=content,
            error_code=None,
            provider=DRAFT_PROVIDER,
        )


def _topics_json(n: int = 2) -> str:
    items = [
        {
            "thesis": "Domain boundaries before ORM choices",
            "referent_positioning": (
                "Shows senior architecture judgment under delivery pressure"
            ),
            "rationale": "Durable authority theme; not a news chase",
            "pillar_hints": ["Domain-first design"],
            "topic_id": "topic-domain-boundaries",
        },
        {
            "thesis": "Governance patterns for AI-assisted SDLC",
            "referent_positioning": (
                "Positions Silverio as a referent on AI delivery guardrails"
            ),
            "rationale": "Leadership + architecture transformation angle",
            "pillar_hints": ["AI-assisted SDLC"],
            "topic_id": "topic-ai-governance",
        },
    ]
    return json.dumps({"topics": items[:n]})


def _editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    for relative in (
        "metadata/campaigns",
        "editorial-calendar",
        "blog-posts/ready",
        "blog-posts/pending-approval",
        "blog-posts/processed",
        "linkedin-posts/generated",
        "prompts/flow-b",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    return base


def _write_canon(tmp_path: Path) -> Path:
    path = tmp_path / "canon.md"
    path.write_text(MINI_CANON, encoding="utf-8")
    return path


def _comfy_env(base: Path) -> dict[str, str]:
    return {
        ENV_OPERATOR_TIMEZONE: TZ,
        "SILVERMAN_BLOG_LINKEDIN_BASE_PATH": str(base),
        "SILVERMAN_COMFYUI_IMAGE_ENABLED": "true",
        "SILVERMAN_COMFYUI_BASE_URL": "http://127.0.0.1:8188",
        "SILVERMAN_COMFYUI_API_KEY": "test-key",
        "DEEPSEEK_API_KEY": "test-deepseek-key",
    }


def _enable_trigger(*, max_drafts: int = 2) -> None:
    save_gap_operator_settings(
        {
            **VALID_SETTINGS,
            "gap_trigger_enabled": True,
            "max_drafts_per_weekly_run": max_drafts,
        }
    )


def _assert_no_secrets(body: dict) -> None:
    blob = str(body).lower()
    for needle in (
        "password",
        "api_key",
        "apikey",
        "oauth",
        "token",
        "postgresql://",
        "sk-",
        "secret",
        "test-deepseek-key",
        "test-key",
    ):
        assert needle not in blob


def _pending_files(base: Path) -> set[str]:
    pending = base / "blog-posts" / "pending-approval"
    return {p.name for p in pending.iterdir()} if pending.exists() else set()


def test_window_helper_friday_afternoon() -> None:
    now = datetime(2026, 7, 17, 20, 0, 0, tzinfo=timezone.utc)
    inside, weekday, hhmm, err = operator_local_in_weekly_window(
        now_utc=now,
        operator_timezone=TZ,
        weekly_run_local_day="friday",
        weekly_run_local_time="15:00",
    )
    assert err is None
    assert inside is True
    assert weekday == "friday"
    assert hhmm == "15:00"


def test_window_helper_before_time() -> None:
    now = datetime(2026, 7, 17, 18, 0, 0, tzinfo=timezone.utc)
    inside, weekday, _, err = operator_local_in_weekly_window(
        now_utc=now,
        operator_timezone=TZ,
        weekly_run_local_day="friday",
        weekly_run_local_time="15:00",
    )
    assert err is None
    assert inside is False
    assert weekday == "friday"


def test_disabled_is_noop(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    save_gap_operator_settings(VALID_SETTINGS)
    before = _pending_files(base)
    result = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_FRIDAY_IN_WINDOW,
        environ=_comfy_env(base),
    )
    assert result.status == STATUS_NOOP_DISABLED
    assert result.gap_trigger_enabled is False
    assert _pending_files(base) == before


def test_outside_window_is_noop(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _enable_trigger()
    before = _pending_files(base)
    result = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_FRIDAY_BEFORE,
        environ=_comfy_env(base),
    )
    assert result.status == STATUS_NOOP_OUTSIDE_WINDOW
    assert _pending_files(base) == before

    result2 = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_THURSDAY,
        environ=_comfy_env(base),
    )
    assert result2.status == STATUS_NOOP_OUTSIDE_WINDOW


def test_no_gap_is_noop_without_claim(tmp_path: Path) -> None:
    """Fill next week so detect returns no_gap; no batch claim."""
    base = _editorial_base(tmp_path)
    # Lower lead so all seven days are actionable; fill each with one pending.
    save_gap_operator_settings({**VALID_SETTINGS, "gap_trigger_enabled": True, "min_lead_days": 0})
    campaign_id = "flow-a-2026-07-19-gap-cover"
    variants = []
    for offset, name in enumerate(
        ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    ):
        day = 20 + offset
        variants.append(
            {
                "variant": f"v-{name}",
                "audience": "senior",
                "publish_state": "pending",
                "scheduled_at_utc": f"2026-07-{day:02d}T15:00:00Z",
            }
        )
    campaign = {
        "campaign_id": campaign_id,
        "flow": "flow_a",
        "state": "distribution_scheduled",
        "updated_at": "2026-07-17T10:00:00Z",
        "source_file_status": {
            "location": "processed",
            "execution_state": "idle",
            "recovery_classification": "no_action",
        },
        "variants": variants,
    }
    (base / "metadata/campaigns" / f"{campaign_id}.json").write_text(
        json.dumps(campaign, indent=2) + "\n", encoding="utf-8"
    )
    before = _pending_files(base)
    result = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_FRIDAY_IN_WINDOW,
        environ=_comfy_env(base),
    )
    assert result.status == STATUS_NOOP_NO_GAP
    assert result.batch_status is None
    store = get_gap_trigger_batch_store()
    key = build_gap_trigger_idempotency_key(TZ, "2026-W30")
    row, _ = store.get(key)
    assert row is None
    assert _pending_files(base) == before


def test_enabled_with_gaps_creates_drafts(
    tmp_path: Path,
) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    _enable_trigger(max_drafts=2)
    discovery = _StubDiscoveryProvider(content=_topics_json(2))
    drafts = _StubDraftProvider(contents_by_call=[GOOD_MARKDOWN_A, GOOD_MARKDOWN_B])
    fake = FakeComfyUIClient()

    result = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_FRIDAY_IN_WINDOW,
        environ=_comfy_env(base),
        discovery_provider=discovery,
        draft_provider=drafts,
        comfyui_client=fake,
        canon_path=canon,
    )
    assert result.status == STATUS_TRIGGERED
    assert result.target_week == "2026-W30"
    assert result.empty_days
    assert result.idempotency_key == build_gap_trigger_idempotency_key(TZ, "2026-W30")
    assert len(result.drafts) <= 2
    assert len(discovery.calls) == 1
    assert discovery.calls[0][1] == 2
    pending = base / "blog-posts" / "pending-approval"
    md_files = list(pending.glob("*.md"))
    assert 1 <= len(md_files) <= 2
    sidecar = list(pending.glob("*.flow-b.json"))
    assert sidecar
    meta = json.loads(sidecar[0].read_text(encoding="utf-8"))
    assert meta.get("target_week") == "2026-W30"
    assert meta.get("empty_days")
    # Never wrote ready/
    assert list((base / "blog-posts" / "ready").glob("*")) == []
    store = get_gap_trigger_batch_store()
    row, _ = store.get(result.idempotency_key or "")
    assert row is not None
    assert row["status"] == STATUS_COMPLETED


def test_idempotent_second_call_noop(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    _enable_trigger()
    discovery = _StubDiscoveryProvider(content=_topics_json(2))
    drafts = _StubDraftProvider(contents_by_call=[GOOD_MARKDOWN_A, GOOD_MARKDOWN_B])
    fake = FakeComfyUIClient()

    first = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_FRIDAY_IN_WINDOW,
        environ=_comfy_env(base),
        discovery_provider=discovery,
        draft_provider=drafts,
        comfyui_client=fake,
        canon_path=canon,
    )
    assert first.status == STATUS_TRIGGERED
    before = _pending_files(base)

    second = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_FRIDAY_IN_WINDOW,
        environ=_comfy_env(base),
        discovery_provider=_StubDiscoveryProvider(content=_topics_json(2)),
        draft_provider=_StubDraftProvider(
            contents_by_call=[GOOD_MARKDOWN_A, GOOD_MARKDOWN_B]
        ),
        comfyui_client=FakeComfyUIClient(),
        canon_path=canon,
    )
    assert second.status == STATUS_NOOP_IDEMPOTENT
    assert _pending_files(base) == before


def test_failed_batch_may_retry(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    _enable_trigger()
    key = build_gap_trigger_idempotency_key(TZ, "2026-W30")
    store = get_gap_trigger_batch_store()
    store.force_set(
        {
            "idempotency_key": key,
            "status": STATUS_FAILED,
            "operator_timezone": TZ,
            "iso_week": "2026-W30",
            "empty_days": ["2026-07-22"],
            "result_summary": None,
            "error_code": "discovery_failed",
            "created_at_utc": "2026-07-17T20:00:00Z",
            "updated_at_utc": "2026-07-17T20:01:00Z",
        }
    )
    result = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_FRIDAY_IN_WINDOW,
        environ=_comfy_env(base),
        discovery_provider=_StubDiscoveryProvider(content=_topics_json(1)),
        draft_provider=_StubDraftProvider(contents_by_call=[GOOD_MARKDOWN_A]),
        comfyui_client=FakeComfyUIClient(),
        canon_path=canon,
    )
    assert result.status == STATUS_TRIGGERED
    row, _ = store.get(key)
    assert row is not None
    assert row["status"] == STATUS_COMPLETED


def test_stale_in_progress_reclaimable(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    _enable_trigger()
    key = build_gap_trigger_idempotency_key(TZ, "2026-W30")
    store = get_gap_trigger_batch_store()
    stale_updated = (
        datetime(2026, 7, 17, 20, 0, 0, tzinfo=timezone.utc)
        - STALE_IN_PROGRESS_TTL
        - timedelta(minutes=1)
    ).strftime("%Y-%m-%dT%H:%M:%SZ")
    store.force_set(
        {
            "idempotency_key": key,
            "status": STATUS_IN_PROGRESS,
            "operator_timezone": TZ,
            "iso_week": "2026-W30",
            "empty_days": ["2026-07-22"],
            "result_summary": None,
            "error_code": None,
            "created_at_utc": stale_updated,
            "updated_at_utc": stale_updated,
        }
    )
    result = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_FRIDAY_IN_WINDOW,
        environ=_comfy_env(base),
        discovery_provider=_StubDiscoveryProvider(content=_topics_json(1)),
        draft_provider=_StubDraftProvider(contents_by_call=[GOOD_MARKDOWN_A]),
        comfyui_client=FakeComfyUIClient(),
        canon_path=canon,
    )
    assert result.status == STATUS_TRIGGERED


def test_dry_run_no_writes_no_claim(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    _enable_trigger()
    before = _pending_files(base)
    result = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_FRIDAY_IN_WINDOW,
        dry_run=True,
        environ=_comfy_env(base),
    )
    assert result.status == STATUS_WOULD_TRIGGER
    assert result.dry_run is True
    assert result.target_week == "2026-W30"
    assert result.idempotency_key == build_gap_trigger_idempotency_key(TZ, "2026-W30")
    assert _pending_files(base) == before
    row, _ = get_gap_trigger_batch_store().get(result.idempotency_key or "")
    assert row is None


def test_force_window_bypasses_window_not_enablement(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    save_gap_operator_settings(VALID_SETTINGS)  # disabled
    result = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_THURSDAY,
        force_window=True,
        environ=_comfy_env(base),
    )
    assert result.status == STATUS_NOOP_DISABLED

    _enable_trigger()
    result2 = run_flow_b_gap_trigger(
        base,
        now_utc=NOW_THURSDAY,
        force_window=True,
        dry_run=True,
        environ=_comfy_env(base),
    )
    assert result2.status == STATUS_WOULD_TRIGGER
    assert result2.force_window is True


def test_http_auth_required(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(_editorial_base(tmp_path))))
    assert client.post(TRIGGER_PATH, json={}).status_code == 401


def test_http_disabled_noop_and_openapi(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    save_gap_operator_settings(VALID_SETTINGS)
    app = create_app(make_settings(base))
    paths = {route.path for route in app.routes}
    assert TRIGGER_PATH in paths
    client = TestClient(app)
    response = client.post(
        TRIGGER_PATH,
        headers=auth_header(),
        json={"now_utc": NOW_FRIDAY_IN_WINDOW},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == STATUS_NOOP_DISABLED
    _assert_no_secrets(body)
    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert TRIGGER_PATH in openapi.json()["paths"]


def test_http_triggered_with_mocks(tmp_path: Path, monkeypatch: Any) -> None:
    base = _editorial_base(tmp_path)
    canon = _write_canon(tmp_path)
    _enable_trigger()
    discovery = _StubDiscoveryProvider(content=_topics_json(2))
    drafts = _StubDraftProvider(contents_by_call=[GOOD_MARKDOWN_A, GOOD_MARKDOWN_B])
    fake = FakeComfyUIClient()
    comfy_env = _comfy_env(base)

    def _fake_run(base_path: Path, **kwargs: Any):
        kwargs["discovery_provider"] = discovery
        kwargs["draft_provider"] = drafts
        kwargs["comfyui_client"] = fake
        kwargs["canon_path"] = canon
        kwargs["environ"] = comfy_env
        return run_flow_b_gap_trigger(base_path, **kwargs)

    monkeypatch.setattr(
        "silverman_blog_linkedin.main.run_flow_b_gap_trigger",
        _fake_run,
    )
    client = TestClient(create_app(make_settings(base)))
    response = client.post(
        TRIGGER_PATH,
        headers=auth_header(),
        json={"now_utc": NOW_FRIDAY_IN_WINDOW},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == STATUS_TRIGGERED, body
    assert len(body["drafts"]) <= 2
    _assert_no_secrets(body)


def test_trigger_module_does_not_call_publish_or_promote() -> None:
    import silverman_blog_linkedin.flow_b_calendar_gap_trigger as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "publish_blog_post" not in source
    assert "schedule_linkedin_distribution" not in source
    assert "publish_linkedin" not in source
    assert "promote_pending_approval_draft" not in source
    assert "approve_pending_approval_draft" not in source
    assert "complete_flow_a_ready_path" not in source


def test_n8n_export_http_only_inactive() -> None:
    assert N8N_EXPORT.is_file()
    payload = json.loads(N8N_EXPORT.read_text(encoding="utf-8"))
    assert payload.get("active") is False
    node_types = {node.get("type") for node in payload.get("nodes", [])}
    assert "n8n-nodes-base.httpRequest" in node_types
    assert "n8n-nodes-base.scheduleTrigger" in node_types
    assert "n8n-nodes-base.executeCommand" not in node_types
    assert "n8n-nodes-base.executeCommand" not in json.dumps(payload).lower()
    http_nodes = [
        n for n in payload["nodes"] if n.get("type") == "n8n-nodes-base.httpRequest"
    ]
    assert http_nodes
    url = http_nodes[0]["parameters"].get("url", "")
    assert "/flow-b/gap-trigger" in url
