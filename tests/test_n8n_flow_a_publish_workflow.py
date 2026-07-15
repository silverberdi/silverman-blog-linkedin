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
}

APPROVED_SCHEDULE_TRIGGER_TYPE = "n8n-nodes-base.scheduleTrigger"
EXPECTED_NODE_COUNT = 35
EXPECTED_SCHEDULE_CRON = "0 9 * * *"
SINGLE_FLIGHT_GUARD_NAME = "Single-Flight Guard"

FORBIDDEN_URL_PATTERNS = [
    re.compile(r"api\.deepseek\.com", re.I),
    re.compile(r"api\.openai\.com", re.I),
    re.compile(r"chatgpt", re.I),
    re.compile(r"ollama", re.I),
    re.compile(r"localhost:11434", re.I),
]

FORBIDDEN_LINKEDIN_HOST_PATTERNS = [
    re.compile(r"api\.linkedin\.com", re.I),
    re.compile(r"(?<![a-z])linkedin\.com", re.I),
]

# Worker LinkedIn *API publication* paths — Flow A stops at package/schedule metadata.
FORBIDDEN_LINKEDIN_PUBLICATION_PATHS = (
    "/queue-linkedin-publication",
    "/publish-linkedin-due-variants",
    "/cancel-linkedin-publication",
)

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
    "/complete-flow-a-ready-path",
)

EXPECTED_NODE_NAMES = {
    "Manual Trigger",
    "Schedule Trigger",
    "Set Configuration",
    "Single-Flight Guard",
    "IF Single-Flight Acquired",
    "Stop Skipped Already Running",
    "Health Check",
    "Process Ready",
    "Publish Blog Post",
    "Generate LinkedIn Package",
    "Schedule LinkedIn Distribution",
    "Complete Flow A Ready Path",
    "IF Health Ready",
    "IF Process Ready Failed",
    "IF Has Valid Candidates",
    "IF Publish Completed",
    "IF Package Completed",
    "IF Schedule Completed",
    "IF Ready Path Completed",
    "Split Out Valid Files",
    "Set Flow A Success",
    "Release Single-Flight Lock",
    "Set Publish Failed",
    "Set Package Failed",
    "Set Schedule Failed",
    "Set Ready Path Failed",
}

REQUIRED_NODE_TYPES = {
    "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.scheduleTrigger",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.if",
    "n8n-nodes-base.set",
    "n8n-nodes-base.splitOut",
    "n8n-nodes-base.noOp",
    "n8n-nodes-base.code",
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
    "git_publication",
    "live_site_confirmation",
    "update_calendar",
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


def test_workflow_has_manual_and_schedule_triggers(workflow: dict):
    node_types = {node["type"] for node in workflow["nodes"]}
    assert "n8n-nodes-base.manualTrigger" in node_types
    assert APPROVED_SCHEDULE_TRIGGER_TYPE in node_types
    assert node_types.isdisjoint(FORBIDDEN_TRIGGER_TYPES)
    schedule_nodes = [
        node
        for node in workflow["nodes"]
        if node["type"] == APPROVED_SCHEDULE_TRIGGER_TYPE
    ]
    assert len(schedule_nodes) == 1
    serialized = json.dumps(schedule_nodes[0].get("parameters", {}))
    assert EXPECTED_SCHEDULE_CRON in serialized
    options = schedule_nodes[0].get("parameters", {}).get("options") or {}
    settings = workflow.get("settings") or {}
    assert (
        str(options.get("timezone", "")).upper() == "UTC"
        or str(settings.get("timezone", "")).upper() == "UTC"
    )


def test_workflow_expected_node_count(workflow: dict):
    assert len(workflow["nodes"]) == EXPECTED_NODE_COUNT


def test_workflow_single_flight_guard_before_health(workflow: dict):
    names = {node["name"] for node in workflow["nodes"]}
    assert SINGLE_FLIGHT_GUARD_NAME in names
    assert "IF Single-Flight Acquired" in names
    assert "Stop Skipped Already Running" in names
    assert "Release Single-Flight Lock" in names
    connections = workflow["connections"]
    assert connections["Set Configuration"]["main"][0][0]["node"] == SINGLE_FLIGHT_GUARD_NAME
    assert (
        connections[SINGLE_FLIGHT_GUARD_NAME]["main"][0][0]["node"]
        == "IF Single-Flight Acquired"
    )
    assert connections["IF Single-Flight Acquired"]["main"][0][0]["node"] == "Health Check"
    assert (
        connections["IF Single-Flight Acquired"]["main"][1][0]["node"]
        == "Stop Skipped Already Running"
    )
    guard = next(n for n in workflow["nodes"] if n["name"] == SINGLE_FLIGHT_GUARD_NAME)
    code = guard["parameters"]["jsCode"]
    assert "skipped_already_running" in code
    assert "flowASingleFlight" in code
    assert "2 * 60 * 60 * 1000" in code or "TTL" in code
    assert ".silverman-flow-a-single-flight.lock" in code


def test_workflow_dual_triggers_enter_set_configuration(workflow: dict):
    connections = workflow["connections"]
    assert connections["Manual Trigger"]["main"][0][0]["node"] == "Set Configuration"
    assert connections["Schedule Trigger"]["main"][0][0]["node"] == "Set Configuration"


def test_workflow_retains_ready_folder_http_path(workflow: dict):
    http_nodes = [
        node for node in workflow["nodes"] if node["type"] == "n8n-nodes-base.httpRequest"
    ]
    serialized = json.dumps([node.get("parameters", {}) for node in http_nodes])
    assert "/process-ready" in serialized
    assert "/publish-blog-post" in serialized
    assert "/generate-linkedin-package" in serialized
    assert "/schedule-linkedin-distribution" in serialized
    assert "/editorial-calendar/execute-flow-a-due" not in serialized


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


def test_workflow_excludes_linkedin_api_publication_paths(workflow: dict, workflow_text: str):
    """US-011: Flow A orchestration must not invoke LinkedIn API publication endpoints."""
    node_types = {node["type"] for node in workflow["nodes"]}
    assert "n8n-nodes-base.linkedIn" not in node_types
    for pattern in FORBIDDEN_LINKEDIN_HOST_PATTERNS:
        assert not pattern.search(workflow_text)
    for path in FORBIDDEN_LINKEDIN_PUBLICATION_PATHS:
        assert path not in workflow_text
    assert "/schedule-linkedin-distribution" in workflow_text


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


def _http_node_by_name(workflow: dict, name: str) -> dict:
    return next(node for node in workflow["nodes"] if node["name"] == name)


def _if_node_by_name(workflow: dict, name: str) -> dict:
    return next(node for node in workflow["nodes"] if node["name"] == name)


def test_workflow_http_methods_and_urls(workflow: dict):
    health = _http_node_by_name(workflow, "Health Check")
    assert health["parameters"]["method"] == "GET"
    assert "/health" in health["parameters"]["url"]

    for name, path in (
        ("Process Ready", "/process-ready"),
        ("Publish Blog Post", "/publish-blog-post"),
        ("Generate LinkedIn Package", "/generate-linkedin-package"),
        ("Schedule LinkedIn Distribution", "/schedule-linkedin-distribution"),
    ):
        node = _http_node_by_name(workflow, name)
        assert node["parameters"]["method"] == "POST"
        assert path in node["parameters"]["url"]
        assert "worker_base_url" in node["parameters"]["url"]


def test_workflow_publish_if_branches_on_completed_not_failed(workflow: dict):
    publish_if = _if_node_by_name(workflow, "IF Publish Completed")
    conditions = publish_if["parameters"]["conditions"]["conditions"]
    assert len(conditions) == 1
    assert conditions[0]["leftValue"] == "={{ $json.status }}"
    assert conditions[0]["rightValue"] == "completed"

    for name in ("IF Package Completed", "IF Schedule Completed"):
        if_node = _if_node_by_name(workflow, name)
        if_conditions = if_node["parameters"]["conditions"]["conditions"]
        assert if_conditions[0]["rightValue"] == "completed"


def test_workflow_process_ready_if_branches_on_failed(workflow: dict):
    process_if = _if_node_by_name(workflow, "IF Process Ready Failed")
    conditions = process_if["parameters"]["conditions"]["conditions"]
    assert conditions[0]["leftValue"] == "={{ $json.status }}"
    assert conditions[0]["rightValue"] == "failed"


def _normalize_js_expr(expr: str) -> str:
    return re.sub(r"\s+", "", expr)


def test_workflow_publish_body_uses_split_item_relative_path_not_stale_source(
    workflow: dict,
):
    publish = _http_node_by_name(workflow, "Publish Blog Post")
    body = publish["parameters"]["jsonBody"]
    normalized = _normalize_js_expr(body)
    assert "item.relative_path" in body
    assert "source_relative_path:item.relative_path" in normalized
    assert "valid_files" not in body


def test_workflow_package_body_prefers_publish_response_campaign_id(workflow: dict):
    package = _http_node_by_name(workflow, "Generate LinkedIn Package")
    body = package["parameters"]["jsonBody"]
    normalized = _normalize_js_expr(body)
    assert "if(item.campaign_id)body.campaign_id=item.campaign_id" in normalized
    assert "$('Publish Blog Post')" not in body


def test_workflow_schedule_body_prefers_package_response_campaign_id(workflow: dict):
    schedule = _http_node_by_name(workflow, "Schedule LinkedIn Distribution")
    body = schedule["parameters"]["jsonBody"]
    normalized = _normalize_js_expr(body)
    assert "if(item.campaign_id)body.campaign_id=item.campaign_id" in normalized
    assert "$('Generate LinkedIn Package')" not in body


def test_workflow_forbids_webhook_and_legacy_cron_triggers(workflow: dict):
    node_types = {node["type"] for node in workflow["nodes"]}
    assert node_types.isdisjoint(FORBIDDEN_TRIGGER_TYPES)


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
