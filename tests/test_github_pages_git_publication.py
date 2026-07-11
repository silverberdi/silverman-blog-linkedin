"""Tests for guarded Git publication of blog artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from silverman_blog_linkedin.campaign_lifecycle import (
    ACTOR_WORKER,
    FLOW_A,
    FLOW_B,
    STATE_BLOG_PUBLISH_PENDING,
    STATE_BLOG_PUBLISHED,
    STATE_VALIDATED,
    build_blog_publish_idempotency_key,
    build_initial_campaign_metadata,
    compute_source_content_sha256,
    read_campaign_metadata,
    transition_state,
    write_campaign_metadata,
)
from silverman_blog_linkedin.github_pages_git_publication import (
    BLOG_GIT_PUBLICATION_ARTIFACTS_MISSING,
    BLOG_GIT_PUBLICATION_DISABLED,
    BLOG_GIT_PUBLICATION_FLOW_B_NOT_ALLOWED,
    BLOG_GIT_PUBLICATION_PUSH_FAILED,
    GIT_RECOVERY_MESSAGE,
    FakeGitRunner,
    GitCommandResult,
    publish_blog_git_publication,
)
from silverman_blog_linkedin.github_pages_git_config import GitPublicationSettings

SOURCE_SLUG = "01-why-i-did-not-start-with-the-database"
PUBLIC_SLUG = "why-i-did-not-start-with-the-database"
PUBLICATION_DATE = "2026-07-06"
CAMPAIGN_ID = f"flow-a-{PUBLICATION_DATE}-{PUBLIC_SLUG}"
POST_RELATIVE = f"_posts/{PUBLICATION_DATE}-{PUBLIC_SLUG}.md"
IMAGE_RELATIVE = f"assets/images/{PUBLIC_SLUG}.png"


def _git_enabled_settings() -> GitPublicationSettings:
    return GitPublicationSettings(
        publication_enabled=True,
        branch="main",
        remote="origin",
        commit_message_template="Add blog post: {public_slug} ({campaign_id})",
        timeout_seconds=120,
        fetch_timeout_seconds=30,
    )


def _blog_publish_record(content_hash: str) -> dict:
    return {
        "idempotency_key": build_blog_publish_idempotency_key(
            source_slug=SOURCE_SLUG,
            public_slug=PUBLIC_SLUG,
            publication_date=PUBLICATION_DATE,
            source_content_sha256=content_hash,
        ),
        "status": "published",
        "public_repo_path": POST_RELATIVE,
        "public_repo_image_path": IMAGE_RELATIVE,
    }


def _campaign(
    editorial_base: Path,
    *,
    flow: str = FLOW_A,
    blog_git_publication: dict | None = None,
) -> dict:
    content = "hash-source"
    content_hash = compute_source_content_sha256(content)
    if flow == FLOW_B:
        campaign = build_initial_campaign_metadata(
            flow=FLOW_B,
            source_slug=SOURCE_SLUG,
            public_slug=PUBLIC_SLUG,
            source_relative_path=f"blog-posts/ready/{SOURCE_SLUG}.md",
            image_relative_path=f"blog-posts/ready/{SOURCE_SLUG}.png",
            source_content=content,
            publication_date=PUBLICATION_DATE,
        )
        campaign["blog_publish"] = _blog_publish_record(content_hash)
        if blog_git_publication is not None:
            campaign["blog_git_publication"] = blog_git_publication
        write_campaign_metadata(editorial_base, campaign["campaign_id"], campaign)
        return campaign

    campaign = build_initial_campaign_metadata(
        flow=FLOW_A,
        source_slug=SOURCE_SLUG,
        public_slug=PUBLIC_SLUG,
        source_relative_path=f"blog-posts/ready/{SOURCE_SLUG}.md",
        image_relative_path=f"blog-posts/ready/{SOURCE_SLUG}.png",
        source_content=content,
        publication_date=PUBLICATION_DATE,
    )
    transition_state(
        campaign,
        STATE_VALIDATED,
        reason="validated",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_BLOG_PUBLISH_PENDING,
        reason="publish pending",
        actor=ACTOR_WORKER,
    )
    transition_state(
        campaign,
        STATE_BLOG_PUBLISHED,
        reason="published",
        actor=ACTOR_WORKER,
    )
    campaign["blog_publish"] = _blog_publish_record(content_hash)
    if blog_git_publication is not None:
        campaign["blog_git_publication"] = blog_git_publication
    write_campaign_metadata(editorial_base, CAMPAIGN_ID, campaign)
    return campaign


def _write_artifacts(repo_path: Path) -> None:
    (repo_path / "_posts").mkdir(parents=True, exist_ok=True)
    (repo_path / "assets/images").mkdir(parents=True, exist_ok=True)
    (repo_path / POST_RELATIVE).write_text("post\n", encoding="utf-8")
    (repo_path / IMAGE_RELATIVE).write_bytes(b"\x89PNG\r\n\x1a\n")


def _success_runner() -> FakeGitRunner:
    runner = FakeGitRunner()
    runner.results[("diff", "--quiet", "--", POST_RELATIVE)] = GitCommandResult(
        returncode=1, stdout="", stderr=""
    )
    runner.results[("diff", "--quiet", "--", IMAGE_RELATIVE)] = GitCommandResult(
        returncode=1, stdout="", stderr=""
    )
    runner.results[("diff", "--cached", "--quiet", "--", POST_RELATIVE)] = GitCommandResult(
        returncode=1, stdout="", stderr=""
    )
    runner.results[("diff", "--cached", "--quiet", "--", IMAGE_RELATIVE)] = GitCommandResult(
        returncode=1, stdout="", stderr=""
    )
    return runner


@pytest.fixture
def editorial_base(tmp_path: Path) -> Path:
    base = tmp_path / "editorial"
    (base / "metadata/campaigns").mkdir(parents=True)
    return base


@pytest.fixture
def public_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "public-blog"
    _write_artifacts(repo)
    return repo


def test_disabled_guard_returns_error_without_git_calls(
    editorial_base: Path, public_repo: Path
) -> None:
    campaign = _campaign(editorial_base)
    runner = FakeGitRunner()
    result = publish_blog_git_publication(
        editorial_base,
        public_repo,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        blog_publish=campaign["blog_publish"],
        settings=GitPublicationSettings(
            publication_enabled=False,
            branch="main",
            remote="origin",
            commit_message_template="Add blog post: {public_slug} ({campaign_id})",
            timeout_seconds=120,
            fetch_timeout_seconds=30,
        ),
        runner=runner,
    )
    assert result.status == "failed"
    assert BLOG_GIT_PUBLICATION_DISABLED in result.errors
    assert runner.calls == []


def test_flow_b_blocked(editorial_base: Path, public_repo: Path) -> None:
    campaign = _campaign(editorial_base, flow=FLOW_B)
    runner = FakeGitRunner()
    result = publish_blog_git_publication(
        editorial_base,
        public_repo,
        campaign_id=campaign["campaign_id"],
        campaign=campaign,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        blog_publish=campaign["blog_publish"],
        settings=_git_enabled_settings(),
        runner=runner,
    )
    assert result.status == "failed"
    assert BLOG_GIT_PUBLICATION_FLOW_B_NOT_ALLOWED in result.errors
    assert runner.calls == []


def test_missing_artifacts_blocks_commit(editorial_base: Path, tmp_path: Path) -> None:
    repo = tmp_path / "empty-repo"
    (repo / "_posts").mkdir(parents=True)
    (repo / "assets/images").mkdir(parents=True)
    campaign = _campaign(editorial_base)
    runner = FakeGitRunner()
    result = publish_blog_git_publication(
        editorial_base,
        repo,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        blog_publish=campaign["blog_publish"],
        settings=_git_enabled_settings(),
        runner=runner,
    )
    assert result.status == "failed"
    assert BLOG_GIT_PUBLICATION_ARTIFACTS_MISSING in result.errors
    assert not any(call[1][0] == "commit" for call in runner.calls)


def test_scoped_staging_and_successful_push(
    editorial_base: Path, public_repo: Path
) -> None:
    campaign = _campaign(editorial_base)
    runner = _success_runner()
    result = publish_blog_git_publication(
        editorial_base,
        public_repo,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        blog_publish=campaign["blog_publish"],
        settings=_git_enabled_settings(),
        runner=runner,
    )
    assert result.status == "completed"
    assert result.blog_git_publication["status"] == "pushed"
    assert result.blog_git_publication["commit_sha"] == "abc123def456"
    add_calls = [call for call in runner.calls if call[1][:2] == ["add", "--"]]
    assert len(add_calls) == 1
    assert add_calls[0][1][2:] == [POST_RELATIVE, IMAGE_RELATIVE]
    call_args = [tuple(call[1]) for call in runner.calls]
    fetch_index = next(i for i, args in enumerate(call_args) if args[0] == "fetch")
    push_index = next(i for i, args in enumerate(call_args) if args[0] == "push")
    assert fetch_index < push_index
    assert ("push", "origin", "main") in call_args

    stored = read_campaign_metadata(editorial_base, CAMPAIGN_ID)
    assert stored is not None
    assert stored["blog_git_publication"]["status"] == "pushed"


def test_unrelated_dirty_files_not_staged(editorial_base: Path, public_repo: Path) -> None:
    (public_repo / "README.md").write_text("dirty\n", encoding="utf-8")
    campaign = _campaign(editorial_base)
    runner = _success_runner()
    publish_blog_git_publication(
        editorial_base,
        public_repo,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        blog_publish=campaign["blog_publish"],
        settings=_git_enabled_settings(),
        runner=runner,
    )
    add_calls = [call for call in runner.calls if call[1][:2] == ["add", "--"]]
    staged = add_calls[0][1][2:]
    assert staged == [POST_RELATIVE, IMAGE_RELATIVE]
    assert "README.md" not in staged


def test_push_failure_returns_failed_with_recovery(
    editorial_base: Path, public_repo: Path
) -> None:
    campaign = _campaign(editorial_base)
    runner = _success_runner()
    runner.results[("push", "origin", "main")] = GitCommandResult(
        returncode=1,
        stdout="",
        stderr="rejected",
    )
    result = publish_blog_git_publication(
        editorial_base,
        public_repo,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        blog_publish=campaign["blog_publish"],
        settings=_git_enabled_settings(),
        runner=runner,
    )
    assert result.status == "failed"
    assert BLOG_GIT_PUBLICATION_PUSH_FAILED in result.errors
    assert GIT_RECOVERY_MESSAGE in result.errors
    assert "rejected" not in " ".join(result.errors)


def test_idempotent_already_published_without_new_commit(
    editorial_base: Path, public_repo: Path
) -> None:
    prior_git = {
        "status": "pushed",
        "commit_sha": "deadbeef",
        "remote": "origin",
        "branch": "main",
        "staged_paths": [POST_RELATIVE, IMAGE_RELATIVE],
    }
    campaign = _campaign(editorial_base, blog_git_publication=prior_git)
    runner = FakeGitRunner()
    result = publish_blog_git_publication(
        editorial_base,
        public_repo,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        blog_publish=campaign["blog_publish"],
        settings=_git_enabled_settings(),
        runner=runner,
    )
    assert result.status == "completed"
    assert result.blog_git_publication["status"] == "already_published"
    assert result.blog_git_publication["commit_sha"] == "deadbeef"
    assert not any(call[1][0] == "commit" for call in runner.calls)
    assert not any(call[1][0] == "push" for call in runner.calls)


def test_fetch_and_ff_only_pull_when_behind_remote(
    editorial_base: Path, public_repo: Path
) -> None:
    campaign = _campaign(editorial_base)
    runner = _success_runner()
    runner.results[("rev-parse", "origin/main")] = GitCommandResult(
        returncode=0, stdout="remote999\n", stderr=""
    )
    runner.results[("merge-base", "--is-ancestor", "abc123def456", "remote999")] = (
        GitCommandResult(returncode=0, stdout="", stderr="")
    )
    result = publish_blog_git_publication(
        editorial_base,
        public_repo,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        blog_publish=campaign["blog_publish"],
        settings=_git_enabled_settings(),
        runner=runner,
    )
    assert result.status == "completed"
    pull_calls = [call for call in runner.calls if call[1][:3] == ["pull", "--ff-only", "origin"]]
    assert len(pull_calls) == 1


def test_remote_divergence_returns_partial_error(
    editorial_base: Path, public_repo: Path
) -> None:
    from silverman_blog_linkedin.github_pages_git_publication import (
        BLOG_GIT_PUBLICATION_REMOTE_DIVERGED,
    )

    campaign = _campaign(editorial_base)
    runner = _success_runner()
    runner.results[("rev-parse", "origin/main")] = GitCommandResult(
        returncode=0, stdout="remote999\n", stderr=""
    )
    runner.results[("merge-base", "--is-ancestor", "abc123def456", "remote999")] = (
        GitCommandResult(returncode=1, stdout="", stderr="")
    )
    runner.results[("merge-base", "--is-ancestor", "remote999", "abc123def456")] = (
        GitCommandResult(returncode=1, stdout="", stderr="")
    )
    result = publish_blog_git_publication(
        editorial_base,
        public_repo,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        blog_publish=campaign["blog_publish"],
        settings=_git_enabled_settings(),
        runner=runner,
    )
    assert result.status == "failed"
    assert BLOG_GIT_PUBLICATION_REMOTE_DIVERGED in result.errors
    assert not any(call[1][0] == "push" for call in runner.calls)


def test_duplicate_artifacts_blocked(editorial_base: Path, public_repo: Path) -> None:
    from silverman_blog_linkedin.github_pages_git_publication import (
        BLOG_GIT_PUBLICATION_DUPLICATE_ARTIFACTS,
    )

    campaign = _campaign(editorial_base)
    runner = _success_runner()
    runner.results[("cat-file", "-e", f"origin/main:{POST_RELATIVE}")] = GitCommandResult(
        returncode=0, stdout="", stderr=""
    )
    runner.results[("log", "-1", "--format=%B", "origin/main", "--", POST_RELATIVE)] = (
        GitCommandResult(
            returncode=0,
            stdout="Add blog post: other (flow-a-2026-01-01-other-post)\n",
            stderr="",
        )
    )
    result = publish_blog_git_publication(
        editorial_base,
        public_repo,
        campaign_id=CAMPAIGN_ID,
        campaign=campaign,
        public_slug=PUBLIC_SLUG,
        publication_date=PUBLICATION_DATE,
        blog_publish=campaign["blog_publish"],
        settings=_git_enabled_settings(),
        runner=runner,
    )
    assert result.status == "failed"
    assert BLOG_GIT_PUBLICATION_DUPLICATE_ARTIFACTS in result.errors
    assert not any(call[1][0] == "commit" for call in runner.calls)
