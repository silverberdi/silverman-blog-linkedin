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
