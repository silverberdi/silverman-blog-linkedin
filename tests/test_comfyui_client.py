"""Tests for ComfyUI client helpers and fake client."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from silverman_blog_linkedin.comfyui_client import (
    BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
    BLOG_IMAGE_GENERATION_NOT_CONFIGURED,
    ComfyUIHttpClient,
    FakeComfyUIClient,
    build_comfyui_api_url,
    build_comfyui_prompt_payload,
    build_comfyui_request_headers,
    inject_workflow_parameters,
    load_workflow_template,
    workflow_has_dimension_bindings,
)
from silverman_blog_linkedin.comfyui_config import (
    ComfyUISettings,
    DEFAULT_WORKFLOW_PATH,
    LOCAL_WORKFLOW_PATH,
    load_comfyui_settings,
)

SECRET_API_KEY = "comfy-secret-key-do-not-leak"


def _settings(
    *,
    base_url: str = "http://127.0.0.1:8188",
    api_prefix: str = "",
    api_key: str | None = None,
    auth_header_name: str = "Authorization",
    extra_data_api_key_field: str | None = None,
) -> ComfyUISettings:
    return ComfyUISettings(
        enabled=True,
        base_url=base_url,
        api_prefix=api_prefix,
        api_key=api_key,
        auth_header_name=auth_header_name,
        extra_data_api_key_field=extra_data_api_key_field,
        workflow_path=DEFAULT_WORKFLOW_PATH,
        timeout_seconds=30,
        image_width=1200,
        image_height=900,
        dry_run=False,
    )


@pytest.fixture
def local_workflow_template() -> tuple[dict, dict]:
    return load_workflow_template(LOCAL_WORKFLOW_PATH)


@pytest.fixture
def openai_workflow_template() -> tuple[dict, dict]:
    return load_workflow_template(DEFAULT_WORKFLOW_PATH)


def test_load_workflow_template_has_bindings(openai_workflow_template):
    workflow, bindings = openai_workflow_template
    assert "10" in workflow
    assert bindings["positive_prompt"]["node"] == "10"
    assert bindings["positive_prompt"]["input"] == "prompt"
    assert bindings["output"]["node"] == "14"


def test_inject_workflow_parameters_sets_prompt_and_dimensions(local_workflow_template):
    workflow, bindings = local_workflow_template
    graph = inject_workflow_parameters(
        workflow,
        bindings,
        positive_prompt="topic prompt",
        negative_prompt="no text",
        width=1200,
        height=900,
        seed=42,
    )

    assert graph["6"]["inputs"]["text"] == "topic prompt"
    assert graph["7"]["inputs"]["text"] == "no text"
    assert graph["5"]["inputs"]["width"] == 1200
    assert graph["5"]["inputs"]["height"] == 900
    assert graph["3"]["inputs"]["seed"] == 42


def test_inject_openai_workflow_parameters_positive_prompt_and_seed_only(
    openai_workflow_template,
):
    workflow, bindings = openai_workflow_template
    graph = inject_workflow_parameters(
        workflow,
        bindings,
        positive_prompt="editorial architecture visual",
        negative_prompt="no text",
        width=1200,
        height=900,
        seed=99,
    )

    assert graph["10"]["inputs"]["prompt"] == "editorial architecture visual"
    assert graph["10"]["inputs"]["seed"] == 99
    assert graph["10"]["inputs"]["size"] == "1536x1024"
    assert graph["10"]["inputs"]["quality"] == "high"
    assert graph["10"]["inputs"]["background"] == "opaque"
    assert graph["10"]["inputs"]["n"] == 1
    assert graph["10"]["inputs"]["model"] == "gpt-image-1.5"


def test_inject_openai_workflow_missing_negative_prompt_binding_does_not_fail(
    openai_workflow_template,
):
    workflow, bindings = openai_workflow_template
    inject_workflow_parameters(
        workflow,
        bindings,
        positive_prompt="topic",
        negative_prompt="ignored negative",
        width=1200,
        height=900,
        seed=1,
    )


def test_inject_openai_workflow_missing_width_height_bindings_does_not_fail(
    openai_workflow_template,
):
    workflow, bindings = openai_workflow_template
    assert not workflow_has_dimension_bindings(bindings)
    graph = inject_workflow_parameters(
        workflow,
        bindings,
        positive_prompt="topic",
        negative_prompt="no text",
        width=9999,
        height=8888,
        seed=1,
    )
    assert graph["10"]["inputs"]["size"] == "1536x1024"


def test_openai_workflow_preserves_preset_size(openai_workflow_template):
    workflow, bindings = openai_workflow_template
    graph = inject_workflow_parameters(
        workflow,
        bindings,
        positive_prompt="topic",
        negative_prompt="no text",
        width=1200,
        height=900,
        seed=1,
    )
    assert graph["10"]["inputs"]["size"] == "1536x1024"


def test_local_workflow_has_dimension_bindings(local_workflow_template):
    _workflow, bindings = local_workflow_template
    assert workflow_has_dimension_bindings(bindings)


def test_fake_client_returns_png_bytes():
    client = FakeComfyUIClient()
    result = client.generate_image(
        positive_prompt="p",
        negative_prompt="n",
        width=1200,
        height=900,
        seed=1,
    )

    assert result.error_code is None
    assert result.png_bytes is not None
    assert result.png_bytes.startswith(b"\x89PNG")
    assert len(client.calls) == 1


def test_fake_client_returns_configured_error():
    client = FakeComfyUIClient(error_code=BLOG_IMAGE_GENERATION_COMFYUI_FAILED)
    result = client.generate_image(
        positive_prompt="p",
        negative_prompt="n",
        width=1200,
        height=900,
        seed=1,
    )

    assert result.png_bytes is None
    assert result.error_code == BLOG_IMAGE_GENERATION_COMFYUI_FAILED


def test_load_workflow_template_rejects_invalid_file(tmp_path: Path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")

    with pytest.raises(ValueError):
        load_workflow_template(bad)


def test_inject_workflow_parameters_requires_positive_prompt_binding(
    local_workflow_template,
):
    workflow, _bindings = local_workflow_template
    with pytest.raises(ValueError, match="positive_prompt"):
        inject_workflow_parameters(
            workflow,
            {},
            positive_prompt="p",
            negative_prompt="n",
            width=1,
            height=1,
            seed=1,
        )


def test_http_client_not_configured_without_base_url():
    settings = _settings(base_url=None)  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        ComfyUIHttpClient(settings)


def test_build_comfyui_api_url_without_prefix():
    assert (
        build_comfyui_api_url("http://127.0.0.1:8188", "", "/prompt")
        == "http://127.0.0.1:8188/prompt"
    )


def test_build_comfyui_api_url_with_prefix():
    assert (
        build_comfyui_api_url("https://cloud.comfy.org", "/api", "/prompt")
        == "https://cloud.comfy.org/api/prompt"
    )
    assert (
        build_comfyui_api_url("https://cloud.comfy.org", "api", "/history/abc")
        == "https://cloud.comfy.org/api/history/abc"
    )


def test_build_comfyui_request_headers_includes_bearer_token():
    headers = build_comfyui_request_headers(_settings(api_key=SECRET_API_KEY))
    assert headers == {"Authorization": f"Bearer {SECRET_API_KEY}"}


def test_build_comfyui_request_headers_empty_without_api_key():
    assert build_comfyui_request_headers(_settings()) == {}


def test_build_comfyui_request_headers_custom_header_name_uses_raw_key():
    headers = build_comfyui_request_headers(
        _settings(api_key=SECRET_API_KEY, auth_header_name="X-API-Key")
    )
    assert headers == {"X-API-Key": SECRET_API_KEY}


def test_build_comfyui_prompt_payload_includes_comfy_cloud_extra_data_field():
    payload = build_comfyui_prompt_payload(
        {"1": {}},
        client_id="client-1",
        settings=_settings(
            api_key=SECRET_API_KEY,
            extra_data_api_key_field="api_key_comfy_org",
        ),
    )
    assert payload["extra_data"] == {"api_key_comfy_org": SECRET_API_KEY}


def test_build_comfyui_prompt_payload_includes_extra_data_when_configured():
    payload = build_comfyui_prompt_payload(
        {"1": {}},
        client_id="client-1",
        settings=_settings(
            api_key=SECRET_API_KEY,
            extra_data_api_key_field="comfy_api_key",
        ),
    )
    assert payload["extra_data"] == {"comfy_api_key": SECRET_API_KEY}


def test_build_comfyui_prompt_payload_omits_extra_data_without_field_name():
    payload = build_comfyui_prompt_payload(
        {"1": {}},
        client_id="client-1",
        settings=_settings(api_key=SECRET_API_KEY),
    )
    assert "extra_data" not in payload


def _mock_http_response(
    method: str,
    url: str,
    *,
    status_code: int = 200,
    json_body: dict | None = None,
    content: bytes = b"",
) -> httpx.Response:
    request = httpx.Request(method, url)
    if json_body is not None:
        return httpx.Response(
            status_code,
            content=json.dumps(json_body).encode("utf-8"),
            request=request,
        )
    return httpx.Response(status_code, content=content, request=request)


def test_http_client_applies_api_prefix_auth_and_extra_data():
    prompt_id = "prompt-123"
    png_bytes = b"\x89PNG\r\n\x1a\ncloud-output"
    mock_client = MagicMock(spec=httpx.Client)

    def _route(method: str, url: str, **kwargs):
        if method == "POST" and url.endswith("/api/prompt"):
            return _mock_http_response(
                method,
                url,
                json_body={"prompt_id": prompt_id},
            )
        if method == "GET" and url.endswith(f"/api/history/{prompt_id}"):
            return _mock_http_response(
                method,
                url,
                json_body={
                    prompt_id: {
                        "outputs": {
                            "14": {
                                "images": [
                                    {
                                        "filename": "out.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                },
            )
        if method == "GET" and url.endswith("/api/view"):
            return _mock_http_response(method, url, content=png_bytes)
        raise AssertionError(f"unexpected request: {method} {url}")

    mock_client.post.side_effect = lambda url, **kwargs: _route("POST", url, **kwargs)
    mock_client.get.side_effect = lambda url, **kwargs: _route("GET", url, **kwargs)

    settings = _settings(
        base_url="https://cloud.comfy.org",
        api_prefix="/api",
        api_key=SECRET_API_KEY,
        auth_header_name="X-API-Key",
        extra_data_api_key_field="api_key_comfy_org",
    )
    client = ComfyUIHttpClient(settings, client=mock_client)
    result = client.generate_image(
        positive_prompt="topic",
        negative_prompt="no text",
        width=1200,
        height=900,
        seed=7,
    )

    assert result.error_code is None
    assert result.png_bytes == png_bytes

    post_call = mock_client.post.call_args
    assert post_call.args[0] == "https://cloud.comfy.org/api/prompt"
    assert post_call.kwargs["headers"] == {
        "X-API-Key": SECRET_API_KEY,
    }
    assert post_call.kwargs["json"]["extra_data"] == {
        "api_key_comfy_org": SECRET_API_KEY,
    }

    history_call = mock_client.get.call_args_list[0]
    assert history_call.args[0] == "https://cloud.comfy.org/api/history/prompt-123"
    assert history_call.kwargs["headers"] == {
        "X-API-Key": SECRET_API_KEY,
    }

    view_call = mock_client.get.call_args_list[1]
    assert view_call.args[0] == "https://cloud.comfy.org/api/view"
    assert view_call.kwargs["headers"] == {
        "X-API-Key": SECRET_API_KEY,
    }

    serialized = json.dumps(
        {
            "error_code": result.error_code,
            "png_size": len(result.png_bytes or b""),
        }
    )
    assert SECRET_API_KEY not in serialized


def test_http_client_local_behavior_without_prefix_or_key():
    prompt_id = "local-prompt"
    png_bytes = b"\x89PNG\r\n\x1a\nlocal-output"
    mock_client = MagicMock(spec=httpx.Client)

    def _route(method: str, url: str, **kwargs):
        if method == "POST" and url.endswith("/prompt"):
            assert kwargs.get("headers") == {}
            assert "extra_data" not in kwargs.get("json", {})
            return _mock_http_response(
                method,
                url,
                json_body={"prompt_id": prompt_id},
            )
        if method == "GET" and url.endswith(f"/history/{prompt_id}"):
            return _mock_http_response(
                method,
                url,
                json_body={
                    prompt_id: {
                        "outputs": {
                            "14": {
                                "images": [
                                    {
                                        "filename": "out.png",
                                        "subfolder": "",
                                        "type": "output",
                                    }
                                ]
                            }
                        }
                    }
                },
            )
        if method == "GET" and url.endswith("/view"):
            return _mock_http_response(method, url, content=png_bytes)
        raise AssertionError(f"unexpected request: {method} {url}")

    mock_client.post.side_effect = lambda url, **kwargs: _route("POST", url, **kwargs)
    mock_client.get.side_effect = lambda url, **kwargs: _route("GET", url, **kwargs)

    client = ComfyUIHttpClient(_settings(), client=mock_client)
    result = client.generate_image(
        positive_prompt="topic",
        negative_prompt="no text",
        width=1200,
        height=900,
        seed=1,
    )

    assert result.error_code is None
    assert result.png_bytes == png_bytes
    assert mock_client.post.call_args.args[0] == "http://127.0.0.1:8188/prompt"


def test_load_comfyui_settings_reads_cloud_compat_fields():
    result = load_comfyui_settings(
        {
            "SILVERMAN_COMFYUI_IMAGE_ENABLED": "true",
            "SILVERMAN_COMFYUI_BASE_URL": "https://cloud.comfy.org",
            "SILVERMAN_COMFYUI_API_PREFIX": "/api",
            "SILVERMAN_COMFYUI_API_KEY": SECRET_API_KEY,
            "SILVERMAN_COMFYUI_AUTH_HEADER_NAME": "X-API-Key",
            "SILVERMAN_COMFYUI_EXTRA_DATA_API_KEY_FIELD": "api_key_comfy_org",
        }
    )

    settings = result.settings
    assert settings.api_prefix == "/api"
    assert settings.api_key == SECRET_API_KEY
    assert settings.auth_header_name == "X-API-Key"
    assert settings.extra_data_api_key_field == "api_key_comfy_org"


def test_load_comfyui_settings_defaults_cloud_compat_fields_empty():
    result = load_comfyui_settings({})
    settings = result.settings

    assert settings.api_prefix == ""
    assert settings.api_key is None
    assert settings.auth_header_name == "Authorization"
    assert settings.extra_data_api_key_field is None


def test_workflow_json_file_is_valid():
    raw = json.loads(DEFAULT_WORKFLOW_PATH.read_text(encoding="utf-8"))
    assert "workflow" in raw
    assert "bindings" in raw
