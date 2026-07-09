"""ComfyUI HTTP client for blog image generation."""

from __future__ import annotations

import copy
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

from silverman_blog_linkedin.comfyui_config import ComfyUISettings

BLOG_IMAGE_GENERATION_COMFYUI_FAILED = "blog_image_generation_comfyui_failed"
BLOG_IMAGE_GENERATION_TIMEOUT = "blog_image_generation_timeout"
BLOG_IMAGE_GENERATION_NOT_CONFIGURED = "blog_image_generation_not_configured"

POLL_INTERVAL_SECONDS = 0.5


def build_comfyui_api_url(base_url: str, api_prefix: str, endpoint: str) -> str:
    """Build a ComfyUI API URL from base URL, optional prefix, and endpoint path."""
    root = base_url.rstrip("/")
    prefix = api_prefix.strip()
    if prefix:
        if not prefix.startswith("/"):
            prefix = f"/{prefix}"
        prefix = prefix.rstrip("/")
    path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
    return f"{root}{prefix}{path}"


def build_comfyui_request_headers(settings: ComfyUISettings) -> dict[str, str]:
    """Return HTTP headers for ComfyUI requests when an API key is configured."""
    if not settings.api_key:
        return {}
    if settings.auth_header_name.lower() == "authorization":
        value = f"Bearer {settings.api_key}"
    else:
        value = settings.api_key
    return {settings.auth_header_name: value}


def build_comfyui_prompt_payload(
    prompt_graph: dict[str, Any],
    *,
    client_id: str,
    settings: ComfyUISettings,
) -> dict[str, Any]:
    """Build the ComfyUI /prompt request body, optionally including extra_data."""
    payload: dict[str, Any] = {"prompt": prompt_graph, "client_id": client_id}
    if settings.api_key and settings.extra_data_api_key_field:
        payload["extra_data"] = {
            settings.extra_data_api_key_field: settings.api_key,
        }
    return payload


@dataclass(frozen=True)
class ComfyUIImageResult:
    png_bytes: bytes | None
    error_code: str | None


class ComfyUIClientProtocol(Protocol):
    def generate_image(
        self,
        *,
        positive_prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int,
    ) -> ComfyUIImageResult:
        """Generate a PNG image from prompts and dimensions."""


def load_workflow_template(workflow_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load workflow JSON and bindings from disk."""
    try:
        raw = json.loads(workflow_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid ComfyUI workflow at {workflow_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise ValueError("ComfyUI workflow must be a JSON object")

    workflow = raw.get("workflow")
    bindings = raw.get("bindings")
    if not isinstance(workflow, dict) or not isinstance(bindings, dict):
        raise ValueError("ComfyUI workflow must include workflow and bindings objects")

    return workflow, bindings


def workflow_has_dimension_bindings(bindings: dict[str, Any]) -> bool:
    """Return True when the workflow template exposes width and height bindings."""
    width = bindings.get("width")
    height = bindings.get("height")
    return isinstance(width, dict) and isinstance(height, dict)


def inject_workflow_parameters(
    workflow: dict[str, Any],
    bindings: dict[str, Any],
    *,
    positive_prompt: str,
    negative_prompt: str,
    width: int,
    height: int,
    seed: int,
) -> dict[str, Any]:
    """Return a copy of the workflow graph with bound prompt and dimension inputs set."""
    graph = copy.deepcopy(workflow)

    def _set_binding(name: str, value: Any, *, required: bool) -> None:
        binding = bindings.get(name)
        if not isinstance(binding, dict):
            if required:
                raise ValueError(f"missing binding for {name!r}")
            return
        node_id = str(binding["node"])
        input_name = str(binding["input"])
        node = graph.get(node_id)
        if not isinstance(node, dict):
            raise ValueError(f"workflow node {node_id!r} not found for {name!r}")
        inputs = node.setdefault("inputs", {})
        if not isinstance(inputs, dict):
            raise ValueError(f"workflow node {node_id!r} inputs must be a mapping")
        inputs[input_name] = value

    _set_binding("positive_prompt", positive_prompt, required=True)
    _set_binding("negative_prompt", negative_prompt, required=False)
    _set_binding("width", width, required=False)
    _set_binding("height", height, required=False)
    _set_binding("seed", seed, required=False)
    return graph


def _extract_output_image(
    history_entry: dict[str, Any],
    bindings: dict[str, Any],
) -> dict[str, str] | None:
    outputs = history_entry.get("outputs")
    if not isinstance(outputs, dict):
        return None

    output_binding = bindings.get("output")
    if isinstance(output_binding, dict):
        preferred_node = str(output_binding.get("node", ""))
        node_outputs = outputs.get(preferred_node)
        if isinstance(node_outputs, dict):
            images = node_outputs.get("images")
            if isinstance(images, list) and images:
                first = images[0]
                if isinstance(first, dict) and first.get("filename"):
                    return {
                        "filename": str(first["filename"]),
                        "subfolder": str(first.get("subfolder") or ""),
                        "type": str(first.get("type") or "output"),
                    }

    for node_outputs in outputs.values():
        if not isinstance(node_outputs, dict):
            continue
        images = node_outputs.get("images")
        if not isinstance(images, list) or not images:
            continue
        first = images[0]
        if isinstance(first, dict) and first.get("filename"):
            return {
                "filename": str(first["filename"]),
                "subfolder": str(first.get("subfolder") or ""),
                "type": str(first.get("type") or "output"),
            }
    return None


class ComfyUIHttpClient:
    """Production ComfyUI client using HTTP /prompt, /history, and /view."""

    def __init__(
        self,
        settings: ComfyUISettings,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        if not settings.base_url:
            raise ValueError("ComfyUI base URL is required")
        self._settings = settings
        self._workflow_path = settings.workflow_path
        self._request_headers = build_comfyui_request_headers(settings)
        self._owns_client = client is None
        self._client = client or httpx.Client(timeout=settings.timeout_seconds)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def generate_image(
        self,
        *,
        positive_prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int,
    ) -> ComfyUIImageResult:
        if not self._settings.base_url:
            return ComfyUIImageResult(
                png_bytes=None,
                error_code=BLOG_IMAGE_GENERATION_NOT_CONFIGURED,
            )

        try:
            workflow, bindings = load_workflow_template(self._workflow_path)
            prompt_graph = inject_workflow_parameters(
                workflow,
                bindings,
                positive_prompt=positive_prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
                seed=seed,
            )
        except ValueError:
            return ComfyUIImageResult(
                png_bytes=None,
                error_code=BLOG_IMAGE_GENERATION_NOT_CONFIGURED,
            )

        base_url = self._settings.base_url.rstrip("/")
        api_prefix = self._settings.api_prefix
        client_id = str(uuid.uuid4())

        try:
            response = self._client.post(
                build_comfyui_api_url(base_url, api_prefix, "/prompt"),
                json=build_comfyui_prompt_payload(
                    prompt_graph,
                    client_id=client_id,
                    settings=self._settings,
                ),
                headers=self._request_headers,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, json.JSONDecodeError):
            return ComfyUIImageResult(
                png_bytes=None,
                error_code=BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
            )

        prompt_id = payload.get("prompt_id") if isinstance(payload, dict) else None
        if not isinstance(prompt_id, str) or not prompt_id:
            return ComfyUIImageResult(
                png_bytes=None,
                error_code=BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
            )

        deadline = time.monotonic() + self._settings.timeout_seconds
        history_entry: dict[str, Any] | None = None

        while time.monotonic() < deadline:
            try:
                history_response = self._client.get(
                    build_comfyui_api_url(
                        base_url,
                        api_prefix,
                        f"/history/{prompt_id}",
                    ),
                    headers=self._request_headers,
                )
                history_response.raise_for_status()
                history_payload = history_response.json()
            except (httpx.HTTPError, json.JSONDecodeError):
                time.sleep(POLL_INTERVAL_SECONDS)
                continue

            if isinstance(history_payload, dict) and prompt_id in history_payload:
                entry = history_payload[prompt_id]
                if isinstance(entry, dict):
                    history_entry = entry
                    break

            time.sleep(POLL_INTERVAL_SECONDS)

        if history_entry is None:
            return ComfyUIImageResult(
                png_bytes=None,
                error_code=BLOG_IMAGE_GENERATION_TIMEOUT,
            )

        image_ref = _extract_output_image(history_entry, bindings)
        if image_ref is None:
            return ComfyUIImageResult(
                png_bytes=None,
                error_code=BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
            )

        params = {
            "filename": image_ref["filename"],
            "type": image_ref["type"],
        }
        if image_ref["subfolder"]:
            params["subfolder"] = image_ref["subfolder"]

        try:
            view_response = self._client.get(
                build_comfyui_api_url(base_url, api_prefix, "/view"),
                params=params,
                headers=self._request_headers,
            )
            view_response.raise_for_status()
            png_bytes = view_response.content
        except httpx.HTTPError:
            return ComfyUIImageResult(
                png_bytes=None,
                error_code=BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
            )

        if not png_bytes:
            return ComfyUIImageResult(
                png_bytes=None,
                error_code=BLOG_IMAGE_GENERATION_COMFYUI_FAILED,
            )

        return ComfyUIImageResult(png_bytes=png_bytes, error_code=None)


class FakeComfyUIClient:
    """Deterministic ComfyUI client for tests (no HTTP)."""

    def __init__(
        self,
        *,
        png_bytes: bytes | None = b"\x89PNG\r\n\x1a\nfake-comfyui-output",
        error_code: str | None = None,
    ) -> None:
        self.png_bytes = png_bytes
        self.error_code = error_code
        self.calls: list[dict[str, Any]] = []

    def generate_image(
        self,
        *,
        positive_prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        seed: int,
    ) -> ComfyUIImageResult:
        self.calls.append(
            {
                "positive_prompt": positive_prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "seed": seed,
            }
        )
        if self.error_code:
            return ComfyUIImageResult(png_bytes=None, error_code=self.error_code)
        return ComfyUIImageResult(png_bytes=self.png_bytes, error_code=None)
