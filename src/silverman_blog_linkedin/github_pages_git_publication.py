"""Guarded Git commit and push for blog publication artifacts."""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from silverman_blog_linkedin.campaign_lifecycle import FLOW_B, write_campaign_metadata
from silverman_blog_linkedin.github_pages_git_config import (
    GitPublicationSettings,
    load_git_publication_settings,
)
from silverman_blog_linkedin.run_metadata import utc_now_iso

logger = logging.getLogger(__name__)

BLOG_GIT_PUBLICATION_DISABLED = "blog_git_publication_disabled"
BLOG_GIT_PUBLICATION_ARTIFACTS_MISSING = "blog_git_publication_artifacts_missing"
BLOG_GIT_PUBLICATION_COMMIT_FAILED = "blog_git_publication_commit_failed"
BLOG_GIT_PUBLICATION_PUSH_FAILED = "blog_git_publication_push_failed"
BLOG_GIT_PUBLICATION_REMOTE_DIVERGED = "blog_git_publication_remote_diverged"
BLOG_GIT_PUBLICATION_DUPLICATE_ARTIFACTS = "blog_git_publication_duplicate_artifacts"
BLOG_GIT_PUBLICATION_FLOW_B_NOT_ALLOWED = "blog_git_publication_flow_b_not_allowed"
BLOG_GIT_PUBLICATION_GIT_UNAVAILABLE = "blog_git_publication_git_unavailable"
BLOG_GIT_PUBLICATION_TIMEOUT = "blog_git_publication_timeout"

GIT_RECOVERY_MESSAGE = (
    "Blog files were written to the public checkout but remote Git publication "
    "did not complete. Commit and push manually or retry with git_publication."
)

_SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{20,}"),
    re.compile(r"gho_[a-zA-Z0-9]{20,}"),
)


@dataclass(frozen=True)
class GitCommandResult:
    returncode: int
    stdout: str
    stderr: str


class GitRunner(Protocol):
    def run(
        self,
        repo_path: Path,
        args: list[str],
        *,
        timeout: float | None = None,
    ) -> GitCommandResult: ...


@dataclass
class FakeGitRunner:
    """Injectable Git runner for tests."""

    results: dict[tuple[str, ...], GitCommandResult] = field(default_factory=dict)
    default_result: GitCommandResult = field(
        default_factory=lambda: GitCommandResult(returncode=0, stdout="", stderr="")
    )
    calls: list[tuple[Path, list[str]]] = field(default_factory=list)
    available: bool = True

    def run(
        self,
        repo_path: Path,
        args: list[str],
        *,
        timeout: float | None = None,
    ) -> GitCommandResult:
        self.calls.append((repo_path, list(args)))
        key = tuple(args)
        if key in self.results:
            return self.results[key]
        if args and args[0] == "rev-parse" and "HEAD" in args:
            return GitCommandResult(returncode=0, stdout="abc123def456\n", stderr="")
        if args and args[0] == "rev-parse" and args[-1].endswith("/main"):
            return GitCommandResult(returncode=0, stdout="abc123def456\n", stderr="")
        if args and args[0] == "fetch":
            return self.default_result
        if args and args[0] == "pull" and "--ff-only" in args:
            return self.default_result
        if args and args[0] == "merge-base" and "--is-ancestor" in args:
            return self.default_result
        if args and args[0] == "status" and "--porcelain" in args:
            return GitCommandResult(returncode=0, stdout="", stderr="")
        if args and args[0] == "cat-file" and "-e" in args:
            return GitCommandResult(returncode=1, stdout="", stderr="")
        if args and args[0] == "diff" and "--quiet" in args:
            return GitCommandResult(returncode=0, stdout="", stderr="")
        return self.default_result


class SubprocessGitRunner:
    """Production Git runner using subprocess."""

    def run(
        self,
        repo_path: Path,
        args: list[str],
        *,
        timeout: float | None = None,
    ) -> GitCommandResult:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return GitCommandResult(
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
        )


@dataclass
class GitPublicationResult:
    status: str
    blog_git_publication: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata_written: bool = False
    metadata_error_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "blog_git_publication": self.blog_git_publication,
            "errors": self.errors,
            "metadata_written": self.metadata_written,
            "metadata_error_code": self.metadata_error_code,
        }


def _sanitize_git_message(message: str) -> str:
    sanitized = message.strip()
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("[redacted]", sanitized)
    if len(sanitized) > 500:
        sanitized = sanitized[:500] + "..."
    return sanitized or "git command failed"


def _git_available() -> bool:
    return shutil.which("git") is not None


def _resolve_artifact_paths(
    *,
    public_slug: str,
    publication_date: str,
    blog_publish: dict[str, Any],
) -> tuple[str, str]:
    post_relative = blog_publish.get("public_repo_path")
    image_relative = blog_publish.get("public_repo_image_path")
    if not post_relative or not image_relative:
        post_relative = f"_posts/{publication_date}-{public_slug}.md"
        image_relative = f"assets/images/{public_slug}.png"
    return str(post_relative), str(image_relative)


def _paths_confined_to_repo(repo_path: Path, *relative_paths: str) -> bool:
    resolved_repo = repo_path.resolve()
    for relative in relative_paths:
        candidate = (resolved_repo / relative).resolve()
        try:
            candidate.relative_to(resolved_repo)
        except ValueError:
            return False
        if not candidate.is_file():
            return False
    return True


def _format_commit_message(
    template: str,
    *,
    public_slug: str,
    campaign_id: str,
    publication_date: str,
) -> str:
    return template.format(
        public_slug=public_slug,
        campaign_id=campaign_id,
        publication_date=publication_date,
    )


_CAMPAIGN_ID_IN_COMMIT = re.compile(r"\((flow-[ab]-[^)]+)\)")


def _git_rev_parse(
    runner: GitRunner,
    repo_path: Path,
    ref: str,
    *,
    timeout: float,
) -> str | None:
    result = runner.run(repo_path, ["rev-parse", ref], timeout=timeout)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _is_git_ancestor(
    runner: GitRunner,
    repo_path: Path,
    ancestor: str,
    descendant: str,
    *,
    timeout: float,
) -> bool:
    result = runner.run(
        repo_path,
        ["merge-base", "--is-ancestor", ancestor, descendant],
        timeout=timeout,
    )
    return result.returncode == 0


def _has_unrelated_dirty_files(
    runner: GitRunner,
    repo_path: Path,
    staged_paths: list[str],
    *,
    timeout: float,
) -> bool:
    result = runner.run(repo_path, ["status", "--porcelain"], timeout=timeout)
    if result.returncode != 0:
        return True
    staged_set = set(staged_paths)
    for line in result.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1].strip()
        if path not in staged_set:
            return True
    return False


def _fetch_and_reconcile_remote(
    runner: GitRunner,
    repo_path: Path,
    config: GitPublicationSettings,
    staged_paths: list[str],
    *,
    timeout: float,
    fetch_timeout: float,
) -> GitPublicationResult | None:
    """Fetch and fast-forward reconcile when behind remote. Returns failure or None."""
    remote = config.remote
    branch = config.branch
    tracking_ref = f"{remote}/{branch}"

    fetch_result = runner.run(
        repo_path,
        ["fetch", remote],
        timeout=fetch_timeout,
    )
    if fetch_result.returncode != 0:
        logger.warning(
            "git fetch failed: %s",
            _sanitize_git_message(fetch_result.stderr),
        )
        return _failed_git_result(
            error_code=BLOG_GIT_PUBLICATION_PUSH_FAILED,
            staged_paths=staged_paths,
            remote=remote,
            branch=branch,
            include_recovery=True,
        )

    local_sha = _git_rev_parse(runner, repo_path, "HEAD", timeout=timeout)
    remote_sha = _git_rev_parse(runner, repo_path, tracking_ref, timeout=timeout)
    if not local_sha:
        return _failed_git_result(
            error_code=BLOG_GIT_PUBLICATION_COMMIT_FAILED,
            staged_paths=staged_paths,
            remote=remote,
            branch=branch,
            include_recovery=True,
        )
    if not remote_sha:
        return None

    if local_sha == remote_sha:
        return None

    if _is_git_ancestor(runner, repo_path, local_sha, remote_sha, timeout=timeout):
        if _has_unrelated_dirty_files(
            runner, repo_path, staged_paths, timeout=timeout
        ):
            return _failed_git_result(
                error_code=BLOG_GIT_PUBLICATION_REMOTE_DIVERGED,
                staged_paths=staged_paths,
                remote=remote,
                branch=branch,
                include_recovery=True,
            )
        pull_result = runner.run(
            repo_path,
            ["pull", "--ff-only", remote, branch],
            timeout=timeout,
        )
        if pull_result.returncode != 0:
            logger.warning(
                "git pull --ff-only failed: %s",
                _sanitize_git_message(pull_result.stderr),
            )
            return _failed_git_result(
                error_code=BLOG_GIT_PUBLICATION_REMOTE_DIVERGED,
                staged_paths=staged_paths,
                remote=remote,
                branch=branch,
                include_recovery=True,
            )
        return None

    if _is_git_ancestor(runner, repo_path, remote_sha, local_sha, timeout=timeout):
        return None

    return _failed_git_result(
        error_code=BLOG_GIT_PUBLICATION_REMOTE_DIVERGED,
        staged_paths=staged_paths,
        remote=remote,
        branch=branch,
        include_recovery=True,
    )


def _extract_campaign_id_from_commit_message(message: str) -> str | None:
    match = _CAMPAIGN_ID_IN_COMMIT.search(message)
    if match:
        return match.group(1)
    return None


def _path_exists_on_remote(
    runner: GitRunner,
    repo_path: Path,
    tracking_ref: str,
    relative_path: str,
    *,
    timeout: float,
) -> bool:
    result = runner.run(
        repo_path,
        ["cat-file", "-e", f"{tracking_ref}:{relative_path}"],
        timeout=timeout,
    )
    return result.returncode == 0


def _check_duplicate_artifacts(
    runner: GitRunner,
    repo_path: Path,
    config: GitPublicationSettings,
    staged_paths: list[str],
    *,
    campaign_id: str,
    timeout: float,
) -> str | None:
    """Return error code when cross-campaign collision detected."""
    tracking_ref = f"{config.remote}/{config.branch}"
    for relative_path in staged_paths:
        if not _path_exists_on_remote(
            runner, repo_path, tracking_ref, relative_path, timeout=timeout
        ):
            continue
        log_result = runner.run(
            repo_path,
            ["log", "-1", "--format=%B", tracking_ref, "--", relative_path],
            timeout=timeout,
        )
        if log_result.returncode != 0:
            continue
        owner_campaign = _extract_campaign_id_from_commit_message(log_result.stdout)
        if owner_campaign and owner_campaign != campaign_id:
            return BLOG_GIT_PUBLICATION_DUPLICATE_ARTIFACTS
    return None


def _paths_have_changes(
    runner: GitRunner,
    repo_path: Path,
    staged_paths: list[str],
    *,
    timeout: float,
) -> bool:
    for relative in staged_paths:
        result = runner.run(
            repo_path,
            ["diff", "--quiet", "--", relative],
            timeout=timeout,
        )
        if result.returncode == 1:
            return True
        staged_result = runner.run(
            repo_path,
            ["diff", "--cached", "--quiet", "--", relative],
            timeout=timeout,
        )
        if staged_result.returncode == 1:
            return True
    return False


def _matching_prior_git_evidence(
    campaign: dict[str, Any],
    *,
    idempotency_key: str,
    staged_paths: list[str],
) -> dict[str, Any] | None:
    prior = campaign.get("blog_git_publication") or {}
    if prior.get("status") != "pushed":
        return None
    blog_publish = campaign.get("blog_publish") or {}
    if blog_publish.get("idempotency_key") != idempotency_key:
        return None
    prior_paths = prior.get("staged_paths") or []
    if list(prior_paths) != list(staged_paths):
        return None
    if not prior.get("commit_sha"):
        return None
    return prior


def _already_published_result(
    prior: dict[str, Any],
    *,
    staged_paths: list[str],
) -> GitPublicationResult:
    blog_git_publication = dict(prior)
    blog_git_publication["status"] = "already_published"
    blog_git_publication["staged_paths"] = list(staged_paths)
    return GitPublicationResult(
        status="completed",
        blog_git_publication=blog_git_publication,
        errors=[],
    )


def _failed_git_result(
    *,
    error_code: str,
    staged_paths: list[str] | None = None,
    remote: str | None = None,
    branch: str | None = None,
    commit_sha: str | None = None,
    include_recovery: bool = False,
) -> GitPublicationResult:
    blog_git_publication: dict[str, Any] = {
        "status": "failed",
        "error_code": error_code,
    }
    if staged_paths is not None:
        blog_git_publication["staged_paths"] = list(staged_paths)
    if remote is not None:
        blog_git_publication["remote"] = remote
    if branch is not None:
        blog_git_publication["branch"] = branch
    if commit_sha is not None:
        blog_git_publication["commit_sha"] = commit_sha
    errors = [error_code]
    if include_recovery:
        errors.append(GIT_RECOVERY_MESSAGE)
    return GitPublicationResult(
        status="failed",
        blog_git_publication=blog_git_publication,
        errors=errors,
    )


def _ensure_safe_git_repository(
    runner: GitRunner,
    repo_path: Path,
    *,
    timeout: float,
) -> None:
    """Trust mounted public checkout ownership when worker user differs from host."""
    runner.run(
        repo_path,
        ["config", "--global", "--add", "safe.directory", str(repo_path)],
        timeout=timeout,
    )


def publish_blog_git_publication(
    base_path: Path,
    repo_path: Path,
    *,
    campaign_id: str,
    campaign: dict[str, Any],
    public_slug: str,
    publication_date: str,
    blog_publish: dict[str, Any],
    settings: GitPublicationSettings | None = None,
    runner: GitRunner | None = None,
    environ: dict[str, str] | None = None,
) -> GitPublicationResult:
    """Commit and push scoped blog publication artifacts for one campaign."""
    config = settings or load_git_publication_settings(environ)
    git_runner = runner or SubprocessGitRunner()

    if campaign.get("flow") == FLOW_B:
        return _failed_git_result(error_code=BLOG_GIT_PUBLICATION_FLOW_B_NOT_ALLOWED)

    if not config.publication_enabled:
        return _failed_git_result(error_code=BLOG_GIT_PUBLICATION_DISABLED)

    if isinstance(git_runner, FakeGitRunner):
        if not git_runner.available:
            return _failed_git_result(error_code=BLOG_GIT_PUBLICATION_GIT_UNAVAILABLE)
    elif not _git_available():
        return _failed_git_result(error_code=BLOG_GIT_PUBLICATION_GIT_UNAVAILABLE)

    handoff_status = blog_publish.get("status")
    if handoff_status not in {"published", "already_published", "reconciled"}:
        return _failed_git_result(error_code=BLOG_GIT_PUBLICATION_ARTIFACTS_MISSING)

    post_relative, image_relative = _resolve_artifact_paths(
        public_slug=public_slug,
        publication_date=publication_date,
        blog_publish=blog_publish,
    )
    staged_paths = [post_relative, image_relative]

    if not _paths_confined_to_repo(repo_path, post_relative, image_relative):
        return _failed_git_result(
            error_code=BLOG_GIT_PUBLICATION_ARTIFACTS_MISSING,
            staged_paths=staged_paths,
        )

    idempotency_key = blog_publish.get("idempotency_key") or ""
    prior = _matching_prior_git_evidence(
        campaign,
        idempotency_key=idempotency_key,
        staged_paths=staged_paths,
    )
    if prior is not None and not _paths_have_changes(
        git_runner,
        repo_path,
        staged_paths,
        timeout=float(config.timeout_seconds),
    ):
        return _already_published_result(prior, staged_paths=staged_paths)

    timeout = float(config.timeout_seconds)
    fetch_timeout = float(config.fetch_timeout_seconds)

    if not isinstance(git_runner, FakeGitRunner):
        _ensure_safe_git_repository(git_runner, repo_path, timeout=timeout)

    add_result = git_runner.run(
        repo_path,
        ["add", "--", post_relative, image_relative],
        timeout=timeout,
    )
    if add_result.returncode != 0:
        logger.warning(
            "git add failed for campaign %s: %s",
            campaign_id,
            _sanitize_git_message(add_result.stderr),
        )
        return _failed_git_result(
            error_code=BLOG_GIT_PUBLICATION_COMMIT_FAILED,
            staged_paths=staged_paths,
            remote=config.remote,
            branch=config.branch,
            include_recovery=True,
        )

    if prior is not None and not _paths_have_changes(
        git_runner,
        repo_path,
        staged_paths,
        timeout=timeout,
    ):
        return _already_published_result(prior, staged_paths=staged_paths)

    if not _paths_have_changes(git_runner, repo_path, staged_paths, timeout=timeout):
        if prior is not None:
            return _already_published_result(prior, staged_paths=staged_paths)
        rev_parse = git_runner.run(
            repo_path,
            ["rev-parse", "HEAD"],
            timeout=timeout,
        )
        commit_sha = rev_parse.stdout.strip() if rev_parse.returncode == 0 else None
        reconcile_error = _fetch_and_reconcile_remote(
            git_runner,
            repo_path,
            config,
            staged_paths,
            timeout=timeout,
            fetch_timeout=fetch_timeout,
        )
        if reconcile_error is not None:
            return reconcile_error
        push_only = git_runner.run(
            repo_path,
            ["push", config.remote, config.branch],
            timeout=timeout,
        )
        if push_only.returncode != 0:
            logger.warning(
                "git push failed for campaign %s: %s",
                campaign_id,
                _sanitize_git_message(push_only.stderr),
            )
            return _failed_git_result(
                error_code=BLOG_GIT_PUBLICATION_PUSH_FAILED,
                staged_paths=staged_paths,
                remote=config.remote,
                branch=config.branch,
                commit_sha=commit_sha,
                include_recovery=True,
            )
        pushed_at = utc_now_iso()
        blog_git_publication = dict(prior or {})
        blog_git_publication.update(
            {
                "status": "pushed",
                "commit_sha": commit_sha,
                "remote": config.remote,
                "branch": config.branch,
                "staged_paths": staged_paths,
                "pushed_at": pushed_at,
            }
        )
        campaign["blog_git_publication"] = blog_git_publication
        metadata_written, metadata_error_code = _persist_campaign(
            base_path, campaign_id, campaign
        )
        return GitPublicationResult(
            status="completed",
            blog_git_publication=blog_git_publication,
            metadata_written=metadata_written,
            metadata_error_code=metadata_error_code,
        )

    duplicate_error = _check_duplicate_artifacts(
        git_runner,
        repo_path,
        config,
        staged_paths,
        campaign_id=campaign_id,
        timeout=timeout,
    )
    if duplicate_error is not None:
        return _failed_git_result(
            error_code=duplicate_error,
            staged_paths=staged_paths,
            remote=config.remote,
            branch=config.branch,
            include_recovery=True,
        )

    commit_message = _format_commit_message(
        config.commit_message_template,
        public_slug=public_slug,
        campaign_id=campaign_id,
        publication_date=publication_date,
    )
    commit_result = git_runner.run(
        repo_path,
        ["commit", "-m", commit_message],
        timeout=timeout,
    )
    if commit_result.returncode != 0:
        logger.warning(
            "git commit failed for campaign %s: %s",
            campaign_id,
            _sanitize_git_message(commit_result.stderr),
        )
        return _failed_git_result(
            error_code=BLOG_GIT_PUBLICATION_COMMIT_FAILED,
            staged_paths=staged_paths,
            remote=config.remote,
            branch=config.branch,
            include_recovery=True,
        )

    rev_parse = git_runner.run(
        repo_path,
        ["rev-parse", "HEAD"],
        timeout=timeout,
    )
    if rev_parse.returncode != 0:
        return _failed_git_result(
            error_code=BLOG_GIT_PUBLICATION_COMMIT_FAILED,
            staged_paths=staged_paths,
            remote=config.remote,
            branch=config.branch,
            include_recovery=True,
        )
    commit_sha = rev_parse.stdout.strip()
    committed_at = utc_now_iso()

    reconcile_error = _fetch_and_reconcile_remote(
        git_runner,
        repo_path,
        config,
        staged_paths,
        timeout=timeout,
        fetch_timeout=fetch_timeout,
    )
    if reconcile_error is not None:
        return reconcile_error

    push_result = git_runner.run(
        repo_path,
        ["push", config.remote, config.branch],
        timeout=timeout,
    )
    if push_result.returncode != 0:
        logger.warning(
            "git push failed for campaign %s: %s",
            campaign_id,
            _sanitize_git_message(push_result.stderr),
        )
        blog_git_publication = {
            "status": "failed",
            "error_code": BLOG_GIT_PUBLICATION_PUSH_FAILED,
            "commit_sha": commit_sha,
            "remote": config.remote,
            "branch": config.branch,
            "staged_paths": staged_paths,
            "committed_at": committed_at,
        }
        campaign["blog_git_publication"] = blog_git_publication
        metadata_written, metadata_error_code = _persist_campaign(
            base_path, campaign_id, campaign
        )
        result = _failed_git_result(
            error_code=BLOG_GIT_PUBLICATION_PUSH_FAILED,
            staged_paths=staged_paths,
            remote=config.remote,
            branch=config.branch,
            commit_sha=commit_sha,
            include_recovery=True,
        )
        result.blog_git_publication = blog_git_publication
        result.metadata_written = metadata_written
        result.metadata_error_code = metadata_error_code
        return result

    pushed_at = utc_now_iso()
    blog_git_publication = {
        "status": "pushed",
        "commit_sha": commit_sha,
        "remote": config.remote,
        "branch": config.branch,
        "staged_paths": staged_paths,
        "committed_at": committed_at,
        "pushed_at": pushed_at,
        "error_code": None,
    }
    campaign["blog_git_publication"] = blog_git_publication
    metadata_written, metadata_error_code = _persist_campaign(
        base_path, campaign_id, campaign
    )
    return GitPublicationResult(
        status="completed",
        blog_git_publication=blog_git_publication,
        metadata_written=metadata_written,
        metadata_error_code=metadata_error_code,
    )


def _persist_campaign(
    base_path: Path,
    campaign_id: str,
    campaign: dict[str, Any],
) -> tuple[bool, str | None]:
    write_result = write_campaign_metadata(base_path, campaign_id, campaign)
    if not write_result.written:
        return False, write_result.error_code
    return True, None


def merge_git_publication_into_publish_result(
    result: Any,
    git_result: GitPublicationResult,
    *,
    handoff_succeeded: bool,
) -> None:
    """Apply Git publication outcome onto a BlogPublishResult."""
    result.blog_git_publication = dict(git_result.blog_git_publication)
    if git_result.errors:
        result.errors = list(dict.fromkeys([*result.errors, *git_result.errors]))
    if not git_result.metadata_written and git_result.metadata_error_code:
        if git_result.metadata_error_code not in result.errors:
            result.errors.append(git_result.metadata_error_code)

    if git_result.status == "completed":
        if handoff_succeeded:
            result.status = "completed"
        return

    if handoff_succeeded:
        result.status = "partial"
    else:
        result.status = "failed"
