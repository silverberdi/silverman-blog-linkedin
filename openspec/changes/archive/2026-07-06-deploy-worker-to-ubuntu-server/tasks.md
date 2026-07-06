## 1. Server compose and environment artifacts

- [x] 1.1 Create `deploy/server/silverman-worker.compose.yaml` with worker service building from repo `Dockerfile`, `restart: unless-stopped`, port `8010:8000`, `PORT=8000`, `SILVERMAN_BLOG_LINKEDIN_BASE_PATH=/data/silverman-blog-linkedin`, editorial volume mount `/home/silverman/compartido_mac/silverman-blog-linkedin:/data/silverman-blog-linkedin`, `env_file` for server-local `.env`, and healthcheck against `GET /health` on container port `8000`
- [x] 1.2 Create `deploy/server/silverman-worker.env.example` with placeholder values for `SILVERMAN_BLOG_LINKEDIN_API_KEY`, `DEEPSEEK_API_KEY`, `DEEPSEEK_MODEL`, `DEEPSEEK_TIMEOUT_SECONDS`, and `DEEPSEEK_MAX_OUTPUT_TOKENS` (no real secrets)
- [x] 1.3 Verify compose does not reference or modify `local-ai-stack` or shared-stack services

## 2. Deploy and smoke scripts

- [x] 2.1 Create `deploy/server/deploy-worker.sh` that creates `/home/silverman/silverman-blog-linkedin-worker` if needed, syncs required build and deploy artifacts, instructs manual `.env` creation from the example, and runs `docker compose -f silverman-worker.compose.yaml up -d --build` only in the worker deploy directory
- [x] 2.2 Ensure `deploy-worker.sh` never runs `docker compose down` or other compose commands against unrelated projects (especially `local-ai-stack`)
- [x] 2.3 Create `deploy/server/smoke-worker.sh` with required checks: `GET http://localhost:8010/health` and authenticated `POST /process-ready` using API key from server-local `.env`
- [x] 2.4 Add optional deeper generation smoke in `smoke-worker.sh` when `DEEPSEEK_API_KEY` and a ready `.md` file exist; do not require it for basic PASS
- [x] 2.5 Make scripts executable and use clear PASS/FAIL output with non-zero exit on required-check failure

## 3. Documentation

- [x] 3.1 Create `docs/deployment/ubuntu-server-worker-deployment.md` covering prerequisites, target paths, port `8010`, `.env` setup, deploy and smoke steps, n8n `worker_base_url` (`http://192.168.0.194:8010`), rollback (`docker compose down` in worker directory only), and troubleshooting
- [x] 3.2 Update `README.md` with a link to the Ubuntu server deployment guide (distinct from local `docker-compose.example.yml` usage)

## 4. Lightweight deployment artifact tests

- [x] 4.1 Add pytest module verifying `deploy/server/silverman-worker.compose.yaml` exists and declares host port `8010`, container port `8000`, and editorial volume mount path
- [x] 4.2 Add pytest checks that `silverman-worker.env.example` documents required variable names and uses placeholders only (no committed real secrets)
- [x] 4.3 Add pytest checks that `deploy-worker.sh` and `smoke-worker.sh` exist

## 5. Validation

- [x] 5.1 Run `python -m pytest` (or `python3 -m pytest` per repo convention) and ensure all tests pass including new deployment artifact tests
- [x] 5.2 Run `openspec validate deploy-worker-to-ubuntu-server` and fix any issues
- [x] 5.3 Run `openspec validate --all` and fix any issues

## 6. Manual server verification (operator)

- [x] 6.1 On `silverman@192.168.0.194`, create server-local `.env` from example with real keys (not committed)
- [x] 6.2 Run `deploy-worker.sh` and confirm worker listens on port `8010`
- [x] 6.3 Run `smoke-worker.sh` and confirm required checks PASS
- [x] 6.4 Update n8n workflow `worker_base_url` to `http://192.168.0.194:8010` and run manual workflow smoke (draft under `linkedin-posts/review/`, source post remains in `blog-posts/ready/`)
