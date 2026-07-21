## 1. Backlog store and validation

- [x] 1.1 Add `editorial_content_backlog` store module (Postgres `silverman_linkedin_db` via `SILVERMAN_CALENDAR_DATABASE_URL`; `memory://` for tests) with idempotent `ensure_schema` for `editorial_content_backlog_items` (and LinkedIn derivative notes as JSONB column or child rows)
- [x] 1.2 Implement create/list/get/update helpers with server-assigned `item_id`, UTC timestamps, and optional `row_version` optimistic concurrency
- [x] 1.3 Implement write-path validation for US-049 fields: non-empty `topic` / `audience` / `objective`; enums `format` (`blog`|`linkedin`|`both`), `priority` (`low`|`medium`|`high`), `status` (`idea`|`planned`|`in_progress`|`done`|`dropped`); optional `target_date` as `YYYY-MM-DD` or null; bounded LinkedIn derivative note objects — reject invalid writes without partial persist

## 2. Authenticated HTTP API

- [x] 2.1 Add authenticated `GET /editorial/content-backlog` (list; empty list is success) and optional `GET /editorial/content-backlog/{item_id}`; reject unauthenticated callers; never expose secrets
- [x] 2.2 Add authenticated `POST /editorial/content-backlog` (create) and `PUT /editorial/content-backlog/{item_id}` (update) with structured 4xx validation errors and clear store-unavailable failures distinct from empty list
- [x] 2.3 Prove create/update does not enable LinkedIn API publish / does not mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`; does not write `linkedin-posts/` packages
- [x] 2.4 Confirm no US-050 dependency fields/routes; no Flow B discover/draft/gap-trigger seeding wiring; no n8n Execute Command; do not change Flow A publish/package/schedule or gap-trigger defaults

## 3. Flow B independence guardrails

- [x] 3.1 Ensure Flow B discovery, draft generation, and gap-trigger modules do not hard-require the backlog store (no import-time or request-time mandatory backlog dependency)
- [x] 3.2 Add or extend a regression assertion that discovery and/or gap-trigger paths still succeed under empty backlog conditions without a backlog-required error code

## 4. Silverman Authority Manager UI

- [x] 4.1 Extend the existing supervision console with an authenticated Content backlog surface (header affordance + modal/panel; not a separate app) using the typed API client + session/`canMutate` patterns
- [x] 4.2 Wire list/create/edit for capture fields and LinkedIn derivative notes; empty state is understandable; validation/auth/store errors in plain language; copy that backlog is optional and save ≠ LinkedIn publish / ≠ Flow B trigger
- [x] 4.3 Rebuild/publish static console assets into the worker static path and ensure the console HTML route still serves them

## 5. Tests

- [x] 5.1 Pytest: create/list/update round-trip (`memory://`), validation failures, auth required, empty list success, store-unavailable messaging, secret-free responses, LinkedIn publish guard untouched, no package side effects
- [x] 5.2 Vitest (if UI ships): backlog list/create/edit happy path, empty state, and validation/auth failure messaging
- [x] 5.3 Run targeted pytest (and frontend tests as applicable); fix warnings attributable to this change; `git diff --check` clean

## 6. Docs and product status

- [x] 6.1 Update `docs/CURRENT-STATE.md` to record editorial content backlog as **implemented** (not Story accepted / not deployed / not BL-020 closed unless separately approved)
- [x] 6.2 After demonstrated AC (local), update `docs/product/user-stories.md` US-049 and `docs/product/progress-checklist.md` only to the validated in-progress state — do not mark Story accepted without operator review; do not close BL-020; leave US-050 unchecked
- [x] 6.3 Optionally note optional-enrichment semantics in ops/glossary cross-links if needed for operator clarity (no invented capabilities)

## 7. Business validation gate

- [x] 7.1 Walk US-049 acceptance criteria against local worker (+ console if shipped): capture field set; LinkedIn derivative links; Flow B discover/gap-trigger still run with empty backlog; outcome visible; failures clear; no unintentional change to completed Flow A/Flow B work
- [x] 7.2 Record any remaining gaps explicitly; leave US-050 / discovery seed / BL-020 closed unchecked
