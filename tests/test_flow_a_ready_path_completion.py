"""Tests for ready-path Flow A completion HTTP (lifecycle + calendar)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    FLOW_A,
    SOURCE_LOCATION_PROCESSED,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_BLOG_PUBLISHED,
    STATE_DERIVATIVES_GENERATED,
    STATE_DERIVATIVES_PENDING,
    STATE_DISTRIBUTION_SCHEDULED,
    STATE_FLOW_A_COMPLETE,
    STATE_READY,
    STATE_VALIDATED,
    build_initial_campaign_metadata,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.editorial_calendar_plan import load_calendar
from silverman_blog_linkedin.flow_a_ready_path_completion import (
    CALENDAR_UPDATE_COMPLETED,
    CALENDAR_UPDATE_FAILED,
    CALENDAR_UPDATE_SKIPPED_ABSENT,
    CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED,
    complete_flow_a_ready_path,
)
from silverman_blog_linkedin.flow_a_source_lifecycle import (
    FLOW_A_SOURCE_LIFECYCLE_PREMATURE,
)
from silverman_blog_linkedin.main import create_app
from tests.conftest import auth_header, create_full_layout, make_settings
from tests.test_editorial_calendar_flow_a_execute import (
    _base_calendar,
    _flow_a_item,
    _write_calendar,
)

SOURCE_SLUG = "05-keep-contracts-boring"
PUBLIC_SLUG = "keep-contracts-boring"
PUBLICATION_DATE = "2026-07-15"
SOURCE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
IMAGE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.png"
PROCESSED_RELATIVE = f"blog-posts/processed/{SOURCE_SLUG}.md"
CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
SOURCE_MARKDOWN = "# Keep contracts boring\n\nBody.\n"


def _write_ready_source(base: Path, *, with_image: bool = True) -> None:
    ready = base / "blog-posts" / "ready"
    ready.mkdir(parents=True, exist_ok=True)
    (ready / f"{SOURCE_SLUG}.md").write_text(SOURCE_MARKDOWN, encoding="utf-8")
    if with_image:
        (ready / f"{SOURCE_SLUG}.png").write_bytes(b"png-bytes")


def _distribution_scheduled_campaign(base: Path) -> dict:
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=SOURCE_RELATIVE,
        image_relative_path=IMAGE_RELATIVE,
        source_content=SOURCE_MARKDOWN,
        publication_date=PUBLICATION_DATE,
    )
    for to_state, reason in (
        (STATE_VALIDATED, "validated"),
        (STATE_BLOG_PUBLISH_PENDING, "publish pending"),
        (STATE_BLOG_PUBLISHED, "published"),
        (STATE_DERIVATIVES_PENDING, "derivatives pending"),
        (STATE_DERIVATIVES_GENERATED, "derivatives generated"),
        (STATE_DISTRIBUTION_SCHEDULED, "distribution scheduled"),
    ):
        transition_state(
            campaign,
            to_state,
            reason=reason,
            actor=ACTOR_WORKER,
        )
    campaign["campaign_id"] = CAMPAIGN_ID
    campaign["source_public_url"] = (
        f"https://silverman.pro/2026/07/15/{PUBLIC_SLUG}/"
    )
    campaign["blog_publish"] = {"status": "published"}
    campaign["linkedin_package"] = {
        "package_id": "pkg-1",
        "package_status": "generated",
    }
    campaign["linkedin_distribution"] = {
        "distribution_id": "dist-1",
        "strategy": "flow_a_staggered",
    }
    campaign["variants"] = [
        {
            "variant": "executive",
            "publish_state": "pending",
            "scheduled_at_utc": "2026-07-16T14:00:00Z",
        }
    ]
    write_campaign_metadata(base, CAMPAIGN_ID, campaign)
    return campaign


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    return base


def test_complete_ready_path_moves_source_and_inserts_calendar(editorial_base: Path):
    _write_ready_source(editorial_base)
    _distribution_scheduled_campaign(editorial_base)
    _write_calendar(editorial_base, _base_calendar(items=[]))

    result = complete_flow_a_ready_path(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        source_relative_path=SOURCE_RELATIVE,
    )

    assert result.status == "completed"
    assert result.source_lifecycle_status == "completed"
    assert result.calendar_update_status == CALENDAR_UPDATE_COMPLETED
    assert not (editorial_base / SOURCE_RELATIVE).exists()
    assert (editorial_base / PROCESSED_RELATIVE).is_file()
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_FLOW_A_COMPLETE
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_PROCESSED

    calendar, _ = load_calendar(editorial_base)
    assert calendar is not None
    assert len(calendar["items"]) == 1
    item = calendar["items"][0]
    assert item["campaign_id"] == CAMPAIGN_ID
    assert item["status"] == "completed"
    assert item["flow_a_completion"]["campaign_state"] == STATE_FLOW_A_COMPLETE


def test_complete_ready_path_matches_existing_calendar_item(editorial_base: Path):
    _write_ready_source(editorial_base)
    _distribution_scheduled_campaign(editorial_base)
    _write_calendar(
        editorial_base,
        _base_calendar(
            items=[
                _flow_a_item(
                    item_id="scheduled-keep-contracts",
                    campaign_id=CAMPAIGN_ID,
                    source_relative_path=SOURCE_RELATIVE,
                    public_slug=PUBLIC_SLUG,
                )
            ]
        ),
    )

    result = complete_flow_a_ready_path(editorial_base, campaign_id=CAMPAIGN_ID)

    assert result.status == "completed"
    assert result.calendar_update_status == CALENDAR_UPDATE_COMPLETED
    calendar, _ = load_calendar(editorial_base)
    assert calendar is not None
    assert len(calendar["items"]) == 1
    assert calendar["items"][0]["item_id"] == "scheduled-keep-contracts"
    assert calendar["items"][0]["status"] == "completed"


def test_complete_ready_path_empty_calendar_still_inserts(editorial_base: Path):
    _write_ready_source(editorial_base)
    _distribution_scheduled_campaign(editorial_base)
    # Empty memory calendar store is valid SoT — completion inserts an item.

    result = complete_flow_a_ready_path(editorial_base, campaign_id=CAMPAIGN_ID)

    assert result.status == "completed"
    assert result.calendar_update_status == CALENDAR_UPDATE_COMPLETED
    assert (editorial_base / PROCESSED_RELATIVE).is_file()
    calendar, _ = load_calendar(editorial_base)
    assert calendar is not None
    assert len(calendar["items"]) == 1


def test_complete_ready_path_idempotent_skip(editorial_base: Path):
    _write_ready_source(editorial_base)
    _distribution_scheduled_campaign(editorial_base)
    _write_calendar(editorial_base, _base_calendar(items=[]))

    first = complete_flow_a_ready_path(editorial_base, campaign_id=CAMPAIGN_ID)
    second = complete_flow_a_ready_path(editorial_base, campaign_id=CAMPAIGN_ID)

    assert first.status == "completed"
    assert second.status == "skipped"
    assert second.calendar_update_status == CALENDAR_UPDATE_SKIPPED_ALREADY_COMPLETED


def test_complete_ready_path_premature_fails(editorial_base: Path):
    _write_ready_source(editorial_base)
    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=SOURCE_RELATIVE,
        image_relative_path=IMAGE_RELATIVE,
        source_content=SOURCE_MARKDOWN,
        publication_date=PUBLICATION_DATE,
    )
    transition_state(
        campaign,
        STATE_VALIDATED,
        reason="validated only",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)

    result = complete_flow_a_ready_path(editorial_base, campaign_id=CAMPAIGN_ID)

    assert result.status == "failed"
    assert FLOW_A_SOURCE_LIFECYCLE_PREMATURE in result.errors
    assert (editorial_base / SOURCE_RELATIVE).is_file()


def test_complete_ready_path_calendar_failure_is_partial(editorial_base: Path):
    _write_ready_source(editorial_base)
    _distribution_scheduled_campaign(editorial_base)
    _write_calendar(editorial_base, _base_calendar(items=[]))

    with patch(
        "silverman_blog_linkedin.flow_a_ready_path_completion.save_calendar_atomic",
        return_value=["calendar_completion_write_failed"],
    ):
        result = complete_flow_a_ready_path(editorial_base, campaign_id=CAMPAIGN_ID)

    assert result.status == "partial"
    assert result.calendar_update_status == CALENDAR_UPDATE_FAILED
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_FLOW_A_COMPLETE


def test_http_complete_flow_a_ready_path_requires_auth(editorial_base: Path):
    client = TestClient(create_app(make_settings(editorial_base)))
    response = client.post(
        "/complete-flow-a-ready-path",
        json={"campaign_id": CAMPAIGN_ID},
    )
    assert response.status_code == 401


def test_http_complete_flow_a_ready_path_success(editorial_base: Path):
    _write_ready_source(editorial_base)
    _distribution_scheduled_campaign(editorial_base)
    _write_calendar(editorial_base, _base_calendar(items=[]))
    client = TestClient(create_app(make_settings(editorial_base)))

    response = client.post(
        "/complete-flow-a-ready-path",
        headers=auth_header(),
        json={"campaign_id": CAMPAIGN_ID, "update_calendar": True},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["campaign_id"] == CAMPAIGN_ID
    assert body["source_lifecycle_status"] == "completed"
    assert body["calendar_update_status"] == CALENDAR_UPDATE_COMPLETED
