## Context

BL-004 progress after US-009 / US-010 (validated 2026-07-15):

| Layer | State |
|-------|-------|
| Canonical Flow A n8n | `silvermanFlowAPublish01` — server **active**, Schedule `0 9 * * *` UTC, single-flight, 31 nodes |
| Repo export | `active: false` (authoritative for git/CI) |
| Flow A HTTP path | publish → package → schedule (HTTP only; no LinkedIn API nodes) |
| `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` | **`true`** in RUNTIME-STATE (operator-restored after US-009 temporary `false` window) |
| LinkedIn queue/publish/cancel | Implemented + fail-closed when flag ≠ `true` (`linkedin_publish_not_enabled`); first real publish validated under BL-002 |
| US-011 / BL-004 closure | **Open** — last BL-004 story |
| BL-005 | **Open** — activation ≠ unattended E2E |

US-011 AC: keep LinkedIn publication disabled until separately approved, with operator-visible outcomes and clear blocked states, without undoing US-009/US-010.

Critical semantic: **US-011 is not “LinkedIn must stay false forever.”** It means enablement is independent of Flow A schedule/activation, fail-closed until an explicit separate approval, and that Flow A running cannot silently publish to LinkedIn. A controlled evidence window may set the flag `false` to prove the guard, then restore the prior operator-approved value (US-009 pattern).

## Goals / Non-Goals

**Goals:**

- Prove Flow A activation/schedule ≠ LinkedIn enablement; `distribution_scheduled` ≠ LinkedIn API published.
- Demonstrate fail-closed LinkedIn publication via existing worker path when flag is `false`.
- Operator-visible PASS/PENDING/FAIL + remediation; record evidence under `docs/operations/`.
- Restore prior operator-approved `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` after the evidence window unless operator explicitly chooses a different lasting value and records it.
- Close US-011 and BL-004 only after demonstrated evidence; leave BL-005 open.
- Prefer docs + evidence + light assertions; no new LinkedIn endpoints.

**Non-Goals:**

- BL-005 unattended E2E; BL-007 / auto_queue / publish-pending WIP; Flow B; calendar execute-flow-a-due rewrite.
- New LinkedIn routes or redesign of queue/publish/cancel.
- Permanent force-off of LinkedIn as the post-US-011 policy.
- Flipping LinkedIn as a side effect of Flow A activation work (already completed under US-010).
- n8n Execute Command.

## Decisions

### 1. Evidence-first + light assertions (not new publication features)

**Decision:** Satisfy US-011 primarily with:

1. Docs clarifying separation (Flow A schedule vs LinkedIn enablement; GLOSSARY / CURRENT-STATE language).
2. Operator evidence procedure on `192.168.0.194`.
3. Light repo assertions (Flow A export has no LinkedIn API/nodes; existing `linkedin_publish_not_enabled` tests remain green).

Do **not** invent new LinkedIn endpoints or expand OpenAPI.

**Rationale:** Publication fail-closed is already implemented and unit-tested; the gap is operator acceptance that scheduled Flow A does not create unintended LinkedIn publication.

**Alternatives considered:**

- Permanently set flag `false` in production — rejected; contradicts RUNTIME-STATE / operator restore and misreads US-011.
- New “guard status” HTTP endpoint — rejected; overengineering for an acceptance story.
- Rework n8n Flow A for LinkedIn nodes with gates — rejected; violates HTTP-only and existing “MUST NOT publish to LinkedIn” orchestration rule.

### 2. Controlled disable → prove → restore window (US-009 pattern)

**Decision:** Evidence procedure:

1. Record baseline: current `.env` / container value of `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` (expected `true` per RUNTIME-STATE snapshot; treat recorded baseline as truth).
2. With explicit operator approval: set flag `false`, recreate worker, confirm container env `false`.
3. Call existing real-mode publish path against a safe fixture (queued variant or dry harness that still exercises the enablement gate) and expect stable `linkedin_publish_not_enabled` (variant state not advanced to published/failed for “not enabled”).
4. Confirm canonical Flow A workflow still has no LinkedIn API/nodes and empty-ready Manual/schedule path does not call LinkedIn publication endpoints.
5. Restore **prior recorded baseline** (not a hardcoded `false`), recreate worker, confirm match.
6. Write `docs/operations/us-011-linkedin-publication-guard-validation-YYYY-MM-DD.md`.

Prefer empty `blog-posts/ready/` for any Flow A run during the window. Do not perform BL-005 full unattended publish. Do not merge BL-007 WIP.

**Rationale:** Matches US-009 §5.5; preserves operator-approved enablement after proof; avoids reading US-011 as permanent disable.

**Alternative considered:** Docs-only without live fail-closed probe — rejected; US-011 needs demonstrated blocked-state communication on the live stack when possible. If live LinkedIn probe is blocked, record PENDING with remediation (do not close story on docs alone).

### 3. Ownership split: activation vs publication guard

| Capability | Owns |
|------------|------|
| `flow-a-n8n-workflow-activation` | Schedule, active server workflow, single-flight, restart — MUST NOT flip LinkedIn as activation side effect |
| `flow-a-linkedin-publication-guard` (new) | US-011 ACs, fail-closed evidence, temporary flag window + restore, BL-004 closure |
| `linkedin-publication-integration` (canonical, unchanged contract) | Existing queue/publish/cancel + `linkedin_publish_not_enabled` |

**Decision:** Modify activation spec so it no longer says “US-011 remains incomplete forever relative to this capability,” but continues to forbid LinkedIn flag flips during activation procedures. Closing US-011 is exclusively via the new guard capability after evidence.

### 4. What “disabled until separately approved” means for product closure

**Decision:** For marking US-011 / BL-004 complete:

- Flow A does not invoke LinkedIn API.
- Publication remains gated by `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` (fail-closed when not `true`).
- Evidence showed disabled behavior during the verify window.
- Post-window RUNTIME-STATE records the restored (or operator-chosen) value explicitly.
- Separate approval for real LinkedIn publish remains an explicit operator/backlog act (existing BL-002 tools; future BL-007) — not automatic from Flow A schedule.

Closing BL-004 does **not** require the lasting operational flag to be `false`.

### 5. Light test/doc touchpoints

**Decision:**

- Assert/continue: Flow A n8n export excludes LinkedIn hosts/nodes (existing or thin extension in `tests/test_n8n_workflow.py`).
- Assert/continue: `tests/test_linkedin_publication.py` covers disabled → `linkedin_publish_not_enabled`.
- Optional thin ops script only if apply finds copy-paste risk in manual steps; default is documented checklist + evidence markdown (prefer fewer new scripts than US-010).
- Update README / deployment docs where they still say US-011 open after validation.
- Product checklist: US-011 → all BL-004 stories → close BL-004; BL-005 stays open.

### 6. HTTP-only and secrets

All verification uses worker HTTP and n8n inspection APIs/scripts already in deployment docs. Never print tokens. No Execute Command.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Misread US-011 as permanent LinkedIn-off | Explicit proposal/design language; restore baseline step mandatory in evidence |
| Leaving flag `false` after failed restore | Trap/finally pattern in ops doc; evidence FAIL if restore mismatch |
| Touching BL-007 WIP during apply | Explicit non-goals; do not stage those paths |
| Live publish probe with wrong campaign | Use dry harness or known safe queued fixture; prefer empty ready; no new post to LinkedIn |
| Confusing activation vs unattended | CURRENT-STATE: BL-004 closed ≠ BL-005 done |
| Docs drift saying US-011 still open after close | Checklist task to update README/CURRENT-STATE/ops pointers together |

## Migration Plan

1. Approve proposal → `/opsx-apply`.
2. Specs already in change; implement light assertions + docs templates/checklist.
3. Operator approval → run disable/prove/restore evidence on `192.168.0.194`.
4. After PASS: update CURRENT-STATE, RUNTIME-STATE, user-stories US-011, progress-checklist (close BL-004), leave BL-005 open.
5. `/opsx-verify` → commit → sync → archive (separate commits; push/deploy only with approval).

**Rollback:** Re-set `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` to the recorded pre-window value and recreate worker; no n8n activation rollback required for this story.

## Open Questions

None blocking approval. Resolve at apply only if:

- No safe fixture exists for live `linkedin_publish_not_enabled` probe → use existing unit/integration test evidence + container env proof as PENDING vs PASS criteria; operator decides whether that is enough for story acceptance before closing.
