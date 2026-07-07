## Context

### Current State

The Silverman Blog LinkedIn automation system runs as an HTTP worker on an Ubuntu server, orchestrated by n8n over HTTP only (ADR-0001). Implemented capabilities include:

| Component | Status |
|-----------|--------|
| `GET /health` | Implemented |
| `POST /process-ready` | Implemented — scans `blog-posts/ready/` |
| `POST /process-file` | Implemented — reads one ready Markdown post |
| `POST /generate-linkedin-draft` | Implemented — generates one LinkedIn draft variant |
| GitHub Pages publishing bridge | Implemented as CLI/domain capability (dry-run default, `--apply` required) |
| n8n draft-generation workflow | Implemented — manual trigger, health → process-ready → process-file → compute URL → generate draft |
| Public blog URL in LinkedIn drafts | Implemented — `source_public_url` derived per post |

Gaps for Flow A completion:

- No automated editorial validation gate for Flow A pre-approval policy.
- Blog publishing is operator-invoked CLI, not worker HTTP endpoint or n8n-orchestrated.
- Public URL is derived (expected), not publish-confirmed after GitHub Pages apply.
- LinkedIn generation produces single drafts per call, not a coordinated derivative package with distribution strategy.
- No scheduling model for staggered LinkedIn publication.
- No lifecycle metadata tying blog publish, derivative package, and scheduled posts together.
- No idempotency/duplicate-prevention across re-runs.
- No canonical editorial artifact file operationalized for worker/prompt consumption.

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
| `variants[]` | List of derivative posts with `variant`, `audience`, `objective`, `cta_mode`, `draft_path`, `schedule_at`, `publish_state` |

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
| `POST /schedule-linkedin-package` | `linkedin-distribution-scheduling-model` | Apply distribution strategy metadata |
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
    └── 8. linkedin-publication-integration (deferred)
            Depends: 6 + integration constraints
            LinkedIn API; automatic publish per schedule when credentials/API known
```

Slice 2 (lifecycle/idempotency) is foundational and SHOULD precede or run closely with slice 3 (validation). Slices 1–4 can partially overlap after umbrella planning approval. Slice 7 integrates prior slices. Slice 8 implements API publish only after scheduling model exists and integration constraints are documented.

### Roadmap progress (as of child slice 3 archive)

| # | Child change | Status | Notes |
|---|--------------|--------|-------|
| 1 | `editorial-canon-and-linkedin-distribution-strategy` | **completed** | Archived; canonical spec `openspec/specs/editorial-canon/spec.md`; artifact `content-strategy/silverman-editorial-system.md`; commit `ae3eb43` |
| 2 | `flow-a-lifecycle-and-duplicate-prevention` | **completed** | Archived; canonical spec `openspec/specs/flow-a-lifecycle/spec.md`; worker `campaign_lifecycle.py`; commit `aa48e6c` |
| 3 | `ready-post-editorial-validation` | **completed** | Archived; canonical spec `openspec/specs/ready-post-editorial-validation/spec.md`; worker `src/silverman_blog_linkedin/ready_post_validation.py`; tests `tests/test_ready_post_validation.py` |
| 4 | `worker-blog-publishing-endpoint` | **pending** | — |
| 5 | `linkedin-derivative-package-generation` | **pending** | — |
| 6 | `linkedin-distribution-scheduling-model` | **pending** | — |
| 7 | `n8n-flow-a-blog-publish-orchestration` | **pending** | — |
| 8 | `linkedin-publication-integration` | **deferred** | LinkedIn API publish when integration constraints documented |

The umbrella remains **active**. Slice 3 is archived; slices 4–7 remain pending.

## Umbrella Lifecycle

This umbrella is a **long-running active roadmap change**, not a one-shot planning artifact archived after stakeholder sign-off.

| Phase | Umbrella status |
|-------|-----------------|
| Planning artifacts approved (tasks 1.1–1.4) | **Active** — remains the organizing source of truth |
| Child changes proposed/applied/archived (tasks 2–9) | **Active** — child changes MUST reference this umbrella for policy, lifecycle, and sequencing |
| Flow A child changes complete and validated (through slice 7; slice 8 when applicable) | **Ready to archive** — or when roadmap is intentionally superseded by a replacement change |

Rules:

- The umbrella **remains active** while child changes are proposed, applied, and archived.
- Each Flow A child change **MUST reference** `flow-a-automatic-blog-linkedin-publishing-roadmap` in its proposal for policy and lifecycle context.
- Archive the umbrella **only after** Flow A child changes are completed/validated (sections 2–8 in `tasks.md`, with slice 8 deferred until integration constraints are clear) **or** the roadmap is intentionally superseded.
- Do **not** archive immediately after stakeholder approval of planning artifacts.

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

### D8: Umbrella remains active during child-change execution

**Decision:** Keep `flow-a-automatic-blog-linkedin-publishing-roadmap` as an active OpenSpec change while Flow A child changes are proposed, applied, and archived. Archive only after Flow A completion/validation or intentional roadmap supersession.

**Rationale:** Child changes cite the umbrella for policy, lifecycle, and dependency order. Archiving after planning sign-off would orphan in-flight slices and lose the organizing source of truth mid-implementation.

**Alternatives:** Archive after stakeholder sign-off — rejected; contradicts multi-slice roadmap methodology.

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

This umbrella is planning-only and remains active while child changes execute. Migration for Flow A rollout (future):

1. Keep umbrella active; implement child changes 1–2 (canon, lifecycle/idempotency).
3. Implement child changes 3–4 (validation, publish endpoint); may overlap with step 2.
4. Implement child changes 5–6 (package generation, scheduling metadata).
5. Implement child change 7 (n8n orchestration); test with manual trigger.
6. Enable scheduled trigger only after end-to-end dry-run validation.
7. Implement child change 8 when LinkedIn API integration constraints are documented.
8. Archive umbrella after Flow A child changes are completed/validated or roadmap is superseded.

Rollback: disable n8n workflow; worker endpoints remain backward-compatible; Flow A metadata states allow identifying in-flight campaigns.

## Open Questions

1. Does blog publish child change include `git commit`/`git push` or remain local-checkout-only with separate deploy step?
2. Exact folder for Flow A auto-approved LinkedIn drafts (`approved/` vs dedicated subfolder)?
3. LinkedIn API provider, credentials storage, and rate-limit policy for slice 8?
4. Should `POST /process-ready` semantics change for Flow A (move to processed after full lifecycle vs after blog publish only)?
5. Cron schedule for Flow A n8n trigger (polling `ready/` vs webhook)?

## Success Criteria (Completed Flow A)

When all child changes through slice 7 (and 8 when applicable) are implemented:

1. User places one valid blog post (+ PNG) in `blog-posts/ready/`.
2. System validates against editorial canon; rejects invalid posts visibly.
3. System publishes blog to GitHub Pages checkout idempotently.
4. System confirms and records public URL.
5. System generates LinkedIn derivative package (one or more variants).
6. System schedules variants per distribution strategy (not all at once; `publish_state` `pending` until API slice).
7. System records complete metadata without storing full markdown/draft bodies.
8. Source is moved or marked processed according to the lifecycle child spec when lifecycle closes.
9. Re-run does not duplicate blog publish or LinkedIn posts for same variant.
10. Errors at any step are visible in metadata and n8n execution output.
11. Flow B content cannot enter Flow A automatic path without explicit policy violation.

LinkedIn API automatic publication completes the policy end-state when slice 8 is implemented; until then, success includes scheduling metadata and draft artifacts ready for deferred API publish.
