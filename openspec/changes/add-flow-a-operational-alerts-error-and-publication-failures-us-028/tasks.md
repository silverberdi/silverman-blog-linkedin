## 1. Alert evaluation core

- [x] 1.1 Add alert config helpers for `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_ENABLED` and `SILVERMAN_FLOW_A_OPERATIONAL_ALERTS_WEBHOOK_URL` with fail-closed defaults (disabled / unset)
- [x] 1.2 Implement alert candidate derivation that reuses operational-status aggregation evidence for `item_moved_to_error`, `image_generation_failure` (`comfyui`), and `blog_publication_failure` (`blog_publish_*` / `blog_git_publication_*` only)
- [x] 1.3 Build secret-safe alert objects (`alert_type`, `severity`, `fingerprint`, identifiers, codes, dependency, short summary) with deterministic ordering and summary counts
- [x] 1.4 Exclude LinkedIn-preview checkout codes from `blog_publication_failure` and ensure US-029/US-030 alert types are not produced

## 2. HTTP contract and optional emission

- [x] 2.1 Wire authenticated `POST /flow-a/operational-alerts/evaluate` in `main.py` with `Depends(require_api_key)`, optional `now_utc`, and `emit` defaulting to `false`
- [x] 2.2 Implement evaluate-only path that returns candidates without webhook calls or ledger writes
- [x] 2.3 Implement fail-closed emit path: when disabled/misconfigured, return explicit `emission` status without webhook or ledger write; when enabled, POST safe payloads to the generic webhook
- [x] 2.4 Implement minimal idempotent ledger at `metadata/operational-alerts/emissions.json` (write after HTTP 2xx only; skip already-emitted fingerprints; never mutate campaign/run/editorial lifecycle files)

## 3. Tests

- [x] 3.1 Add focused tests for each US-028 alert type from controlled fixtures (error-folder campaign, comfyui codes, blog publish/git publication codes)
- [x] 3.2 Add tests excluding preview-only checkout codes from `blog_publication_failure` and asserting absence of US-029/US-030 types
- [x] 3.3 Add tests for auth 401, invalid `now_utc` 422, deterministic ordering, and safe-output exclusions (no secrets/bodies/webhook URL)
- [x] 3.4 Add tests for evaluate-only zero lifecycle mutation, fail-closed emit, successful emit + ledger write, and no re-emit for existing fingerprints
- [x] 3.5 Run targeted operational-alerts tests plus operational-status regression coverage; resolve warnings attributable to this change

## 4. Documentation and progress

- [x] 4.1 Add operator documentation for the evaluate/emit contract, env flags, webhook MVP channel, ledger path, and relationship to `GET /flow-a/operational-status`
- [x] 4.2 Update `docs/CURRENT-STATE.md` to the demonstrated US-028 implementation level only; do not claim US-028 acceptance, BL-011 closure, or BL-010 closure
- [x] 4.3 Update `docs/product/user-stories.md` US-028 status and `docs/product/progress-checklist.md` only for criteria actually demonstrated; leave US-029/US-030 and BL-011 closure unchanged

## 5. Business validation

- [x] 5.1 Demonstrate against controlled fixtures that an authenticated operator/n8n client can evaluate alerts for error-folder items, image-generation failures, and blog publication failures with understandable payloads
- [x] 5.2 Confirm failures/blocked states are clearly communicated and that evaluate-only does not mutate existing completed lifecycle work
- [x] 5.3 Confirm out-of-scope items remain absent (US-029/US-030 types, BL-015 UI, Slack/email SDK assumption, deploy/live mutation) and record remaining acceptance gaps explicitly
