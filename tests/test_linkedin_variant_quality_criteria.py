"""Tests for docs/operations/linkedin-variant-quality-criteria.md (US-016)."""

from __future__ import annotations

from pathlib import Path

import pytest

CRITERIA_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "operations"
    / "linkedin-variant-quality-criteria.md"
)

REQUIRED_HEADINGS = frozenset(
    {
        "## Purpose and scope",
        "## Relationship to US-015 supervision window",
        "## Normative default variant mapping",
        "## Quality criteria",
        "## Differentiation criteria (sibling variants)",
        "## Supervision-window checklist",
        "## Criteria failure, technical blocks, and deferred states",
        "## Preserved behavior (no duplication)",
    }
)

REQUIRED_PHRASES = frozenset(
    {
        "quality and differentiation criteria",
        "good enough and distinct enough",
        "optional supervision window",
        "executive-recruiter",
        "technical-architect",
        "engineering-leadership",
        "short-provocative",
        "audience lens",
        "publication objective",
        "Source fidelity",
        "anti-ai-writing-rules",
        "no-redundancy-rules",
        "Supervision-window checklist",
        "Criteria failure",
        "not a new worker `publish_state`",
        "US-015",
        "US-017",
        "BL-007",
        "linkedin-variant-review-policy.md",
        "GLOSSARY.md",
        "user-stories.md",
        "audience-map",
        "linkedin-derivative-package",
        "linkedin-distribution-strategy",
        "flow-a-vs-flow-b",
        "mandatory approval gate",
    }
)


@pytest.fixture(scope="module")
def criteria_text() -> str:
    assert CRITERIA_PATH.is_file(), f"Missing criteria artifact: {CRITERIA_PATH}"
    return CRITERIA_PATH.read_text(encoding="utf-8")


def test_criteria_file_exists_and_non_empty():
    assert CRITERIA_PATH.is_file()
    assert CRITERIA_PATH.read_text(encoding="utf-8").strip()


def test_criteria_contains_required_headings(criteria_text: str):
    missing = sorted(heading for heading in REQUIRED_HEADINGS if heading not in criteria_text)
    assert not missing, f"Missing required headings: {missing}"


def test_criteria_contains_required_phrases(criteria_text: str):
    missing = sorted(phrase for phrase in REQUIRED_PHRASES if phrase not in criteria_text)
    assert not missing, f"Missing required phrases: {missing}"


def test_criteria_does_not_instruct_bl007_wip_merge(criteria_text: str):
    assert "do not merge or run" in criteria_text.lower() or "Do not merge or run" in criteria_text
