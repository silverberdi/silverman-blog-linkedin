## Context

LinkedIn API publication is fully implemented in the worker (`linkedin_publication_flow.py`, `linkedin_client.py`, three HTTP endpoints) with unit tests and a generic dry-run smoke script (`run-linkedin-publication-smoke.sh`). Production worker at `192.168.0.194:8010` keeps `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` — correctly fail-closed but leaving **BL-002** open.

US-001/US-002 established a repeatable pattern: dedicated `run-us00N-*.sh` script, temporary enablement window, real external evidence, idempotency check, cleanup/restoration, Phase 3 report under `docs/operations/`, then canonical doc updates.

OAuth token lifecycle is implemented with `GET /linkedin/oauth/status` for safe preflight. Queue → safety delay → publish-due is the normative two-step model; controlled validation will use `publish_now: true` on publish-due to avoid waiting two hours.

**OAuth bootstrap is a blocking prerequisite** (not assumed from US-001/US-002 phases). Phase 2 server notes recorded absent `linkedin-oauth-tokens.json` / `linkedin-oauth-state.json` on the host. Before US-003 validation: create token store files, confirm Cloudflare Tunnel routes `api.silverman.pro` → worker, complete browser authorization, and verify `GET /linkedin/oauth/status` reports `token_present` and `member_urn` — see `docs/deployment/linkedin-publication-prerequisites.md`.

**Idempotency is already implemented:** `publish_linkedin_due_variants` returns `completed` with warning `linkedin_publish_already_published` for `published` variants without a second LinkedIn API call (`test_idempotent_published_rerun`). US-003 script asserts this behavior; no worker change expected unless HTTP-layer assertion gaps appear.

**State terminology:** user story US-003 lists `publishing` as a lifecycle step; canonical `publish_state` values are `pending | queued | published | failed | cancelled`. During the API call the variant remains `queued` until success transitions to `published`. Phase 3 reports should describe “publishing” as the in-flight API step, not a persisted metadata state.

Unlike US-001/US-002 smoke validation, the LinkedIn post is an **irreversible external artifact** (no repo cleanup); operator may delete manually in LinkedIn afterward.

Constraints:

- ADR-0001: validation orchestration via worker HTTP only.
- No secrets in scripts, reports, logs, or HTTP responses.
- One real LinkedIn post on operator profile (visible until manually removed).
- Default endpoint `dry_run: true` unchanged for all callers.

## Goals / Non-Goals

**Goals:**

- Deliver `run-us003-linkedin-publication-validation-smoke.sh` mirroring US-001/US-002 rigor.
- Prove OAuth + member URN + queue + publish + URN storage + LinkedIn visibility + idempotency + safeguard restoration.
- Minimal code changes — fix only validation blockers.
- Update canonical state docs only after demonstrated evidence.

**Non-Goals:**

- New publication endpoints or campaign state transitions beyond existing spec.
- n8n activation, cron, or automatic publish-due scheduling.
- Multi-variant or due-date scheduling validation (BL-007).
- Automated LinkedIn feed scraping for visibility (human checklist v1).
- Deleting the LinkedIn post programmatically after validation.

## Decisions

### 1. Dedicated US-003 script rather than extending generic smoke only

**Choice:** New `run-us003-linkedin-publication-validation-smoke.sh`; extend `run-linkedin-publication-smoke.sh` only for shared flags (`--publish-now`, `--idempotency-rerun`) if needed.

**Rationale:** US-001/US-002 use dedicated scripts with precondition checks, enablement window handling, and evidence summaries. Generic smoke auto-detects latest campaign — unsafe for real LinkedIn publish.

**Alternative:** Extend generic smoke with `--us003` mode — rejected to keep dangerous real-publish path explicit and named.

### 2. Campaign selection — operator-specified, default bounded-context campaign

**Choice:** Script requires `--campaign-id` and `--variant`; document recommended starting point: existing validated Flow A campaign for post `04-a-bounded-context-is-not-a-folder` with one operator-approved variant (e.g. `executive-recruiter`) in `publish_state` `pending`.

**Rationale:** BL-002 asks for one **approved** variant on real content, not synthetic smoke. Operator explicitly selects variant to publish.

**Alternative:** Auto-create isolated smoke campaign — acceptable only with `--allow-smoke-campaign` flag and operator acknowledgment; not default.

### 3. Validation sequence

**Choice:** Ordered steps:

1. Load worker `.env`; verify API key present (never print).
2. Optional: set `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` and recreate container (mirror US-001 pattern).
3. `GET /health` — record `BUILD_REVISION`.
4. `GET /linkedin/oauth/status` — preflight (member URN, token present, expiry, publication enabled).
5. Snapshot variant state from campaign metadata.
6. `POST /queue-linkedin-publication` `{ dry_run: false, campaign_id, variant }` — expect `queued`.
7. `POST /publish-linkedin-due-variants` `{ dry_run: false, publish_now: true, campaign_id, variant }` — expect `published` + `linkedin_post_urn`.
8. Snapshot metadata; operator visibility checklist prompt.
9. Repeat step 7 — expect idempotent already-published, no second API call.
10. Safeguard restoration: `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false`, recreate container, verify disabled.
11. Print `OVERALL: PASS` or `FAIL`.

**Rationale:** Matches canonical two-step publication model while using `publish_now` for controlled test window.

### 4. OAuth preflight via existing diagnostic endpoint

**Choice:** Use `GET /linkedin/oauth/status` (already spec'd) — no new preflight endpoint unless implementation gap found.

**Rationale:** Avoids new HTTP surface; diagnostic already reports member URN and expiry without tokens.

### 5. Idempotency evidence

**Choice:** Assert existing publish-due idempotency — `linkedin_publish_already_published` warning, no second API call, URN unchanged. US-003 script checks HTTP response and/or campaign metadata on repeat publish-due.

**Rationale:** Already implemented and covered by `test_idempotent_published_rerun`. Delta spec codifies behavior for archive traceability; apply should verify, not reimplement.

### 6. Safeguard restoration is mandatory operator step

**Choice:** Script attempts automatic restoration of `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` in a `trap`/`finally` block; operator must confirm in Phase 3 report.

**Rationale:** US-005 explicit; prevents leaving production worker in always-publish mode after test.

### 7. Phase 3 report template

**Choice:** Add `docs/operations/phase3-us003-linkedin-publication-validation-TEMPLATE.md` or inline section in deployment docs; fill dated report after live run.

**Rationale:** Consistent with US-001/US-002 evidence artifacts.

### 8. Code changes expected to be minimal

**Choice:** Primary deliverable is scripts + docs. Touch worker code only if validation exposes: missing idempotent publish-due, oauth status gaps, or metadata fields needed for evidence.

**Rationale:** Implementation already exists; this change validates it.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Real post remains on LinkedIn profile | Document operator manual delete option; use approved content operator accepts publishing |
| Accidental publish of wrong variant | Require explicit `--campaign-id` and `--variant`; no auto-detect |
| Token expires mid-validation | Preflight + abort; reauthorization docs |
| Publication flag left enabled | `trap` restoration + Phase 3 confirmation |
| LinkedIn API rate limit or content rejection | Record failure in Phase 3; variant may become `failed` per existing spec; restore safeguards anyway |
| LinkedIn HTTP 426 (unsupported API version) | Check `SILVERMAN_LINKEDIN_API_VERSION`; update per LinkedIn versioning docs, redeploy, retry publish-due |
| OAuth bootstrap incomplete | Block US-003 script at preflight; complete prerequisites in tasks §0 before validation window |

## Migration Plan

0. **OAuth bootstrap (blocking):** create host token/state files, confirm tunnel, run browser authorization, verify `/linkedin/oauth/status` green — tasks §0.
1. Implement US-003 script and doc updates on Mac; review in PR.
2. Deploy worker image to `192.168.0.194` if script depends on new code (otherwise script-only deploy).
3. Reconfirm OAuth status immediately before validation window (token may expire between bootstrap and run).
4. Run US-003 script during approved validation window with explicit campaign/variant.
5. Complete visibility checklist; write Phase 3 report.
6. Confirm safeguards restored; update `CURRENT-STATE`, `RUNTIME-STATE`, `progress-checklist`.
7. Rollback: publication flag false (default); no code rollback required if validation-only.

## Open Questions

| Question | Resolution |
|----------|------------|
| Which variant to publish first? | Operator chooses; document `executive-recruiter` on bounded-context campaign as example |
| Keep published post or delete? | Operator decision; out of scope for automation |
| Need worker code change for idempotency? | **Closed** — verified in `linkedin_publication_flow.py` + `test_idempotent_published_rerun`; script assertion only |
| OAuth bootstrap in scope? | **Closed** — operator prerequisites in tasks §0; documented in runbook, not new worker features |
