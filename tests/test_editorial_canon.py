"""Tests for content-strategy/silverman-editorial-system.md section anchors."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CANON_PATH = (
    Path(__file__).resolve().parent.parent
    / "content-strategy"
    / "silverman-editorial-system.md"
)

HEADING_PATTERN = re.compile(r"^## .+ \{#([a-z0-9-]+)\}\s*$", re.MULTILINE)

FORBIDDEN_NOISE_TERMS = frozenset(
    {
        "Dairector",
    }
)

REQUIRED_ANCHORS = frozenset(
    {
        "purpose",
        "brand-positioning",
        "business-goals",
        "audience-map",
        "content-pillars",
        "topic-boundaries",
        "blog-post-rules",
        "linkedin-derivative-package",
        "linkedin-distribution-strategy",
        "no-redundancy-rules",
        "anti-ai-writing-rules",
        "voice-and-style",
        "cta-rules",
        "flow-a-vs-flow-b",
        "machine-readable-anchors",
        "validation-and-prompt-usage",
        "examples",
    }
)

ANTI_AI_REQUIRED_PHRASES = frozenset(
    {
        "Anti-AI posture",
        'What "AI-sounding" means in this project',
        "Forbidden AI-sounding openings",
        "Forbidden AI-sounding transitions",
        "Forbidden AI-sounding endings",
        "Forbidden AI-sounding vocabulary",
        "Structural patterns to avoid",
        "Humanization rules",
        "Rewrite rules",
        "Source-informed rationale",
        "AI writing detectors are not reliable enough to be used as final editorial verdicts.",
        "This project uses anti-AI rules as editorial quality rules, not authorship detection.",
        "AI-sounding editorial pattern",
    }
)

VOICE_AND_STYLE_REQUIRED_PHRASES = frozenset(
    {
        "Silverio writing style DNA",
        "Preferred argument patterns",
        "Disallowed writing patterns",
        "Common instinct → hidden cost → better architectural move",
        "Symptom in the team → architectural root cause → leadership action",
    }
)


def _parse_sections(text: str) -> dict[str, str]:
    """Return anchor_id -> section body (trimmed, excluding heading line)."""
    matches = list(HEADING_PATTERN.finditer(text))
    sections: dict[str, str] = {}

    for index, match in enumerate(matches):
        anchor_id = match.group(1)
        body_start = match.end()
        body_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()
        sections[anchor_id] = body

    return sections


@pytest.fixture(scope="module")
def canon_text() -> str:
    assert CANON_PATH.is_file(), f"Missing canonical artifact: {CANON_PATH}"
    return CANON_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def canon_sections(canon_text: str) -> dict[str, str]:
    return _parse_sections(canon_text)


def test_canon_file_exists_and_non_empty():
    assert CANON_PATH.is_file()
    assert CANON_PATH.read_text(encoding="utf-8").strip()


def test_all_required_anchors_present(canon_sections: dict[str, str]):
    found = set(canon_sections)
    missing = REQUIRED_ANCHORS - found
    assert not missing, f"Missing required anchors: {sorted(missing)}"


def test_required_anchor_bodies_non_empty(canon_sections: dict[str, str]):
    empty = sorted(
        anchor for anchor in REQUIRED_ANCHORS if not canon_sections.get(anchor, "").strip()
    )
    assert not empty, f"Empty section bodies for anchors: {empty}"


def test_anchor_headings_use_explicit_id_suffix(canon_text: str):
    for anchor in REQUIRED_ANCHORS:
        pattern = re.compile(rf"^## .+ \{{#{anchor}\}}\s*$", re.MULTILINE)
        assert pattern.search(canon_text), (
            f"Required heading with {{#{anchor}}} not found in canonical artifact"
        )


def test_canon_does_not_contain_forbidden_noise_terms(canon_text: str):
    found = sorted(term for term in FORBIDDEN_NOISE_TERMS if term in canon_text)
    assert not found, f"Canonical artifact must not contain noise terms: {found}"


def test_examples_reference_database_post(canon_sections: dict[str, str]):
    examples = canon_sections["examples"]
    assert "01-why-i-did-not-start-with-the-database" in examples
    assert "why-i-did-not-start-with-the-database" in examples
    assert "https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/" in examples
    assert "executive-recruiter" in examples
    assert "technical-architect" in examples
    assert "engineering-leadership" in examples
    assert "short-provocative" in examples


def test_voice_and_style_contains_operational_subsections(canon_sections: dict[str, str]):
    voice = canon_sections["voice-and-style"]
    missing = sorted(phrase for phrase in VOICE_AND_STYLE_REQUIRED_PHRASES if phrase not in voice)
    assert not missing, f"Missing voice-and-style phrases: {missing}"


def test_anti_ai_rules_contains_operational_subsections(canon_sections: dict[str, str]):
    anti_ai = canon_sections["anti-ai-writing-rules"]
    missing = sorted(phrase for phrase in ANTI_AI_REQUIRED_PHRASES if phrase not in anti_ai)
    assert not missing, f"Missing anti-ai-writing-rules phrases: {missing}"


def test_examples_contain_style_transformation(canon_sections: dict[str, str]):
    examples = canon_sections["examples"]
    assert "Style transformation examples" in examples
    assert (
        "The database matters. But it should not be the first thing that defines the system."
        in examples
    )
    assert "This design reduces coupling now, but it also creates a new ownership problem" in examples


def test_blog_post_rules_contain_blog_style_rules(canon_sections: dict[str, str]):
    blog = canon_sections["blog-post-rules"]
    assert "Blog style rules" in blog
    assert "one argument deeply" in blog.lower()
    assert "seo-first content" in blog.lower()


def test_linkedin_package_contains_linkedin_style_rules(canon_sections: dict[str, str]):
    linkedin = canon_sections["linkedin-derivative-package"]
    assert "LinkedIn style rules" in linkedin
    assert "compressed architectural arguments" in linkedin
    assert "independently readable" in linkedin
