"""Deterministic visual prompt assembly for blog hero images."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

BODY_EXCERPT_MAX_CHARS = 400

WHITESPACE_PATTERN = re.compile(r"\s+")


@dataclass(frozen=True)
class BlogImagePrompt:
    positive: str
    negative: str
    prompt_hash: str


POSITIVE_STYLE_SUFFIX = (
    "Professional technical editorial illustration, software architecture and systems design, "
    "4:3 composition, main subject centered with generous safe margins for cover crop, "
    "clean modern aesthetic, no readable text, no logos, no watermarks, "
    "suitable for engineering leadership blog hero image."
)

NEGATIVE_PROMPT = (
    "text, typography, letters, words, captions, subtitles, logos, brand marks, watermarks, "
    "UI screenshots with readable text, cluttered borders, cropped subject at edges, "
    "low quality, blurry, distorted, amateur, meme, cartoonish"
)


def _normalize_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raw = str(value).strip()
    return [raw] if raw else []


def _bounded_body_excerpt(
    body: str,
    *,
    title: str = "",
    max_chars: int = BODY_EXCERPT_MAX_CHARS,
) -> str:
    stripped = body.strip()
    if not stripped:
        return ""

    title_normalized = WHITESPACE_PATTERN.sub(" ", title.lower().strip())
    paragraphs = [part.strip() for part in stripped.split("\n\n") if part.strip()]
    for paragraph in paragraphs:
        text = re.sub(r"^#+\s*", "", paragraph).strip()
        if not text:
            continue
        text_normalized = WHITESPACE_PATTERN.sub(" ", text.lower().strip())
        if title_normalized and text_normalized == title_normalized:
            continue
        return text[:max_chars].strip()

    collapsed = WHITESPACE_PATTERN.sub(" ", stripped)
    collapsed = re.sub(r"^#+\s*", "", collapsed).strip()
    return collapsed[:max_chars].strip()


def _build_positive_prompt(
    *,
    title: str,
    description: str | None,
    tags: list[str],
    categories: list[str],
    body_excerpt: str,
) -> str:
    parts: list[str] = []

    if title.strip():
        parts.append(f"Topic: {title.strip()}.")

    if description and description.strip():
        parts.append(description.strip())

    theme_bits: list[str] = []
    if categories:
        theme_bits.append(f"categories: {', '.join(categories)}")
    if tags:
        theme_bits.append(f"tags: {', '.join(tags)}")
    if theme_bits:
        parts.append("; ".join(theme_bits))

    if body_excerpt:
        parts.append(f"Context: {body_excerpt}")

    parts.append(POSITIVE_STYLE_SUFFIX)
    return " ".join(parts)


def compute_prompt_hash(positive: str, negative: str) -> str:
    digest = hashlib.sha256()
    digest.update(positive.encode("utf-8"))
    digest.update(b"\0")
    digest.update(negative.encode("utf-8"))
    return digest.hexdigest()


def build_blog_image_prompt(
    *,
    title: str,
    description: Any = None,
    tags: Any = None,
    categories: Any = None,
    body: str = "",
) -> BlogImagePrompt:
    """Assemble positive/negative prompts from post metadata and body excerpt."""
    description_text = str(description).strip() if description is not None else ""
    tag_list = _normalize_list(tags)
    category_list = _normalize_list(categories)
    excerpt = _bounded_body_excerpt(body, title=title)

    positive = _build_positive_prompt(
        title=title,
        description=description_text or None,
        tags=tag_list,
        categories=category_list,
        body_excerpt=excerpt,
    )
    negative = NEGATIVE_PROMPT
    prompt_hash = compute_prompt_hash(positive, negative)
    return BlogImagePrompt(positive=positive, negative=negative, prompt_hash=prompt_hash)
