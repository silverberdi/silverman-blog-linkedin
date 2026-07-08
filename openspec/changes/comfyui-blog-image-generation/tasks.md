## 1. Configuration and workflow template

- [ ] 1.1 Add ComfyUI image generation settings to worker config module with env vars: `SILVERMAN_COMFYUI_IMAGE_ENABLED` (default false), `SILVERMAN_COMFYUI_BASE_URL`, `SILVERMAN_COMFYUI_WORKFLOW_PATH`, `SILVERMAN_COMFYUI_TIMEOUT_SECONDS`, `SILVERMAN_COMFYUI_IMAGE_WIDTH` (default 1200), `SILVERMAN_COMFYUI_IMAGE_HEIGHT` (default 900), `SILVERMAN_COMFYUI_DRY_RUN`
- [ ] 1.2 Add default ComfyUI workflow JSON template under `prompts/comfyui/` (configurable path) with placeholders for prompt, negative prompt, width, height, and seed
- [ ] 1.3 Document new env vars in README or deployment docs (minimal operator notes; no public repo changes)

## 2. Prompt assembly

- [ ] 2.1 Implement `blog_image_prompt.py` to build positive/negative prompts from title, description, tags, categories, and bounded body excerpt
- [ ] 2.2 Encode editorial rules in prompt templates: 4:3 composition, centered subject, safe margins, no readable text/logos, professional technical editorial style
- [ ] 2.3 Add unit tests for prompt assembly covering sparse vs rich front matter and prompt hash stability

## 3. ComfyUI client

- [ ] 3.1 Implement `comfyui_client.py` with `ComfyUIClientProtocol` and production HTTP client: load workflow JSON, inject parameters, POST `/prompt`, poll `/history`, download PNG via `/view`
- [ ] 3.2 Implement `FakeComfyUIClient` for tests returning deterministic PNG bytes
- [ ] 3.3 Map ComfyUI/network failures to stable error codes (`blog_image_generation_comfyui_failed`, `blog_image_generation_timeout`, `blog_image_generation_not_configured`)
- [ ] 3.4 Add unit tests for fake client success, timeout, and misconfiguration paths

## 4. Blog image generation orchestration

- [ ] 4.1 Implement `blog_image_generation.py` with `ensure_blog_image()` and `BlogImageGenerationResult` dataclass
- [ ] 4.2 Implement missing-image detection (empty/missing `image` or missing companion PNG; skip when wrong non-canonical `image` path)
- [ ] 4.3 Write generated PNG to `blog-posts/ready/<source_slug>.png` and patch front matter to `image: /assets/images/<public_slug>.png` using existing front matter utilities
- [ ] 4.4 Implement dry-run mode (plan paths/dimensions/prompt hash; no HTTP or file writes)
- [ ] 4.5 Record `blog_image_generation` on campaign metadata and append run metadata under `metadata/runs/` when applicable
- [ ] 4.6 Add `tests/test_blog_image_generation.py` covering: missing image generation, existing image skip, generation failure, metadata recording, dry-run, disabled default

## 5. Publish flow integration

- [ ] 5.1 Integrate `ensure_blog_image()` into `publish_blog_post()` after preflight/idempotent short-circuit and before `validate_ready_post()`
- [ ] 5.2 Recompute `source_content_sha256` when front matter is updated by generation before validation/idempotency checks
- [ ] 5.3 Abort publish on required generation failure; include `blog_image_generation` summary and stable error codes in `BlogPublishResult` / HTTP response
- [ ] 5.4 Extend `tests/test_blog_publish_flow.py` with fake ComfyUI client scenarios: generate-then-publish success, generation failure blocks publish, disabled generation unchanged behavior

## 6. Validation and regression

- [ ] 6.1 Run full pytest suite; confirm no live ComfyUI dependency in default test run
- [ ] 6.2 Verify backward compatibility: posts with existing valid `image` + PNG publish unchanged when generation disabled
- [ ] 6.3 Run `openspec validate comfyui-blog-image-generation --strict` (or project equivalent) and fix any spec issues
