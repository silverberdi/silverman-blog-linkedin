"""Tests for docs/operations/linkedin-variant-supervision-mechanics.md (US-017)."""

from __future__ import annotations

from pathlib import Path

import pytest

MECHANICS_PATH = (
    Path(__file__).resolve().parent.parent
    / "docs"
    / "operations"
    / "linkedin-variant-supervision-mechanics.md"
)

REQUIRED_HEADINGS = frozenset(
    {
        "## Purpose and scope",
        "## Relationship to US-015 optional supervision",
        "## Relationship to US-016 criteria failure",
        "## Correction (edit) mechanics",
        "## Rejection and cancel: pre-queue vs post-queue",
        "## Defer/delay mechanics",
        "## `operator_supervision` metadata contract",
        "## Blocked and invalid actions",
        "## BL-007 auto-queue eligibility (implemented by US-018)",
        "## Preserved behavior (no duplication)",
    }
)

REQUIRED_PHRASES = frozenset(
    {
        "edit",
        "defer",
        "cancel",
        "pre_queue",
        "post_queue",
        "auto_queue_eligible",
        "BL-007",
        "US-015",
        "US-016",
        "criteria_failure",
        "linkedin-variant-review-policy.md",
        "linkedin-variant-quality-criteria.md",
        "GLOSSARY.md",
        "user-stories.md",
        "flow-a-vs-flow-b",
        "linkedin-distribution-strategy",
        "linkedin_supervision_variant_not_pending",
        "operator_supervision",
        "POST /correct-linkedin-variant",
        "POST /defer-linkedin-variant",
        "SILVERMAN_LINKEDIN_PUBLICATION_ENABLED",
    }
)


@pytest.fixture(scope="module")
def mechanics_text() -> str:
    assert MECHANICS_PATH.is_file(), f"Missing mechanics artifact: {MECHANICS_PATH}"
    return MECHANICS_PATH.read_text(encoding="utf-8")


def test_mechanics_file_exists_and_non_empty():
    assert MECHANICS_PATH.is_file()
    assert MECHANICS_PATH.read_text(encoding="utf-8").strip()


def test_mechanics_contains_required_headings(mechanics_text: str):
    missing = sorted(heading for heading in REQUIRED_HEADINGS if heading not in mechanics_text)
    assert not missing, f"Missing required headings: {missing}"


def test_mechanics_contains_required_phrases(mechanics_text: str):
    missing = sorted(phrase for phrase in REQUIRED_PHRASES if phrase not in mechanics_text)
    assert not missing, f"Missing required phrases: {missing}"


def test_mechanics_does_not_imply_deploy_or_activation(mechanics_text: str):
    assert "does not imply deploy, workflow activation, or operational validation" in (
        mechanics_text.lower()
    )
