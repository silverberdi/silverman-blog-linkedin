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
    assert "Topic theme hint" not in user
    assert "Public blog article URL" not in user


def test_build_chat_messages_includes_source_public_url():
    public_url = "https://silverman.pro/2026/07/06/my-post/"
    messages = build_chat_messages(
        markdown_content="# Post",
        source_public_url=public_url,
    )
    user = messages[1]["content"]

    assert public_url in user
    assert "exactly once" in user.lower()
    assert "call to action" in user.lower()


def test_build_chat_messages_omits_source_public_url_when_not_provided():
    messages = build_chat_messages(markdown_content="# Post")
    user = messages[1]["content"].lower()

    assert "public blog article url" not in user
    assert "call to action" not in user
    assert "do not repeat the url" not in user


def test_build_chat_messages_includes_topic_theme():
    messages = build_chat_messages(
        markdown_content="# Post",
        topic_theme="architecture",
    )
    user = messages[1]["content"]

    assert "architecture" in user
    assert "Topic theme hint" in user


def test_build_chat_messages_topic_theme_with_url_for_cta_phrasing():
    public_url = "https://silverman.pro/2026/07/06/my-post/"
    messages = build_chat_messages(
        markdown_content="# Post",
        source_public_url=public_url,
        topic_theme="architecture",
    )
    user = messages[1]["content"]

    assert "Read the full architecture story here" in user
    assert "Topic theme hint" not in user


def test_build_chat_messages_cta_allows_varied_wording():
    public_url = "https://silverman.pro/2026/07/06/my-post/"
    messages = build_chat_messages(
        markdown_content="# Post",
        source_public_url=public_url,
    )
    user = messages[1]["content"].lower()

    assert "vary the cta wording" in user
    assert "do not use the same fixed cta phrase every time" in user
    assert "read the full story here" in user
    assert "i wrote the full article here" in user
