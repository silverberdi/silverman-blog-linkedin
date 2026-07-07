"""Lightweight validation for importable n8n workflow JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = (
    REPO_ROOT / "n8n" / "workflows" / "silverman-blog-linkedin-draft-generation.json"
)

FORBIDDEN_NODE_TYPES = {
    "n8n-nodes-base.executeCommand",
    "n8n-nodes-base.ssh",
    "n8n-nodes-base.readBinaryFile",
    "n8n-nodes-base.readBinaryFiles",
    "n8n-nodes-base.writeBinaryFile",
    "n8n-nodes-base.linkedIn",
    "n8n-nodes-base.github",
    "n8n-nodes-base.openAi",
}

FORBIDDEN_URL_PATTERNS = [
    re.compile(r"api\.deepseek\.com", re.I),
    re.compile(r"api\.openai\.com", re.I),
    re.compile(r"chatgpt", re.I),
    re.compile(r"ollama", re.I),
    re.compile(r"localhost:11434", re.I),
]

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9_-]{24,}"),
]

EXPECTED_NODE_NAMES = {
    "Manual Trigger",
    "Set Configuration",
    "Health Check",
    "Process Ready",
    "Process File",
    "Compute Source Public URL",
    "Generate LinkedIn Draft",
    "IF Health Ready",
    "IF Process Ready Failed",
    "IF Has Valid Candidates",
    "IF Process File OK",
    "IF Generate Completed",
    "Split Out Valid Files",
}

REQUIRED_NODE_TYPES = {
    "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.if",
    "n8n-nodes-base.set",
    "n8n-nodes-base.splitOut",
    "n8n-nodes-base.noOp",
    "n8n-nodes-base.code",
}

WORKER_ENDPOINT_FRAGMENTS = (
    "/health",
    "/process-ready",
    "/process-file",
    "/generate-linkedin-draft",
)

EXPECTED_CONFIG_VALUES = (
    "http://192.168.0.194:8010",
    "CHANGE_ME_WORKER_API_KEY",
    "worker_base_url",
    "worker_api_key",
)

STALE_WORKER_URLS = (
    "http://localhost:8000",
    "http://192.168.0.195:8000",
)

CANONICAL_READY_RELATIVE_PATH = (
    "blog-posts/ready/01-why-i-did-not-start-with-the-database.md"
)
CANONICAL_READY_MARKDOWN = """---
title: Why I did not start with the database
date: 2026-07-06 00:00:00 -0500
---

# Why I did not start with the database

Body copy for the smoke fixture.
"""
CANONICAL_SOURCE_PUBLIC_URL = (
    "https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/"
)


def _mirror_compute_source_public_url(
    *,
    relative_path: str,
    markdown_content: str,
    site_base_url: str = "https://silverman.pro",
) -> dict[str, str]:
    """Mirror Compute Source Public URL jsCode for fixture-level validation."""
    site_base = site_base_url.rstrip("/")
    relative_path = (relative_path or "").strip()
    if not relative_path:
        return {
            "source_public_url": "",
            "source_public_url_error": "missing_relative_path",
        }

    basename = relative_path.split("/")[-1]
    slug = re.sub(r"\.md$", "", basename, flags=re.I)
    slug_match = re.match(r"^(\d+)-(.+)$", slug)
    if slug_match:
        slug = slug_match.group(2)

    date_error = "missing_frontmatter_date"
    year = month = day = None
    fm_match = re.match(r"^---\s*\n([\s\S]*?)\n---", markdown_content or "")
    if fm_match:
        date_match = re.search(r"^date:\s*(.+)$", fm_match.group(1), flags=re.M)
        if date_match:
            date_portion = re.match(
                r"^(\d{4})-(\d{2})-(\d{2})",
                date_match.group(1).strip(),
            )
            if date_portion:
                year, month, day = date_portion.groups()
                date_error = None

    if date_error:
        return {"source_public_url": "", "source_public_url_error": date_error}

    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        return {
            "source_public_url": "",
            "source_public_url_error": "invalid_public_slug",
        }

    return {
        "source_public_url": f"{site_base}/{year}/{month}/{day}/{slug}/",
        "source_public_url_error": "",
    }


@pytest.fixture(scope="module")
def workflow() -> dict:
    assert WORKFLOW_PATH.is_file(), f"missing workflow file: {WORKFLOW_PATH}"
    return json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_workflow_file_exists():
    assert WORKFLOW_PATH.is_file()


def test_workflow_json_parses(workflow: dict):
    assert isinstance(workflow, dict)
    assert "nodes" in workflow
    assert "connections" in workflow


def test_workflow_has_expected_node_types(workflow: dict):
    node_types = {node["type"] for node in workflow["nodes"]}
    assert REQUIRED_NODE_TYPES.issubset(node_types)


def test_workflow_has_expected_node_names(workflow: dict):
    node_names = {node["name"] for node in workflow["nodes"]}
    assert EXPECTED_NODE_NAMES.issubset(node_names)


def test_workflow_has_http_request_nodes_for_worker_endpoints(workflow: dict):
    http_nodes = [
        node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.httpRequest"
    ]
    assert len(http_nodes) >= 4
    serialized = json.dumps([node.get("parameters", {}) for node in http_nodes])
    for fragment in WORKER_ENDPOINT_FRAGMENTS:
        assert fragment in serialized


def test_workflow_has_no_forbidden_node_types(workflow: dict):
    node_types = {node["type"] for node in workflow["nodes"]}
    assert node_types.isdisjoint(FORBIDDEN_NODE_TYPES)


def test_workflow_has_no_direct_llm_provider_urls(workflow_text: str):
    for pattern in FORBIDDEN_URL_PATTERNS:
        assert not pattern.search(workflow_text)


def test_workflow_has_no_obvious_real_secrets(workflow_text: str):
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(workflow_text)


def test_workflow_contains_configuration_placeholders(workflow_text: str):
    for value in EXPECTED_CONFIG_VALUES:
        assert value in workflow_text
    for stale_url in STALE_WORKER_URLS:
        assert stale_url not in workflow_text


def test_workflow_authenticated_calls_use_bearer_expression(workflow: dict):
    http_nodes = [
        node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.httpRequest"
    ]
    auth_nodes = [
        node
        for node in http_nodes
        if any(fragment in json.dumps(node.get("parameters", {})) for fragment in (
            "/process-ready",
            "/process-file",
            "/generate-linkedin-draft",
        ))
    ]
    assert len(auth_nodes) == 3
    for node in auth_nodes:
        headers = node["parameters"].get("headerParameters", {}).get("parameters", [])
        auth_header = next((h for h in headers if h.get("name") == "Authorization"), None)
        assert auth_header is not None
        assert "worker_api_key" in auth_header.get("value", "")
        assert "CHANGE_ME" not in auth_header.get("value", "")


def test_workflow_set_configuration_has_editorial_hints(workflow: dict):
    config_node = next(
        node for node in workflow["nodes"] if node["name"] == "Set Configuration"
    )
    assignments = config_node["parameters"]["assignments"]["assignments"]
    names = {item["name"] for item in assignments}
    assert {"tone", "audience", "variant", "worker_base_url", "worker_api_key"}.issubset(
        names
    )


def test_workflow_set_configuration_has_optional_public_context(workflow: dict):
    config_node = next(
        node for node in workflow["nodes"] if node["name"] == "Set Configuration"
    )
    assignments = {
        item["name"]: item["value"]
        for item in config_node["parameters"]["assignments"]["assignments"]
    }
    assert "source_public_url" not in assignments
    assert "site_base_url" in assignments
    assert assignments["site_base_url"] == "https://silverman.pro"
    assert "topic_theme" in assignments
    assert assignments["topic_theme"] == ""


def _compute_source_public_url_node(workflow: dict) -> dict:
    return next(
        node for node in workflow["nodes"] if node["name"] == "Compute Source Public URL"
    )


def test_compute_source_public_url_node_exists_and_is_code(workflow: dict):
    node = _compute_source_public_url_node(workflow)
    assert node["type"] == "n8n-nodes-base.code"
    assert node["parameters"].get("mode") == "runOnceForEachItem"


def test_compute_source_public_url_js_code_has_derivation_logic(workflow: dict):
    code = _compute_source_public_url_node(workflow)["parameters"]["jsCode"]
    assert "source_public_url_error" in code
    assert "site_base_url" in code
    assert "$json" in code
    assert "$input.first()" not in code
    assert re.search(r"\^\\d\+\)-", code) or "slugMatch" in code
    assert "date" in code
    assert "YYYY" in code or "datePortion" in code or "dateMatch" in code
    assert "missing_relative_path" in code
    assert "missing_frontmatter_date" in code
    assert "invalid_public_slug" in code
    assert re.search(r"a-z0-9", code)
    assert "return{json:" in code.replace(" ", "")
    assert "return[{json:" not in code.replace(" ", "")


def test_compute_source_public_url_supports_real_frontmatter_date_format():
    result = _mirror_compute_source_public_url(
        relative_path=CANONICAL_READY_RELATIVE_PATH,
        markdown_content=CANONICAL_READY_MARKDOWN,
    )
    assert result["source_public_url_error"] == ""
    assert result["source_public_url"] == CANONICAL_SOURCE_PUBLIC_URL


def test_compute_source_public_url_fixture_matches_workflow_js_code(workflow: dict):
    code = _compute_source_public_url_node(workflow)["parameters"]["jsCode"]
    assert "2026-07-06" in CANONICAL_READY_MARKDOWN
    assert re.search(r"\^date:\\s\*\(\.\+\)\$", code) or "dateMatch" in code
    assert "datePortion" in code
    result = _mirror_compute_source_public_url(
        relative_path=CANONICAL_READY_RELATIVE_PATH,
        markdown_content=CANONICAL_READY_MARKDOWN,
    )
    assert result["source_public_url"] == CANONICAL_SOURCE_PUBLIC_URL


def test_workflow_is_inactive(workflow: dict):
    assert workflow.get("active") is False


def _generate_linkedin_draft_node(workflow: dict) -> dict:
    return next(
        node for node in workflow["nodes"] if node["name"] == "Generate LinkedIn Draft"
    )


def test_generate_linkedin_draft_json_body_maps_optional_fields_conditionally(
    workflow: dict,
):
    json_body = _generate_linkedin_draft_node(workflow)["parameters"]["jsonBody"]
    assert "source_public_url" in json_body
    assert "topic_theme" in json_body
    assert "const item = $json" in json_body
    assert "item.source_public_url" in json_body
    assert "config.source_public_url" not in json_body
    assert "$('Compute Source Public URL').item" not in json_body
    assert "$('Process File').item" not in json_body
    assert ".trim()" in json_body
    assert "if (url)" in json_body
    assert "if (theme)" in json_body
    for field in (
        "source_relative_path",
        "markdown_content",
        "source_content_sha256",
        "tone",
        "audience",
        "variant",
    ):
        assert field in json_body


def test_generate_linkedin_draft_reads_source_public_url_from_current_item(
    workflow: dict,
):
    json_body = _generate_linkedin_draft_node(workflow)["parameters"]["jsonBody"]
    compact = json_body.replace(" ", "")
    assert "constitem=$json" in compact or "const item = $json" in json_body
    assert "item.source_public_url" in json_body
    assert "item.relative_path" in json_body
    assert "item.markdown_content" in json_body
    assert "item.content_sha256" in json_body

def test_generate_linkedin_draft_does_not_send_empty_optional_literals(workflow: dict):
    json_body = _generate_linkedin_draft_node(workflow)["parameters"]["jsonBody"]
    compact = json_body.replace(" ", "")
    assert 'source_public_url:""' not in compact
    assert "source_public_url:''" not in compact
    assert 'topic_theme:""' not in compact
    assert "topic_theme:''" not in compact


def test_set_generate_success_exposes_optional_public_context(workflow: dict):
    success_node = next(
        node for node in workflow["nodes"] if node["name"] == "Set Generate Success"
    )
    names = {
        item["name"]
        for item in success_node["parameters"]["assignments"]["assignments"]
    }
    assert {"source_public_url", "topic_theme"}.issubset(names)
