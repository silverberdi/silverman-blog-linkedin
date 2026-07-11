## Context

The `silverman-blog-linkedin` repository at revision `88cd5bc` (last verified baseline `2026-07-10T00:00:00Z`) implements a production-deployed HTTP worker with 27 canonical OpenSpec specs (all passing strict validation) and 850 automated tests. Flow A core—queue acceptance through campaign `flow_a_complete`, calendar reconciliation, and publication idempotency—has been operationally validated with a real post (`04-a-bounded-context-is-not-a-folder.md`). ComfyUI image generation, blog file handoff to the public checkout, LinkedIn package generation, and staggered scheduling metadata are validated. Git commit/push to GitHub Pages, real LinkedIn API publication, and unattended n8n scheduling remain manual, guarded, or incomplete.

Despite this, context sources still describe early bootstrap/Phase 1 scope:

| Source | Stale signal |
|--------|----------------|
| `openspec/config.yaml` | "Phase 1 excludes … GitHub publishing, automatic LinkedIn publishing"; endpoint sequence stops at `process-file` |
| `.cursor/rules/silverman-blog-linkedin-project.mdc` | Phasing ladder ending at LinkedIn publish; endpoints "implement only when approved" |
| `docs/context/backlog-and-phasing.md` | Phase 0–6 roadmap as if worker foundation not shipped |
| `docs/context/project-overview.md` | "will contain", Phase 1 scope only |
| `docs/workflows/phase-1-target-flow.md` | Mixed Phase 1 / Flow A / LinkedIn review responsibilities |
| `content-strategy/silverman-editorial-system.md` | References archived umbrella as "active" |
| `README.md` | Stale expected-commit defaults in readiness script section |

A new Cursor session reading only these files would underestimate implemented capabilities or overestimate automation (e.g., treating workflow JSON import as production activation).

**Verified operational evidence (2026-07-10):**

- Real post processed end-to-end through worker (ComfyUI, validation, handoff, package, schedule, lifecycle, `flow_a_complete`).
- Blog live at `https://silverman.pro/2026/07/10/a-bounded-context-is-not-a-folder/` after **manual** Git commit/push (worker handoff ≠ site published/live).
- `POST /publish-blog-post` idempotency returned `already_published` with no metadata side effects.
- Calendar reconciliation deployed; stale item moved `scheduled` → `completed` via authoritative `campaign_id` without repeating pipeline side effects.
- Worker deployed at `http://192.168.0.194:8010` with `BUILD_REVISION=88cd5bc…`; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false`; n8n Flow A workflow imported but **inactive** (existence ≠ unattended automation).

**Confirmed archived umbrella reference:** `openspec/changes/archive/2026-07-07-flow-a-automatic-blog-linkedin-publishing-roadmap/`

## Goals / Non-Goals

**Goals:**

- Single source of truth for **current status** (`docs/CURRENT-STATE.md`) separate from **authority rules** (`docs/CONTEXT-AUTHORITY.md`) and **terminology** (`docs/GLOSSARY.md`).
- Volatile operational snapshot (`docs/RUNTIME-STATE.md`) separate from durable status.
- Concise Cursor always-on rule pointing to canonical docs; rich OpenSpec injected context aligned with post-Flow-A-core reality.
- Closed file-action matrix for every evaluated context-bearing file.
- Standardized engineering lifecycle, hyphenated slash commands, and `/opsx-verify` wrapper contract.
- Ownership matrix and context-drift prevention checklist.

**Non-Goals:**

- Runtime behavior changes, live server operations, n8n activation, LinkedIn publication enablement, Git automation, Flow B implementation, new ADRs, executable changes to `scripts/flow_a_readiness.py`.

## Decisions

### D1: Three-document canonical structure plus runtime snapshot (not one combined doc)

**Decision:** Create `CURRENT-STATE.md`, `CONTEXT-AUTHORITY.md`, and `GLOSSARY.md` as separate durable governance files. Create `RUNTIME-STATE.md` as a volatile snapshot file.

**Rationale:** Different update cadences and audiences—status changes frequently; authority hierarchy is stable; glossary grows with terminology; runtime flags change on deploy/validation events. Combining would bloat always-on references.

### D2: Authority semantics (precedence and conflict)

| Layer | Role | Authority |
|-------|------|-----------|
| Canonical OpenSpec specs (`openspec/specs/`) | Normative requirements | Define what the system MUST do |
| Current implementation and tests (`src/`, `tests/`) | Evidence of real behavior | Demonstrate what the system actually does |
| `docs/CURRENT-STATE.md` | Operational completeness and status | Records validated/manual/incomplete state and **known unresolved divergences** |
| Accepted ADRs (`docs/decisions/ADR-000*.md`) | Durable architectural decisions | Bind design choices |
| Operator/deployment documentation | Procedures and topology | Guide operations |
| Editorial canon (`content-strategy/silverman-editorial-system.md`) | Editorial policy | Govern content rules |
| Bootstrap/historical context (`docs/context/`) | Rationale and history | Lower authority; bannered |
| Archived OpenSpec changes (`openspec/changes/archive/`) | Historical evidence only | MUST NOT drive new work |

**Conflict rule:**

- Canonical specs and implementation/tests are **peers in tension**, not a silent override hierarchy: specs are normative; implementation/tests are evidence.
- **Neither silently overrides a discrepancy.** Any spec↔implementation mismatch MUST be recorded in `docs/CURRENT-STATE.md` and resolved through a new OpenSpec change.
- Archived changes MUST NOT be cited as active requirements or implementation instructions.

### D3: Flow A completion terminology and anti-patterns

| Term | Meaning | MUST NOT mean |
|------|---------|---------------|
| `flow_a_complete` | Campaign metadata lifecycle state after source moved to `processed/` | Entire product/feature complete |
| Flow A core | Worker pipeline through package, schedule, lifecycle, calendar reconciliation | Unattended n8n production |
| Fully unattended Flow A | n8n scheduled trigger + worker + manual steps eliminated | Same as `flow_a_complete` |
| Blog files written / blog handoff | Worker wrote Jekyll files to public checkout mount | Site published/live |
| Site published/live | Git commit pushed; GitHub Pages deployed | Worker completed handoff |
| LinkedIn package/scheduling implemented | Worker generates packages and schedule metadata | Real LinkedIn API publication operationally validated |
| n8n workflow imported | Workflow JSON exists in n8n instance | Unattended production automation active |

Documents MUST NOT use bare "Flow A is complete" without qualifying which layer.

### D4: Bootstrap context file treatment

See file-action matrix (rows 12–18).

### D5: Workflow document split (not rename)

**Decision:** Split `docs/workflows/phase-1-target-flow.md` mixed responsibilities into two current documents:

- **`docs/workflows/flow-a-target-flow.md`** — Flow A automation: calendar connector, queue acceptance, publish/package/schedule/lifecycle, folder semantics, recovery.
- **`docs/workflows/linkedin-draft-review-flow.md`** — Human review path: `linkedin-posts/review/` → `approved/` → `published/`, manual publication, future automated publication boundary.

Convert **`docs/workflows/phase-1-target-flow.md`** into a **historical compatibility stub** explaining the split and linking both current documents. Do not simply rename the original file.

Update related workflow docs to cross-link glossary terms and CURRENT-STATE status.

### D6: Cursor rule shape

Keep `.cursor/rules/silverman-blog-linkedin-project.mdc` under ~80 lines:

- Purpose (one paragraph)
- Critical guardrails (HTTP-only n8n, OpenSpec before code, no secrets, no casual env flag changes)
- Links: CURRENT-STATE, CONTEXT-AUTHORITY, GLOSSARY, `openspec/specs/`, ADRs
- Engineering workflow (abbreviated lifecycle with approval gates)
- Explicit: qualified Flow A completion layers; link CURRENT-STATE roadmap

### D7: OpenSpec `config.yaml` injected context

Replace Phase 1 bootstrap narrative with:

- Post-Flow-A-core capability summary (implemented / validated / manual / incomplete)
- Authority semantics (D2)
- **Explicit canonical context paths only:**
  - `docs/CURRENT-STATE.md`
  - `docs/CONTEXT-AUTHORITY.md`
  - `docs/GLOSSARY.md`
  - `docs/decisions/ADR-000*.md` (accepted ADRs)
  - `openspec/specs/` (canonical specs)
- Engineering lifecycle and hyphenated command names
- Rule: proposals MUST consult CURRENT-STATE when operational status matters; MUST NOT inject all of `docs/context/` or all workflow documents; MUST NOT cite archived changes as requirements
- `docs/RUNTIME-STATE.md` consulted only when live operational state is relevant—not injected indiscriminately into every proposal

Add `specs` rules block if schema supports it.

### D8: `/opsx-verify` command contract (project-specific Cursor wrapper)

**Not a native OpenSpec CLI command.** Implemented as `.cursor/commands/opsx-verify.md` alongside other `/opsx-*` wrappers.

**Invocation:** `/opsx-verify [change-name]` — defaults to active change from conversation context.

**Required steps (in order):**

1. **Strict validation** — `openspec validate <change-name> --strict`
2. **Artifact completion** — `openspec status --change "<name>" --json`; confirm all `applyRequires` artifacts are `done`
3. **Task completion** — parse `tasks.md`; report incomplete checkboxes
4. **Change-required tests** — run tests scoped to the change (per tasks); skip full suite when change is docs-only unless tasks require otherwise
5. **Spec-to-implementation traceability** — for behavioral changes, confirm delta spec requirements have corresponding implementation/test evidence; flag gaps
6. **Staleness detection** — compare working tree to last verification marker if present; report any modifications since prior verification
7. **Staleness rule** — state explicitly: **any code or artifact modification after a prior verification makes that verification stale**; re-run `/opsx-verify` before commit/sync/archive
8. **Lifecycle guidance** — follow repository sequence: **commit (approved implementation) → `/opsx-sync` → `/opsx-archive`**
9. **Archive gate** — NEVER recommend `/opsx-archive` before approved implementation is committed and delta specs are synced

### D9: `docs/RUNTIME-STATE.md` maintenance contract

| Property | Requirement |
|----------|-------------|
| Nature | Volatile point-in-time operational snapshot |
| Authority | NOT architectural authority; NOT in normative hierarchy above bootstrap |
| Update triggers | After deploys, activation changes, real smoke tests, external-integration validation, or confirmed deployed-revision changes |
| Required fields | `verified_at_utc`, evidence source per fact, `unknown` for unverified facts |
| Secrets | MUST NOT contain secrets |
| Injection | NOT injected indiscriminately into every OpenSpec proposal |
| Consultation | Only when live operational state is relevant to the task |

Initial snapshot: `verified_at_utc=2026-07-10T00:00:00Z`, `BUILD_REVISION=88cd5bc`, topology, n8n inactive, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false`, ComfyUI enabled during validation (booleans/names only).

### D10: Context-drift prevention

When an approved change modifies any of: capability status, runtime topology, activation state, completion criteria, ownership boundary, OpenSpec workflow, deployment procedure, or external integration readiness—the implementing change MUST update `docs/CURRENT-STATE.md` (and `RUNTIME-STATE.md` when live flags change) in the same change or an immediate follow-up docs-only change.

### D11: Ownership matrix (canonical in CURRENT-STATE)

| Concern | Owner |
|---------|-------|
| Editorial source approval | Human operator |
| Flow A validation and lifecycle | Worker |
| Image generation | Worker → ComfyUI |
| Public checkout file writes | Worker (handoff only) |
| Git review/commit/push | Human/operator (site published/live) |
| LinkedIn package generation | Worker |
| LinkedIn schedule metadata | Worker |
| LinkedIn real API publish | Worker when explicitly enabled (not operationally validated) |
| Workflow timing/orchestration | n8n when activated (currently inactive) |
| Secrets and environment flags | Operator |
| Deployment | Operator (`deploy/server/deploy-worker.sh`) |
| Behavioral requirements | Canonical OpenSpec specs (normative) |
| Real behavior evidence | Implementation and tests |
| Current status and known divergences | `docs/CURRENT-STATE.md` |
| Volatile live flags | `docs/RUNTIME-STATE.md` |
| Editorial policy | Editorial canon |

### D12: README scope

README remains operator/developer quickstart. Add prominent "Project status" section linking three canonical docs. Trim duplicate readiness narrative; reference CURRENT-STATE for validation status. Document `BUILD_REVISION` correctly. Do not treat `88cd5bc` as permanent expected commit.

### D13: Executable script scope boundary

For `scripts/flow_a_readiness.py`:

- **In scope:** README references, documentation, comments, help text corrections
- **Out of scope:** `DEFAULT_EXPECTED_COMMITS`, CLI default logic, expected-commit behavior
- **Follow-up:** Stale hardcoded revisions (`79f5345`, `962ba2f`, `53708eb`) documented in CURRENT-STATE or CONTEXT-AUTHORITY as known divergence; separate OpenSpec change required to update executable defaults

### D14: No new ADR

Authority hierarchy and operational ownership are documentation governance. `CONTEXT-AUTHORITY.md` suffices. ADRs get cross-links only.

## Closed file-action matrix

Every evaluated context-bearing file. Actions: **create**, **substantive update**, **historical banner**, **compatibility stub**, **cross-link only**, **inspect-only**, **no change**.

| # | Path | Action | Reason | Authority source | Validation required |
|---|------|--------|--------|------------------|---------------------|
| 1 | `docs/CURRENT-STATE.md` | create | Canonical status, roadmap, divergences, last-verified baseline `88cd5bc` @ `2026-07-10T00:00:00Z` | Verified evidence + canonical specs | Path exists; links resolve; no ambiguous Flow A completion |
| 2 | `docs/CONTEXT-AUTHORITY.md` | create | Authority hierarchy, conflict rules, lifecycle | D2, engineering practice | Cross-references resolve |
| 3 | `docs/GLOSSARY.md` | create | Terminology precision | Canonical specs, CURRENT-STATE | Terms cover D3 table |
| 4 | `docs/RUNTIME-STATE.md` | create | Volatile operational snapshot per D9 | Deploy/smoke evidence | `verified_at_utc`, no secrets |
| 5 | `.cursor/commands/opsx-verify.md` | create | Verification wrapper per D8 | D8 contract | Command file exists; syntax documented |
| 6 | `docs/workflows/flow-a-target-flow.md` | create | Flow A automation split from mixed doc | `phase-1-target-flow.md`, specs | Terminology aligned with glossary |
| 7 | `docs/workflows/linkedin-draft-review-flow.md` | create | Human review split from mixed doc | `phase-1-target-flow.md`, editorial model | Handoff vs publication distinguished |
| 8 | `docs/workflows/phase-1-target-flow.md` | compatibility stub | Historical filename; explain split | D5 | Links to rows 6–7 |
| 9 | `.cursor/rules/silverman-blog-linkedin-project.mdc` | substantive update | Stale Phase 1 endpoints/phasing | CURRENT-STATE, CONTEXT-AUTHORITY | Under ~80 lines; canonical links |
| 10 | `openspec/config.yaml` | substantive update | Stale injected context | D7 explicit paths | YAML parse; no bulk context injection |
| 11 | `README.md` | substantive update | Stale capabilities, readiness SHAs | CURRENT-STATE | Links; BUILD_REVISION correct |
| 12 | `docs/context/project-overview.md` | historical banner | Superseded by CURRENT-STATE | CONTEXT-AUTHORITY | Banner visible; links canonical |
| 13 | `docs/context/backlog-and-phasing.md` | historical banner | Superseded roadmap | CURRENT-STATE | Banner visible |
| 14 | `docs/context/worker-architecture.md` | substantive update | Current endpoints, Flow A scope | Canonical specs, src/ | Endpoints match implementation |
| 15 | `docs/context/deployment-context.md` | substantive update | Current topology paths | Deployment docs, RUNTIME-STATE | Paths accurate |
| 16 | `docs/context/n8n-integration-context.md` | substantive update | Imported vs active distinction | RUNTIME-STATE | Inactive stated clearly |
| 17 | `docs/context/openai-content-generation-context.md` | historical banner | DeepSeek not OpenAI; historical | Canonical spec | Banner + correct provider |
| 18 | `docs/context/editorial-operating-model.md` | substantive update | Flow A/B approval semantics | Editorial canon, glossary | Phase 1 review language historical |
| 19 | `docs/workflows/blog-publishing-bridge.md` | substantive update | Handoff vs publication | GLOSSARY | No "published" conflation |
| 20 | `docs/workflows/editorial-calendar-orchestration.md` | substantive update | Flow A terminology | GLOSSARY, CURRENT-STATE | Cross-links |
| 21 | `docs/workflows/editorial-calendar-flow-a-execution-connector.md` | substantive update | Queue/folder semantics | Canonical specs | Recovery classifications |
| 22 | `docs/deployment/ubuntu-server-worker-deployment.md` | substantive update | Topology, BUILD_REVISION, manual Git | RUNTIME-STATE | Deploy paths correct |
| 23 | `docs/deployment/linkedin-publication-prerequisites.md` | substantive update | Implemented vs API-validated | CURRENT-STATE | Guard flags distinguished |
| 24 | `docs/operations/n8n-server-worker-integration-2026-07-06.md` | historical banner | Point-in-time record | CONTEXT-AUTHORITY | Banner + date |
| 25 | `content-strategy/silverman-editorial-system.md` | substantive update | Archived umbrella, metadata only | Archived change path | Policy body preserved |
| 26 | `docs/decisions/ADR-0001-use-worker-instead-of-n8n-execute-command.md` | cross-link only | Point to canonical context | ADR acceptance | No decision text change |
| 27 | `docs/decisions/ADR-0002-blog-post-is-canonical-content-source.md` | cross-link only | Point to canonical context | ADR acceptance | No decision text change |
| 28 | `docs/decisions/ADR-0003-develop-locally-deploy-containerized.md` | cross-link only | Point to canonical context | ADR acceptance | No decision text change |
| 29 | `docs/examples/editorial-calendar/calendar.example.json` | inspect-only | Example data; no stale claims expected | — | Grep if Phase 1 references found |
| 30 | `scripts/flow_a_readiness.py` | inspect-only | Executable out of scope (D13) | D13 | Document stale defaults as follow-up only |
| 31 | `deploy/server/*.sh` | inspect-only | Update comments only if stale | — | No behavior change |
| 32 | `deploy/server/silverman-worker.env.example` | inspect-only | Env template | — | No change unless stale comment |
| 33 | `deploy/server/silverman-worker.compose.yaml` | inspect-only | Compose template | — | No change |
| 34 | `tests/test_flow_a_readiness.py` | no change | Tests match frozen script behavior | — | — |
| 35 | `openspec/specs/**` | no change | Normative source; not edited by this change | — | Strict validation passes |
| 36 | `openspec/changes/archive/**` | no change | Historical evidence preserved | — | Not cited as active |

**Inventory totals:** 5 primary creates + 2 workflow-split creates = **7 creates**; 1 compatibility stub; **13 substantive updates**; 4 historical banners; 3 cross-link only; **5 inspect-only**; **3 no change**; **36 total**.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| CURRENT-STATE becomes stale quickly | `last_verified_at_utc`; drift-prevention rule; RUNTIME-STATE for volatile flags |
| Duplication between README and CURRENT-STATE | README links; no copy of roadmap tables |
| Broken links after workflow split | Compatibility stub at old path; grep for `phase-1-target-flow` |
| Operators confuse `flow_a_complete` with product complete | GLOSSARY + explicit bans in Cursor rule and OpenSpec context |
| opsx-verify wrapper diverges from CLI | Documents exact `openspec validate <name> --strict` invocation |
| Historical docs still read as current | Prominent `> **Historical bootstrap**` banners with date |
| Spec↔implementation drift hidden | CURRENT-STATE records known divergences; D2 conflict rule |

## Migration Plan

1. Create canonical docs and opsx-verify command (rows 1–5).
2. Create workflow split documents and compatibility stub (rows 6–8).
3. Update Cursor rule, OpenSpec config, README (rows 9–11).
4. Update bootstrap, workflow, deployment, editorial, ADR files per matrix (rows 12–28).
5. Inspect-only pass on examples, scripts, deploy artifacts (rows 29–33).
6. Grep audits (stale Phase 1, ambiguous Flow A completion, colon commands, archived-as-active).
7. `openspec validate align-project-context-and-current-state --strict`; path existence checks.
8. No deploy or live operations.

**Rollback:** Revert documentation commit; no runtime impact.

## Anti-pattern enforcement (design-level)

The following MUST appear in canonical docs and injected context:

1. Archived changes are historical evidence—not active instructions.
2. "Flow A complete" always qualified by completion layer (see D3).
3. Blog handoff ≠ site published/live.
4. LinkedIn implementation ≠ LinkedIn API operational validation.
5. n8n workflow existence/import ≠ unattended automation.
