## Context

US-079 is deployed on `192.168.0.194:8010` (`BUILD_REVISION=c69b603…`): authenticated `POST /flow-b/generate-blog-drafts` writes `.md` + `.png` + sibling `.flow-b.json` under `blog-posts/pending-approval/` with `status: pending_approval` (or `pending_approval_image_failed`), discovery fields (`topic_id`, `thesis`, `referent_positioning`, `rationale`), and optional `target_week` / `empty_days[]`. US-078 discovery, US-076 settings, and US-077 gap detect are also deployed. There is still no operator surface to review those packages or record approve/reject.

Silverman Authority Manager is the existing Vite React console served at `GET /flow-a/console/linkedin-variant-supervision` (package `frontend/linkedin-variant-supervision-console/`), already extended for Flow B Gap settings (US-076). Policy names this surface for Flow B blog approve/reject — not a separate app.

Constraints: ADR-0001 (n8n → worker HTTP only); rejected drafts MUST remain non-publishable; this change MUST NOT promote to `ready/` or apply spill A (US-081); no revision CMS / multi-round feedback / mandatory edit-apply; no Flow A publish/package/schedule or LinkedIn API publish; do not close BL-018 or mark Story accepted without operator walkthrough.

Stakeholders: content operator (review pending AI blogs and gate quality); system operator (authenticated HTTP, clear errors); US-081 implementer (stable approve-decision + draft-id handoff without assuming promote already ran).

## Goals / Non-Goals

**Goals:**

- Authenticated list/read of pending-approval packages for presentation.
- Authority Manager UI showing title/topic, body, image, discovery summary, and gap week / empty-days when present.
- Approve and reject actions via authenticated worker HTTP.
- Reject: durable rejected/blocked state; MUST NOT promote to `ready/`.
- Approve: durable operator decision for US-081 handoff; MUST NOT move pairs to `ready/` or run spill A.
- Clear operator-visible rejected/blocked and failure communication.
- CURRENT-STATE updated as implemented (not Story accepted); BL-018 remains open.

**Non-Goals:**

- Promote/move `pending-approval/` → `ready/` or spill algorithm A (US-081).
- Gap trigger (US-082).
- Revision-history CMS, structured feedback threads, mandatory in-app edit-apply.
- Auto-publish blog/LinkedIn; Flow A lifecycle; LinkedIn API publish.
- Changing US-076–US-079 HTTP contracts except consuming their artifacts/fields.
- Closing BL-017/BL-018 or Story accepted without walkthrough.

## Decisions

### D1 — HTTP surface: list + approve + reject under `/flow-b/`

**Choice:** Authenticated worker routes (names locked for implementers):

| Method | Path | Role |
|--------|------|------|
| `GET` | `/flow-b/pending-approval-drafts` | List pending (and optionally filterable) drafts |
| `GET` | `/flow-b/pending-approval-drafts/{draft_id}` | Detail: body Markdown, image URL, discovery + gap fields |
| `POST` | `/flow-b/pending-approval-drafts/{draft_id}/approve` | Record approve decision; no promote |
| `POST` | `/flow-b/pending-approval-drafts/{draft_id}/reject` | Record reject; remain non-publishable |

`draft_id` = filesystem slug (stem of the pending-approval pair), matching US-079 sidecar `slug` / basename without extension. Path-traversal and escape outside `blog-posts/pending-approval/` MUST fail closed.

List item fields (minimum):

| Field | Source |
|-------|--------|
| `draft_id` / `slug` | Basename |
| `title` | Front matter or thesis fallback |
| `topic_id`, `thesis`, `referent_positioning`, `rationale` | Sidecar |
| `status` | Sidecar (`pending_approval`, `approved`, `rejected`, …) |
| `target_week`, `empty_days` | Sidecar when present |
| `blog_relative_path`, `image_relative_path`, `metadata_relative_path` | Sidecar / pair discovery |
| `image_url` | Authenticated worker asset URL for console display (D4) |
| `generated_at_utc` | Sidecar |

Default list filter: actionable pending statuses (`pending_approval`, `pending_approval_image_failed`); include `status` query for rejected/approved inspection. Empty folder → empty list, not error.

**Why:** Matches Flow B route naming; ADR-0001; clear split from US-081 promote route.

**Alternatives rejected:** Folding into Gap settings modal (wrong job); filesystem-only UI without HTTP (breaks n8n/console auth pattern); promote-on-approve in this change (US-081).

### D2 — Approve records decision only; promote is US-081

**Choice:** `POST …/approve`:

1. Validate draft exists under `pending-approval/` and is in an approvable status (`pending_approval` or operator-visible `pending_approval_image_failed` — document whether image-failed is approvable; **prefer allow with clear warning** so operator can still gate text, US-081 may still require pair completeness).
2. Update sibling `.flow-b.json` atomically: `status: approved`, `approved_at_utc`, optional `approved_by` (from request body or auth principal label if available; otherwise `"operator"` / omitted with documented default).
3. MUST NOT move `.md`/`.png`/sidecar to `blog-posts/ready/`.
4. MUST NOT invoke Flow A publish/package/schedule, Git handoff, or LinkedIn API publish.
5. Response: `status: approved`, `promotion_pending: true`, `promoted: false`, paths unchanged under `pending-approval/`, operator-visible note that Flow A eligibility requires US-081 promote.

Idempotent re-approve of already-`approved` draft: return success with same semantics (no double side effects). Approve of `rejected` draft: fail closed with clear code (e.g. `draft_already_rejected`) unless a future story defines reopen.

**Why:** US-080 AC requires support approve; user scope forbids promote/spill (US-081). Recording decision gives a durable handoff without violating eligibility.

### D3 — Reject marks non-publishable; never promote

**Choice:** `POST …/reject`:

1. Update sidecar: `status: rejected`, `rejected_at_utc`, optional `rejection_reason` (free-text optional; **not** a structured multi-round feedback CMS — single optional string only).
2. Keep pair under `pending-approval/` (or a confined subfolder under the same tree if implementers prefer isolation — **prefer stay in place with status** to avoid new lifecycle folders in this change).
3. MUST NOT write or move anything into `blog-posts/ready/`.
4. List default excludes rejected; detail/list-with-filter still shows rejected clearly.
5. UI communicates rejected/blocked state (banner / status chip).

Idempotent re-reject: success. Reject of already-`approved` (decision-only): fail closed or allow override to rejected without promote — **prefer allow reject to supersede approved-but-not-promoted** so operator can reverse a mistaken approve before US-081; document in response.

**Why:** US-080 AC; eligibility policy.

### D4 — Present body + image in Authority Manager

**Choice:**

- Detail API returns full Markdown body (and parsed title) for in-console reading.
- Hero image served via authenticated worker route confined to `pending-approval/` PNGs (e.g. `GET /flow-b/pending-approval-drafts/{draft_id}/image`) — same API-key session as console; no unauthenticated static mount of editorial tree.
- UI: extend existing console — new view or panel (e.g. “Flow B drafts” / pending-approval queue) reachable from AppShell alongside Gap settings; not a separate SPA/deployable.
- Presentation: title/topic, body (readable Markdown render or monospace), image, discovery summary (`thesis`, `referent_positioning`, `rationale`), gap week / empty-days when present.
- Approve / Reject primary actions; optional one-line reject reason; **no** revision history UI, comment threads, or mandatory edit-apply loop. Offline file edit remains out of band.

**Why:** US-080 AC; glossary Authority Manager naming; security (no open editorial static).

### D5 — Sidecar update writer (overwrite)

**Choice:** Extend pending-approval writer helpers to support **atomic overwrite** of existing `.flow-b.json` (US-079 writer uses exclusive create `xb` only). Preserve confinement checks; never touch `ready/`. Prefer write-temp + replace.

**Why:** Approve/reject need durable status updates without rewriting Markdown/PNG.

### D6 — No revision CMS / edit-apply

**Choice:** Spec and UI explicitly omit: revision history, multi-round structured feedback, in-app mandatory edit then re-submit. Operator MAY edit `.md`/`.png` on disk offline; refresh reloads current files. No “apply feedback” workflow in this change.

### D7 — Module and frontend layout

**Choice:**

- `flow_b_blog_draft_approval.py` — list/detail, approve, reject, path confinement, sidecar status updates, response shaping.
- Thin FastAPI routes in `main.py` under `/flow-b/pending-approval-drafts…`.
- Frontend: components under `frontend/linkedin-variant-supervision-console/` (e.g. `FlowBPendingDraftsPanel` / view); API client paths; rebuild static assets into `src/silverman_blog_linkedin/static/linkedin-variant-supervision-console/` per existing console pipeline.
- Tests: `tests/test_flow_b_blog_draft_approval.py` (+ frontend tests mirroring US-076 gap-settings pattern).

### D8 — Auth, secrets, dry-run

**Choice:** Same worker API-key auth as other `/flow-b/*` routes. Never return secrets. Optional `dry_run` on approve/reject: validate and return would-be status **without** durable sidecar mutation (mirror other Flow B dry-run patterns). Default for console mutations: follow existing dry-run default toggle in AppShell.

### D9 — Docs / product status

**Choice:** Update `docs/CURRENT-STATE.md`, Flow B policy approve cross-link, user-story automated AC only where demonstrated. Leave Story accepted unchecked; BL-018 open; US-081–US-082 unchecked. Do not claim promote implemented.

### D10 — Tests

**Choice:** Unit/API (+ focused UI) tests:

- List returns pending drafts with discovery + optional gap fields; empty folder OK.
- Detail returns body + image URL; path traversal rejected.
- Approve updates sidecar to `approved`, leaves files under `pending-approval/`, no `ready/` writes.
- Reject updates sidecar to `rejected`, no `ready/` writes; default list excludes rejected; UI/HTTP communicate rejected.
- Auth required; dry-run does not mutate; no Flow A / LinkedIn publish calls (monkeypatch guards).

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Operators confuse “approved” with Flow A–eligible | Response + UI copy: `promotion_pending`; CURRENT-STATE / policy cross-link US-081 |
| Approve of image-failed drafts | Allow with warning; US-081 can enforce pair completeness |
| Sidecar exclusive-create blocks updates | D5 overwrite helper |
| Serving editorial images without auth | Authenticated image route only |
| Scope creep into promote/spill | Explicit non-goals + tests asserting no `ready/` moves |
| Mini-CMS pressure | Spec forbids revision threads / mandatory edit-apply |

## Migration Plan

1. Implement after explicit `/opsx-apply` approval.
2. `/opsx-verify` → implementation commit → sync → archive (separate commits).
3. Deploy only with explicit approval; rebuild console static assets in worker image.
4. Rollback: revert worker build; sidecar status fields remain backward-compatible for operators (`pending_approval` still valid).

## Open Questions

None blocking. Resolved by AC/proposal:

- Approve in US-080 = decision only; promote = US-081 (D2).
- Reject stays in `pending-approval/` with status (D3).
- Image via authenticated worker route (D4).
- Optional single reject reason string only — not multi-round feedback (D6).
