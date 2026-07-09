## 1. Configuration and workflow template

- [x] 1.1 Add ComfyUI image generation settings to worker config module with env vars: `SILVERMAN_COMFYUI_IMAGE_ENABLED` (default false), `SILVERMAN_COMFYUI_BASE_URL`, `SILVERMAN_COMFYUI_WORKFLOW_PATH`, `SILVERMAN_COMFYUI_TIMEOUT_SECONDS`, `SILVERMAN_COMFYUI_IMAGE_WIDTH` (default 1200), `SILVERMAN_COMFYUI_IMAGE_HEIGHT` (default 900), `SILVERMAN_COMFYUI_DRY_RUN`
- [x] 1.2 Add default ComfyUI workflow JSON template under `prompts/comfyui/` (configurable path) with placeholders for prompt, negative prompt, width, height, and seed
- [x] 1.3 Document new env vars in README or deployment docs (minimal operator notes; no public repo changes)

## 2. Prompt assembly

- [x] 2.1 Implement `blog_image_prompt.py` to build positive/negative prompts from title, description, tags, categories, and bounded body excerpt
- [x] 2.2 Encode editorial rules in prompt templates: 4:3 composition, centered subject, safe margins, no readable text/logos, professional technical editorial style
- [x] 2.3 Add unit tests for prompt assembly covering sparse vs rich front matter and prompt hash stability

## 3. ComfyUI client

- [x] 3.1 Implement `comfyui_client.py` with `ComfyUIClientProtocol` and production HTTP client: load workflow JSON, inject parameters, POST `/prompt`, poll `/history`, download PNG via `/view`
- [x] 3.2 Implement `FakeComfyUIClient` for tests returning deterministic PNG bytes
- [x] 3.3 Map ComfyUI/network failures to stable error codes (`blog_image_generation_comfyui_failed`, `blog_image_generation_timeout`, `blog_image_generation_not_configured`)
- [x] 3.4 Add unit tests for fake client success, timeout, and misconfiguration paths

## 4. Blog image generation orchestration

- [x] 4.1 Implement `blog_image_generation.py` with `ensure_blog_image()` and `BlogImageGenerationResult` dataclass
- [x] 4.2 Implement missing-image detection (empty/missing `image` or missing companion PNG; skip when wrong non-canonical `image` path)
- [x] 4.3 Write generated PNG to `blog-posts/ready/<source_slug>.png` and patch front matter to `image: /assets/images/<public_slug>.png` using existing front matter utilities
- [x] 4.4 Implement dry-run mode (plan paths/dimensions/prompt hash; no HTTP or file writes)
- [x] 4.5 Record `blog_image_generation` on campaign metadata and append run metadata under `metadata/runs/` when applicable
- [x] 4.6 Add `tests/test_blog_image_generation.py` covering: missing image generation, existing image skip, generation failure, metadata recording, dry-run, disabled default

## 5. Publish flow integration

- [x] 5.1 Integrate `ensure_blog_image()` into `publish_blog_post()` after preflight/idempotent short-circuit and before `validate_ready_post()`
- [x] 5.2 Recompute `source_content_sha256` when front matter is updated by generation before validation/idempotency checks
- [x] 5.3 Abort publish on required generation failure; include `blog_image_generation` summary and stable error codes in `BlogPublishResult` / HTTP response
- [x] 5.4 Extend `tests/test_blog_publish_flow.py` with fake ComfyUI client scenarios: generate-then-publish success, generation failure blocks publish, disabled generation unchanged behavior

## 6. Validation and regression

- [x] 6.1 Run full pytest suite; confirm no live ComfyUI dependency in default test run
- [x] 6.2 Verify backward compatibility: posts with existing valid `image` + PNG publish unchanged when generation disabled
- [x] 6.3 Run `openspec validate comfyui-blog-image-generation --strict` (or project equivalent) and fix any spec issues

## 7. Comfy Cloud / hosted compatibility

- [x] 7.1 Add optional env vars: `SILVERMAN_COMFYUI_API_PREFIX`, `SILVERMAN_COMFYUI_API_KEY`, `SILVERMAN_COMFYUI_AUTH_HEADER_NAME`, `SILVERMAN_COMFYUI_EXTRA_DATA_API_KEY_FIELD`
- [x] 7.2 Build ComfyUI client URLs with optional API prefix; send conditional auth header (`Authorization` → Bearer, other headers → raw key) and optional `extra_data` API key field without exposing secrets
- [x] 7.3 Update README, deployment docs, and env example for local/LAN and Comfy Cloud/hosted ComfyUI
- [x] 7.4 Add tests for API prefix, auth header, `extra_data`, secret non-leakage, and unchanged local behavior

## 8. Comfy Cloud OpenAI workflow template

- [x] 8.1 Add `prompts/comfyui/silverman-blog-openai-gpt-image.json` with Comfy Cloud `OpenAIGPTImage1` + `SaveImage` workflow and bindings (`positive_prompt`, `seed`, `output`)
- [x] 8.2 Point default `SILVERMAN_COMFYUI_WORKFLOW_PATH` to Comfy Cloud workflow; keep `blog-image-workflow.json` for local SD with width/height bindings
- [x] 8.3 Make `negative_prompt`, `width`, `height`, and `seed` optional bindings in `inject_workflow_parameters()`
- [x] 8.4 Record `workflow_controls_dimensions` in generation metadata when width/height bindings are absent
- [x] 8.5 Document 1536×1024 Comfy Cloud preset vs 1200×900 future/local target in README and env example
- [x] 8.6 Add tests for OpenAI workflow injection, optional bindings, preset size preservation, and local workflow compatibility
