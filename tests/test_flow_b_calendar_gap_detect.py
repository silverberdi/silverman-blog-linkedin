"""US-077: Flow B next-week LinkedIn calendar gap detect (detect-only)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from silverman_blog_linkedin.flow_b_calendar_gap_detect import (
    detect_next_week_calendar_gaps,
    next_operator_local_week,
)
from silverman_blog_linkedin.flow_b_gap_operator_settings import (
    save_gap_operator_settings,
)
from silverman_blog_linkedin.local_day_density import ENV_OPERATOR_TIMEZONE
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, make_settings

GAPS_PATH = "/flow-b/calendar-gaps"
CAMPAIGN_ID = "flow-a-2026-07-19-gap-detect"

# Friday afternoon America/Chicago → next week is Mon 2026-07-20 … Sun 2026-07-26.
# Lead from Fri 2026-07-17 to Mon 2026-07-20 is 3 days; with min_lead_days=5,
# Mon–Tue are filtered; Wed–Sun (lead 5–9) remain actionable when empty.
NOW_FRIDAY = "2026-07-17T20:00:00Z"  # 15:00 America/Chicago
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


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    for relative in (
        "metadata/campaigns",
        "editorial-calendar",
        "blog-posts/ready",
        "blog-posts/pending-approval",
        "linkedin-posts/generated",
    ):
        (base / relative).mkdir(parents=True, exist_ok=True)
    return base


def _variant(
    variant_id: str,
    *,
    publish_state: str = "pending",
    scheduled_at_utc: str,
) -> dict:
    return {
        "variant": variant_id,
        "audience": "senior practitioners",
        "publish_state": publish_state,
        "scheduled_at_utc": scheduled_at_utc,
    }


def _write_campaign(
    base: Path,
    *,
    variants: list[dict],
    campaign_id: str = CAMPAIGN_ID,
) -> Path:
    payload = {
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
    return _write_json(base / "metadata/campaigns" / f"{campaign_id}.json", payload)


def _snapshot_tree(base: Path) -> dict[str, tuple[bytes, int]]:
    return {
        str(path.relative_to(base)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in sorted(base.rglob("*"))
        if path.is_file()
    }


def _assert_no_secrets(body: dict) -> None:
    blob = str(body).lower()
    for needle in (
        "password",
        "api_key",
        "apikey",
        "oauth",
        "token",
        "postgresql://",
        "secret",
    ):
        assert needle not in blob


def test_next_operator_local_week_is_ahead_full_week() -> None:
    now = datetime(2026, 7, 17, 20, 0, 0, tzinfo=timezone.utc)
    monday, sunday, iso = next_operator_local_week(now, ZoneInfo(TZ))
    assert monday.isoformat() == "2026-07-20"
    assert sunday.isoformat() == "2026-07-26"
    assert iso == "2026-W30"


def test_empty_next_week_yields_gaps_subject_to_lead(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    result = detect_next_week_calendar_gaps(
        base,
        now_utc=NOW_FRIDAY,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    assert result.status == "gaps_found"
    assert result.read_only is True
    assert result.settings_source == "defaults"
    assert result.min_lead_days == 5
    assert result.gap_posts_threshold == 0
    assert result.gap_trigger_enabled is False
    assert result.operator_timezone == TZ
    assert result.target_week is not None
    assert result.target_week["iso_week"] == "2026-W30"
    # Lead Fri→Mon=3, Tue=4 filtered; Wed–Sun actionable (5–9).
    days = [g.local_date for g in result.gaps]
    assert days == [
        "2026-07-22",
        "2026-07-23",
        "2026-07-24",
        "2026-07-25",
        "2026-07-26",
    ]
    assert "2026-07-20" not in days
    assert "2026-07-21" not in days


def test_day_with_one_pending_is_not_a_gap(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    # Wednesday 2026-07-22 14:00 UTC ≈ 09:00 Chicago — still that local day.
    _write_campaign(
        base,
        variants=[
            _variant(
                "engineering-leadership",
                publish_state="pending",
                scheduled_at_utc="2026-07-22T14:00:00Z",
            )
        ],
    )
    result = detect_next_week_calendar_gaps(
        base,
        now_utc=NOW_FRIDAY,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    days = {g.local_date for g in result.gaps}
    assert "2026-07-22" not in days
    assert result.status == "gaps_found"
    # Not treated as density-capacity gap merely because count is 1 under max-2.


def test_min_lead_days_filters_near_empty_days(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    save_gap_operator_settings({**VALID_SETTINGS, "min_lead_days": 8})
    result = detect_next_week_calendar_gaps(
        base,
        now_utc=NOW_FRIDAY,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    # Lead Fri→Sun 2026-07-26 = 9; Sat=8; Fri=7 filtered. With 8: Sat+Sun only.
    days = [g.local_date for g in result.gaps]
    assert days == ["2026-07-25", "2026-07-26"]
    assert result.min_lead_days == 8
    assert result.settings_source == "database"


def test_defaults_when_settings_row_missing(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    result = detect_next_week_calendar_gaps(
        base,
        now_utc=NOW_FRIDAY,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    assert result.settings_source == "defaults"
    assert result.min_lead_days == 5
    assert result.gap_posts_threshold == 0


def test_db_min_lead_days_honored(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    save_gap_operator_settings({**VALID_SETTINGS, "min_lead_days": 7})
    result = detect_next_week_calendar_gaps(
        base,
        now_utc=NOW_FRIDAY,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    assert result.settings_source == "database"
    assert result.min_lead_days == 7
    # Lead Fri→Thu=6 filtered; Fri–Sun lead 7–9 actionable.
    days = [g.local_date for g in result.gaps]
    assert days == [
        "2026-07-24",
        "2026-07-25",
        "2026-07-26",
    ]


def test_detect_allowed_when_gap_trigger_disabled(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    save_gap_operator_settings({**VALID_SETTINGS, "gap_trigger_enabled": False})
    before = _snapshot_tree(base)
    result = detect_next_week_calendar_gaps(
        base,
        now_utc=NOW_FRIDAY,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    assert result.gap_trigger_enabled is False
    assert result.status in {"gaps_found", "no_gap"}
    assert result.read_only is True
    assert _snapshot_tree(base) == before
    assert not any(
        (base / "blog-posts/pending-approval").glob("*")
    )
    assert list((base / "blog-posts/ready").iterdir()) == []


def test_no_gap_when_every_day_has_coverage(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    # Lower lead so all seven days are actionable; fill each with one pending.
    save_gap_operator_settings({**VALID_SETTINGS, "min_lead_days": 0})
    variants = []
    for offset, name in enumerate(
        ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    ):
        day = 20 + offset
        variants.append(
            _variant(
                f"v-{name}",
                publish_state="pending",
                scheduled_at_utc=f"2026-07-{day:02d}T15:00:00Z",
            )
        )
    _write_campaign(base, variants=variants)
    result = detect_next_week_calendar_gaps(
        base,
        now_utc=NOW_FRIDAY,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    assert result.status == "no_gap"
    assert result.gaps == []


def test_ready_folder_alone_does_not_clear_gaps(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    (base / "blog-posts/ready" / "some-post.md").write_text("# Ready\n", encoding="utf-8")
    result = detect_next_week_calendar_gaps(
        base,
        now_utc=NOW_FRIDAY,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    assert result.status == "gaps_found"
    assert len(result.gaps) >= 1


def test_detect_does_not_mutate_campaigns(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    path = _write_campaign(
        base,
        variants=[
            _variant(
                "engineering-leadership",
                publish_state="pending",
                scheduled_at_utc="2026-07-22T14:00:00Z",
            )
        ],
    )
    before = path.read_bytes()
    tree_before = _snapshot_tree(base)
    detect_next_week_calendar_gaps(
        base,
        now_utc=NOW_FRIDAY,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    detect_next_week_calendar_gaps(
        base,
        now_utc=NOW_FRIDAY,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    assert path.read_bytes() == before
    assert _snapshot_tree(base) == tree_before


def test_http_requires_auth(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(_editorial_base(tmp_path))))
    assert client.get(GAPS_PATH).status_code == 401


def test_http_authenticated_returns_structured_result(tmp_path: Path) -> None:
    base = _editorial_base(tmp_path)
    client = TestClient(create_app(make_settings(base)))
    response = client.get(
        GAPS_PATH,
        headers=auth_header(),
        params={"now_utc": NOW_FRIDAY},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "gaps_found"
    assert body["read_only"] is True
    assert body["operator_timezone"] == TZ
    assert body["settings_source"] == "defaults"
    assert body["target_week"]["iso_week"] == "2026-W30"
    assert isinstance(body["gaps"], list)
    assert body["min_lead_days"] == 5
    assert body["gap_posts_threshold"] == 0
    assert body["gap_trigger_enabled"] is False
    assert "observed_at_utc" in body
    _assert_no_secrets(body)


def test_http_invalid_now_utc_422(tmp_path: Path) -> None:
    client = TestClient(create_app(make_settings(_editorial_base(tmp_path))))
    response = client.get(
        GAPS_PATH,
        headers=auth_header(),
        params={"now_utc": "not-a-timestamp"},
    )
    assert response.status_code == 422


def test_no_out_of_scope_flow_b_routes(tmp_path: Path) -> None:
    """US-077 detect must not add draft/approve/promote placeholder routes.

    Discovery (``/flow-b/discover-topics``) and gap-trigger (``/flow-b/gap-trigger``)
    are owned by later stories and MAY exist.
    """
    app = create_app(make_settings(_editorial_base(tmp_path)))
    paths = {getattr(route, "path", None) for route in app.routes}
    assert "/flow-b/calendar-gaps" in paths
    forbidden = {
        "/flow-b/draft",
        "/flow-b/approve",
        "/flow-b/promote",
    }
    assert not (paths & forbidden)
