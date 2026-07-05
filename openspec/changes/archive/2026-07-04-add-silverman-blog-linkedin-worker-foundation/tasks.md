## 1. Project scaffolding

- [x] 1.1 Add `pyproject.toml` with Python 3.11+, FastAPI, uvicorn, pytest, and httpx (or equivalent test client) dependencies
- [x] 1.2 Create package layout under `src/silverman_blog_linkedin/` with `__init__.py` exposing version/service identifier (`0.1.0`, `silverman-blog-linkedin-worker`)
- [x] 1.3 Add `.gitignore` entries for virtualenv, `__pycache__`, and local `data/` if not already present

## 2. Configuration module

- [x] 2.1 Implement `config.py` to load `SILVERMAN_BLOG_LINKEDIN_BASE_PATH` (default `./data/silverman-blog-linkedin`), `SILVERMAN_BLOG_LINKEDIN_API_KEY` (required), and `PORT` (default `8000`)
- [x] 2.2 Resolve base path to absolute/normalized form after load
- [x] 2.3 Fail fast at startup when API key is missing or empty; never log secret values
- [x] 2.4 Add `tests/test_config.py` covering defaults, overrides, missing API key, and path resolution

## 3. Editorial path validation

- [x] 3.1 Implement `paths.py` with the canonical list of ten expected relative folders under the base path
- [x] 3.2 Implement read-only validation returning per-folder results (`exists`, `is_directory`) and aggregate `folders_ready`
- [x] 3.3 Add `tests/test_paths.py` using temporary directories for complete layout, missing folders, and missing base path

## 4. FastAPI application and health endpoint

- [x] 4.1 Implement `main.py` with FastAPI app factory wired to configuration
- [x] 4.2 Implement `GET /health` returning JSON with `status`, `service`, `version`, `base_path`, `folders_ready`, and `folders` map
- [x] 4.3 Map `status` to `healthy` when all folders ready, `degraded` otherwise; do not expose API key in response
- [x] 4.4 Add uvicorn entrypoint (module `main:app` or equivalent) honoring `PORT`
- [x] 4.5 Add `tests/test_health.py` using FastAPI TestClient for healthy, degraded, and no-secrets-in-response cases

## 5. Docker and deployment artifacts

- [x] 5.1 Add `Dockerfile` building a slim Python image that runs the worker on `PORT`
- [x] 5.2 Add `docker-compose.example.yml` with env vars, port mapping, volume mount to `/data/silverman-blog-linkedin`, and optional healthcheck against `GET /health`
- [x] 5.3 Verify locally: build image and run container against a sample editorial tree (manual smoke check)

## 6. Documentation

- [x] 6.1 Add or update `README.md` with project purpose, env var reference, editorial folder layout, local run instructions, test commands, Docker usage, and `/health` example response
- [x] 6.2 Document local default base path (`./data/silverman-blog-linkedin`) vs container path (`/data/silverman-blog-linkedin`)

## 7. Validation

- [x] 7.1 Run full test suite (`pytest`) and ensure all tests pass
- [x] 7.2 Run `openspec validate add-silverman-blog-linkedin-worker-foundation` after implementation
- [x] 7.3 Manual smoke test: start worker locally, call `GET /health`, confirm JSON structure matches spec
