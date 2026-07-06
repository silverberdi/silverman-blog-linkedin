## 1. Documentation

- [x] 1.1 Add **Worker API key rotation** section to `docs/deployment/ubuntu-server-worker-deployment.md` covering preparation (generate key, backup current values), rotation order (worker `.env` → restart → validate → n8n `worker_api_key`), and explicit warning not to commit secrets
- [x] 1.2 Document post-rotation validation: `GET /health` (200), old Bearer rejected (401), new Bearer accepted (200), `smoke-worker.sh` PASS, manual n8n workflow run with draft in `linkedin-posts/review/`
- [x] 1.3 Document rollback: restore previous `.env` value, restart worker, run `smoke-worker.sh`, restore previous n8n `worker_api_key`, re-run workflow

## 2. Verification helper script

- [x] 2.1 Create `deploy/server/verify-worker-api-key-rotation.sh` with health, old-key 401, and new-key 200 checks; read new key from server `.env`; accept old key only via `OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY` env var
- [x] 2.2 Ensure the script never prints, writes, or logs API key values; document usage in the deployment guide (example: `OLD_SILVERMAN_BLOG_LINKEDIN_API_KEY=local-test-key ./verify-worker-api-key-rotation.sh`)
- [x] 2.3 Ensure `deploy-worker.sh` syncs the new script to `/home/silverman/silverman-blog-linkedin-worker` (add to artifact copy list if not already covered by directory sync)

## 3. Tests and validation

- [x] 3.1 Extend `tests/test_server_deployment_artifacts.py` to verify `verify-worker-api-key-rotation.sh` exists and deployment doc mentions worker API key rotation
- [x] 3.2 Run `pytest tests/test_server_deployment_artifacts.py` locally
- [x] 3.3 Run `openspec validate rotate-worker-api-key` and `openspec validate --all`

## 4. Server execution (operator — not committed)

- [x] 4.1 On server: generate new key, update `/home/silverman/silverman-blog-linkedin-worker/.env`, restart worker via isolated compose
- [x] 4.2 On server: run `verify-worker-api-key-rotation.sh` with old key env var, then `smoke-worker.sh`
- [x] 4.3 In n8n: update `worker_api_key` in **Silverman Blog LinkedIn Draft Generation** Set Configuration; run workflow and confirm new LinkedIn draft
