"""US-040K: max-2 publications per operator-local day density enforcement."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from silverman_blog_linkedin.campaign_lifecycle import (
    read_campaign_metadata,
)
from silverman_blog_linkedin.editorial_calendar_schedule_update import (
    CALENDAR_SCHEDULE_DUPLICATE_SLOT,
    CALENDAR_SCHEDULE_LOCAL_DAY_DENSITY,
    update_editorial_calendar_item_schedule,
)
from silverman_blog_linkedin.local_day_density import (
    ENV_OPERATOR_TIMEZONE,
    LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY,
    OPERATOR_TIMEZONE_INVALID,
    OPERATOR_TIMEZONE_REQUIRED,
    evaluate_local_day_density,
)
from silverman_blog_linkedin.linkedin_publication_flow import (
    PUBLISH_STATE_CANCELLED,
    PUBLISH_STATE_FAILED,
    PUBLISH_STATE_PENDING,
    PUBLISH_STATE_QUEUED,
    cancel_linkedin_publication,
)
from silverman_blog_linkedin.linkedin_supervision_flow import (
    defer_linkedin_variant,
    reopen_linkedin_variant,
)
from tests.conftest import create_full_layout, write_and_seed_calendar
from tests.test_editorial_calendar_flow_a_execute import (
    _base_calendar,
    _flow_a_item,
)
from tests.test_linkedin_publication import (
    CANONICAL_CAMPAIGN_ID,
    TARGET_VARIANT,
    _distribution_scheduled_campaign,
    _setup_metadata_campaigns,
    _update_variant,
)

TZ = "America/Chicago"
NOW = datetime(2026, 7, 10, 12, 0, 0, tzinfo=timezone.utc)
# Local day 2026-08-15 in America/Chicago (CDT = UTC-5):
# 05:00Z → 00:00 local; 10:00Z → 05:00 local; 16:00Z → 11:00 local
DAY_A_T1 = "2026-08-15T10:00:00Z"
DAY_A_T2 = "2026-08-15T16:00:00Z"
DAY_A_T3 = "2026-08-15T20:00:00Z"
DAY_B_EMPTY = "2026-08-20T15:00:00Z"
# Near local midnight Chicago: 04:30Z on 16th is still 2026-08-15 23:30 CDT
NEAR_MIDNIGHT_STILL_15 = "2026-08-16T04:30:00Z"
# 05:30Z on 16th is 2026-08-16 00:30 CDT
AFTER_MIDNIGHT_16 = "2026-08-16T05:30:00Z"

OTHER_CAMPAIGN_A = "flow-a-2026-08-15-density-a"
OTHER_CAMPAIGN_B = "flow-a-2026-08-15-density-b"
OTHER_CAMPAIGN_C = "flow-a-2026-08-15-density-c"


@pytest.fixture
def density_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    _setup_metadata_campaigns(base)
    (base / "linkedin-posts").mkdir(parents=True, exist_ok=True)
    _distribution_scheduled_campaign(base)
    return base


def _write_campaign(base: Path, campaign_id: str, variants: list[dict]) -> None:
    path = base / "metadata" / "campaigns" / f"{campaign_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "campaign_id": campaign_id,
        "flow": "flow_a",
        "state": "distribution_scheduled",
        "variants": variants,
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _li_variant(
    variant_id: str,
    *,
    scheduled_at_utc: str,
    publish_state: str = PUBLISH_STATE_PENDING,
) -> dict:
    return {
        "variant": variant_id,
        "audience": variant_id,
        "publish_state": publish_state,
        "scheduled_at_utc": scheduled_at_utc,
        "derivative_content_sha256": "abc",
        "artifact_relative_path": f"linkedin-posts/generated/{variant_id}.md",
    }


def _seed_two_occupants_day_a(base: Path) -> None:
    """Two density members on local day 2026-08-15 (Chicago) from other campaigns."""
    _write_campaign(
        base,
        OTHER_CAMPAIGN_A,
        [_li_variant("exec", scheduled_at_utc=DAY_A_T1)],
    )
    _write_campaign(
        base,
        OTHER_CAMPAIGN_B,
        [_li_variant("peer", scheduled_at_utc=DAY_A_T2)],
    )


def test_defer_refuses_third_density_member(density_base: Path):
    _seed_two_occupants_day_a(density_base)
    before = json.dumps(
        read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID), sort_keys=True
    )

    result = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_A_T3,
        dry_run=False,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY in result.errors
    assert json.dumps(
        read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID), sort_keys=True
    ) == before


def test_defer_dry_run_density_no_mutation(density_base: Path):
    _seed_two_occupants_day_a(density_base)
    before = json.dumps(
        read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID), sort_keys=True
    )

    result = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_A_T3,
        dry_run=True,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY in result.errors
    assert result.metadata_written is False
    assert json.dumps(
        read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID), sort_keys=True
    ) == before


def test_defer_self_move_same_local_day_allowed(density_base: Path):
    """Day has TARGET + one other; self-move same day → others=1 → allowed."""
    _write_campaign(
        density_base,
        OTHER_CAMPAIGN_A,
        [_li_variant("exec", scheduled_at_utc=DAY_A_T1)],
    )
    _update_variant(density_base, variant=TARGET_VARIANT, scheduled_at_utc=DAY_A_T2)

    result = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_A_T3,
        dry_run=False,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "completed"
    assert result.scheduled_at_utc == DAY_A_T3
    entry = next(
        v
        for v in read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID)["variants"]
        if v["variant"] == TARGET_VARIANT
    )
    assert entry["scheduled_at_utc"] == DAY_A_T3


def test_cancelled_excluded_from_density(density_base: Path):
    _write_campaign(
        density_base,
        OTHER_CAMPAIGN_A,
        [
            _li_variant(
                "cancelled-a",
                scheduled_at_utc=DAY_A_T1,
                publish_state=PUBLISH_STATE_CANCELLED,
            ),
            _li_variant(
                "cancelled-b",
                scheduled_at_utc=DAY_A_T2,
                publish_state=PUBLISH_STATE_CANCELLED,
            ),
        ],
    )

    result = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_A_T3,
        dry_run=False,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "completed"
    assert LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY not in (result.errors or [])


def test_published_counts_toward_density(density_base: Path):
    _write_campaign(
        density_base,
        OTHER_CAMPAIGN_A,
        [
            _li_variant(
                "pub-a",
                scheduled_at_utc=DAY_A_T1,
                publish_state="published",
            ),
            _li_variant(
                "pub-b",
                scheduled_at_utc=DAY_A_T2,
                publish_state="published",
            ),
        ],
    )
    before = json.dumps(
        read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID), sort_keys=True
    )

    result = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_A_T3,
        dry_run=True,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY in result.errors
    assert json.dumps(
        read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID), sort_keys=True
    ) == before


def test_failed_excluded_from_density(density_base: Path):
    _write_campaign(
        density_base,
        OTHER_CAMPAIGN_A,
        [
            _li_variant(
                "fail-a",
                scheduled_at_utc=DAY_A_T1,
                publish_state=PUBLISH_STATE_FAILED,
            ),
            _li_variant(
                "fail-b",
                scheduled_at_utc=DAY_A_T2,
                publish_state=PUBLISH_STATE_FAILED,
            ),
        ],
    )

    result = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_A_T3,
        dry_run=False,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "completed"


def test_missing_timezone_fails_closed(density_base: Path):
    before = json.dumps(
        read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID), sort_keys=True
    )

    result = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_B_EMPTY,
        dry_run=False,
        operator_timezone=None,
        now=NOW,
        environ={},  # no SILVERMAN_OPERATOR_TIMEZONE
    )

    assert result.status == "failed"
    assert OPERATOR_TIMEZONE_REQUIRED in result.errors
    assert json.dumps(
        read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID), sort_keys=True
    ) == before


def test_invalid_timezone_fails_closed(density_base: Path):
    result = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_B_EMPTY,
        dry_run=True,
        operator_timezone="Not/A_Real_Zone",
        now=NOW,
        environ={},
    )

    assert result.status == "failed"
    assert OPERATOR_TIMEZONE_INVALID in result.errors


def test_density_does_not_call_linkedin(density_base: Path):
    _seed_two_occupants_day_a(density_base)

    with patch("httpx.Client") as httpx_client:
        result = defer_linkedin_variant(
            density_base,
            campaign_id=CANONICAL_CAMPAIGN_ID,
            variant=TARGET_VARIANT,
            new_scheduled_at_utc=DAY_A_T3,
            dry_run=False,
            operator_timezone=TZ,
            now=NOW,
            environ={},
        )

    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY in result.errors
    httpx_client.assert_not_called()


def test_reopen_refuses_full_local_day(density_base: Path):
    _seed_two_occupants_day_a(density_base)
    cancel_linkedin_publication(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        reason="operator_choice",
    )
    before = json.dumps(
        read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID), sort_keys=True
    )

    result = reopen_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_A_T3,
        dry_run=False,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY in result.errors
    entry = next(
        v
        for v in read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID)["variants"]
        if v["variant"] == TARGET_VARIANT
    )
    assert entry["publish_state"] == PUBLISH_STATE_CANCELLED
    assert json.dumps(
        read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID), sort_keys=True
    ) == before


def test_reopen_succeeds_onto_under_capacity_day(density_base: Path):
    cancel_linkedin_publication(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        dry_run=False,
        reason="operator_choice",
    )

    result = reopen_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_B_EMPTY,
        dry_run=False,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "completed"
    assert result.publish_state == PUBLISH_STATE_PENDING
    entry = next(
        v
        for v in read_campaign_metadata(density_base, CANONICAL_CAMPAIGN_ID)["variants"]
        if v["variant"] == TARGET_VARIANT
    )
    assert entry["publish_state"] == PUBLISH_STATE_PENDING
    assert entry["scheduled_at_utc"] == DAY_B_EMPTY


def test_local_midnight_boundary_chicago(density_base: Path):
    """Item at 04:30Z Aug 16 counts as local Aug 15 Chicago; 05:30Z is Aug 16."""
    _write_campaign(
        density_base,
        OTHER_CAMPAIGN_A,
        [_li_variant("edge", scheduled_at_utc=NEAR_MIDNIGHT_STILL_15)],
    )
    _write_campaign(
        density_base,
        OTHER_CAMPAIGN_B,
        [_li_variant("day", scheduled_at_utc=DAY_A_T1)],
    )

    # Third onto Aug 15 local → refuse
    refused = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_A_T2,
        dry_run=True,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )
    assert refused.status == "failed"
    assert LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY in refused.errors

    # Onto Aug 16 local (after midnight) → only 0 others on that day → ok
    allowed = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=AFTER_MIDNIGHT_16,
        dry_run=False,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )
    assert allowed.status == "completed"


def test_blog_schedule_refuses_day_with_two_linkedin(density_base: Path):
    _seed_two_occupants_day_a(density_base)
    item_id = "blog-density-1"
    write_and_seed_calendar(
        density_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    item_id=item_id,
                    status="scheduled",
                    due_at_utc=DAY_B_EMPTY,
                ),
            ]
        ),
    )

    from silverman_blog_linkedin.editorial_calendar_plan import load_calendar

    before_cal, _ = load_calendar(density_base)
    before = json.dumps(before_cal, sort_keys=True)

    result = update_editorial_calendar_item_schedule(
        density_base,
        item_id=item_id,
        new_due_at_utc=DAY_A_T3,
        dry_run=False,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "failed"
    assert CALENDAR_SCHEDULE_LOCAL_DAY_DENSITY in result.errors
    after_cal, _ = load_calendar(density_base)
    assert json.dumps(after_cal, sort_keys=True) == before


def test_blog_interim_one_per_utc_day_still_additive(density_base: Path):
    """Two blog items same UTC day still fail interim duplicate-slot (additive to K)."""
    item_a = "blog-a"
    item_b = "blog-b"
    write_and_seed_calendar(
        density_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    item_id=item_a,
                    status="scheduled",
                    due_at_utc="2026-08-15T10:00:00Z",
                ),
                _flow_a_item(
                    item_id=item_b,
                    status="scheduled",
                    due_at_utc=DAY_B_EMPTY,
                ),
            ]
        ),
    )

    result = update_editorial_calendar_item_schedule(
        density_base,
        item_id=item_b,
        new_due_at_utc="2026-08-15T18:00:00Z",
        dry_run=True,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "failed"
    assert CALENDAR_SCHEDULE_DUPLICATE_SLOT in result.errors
    # Interim fires before density; density code must not be the only refusal.
    assert CALENDAR_SCHEDULE_LOCAL_DAY_DENSITY not in result.errors


def test_grandfather_reduce_from_overfull_day(density_base: Path):
    """Moving one of three off an over-full day onto empty day succeeds."""
    _write_campaign(
        density_base,
        OTHER_CAMPAIGN_A,
        [_li_variant("a", scheduled_at_utc=DAY_A_T1)],
    )
    _write_campaign(
        density_base,
        OTHER_CAMPAIGN_B,
        [_li_variant("b", scheduled_at_utc=DAY_A_T2)],
    )
    _update_variant(density_base, variant=TARGET_VARIANT, scheduled_at_utc=DAY_A_T3)

    result = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_B_EMPTY,
        dry_run=False,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "completed"
    assert result.scheduled_at_utc == DAY_B_EMPTY


def test_evaluate_env_fallback_timezone(density_base: Path):
    density = evaluate_local_day_density(
        density_base,
        target_utc=datetime(2026, 8, 20, 15, 0, 0, tzinfo=timezone.utc),
        operator_timezone=None,
        environ={ENV_OPERATOR_TIMEZONE: TZ},
    )
    assert density.ok is True
    assert density.resolved_timezone == TZ


def test_queued_counts_toward_density(density_base: Path):
    _write_campaign(
        density_base,
        OTHER_CAMPAIGN_A,
        [
            _li_variant(
                "q1",
                scheduled_at_utc=DAY_A_T1,
                publish_state=PUBLISH_STATE_QUEUED,
            ),
            _li_variant(
                "q2",
                scheduled_at_utc=DAY_A_T2,
                publish_state=PUBLISH_STATE_QUEUED,
            ),
        ],
    )

    result = defer_linkedin_variant(
        density_base,
        campaign_id=CANONICAL_CAMPAIGN_ID,
        variant=TARGET_VARIANT,
        new_scheduled_at_utc=DAY_A_T3,
        dry_run=True,
        operator_timezone=TZ,
        now=NOW,
        environ={},
    )

    assert result.status == "failed"
    assert LINKEDIN_SUPERVISION_LOCAL_DAY_DENSITY in result.errors
