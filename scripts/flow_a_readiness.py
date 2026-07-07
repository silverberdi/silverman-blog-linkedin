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

DEFAULT_EXPECTED_COMMITS = ("79f5345", "962ba2f", "53708eb")

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

WORKFLOW_EXPORT_REL = "n8n/workflows/silverman-blog-linkedin-flow-a-publish.json"

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
    "Confirm workflow remains inactive in n8n UI (export has active: false).",
    "Place a valid test blog post (+ PNG) in blog-posts/ready/.",
    "Execute the Flow A workflow using the Manual Trigger only (no cron/webhook).",
    "Verify campaign metadata, publish-confirmed URL, package artifacts, and scheduling metadata.",
]

PHASE4_MANUAL_STEPS = [
    "Re-run the Flow A workflow manual trigger for the same source post.",
    "Confirm worker returns idempotent already_* / skip responses where applicable.",
    "Verify no duplicate blog publish artifacts or duplicate LinkedIn variant files.",
    "Confirm publish_state remains pending until slice 8 (LinkedIn API deferred).",
]

N8N_IMPORT_CHECKLIST = [
    "Import n8n/workflows/silverman-blog-linkedin-flow-a-publish.json into n8n.",
    "Set worker_base_url to the deployed worker (e.g. http://192.168.0.194:8010).",
    "Set worker_api_key to match SILVERMAN_BLOG_LINKEDIN_API_KEY on the server.",
    "Leave workflow inactive in n8n until a future operational change enables scheduling.",
]


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
                    "n8n workflow import status inconclusive; pending manual import verification",
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


def run_phase2(report: ReadinessReport, *, n8n_base_url: str | None) -> None:
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
    if n8n_status is not None and 200 <= n8n_status < 500:
        report.add(
            CheckResult(
                "n8n_configuration",
                2,
                CheckStatus.PENDING,
                f"n8n reachable at {n8n_base}; workflow import/configuration pending operator checklist",
            )
        )
        for item in N8N_IMPORT_CHECKLIST:
            report.append_remediation(f"n8n import: {item}")
    else:
        report.add(
            CheckResult(
                "n8n_configuration",
                2,
                CheckStatus.FAIL,
                f"n8n not reachable at {n8n_base} for Phase 2 configuration smoke",
            )
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
        "--expected-commit",
        action="append",
        dest="expected_commits",
        help="Expected commit reachable from HEAD (repeatable). Defaults to Flow A baseline trio.",
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
            run_phase2(report, n8n_base_url=n8n_base_url)
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
