"""Tests for Flow A physical source lifecycle completion."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

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
    compute_source_content_sha256,
    find_campaign_by_source_path,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.blog_publish_flow import publish_blog_post
from silverman_blog_linkedin.flow_a_source_lifecycle import (
    FLOW_A_SOURCE_LIFECYCLE_PREMATURE,
    FLOW_A_SOURCE_MOVE_COLLISION_EXHAUSTED,
    FLOW_A_SOURCE_MOVE_FAILED,
    complete_flow_a_source_lifecycle,
)
from tests.conftest import create_full_layout

SOURCE_SLUG = "02-example-post"
PUBLIC_SLUG = "example-post"
PUBLICATION_DATE = "2026-07-06"
SOURCE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.md"
IMAGE_RELATIVE = f"blog-posts/ready/{SOURCE_SLUG}.png"
PROCESSED_RELATIVE = f"blog-posts/processed/{SOURCE_SLUG}.md"
PROCESSED_IMAGE_RELATIVE = f"blog-posts/processed/{SOURCE_SLUG}.png"
CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
SOURCE_MARKDOWN = "# Example\n\nBody.\n"


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
    campaign["source_public_url"] = "https://silverman.pro/2026/07/06/example-post/"
    write_campaign_metadata(base, CAMPAIGN_ID, campaign)
    return campaign


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    create_full_layout(base)
    return base


def test_successful_lifecycle_moves_markdown_to_processed(editorial_base: Path):
    _write_ready_source(editorial_base, with_image=False)
    _distribution_scheduled_campaign(editorial_base)

    result = complete_flow_a_source_lifecycle(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        source_relative_path=SOURCE_RELATIVE,
    )

    assert result.status == "completed"
    assert not (editorial_base / SOURCE_RELATIVE).exists()
    assert (editorial_base / PROCESSED_RELATIVE).is_file()
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_FLOW_A_COMPLETE
    assert campaign["source_file_status"]["location"] == SOURCE_LOCATION_PROCESSED


def test_successful_lifecycle_moves_companion_image(editorial_base: Path):
    _write_ready_source(editorial_base, with_image=True)
    _distribution_scheduled_campaign(editorial_base)

    result = complete_flow_a_source_lifecycle(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
    )

    assert result.status == "completed"
    assert not (editorial_base / IMAGE_RELATIVE).exists()
    assert (editorial_base / PROCESSED_IMAGE_RELATIVE).is_file()
    assert result.processed_image_relative_path == PROCESSED_IMAGE_RELATIVE


def test_metadata_records_original_and_processed_paths(editorial_base: Path):
    _write_ready_source(editorial_base, with_image=True)
    _distribution_scheduled_campaign(editorial_base)

    complete_flow_a_source_lifecycle(editorial_base, campaign_id=CAMPAIGN_ID)

    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["original_source_relative_path"] == SOURCE_RELATIVE
    assert campaign["processed_source_relative_path"] == PROCESSED_RELATIVE
    assert campaign["original_image_relative_path"] == IMAGE_RELATIVE
    assert campaign["processed_image_relative_path"] == PROCESSED_IMAGE_RELATIVE
    assert campaign["source_relative_path"] == PROCESSED_RELATIVE
    assert campaign["source_content_sha256"] == compute_source_content_sha256(
        SOURCE_MARKDOWN
    )


def test_idempotent_skip_without_ready_copy(editorial_base: Path):
    _write_ready_source(editorial_base, with_image=True)
    _distribution_scheduled_campaign(editorial_base)
    first = complete_flow_a_source_lifecycle(editorial_base, campaign_id=CAMPAIGN_ID)
    assert first.status == "completed"

    second = complete_flow_a_source_lifecycle(
        editorial_base,
        campaign_id=CAMPAIGN_ID,
        source_relative_path=SOURCE_RELATIVE,
    )

    assert second.status == "skipped"
    assert second.already_processed is True
    assert not (editorial_base / SOURCE_RELATIVE).exists()


def test_premature_lifecycle_does_not_move_files(editorial_base: Path):
    _write_ready_source(editorial_base, with_image=False)
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
        reason="validated",
        actor=ACTOR_WORKER,
    )
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)

    result = complete_flow_a_source_lifecycle(editorial_base, campaign_id=CAMPAIGN_ID)

    assert result.status == "failed"
    assert FLOW_A_SOURCE_LIFECYCLE_PREMATURE in result.errors
    assert (editorial_base / SOURCE_RELATIVE).is_file()
    assert not (editorial_base / PROCESSED_RELATIVE).exists()


def test_collision_uses_deterministic_suffix(editorial_base: Path):
    _write_ready_source(editorial_base, with_image=False)
    processed = editorial_base / "blog-posts" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    (processed / f"{SOURCE_SLUG}.md").write_text("other content", encoding="utf-8")
    _distribution_scheduled_campaign(editorial_base)

    result = complete_flow_a_source_lifecycle(editorial_base, campaign_id=CAMPAIGN_ID)

    assert result.status == "completed"
    expected = f"blog-posts/processed/{SOURCE_SLUG}-processed-1.md"
    assert (editorial_base / expected).is_file()
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["processed_source_relative_path"] == expected


def test_find_campaign_by_original_or_processed_path(editorial_base: Path):
    _write_ready_source(editorial_base, with_image=False)
    _distribution_scheduled_campaign(editorial_base)
    complete_flow_a_source_lifecycle(editorial_base, campaign_id=CAMPAIGN_ID)

    by_ready = find_campaign_by_source_path(editorial_base, SOURCE_RELATIVE)
    by_processed = find_campaign_by_source_path(editorial_base, PROCESSED_RELATIVE)
    assert by_ready is not None
    assert by_processed is not None
    assert by_ready["campaign_id"] == CAMPAIGN_ID


def test_move_failure_after_schedule_preserves_distribution_state(editorial_base: Path):
    _write_ready_source(editorial_base, with_image=False)
    _distribution_scheduled_campaign(editorial_base)

    with patch(
        "silverman_blog_linkedin.flow_a_source_lifecycle._move_source_file",
        side_effect=OSError("disk full"),
    ):
        result = complete_flow_a_source_lifecycle(editorial_base, campaign_id=CAMPAIGN_ID)

    assert result.status == "failed"
    assert FLOW_A_SOURCE_MOVE_FAILED in result.errors
    campaign = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert campaign is not None
    assert campaign["state"] == STATE_DISTRIBUTION_SCHEDULED
    assert (editorial_base / SOURCE_RELATIVE).is_file()


def test_collision_exhausted_returns_stable_error(editorial_base: Path):
    _write_ready_source(editorial_base, with_image=False)
    processed = editorial_base / "blog-posts" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    for index in range(100):
        suffix = "" if index == 0 else f"-processed-{index}"
        (processed / f"{SOURCE_SLUG}{suffix}.md").write_text(
            f"blocker {index}", encoding="utf-8"
        )
    _distribution_scheduled_campaign(editorial_base)

    result = complete_flow_a_source_lifecycle(editorial_base, campaign_id=CAMPAIGN_ID)

    assert result.status == "failed"
    assert FLOW_A_SOURCE_MOVE_COLLISION_EXHAUSTED in result.errors


def test_publish_idempotent_rerun_with_processed_source_only(
    editorial_base: Path, tmp_path: Path
):
    public_repo = tmp_path / "public-blog"
    public_repo.mkdir()
    (public_repo / "_posts").mkdir()
    (public_repo / "assets" / "images").mkdir(parents=True)

    _write_ready_source(editorial_base, with_image=False)
    _distribution_scheduled_campaign(editorial_base)
    complete_flow_a_source_lifecycle(editorial_base, campaign_id=CAMPAIGN_ID)

    result = publish_blog_post(
        editorial_base,
        SOURCE_RELATIVE,
        github_pages_repo_path=str(public_repo),
    )

    assert result.status == "completed"
    assert result.blog_publish["status"] == "already_published"
    assert "blog_publish_source_not_ready" not in result.errors
