"""Tests for LinkedIn draft prompt builders."""

from silverman_blog_linkedin.linkedin_prompt import build_chat_messages


def test_build_chat_messages_has_system_and_user():
    messages = build_chat_messages(markdown_content="# Blog\n\nBody.")

    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"


def test_build_chat_messages_includes_markdown():
    markdown = "# My Architecture Post\n\nKey insight here."
    messages = build_chat_messages(markdown_content=markdown)

    assert markdown in messages[1]["content"]


def test_build_chat_messages_system_instructions():
    messages = build_chat_messages(markdown_content="content")

    system = messages[0]["content"].lower()
    assert "only" in system
    assert "json" in system
    assert "hashtag" in system
    assert "fabricate" in system
    assert "english" in system


def test_build_chat_messages_reflects_hints():
    messages = build_chat_messages(
        markdown_content="# Post",
        title="Architecture Lessons",
        tone="executive",
        audience="CTOs",
        variant="technical-leadership",
    )
    user = messages[1]["content"]

    assert "Architecture Lessons" in user
    assert "executive" in user
    assert "CTOs" in user
    assert "technical-leadership" in user


def test_build_chat_messages_without_optional_hints():
    messages = build_chat_messages(markdown_content="minimal content")
    user = messages[1]["content"]

    assert "Title hint" not in user
    assert "Tone hint" not in user
    assert "Audience hint" not in user
    assert "Variant hint" not in user
