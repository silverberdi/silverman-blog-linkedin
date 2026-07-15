"""Lightweight validation for Ubuntu server deployment artifacts."""

from __future__ import annotations

import re
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SERVER = REPO_ROOT / "deploy" / "server"

COMPOSE_PATH = DEPLOY_SERVER / "silverman-worker.compose.yaml"
ENV_EXAMPLE_PATH = DEPLOY_SERVER / "silverman-worker.env.example"
DEPLOY_SCRIPT_PATH = DEPLOY_SERVER / "deploy-worker.sh"
SMOKE_SCRIPT_PATH = DEPLOY_SERVER / "smoke-worker.sh"
VERIFY_DEPLOY_SCRIPT_PATH = DEPLOY_SERVER / "verify-worker-deploy.sh"
IMPORT_FLOW_A_SCRIPT_PATH = DEPLOY_SERVER / "import-flow-a-n8n-workflow.sh"
COLLECT_FLOW_A_EVIDENCE_SCRIPT_PATH = DEPLOY_SERVER / "collect-flow-a-smoke-evidence.sh"
FLOW_A_WORKER_SMOKE_SCRIPT_PATH = DEPLOY_SERVER / "run-flow-a-worker-smoke.sh"
LINKEDIN_PUBLICATION_SMOKE_SCRIPT_PATH = DEPLOY_SERVER / "run-linkedin-publication-smoke.sh"
VERIFY_ROTATION_SCRIPT_PATH = DEPLOY_SERVER / "verify-worker-api-key-rotation.sh"
DEPLOYMENT_DOC_PATH = REPO_ROOT / "docs" / "deployment" / "ubuntu-server-worker-deployment.md"

REQUIRED_ENV_VARS = (
    "SILVERMAN_BLOG_LINKEDIN_API_KEY",
    "DEEPSEEK_API_KEY",
    "DEEPSEEK_MODEL",
    "DEEPSEEK_TIMEOUT_SECONDS",
    "DEEPSEEK_MAX_OUTPUT_TOKENS",
)

PLACEHOLDER_VALUES = {
    "SILVERMAN_BLOG_LINKEDIN_API_KEY": "CHANGE_ME_WORKER_API_KEY",
    "DEEPSEEK_API_KEY": "CHANGE_ME_DEEPSEEK_API_KEY",
}

SECRET_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"Bearer\s+[a-zA-Z0-9_-]{24,}"),
]


@pytest.fixture
def compose_text() -> str:
    assert COMPOSE_PATH.is_file(), f"missing compose file: {COMPOSE_PATH}"
    return COMPOSE_PATH.read_text(encoding="utf-8")


def test_compose_file_exists() -> None:
    assert COMPOSE_PATH.is_file()


def test_dockerfile_installs_git_binary() -> None:
    dockerfile = REPO_ROOT / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")
    assert "apt-get install" in content
    assert "git" in content
    assert "git --version" in content


def test_compose_port_mapping(compose_text: str) -> None:
    assert '"8010:8000"' in compose_text or "8010:8000" in compose_text


def test_compose_port_environment(compose_text: str) -> None:
    assert re.search(r'PORT:\s*"?8000"?', compose_text)


def test_compose_base_path_environment(compose_text: str) -> None:
    assert (
        "SILVERMAN_BLOG_LINKEDIN_BASE_PATH: /data/silverman-blog-linkedin"
        in compose_text
    )


def test_compose_editorial_volume_mount(compose_text: str) -> None:
    expected = (
        "/home/silverman/compartido_mac/silverman-blog-linkedin:"
        "/data/silverman-blog-linkedin"
    )
    assert expected in compose_text


def test_compose_public_blog_repo_environment(compose_text: str) -> None:
    assert "SILVERMAN_GITHUB_PAGES_REPO_PATH: /public-blog" in compose_text
    assert "SILVERMAN_SITE_URL:" in compose_text
    assert "https://silverman.pro" in compose_text


def test_compose_public_blog_repo_volume_mount(compose_text: str) -> None:
    assert "SILVERMAN_PUBLIC_BLOG_REPO_PATH" in compose_text
    assert "/public-blog" in compose_text
    assert "silverberdi.github.io" in compose_text


def test_compose_build_revision_arg(compose_text: str) -> None:
    assert "BUILD_REVISION" in compose_text


def test_compose_does_not_reference_local_ai_stack(compose_text: str) -> None:
    assert "local-ai-stack" not in compose_text


def test_env_example_exists() -> None:
    assert ENV_EXAMPLE_PATH.is_file()


def test_env_example_documents_required_variables() -> None:
    content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    for var in REQUIRED_ENV_VARS:
        assert f"{var}=" in content, f"missing {var} in env example"


def test_env_example_documents_public_blog_repo_path() -> None:
    content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    assert "SILVERMAN_PUBLIC_BLOG_REPO_PATH=" in content
    assert "/home/silverman/silverberdi.github.io" in content
    assert "SILVERMAN_SITE_URL=" in content
    assert "https://silverman.pro" in content


def test_env_example_uses_placeholders_only() -> None:
    content = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    for var, placeholder in PLACEHOLDER_VALUES.items():
        assert f"{var}={placeholder}" in content
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(content), f"env example may contain a real secret: {pattern}"


def test_deploy_and_smoke_scripts_exist() -> None:
    assert DEPLOY_SCRIPT_PATH.is_file()
    assert SMOKE_SCRIPT_PATH.is_file()


def test_deploy_and_smoke_scripts_are_executable() -> None:
    for path in (DEPLOY_SCRIPT_PATH, SMOKE_SCRIPT_PATH):
        mode = path.stat().st_mode
        assert mode & stat.S_IXUSR, f"{path.name} is not executable (owner)"


def test_deploy_script_safe_compose_usage() -> None:
    content = DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "docker compose -f silverman-worker.compose.yaml build" in content
    assert "docker compose -f silverman-worker.compose.yaml up -d --force-recreate" in content
    assert "docker compose down" not in content
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "docker compose" in stripped:
            assert "local-ai-stack" not in stripped
            assert "silverman-worker.compose.yaml" in stripped


def test_deploy_script_syncs_src_directory_as_top_level_folder() -> None:
    content = DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    assert '"${SOURCE_ROOT}/src" \\' in content
    assert '"${SOURCE_ROOT}/src/" \\' not in content
    assert 'cp -R "${SOURCE_ROOT}/src" "${TARGET_DIR}/src"' in content


@pytest.fixture
def deploy_script_content() -> str:
    return DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")


def test_deploy_script_detects_repo_and_target_layout(deploy_script_content: str) -> None:
    assert 'DEPLOY_LAYOUT="target"' in deploy_script_content
    assert 'DEPLOY_LAYOUT="repo"' in deploy_script_content
    assert "has_target_layout_markers" in deploy_script_content
    assert "SOURCE_ROOT=" in deploy_script_content
    assert "DEPLOY_SERVER_DIR=" in deploy_script_content


def test_deploy_script_repo_layout_does_not_use_bare_repo_root_variable(
    deploy_script_content: str,
) -> None:
    assert 'SOURCE_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"' in deploy_script_content
    assert "REPO_ROOT=" not in deploy_script_content
    assert '"${REPO_ROOT}/Dockerfile"' not in deploy_script_content


def test_deploy_script_rsync_only_in_repo_layout(deploy_script_content: str) -> None:
    assert 'if [[ "${DEPLOY_LAYOUT}" == "target" ]]; then' in deploy_script_content
    assert 'DEPLOY_LAYOUT="repo"' in deploy_script_content
    assert '"${SOURCE_ROOT}/Dockerfile"' in deploy_script_content
    assert "Target layout: validating local build artifacts (skip rsync)" in deploy_script_content
    assert "Repo layout: syncing build and deployment artifacts" in deploy_script_content


def test_deploy_script_target_layout_validates_builds_and_verifies(
    deploy_script_content: str,
) -> None:
    assert 'if [[ "${DEPLOY_LAYOUT}" == "target" ]]; then' in deploy_script_content
    assert "docker compose -f silverman-worker.compose.yaml build" in deploy_script_content
    assert "docker compose -f silverman-worker.compose.yaml up -d --force-recreate" in deploy_script_content
    assert "verify-worker-deploy.sh" in deploy_script_content
    assert "BUILD_REVISION" in deploy_script_content


def test_deploy_script_never_rsyncs_from_home_root(deploy_script_content: str) -> None:
    assert '"/home/Dockerfile"' not in deploy_script_content
    assert '"/home/pyproject.toml"' not in deploy_script_content
    assert '"/home/src"' not in deploy_script_content
    target_section, repo_section = deploy_script_content.split(
        'if [[ "${DEPLOY_LAYOUT}" == "target" ]]; then', 1
    )[1].split("else", 1)
    assert "rsync -a" not in target_section
    assert "rsync -a" in repo_section


def test_deploy_script_layout_detection_subprocess(tmp_path: Path) -> None:
    """Repo vs target layout resolves SOURCE_ROOT without climbing to /home."""
    repo_root = tmp_path / "repo"
    deploy_server = repo_root / "deploy" / "server"
    deploy_server.mkdir(parents=True)
    for name in ("Dockerfile", "pyproject.toml", "README.md"):
        (repo_root / name).write_text("stub\n", encoding="utf-8")
    (repo_root / "src").mkdir()

    target_dir = tmp_path / "silverman-blog-linkedin-worker"
    target_dir.mkdir()
    for name in ("Dockerfile", "pyproject.toml", "README.md"):
        (target_dir / name).write_text("stub\n", encoding="utf-8")
    (target_dir / "src").mkdir()

    probe = r"""
has_target_layout_markers() {
  local base="$1"
  local name
  for name in Dockerfile pyproject.toml README.md src; do
    if [[ "${name}" == "src" ]]; then
      [[ -d "${base}/${name}" ]] || return 1
    else
      [[ -f "${base}/${name}" ]] || return 1
    fi
  done
  return 0
}
SCRIPT_DIR="$1"
if has_target_layout_markers "${SCRIPT_DIR}"; then
  echo "target:${SCRIPT_DIR}"
else
  echo "repo:$(cd "${SCRIPT_DIR}/../.." && pwd)"
fi
"""

    repo_result = subprocess.run(
        ["bash", "-c", probe, "_", str(deploy_server)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert repo_result == f"repo:{repo_root}"

    target_result = subprocess.run(
        ["bash", "-c", probe, "_", str(target_dir)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert target_result == f"target:{target_dir}"
    assert target_result != "repo:/home"


def test_verify_rotation_script_exists() -> None:
    assert VERIFY_ROTATION_SCRIPT_PATH.is_file()


def test_verify_rotation_script_is_executable() -> None:
    mode = VERIFY_ROTATION_SCRIPT_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, "verify-worker-api-key-rotation.sh is not executable (owner)"


def test_verify_rotation_script_references_old_key_env_var() -> None:
    content = VERIFY_ROTATION_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY" in content
    assert "SILVERMAN_BLOG_LINKEDIN_API_KEY" in content


def test_verify_rotation_script_has_no_obvious_secret_literals() -> None:
    content = VERIFY_ROTATION_SCRIPT_PATH.read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(content), (
            f"verify-worker-api-key-rotation.sh may contain a real secret: {pattern}"
        )
    assert "local-test-key" not in content
    assert "CHANGE_ME" not in content


def test_deploy_script_syncs_verify_rotation_script() -> None:
    content = DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "verify-worker-api-key-rotation.sh" in content
    assert "verify-worker-deploy.sh" in content


def test_deploy_script_syncs_linkedin_publication_smoke_scripts() -> None:
    content = DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    for script in (
        "run-linkedin-publication-smoke.sh",
        "collect-flow-a-smoke-evidence.sh",
    ):
        assert script in content
    assert '"${TARGET_DIR}/run-linkedin-publication-smoke.sh"' in content
    assert '"${TARGET_DIR}/collect-flow-a-smoke-evidence.sh"' in content
    assert "chmod +x" in content


def test_verify_deploy_script_exists() -> None:
    assert VERIFY_DEPLOY_SCRIPT_PATH.is_file()


def test_verify_deploy_script_is_executable() -> None:
    mode = VERIFY_DEPLOY_SCRIPT_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, "verify-worker-deploy.sh is not executable (owner)"


def test_verify_deploy_script_checks_flow_a_openapi_paths() -> None:
    content = VERIFY_DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    for path in (
        "/publish-blog-post",
        "/generate-linkedin-package",
        "/schedule-linkedin-distribution",
        "/queue-linkedin-publication",
        "/publish-linkedin-due-variants",
        "/cancel-linkedin-publication",
    ):
        assert path in content
    assert "blog_publish_flow.py" in content
    assert "SILVERMAN_BLOG_LINKEDIN_API_KEY" not in content
    assert "SILVERMAN_LINKEDIN_ACCESS_TOKEN" not in content


def test_verify_deploy_script_waits_for_worker_readiness() -> None:
    content = VERIFY_DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "VERIFY_MAX_ATTEMPTS" in content
    assert "VERIFY_RETRY_INTERVAL_SECONDS" in content
    assert "sleep" in content
    assert re.search(r"attempt\s+\$\{attempt\}/\$\{VERIFY_MAX_ATTEMPTS\}", content)
    assert 'wait_for_worker_http_200 "health"' in content
    assert "waiting for worker OpenAPI" in content


def test_verify_deploy_script_checks_health_and_openapi() -> None:
    content = VERIFY_DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "/health" in content
    assert "/openapi.json" in content
    assert "wait_for_worker_http_200" in content


def test_deploy_script_invokes_verify_after_recreate(deploy_script_content: str) -> None:
    recreate_marker = (
        "docker compose -f silverman-worker.compose.yaml up -d --force-recreate --remove-orphans"
    )
    verify_marker = "Post-deploy verification"
    recreate_idx = deploy_script_content.index(recreate_marker)
    verify_idx = deploy_script_content.index(verify_marker)
    assert verify_idx > recreate_idx
    assert '"${TARGET_DIR}/verify-worker-deploy.sh"' in deploy_script_content


def test_deploy_script_checks_public_blog_repo_path(deploy_script_content: str) -> None:
    assert "check_public_blog_repo_path" in deploy_script_content
    assert "SILVERMAN_PUBLIC_BLOG_REPO_PATH" in deploy_script_content
    assert "SKIP_PUBLIC_BLOG_REPO_CHECK" in deploy_script_content
    assert "_posts" in deploy_script_content
    assert "assets/images" in deploy_script_content
    assert "blog_publish_public_repo_not_configured" in deploy_script_content
    assert "does not clone automatically" in deploy_script_content


def test_deploy_script_public_blog_check_runs_before_compose_up(
    deploy_script_content: str,
) -> None:
    check_idx = deploy_script_content.index("check_public_blog_repo_path")
    up_idx = deploy_script_content.index(
        "docker compose -f silverman-worker.compose.yaml up -d --force-recreate"
    )
    assert check_idx < up_idx


def test_verify_deploy_script_checks_public_blog_repo_mount() -> None:
    content = VERIFY_DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "SILVERMAN_GITHUB_PAGES_REPO_PATH" in content
    assert "/public-blog" in content
    assert "/public-blog/_posts" in content or '"/public-blog/${rel}"' in content
    assert "assets/images" in content
    assert "SILVERMAN_BLOG_LINKEDIN_API_KEY" not in content


def test_verify_deploy_script_does_not_pipe_docker_inspect_to_python_stdin() -> None:
    content = VERIFY_DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    assert not re.search(r"docker inspect.*\|\s*python3\s+-", content), (
        "verify-worker-deploy.sh must not pipe docker inspect JSON into python3 stdin "
        "(heredoc replaces stdin)"
    )


def test_verify_deploy_script_uses_docker_inspect_temp_file_helper() -> None:
    content = VERIFY_DEPLOY_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "docker_inspect_json_tmp" in content
    assert "docker inspect" in content
    assert re.search(r'docker inspect\s+"\$\{[^}]+\}"\s*>\s*"\$\{tmp\}"', content)
    assert "with open(sys.argv[1]" in content


def test_deployment_doc_documents_worker_api_key_rotation() -> None:
    content = DEPLOYMENT_DOC_PATH.read_text(encoding="utf-8")
    assert "## Worker API key rotation" in content
    assert "OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY" in content
    assert "verify-worker-api-key-rotation.sh" in content
    assert "verify-worker-deploy.sh" in content
    assert "Silverman Blog LinkedIn Draft Generation" in content


def test_deployment_doc_documents_repo_and_target_layout_modes() -> None:
    content = DEPLOYMENT_DOC_PATH.read_text(encoding="utf-8")
    assert "## Execution modes" in content
    assert "repo layout" in content.lower()
    assert "target layout" in content.lower()
    assert "./deploy/server/deploy-worker.sh" in content
    assert "/home/silverman/silverman-blog-linkedin-worker/deploy-worker.sh" in content


def test_deployment_doc_documents_public_blog_repo_mount() -> None:
    content = DEPLOYMENT_DOC_PATH.read_text(encoding="utf-8")
    assert "silverberdi.github.io" in content
    assert "SILVERMAN_PUBLIC_BLOG_REPO_PATH" in content
    assert "SILVERMAN_GITHUB_PAGES_REPO_PATH" in content
    assert "/public-blog" in content
    assert "_posts" in content
    assert "assets/images" in content
    assert "blog_publish_public_repo_not_configured" in content
    assert "does not clone" in content.lower()


@pytest.fixture
def import_flow_a_script_content() -> str:
    assert IMPORT_FLOW_A_SCRIPT_PATH.is_file(), (
        f"missing import script: {IMPORT_FLOW_A_SCRIPT_PATH}"
    )
    return IMPORT_FLOW_A_SCRIPT_PATH.read_text(encoding="utf-8")


def test_import_flow_a_script_exists() -> None:
    assert IMPORT_FLOW_A_SCRIPT_PATH.is_file()


def test_import_flow_a_script_is_executable() -> None:
    mode = IMPORT_FLOW_A_SCRIPT_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, "import-flow-a-n8n-workflow.sh is not executable (owner)"


def test_import_flow_a_script_finds_n8n_container_by_image_not_gateway(
    import_flow_a_script_content: str,
) -> None:
    content = import_flow_a_script_content
    assert "n8nio/n8n" in content
    assert "docker.n8n.io/n8nio/n8n" in content
    assert "n8n-gateway" in content
    assert "is_gateway_container" in content
    assert "find_n8n_container" in content
    assert "docker ps --format" in content
    assert "local-ai-stack-n8n-gateway" not in content


def test_import_flow_a_script_sets_stable_workflow_id(
    import_flow_a_script_content: str,
) -> None:
    assert 'WORKFLOW_ID="silvermanFlowAPublish01"' in import_flow_a_script_content
    assert "workflow_id" in import_flow_a_script_content


def test_import_flow_a_script_forces_active_false(import_flow_a_script_content: str) -> None:
    assert 'workflow["active"] = False' in import_flow_a_script_content
    assert "workflow inactive" in import_flow_a_script_content
    assert "remains inactive" in import_flow_a_script_content
    assert "separate US-010 operator step" in import_flow_a_script_content


def test_import_flow_a_script_updates_worker_base_url(
    import_flow_a_script_content: str,
) -> None:
    assert "WORKER_BASE_URL" in import_flow_a_script_content
    assert "worker_base_url" in import_flow_a_script_content
    assert "http://192.168.0.194:8010" in import_flow_a_script_content


def test_import_flow_a_script_injects_worker_api_key_without_printing_secret(
    import_flow_a_script_content: str,
) -> None:
    content = import_flow_a_script_content
    assert "SILVERMAN_BLOG_LINKEDIN_API_KEY" in content
    assert "worker_api_key" in content
    assert "worker_api_key: configured" in content
    assert "read_worker_api_key" in content
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(content), (
            f"import-flow-a-n8n-workflow.sh may contain a real secret: {pattern}"
        )
    assert "echo \"${WORKER_API_KEY}\"" not in content
    assert "echo ${WORKER_API_KEY}" not in content


def test_import_flow_a_script_removes_null_import_breaking_fields(
    import_flow_a_script_content: str,
) -> None:
    content = import_flow_a_script_content
    for field in ("createdAt", "updatedAt", "versionId"):
        assert field in content
    assert "workflow[field] is None" in content


def test_import_flow_a_script_verifies_imported_workflow_inactive(
    import_flow_a_script_content: str,
) -> None:
    content = import_flow_a_script_content
    assert "export:workflow" in content
    assert "import:workflow" in content
    assert "verify_exported_workflow" in content
    assert 'match.get("active") is not False' in content
    assert "EXPECTED_NODE_COUNT=31" in content
    assert "EXPECTED_SCHEDULE_CRON" in content
    assert "Single-Flight Guard" in content
    assert "separate US-010 operator step" in content or "separate" in content.lower()


def test_import_flow_a_script_does_not_activate_or_call_linkedin_api(
    import_flow_a_script_content: str,
) -> None:
    content = import_flow_a_script_content
    lowered = content.lower()
    assert 'workflow["active"] = False' in content
    assert '"active": true' not in content
    assert "n8n activate" not in lowered
    assert "linkedin api" not in lowered or "call linkedin api" in lowered
    assert "separate US-010 operator step" in content
    assert "Schedule Trigger" in content


def test_import_flow_a_script_prints_canonical_identity_summary(
    import_flow_a_script_content: str,
) -> None:
    content = import_flow_a_script_content
    assert "Canonical Flow A n8n identity" in content
    assert 'WORKFLOW_ID="silvermanFlowAPublish01"' in content
    assert "EXPECTED_NODE_COUNT=31" in content
    assert "worker_base_url:" in content
    assert "worker_api_key:   configured" in content
    assert "worker_api_key:   missing" in content
    assert "0 9 * * *" in content
    assert "publish-pending" in content
    assert "US-010" in content
    assert "Schedule Trigger is present" in content or "Schedule Trigger" in content


def test_import_flow_a_script_fail_closed_requires_workflow_id(
    import_flow_a_script_content: str,
) -> None:
    content = import_flow_a_script_content
    assert 'item.get("id") == workflow_id or item.get("name") == workflow_name' not in content
    assert "match_by_id" in content
    assert "found by name" in content
    assert "expected id" in content
    assert "Re-run deploy/server/import-flow-a-n8n-workflow.sh" in content


def test_collect_flow_a_evidence_script_fail_closed_requires_workflow_id(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert 'item.get("id") == workflow_id or item.get("name") == workflow_name' not in content
    assert "match_by_id" in content
    assert "found by name" in content
    assert "Re-run deploy/server/import-flow-a-n8n-workflow.sh" in content


def test_deployment_doc_documents_flow_a_n8n_import() -> None:
    content = DEPLOYMENT_DOC_PATH.read_text(encoding="utf-8")
    assert "import-flow-a-n8n-workflow.sh" in content
    assert "silvermanFlowAPublish01" in content
    assert "Canonical Flow A workflow identity" in content
    assert "09:00 UTC" in content
    assert "n8n-gateway" in content or "nginx gateway" in content.lower()
    assert "active: false" in content.lower() or '"active": false' in content.lower()
    assert "expect-server-active" in content or "--expect-server-active" in content
    assert "31" in content
    assert "US-011" in content or "BL-005" in content


@pytest.fixture
def collect_flow_a_evidence_script_content() -> str:
    assert COLLECT_FLOW_A_EVIDENCE_SCRIPT_PATH.is_file(), (
        f"missing evidence script: {COLLECT_FLOW_A_EVIDENCE_SCRIPT_PATH}"
    )
    return COLLECT_FLOW_A_EVIDENCE_SCRIPT_PATH.read_text(encoding="utf-8")


def test_collect_flow_a_evidence_script_exists() -> None:
    assert COLLECT_FLOW_A_EVIDENCE_SCRIPT_PATH.is_file()


def test_collect_flow_a_evidence_script_is_executable() -> None:
    mode = COLLECT_FLOW_A_EVIDENCE_SCRIPT_PATH.stat().st_mode
    assert mode & stat.S_IXUSR, "collect-flow-a-smoke-evidence.sh is not executable (owner)"


def test_collect_flow_a_evidence_script_is_read_only_and_safe(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    lowered = content.lower()
    assert "read-only" in lowered
    assert "deploy-worker.sh" not in content
    assert "docker compose up" not in lowered
    assert "docker compose build" not in lowered
    assert "force-recreate" not in lowered
    assert "import:workflow" not in content
    assert "activate" not in lowered or "expect-server-active" in lowered or "no n8n activation" in lowered
    assert "schedule trigger" in lowered or "expected_schedule_cron" in lowered
    assert "linkedin api" in lowered
    assert "no linkedin api" in lowered


def test_collect_flow_a_evidence_script_resolves_base_path_from_container_env_or_mounts(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "SILVERMAN_BLOG_LINKEDIN_BASE_PATH" in content
    assert "resolve_base_path_from_container_env" in content
    assert "resolve_base_path_from_container_mounts" in content
    assert "docker inspect" in content
    assert "Mounts" in content
    assert "BASE_PATH" in content
    assert "known host candidate path" in content


def test_collect_flow_a_evidence_script_checks_worker_health_and_openapi_paths(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "/health" in content
    assert "/openapi.json" in content
    for path in (
        "/publish-blog-post",
        "/generate-linkedin-package",
        "/schedule-linkedin-distribution",
    ):
        assert path in content


def test_collect_flow_a_evidence_script_checks_n8n_workflow_inactive_and_node_count(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "silvermanFlowAPublish01" in content
    assert "EXPECTED_NODE_COUNT=31" in content
    assert "--expect-server-active" in content
    assert "EXPECT_SERVER_ACTIVE" in content
    assert "EXPECTED_SCHEDULE_CRON" in content
    assert "Single-Flight Guard" in content
    assert "export:workflow" in content
    assert "find_n8n_container" in content
    assert "pre-activation" in content
    assert "post-activation" in content


def test_collect_flow_a_evidence_script_supports_slug_fragment(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "POST_SLUG_FRAGMENT" in content
    assert "why-i-did-not-start-with-the-database" in content
    assert "_posts" in content
    assert "assets/images" in content


def test_collect_flow_a_evidence_script_checks_public_blog_artifacts_via_host_mount(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "check_public_blog_artifacts" in content
    assert "Public blog artifacts" in content
    assert "PUBLIC_BLOG_HOST_MOUNT" in content
    assert '"${PUBLIC_BLOG_HOST_MOUNT}/_posts"' in content
    assert '"${PUBLIC_BLOG_HOST_MOUNT}/assets/images"' in content
    assert "find_matching_files_in_container" in content


def test_collect_flow_a_evidence_script_does_not_search_editorial_base_for_published_blog(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert '"${RESOLVED_BASE_PATH}/_posts"' not in content
    assert '"${RESOLVED_BASE_PATH}/assets/images"' not in content


def test_collect_flow_a_evidence_script_collects_metadata_and_generated_artifacts(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "metadata/runs" in content
    assert "metadata/campaigns" in content
    assert "linkedin-posts/generated" in content


def test_collect_flow_a_evidence_script_does_not_print_secrets(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(content), (
            f"collect-flow-a-smoke-evidence.sh may contain a real secret: {pattern}"
        )
    assert "SILVERMAN_BLOG_LINKEDIN_API_KEY" not in content
    assert "DEEPSEEK_API_KEY" not in content
    assert "worker_api_key" not in content
    assert "no secrets" in content.lower()


def test_collect_flow_a_evidence_script_prints_canonical_identity_section(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "canonical Flow A n8n identity" in content
    assert 'N8N_WORKFLOW_ID="${N8N_WORKFLOW_ID:-silvermanFlowAPublish01}"' in content
    assert "expected nodes:" in content
    assert "required active:" in content
    assert "pre-activation" in content
    assert "post-activation" in content
    assert "publish-pending" in content


def test_collect_flow_a_evidence_script_reports_overall_status_values(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert 'OVERALL: PASS' in content
    assert 'OVERALL: PENDING' in content
    assert 'OVERALL: FAIL' in content


def test_collect_flow_a_evidence_script_pass_requires_distribution_evidence(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "FLOW_A_COMPLETE" in content
    assert "distribution_scheduled" in content
    assert "HAS_LINKEDIN_DISTRIBUTION" in content
    assert "read_campaign_evidence" in content
    assert 'if [[ "${FLOW_A_COMPLETE}" -eq 1 ]]; then' in content
    assert "OVERALL: PASS (worker OK, public blog repo ready," in content
    assert "Flow A reached distribution_scheduled" in content


def test_collect_flow_a_evidence_script_campaign_error_is_fail(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert 'if [[ "${CAMPAIGN_STATE}" == "error" ]]; then' in content
    assert "campaign state is error" in content


def test_collect_flow_a_evidence_script_public_blog_artifacts_informational_only(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "public blog files do not affect OVERALL PASS" in content
    assert "check_public_blog_artifacts" in content
    assert "FLOW_A_COMPLETE" in content


def test_collect_flow_a_evidence_script_plain_campaign_metadata_not_pass(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "if [[ \"${FLOW_A_COMPLETE}\" -eq 1 ]]; then" in content
    assert "HAS_SMOKE_ARTIFACTS=1" in content
    assert 'pass "latest campaign metadata:' in content
    assert "campaign state:" in content
    assert "has linkedin package:" in content
    assert "not counting toward PASS" in content


def test_collect_flow_a_evidence_script_checks_public_blog_repo_readiness(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "check_public_blog_repo" in content
    assert "Public blog repo readiness" in content
    assert "SILVERMAN_GITHUB_PAGES_REPO_PATH" in content
    assert "/public-blog" in content
    assert "_posts" in content
    assert "assets/images" in content
    assert "PUBLIC_BLOG_REPO_OK" in content
    assert "blog_publish_public_repo_not_configured" in content
    assert "public_blog_repo_ok" in content


def test_collect_flow_a_evidence_script_does_not_pipe_docker_inspect_to_python_stdin(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert not re.search(r"docker inspect.*\|\s*python3\s+-", content), (
        "collect-flow-a-smoke-evidence.sh must not pipe docker inspect JSON into "
        "python3 stdin (heredoc replaces stdin)"
    )


def test_collect_flow_a_evidence_script_uses_docker_inspect_temp_file_helper(
    collect_flow_a_evidence_script_content: str,
) -> None:
    content = collect_flow_a_evidence_script_content
    assert "docker_inspect_json_tmp" in content
    assert "docker inspect" in content
    assert re.search(r'docker inspect\s+"\$\{[^}]+\}"\s*>\s*"\$\{tmp\}"', content)
    assert "with open(sys.argv[1]" in content


@pytest.fixture
def flow_a_worker_smoke_script_content() -> str:
    assert FLOW_A_WORKER_SMOKE_SCRIPT_PATH.is_file(), (
        f"missing script: {FLOW_A_WORKER_SMOKE_SCRIPT_PATH}"
    )
    return FLOW_A_WORKER_SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")


def test_flow_a_worker_smoke_script_exists_and_is_executable() -> None:
    assert FLOW_A_WORKER_SMOKE_SCRIPT_PATH.is_file()
    mode = FLOW_A_WORKER_SMOKE_SCRIPT_PATH.stat().st_mode
    assert mode & stat.S_IXUSR


def test_flow_a_worker_smoke_script_calls_endpoints_in_order(
    flow_a_worker_smoke_script_content: str,
) -> None:
    content = flow_a_worker_smoke_script_content
    health_idx = content.index("Step 1: GET /health")
    publish_idx = content.index("Step 2: POST /publish-blog-post")
    package_idx = content.index("Step 3: POST /generate-linkedin-package")
    schedule_idx = content.index("Step 4: POST /schedule-linkedin-distribution")
    assert health_idx < publish_idx < package_idx < schedule_idx


def test_flow_a_worker_smoke_script_reads_api_key_without_printing(
    flow_a_worker_smoke_script_content: str,
) -> None:
    content = flow_a_worker_smoke_script_content
    assert "load_env_var SILVERMAN_BLOG_LINKEDIN_API_KEY" in content
    assert 'echo "${API_KEY}"' not in content
    assert "printf '%s' \"${API_KEY}\"" not in content
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(content)


def test_flow_a_worker_smoke_script_safety_constraints(
    flow_a_worker_smoke_script_content: str,
) -> None:
    content = flow_a_worker_smoke_script_content
    lowered = content.lower()
    assert "no n8n activation" in lowered or '"active": true' not in content
    assert "no linkedin api" in lowered or "linkedin api" in lowered
    assert "git push" not in lowered or "no git push" in lowered
    assert "rm -rf" not in content
    assert "destructive cleanup" in lowered


def test_flow_a_worker_smoke_script_supports_flags(
    flow_a_worker_smoke_script_content: str,
) -> None:
    content = flow_a_worker_smoke_script_content
    assert "--dry-run" in content
    assert "--worker-base-url" in content
    assert "--relative-path" in content
    assert "--site-url" in content


def test_flow_a_worker_smoke_script_checks_campaign_state_and_artifacts(
    flow_a_worker_smoke_script_content: str,
) -> None:
    content = flow_a_worker_smoke_script_content
    assert "print_campaign_snapshot" in content
    assert "distribution_scheduled" in content
    assert "verify_public_artifacts" in content
    assert "verify_generated_artifacts" in content
    assert "verify_campaign_distribution_complete" in content
    assert "linkedin_distribution metadata is missing" in content
    assert "published_post_relative_path" in content
    assert "linkedin_package" in content
    assert "deepseek_config_invalid" in content
    assert "Campaign metadata after publish failure" in content
    assert "OVERALL: PASS" in content
    assert "OVERALL: FAIL" in content
    assert "final campaign state must be distribution_scheduled with linkedin_distribution" in content


def test_linkedin_publication_smoke_script_exists_and_is_executable() -> None:
    assert LINKEDIN_PUBLICATION_SMOKE_SCRIPT_PATH.is_file()
    mode = LINKEDIN_PUBLICATION_SMOKE_SCRIPT_PATH.stat().st_mode
    assert mode & stat.S_IXUSR


def test_linkedin_publication_smoke_script_defaults_to_dry_run(
) -> None:
    content = LINKEDIN_PUBLICATION_SMOKE_SCRIPT_PATH.read_text(encoding="utf-8")
    assert "/queue-linkedin-publication" in content
    assert "/publish-linkedin-due-variants" in content
    assert "/cancel-linkedin-publication" in content
    assert "dry-run" in content.lower() or "dry_run" in content
    assert "SILVERMAN_LINKEDIN_ACCESS_TOKEN" not in content
    for pattern in SECRET_PATTERNS:
        assert not pattern.search(content), (
            f"run-linkedin-publication-smoke.sh may contain a real secret: {pattern}"
        )
