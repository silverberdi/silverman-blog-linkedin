"""Git publication configuration for the public GitHub Pages checkout."""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PUBLICATION_ENABLED = "SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED"
ENV_PUBLICATION_BRANCH = "SILVERMAN_BLOG_GIT_PUBLICATION_BRANCH"
ENV_PUBLICATION_REMOTE = "SILVERMAN_BLOG_GIT_PUBLICATION_REMOTE"
ENV_COMMIT_MESSAGE_TEMPLATE = "SILVERMAN_BLOG_GIT_COMMIT_MESSAGE_TEMPLATE"
ENV_TIMEOUT_SECONDS = "SILVERMAN_BLOG_GIT_PUBLICATION_TIMEOUT_SECONDS"

DEFAULT_BRANCH = "main"
DEFAULT_REMOTE = "origin"
DEFAULT_COMMIT_MESSAGE_TEMPLATE = "Add blog post: {public_slug} ({campaign_id})"
DEFAULT_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class GitPublicationSettings:
    publication_enabled: bool
    branch: str
    remote: str
    commit_message_template: str
    timeout_seconds: int


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_positive_int(raw: str, default: int) -> int:
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def load_git_publication_settings(
    environ: dict[str, str] | None = None,
) -> GitPublicationSettings:
    """Load Git publication settings from environment."""
    env = os.environ if environ is None else environ
    publication_enabled = _parse_bool(env.get(ENV_PUBLICATION_ENABLED, ""))
    branch = env.get(ENV_PUBLICATION_BRANCH, DEFAULT_BRANCH).strip() or DEFAULT_BRANCH
    remote = env.get(ENV_PUBLICATION_REMOTE, DEFAULT_REMOTE).strip() or DEFAULT_REMOTE
    commit_message_template = (
        env.get(ENV_COMMIT_MESSAGE_TEMPLATE, DEFAULT_COMMIT_MESSAGE_TEMPLATE).strip()
        or DEFAULT_COMMIT_MESSAGE_TEMPLATE
    )
    timeout_seconds = _parse_positive_int(
        env.get(ENV_TIMEOUT_SECONDS, str(DEFAULT_TIMEOUT_SECONDS)),
        DEFAULT_TIMEOUT_SECONDS,
    )
    return GitPublicationSettings(
        publication_enabled=publication_enabled,
        branch=branch,
        remote=remote,
        commit_message_template=commit_message_template,
        timeout_seconds=timeout_seconds,
    )
