#!/usr/bin/env python3
"""Flow A deployment readiness and phased smoke verification."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# Operational capability milestones for Phase 0 ancestry checks (not last_verified_baseline).
# 88cd5bc — Flow A calendar completion archived (core operational validation floor)
# 96519c3 — Guarded blog Git publication automation (US-001)
# 9dba064 — Live-site confirmation and Git reconciliation (US-002)
DEFAULT_EXPECTED_COMMITS = ("88cd5bc", "96519c3", "9dba064")

REQUIRED_FLOW_A_FILES = (
    "n8n/workflows/silverman-blog-linkedin-flow-a-publish.json",
    "content-strategy/silverman-editorial-system.md",
    "src/silverman_blog_linkedin/blog_publish_flow.py",
    "src/silverman_blog_linkedin/linkedin_package_flow.py",
    "src/silverman_blog_linkedin/linkedin_distribution_schedule.py",
    "src/silverman_blog_linkedin/ready_post_validation.py",
)

REQUIRED_OPENAPI_PATHS = (
    "/health",
    "/process-ready",
    "/publish-blog-post",
    "/generate-linkedin-package",
    "/schedule-linkedin-distribution",
)

# Canonical Flow A n8n workflow identity (US-009 / US-010 / BL-004).
WORKFLOW_EXPORT_REL = "n8n/workflows/silverman-blog-linkedin-flow-a-publish.json"
FLOW_A_N8N_WORKFLOW_ID = "silvermanFlowAPublish01"
FLOW_A_N8N_WORKFLOW_NAME = "Silverman Blog LinkedIn Flow A Publish"
FLOW_A_N8N_EXPECTED_NODE_COUNT = 35
FLOW_A_N8N_SCHEDULE_CRON = "0 9 * * *"
FLOW_A_N8N_SCHEDULE_TRIGGER_TYPE = "n8n-nodes-base.scheduleTrigger"
FLOW_A_N8N_SINGLE_FLIGHT_GUARD_NAME = "Single-Flight Guard"
FLOW_B_DRAFT_WORKFLOW_EXPORT_REL = (
    "n8n/workflows/silverman-blog-linkedin-draft-generation.json"
)
# Not the Flow A publish orchestration workflow (BL-007 construction handoff / other).
NON_CANONICAL_FLOW_A_LOOKALIKES = (
    "n8n/workflows/silverman-blog-linkedin-publish-pending.json",
)
# Extra triggers beyond the single approved Schedule Trigger (US-010).
FORBIDDEN_EXTRA_N8N_TRIGGER_TYPE_FRAGMENTS = (
    "webhook",
)
# Legacy Cron node type (distinct from scheduleTrigger) remains forbidden.
FORBIDDEN_LEGACY_CRON_TYPE_FRAGMENTS = (
    "n8nnodesbasecron",  # n8n-nodes-base.cron normalized
)
FORBIDDEN_N8N_ORCHESTRATION_TYPE_FRAGMENTS = (
    "executecommand",
    "n8n-nodes-base.executecommand",
)

STALE_WORKER_MESSAGE = (
    "Repository checks passed but the running worker OpenAPI surface is missing "
    "required Flow A endpoints. Deploy completed but running worker still stale; "
    "verify deploy script rebuilds/recreates the worker container and that port 8010 "
    "points to the updated worker. The checkout may be current while the worker image "
    "was not rebuilt or the deploy ran against the wrong host/target directory. "
    "Remediation: run deploy/server/deploy-worker.sh on the Ubuntu server, then "
    "deploy/server/verify-worker-deploy.sh; if still stale use "
    "DEPLOY_FORCE_REBUILD=1 or docker compose build --no-cache && up --force-recreate "
    "(not executed by this script)."
)

WORKER_CONTAINER_IDENTITY_UNKNOWN_MESSAGE = (
    "Worker container identity could not be determined; this is informational only."
)

WORKER_CONTAINER_MARKERS = (
    "silverman-worker",
    "silverman-blog-linkedin",
)

N8N_CONTAINER_MARKERS = (
    "n8n",
    "n8nio",
)

WORKER_CONTAINER_PORT_MARKERS = (
    ":8010->",
    "0.0.0.0:8010",
    "[::]:8010",
)

PHASE3_MANUAL_STEPS = [
    "Import n8n/workflows/silverman-blog-linkedin-flow-a-publish.json if not already imported.",
    "Set worker_base_url and worker_api_key in the Flow A Set Configuration node.",
    "Confirm repository export remains active: false; server may be activated under US-010 ops.",
    "Prefer empty blog-posts/ready/ for no-op Manual runs during activation evidence.",
    "Execute the Flow A workflow using Manual Trigger (Schedule Trigger is daily 09:00 UTC).",
    "Verify campaign metadata, publish-confirmed URL, package artifacts, and scheduling metadata.",
]

PHASE4_MANUAL_STEPS = [
    "Re-run the Flow A workflow manual trigger for the same source post.",
    "Confirm worker returns idempotent already_* / skip responses where applicable.",
    "Verify no duplicate blog publish artifacts or duplicate LinkedIn variant files.",
    "Confirm publish_state remains pending until slice 8 (LinkedIn API deferred).",
]

N8N_IMPORT_CHECKLIST = [
    (
        "Copy n8n/workflows/silverman-blog-linkedin-flow-a-publish.json to the server "
        "import path (default: /home/silverman/n8n-imports/"
        "silverman-blog-linkedin-flow-a-publish.source.json)."
    ),
    (
        "Run deploy/server/import-flow-a-n8n-workflow.sh on the Ubuntu server "
        f"(sets stable workflow id {FLOW_A_N8N_WORKFLOW_ID}, worker_base_url, "
        "worker_api_key; leaves workflow inactive immediately after import)."
    ),
    (
        "Confirm import script reports OVERALL: PASS with canonical identity "
        f"id={FLOW_A_N8N_WORKFLOW_ID}, "
        f"{FLOW_A_N8N_EXPECTED_NODE_COUNT} nodes, Schedule Trigger "
        f"{FLOW_A_N8N_SCHEDULE_CRON} UTC, single-flight guard, and active=false."
    ),
    (
        "Activate silvermanFlowAPublish01 on the server only as a separate "
        "operator step (US-010); repository export must remain active: false. "
        "Verify with collect-flow-a-smoke-evidence.sh --expect-server-active."
    ),
    (
        "Do not treat Flow B draft-generation or publish-pending workflows as "
        "canonical Flow A orchestration. US-011 / BL-005 remain out of scope."
    ),
]

N8N_IMPORT_PENDING_MESSAGE = (
    "n8n workflow import status inconclusive from HTTP probe alone "
    f"(canonical id {FLOW_A_N8N_WORKFLOW_ID}); "
    "run deploy/server/import-flow-a-n8n-workflow.sh on the Ubuntu server "
    "and confirm OVERALL: PASS to satisfy manual import verification evidence"
)


class CheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"
    WARN = "warn"
    SKIP = "skip"


class OverallStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"


@dataclass
class CheckResult:
    id: str
    phase: int
    status: CheckStatus
    message: str


@dataclass
class ReadinessReport:
    phases_run: list[int] = field(default_factory=list)
    checks: list[CheckResult] = field(default_factory=list)
    remediation: list[str] = field(default_factory=list)
    api_key_configured: bool = False
    phase3_manual_steps: list[str] = field(default_factory=list)
    phase4_manual_steps: list[str] = field(default_factory=list)

    @property
    def overall(self) -> OverallStatus:
        statuses = {check.status for check in self.checks}
        if CheckStatus.FAIL in statuses:
            return OverallStatus.FAIL
        if CheckStatus.PENDING in statuses or CheckStatus.WARN in statuses:
            return OverallStatus.PENDING
        return OverallStatus.PASS

    def add(self, check: CheckResult) -> None:
        self.checks.append(check)
        if (
            check.status == CheckStatus.FAIL
            and check.id == "openapi_paths"
            and repo_state_passed(self.checks)
        ):
            self.append_remediation(STALE_WORKER_MESSAGE)

    def append_remediation(self, item: str) -> None:
        if item and item not in self.remediation:
            self.remediation.append(item)

    def deduped_remediation(self) -> list[str]:
        return dedupe_preserve_order(self.remediation)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "phases_run": self.phases_run,
            "overall": self.overall.value,
            "checks": [
                {
                    "id": check.id,
                    "phase": check.phase,
                    "status": check.status.value,
                    "message": check.message,
                }
                for check in self.checks
            ],
            "remediation": self.deduped_remediation(),
            "api_key_configured": self.api_key_configured,
            "phase3_manual_steps": list(self.phase3_manual_steps),
            "phase4_manual_steps": list(self.phase4_manual_steps),
        }


def _run_git(repo_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )


def git_rev_parse(repo_path: Path, ref: str) -> str | None:
    result = _run_git(repo_path, "rev-parse", ref)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def commit_is_ancestor(repo_path: Path, commit: str, head: str) -> bool:
    short = commit[:7] if len(commit) >= 7 else commit
    for candidate in (commit, short):
        result = _run_git(repo_path, "merge-base", "--is-ancestor", candidate, head)
        if result.returncode == 0:
            return True
    full = git_rev_parse(repo_path, commit)
    if full:
        result = _run_git(repo_path, "merge-base", "--is-ancestor", full, head)
        return result.returncode == 0
    return False


def extract_openapi_paths(openapi_doc: dict[str, Any]) -> set[str]:
    paths = openapi_doc.get("paths", {})
    if not isinstance(paths, dict):
        return set()
    return {str(path) for path in paths}


def missing_openapi_paths(openapi_doc: dict[str, Any]) -> list[str]:
    present = extract_openapi_paths(openapi_doc)
    return [path for path in REQUIRED_OPENAPI_PATHS if path not in present]


def parse_workflow_active(workflow_json: dict[str, Any]) -> bool | None:
    if "active" not in workflow_json:
        return None
    return bool(workflow_json["active"])


def workflow_node_types(workflow_json: dict[str, Any]) -> list[str]:
    nodes = workflow_json.get("nodes")
    if not isinstance(nodes, list):
        return []
    types: list[str] = []
    for node in nodes:
        if isinstance(node, dict):
            node_type = node.get("type")
            if isinstance(node_type, str) and node_type.strip():
                types.append(node_type)
    return types


def _normalize_node_type(node_type: str) -> str:
    return node_type.lower().replace(".", "").replace("-", "").replace("_", "")


def forbidden_trigger_types_present(workflow_json: dict[str, Any]) -> list[str]:
    """Return disallowed extra triggers (webhook / legacy cron), excluding scheduleTrigger."""
    found: list[str] = []
    for node_type in workflow_node_types(workflow_json):
        lowered = _normalize_node_type(node_type)
        if "scheduletrigger" in lowered:
            continue
        for fragment in FORBIDDEN_EXTRA_N8N_TRIGGER_TYPE_FRAGMENTS:
            if fragment in lowered:
                found.append(node_type)
                break
        else:
            # n8n-nodes-base.cron (legacy) — scheduleTrigger uses scheduletrigger fragment
            if lowered.endswith("cron") or lowered == "n8nnodesbasecron":
                found.append(node_type)
    return list(dict.fromkeys(found))


def schedule_trigger_nodes(workflow_json: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = workflow_json.get("nodes")
    if not isinstance(nodes, list):
        return []
    return [
        node
        for node in nodes
        if isinstance(node, dict)
        and isinstance(node.get("type"), str)
        and "scheduletrigger" in _normalize_node_type(node["type"])
    ]


def approved_daily_utc_schedule_present(
    workflow_json: dict[str, Any],
) -> tuple[bool, str]:
    """Require exactly one Schedule Trigger with cron 0 9 * * * and UTC semantics."""
    triggers = schedule_trigger_nodes(workflow_json)
    if len(triggers) == 0:
        return False, "missing Schedule Trigger (expected daily 09:00 UTC)"
    if len(triggers) > 1:
        return False, f"expected exactly one Schedule Trigger, found {len(triggers)}"
    trigger = triggers[0]
    serialized = json.dumps(trigger.get("parameters", {}))
    if FLOW_A_N8N_SCHEDULE_CRON not in serialized:
        return (
            False,
            f"Schedule Trigger cron must include {FLOW_A_N8N_SCHEDULE_CRON!r}",
        )
    settings = workflow_json.get("settings")
    settings_tz = ""
    if isinstance(settings, dict):
        settings_tz = str(settings.get("timezone") or "")
    options = trigger.get("parameters", {}).get("options")
    options_tz = ""
    if isinstance(options, dict):
        options_tz = str(options.get("timezone") or "")
    if settings_tz.upper() != "UTC" and options_tz.upper() != "UTC":
        return False, "Schedule Trigger / workflow settings must declare timezone UTC"
    return True, f"Schedule Trigger present with cron {FLOW_A_N8N_SCHEDULE_CRON} UTC"


def single_flight_guard_present(workflow_json: dict[str, Any]) -> bool:
    nodes = workflow_json.get("nodes")
    if not isinstance(nodes, list):
        return False
    return any(
        isinstance(node, dict) and node.get("name") == FLOW_A_N8N_SINGLE_FLIGHT_GUARD_NAME
        for node in nodes
    )


def manual_trigger_present(workflow_json: dict[str, Any]) -> bool:
    for node_type in workflow_node_types(workflow_json):
        if "manualtrigger" in _normalize_node_type(node_type):
            return True
    return False


def forbidden_orchestration_types_present(workflow_json: dict[str, Any]) -> list[str]:
    found: list[str] = []
    for node_type in workflow_node_types(workflow_json):
        lowered = _normalize_node_type(node_type)
        for fragment in FORBIDDEN_N8N_ORCHESTRATION_TYPE_FRAGMENTS:
            frag = fragment.lower().replace(".", "").replace("-", "").replace("_", "")
            if frag and frag in lowered:
                found.append(node_type)
                break
    return list(dict.fromkeys(found))


def select_canonical_imported_workflow(
    payload: Any,
    *,
    workflow_id: str = FLOW_A_N8N_WORKFLOW_ID,
    workflow_name: str = FLOW_A_N8N_WORKFLOW_NAME,
) -> tuple[dict[str, Any] | None, str | None]:
    """Resolve imported workflow by stable id only.

    Returns (workflow, error_message). Name-only matches are rejected (fail-closed).
    """
    candidates = payload if isinstance(payload, list) else [payload]
    match_by_id: dict[str, Any] | None = None
    match_by_name: dict[str, Any] | None = None
    for item in candidates:
        if not isinstance(item, dict):
            continue
        if item.get("id") == workflow_id:
            match_by_id = item
        if item.get("name") == workflow_name:
            match_by_name = item

    if match_by_id is None:
        if match_by_name is not None:
            observed_id = match_by_name.get("id")
            return (
                None,
                (
                    f"FAIL: workflow found by name {workflow_name!r} but id is "
                    f"{observed_id!r}; expected id {workflow_id!r}. "
                    "Re-run deploy/server/import-flow-a-n8n-workflow.sh"
                ),
            )
        return (
            None,
            (
                f"FAIL: workflow not found by id={workflow_id!r}. "
                "Re-run deploy/server/import-flow-a-n8n-workflow.sh"
            ),
        )
    return match_by_id, None


def verify_canonical_imported_workflow(
    workflow: dict[str, Any],
    *,
    workflow_id: str = FLOW_A_N8N_WORKFLOW_ID,
    workflow_name: str = FLOW_A_N8N_WORKFLOW_NAME,
    expected_nodes: int = FLOW_A_N8N_EXPECTED_NODE_COUNT,
) -> tuple[CheckStatus, str]:
    """Secondary asserts after id resolution: name, active=false, node count."""
    if workflow.get("id") != workflow_id:
        return (
            CheckStatus.FAIL,
            (
                f"FAIL: workflow id is {workflow.get('id')!r}; "
                f"expected {workflow_id!r}"
            ),
        )
    if workflow.get("name") != workflow_name:
        return (
            CheckStatus.FAIL,
            (
                f"FAIL: workflow name is {workflow.get('name')!r}; "
                f"expected {workflow_name!r}"
            ),
        )
    if workflow.get("active") is not False:
        return (
            CheckStatus.FAIL,
            f"FAIL: workflow active is {workflow.get('active')!r}, expected false",
        )
    nodes = workflow.get("nodes")
    node_count = len(nodes) if isinstance(nodes, list) else -1
    if node_count != expected_nodes:
        return (
            CheckStatus.FAIL,
            f"FAIL: workflow node count is {node_count}, expected {expected_nodes}",
        )
    return (
        CheckStatus.PASS,
        (
            f"PASS: imported canonical Flow A id={workflow_id!r} "
            f"name={workflow_name!r} nodes={node_count} active=false"
        ),
    )


def assess_canonical_export_identity(
    workflow_json: dict[str, Any],
) -> list[tuple[str, CheckStatus, str]]:
    """Return (check_id, status, message) tuples for repo export identity checks."""
    results: list[tuple[str, CheckStatus, str]] = []
    name = workflow_json.get("name")
    if name == FLOW_A_N8N_WORKFLOW_NAME:
        results.append(
            (
                "canonical_workflow_name",
                CheckStatus.PASS,
                f'Canonical Flow A workflow name is "{FLOW_A_N8N_WORKFLOW_NAME}"',
            )
        )
    else:
        results.append(
            (
                "canonical_workflow_name",
                CheckStatus.FAIL,
                f'Canonical Flow A workflow name is {name!r}; expected "{FLOW_A_N8N_WORKFLOW_NAME}"',
            )
        )

    nodes = workflow_json.get("nodes")
    node_count = len(nodes) if isinstance(nodes, list) else -1
    if node_count == FLOW_A_N8N_EXPECTED_NODE_COUNT:
        results.append(
            (
                "canonical_workflow_node_count",
                CheckStatus.PASS,
                (
                    f"Canonical Flow A workflow has "
                    f"{FLOW_A_N8N_EXPECTED_NODE_COUNT} nodes "
                    f"(stable import id {FLOW_A_N8N_WORKFLOW_ID})"
                ),
            )
        )
    else:
        results.append(
            (
                "canonical_workflow_node_count",
                CheckStatus.FAIL,
                (
                    f"Canonical Flow A workflow node count is {node_count}; "
                    f"expected {FLOW_A_N8N_EXPECTED_NODE_COUNT}"
                ),
            )
        )

    forbidden = forbidden_trigger_types_present(workflow_json)
    if forbidden:
        results.append(
            (
                "canonical_workflow_no_extra_triggers",
                CheckStatus.FAIL,
                (
                    "Canonical Flow A export contains forbidden extra trigger "
                    f"node types (webhook/legacy cron): {', '.join(forbidden)}"
                ),
            )
        )
    else:
        results.append(
            (
                "canonical_workflow_no_extra_triggers",
                CheckStatus.PASS,
                "Canonical Flow A export has no webhook/legacy-cron triggers beyond approved Schedule Trigger",
            )
        )

    schedule_ok, schedule_msg = approved_daily_utc_schedule_present(workflow_json)
    if schedule_ok:
        results.append(
            (
                "canonical_workflow_schedule_trigger",
                CheckStatus.PASS,
                schedule_msg,
            )
        )
    else:
        results.append(
            (
                "canonical_workflow_schedule_trigger",
                CheckStatus.FAIL,
                f"Canonical Flow A Schedule Trigger check failed: {schedule_msg}",
            )
        )

    if manual_trigger_present(workflow_json):
        results.append(
            (
                "canonical_workflow_manual_trigger",
                CheckStatus.PASS,
                "Canonical Flow A export retains Manual Trigger",
            )
        )
    else:
        results.append(
            (
                "canonical_workflow_manual_trigger",
                CheckStatus.FAIL,
                "Canonical Flow A export missing Manual Trigger",
            )
        )

    if single_flight_guard_present(workflow_json):
        results.append(
            (
                "canonical_workflow_single_flight_guard",
                CheckStatus.PASS,
                f"Single-flight guard node {FLOW_A_N8N_SINGLE_FLIGHT_GUARD_NAME!r} present",
            )
        )
    else:
        results.append(
            (
                "canonical_workflow_single_flight_guard",
                CheckStatus.FAIL,
                f"Missing single-flight guard node {FLOW_A_N8N_SINGLE_FLIGHT_GUARD_NAME!r}",
            )
        )

    forbidden_orch = forbidden_orchestration_types_present(workflow_json)
    if forbidden_orch:
        results.append(
            (
                "canonical_workflow_http_only",
                CheckStatus.FAIL,
                (
                    "Canonical Flow A export contains forbidden non-HTTP orchestration "
                    f"node types (ADR-0001): {', '.join(forbidden_orch)}"
                ),
            )
        )
    else:
        results.append(
            (
                "canonical_workflow_http_only",
                CheckStatus.PASS,
                "Canonical Flow A export has no Execute Command (HTTP-only orchestration)",
            )
        )

    prerequisite_ids = (
        "canonical_workflow_name",
        "canonical_workflow_node_count",
        "canonical_workflow_no_extra_triggers",
        "canonical_workflow_schedule_trigger",
        "canonical_workflow_manual_trigger",
        "canonical_workflow_single_flight_guard",
        "canonical_workflow_http_only",
    )
    prereq_failed = any(
        check_id in prerequisite_ids and status == CheckStatus.FAIL
        for check_id, status, _ in results
    )
    if prereq_failed:
        results.append(
            (
                "canonical_workflow_identity",
                CheckStatus.FAIL,
                (
                    "Canonical Flow A n8n identity aggregate FAIL: one or more "
                    "name/node-count/schedule/guard/HTTP-only checks failed "
                    f"(stable import id {FLOW_A_N8N_WORKFLOW_ID})"
                ),
            )
        )
    else:
        results.append(
            (
                "canonical_workflow_identity",
                CheckStatus.PASS,
                (
                    f"Canonical Flow A n8n identity: export={WORKFLOW_EXPORT_REL}; "
                    f"import id={FLOW_A_N8N_WORKFLOW_ID}; name={FLOW_A_N8N_WORKFLOW_NAME}; "
                    f"nodes={FLOW_A_N8N_EXPECTED_NODE_COUNT}; active=false; "
                    f"schedule={FLOW_A_N8N_SCHEDULE_CRON} UTC; "
                    f"not Flow B ({FLOW_B_DRAFT_WORKFLOW_EXPORT_REL})"
                ),
            )
        )
    return results


def load_env_var(env_file: Path | None, key: str) -> str | None:
    if env_file and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{key}="):
                value = line.split("=", 1)[1].strip().strip('"').strip("'")
                return value or None
    import os

    value = os.environ.get(key)
    return value if value else None


def http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: float = 10.0,
) -> tuple[int | None, bytes | str]:
    request = Request(url, data=body, method=method)
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()
    except URLError as exc:
        return None, str(exc.reason)


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def repo_state_passed(checks: list[CheckResult]) -> bool:
    repo_ids = {
        "repo_path",
        "git_head",
        "git_origin_main",
        "expected_commits",
        "file_manifest",
        "workflow_export_parse",
        "workflow_active_false",
    }
    repo_checks = [c for c in checks if c.id in repo_ids]
    return bool(repo_checks) and all(c.status == CheckStatus.PASS for c in repo_checks)


def run_phase0(
    report: ReadinessReport,
    *,
    repo_path: Path,
    worker_base_url: str,
    n8n_base_url: str | None,
    expected_commits: list[str],
) -> None:
    report.phases_run.append(0)

    if not repo_path.is_dir():
        report.add(
            CheckResult("repo_path", 0, CheckStatus.FAIL, f"Repo path does not exist: {repo_path}")
        )
        return
    report.add(CheckResult("repo_path", 0, CheckStatus.PASS, f"Repo path exists: {repo_path}"))

    git_dir = repo_path / ".git"
    if not git_dir.exists():
        report.add(
            CheckResult("git_head", 0, CheckStatus.FAIL, "Not a git repository (.git missing)")
        )
        return

    head = git_rev_parse(repo_path, "HEAD")
    if head:
        report.add(CheckResult("git_head", 0, CheckStatus.PASS, f"git HEAD: {head[:12]}"))
    else:
        report.add(CheckResult("git_head", 0, CheckStatus.FAIL, "git rev-parse HEAD failed"))

    origin_main = git_rev_parse(repo_path, "origin/main")
    if origin_main:
        report.add(
            CheckResult(
                "git_origin_main",
                0,
                CheckStatus.PASS,
                f"git origin/main: {origin_main[:12]}",
            )
        )
    else:
        report.add(
            CheckResult(
                "git_origin_main",
                0,
                CheckStatus.WARN,
                "git rev-parse origin/main unavailable (fetch origin/main if needed)",
            )
        )

    if head and expected_commits:
        missing_commits = [
            commit for commit in expected_commits if not commit_is_ancestor(repo_path, commit, head)
        ]
        if missing_commits:
            report.add(
                CheckResult(
                    "expected_commits",
                    0,
                    CheckStatus.FAIL,
                    f"Expected commits not reachable from HEAD: {', '.join(missing_commits)}",
                )
            )
        else:
            report.add(
                CheckResult(
                    "expected_commits",
                    0,
                    CheckStatus.PASS,
                    f"Expected commits present: {', '.join(expected_commits)}",
                )
            )

    missing_files = [rel for rel in REQUIRED_FLOW_A_FILES if not (repo_path / rel).is_file()]
    if missing_files:
        report.add(
            CheckResult(
                "file_manifest",
                0,
                CheckStatus.FAIL,
                f"Missing required Flow A files: {', '.join(missing_files)}",
            )
        )
    else:
        report.add(
            CheckResult(
                "file_manifest",
                0,
                CheckStatus.PASS,
                f"Required Flow A files present ({len(REQUIRED_FLOW_A_FILES)}/{len(REQUIRED_FLOW_A_FILES)})",
            )
        )

    workflow_path = repo_path / WORKFLOW_EXPORT_REL
    try:
        workflow_data = json.loads(workflow_path.read_text(encoding="utf-8"))
        report.add(
            CheckResult("workflow_export_parse", 0, CheckStatus.PASS, "Flow A workflow JSON parses")
        )
        active = parse_workflow_active(workflow_data)
        if active is True:
            report.add(
                CheckResult(
                    "workflow_active_false",
                    0,
                    CheckStatus.FAIL,
                    'Flow A workflow export has "active": true (must be false in export)',
                )
            )
        elif active is False:
            report.add(
                CheckResult(
                    "workflow_active_false",
                    0,
                    CheckStatus.PASS,
                    'Flow A workflow export has "active": false',
                )
            )
        else:
            report.add(
                CheckResult(
                    "workflow_active_false",
                    0,
                    CheckStatus.FAIL,
                    'Flow A workflow export missing top-level "active" flag',
                )
            )
        for check_id, status, message in assess_canonical_export_identity(workflow_data):
            report.add(CheckResult(check_id, 0, status, message))
            if status == CheckStatus.FAIL:
                if check_id == "canonical_workflow_node_count":
                    report.append_remediation(
                        "Pull latest origin/main and re-verify "
                        f"{WORKFLOW_EXPORT_REL} node count "
                        f"({FLOW_A_N8N_EXPECTED_NODE_COUNT})."
                    )
                elif check_id == "canonical_workflow_schedule_trigger":
                    report.append_remediation(
                        "Ensure exactly one Schedule Trigger with cron "
                        f"{FLOW_A_N8N_SCHEDULE_CRON} and timezone UTC in "
                        f"{WORKFLOW_EXPORT_REL}."
                    )
                elif check_id == "canonical_workflow_no_extra_triggers":
                    report.append_remediation(
                        "Remove webhook/legacy Cron trigger nodes from the "
                        "canonical Flow A export (only approved Schedule Trigger allowed)."
                    )
                elif check_id == "canonical_workflow_single_flight_guard":
                    report.append_remediation(
                        f"Restore {FLOW_A_N8N_SINGLE_FLIGHT_GUARD_NAME!r} on the "
                        "shared path after Set Configuration / before Health Check."
                    )
                elif check_id == "canonical_workflow_manual_trigger":
                    report.append_remediation(
                        "Restore Manual Trigger in the canonical Flow A export."
                    )
                elif check_id == "canonical_workflow_name":
                    report.append_remediation(
                        f'Restore workflow name "{FLOW_A_N8N_WORKFLOW_NAME}" '
                        f"in {WORKFLOW_EXPORT_REL}."
                    )
                elif check_id == "canonical_workflow_http_only":
                    report.append_remediation(
                        "Remove Execute Command (and other non-HTTP) nodes from "
                        f"{WORKFLOW_EXPORT_REL} (ADR-0001)."
                    )
    except (OSError, json.JSONDecodeError) as exc:
        report.add(
            CheckResult(
                "workflow_export_parse",
                0,
                CheckStatus.FAIL,
                f"Flow A workflow JSON unreadable or invalid: {exc}",
            )
        )

    worker_base = worker_base_url.rstrip("/")
    health_status, health_body = http_request("GET", f"{worker_base}/health")
    if health_status == 200:
        report.add(
            CheckResult("worker_health", 0, CheckStatus.PASS, f"GET {worker_base}/health HTTP 200")
        )
    else:
        report.add(
            CheckResult(
                "worker_health",
                0,
                CheckStatus.FAIL,
                f"GET {worker_base}/health failed (HTTP {health_status}); check worker port/base URL",
            )
        )

    openapi_status, openapi_body = http_request("GET", f"{worker_base}/openapi.json")
    openapi_doc: dict[str, Any] | None = None
    if openapi_status == 200 and isinstance(openapi_body, bytes):
        try:
            openapi_doc = json.loads(openapi_body.decode("utf-8"))
            report.add(
                CheckResult(
                    "worker_openapi",
                    0,
                    CheckStatus.PASS,
                    f"GET {worker_base}/openapi.json HTTP 200",
                )
            )
        except json.JSONDecodeError:
            report.add(
                CheckResult(
                    "worker_openapi",
                    0,
                    CheckStatus.FAIL,
                    "OpenAPI response is not valid JSON",
                )
            )
    else:
        report.add(
            CheckResult(
                "worker_openapi",
                0,
                CheckStatus.FAIL,
                f"GET {worker_base}/openapi.json failed (HTTP {openapi_status})",
            )
        )

    if openapi_doc is not None:
        missing_paths = missing_openapi_paths(openapi_doc)
        if missing_paths:
            message = f"OpenAPI missing required Flow A paths: {', '.join(missing_paths)}"
            report.add(CheckResult("openapi_paths", 0, CheckStatus.FAIL, message))
        else:
            report.add(
                CheckResult(
                    "openapi_paths",
                    0,
                    CheckStatus.PASS,
                    f"OpenAPI exposes required Flow A paths ({len(REQUIRED_OPENAPI_PATHS)}/{len(REQUIRED_OPENAPI_PATHS)})",
                )
            )

    container_status, container_message = detect_worker_container_identity()
    report.add(
        CheckResult(
            "worker_container_identity",
            0,
            container_status,
            container_message,
        )
    )

    if n8n_base_url:
        n8n_base = n8n_base_url.rstrip("/")
        n8n_status, _ = http_request("GET", n8n_base)
        if n8n_status is not None and 200 <= n8n_status < 500:
            report.add(
                CheckResult(
                    "n8n_reachability",
                    0,
                    CheckStatus.PASS,
                    f"n8n reachable at {n8n_base} (HTTP {n8n_status})",
                )
            )
            report.add(
                CheckResult(
                    "n8n_workflow_import",
                    0,
                    CheckStatus.PENDING,
                    N8N_IMPORT_PENDING_MESSAGE,
                )
            )
            for item in N8N_IMPORT_CHECKLIST:
                report.append_remediation(f"n8n import: {item}")
        else:
            report.add(
                CheckResult(
                    "n8n_reachability",
                    0,
                    CheckStatus.FAIL,
                    f"n8n not reachable at {n8n_base} (HTTP {n8n_status}); check host/port",
                )
            )


def is_n8n_container(name: str, image: str) -> bool:
    combined = f"{name} {image}".lower()
    return any(marker in combined for marker in N8N_CONTAINER_MARKERS)


def worker_container_confidence(name: str, image: str, ports: str) -> int:
    if is_n8n_container(name, image):
        return -1
    combined = f"{name} {image}".lower()
    ports_lower = ports.lower()
    score = 0
    if any(marker in combined for marker in WORKER_CONTAINER_MARKERS):
        score += 3
    if any(marker in ports_lower for marker in WORKER_CONTAINER_PORT_MARKERS):
        score += 2
    return score


def parse_docker_ps_line(line: str) -> tuple[str, str, str, str] | None:
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    container_id = parts[0].strip()
    name = parts[1].strip()
    image = parts[2].strip()
    ports = parts[3].strip() if len(parts) > 3 else ""
    if not container_id or not name:
        return None
    return container_id, name, image, ports


def list_running_containers() -> list[tuple[str, str, str, str]]:
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--format",
                "{{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Ports}}",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    containers: list[tuple[str, str, str, str]] = []
    for line in result.stdout.strip().splitlines():
        parsed = parse_docker_ps_line(line)
        if parsed:
            containers.append(parsed)
    return containers


def detect_worker_container_identity() -> tuple[CheckStatus, str]:
    containers = list_running_containers()
    if not containers:
        return (
            CheckStatus.SKIP,
            "Worker container identity not available (docker not running or not installed)",
        )

    matches: list[tuple[int, str]] = []
    for container_id, name, image, ports in containers:
        confidence = worker_container_confidence(name, image, ports)
        if confidence > 0:
            matches.append(
                (
                    confidence,
                    f"{name} {image}" + (f" ({ports})" if ports else ""),
                )
            )

    if not matches:
        return CheckStatus.WARN, WORKER_CONTAINER_IDENTITY_UNKNOWN_MESSAGE

    matches.sort(key=lambda item: item[0], reverse=True)
    best_confidence = matches[0][0]
    best_matches = [identity for confidence, identity in matches if confidence == best_confidence]
    if len(best_matches) == 1:
        return CheckStatus.PASS, f"Worker container identity: {best_matches[0]}"

    return CheckStatus.WARN, WORKER_CONTAINER_IDENTITY_UNKNOWN_MESSAGE


def _optional_worker_container_identity() -> str | None:
    status, message = detect_worker_container_identity()
    if status == CheckStatus.PASS and message.startswith("Worker container identity: "):
        return message.removeprefix("Worker container identity: ")
    return None


def phase0_passed(report: ReadinessReport) -> bool:
    phase0_checks = [c for c in report.checks if c.phase == 0]
    return bool(phase0_checks) and all(c.status != CheckStatus.FAIL for c in phase0_checks)


def run_phase1(
    report: ReadinessReport,
    *,
    worker_base_url: str,
    api_key: str | None,
) -> None:
    report.phases_run.append(1)
    report.api_key_configured = bool(api_key)

    if not api_key:
        report.add(
            CheckResult(
                "api_key_configured",
                1,
                CheckStatus.SKIP,
                "API key not configured; skipping authenticated POST /process-ready",
            )
        )
        return

    report.add(
        CheckResult(
            "api_key_configured",
            1,
            CheckStatus.PASS,
            "API key configured: true",
        )
    )

    worker_base = worker_base_url.rstrip("/")
    status, _ = http_request(
        "POST",
        f"{worker_base}/process-ready",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        body=b"{}",
    )
    if status == 200:
        report.add(
            CheckResult(
                "process_ready_contract",
                1,
                CheckStatus.PASS,
                f"POST {worker_base}/process-ready HTTP 200",
            )
        )
    elif status == 401:
        report.add(
            CheckResult(
                "process_ready_contract",
                1,
                CheckStatus.FAIL,
                "POST /process-ready returned HTTP 401; likely API key mismatch between worker and n8n",
            )
        )
    else:
        report.add(
            CheckResult(
                "process_ready_contract",
                1,
                CheckStatus.FAIL,
                f"POST /process-ready returned HTTP {status}",
            )
        )


def run_phase2(
    report: ReadinessReport,
    *,
    n8n_base_url: str | None,
    n8n_workflow_export: Path | None = None,
) -> None:
    report.phases_run.append(2)
    if not n8n_base_url:
        report.add(
            CheckResult(
                "n8n_configuration",
                2,
                CheckStatus.SKIP,
                "No --n8n-base-url provided; skipping Phase 2 n8n configuration smoke",
            )
        )
        return

    n8n_base = n8n_base_url.rstrip("/")
    n8n_status, _ = http_request("GET", n8n_base)
    if n8n_status is None or not (200 <= n8n_status < 500):
        report.add(
            CheckResult(
                "n8n_configuration",
                2,
                CheckStatus.FAIL,
                f"n8n not reachable at {n8n_base} for Phase 2 configuration smoke",
            )
        )
        return

    if n8n_workflow_export is None:
        report.add(
            CheckResult(
                "n8n_configuration",
                2,
                CheckStatus.PENDING,
                (
                    f"n8n reachable at {n8n_base}; canonical Flow A workflow "
                    f"import id {FLOW_A_N8N_WORKFLOW_ID} / configuration pending "
                    "operator checklist (pending_import until import script PASS "
                    "or --n8n-workflow-export confirms identity)"
                ),
            )
        )
        for item in N8N_IMPORT_CHECKLIST:
            report.append_remediation(f"n8n import: {item}")
        report.append_remediation(
            "Or re-run Phase 2 with --n8n-workflow-export PATH to a read-only "
            f"n8n export containing id {FLOW_A_N8N_WORKFLOW_ID}."
        )
        return

    export_path = n8n_workflow_export.expanduser()
    if not export_path.is_file():
        report.add(
            CheckResult(
                "n8n_configuration",
                2,
                CheckStatus.FAIL,
                f"--n8n-workflow-export not found: {export_path}",
            )
        )
        report.append_remediation(
            "Provide a readable n8n export JSON path, or run "
            "deploy/server/import-flow-a-n8n-workflow.sh / "
            "deploy/server/collect-flow-a-smoke-evidence.sh on the Ubuntu server."
        )
        return

    try:
        payload = json.loads(export_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        report.add(
            CheckResult(
                "n8n_configuration",
                2,
                CheckStatus.FAIL,
                f"n8n workflow export unreadable or invalid: {exc}",
            )
        )
        return

    match, select_error = select_canonical_imported_workflow(payload)
    if match is None:
        # Name-only match with wrong/missing id → FAIL; id absent entirely → PENDING
        if select_error and "found by name" in select_error:
            status = CheckStatus.FAIL
            message = select_error
        else:
            status = CheckStatus.PENDING
            message = (
                f"n8n export at {export_path} does not contain id "
                f"{FLOW_A_N8N_WORKFLOW_ID} (pending_import)"
            )
        report.add(CheckResult("n8n_configuration", 2, status, message))
        for item in N8N_IMPORT_CHECKLIST:
            report.append_remediation(f"n8n import: {item}")
        return

    status, message = verify_canonical_imported_workflow(match)
    report.add(CheckResult("n8n_configuration", 2, status, message))
    if status == CheckStatus.FAIL:
        report.append_remediation(
            "Re-run deploy/server/import-flow-a-n8n-workflow.sh so n8n contains "
            f"id {FLOW_A_N8N_WORKFLOW_ID}, active=false, "
            f"{FLOW_A_N8N_EXPECTED_NODE_COUNT} nodes."
        )


def attach_manual_phase_docs(report: ReadinessReport) -> None:
    report.phase3_manual_steps = list(PHASE3_MANUAL_STEPS)
    report.phase4_manual_steps = list(PHASE4_MANUAL_STEPS)


def render_human(report: ReadinessReport) -> str:
    lines: list[str] = []
    for phase in sorted(set(check.phase for check in report.checks)):
        lines.append(f"==> Flow A readiness (Phase {phase})")
        for check in report.checks:
            if check.phase != phase:
                continue
            label = check.status.value.upper()
            lines.append(f"{label:7} {check.id}: {check.message}")
        lines.append("")

    if report.phase3_manual_steps:
        lines.append("==> Phase 3 manual steps (operator)")
        for step in report.phase3_manual_steps:
            lines.append(f"  - {step}")
        lines.append("")

    if report.phase4_manual_steps:
        lines.append("==> Phase 4 manual steps (operator)")
        for step in report.phase4_manual_steps:
            lines.append(f"  - {step}")
        lines.append("")

    remediation = report.deduped_remediation()
    if remediation:
        lines.append("==> Remediation")
        for item in remediation:
            lines.append(f"  - {item}")
        lines.append("")

    lines.append(f"OVERALL: {report.overall.value.upper()}")
    lines.append(f"api_key_configured: {str(report.api_key_configured).lower()}")
    return "\n".join(lines)


def contains_secret_leak(text: str, secret: str) -> bool:
    if not secret:
        return False
    return secret in text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Flow A deployment readiness and phased smoke verification.",
    )
    parser.add_argument("--repo-path", type=Path, default=Path.cwd())
    parser.add_argument("--worker-base-url", default="http://localhost:8010")
    parser.add_argument("--n8n-base-url", default=None)
    parser.add_argument(
        "--n8n-workflow-export",
        type=Path,
        default=None,
        help=(
            "Optional read-only n8n workflow export JSON (single workflow or list) "
            "to confirm canonical id in Phase 2"
        ),
    )
    parser.add_argument(
        "--expected-commit",
        action="append",
        dest="expected_commits",
        help="Expected commit reachable from HEAD (repeatable). Replaces DEFAULT_EXPECTED_COMMITS entirely.",
    )
    parser.add_argument(
        "--phase",
        choices=("0", "1", "2", "all"),
        default="0",
        help="Phase to run: 0=readiness, 1=+worker contract, 2=+n8n config, all=0-2 plus manual checklists",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--api-key-env",
        default="SILVERMAN_BLOG_LINKEDIN_API_KEY",
        help="Environment variable name for worker API key (value never printed)",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional env file to load API key from (value never printed)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip Phase 0 gate for debugging only",
    )
    return parser


def run_readiness(
    *,
    repo_path: Path,
    worker_base_url: str,
    n8n_base_url: str | None,
    expected_commits: list[str] | None,
    phase: str,
    api_key: str | None,
    force: bool = False,
    n8n_workflow_export: Path | None = None,
) -> ReadinessReport:
    commits = expected_commits or list(DEFAULT_EXPECTED_COMMITS)
    report = ReadinessReport()

    run_phase0(
        report,
        repo_path=repo_path.resolve(),
        worker_base_url=worker_base_url,
        n8n_base_url=n8n_base_url,
        expected_commits=commits,
    )

    max_phase = {"0": 0, "1": 1, "2": 2, "all": 2}[phase]
    gate_ok = phase0_passed(report) or force

    if max_phase >= 1:
        if gate_ok:
            run_phase1(report, worker_base_url=worker_base_url, api_key=api_key)
        else:
            report.add(
                CheckResult(
                    "phase_gate",
                    1,
                    CheckStatus.FAIL,
                    "Phase 1 blocked: Phase 0 deployment readiness failed",
                )
            )

    if max_phase >= 2:
        if gate_ok:
            run_phase2(
                report,
                n8n_base_url=n8n_base_url,
                n8n_workflow_export=n8n_workflow_export,
            )
        else:
            report.add(
                CheckResult(
                    "phase_gate",
                    2,
                    CheckStatus.FAIL,
                    "Phase 2 blocked: Phase 0 deployment readiness failed",
                )
            )

    if phase == "all":
        attach_manual_phase_docs(report)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    api_key = load_env_var(args.env_file, args.api_key_env)
    report = run_readiness(
        repo_path=args.repo_path,
        worker_base_url=args.worker_base_url,
        n8n_base_url=args.n8n_base_url,
        expected_commits=args.expected_commits,
        phase=args.phase,
        api_key=api_key,
        force=args.force,
        n8n_workflow_export=args.n8n_workflow_export,
    )

    if args.json_output:
        output = json.dumps(report.to_json_dict(), indent=2)
        if api_key and contains_secret_leak(output, api_key):
            print("FAIL: secret leak detected in JSON output", file=sys.stderr)
            return 2
        print(output)
    else:
        output = render_human(report)
        if api_key and contains_secret_leak(output, api_key):
            print("FAIL: secret leak detected in output", file=sys.stderr)
            return 2
        print(output)

    if report.overall == OverallStatus.PASS:
        return 0
    if report.overall == OverallStatus.PENDING:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
