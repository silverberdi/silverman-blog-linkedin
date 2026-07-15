"""Tests for Flow A deployment readiness script."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "flow_a_readiness.py"


def load_readiness_module():
    spec = importlib.util.spec_from_file_location("flow_a_readiness", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["flow_a_readiness"] = module
    spec.loader.exec_module(module)
    return module


far = load_readiness_module()

DOCUMENTED_OPERATIONAL_MILESTONES = ("88cd5bc", "96519c3", "9dba064")


@pytest.fixture
def repo_path() -> Path:
    return REPO_ROOT


def test_default_expected_commits_match_documented_operational_milestones() -> None:
    assert far.DEFAULT_EXPECTED_COMMITS == DOCUMENTED_OPERATIONAL_MILESTONES


def test_expected_commit_override_replaces_defaults(repo_path: Path) -> None:
    head = far.git_rev_parse(repo_path, "HEAD")
    assert head is not None

    report = far.ReadinessReport()

    def fake_http(method: str, url: str, **kwargs):
        if url.endswith("/health"):
            return 200, b'{"status":"healthy"}'
        if url.endswith("/openapi.json"):
            paths = {p: {} for p in far.REQUIRED_OPENAPI_PATHS}
            return 200, json.dumps({"paths": paths}).encode()
        return None, "unreachable"

    override = [head[:7]]
    with patch.object(far, "http_request", side_effect=fake_http):
        with patch.object(far, "list_running_containers", return_value=[]):
            far.run_phase0(
                report,
                repo_path=repo_path,
                worker_base_url="http://localhost:8000",
                n8n_base_url=None,
                expected_commits=override,
            )

    commits = next(c for c in report.checks if c.id == "expected_commits")
    assert commits.status == far.CheckStatus.PASS
    assert override[0] in commits.message
    for default_sha in far.DEFAULT_EXPECTED_COMMITS:
        if default_sha != override[0]:
            assert default_sha not in commits.message


def test_repo_current_and_required_files_pass(repo_path: Path) -> None:
    missing = [
        rel for rel in far.REQUIRED_FLOW_A_FILES if not (repo_path / rel).is_file()
    ]
    assert not missing, f"missing fixture files: {missing}"

    head = far.git_rev_parse(repo_path, "HEAD")
    assert head is not None


def test_missing_required_file_fails(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    report = far.ReadinessReport()

    def fake_http(method: str, url: str, **kwargs):
        return None, "unreachable"

    with patch.object(far, "http_request", side_effect=fake_http):
        with patch.object(far, "list_running_containers", return_value=[]):
            far.run_phase0(
                report,
                repo_path=tmp_path,
                worker_base_url="http://localhost:9999",
                n8n_base_url=None,
                expected_commits=["deadbeef"],
            )

    manifest = next(c for c in report.checks if c.id == "file_manifest")
    assert manifest.status == far.CheckStatus.FAIL


def test_workflow_active_true_fails(repo_path: Path) -> None:
    workflow = json.loads((repo_path / far.WORKFLOW_EXPORT_REL).read_text(encoding="utf-8"))
    workflow["active"] = True
    assert far.parse_workflow_active(workflow) is True


def test_workflow_active_false_passes(repo_path: Path) -> None:
    workflow = json.loads((repo_path / far.WORKFLOW_EXPORT_REL).read_text(encoding="utf-8"))
    assert far.parse_workflow_active(workflow) is False


def test_openapi_missing_required_paths_fails_with_stale_message() -> None:
    openapi_doc = {"paths": {"/health": {}, "/process-ready": {}}}
    missing = far.missing_openapi_paths(openapi_doc)
    assert "/publish-blog-post" in missing

    report = far.ReadinessReport()
    report.add(far.CheckResult("repo_path", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("git_head", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("git_origin_main", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("expected_commits", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("file_manifest", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("workflow_export_parse", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("workflow_active_false", 0, far.CheckStatus.PASS, "ok"))

    message = f"OpenAPI missing required Flow A paths: {', '.join(missing)}"
    report.add(far.CheckResult("openapi_paths", 0, far.CheckStatus.FAIL, message))
    assert far.STALE_WORKER_MESSAGE in report.deduped_remediation()
    assert far.repo_state_passed(report.checks)


def test_n8n_container_not_classified_as_worker() -> None:
    n8n_line = (
        "abc123\tsilverman-n8n-smoke\tdocker.n8n.io/n8nio/n8n:2.21.7\t"
        "0.0.0.0:5679->5678/tcp"
    )
    parsed = far.parse_docker_ps_line(n8n_line)
    assert parsed is not None
    container_id, name, image, ports = parsed
    assert far.is_n8n_container(name, image)
    assert far.worker_container_confidence(name, image, ports) < 0

    with patch.object(far, "list_running_containers", return_value=[parsed]):
        status, message = far.detect_worker_container_identity()

    assert status != far.CheckStatus.PASS
    assert "n8n" not in message.lower() or "could not be determined" in message.lower()
    assert far._optional_worker_container_identity() is None


def test_worker_container_detected_with_high_confidence() -> None:
    worker_line = (
        "def456\tsilverman-blog-linkedin-worker\tsilverman-blog-linkedin-worker:latest\t"
        "0.0.0.0:8010->8000/tcp"
    )
    parsed = far.parse_docker_ps_line(worker_line)
    assert parsed is not None
    container_id, name, image, ports = parsed
    assert far.worker_container_confidence(name, image, ports) > 0

    with patch.object(far, "list_running_containers", return_value=[parsed]):
        status, message = far.detect_worker_container_identity()

    assert status == far.CheckStatus.PASS
    assert "silverman-blog-linkedin-worker" in message
    assert "n8n" not in message.lower()


def test_unknown_worker_container_identity_does_not_fail_phase0() -> None:
    report = far.ReadinessReport()

    def fake_http(method: str, url: str, **kwargs):
        if url.endswith("/health"):
            return 200, b'{"status":"healthy"}'
        if url.endswith("/openapi.json"):
            paths = {p: {} for p in far.REQUIRED_OPENAPI_PATHS}
            return 200, json.dumps({"paths": paths}).encode()
        return None, "unreachable"

    n8n_only = (
        "abc123",
        "silverman-n8n-smoke",
        "docker.n8n.io/n8nio/n8n:2.21.7",
        "0.0.0.0:5679->5678/tcp",
    )

    with patch.object(far, "http_request", side_effect=fake_http):
        with patch.object(far, "list_running_containers", return_value=[n8n_only]):
            far.run_phase0(
                report,
                repo_path=REPO_ROOT,
                worker_base_url="http://localhost:8000",
                n8n_base_url=None,
                expected_commits=list(far.DEFAULT_EXPECTED_COMMITS),
            )

    identity = next(c for c in report.checks if c.id == "worker_container_identity")
    assert identity.status in {
        far.CheckStatus.SKIP,
        far.CheckStatus.PENDING,
        far.CheckStatus.WARN,
    }
    assert identity.status != far.CheckStatus.PASS
    assert far.WORKER_CONTAINER_IDENTITY_UNKNOWN_MESSAGE in identity.message
    assert far.phase0_passed(report)


def test_remediation_messages_are_deduplicated() -> None:
    report = far.ReadinessReport()
    report.append_remediation(far.STALE_WORKER_MESSAGE)
    report.append_remediation(far.STALE_WORKER_MESSAGE)
    report.append_remediation("n8n import: first")
    report.append_remediation("n8n import: first")

    deduped = report.deduped_remediation()
    assert deduped.count(far.STALE_WORKER_MESSAGE) == 1
    assert deduped.count("n8n import: first") == 1


def test_stale_worker_remediation_appears_once_after_openapi_fail() -> None:
    report = far.ReadinessReport()
    report.add(far.CheckResult("repo_path", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("git_head", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("git_origin_main", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("expected_commits", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("file_manifest", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("workflow_export_parse", 0, far.CheckStatus.PASS, "ok"))
    report.add(far.CheckResult("workflow_active_false", 0, far.CheckStatus.PASS, "ok"))
    report.add(
        far.CheckResult(
            "openapi_paths",
            0,
            far.CheckStatus.FAIL,
            "OpenAPI missing required Flow A paths: /publish-blog-post",
        )
    )

    human = far.render_human(report)
    payload = json.loads(json.dumps(report.to_json_dict()))

    assert report.deduped_remediation().count(far.STALE_WORKER_MESSAGE) == 1
    assert human.count(far.STALE_WORKER_MESSAGE) == 1
    assert payload["remediation"].count(far.STALE_WORKER_MESSAGE) == 1
    assert "Deploy completed but running worker still stale" in far.STALE_WORKER_MESSAGE
    assert "verify-worker-deploy.sh" in far.STALE_WORKER_MESSAGE


def test_health_unhealthy_fails() -> None:
    report = far.ReadinessReport()

    def fake_http(method: str, url: str, **kwargs):
        if url.endswith("/health"):
            return 503, b""
        return None, "unreachable"

    with patch.object(far, "http_request", side_effect=fake_http):
        far.run_phase0(
            report,
            repo_path=REPO_ROOT,
            worker_base_url="http://localhost:8000",
            n8n_base_url=None,
            expected_commits=["88cd5bc"],
        )

    health = next(c for c in report.checks if c.id == "worker_health")
    assert health.status == far.CheckStatus.FAIL


def test_n8n_unreachable_fails() -> None:
    report = far.ReadinessReport()

    def fake_http(method: str, url: str, **kwargs):
        if url.endswith("/health"):
            return 200, b'{"status":"healthy"}'
        if url.endswith("/openapi.json"):
            paths = {p: {} for p in far.REQUIRED_OPENAPI_PATHS}
            return 200, json.dumps({"paths": paths}).encode()
        return None, "connection refused"

    with patch.object(far, "http_request", side_effect=fake_http):
        with patch.object(far, "list_running_containers", return_value=[]):
            far.run_phase0(
                report,
                repo_path=REPO_ROOT,
                worker_base_url="http://localhost:8000",
                n8n_base_url="http://localhost:5679",
                expected_commits=list(far.DEFAULT_EXPECTED_COMMITS),
            )

    n8n = next(c for c in report.checks if c.id == "n8n_reachability")
    assert n8n.status == far.CheckStatus.FAIL


def test_n8n_import_inconclusive_reports_pending() -> None:
    report = far.ReadinessReport()

    def fake_http(method: str, url: str, **kwargs):
        if url.endswith("/health"):
            return 200, b'{"status":"healthy"}'
        if url.endswith("/openapi.json"):
            paths = {p: {} for p in far.REQUIRED_OPENAPI_PATHS}
            return 200, json.dumps({"paths": paths}).encode()
        if "5679" in url:
            return 200, b"ok"
        return None, "unreachable"

    with patch.object(far, "http_request", side_effect=fake_http):
        with patch.object(far, "list_running_containers", return_value=[]):
            far.run_phase0(
                report,
                repo_path=REPO_ROOT,
                worker_base_url="http://localhost:8000",
                n8n_base_url="http://localhost:5679",
                expected_commits=list(far.DEFAULT_EXPECTED_COMMITS),
            )

    import_check = next(c for c in report.checks if c.id == "n8n_workflow_import")
    assert import_check.status == far.CheckStatus.PENDING


def test_api_key_never_appears_in_text_or_json_output() -> None:
    secret = "super-secret-test-key-do-not-print"
    report = far.ReadinessReport()
    report.api_key_configured = True
    report.add(far.CheckResult("api_key_configured", 1, far.CheckStatus.PASS, "configured"))

    human = far.render_human(report)
    payload = json.dumps(report.to_json_dict())

    assert secret not in human
    assert secret not in payload
    assert "super-secret" not in human


def test_json_output_parses() -> None:
    report = far.ReadinessReport()
    report.phases_run = [0]
    report.add(far.CheckResult("repo_path", 0, far.CheckStatus.PASS, "ok"))
    parsed = json.loads(json.dumps(report.to_json_dict()))
    assert parsed["overall"] in {"pass", "fail", "pending"}
    assert isinstance(parsed["checks"], list)


def test_phase1_blocked_when_phase0_fails() -> None:
    report = far.ReadinessReport()
    report.add(far.CheckResult("worker_health", 0, far.CheckStatus.FAIL, "down"))
    assert not far.phase0_passed(report)

    gated = far.ReadinessReport()
    gated.checks = list(report.checks)
    if far.phase0_passed(gated):
        far.run_phase1(gated, worker_base_url="http://localhost:8000", api_key="secret")
    else:
        gated.add(
            far.CheckResult(
                "phase_gate",
                1,
                far.CheckStatus.FAIL,
                "Phase 1 blocked: Phase 0 deployment readiness failed",
            )
        )

    gate = next(c for c in gated.checks if c.id == "phase_gate")
    assert gate.status == far.CheckStatus.FAIL


def test_no_linkedin_api_call_attempted() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "linkedin.com" not in source.lower()
    assert "api.linkedin" not in source.lower()
    assert "http_request(" in source


def test_commit_is_ancestor_with_head(repo_path: Path) -> None:
    head = far.git_rev_parse(repo_path, "HEAD")
    assert head is not None
    assert far.commit_is_ancestor(repo_path, head, head)


def test_extract_openapi_paths() -> None:
    doc = {"paths": {"/health": {}, "/process-ready": {}}}
    assert far.extract_openapi_paths(doc) == {"/health", "/process-ready"}


def test_canonical_flow_a_n8n_identity_constants() -> None:
    assert far.FLOW_A_N8N_WORKFLOW_ID == "silvermanFlowAPublish01"
    assert far.FLOW_A_N8N_WORKFLOW_NAME == "Silverman Blog LinkedIn Flow A Publish"
    assert far.FLOW_A_N8N_EXPECTED_NODE_COUNT == 26
    assert far.WORKFLOW_EXPORT_REL.endswith(
        "silverman-blog-linkedin-flow-a-publish.json"
    )
    assert "draft-generation" in far.FLOW_B_DRAFT_WORKFLOW_EXPORT_REL


def test_assess_canonical_export_identity_on_repo_export(repo_path: Path) -> None:
    workflow_path = repo_path / far.WORKFLOW_EXPORT_REL
    data = json.loads(workflow_path.read_text(encoding="utf-8"))
    results = far.assess_canonical_export_identity(data)
    by_id = {check_id: (status, message) for check_id, status, message in results}
    assert by_id["canonical_workflow_name"][0] == far.CheckStatus.PASS
    assert by_id["canonical_workflow_node_count"][0] == far.CheckStatus.PASS
    assert by_id["canonical_workflow_no_schedule_triggers"][0] == far.CheckStatus.PASS
    assert by_id["canonical_workflow_http_only"][0] == far.CheckStatus.PASS
    assert by_id["canonical_workflow_identity"][0] == far.CheckStatus.PASS
    assert far.FLOW_A_N8N_WORKFLOW_ID in by_id["canonical_workflow_identity"][1]
    assert far.forbidden_trigger_types_present(data) == []
    assert far.forbidden_orchestration_types_present(data) == []


def test_assess_canonical_export_fails_for_wrong_name_and_active_schedule() -> None:
    workflow = {
        "name": "Wrong Name",
        "active": False,
        "nodes": [
            {"type": "n8n-nodes-base.manualTrigger"},
            {"type": "n8n-nodes-base.scheduleTrigger"},
        ],
    }
    results = far.assess_canonical_export_identity(workflow)
    by_id = {check_id: status for check_id, status, _ in results}
    assert by_id["canonical_workflow_name"] == far.CheckStatus.FAIL
    assert by_id["canonical_workflow_node_count"] == far.CheckStatus.FAIL
    assert by_id["canonical_workflow_no_schedule_triggers"] == far.CheckStatus.FAIL
    assert by_id["canonical_workflow_identity"] == far.CheckStatus.FAIL


def test_assess_canonical_export_fails_execute_command_and_gates_identity() -> None:
    workflow = {
        "name": far.FLOW_A_N8N_WORKFLOW_NAME,
        "active": False,
        "nodes": [
            {"type": "n8n-nodes-base.manualTrigger"},
            {"type": "n8n-nodes-base.executeCommand"},
        ]
        + [{"type": "n8n-nodes-base.noOp"} for _ in range(far.FLOW_A_N8N_EXPECTED_NODE_COUNT - 2)],
    }
    results = far.assess_canonical_export_identity(workflow)
    by_id = {check_id: status for check_id, status, _ in results}
    assert by_id["canonical_workflow_name"] == far.CheckStatus.PASS
    assert by_id["canonical_workflow_node_count"] == far.CheckStatus.PASS
    assert by_id["canonical_workflow_http_only"] == far.CheckStatus.FAIL
    assert by_id["canonical_workflow_identity"] == far.CheckStatus.FAIL


def test_select_canonical_imported_workflow_rejects_name_only_wrong_id() -> None:
    payload = [
        {
            "id": "wrongId",
            "name": far.FLOW_A_N8N_WORKFLOW_NAME,
            "active": False,
            "nodes": [{}] * far.FLOW_A_N8N_EXPECTED_NODE_COUNT,
        }
    ]
    match, error = far.select_canonical_imported_workflow(payload)
    assert match is None
    assert error is not None
    assert "found by name" in error
    assert far.FLOW_A_N8N_WORKFLOW_ID in error


def test_select_and_verify_canonical_imported_workflow_pass() -> None:
    workflow = {
        "id": far.FLOW_A_N8N_WORKFLOW_ID,
        "name": far.FLOW_A_N8N_WORKFLOW_NAME,
        "active": False,
        "nodes": [{}] * far.FLOW_A_N8N_EXPECTED_NODE_COUNT,
    }
    match, error = far.select_canonical_imported_workflow([workflow])
    assert error is None
    assert match is not None
    status, message = far.verify_canonical_imported_workflow(match)
    assert status == far.CheckStatus.PASS
    assert far.FLOW_A_N8N_WORKFLOW_ID in message


def test_phase2_reports_pending_import_with_canonical_id() -> None:
    report = far.ReadinessReport()

    def fake_http(method: str, url: str, **kwargs):
        return 200, b"ok"

    with patch.object(far, "http_request", side_effect=fake_http):
        far.run_phase2(report, n8n_base_url="http://192.168.0.194:5678")

    cfg = next(c for c in report.checks if c.id == "n8n_configuration")
    assert cfg.status == far.CheckStatus.PENDING
    assert far.FLOW_A_N8N_WORKFLOW_ID in cfg.message
    assert "pending_import" in cfg.message
    remediation = "\n".join(report.deduped_remediation())
    assert "import-flow-a-n8n-workflow.sh" in remediation
    assert far.FLOW_A_N8N_WORKFLOW_ID in remediation
    assert "--n8n-workflow-export" in remediation


def test_phase2_passes_with_confirmed_export(tmp_path: Path) -> None:
    export_path = tmp_path / "n8n-export.json"
    export_path.write_text(
        json.dumps(
            [
                {
                    "id": far.FLOW_A_N8N_WORKFLOW_ID,
                    "name": far.FLOW_A_N8N_WORKFLOW_NAME,
                    "active": False,
                    "nodes": [{}] * far.FLOW_A_N8N_EXPECTED_NODE_COUNT,
                }
            ]
        ),
        encoding="utf-8",
    )
    report = far.ReadinessReport()

    def fake_http(method: str, url: str, **kwargs):
        return 200, b"ok"

    with patch.object(far, "http_request", side_effect=fake_http):
        far.run_phase2(
            report,
            n8n_base_url="http://192.168.0.194:5678",
            n8n_workflow_export=export_path,
        )

    cfg = next(c for c in report.checks if c.id == "n8n_configuration")
    assert cfg.status == far.CheckStatus.PASS


def test_phase2_fails_when_export_has_name_but_wrong_id(tmp_path: Path) -> None:
    export_path = tmp_path / "n8n-export.json"
    export_path.write_text(
        json.dumps(
            [
                {
                    "id": "notCanonical",
                    "name": far.FLOW_A_N8N_WORKFLOW_NAME,
                    "active": False,
                    "nodes": [{}] * far.FLOW_A_N8N_EXPECTED_NODE_COUNT,
                }
            ]
        ),
        encoding="utf-8",
    )
    report = far.ReadinessReport()

    def fake_http(method: str, url: str, **kwargs):
        return 200, b"ok"

    with patch.object(far, "http_request", side_effect=fake_http):
        far.run_phase2(
            report,
            n8n_base_url="http://192.168.0.194:5678",
            n8n_workflow_export=export_path,
        )

    cfg = next(c for c in report.checks if c.id == "n8n_configuration")
    assert cfg.status == far.CheckStatus.FAIL
    assert "found by name" in cfg.message


def test_phase2_fails_when_n8n_unreachable() -> None:
    report = far.ReadinessReport()

    def fake_http(method: str, url: str, **kwargs):
        return None, "unreachable"

    with patch.object(far, "http_request", side_effect=fake_http):
        far.run_phase2(report, n8n_base_url="http://192.168.0.194:5678")

    cfg = next(c for c in report.checks if c.id == "n8n_configuration")
    assert cfg.status == far.CheckStatus.FAIL


def test_main_json_exit_code_without_secret_leak(repo_path: Path) -> None:
    import os

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--repo-path",
            str(repo_path),
            "--worker-base-url",
            "http://127.0.0.1:1",
            "--phase",
            "0",
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=os.environ.copy(),
    )
    assert result.stdout
    parsed = json.loads(result.stdout)
    assert "checks" in parsed
    assert parsed["api_key_configured"] is False
