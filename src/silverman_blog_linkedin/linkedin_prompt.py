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
    source_public_url: str | None = None,
    topic_theme: str | None = None,
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
    if topic_theme and not source_public_url:
        user_lines.append(
            f"Topic theme hint (editorial only, do not invent facts): {topic_theme}"
        )
    user_lines.append("")
    user_lines.append("Blog Markdown:")
    user_lines.append(markdown_content)

    if source_public_url:
        user_lines.append("")
        user_lines.append("Public blog article URL (use verbatim in the draft):")
        user_lines.append(source_public_url)
        user_lines.append(
            "Include this public article URL exactly once near the end of the "
            "LinkedIn post as a natural call to action."
        )
        user_lines.append(
            "Vary the CTA wording naturally. Examples (choose similar phrasing, "
            "not necessarily these exact words):"
        )
        user_lines.append(f'- "Read the full story here: {source_public_url}"')
        user_lines.append(f'- "I wrote the full article here: {source_public_url}"')
        if topic_theme:
            user_lines.append(
                f'- "Read the full {topic_theme} story here: {source_public_url}"'
            )
        user_lines.append("Do not use the same fixed CTA phrase every time.")
        user_lines.append("Do not repeat the URL.")
        user_lines.append("Do not invent, modify, or substitute a different URL.")
        user_lines.append("Do not sound spammy.")
        user_lines.append("Do not include hashtags.")

    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(user_lines)},
    ]
