## Why

Repository context sources—Cursor rules, OpenSpec injected context, bootstrap docs, README, and workflow narratives—still describe an early Phase 1 worker (`GET /health` → `process-ready` → `process-file`) and omit or misstate capabilities that are now implemented, tested, and deployed (Flow A core through campaign `flow_a_complete`, ComfyUI image generation, blog handoff, LinkedIn package/scheduling, calendar reconciliation, publication idempotency). Stale context causes new Cursor sessions and OpenSpec proposals to mis-scope work, treat archived changes as active requirements, or collapse distinct completion states (e.g., campaign `flow_a_complete` vs fully unattended Flow A vs site published/live vs LinkedIn API publication validated). This change consolidates authoritative current-state documentation and aligns all context-bearing files before further engineering.

## Goals

- Establish three canonical governance documents: `docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, `docs/GLOSSARY.md`.
- Add `docs/RUNTIME-STATE.md` as a volatile operational snapshot (not architectural authority).
- Introduce an explicit authority hierarchy and conflict-resolution rules where canonical specs are normative, implementation/tests are evidence, and neither silently overrides a discrepancy.
- Align Cursor always-on rule, OpenSpec `config.yaml`, README, bootstrap context, workflows, deployment/operations docs, and editorial canon metadata with verified repository evidence (last verified baseline revision `88cd5bc` at `2026-07-10T00:00:00Z`, 27/27 OpenSpec specs, 850 tests).
- Standardize engineering workflow and hyphenated slash-command syntax (`/opsx-propose`, `/opsx-apply`, `/opsx-verify`, etc.).
- Distinguish precisely: implemented vs operationally validated vs manual vs incomplete vs deferred.
- Prevent ambiguous "Flow A complete" language; reserve `flow_a_complete` for campaign lifecycle state only.
- Split mixed workflow responsibilities into `flow-a-target-flow.md` and `linkedin-draft-review-flow.md`.
- Define lightweight context-drift prevention rules tied to capability, topology, and activation changes.
- Mark historical/bootstrap documents visibly; reduce duplication without deleting useful rationale.

## Non-Goals

- Implementing Git commit/push automation, activating n8n, publishing to LinkedIn, modifying OAuth credentials, changing ComfyUI or Flow A runtime behavior, implementing Flow B, adding observability, changing deployment topology, modifying live server files, changing canonical behavioral specs unrelated to context governance, rewriting archived OpenSpec changes, deleting historical evidence, or modifying executable logic in `scripts/flow_a_readiness.py` (stale hardcoded revision defaults are documented as a separate follow-up).

## What Changes

### Inventory summary

| Category | Count | Paths |
|----------|-------|-------|
| **Create** | **5** | `docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, `docs/GLOSSARY.md`, `docs/RUNTIME-STATE.md`, `.cursor/commands/opsx-verify.md` |
| **Create (workflow split)** | **2** | `docs/workflows/flow-a-target-flow.md`, `docs/workflows/linkedin-draft-review-flow.md` |
| **Substantive update** | **13** | See file-action matrix in `design.md` (rows 9–11, 14–16, 18–23, 25) |
| **Historical banner** | **4** | Bootstrap/operations docs superseded by canonical sources (rows 12–13, 17, 24) |
| **Compatibility stub** | **1** | `docs/workflows/phase-1-target-flow.md` (row 8) |
| **Cross-link only** | **3** | ADR-0001, ADR-0002, ADR-0003 (rows 26–28) |
| **Inspect-only** | **5** | Examples, deploy manifests, `scripts/flow_a_readiness.py` (rows 29–33) |
| **No change** | **3** | Canonical specs, archived changes, readiness tests (rows 34–36) |

### New canonical and command documents (5 creates)

- **`docs/CURRENT-STATE.md`** — Canonical project status: purpose, business goals, architecture, ownership matrix, implemented/validated/manual/incomplete/deferred roadmap with `last_verified_at_utc`, real operational evidence (post `04-a-bounded-context-is-not-a-folder.md`), runtime topology pointers, known spec↔implementation divergences, and explicit qualified completion layers. Records revision `88cd5bc` as the last verified baseline with timestamp; MUST NOT treat that SHA as a permanent runtime requirement.
- **`docs/CONTEXT-AUTHORITY.md`** — Authority hierarchy, document roles, conflict resolution, historical-document handling, canonical references for Cursor and OpenSpec.
- **`docs/GLOSSARY.md`** — Precise definitions for Flow A, Flow A Core, `distribution_scheduled`, `flow_a_complete`, operational smoke pass, fully unattended Flow A, Flow B, folder states, blog handoff vs site published/live, LinkedIn publication states, OpenSpec terms, reconciliation, idempotency.
- **`docs/RUNTIME-STATE.md`** — Volatile point-in-time operational snapshot with `verified_at_utc`, evidence source, and `unknown` for unverified facts; no secrets; not architectural authority; consulted only when live state is relevant.
- **`.cursor/commands/opsx-verify.md`** — Project-specific Cursor command wrapper (not a native OpenSpec CLI command). Uses `openspec validate <change-name> --strict` plus artifact/task completion, change-required tests, traceability, and staleness checks. See design D8.

### Workflow split (2 creates + 1 stub)

- **`docs/workflows/flow-a-target-flow.md`** — Flow A automation pipeline (calendar connector through source lifecycle completion).
- **`docs/workflows/linkedin-draft-review-flow.md`** — Human LinkedIn draft review, approval, and manual publication path.
- **`docs/workflows/phase-1-target-flow.md`** — Convert to historical compatibility stub explaining the split; link both current documents. Do not simply rename.

### Cursor and OpenSpec configuration

- **`.cursor/rules/silverman-blog-linkedin-project.mdc`** — Concise always-on guardrails; links to canonical docs; current engineering workflow with approval gates; remove stale phased-delivery claims; prevent Flow A completion ambiguity.
- **`openspec/config.yaml`** — Inject explicit canonical context paths only (`docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, `docs/GLOSSARY.md`, accepted ADRs, canonical specs). Do not inject all of `docs/context/` or all workflow documents. Bootstrap and historical documents are lower authority.

### README and existing documentation

- **`README.md`** — Prominent links to canonical docs; accurate capability summary; blog handoff vs Git publication; LinkedIn implemented vs operationally validated (real API publication not validated); n8n imported but inactive (not unattended automation); `BUILD_REVISION` (not `SILVERMAN_BUILD_REVISION`).
- **Bootstrap context (`docs/context/*.md`)** — File-by-file per design matrix: historical banners or substantive updates pointing to canonical sources.
- **Deployment/operations** — Align deployment docs; historical banner on `docs/operations/n8n-server-worker-integration-2026-07-06.md`.
- **`content-strategy/silverman-editorial-system.md`** — Correct umbrella reference to archived `openspec/changes/archive/2026-07-07-flow-a-automatic-blog-linkedin-publishing-roadmap/`; metadata-only corrections; preserve editorial policy body.
- **ADRs (`docs/decisions/ADR-0001`–`0003`)** — Cross-links to canonical context only; do not alter accepted decisions.
- **`scripts/flow_a_readiness.py`** — Documentation, comments, and help text in README may be corrected; executable defaults, logic, and expected-commit behavior MUST NOT change. Stale `DEFAULT_EXPECTED_COMMITS` documented as follow-up change.

## Capabilities

### New Capabilities

- `repository-context-governance`: Requirements for canonical current-state, authority, and glossary documentation; authority hierarchy precedence; document classification (current, historical, deprecated); context-drift prevention triggers; engineering workflow encoding; `/opsx-verify` wrapper contract; RUNTIME-STATE maintenance contract; and precise operational-status terminology that Cursor and OpenSpec must consume.

### Modified Capabilities

- _(none)_ — No behavioral requirement changes to worker, n8n, or editorial processing specs. Editorial canon policy content is corrected at document level only; canonical `editorial-canon` spec requirements remain unchanged unless a proven contradiction is found during apply.

## Impact

- **Documentation and configuration only** — No application code, endpoints, or runtime behavior changes in this change.
- **Consumers:** Cursor (always-on rule + commands), OpenSpec CLI injected context, operators, and future proposal authors.
- **Verification:** `openspec validate align-project-context-and-current-state --strict`; path existence checks; grep-based stale-claim audits; YAML parse of `openspec/config.yaml`; no full test suite unless executable scripts are modified (they are not).

## Why a Dedicated HTTP Worker (unchanged architectural fact)

n8n orchestrates over HTTP only (ADR-0001). The worker owns filesystem boundaries, validation, generation, metadata, and lifecycle moves. This documentation change does not alter that separation; it ensures context accurately reflects how far Flow A has progressed and what remains manual or unvalidated.

## Explicit anti-patterns this change prevents

- Archived OpenSpec changes treated as active implementation instructions.
- Bare "Flow A complete" without a qualified completion layer.
- Worker public-checkout file writes described as site published/live.
- Implemented LinkedIn package/scheduling support described as operationally validated real API publication.
- n8n workflow JSON import/existence described as unattended production automation.
