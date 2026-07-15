## Context

US-009 validated canonical Flow A n8n identity on `192.168.0.194`:

| Field | Value |
|-------|-------|
| Export | `n8n/workflows/silverman-blog-linkedin-flow-a-publish.json` |
| Id | `silvermanFlowAPublish01` |
| Name | Silverman Blog LinkedIn Flow A Publish |
| Nodes | 26 |
| Server state | Imported, **inactive**, no Schedule Trigger |
| Proposed schedule | Daily **09:00 UTC** (docs-only until this change) |

Worker Flow A HTTP path is operationally validated. The export already chains Manual Trigger → health → `POST /process-ready` → publish → package → schedule (HTTP only, ADR-0001). Import/evidence/readiness scripts currently **fail** if `active: true` or if Schedule Trigger nodes exist — those US-009 gates must become intentional, mode-aware exceptions for US-010.

RUNTIME-STATE (2026-07-15): `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` (operator-restored after US-009 verify window). Flow A orchestration does **not** call LinkedIn publication APIs; US-011 still owns the “disabled until separately approved” acceptance and is **out of scope** here.

## Goals / Non-Goals

**Goals:**

- Activate `silvermanFlowAPublish01` on the Ubuntu server with a real Schedule Trigger (daily 09:00 UTC).
- Keep Manual Trigger for operator-initiated runs.
- Prevent overlapping concurrent executions (single-flight).
- Prove restart/recovery does not double-process or leave permanent stuck locks.
- Operator-visible pass/fail/pending + remediation; update scripts/docs for repo-vs-server active divergence.
- Preserve qualified language and HTTP-only boundary.

**Non-Goals:**

- US-011 LinkedIn publication-guard story completion; flag flips for production policy.
- BL-005 fully unattended end-to-end test.
- BL-007 / auto_queue WIP; publish-pending LinkedIn workflow.
- Flow B draft workflow; calendar connector rewrite to replace ready-folder path.
- New worker endpoints unless apply proves the chosen n8n single-flight cannot be implemented.
- n8n Execute Command.

## Decisions

### 1. Schedule Trigger expression (daily 09:00 UTC)

**Decision:** Add an n8n **Schedule Trigger** node (`n8n-nodes-base.scheduleTrigger`) with cron expression:

```text
0 9 * * *
```

Timezone: **UTC** (explicit in node parameters / trigger timezone field so server local TZ cannot drift the wall clock).

Both **Manual Trigger** and **Schedule Trigger** connect into the existing **Set Configuration** entry (dual entry; no change to downstream HTTP chain).

**Rationale:** Matches US-009 proposed frequency; cron is unambiguous; UTC avoids DST surprises on the host.

**Alternatives considered:**

- Interval every 24h from activation time — rejected; drifts from clock-aligned editorial window.
- Hourly polling — rejected; higher overlap risk without BL-013 full concurrency suite.
- Calendar webhook / only `execute-flow-a-due` — rejected for US-010; keeps scope to activating the already-canonical ready-folder workflow.

### 2. Relationship to `POST /editorial-calendar/execute-flow-a-due`

**Decision:** US-010 activates the **existing ready-folder** orchestration (`POST /process-ready` → publish → package → schedule). It does **not** rewire the workflow to `POST /editorial-calendar/execute-flow-a-due`.

Document the split clearly:

| Mechanism | Role |
|-----------|------|
| Schedule Trigger @ 09:00 UTC | Orchestration **timer** — wakes Flow A n8n |
| `POST /process-ready` path | Scan operator-approved `blog-posts/ready/` |
| `POST /editorial-calendar/execute-flow-a-due` | Calendar **policy** connector for due calendar items (unchanged; not this workflow’s body) |

**Rationale:** US-009 identified this export as canonical; changing the HTTP path would expand scope and risk BL-003/calendar regressions. Empty ready folder → clean no-op (already in orchestration spec).

### 3. Single-flight / anti-concurrency mechanism

**Decision (layered):**

1. **Primary (orchestration):** Single-flight guard at the start of the shared path (after Set Configuration, before Health Check) using n8n **workflow static data** (or equivalent Code/IF pattern allowed under ADR-0001 — not Execute Command):
   - If a lock is held and **not past TTL**, exit on a dedicated skip branch with operator-visible `outcome: skipped_already_running` (not a hard failure for schedule).
   - If free or expired, acquire lock with `execution_id` + `acquired_at_utc`.
   - Release lock on all terminal success/error/empty-ready stop paths (best effort).
   - **TTL:** 2 hours (configurable constant documented in workflow notes / ops doc) so container kills cannot permanently stick the lock.
2. **Safety net (worker, existing):** Idempotent `already_published` / package / schedule responses — do not invent new worker locks for US-010.
3. **Optional native:** If server n8n version exposes a first-class “max concurrent executions = 1” workflow setting, enable it **in addition** to the guard; do not rely on it alone without verified evidence.

**Rationale:** Prefer orchestration-side over new worker contracts; static-data lock is the standard n8n pattern when native skip-if-running is absent or unverified; worker idempotency covers completed work duplication even if two runs race past a broken lock.

**Alternatives considered:**

- Worker filesystem mutex / new endpoint — deferred; violates “orchestration-side first” and expands OpenAPI surface.
- Campaign idempotency only — insufficient for concurrent mid-publish races on a fresh ready post.
- “Operator discipline only” — fails US-010 AC for preventing concurrent processing.
- Global n8n concurrency env = 1 — too blunt; affects unrelated workflows in `local-ai-stack`.

### 4. Repo `active` vs server activation (authoritative path)

**Decision:**

| Layer | `active` | Schedule Trigger |
|-------|----------|------------------|
| **Repository export** (git) | **`false`** (authoritative for CI/clones) | **Present** (materialized) |
| **Server n8n** after US-010 | **`true`** (authoritative for live ops) | Present (imported) |

Activation procedure (separate from import prepare):

1. Re-import updated export via `import-flow-a-n8n-workflow.sh` (import still prepares/`verifies` inactive immediately after import).
2. Run identity checks (id, name, node count, schedule present, HTTP-only, no secrets).
3. Enable single-flight settings/nodes.
4. **Activate** on server (n8n UI or scripted activate API) — explicit operator/approval-gated step in apply/ops tasks.
5. Record `active: true` in RUNTIME-STATE; keep export `active: false` in git.

**Rationale:** Prevents accidental auto-activation on other hosts importing the JSON; CI continues to assert export inactivity; live state is documented in RUNTIME-STATE.

**Alternative considered:** `active: true` in git export — rejected; unsafe for clones and breaks “export ≠ production” discipline.

### 5. Expected node count

**Decision:** Update the constant from `26` to the measured post-edit count after adding Schedule Trigger + single-flight guard node(s). Design baseline expectation: **+2 nodes** (Schedule Trigger + Guard Code/Set) → **28**, unless apply finds a Merge is required (`+3` → **29**). Specs/scripts MUST use one named constant after the JSON is edited; tasks include measuring and updating all `EXPECTED_NODE_COUNT` / `FLOW_A_N8N_EXPECTED_NODE_COUNT` sites together.

### 6. Script/readiness intentional exceptions (US-009 → US-010)

| Check | US-009 | US-010 target |
|-------|--------|----------------|
| Repo export `active` | Must be `false` | Still must be `false` |
| Repo export Schedule Trigger | Forbidden | **Required** (exactly one Schedule Trigger with 09:00 UTC cron) |
| Server import immediate post-import | `active: false` | Still `false` until activation step |
| Server evidence (activation mode) | Fail if active | **Expect `active: true`** when `--expect-server-active` (or dedicated activation evidence script) |
| Node count | 26 | New constant (see §5) |

Add modes rather than deleting safety:

- `import-flow-a-n8n-workflow.sh`: still imports inactive; notes US-010 activation is a separate step; verify schedule node presence; update node count.
- `collect-flow-a-smoke-evidence.sh` / new thin `verify-flow-a-n8n-activation.sh`: support inactive (pre-activate) vs active (post-activate) expectations.
- `scripts/flow_a_readiness.py`: Phase 0 asserts export inactive + schedule present; Phase 2 can PASS on export identity including schedule; server-active is ops evidence, not repo Phase 0.

### 7. Restart and recovery evidence plan

**Safety first:** Prefer paths with **empty `blog-posts/ready/`** or non-mutating probes so schedule/manual runs are no-ops. Do **not** call LinkedIn publication APIs. Do **not** require live Git publish for concurrency/restart ACs. If any live blog side effect is later needed, gate behind **explicit operator approval** in the ops session (out of default path).

**Procedure (server `192.168.0.194`):**

1. **Baseline:** Confirm workflow id, schedule expression, `active: true`, single-flight configured; empty ready → Manual execute → clean stop (no candidates).
2. **Concurrent skip:** Acquire lock (Manual execute that holds path briefly, or inject lock via documented test hook if needed); second Manual execute while locked → `skipped_already_running`; no second worker apply chain.
3. **Idle restart:** Restart n8n container while idle; workflow remains active; next Manual or schedule fire works; no duplicate artifacts.
4. **Lock TTL after kill:** Hold lock without release (kill n8n mid-run or simulate); wait past TTL (or accelerate TTL in a temporary test config if approved); next run acquires lock successfully; no stuck-permanent fail.
5. **Completed-work safety:** Against an already-published campaign (or empty ready), rerun → worker idempotent completed / no-op; no duplicate public posts.
6. **Evidence:** Write `docs/operations/us-010-flow-a-n8n-activation-validation-YYYY-MM-DD.md` with timestamps, pass/fail per step, remediation notes. Update RUNTIME-STATE / CURRENT-STATE only after pass.

### 8. LinkedIn / US-011 boundary

**Decision:** US-010 MUST NOT flip `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` and MUST NOT call LinkedIn publish endpoints from the Flow A workflow. Design notes current RUNTIME value (`true` as of last snapshot) for operator awareness only. **US-011** owns proving publication remains disabled-until-approved relative to activated orchestration (and any policy restore). BL-005 remains the fully unattended proof.

### 9. HTTP-only boundary preserved

All worker integration remains HTTP Request nodes. Allowed additions: Schedule Trigger, Manual Trigger, IF/Set/NoOp/Code for guard/control. Forbidden: Execute Command, SSH, LinkedIn nodes, GitHub nodes, filesystem nodes.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Static-data lock not released on crash | TTL + idle restart evidence; document manual unlock procedure |
| Schedule runs with posts in ready while operator unready | Empty-ready ops discipline; activation noted ≠ BL-005 unattended; operator controls ready inbox |
| Import resets `active` to false | Activation is explicit post-import step; evidence verifies active after activate |
| Node-count drift breaks scripts | Single constant update task across all scripts/tests |
| Dual Manual+Schedule race before guard | Guard is first shared step after Set Configuration |
| Accidental live blog publish during tests | Default evidence uses empty ready; live side effects approval-gated |
| US-011 confusion if LinkedIn flag already true | Explicit non-goals + CURRENT-STATE language; do not close US-011 |
| Calendar due items not processed by this timer | Documented; calendar connector remains separate; BL-005 may revisit wiring |

## Migration Plan

1. Approve proposal → `/opsx-apply`.
2. Edit export JSON (Schedule Trigger, guard, connections); keep `active: false`; measure node count; update tests.
3. Update import/evidence/readiness scripts + docs for schedule-required / mode-aware active checks.
4. Deploy/sync repo to server; re-import workflow (still inactive).
5. Operator approval → activate workflow; run US-010 evidence procedure.
6. Update RUNTIME-STATE / CURRENT-STATE / product checklist for demonstrated US-010 only.
7. `/opsx-verify` → commit → sync → archive (separate commits; push/deploy only with approval).

**Rollback:** Deactivate workflow in n8n UI (or script); optionally re-import previous export without Schedule Trigger; record RUNTIME-STATE `active: false`. Worker unchanged.

## Open Questions

None blocking proposal approval. Resolve at apply only if:

- Server n8n build lacks Schedule Trigger / static data → fall back documented in apply notes and pause for operator decision.
- Exact node count after Merge necessity → update constant in the same apply pass.
