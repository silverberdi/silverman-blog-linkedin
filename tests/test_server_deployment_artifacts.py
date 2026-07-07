"""Lightweight validation for Ubuntu server deployment artifacts."""

from __future__ import annotations

import re
import stat
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY_SERVER = REPO_ROOT / "deploy" / "server"

COMPOSE_PATH = DEPLOY_SERVER / "silverman-worker.compose.yaml"
ENV_EXAMPLE_PATH = DEPLOY_SERVER / "silverman-worker.env.example"
DEPLOY_SCRIPT_PATH = DEPLOY_SERVER / "deploy-worker.sh"
SMOKE_SCRIPT_PATH = DEPLOY_SERVER / "smoke-worker.sh"
VERIFY_DEPLOY_SCRIPT_PATH = DEPLOY_SERVER / "verify-worker-deploy.sh"
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
    assert '"${REPO_ROOT}/src" \\' in content
    assert '"${REPO_ROOT}/src/" \\' not in content
    assert 'cp -R "${REPO_ROOT}/src" "${TARGET_DIR}/src"' in content


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
    ):
        assert path in content
    assert "blog_publish_flow.py" in content
    assert "SILVERMAN_BLOG_LINKEDIN_API_KEY" not in content


def test_deployment_doc_documents_worker_api_key_rotation() -> None:
    content = DEPLOYMENT_DOC_PATH.read_text(encoding="utf-8")
    assert "## Worker API key rotation" in content
    assert "OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY" in content
    assert "verify-worker-api-key-rotation.sh" in content
    assert "verify-worker-deploy.sh" in content
    assert "Silverman Blog LinkedIn Draft Generation" in content
