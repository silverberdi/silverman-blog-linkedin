# Tasks: respect-linkedin-audience-cadence-us-020

## 1. Contract cross-check (before any code)

- [x] 1.1 Re-read canonical `linkedin-publication-integration` and `linkedin-distribution-scheduling-model` and confirm this delta is purely additive: no renamed/retyped fields, no new endpoints, no new request flags, no `publish_state` changes, no US-017 endpoint/mechanics changes, no `POST /queue-linkedin-publication` contract changes, and no edits to `linkedin-distribution-scheduling-model` (justification: no schedule-time behavior changes; the guard only consumes the canonical sequence and stored evidence at execution time)
- [x] 1.2 Confirm the synced US-018 contract is preserved: existing scenarios (default-off, skip taxonomy and precedence, once-only, bounded scan, dry-run no-mutation) remain satisfiable with the auto-queue sequence pre-filter evaluated last and the publish-time guard evaluated after already-published/not-queued/not-due handling
- [x] 1.3 Confirm the synced US-019 contract is preserved: evidence fields, blocked-vs-failed taxonomy, no-automatic-retry, and idempotency evidence requirements are untouched; `published_at` is consumed read-only by the cadence rule; "failed releases the chain" takes no retry position and leaves stored failure evidence intact
- [x] 1.4 Confirm BL-008 exclusions are named in the delta and that no task below implements retries, recoverable classification, token renewal, timeout handling, or attempt history after manual re-queue

## 2. Minimal code (publish-time guard + auto-queue pre-filter)

- [x] 2.1 Reuse the canonical audience sequence from `linkedin_distribution_schedule.py` (import `AUDIENCE_SEQUENCE`; deterministic fallback ordering for non-canonical variant ids: ascending `scheduled_at_utc`, then variant id)
- [x] 2.2 Add stable reason constants in `linkedin_publication_flow.py`: `linkedin_publish_blocked_sequence`, `linkedin_publish_blocked_cadence`, `linkedin_publish_blocked_evidence_invalid`, and `linkedin_publish_auto_queue_skipped_sequence`
- [x] 2.3 Publish-time guard in the publish evaluation of `queued` variants (all modes: plain publish-due, combined flow, targeted requests, cross-campaign scan): after existing already-published/not-queued/`publish_after_utc` handling and before dry-run reporting, config validation, token resolution, or any LinkedIn call, evaluate sequence → evidence → cadence against the campaign document; blocked variants keep `publish_state`, report the stable reason, make zero LinkedIn/OAuth calls, and never fail the overall operation
- [x] 2.4 Sequence rule: block while an earlier canonical-sequence variant is awaiting publication (`pending` — including operator-deferred — or `queued` unpublished); releasing states: `published` (feeds cadence), `failed` (evidence intact, no retry), `cancelled`; no mutation of any sibling or supervision metadata
- [x] 2.5 Cadence rule: block unless every `published` sibling has parsable `published_at` with `published_at + 72h <= now_utc`; a publish completed within the current run counts (no second same-campaign publication in one run); missing/invalid `published_at` on any `published` sibling fails closed with `linkedin_publish_blocked_evidence_invalid`; guard scope strictly per campaign document
- [x] 2.6 Auto-queue pre-filter in `_auto_queue_skip_reason`: skip a due eligible `pending` variant with `linkedin_publish_auto_queue_skipped_sequence` while an earlier variant is awaiting publication (including a variant queued earlier in the same request); existing skip-reason precedence preserved (state → supervision → not-due → sequence)
- [x] 2.7 Ensure `publish_now` bypasses only the ordinary timing gates (`scheduled_at_utc` due gate, `publish_after_utc`), never sequence, cadence, evidence fail-closed, supervision exclusions, or a deferred time; dry-run reports planned blocks with zero metadata writes and zero LinkedIn/OAuth calls; `POST /queue-linkedin-publication` request/response contract byte-for-byte unchanged

## 3. Scenario-mirroring tests (mocked LinkedIn client, zero real calls)

- [x] 3.1 US-020 sequence over queued variants: two `queued` variants past `publish_after_utc` → variant N not published while N-1 remains `queued`/unpublished; N reports `linkedin_publish_blocked_sequence` and stays `queued`
- [x] 3.2 US-020 plain publish-due guard: same enforcement with `auto_queue_pending` false
- [x] 3.3 US-020 publish_now non-bypass: `publish_now` true bypasses neither sequence nor cadence; blocked variants keep `publish_state` and trigger no LinkedIn call
- [x] 3.4 US-020 cadence blocks under 3 days: `published` sibling with `published_at` less than 72h ago blocks the next due `queued` variant with `linkedin_publish_blocked_cadence`
- [x] 3.5 US-020 cadence allows at 3+ days: latest `published_at` ≥72h ago and sequence satisfied → next due `queued` variant publishes
- [x] 3.6 US-020 within-run cadence: after a successful publish in the current run, no second variant of the same campaign publishes in that run
- [x] 3.7 US-020 releasing states: earlier `failed` and `cancelled` release the chain; the `failed` variant is not retried and its stored failure evidence is byte-for-byte unchanged
- [x] 3.8 US-020 defer blocks followers: operator-deferred earlier `pending` variant blocks later variants from auto-queue and from publish, including under `publish_now`, without mutating any sibling or supervision metadata
- [x] 3.9 US-020 per-campaign scope: cross-campaign scan without `campaign_id` evaluates sequence and cadence independently per campaign; one campaign's block or publication never gates another campaign's
- [x] 3.10 US-020 dry-run: sequence, cadence, and evidence blocks reported under `dry_run` true with no metadata writes and no LinkedIn/OAuth calls
- [x] 3.11 US-020 evidence fail-closed: `published` sibling with missing or unparsable `published_at` blocks the campaign with `linkedin_publish_blocked_evidence_invalid`, visibly, without failing the overall operation and without affecting other campaigns in the scan
- [x] 3.12 US-020 manual queue no escape hatch: a later-sequence variant manually queued via `POST /queue-linkedin-publication` while an earlier variant is `pending` or `queued` is blocked at publish time with `linkedin_publish_blocked_sequence`
- [x] 3.13 US-020 skip-reason precedence: a not-due later variant behind an awaiting earlier variant still reports `linkedin_publish_auto_queue_skipped_not_due` at auto-queue (existing US-018 precedence preserved)
- [x] 3.14 US-020 no contract reshape: full `tests/test_linkedin_publication.py` passes with existing US-018/US-019 tests unmodified and no weakened assertions

## 4. Documentation

- [x] 4.1 Operator docs (`docs/deployment/linkedin-publication-prerequisites.md`): add a publish-time cadence/sequence section — sequence and 72-hour cadence rules, blocking vs releasing table (defer blocks followers; failed/cancelled release), `publish_now` timing-only scope, fail-closed behavior on invalid `published_at` and its manual repair path, and the explicit note that manual queueing does not bypass the guard at publish time (no out-of-order escape hatch exists)
- [x] 4.2 Update `docs/CURRENT-STATE.md`: US-020 publish-time sequence/cadence guard **implemented, not deployed** (local build only until an approved deploy); BL-007 remains open; US-019/US-020 not closed; no RUNTIME-STATE change (no live flags touched)

## 5. Verification

- [x] 5.1 Targeted tests: `pytest tests/test_linkedin_publication.py tests/test_linkedin_distribution_scheduling.py`
- [x] 5.2 Full `pytest` (executable code changed) with zero new warnings
- [x] 5.3 `openspec validate --strict` for this change passes
- [x] 5.4 Run `/opsx-verify`; re-run after any post-verify edit
- [x] 5.5 `git diff --check` clean; stage-time secrets audit on all new/modified files (no tokens, keys, or body text in code, tests, or docs)

## 6. Acceptance-criteria mapping (no story closure)

- [x] 6.1 Map US-020 acceptance criteria to demonstrated evidence (test names + docs sections) in `docs/product/user-stories.md`, marking US-020 **in progress — implementation demonstrated in tests/docs, not complete**; do NOT check the story complete, do NOT close US-019 or BL-007
- [x] 6.2 Update `docs/product/progress-checklist.md` to the actual state only: implemented, not deployed, not operationally validated; closure of US-019/US-020/BL-007 remains a separate authorized validation step (business validation deferred to that step — no deploy, no n8n activation in this change)
