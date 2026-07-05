"""Internal LinkedIn draft prompt builders (not stored in metadata or responses)."""

from __future__ import annotations

_SYSTEM_PROMPT = """You are a senior software architect writing LinkedIn posts for a professional audience.

Output ONLY the LinkedIn post draft text. Do not include JSON, markdown code fences, explanations, preamble, labels, or commentary.

Write in English with a professional, human tone suitable for senior architecture and software leadership readers.

Derive content ONLY from the blog Markdown provided by the user. Do not fabricate facts, metrics, names, companies, or URLs that are not present in the input.

Do not include hashtags.

The output is for human review before publishing—not for auto-publishing."""


def build_chat_messages(
    *,
    markdown_content: str,
    title: str | None = None,
    tone: str | None = None,
    audience: str | None = None,
    variant: str | None = None,
) -> list[dict[str, str]]:
    """Build system and user messages for DeepSeek chat completions."""
    user_lines = [
        "Transform the following blog Markdown into one LinkedIn post draft.",
        "Follow all system instructions exactly.",
    ]
    if title:
        user_lines.append(f"Title hint (editorial only, do not invent facts): {title}")
    if tone:
        user_lines.append(f"Tone hint: {tone}")
    if audience:
        user_lines.append(f"Audience hint: {audience}")
    if variant:
        user_lines.append(f"Variant hint: {variant}")
    user_lines.append("")
    user_lines.append("Blog Markdown:")
    user_lines.append(markdown_content)

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(user_lines)},
    ]
