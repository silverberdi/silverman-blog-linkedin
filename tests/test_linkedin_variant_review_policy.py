"""Tests for docs/operations/linkedin-variant-review-policy.md (US-015)."""

from __future__ import annotations

from pathlib import Path

import pytest

POLICY_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "operations"
    / "linkedin-variant-review-policy.md"
)

REQUIRED_HEADINGS = frozenset(
    {
        "## Purpose and scope",
        "## Strategy-driven publication default",
        "## Optional supervision window (`pending` before API send)",
        "## Mandatory review: Flow A vs Flow B",
        "## `publish_state`, enablement, and supervision",
        "## Blocked and deferred states",
        "## Future BL-007 eligibility (documentation only)",
    }
)

REQUIRED_PHRASES = frozenset(
    {
        "expected to publish",
        "optional supervision window",
        "Flow A",
        "Flow B",
        "mandatory",
        "SILVERMAN_LINKEDIN_PUBLICATION_ENABLED",
        "distribution_scheduled",
        "flow_a_complete",
        "US-016",
        "US-017",
        "BL-007",
        "auto_queue_pending",
        "not eligible for strategy-driven auto-queue",
        "GLOSSARY.md",
        "user-stories.md",
        "flow-a-vs-flow-b",
        "bl-007-auto-queue-pending-handoff.md",
    }
)


@pytest.fixture(scope="module")
def policy_text() -> str:
    assert POLICY_PATH.is_file(), f"Missing policy artifact: {POLICY_PATH}"
    return POLICY_PATH.read_text(encoding="utf-8")


def test_policy_file_exists_and_non_empty():
    assert POLICY_PATH.is_file()
    assert POLICY_PATH.read_text(encoding="utf-8").strip()


def test_policy_contains_required_headings(policy_text: str):
    missing = sorted(heading for heading in REQUIRED_HEADINGS if heading not in policy_text)
    assert not missing, f"Missing required headings: {missing}"


def test_policy_contains_required_phrases(policy_text: str):
    missing = sorted(phrase for phrase in REQUIRED_PHRASES if phrase not in policy_text)
    assert not missing, f"Missing required phrases: {missing}"


def test_policy_does_not_instruct_bl007_wip_merge(policy_text: str):
    assert "do not merge or run" in policy_text.lower() or "Do not merge or run" in policy_text
    assert "permanent LinkedIn enablement" in policy_text
