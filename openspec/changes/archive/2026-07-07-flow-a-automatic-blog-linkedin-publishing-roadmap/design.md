## Context

### Current State (Flow A Core Complete — 2026-07)

The Silverman Blog LinkedIn automation system runs as an HTTP worker on an Ubuntu server, orchestrated by n8n over HTTP only (ADR-0001). **Flow A Core is implemented and operationally verified** through child slices 1–7 and deployment readiness/smoke verification:

| Component | Status |
|-----------|--------|
| `GET /health` | Implemented |
| `POST /process-ready` | Implemented — scans `blog-posts/ready/` |
| `POST /process-file` | Implemented — reads one ready Markdown post |
| `POST /generate-linkedin-draft` | Implemented — generates one LinkedIn draft variant |
| GitHub Pages publishing bridge | Implemented as CLI/domain capability (dry-run default, `--apply` required) |
| `POST /publish-blog-post` | Implemented — Flow A blog publish with validation, lifecycle, reconciliation, and GitHub Pages bridge |
| `POST /generate-linkedin-package` | Implemented — multi-variant Flow A package generation |
| `POST /schedule-linkedin-distribution` | Implemented — staggered scheduling metadata; `publish_state: pending` |
| Editorial canon | Implemented — `content-strategy/silverman-editorial-system.md` |
| Flow A lifecycle / campaign metadata | Implemented — `campaign_lifecycle.py`, `metadata/campaigns/` |
| Ready-post validation | Implemented — `ready_post_validation.py` |
| n8n Flow A orchestration workflow | Implemented — `silverman-blog-linkedin-flow-a-publish.json`, `"active": false`, 26 nodes |
| Deployment readiness + smoke verification | Implemented and archived — `scripts/flow_a_readiness.py`, `deploy/server/run-flow-a-worker-smoke.sh`, `collect-flow-a-smoke-evidence.sh` |

**Operational verification (Ubuntu server, 2026-07):** Worker smoke `OVERALL: PASS` end-to-end (`publish-blog-post` → `generate-linkedin-package` → `schedule-linkedin-distribution`); final campaign state `distribution_scheduled`; public image adopted safely during publish reconciliation; evidence collector `OVERALL: PASS`; n8n workflow inactive by design.

**Flow A Core boundary:** The pipeline stops at generated LinkedIn artifacts under `linkedin-posts/generated/`, scheduled distribution metadata with `publish_state: pending`, and campaign state `distribution_scheduled`. No LinkedIn API publication, no n8n activation, no cron/webhook triggers.

**Deferred (slice 8 — outside umbrella closure):** `linkedin-publication-integration` — LinkedIn API publish when schedule matures; propose as a **new follow-up OpenSpec change** after this umbrella is archived.

### Prior Gaps (resolved by Flow A Core)

The following gaps existed before child slice implementation and are now addressed:
- ~~No automated editorial validation gate for Flow A pre-approval policy.~~ → **Resolved** (slice 3)
- ~~Blog publishing is operator-invoked CLI, not worker HTTP endpoint or n8n-orchestrated.~~ → **Resolved** (slice 4 + 7)
- ~~Public URL is derived (expected), not publish-confirmed after GitHub Pages apply.~~ → **Resolved** (slice 4)
- ~~LinkedIn generation produces single drafts per call, not a coordinated derivative package with distribution strategy.~~ → **Resolved** (slice 5)
- ~~No scheduling model for staggered LinkedIn publication.~~ → **Resolved** (slice 6)
- ~~No lifecycle metadata tying blog publish, derivative package, and scheduled posts together.~~ → **Resolved** (slice 2)
- ~~No idempotency/duplicate-prevention across re-runs.~~ → **Resolved** (slice 2 + worker endpoints)
- ~~No canonical editorial artifact file operationalized for worker/prompt consumption.~~ → **Resolved** (slice 1)

**Remaining gap (slice 8 — deferred follow-up change):**

- LinkedIn API publication when scheduled slots mature (`linkedin-publication-integration`; propose as new OpenSpec change after umbrella archive)

### Stakeholders and Constraints

- **Author/operator**: Places user-written blog posts in `blog-posts/ready/`; expects automatic pipeline after validation.
- **n8n**: Orchestrates HTTP calls only; no filesystem or LLM access (ADR-0001).
- **Worker**: Owns filesystem I/O, path validation, LLM calls, metadata writes, file moves.
- **Reviewer (Flow B only)**: Human approval for system-generated content; not required for Flow A after validation.
- **Blog post is canonical** (ADR-0002); LinkedIn posts are distribution derivatives.

## Goals / Non-Goals

**Goals:**

- Define Flow A end-to-end lifecycle and state machine.
- Distinguish Flow A (automatic after validation) from Flow B (review required, deferred).
- Specify canonical editorial artifact requirements at `content-strategy/silverman-editorial-system.md`.
- Define LinkedIn derivative package model and digital distribution strategy dimensions.
- Decompose implementation into child OpenSpec changes with dependency order.
- Define metadata, idempotency, error handling, and success criteria.
- Preserve HTTP-only n8n orchestration and worker as filesystem/LLM boundary.

**Non-Goals:**

- Implementing any of the above in this umbrella change.
- Flow B implementation (idea generation, draft review queues, approval workflows).
- n8n Execute Command, SSH, filesystem nodes, direct LLM calls from n8n.
- Runtime LinkedIn API integration in this umbrella (Flow A policy allows automatic LinkedIn publication after validation and scheduling; API publish deferred to `linkedin-publication-integration`).
- Creating `content-strategy/silverman-editorial-system.md` content now.
- Modifying production n8n workflow JSON or worker code.

## Flow A vs Flow B Policy

| Dimension | Flow A | Flow B |
|-----------|--------|--------|
| Content source | User-provided blog post in `blog-posts/ready/` | System-generated ideas/drafts |
| Pre-approval | Automated editorial validation passes → treated as pre-approved | Not pre-approved |
| Blog publish | Automatic after validation | Requires human review before publish |
| LinkedIn derivatives | Automatic generation after blog publish + confirmed URL | Requires human review before publish |
| LinkedIn scheduling | Automatic per distribution strategy (variants staggered, not simultaneous) | Requires approval per post or package |
| LinkedIn API publish | Automatic per schedule when `linkedin-publication-integration` is implemented; until then scheduling metadata and drafts only | Requires approval before API publish |
| Human gate | None after validation | Mandatory review/approval |
| Implementation | In scope via child changes | Reserved; out of scope now |

Flow A MUST NOT bypass Flow B approval requirements when content is system-generated. Flow B MUST NOT be conflated with Flow A even if folder paths overlap in the future.

**LinkedIn publication policy vs technical integration:** Flow A *policy* allows automatic LinkedIn publication after validation and distribution scheduling—variants are scheduled according to strategy, not published all at once. The roadmap first implements derivative package generation and scheduling metadata (`publish_state` `pending`). Actual LinkedIn API publication remains deferred to `linkedin-publication-integration` until credentials, API surface, and rate-limit constraints are documented.

## Slug Terminology

Flow A validation and publishing MUST distinguish `source_slug` from `public_slug`:

| Term | Definition |
|------|------------|
| `source_slug` | Basename of the ready Markdown file without `.md`; MAY include a leading numeric ordering prefix (e.g. `01-`, `02-`, `003-`). |
| `public_slug` | Published slug after stripping a leading numeric ordering prefix matching `^\d+-` when present; used for `_posts/`, `assets/images/`, and public URLs. |

**Canonical example:**

| Field | Value |
|-------|-------|
| Source file | `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` |
| `source_slug` | `01-why-i-did-not-start-with-the-database` |
| `public_slug` | `why-i-did-not-start-with-the-database` |
| Public URL | `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/` |

Flow A validation MUST verify:

1. `source_slug` is safe as an input filename (lowercase alphanumeric segments separated by hyphens; no path separators or `..`).
2. Derived `public_slug` matches `^[a-z0-9]+(?:-[a-z0-9]+)*$`.

Prefix stripping rules align with `openspec/specs/github-pages-blog-publishing/spec.md`.

## Flow A Lifecycle

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                           FLOW A LIFECYCLE                                        │
└──────────────────────────────────────────────────────────────────────────────────┘

 [User]
    │
    │  writes blog post + image; places in blog-posts/ready/
    ▼
 blog-posts/ready/<source-slug>.{md,png}
    │
    │  n8n trigger (manual or scheduled) → worker HTTP
    ▼
 ┌─────────────────────┐
 │ 1. VALIDATE         │  editorial validation (structure, frontmatter, slugs, canon rules)
 │    (automated)      │  fail → move to blog-posts/error/ or mark error per lifecycle child spec
 └──────────┬──────────┘
            │ pass (Flow A pre-approved)
            ▼
 ┌─────────────────────┐
 │ 2. PUBLISH BLOG     │  worker HTTP wraps GitHub Pages bridge (--apply)
 │    (idempotent)     │  skip if already published for source-slug + date
 └──────────┬──────────┘
            │
            ▼
 ┌─────────────────────┐
 │ 3. CONFIRM URL      │  publish-confirmed source_public_url in metadata
 │                     │  (not merely derived-from-frontmatter)
 └──────────┬──────────┘
            │
            ▼
 ┌─────────────────────┐
 │ 4. GENERATE         │  one or more LinkedIn variants per editorial canon
 │    DERIVATIVE       │  linked package ID in metadata/campaigns/
 │    PACKAGE          │  drafts → linkedin-posts/review/ or flow-a auto path
 └──────────┬──────────┘
            │
            ▼
 ┌─────────────────────┐
 │ 5. SCHEDULE /       │  cadence, audience, variant, CTA, non-redundancy
 │    DISTRIBUTE       │  NOT all variants at once
 │    (strategy)       │  scheduling metadata per derivative post
 └──────────┬──────────┘
            │
            ▼
 ┌─────────────────────┐
 │ 6. PUBLISH LINKEDIN │  deferred slice: linkedin-publication-integration
 │    (per schedule)   │  policy: automatic when API ready; NOT immediate on generation
 │                     │  idempotent per blog+variant+schedule slot
 └──────────┬──────────┘
            │
            ▼
 ┌─────────────────────┐
 │ 7. LIFECYCLE CLOSE  │  source moved or marked processed per lifecycle child spec
 │    + METADATA       │  traceability without full content in metadata
 └─────────────────────┘
```

### Lifecycle States (per blog post campaign)

| State | Meaning |
|-------|---------|
| `ready` | File in `blog-posts/ready/`, not yet validated |
| `validation_failed` | Failed automated checks; moved to `blog-posts/error/` or marked error per lifecycle child spec |
| `validated` | Passed Flow A validation; eligible for publish |
| `blog_publish_pending` | Publish requested/in progress |
| `blog_published` | GitHub Pages assets written; URL confirmed |
| `derivatives_pending` | Blog live; package generation not started or in progress |
| `derivatives_generated` | LinkedIn package created; scheduling may be pending |
| `distribution_scheduled` | Each derivative has schedule slot per strategy |
| `distribution_complete` | All scheduled derivatives published or terminal |
| `flow_a_complete` | Lifecycle closed; source moved or marked processed per lifecycle child spec |
| `error` | Unrecoverable failure with visible error context |

States SHALL be recorded in `metadata/campaigns/<campaign-id>.json` (exact schema defined in child change `flow-a-lifecycle-and-duplicate-prevention`).

### Error Handling

- Validation failures: move source to `blog-posts/error/` or mark as error according to the lifecycle child spec; write error metadata; do not publish or generate derivatives.
- Blog publish failures: remain in `ready/` or move/mark error per lifecycle child spec; record failure reason; no derivative generation.
- Partial derivative generation: record which variants succeeded; allow idempotent retry for missing variants.
- URL confirmation failure: do not pass derived-only URL as publish-confirmed; block derivative CTA that depends on live URL.
- n8n branches on worker `status` field (`completed` / `failed`) at each step.

### Idempotency and Duplicate Prevention

- **Blog publish**: Key on `source_slug` + `public_slug` + `publication_date`; refuse overwrite (existing CLI behavior); worker endpoint returns `already_published` without re-writing.
- **LinkedIn draft generation**: Key on `source_content_sha256` + `variant` + `flow` (`flow_a`); skip or return existing draft path if unchanged.
- **LinkedIn publication**: Key on `campaign_id` + `variant` + `scheduled_at` slot; prevent duplicate posts for same blog/variant.
- **Re-runs**: Safe to re-trigger n8n workflow; worker returns structured skip/already-done responses.

## Canonical Editorial Artifact

**Intended path:** `content-strategy/silverman-editorial-system.md`

**Purpose:** Single operational document read by worker validation, LLM prompt assembly, and distribution strategy logic. Not decorative marketing copy—specific rules the system can enforce or inject.

**Required sections (to be authored in child change `editorial-canon-and-linkedin-distribution-strategy`):**

1. Brand positioning (Solutions Architect; remote senior roles; AI/architecture/governance themes)
2. Target audiences (recruiters, C-level, technical leadership) with lens per variant
3. Content pillars and topic boundaries
4. Goals (short-term recruiter attraction; long-term thought leadership)
5. Writing style rules (practical, senior, executive-friendly, English primary)
6. Anti-AI-writing rules (applied strongly to generated LinkedIn derivatives and Flow B content; for user-provided blog input, automatable checks MAY warn rather than block unless a child spec marks a rule as blocking—the system cannot perfectly detect AI writing)
7. Blog rules (frontmatter requirements, slug conventions, forbidden content types)
8. LinkedIn derivative rules (minimum variants, fidelity to blog, length/emphasis per variant)
9. CTA rules (when to include blog URL, tone of CTA, no engagement bait)
10. No-redundancy rules (variants must differ in angle; staggered posts must not repeat hooks)
11. LinkedIn cadence/distribution strategy (spacing between variants, audience timing, objectives)
12. Automatic vs approval-required policy (Flow A vs Flow B explicit table)

Worker and prompts MUST load applicable sections. Validation MUST reference blog and LinkedIn rules. For Flow A user-provided blog input, validation blocks only reliably automatable structural and editorial contract violations; anti-AI-writing rules apply strongly at LinkedIn generation time.

## LinkedIn Derivative Package Model

A **derivative package** is the set of one or more LinkedIn posts linked to a single source blog post via `campaign_id`.

| Field | Purpose |
|-------|---------|
| `campaign_id` | Stable ID for blog post + flow |
| `source_slug` | Editorial source basename (may include ordering prefix, e.g. `01-...`) |
| `public_slug` | Published slug after prefix strip (e.g. `why-i-did-not-start-with-the-database`) |
| `source_content_sha256` | Content fingerprint |
| `source_public_url` | Publish-confirmed blog URL |
| `flow` | `flow_a` or `flow_b` |
| `variants[]` | List of derivative posts with `variant`, `audience`, `objective`, `cta_mode`, `draft_path`, `scheduled_at_utc` (umbrella legacy name: `schedule_at`), `publish_state` |

Distribution strategy (expert digital strategist role for the system):

- **Cadence**: Minimum spacing between variants (e.g., 3–7 days); not same-day unless strategy explicitly allows.
- **Audience**: Match variant to audience lens (executive vs technical).
- **Objective**: Awareness, credibility, engagement—one primary objective per scheduled post.
- **Variant**: executive / technical / short provocative (minimum three over campaign lifetime unless canon narrows).
- **CTA behavior**: Include publish-confirmed blog URL when live; omit when URL not confirmed.
- **Non-redundancy**: No duplicate hooks or overlapping thesis across scheduled variants.
- **Scheduling window**: Preferred days/times (defined in editorial canon).

## Target Architecture

```
┌────────────┐     HTTP only      ┌─────────────────────────────────────────┐
│    n8n     │ ─────────────────► │              Worker                      │
│ (orchestr.)│                      │  - validation                            │
└────────────┘                      │  - blog publish (CLI bridge)             │
                                    │  - URL confirmation                      │
                                    │  - derivative package generation         │
                                    │  - scheduling metadata                   │
                                    │  - filesystem + LLM boundary             │
                                    └──────────────┬──────────────────────────┘
                                                   │
                    ┌──────────────────────────────┼──────────────────────────────┐
                    ▼                              ▼                              ▼
           blog-posts/{ready,           linkedin-posts/{review,          metadata/{campaigns,
           processed,error}/             approved,published}/              runs,backups}/
                    │                              │
                    ▼                              ▼
           content-strategy/              Public blog repo checkout
           silverman-editorial-system.md  (silverberdi.github.io)
```

### Future Worker Endpoints (child changes)

| Capability / endpoint | Child Change | Purpose |
|----------|--------------|---------|
| Validation library/module (`ready_post_validation.py`; HTTP deferred) | `ready-post-editorial-validation` | Flow A automated validation gate; HTTP exposure deferred to orchestration slice |
| `POST /publish-blog-post` | `worker-blog-publishing-endpoint` | HTTP wrapper for GitHub Pages bridge |
| `POST /generate-linkedin-package` | `linkedin-derivative-package-generation` | Multi-variant package generation |
| `POST /schedule-linkedin-distribution` | `linkedin-distribution-scheduling-model` | Apply distribution strategy metadata |
| (TBD) | `linkedin-publication-integration` | LinkedIn API publish when constraints clear |

Existing endpoints remain: `/health`, `/process-ready`, `/process-file`, `/generate-linkedin-draft` (may be composed by package endpoint).

## Child Changes / Slices

Dependency order (each is a separate OpenSpec change; cite this umbrella):

```
flow-a-automatic-blog-linkedin-publishing-roadmap (this umbrella)
    │
    ├── 1. editorial-canon-and-linkedin-distribution-strategy
    │       Create content-strategy/silverman-editorial-system.md
    │
    ├── 2. flow-a-lifecycle-and-duplicate-prevention
    │       Depends: 1
    │       Campaign metadata schema, state machine, idempotency keys (foundational)
    │
    ├── 3. ready-post-editorial-validation
    │       Depends: 1, 2 (closely with lifecycle; may develop in parallel)
    │       Library module `validate_ready_post()`; source_slug + public_slug validation; HTTP deferred
    │
    ├── 4. worker-blog-publishing-endpoint
    │       Depends: 1, 2 (slug/URL rules)
    │       POST /publish-blog-post; idempotent; returns confirmed URL
    │
    ├── 5. linkedin-derivative-package-generation
    │       Depends: 1, 2, 4
    │       Multi-variant package; uses confirmed URL + canon
    │
    ├── 6. linkedin-distribution-scheduling-model
    │       Depends: 1, 2, 5
    │       Strategy application; schedule metadata; non-redundancy; publish_state pending
    │
    ├── 7. n8n-flow-a-blog-publish-orchestration
    │       Depends: 3, 4, 5, 6
    │       Extended workflow: validate → publish → package → schedule
    │
    ├── OV. flow-a-deployment-readiness-and-smoke-test (operational verification)
    │       Depends: 7
    │       Deployment readiness + phased smoke test; blocks umbrella archive
    │
    └── 8. linkedin-publication-integration (deferred — follow-up change)
            Depends: 6 + integration constraints
            LinkedIn API; automatic publish per schedule when credentials/API known
            NOT part of umbrella closure; propose after umbrella archive
```

Slice 2 (lifecycle/idempotency) is foundational and SHOULD precede or run closely with slice 3 (validation). Slices 1–4 can partially overlap after umbrella planning approval. Slice 7 integrates prior slices. Slice 8 is a **separate follow-up change** after umbrella archive.

### Roadmap progress (Flow A Core Complete — 2026-07)

| # | Child change | Status | Notes |
|---|--------------|--------|-------|
| 1 | `editorial-canon-and-linkedin-distribution-strategy` | **completed** (archived) | Canonical spec `openspec/specs/editorial-canon/spec.md`; artifact `content-strategy/silverman-editorial-system.md`; commit `ae3eb43` |
| 2 | `flow-a-lifecycle-and-duplicate-prevention` | **completed** (archived) | Canonical spec `openspec/specs/flow-a-lifecycle/spec.md`; worker `campaign_lifecycle.py`; commit `aa48e6c` |
| 3 | `ready-post-editorial-validation` | **completed** (archived) | Canonical spec `openspec/specs/ready-post-editorial-validation/spec.md`; worker `ready_post_validation.py`; tests `tests/test_ready_post_validation.py` |
| 4 | `worker-blog-publishing-endpoint` | **completed** (archived) | Canonical spec `openspec/specs/worker-blog-publishing-endpoint/spec.md`; endpoint `POST /publish-blog-post`; commit `c9a0cb2` |
| 5 | `linkedin-derivative-package-generation` | **completed** (archived) | Canonical spec `openspec/specs/linkedin-derivative-package-generation/spec.md`; endpoint `POST /generate-linkedin-package`; commit archived |
| 6 | `linkedin-distribution-scheduling-model` | **completed** (archived) | Canonical spec `openspec/specs/linkedin-distribution-scheduling-model/spec.md`; endpoint `POST /schedule-linkedin-distribution`; commit `53708eb` |
| 7 | `n8n-flow-a-blog-publish-orchestration` | **completed** (archived) | Canonical spec `openspec/specs/n8n-flow-a-blog-publish-orchestration/spec.md`; workflow inactive, 26 nodes; commit `962ba2f` |
| — | `flow-a-deployment-readiness-and-smoke-test` | **completed** (archived) | Canonical spec `openspec/specs/flow-a-deployment-readiness-and-smoke-test/spec.md`; worker smoke + evidence collector; commit `1457af0` |
| 8 | `linkedin-publication-integration` | **deferred** (follow-up change) | LinkedIn API publish; NOT part of umbrella closure |

**Flow A Core is complete and operationally verified.** All in-scope child changes (slices 1–7 + operational verification) are archived. The umbrella is **ready to archive**. Slice 8 remains **deferred** to a new follow-up OpenSpec change.

## Umbrella Lifecycle

This umbrella was a **long-running active roadmap change**. As of 2026-07, Flow A Core closure criteria are met.

| Phase | Umbrella status |
|-------|-----------------|
| Planning artifacts approved (tasks 1.1–1.4) | **Complete** |
| Child changes 1–7 implemented and archived | **Complete** |
| Operational verification archived (`flow-a-deployment-readiness-and-smoke-test`, commit `1457af0`) | **Complete** |
| Ubuntu server end-to-end verification (worker smoke + evidence collector `OVERALL: PASS`) | **Complete** |
| Slice 8 (`linkedin-publication-integration`) | **Deferred** — new follow-up change, not umbrella closure scope |
| **Current status** | **Ready to archive** via `/opsx-archive flow-a-automatic-blog-linkedin-publishing-roadmap` |

Rules:

- The umbrella **remained active** while child changes were proposed, applied, and archived.
- Each Flow A child change **referenced** this umbrella for policy and lifecycle context.
- Archive the umbrella **after** Flow A Core child changes and operational verification are completed/validated (slices 1–7 + OV archived). Slice 8 is **not** required for umbrella archive.
- Do **not** activate n8n, add cron/webhook triggers, or implement LinkedIn API publication as part of umbrella closure.

## Success Criteria (Flow A Core Complete)

When all in-scope child changes (slices 1–7 + operational verification) are implemented, archived, and server-validated:

1. User places one valid blog post (+ PNG) in `blog-posts/ready/`.
2. System validates against editorial canon; rejects invalid posts visibly.
3. System publishes blog to GitHub Pages checkout idempotently (with safe reconciliation when public artifacts already exist).
4. System confirms and records public URL.
5. System generates LinkedIn derivative package (one or more variants) under `linkedin-posts/generated/`.
6. System schedules variants per distribution strategy with `publish_state: pending` (not all at once).
7. System records complete metadata without storing full markdown/draft bodies.
8. Final campaign state reaches `distribution_scheduled`.
9. Re-run does not duplicate blog publish or LinkedIn drafts for same variant.
10. Errors at any step are visible in metadata and worker/n8n execution output.
11. Flow B content cannot enter Flow A automatic path without explicit policy violation.
12. Worker smoke and evidence collector report `OVERALL: PASS` on Ubuntu server.
13. n8n workflow export remains `"active": false` (no cron/webhook/scheduled trigger).

**Flow A Core stops here.** LinkedIn API automatic publication is **deferred** to `linkedin-publication-integration` (slice 8), a separate follow-up OpenSpec change proposed after this umbrella is archived.

## Decisions

### D1: Umbrella spec only; no modification of existing specs in this change

**Decision:** Introduce `flow-a-automatic-publishing` as a new target spec; child changes carry deltas to `n8n-worker-orchestration-flow`, `github-pages-blog-publishing`, `deepseek-linkedin-draft-generation`, etc.

**Rationale:** Avoids premature requirement changes before slice design; keeps umbrella stable as reference.

**Alternatives:** Modify n8n spec now — rejected; would mix planning with premature implementation commitments.

### D2: Worker HTTP endpoint for blog publish (not n8n CLI)

**Decision:** Wrap existing GitHub Pages CLI bridge in `POST /publish-blog-post` in a child change.

**Rationale:** ADR-0001 — n8n must not Execute Command; worker already owns filesystem boundary.

**Alternatives:** Operator-only CLI — rejected for Flow A automation goal.

### D3: Publish-confirmed URL distinct from derived URL

**Decision:** After successful blog publish, worker returns and metadata stores `source_public_url` as publish-confirmed; n8n may still derive expected URL pre-publish for dry-run only.

**Rationale:** LinkedIn CTAs must not point at non-live URLs; current workflow derives expected URL only.

### D4: Derivative package is metadata-first, staggered publication

**Decision:** Generate all variants in a package but schedule publication separately per distribution strategy. LinkedIn API publish is deferred; until `linkedin-publication-integration`, variants have `publish_state` `pending`.

**Rationale:** Flow A policy allows automatic LinkedIn publication after scheduling, but "one or more" does not mean simultaneous publish. Technical API integration follows scheduling model.

### D5: Flow A skips `linkedin-posts/review/` human gate

**Decision:** Flow A drafts may write directly to an auto-approved path (e.g., `linkedin-posts/approved/` or dedicated `flow-a/` subfolder — finalized in child change) after validation + canon compliance checks.

**Rationale:** Flow A policy = no manual approval after validation.

**Alternatives:** Keep review folder — conflicts with Flow A automatic policy.

### D6: Editorial canon as Markdown file, not database

**Decision:** `content-strategy/silverman-editorial-system.md` versioned in repo; worker reads at runtime.

**Rationale:** Git-reviewed, prompt-friendly, no new infrastructure.

### D7: n8n workflow remains `active: false` until scheduling change explicitly activates

**Decision:** Child n8n changes keep export inactive unless a later operational change enables cron.

**Rationale:** Guardrail from existing n8n spec; prevents accidental production runs.

### D8: Umbrella remains active during child-change execution; ready to archive after Flow A Core

**Decision:** Keep `flow-a-automatic-blog-linkedin-publishing-roadmap` active while Flow A child changes execute. Archive after Flow A Core (slices 1–7 + operational verification) is complete and server-validated. Slice 8 is deferred to a follow-up change.

**Rationale:** Child changes cite the umbrella for policy, lifecycle, and dependency order. As of 2026-07, Flow A Core criteria are met and the umbrella is ready to archive.

**Alternatives:** Archive after planning sign-off — rejected; contradicts multi-slice roadmap methodology. Include slice 8 in umbrella closure — rejected; LinkedIn API constraints not yet documented.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Flow A auto-publish publishes low-quality content | Automated validation blocks structural/contract violations; anti-AI rules enforced strongly on generated LinkedIn content, not claimed perfect detection on user blog input |
| Idempotency gaps cause duplicate LinkedIn posts | Explicit keys in lifecycle child change; worker returns `already_*` statuses |
| Editorial canon too vague to operationalize | Child change 1 requires specific enforceable rules, not prose-only |
| LinkedIn API integration unknown | Defer slice 8; scheduling model works without API |
| Confusion between Flow A and Flow B paths | Explicit `flow` field in metadata; Flow B child changes separate later |
| Git push still manual after CLI apply | Child change 3 documents whether worker triggers push or operator remains in loop |

## Migration Plan

Flow A Core rollout is complete. Migration notes for operators:

1. Child changes 1–7 and operational verification are implemented, archived, and server-validated.
2. Use `deploy/server/run-flow-a-worker-smoke.sh` as diagnostic source of truth before manual n8n runs.
3. n8n workflow remains `"active": false`; manual trigger only until a future operational change explicitly enables scheduling.
4. LinkedIn API integration (`linkedin-publication-integration`) is a **separate follow-up change** — propose after umbrella archive.
5. Archive this umbrella via `/opsx-archive flow-a-automatic-blog-linkedin-publishing-roadmap`.

Rollback: disable n8n workflow; worker endpoints remain backward-compatible; Flow A metadata states allow identifying in-flight campaigns.

## Open Questions (deferred to slice 8 follow-up change)

1. LinkedIn API provider, credentials storage, and rate-limit policy for `linkedin-publication-integration`
2. Exact n8n workflow extension for API publish when schedule matures
3. Cron schedule for Flow A n8n trigger (polling `ready/` vs webhook) — remains inactive until explicitly enabled
4. Should `POST /process-ready` semantics change for Flow A (move to processed after full lifecycle vs after blog publish only)?

**Resolved during Flow A Core:**

- Blog publish remains local-checkout-only with separate operator git push (no automatic git push in worker).
- Flow A LinkedIn drafts write to `linkedin-posts/generated/` per child slice 5.
