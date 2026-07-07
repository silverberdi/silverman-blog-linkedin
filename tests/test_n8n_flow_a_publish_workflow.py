"""Lightweight validation for Flow A n8n publish orchestration workflow JSON."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = (
    REPO_ROOT / "n8n" / "workflows" / "silverman-blog-linkedin-flow-a-publish.json"
)
DRAFT_WORKFLOW_PATH = (
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

FORBIDDEN_TRIGGER_TYPES = {
    "n8n-nodes-base.cron",
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.scheduleTrigger",
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

WORKER_ENDPOINT_FRAGMENTS = (
    "/health",
    "/process-ready",
    "/publish-blog-post",
    "/generate-linkedin-package",
    "/schedule-linkedin-distribution",
)

EXPECTED_NODE_NAMES = {
    "Manual Trigger",
    "Set Configuration",
    "Health Check",
    "Process Ready",
    "Publish Blog Post",
    "Generate LinkedIn Package",
    "Schedule LinkedIn Distribution",
    "IF Health Ready",
    "IF Process Ready Failed",
    "IF Has Valid Candidates",
    "IF Publish Completed",
    "IF Package Completed",
    "IF Schedule Completed",
    "Split Out Valid Files",
    "Set Flow A Success",
    "Set Publish Failed",
    "Set Package Failed",
    "Set Schedule Failed",
}

REQUIRED_NODE_TYPES = {
    "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.if",
    "n8n-nodes-base.set",
    "n8n-nodes-base.splitOut",
    "n8n-nodes-base.noOp",
}

EXPECTED_CONFIG_VALUES = (
    "http://192.168.0.194:8010",
    "CHANGE_ME_WORKER_API_KEY",
    "worker_base_url",
    "worker_api_key",
    "site_url",
    "topic_theme",
    "schedule_strategy",
    "start_at_utc",
    "timezone",
)

CANONICAL_CAMPAIGN_ID = "flow-a-2026-07-06-why-i-did-not-start-with-the-database"
WRONG_CAMPAIGN_ID = "flow-a-2026-07-06-01-why-i-did-not-start-with-the-database"


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


def test_workflow_name_identifies_flow_a(workflow: dict):
    name = workflow.get("name", "")
    assert "Flow A" in name


def test_workflow_is_inactive(workflow: dict):
    assert workflow.get("active") is False


def test_workflow_has_manual_trigger_only(workflow: dict):
    node_types = {node["type"] for node in workflow["nodes"]}
    assert "n8n-nodes-base.manualTrigger" in node_types
    assert node_types.isdisjoint(FORBIDDEN_TRIGGER_TYPES)


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
    assert len(http_nodes) >= 5
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


def test_workflow_authenticated_calls_use_bearer_expression(workflow: dict):
    http_nodes = [
        node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.httpRequest"
    ]
    auth_fragments = (
        "/process-ready",
        "/publish-blog-post",
        "/generate-linkedin-package",
        "/schedule-linkedin-distribution",
    )
    auth_nodes = [
        node
        for node in http_nodes
        if any(fragment in json.dumps(node.get("parameters", {})) for fragment in auth_fragments)
    ]
    assert len(auth_nodes) == 4
    for node in auth_nodes:
        headers = node["parameters"].get("headerParameters", {}).get("parameters", [])
        auth_header = next((h for h in headers if h.get("name") == "Authorization"), None)
        assert auth_header is not None
        assert "worker_api_key" in auth_header.get("value", "")
        assert "CHANGE_ME" not in auth_header.get("value", "")


def test_workflow_set_configuration_has_flow_a_fields(workflow: dict):
    config_node = next(
        node for node in workflow["nodes"] if node["name"] == "Set Configuration"
    )
    assignments = config_node["parameters"]["assignments"]["assignments"]
    names = {item["name"] for item in assignments}
    assert {
        "worker_base_url",
        "worker_api_key",
        "site_url",
        "topic_theme",
        "schedule_strategy",
        "start_at_utc",
        "timezone",
    }.issubset(names)
    assert "tone" not in names
    assert "audience" not in names
    assert "variant" not in names


def test_workflow_branches_on_completed_status(workflow: dict):
    if_nodes = [node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.if"]
    serialized = json.dumps([node.get("parameters", {}) for node in if_nodes])
    assert '"rightValue": "completed"' in serialized or '"rightValue":"completed"' in serialized.replace(
        " ", ""
    )
    assert '"rightValue": "failed"' in serialized or '"rightValue":"failed"' in serialized.replace(
        " ", ""
    )


def test_workflow_failure_branches_expose_errors_and_warnings(workflow: dict):
    failure_nodes = [
        node
        for node in workflow["nodes"]
        if node["type"] == "n8n-nodes-base.set"
        and node["name"]
        in {
            "Set Health Not Ready",
            "Set Process Ready Error",
            "Set Publish Failed",
            "Set Package Failed",
            "Set Schedule Failed",
        }
    ]
    assert len(failure_nodes) == 5
    for node in failure_nodes:
        names = {
            item["name"]
            for item in node["parameters"]["assignments"]["assignments"]
        }
        assert "errors" in names
        assert "warnings" in names


def test_workflow_success_branch_exposes_campaign_outputs(workflow: dict):
    success_node = next(
        node for node in workflow["nodes"] if node["name"] == "Set Flow A Success"
    )
    names = {
        item["name"]
        for item in success_node["parameters"]["assignments"]["assignments"]
    }
    assert {"campaign_id", "source_public_url", "variant_schedules"}.issubset(names)


def test_publish_blog_post_sends_source_relative_path(workflow: dict):
    publish_node = next(
        node for node in workflow["nodes"] if node["name"] == "Publish Blog Post"
    )
    json_body = publish_node["parameters"]["jsonBody"]
    assert "source_relative_path" in json_body
    assert "item.relative_path" in json_body


def test_generate_package_prefers_campaign_id_from_publish_response(workflow: dict):
    package_node = next(
        node for node in workflow["nodes"] if node["name"] == "Generate LinkedIn Package"
    )
    json_body = package_node["parameters"]["jsonBody"]
    assert "campaign_id" in json_body
    assert "item.campaign_id" in json_body
    assert "source_relative_path" in json_body


def test_schedule_distribution_uses_campaign_id(workflow: dict):
    schedule_node = next(
        node
        for node in workflow["nodes"]
        if node["name"] == "Schedule LinkedIn Distribution"
    )
    json_body = schedule_node["parameters"]["jsonBody"]
    assert "campaign_id" in json_body
    assert "item.campaign_id" in json_body


def test_workflow_does_not_reference_wrong_campaign_id_with_source_prefix(workflow_text: str):
    assert WRONG_CAMPAIGN_ID not in workflow_text


def test_canonical_campaign_id_format_uses_public_slug():
    assert CANONICAL_CAMPAIGN_ID == "flow-a-2026-07-06-why-i-did-not-start-with-the-database"
    assert "-01-" not in CANONICAL_CAMPAIGN_ID.split("-", 3)[-1]


def test_draft_generation_workflow_unchanged():
    assert DRAFT_WORKFLOW_PATH.is_file()
    draft = json.loads(DRAFT_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert draft.get("name") == "Silverman Blog LinkedIn Draft Generation"
    assert "process-file" in DRAFT_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "generate-linkedin-draft" in DRAFT_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "publish-blog-post" not in DRAFT_WORKFLOW_PATH.read_text(encoding="utf-8")
