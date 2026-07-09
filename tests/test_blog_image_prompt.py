"""Tests for blog image prompt assembly."""

from __future__ import annotations

from silverman_blog_linkedin.blog_image_prompt import (
    NEGATIVE_PROMPT,
    build_blog_image_prompt,
    compute_prompt_hash,
)


def test_prompt_includes_title_and_description():
    prompt = build_blog_image_prompt(
        title="Why I Did Not Start With the Database",
        description="A senior practitioner's take on domain modeling.",
        tags=["databases", "architecture"],
        categories=["architecture"],
        body="# Why I Did Not Start With the Database\n\nBody text.",
    )

    assert "Why I Did Not Start With the Database" in prompt.positive
    assert "senior practitioner's take" in prompt.positive
    assert "databases" in prompt.positive
    assert "4:3 composition" in prompt.positive
    assert prompt.negative == NEGATIVE_PROMPT
    assert len(prompt.prompt_hash) == 64


def test_prompt_uses_body_excerpt_when_metadata_sparse():
    body = (
        "# Sparse Metadata Post\n\n"
        "The real problem is naming the business boundary before choosing storage."
    )
    prompt = build_blog_image_prompt(
        title="Sparse Metadata Post",
        body=body,
    )

    assert "naming the business boundary" in prompt.positive


def test_prompt_hash_is_stable_for_same_inputs():
    kwargs = {
        "title": "Stable Title",
        "description": "Stable description",
        "tags": ["ai"],
        "categories": ["leadership"],
        "body": "Body excerpt for hashing.",
    }
    first = build_blog_image_prompt(**kwargs)
    second = build_blog_image_prompt(**kwargs)

    assert first.prompt_hash == second.prompt_hash
    assert first.prompt_hash == compute_prompt_hash(first.positive, first.negative)
