## Why

US-079 is implemented and deployed: authenticated `POST /flow-b/generate-blog-drafts` writes Markdown + PNG + `.flow-b.json` under `blog-posts/pending-approval/` only. Operators still have no Silverman Authority Manager surface to review those packages and gate quality with approve/reject. US-080 is the next apply-order step so the mandatory blog gate exists before US-081 promotion to `ready/` and Flow A.

## Goals

- Extend **Silverman Authority Manager** (not a separate Flow B-only app) to present pending drafts from `blog-posts/pending-approval/` (title/topic, body, image, discovery summary; gap week / empty-days when present).
- Support **approve** and **reject** operator actions via authenticated worker HTTP (ADR-0001).
- Reject clearly; rejected drafts MUST remain non-publishable (MUST NOT promote to `blog-posts/ready/`).
- Approve records the operator decision for handoff to US-081; this change MUST NOT promote/move to `ready/` or apply spill algorithm A.
- No revision-history CMS, structured multi-round feedback capture, or mandatory edit-apply loop (operator MAY edit files offline; out of band).
- Communicate rejected/blocked and other failure states clearly in UI and HTTP.
- Update CURRENT-STATE as **implemented** (not Story accepted without operator walkthrough); do **not** close BL-018.

## Non-goals

- US-081 promote `pending-approval/` → `ready/` + spill algorithm A (record promotion + move).
- US-082 gap trigger orchestration.
- Auto-publish blog or LinkedIn; Flow A publish/package/schedule; LinkedIn API publish.
- Closing BL-017 or BL-018; marking US-080 Story accepted without operator walkthrough.
- Re-implementing US-076–US-079 generation/detect/settings contracts.
- A separate Flow B-only application or mini-CMS of revision threads.

## What Changes

- Add authenticated worker HTTP to **list/read** pending Flow B drafts from `blog-posts/pending-approval/` (pair + sidecar fields needed for presentation).
- Add authenticated **reject** action that marks the draft rejected/blocked, keeps it non-publishable, and MUST NOT write or move into `blog-posts/ready/`.
- Add authenticated **approve** action that records the operator approve decision (durable sidecar metadata) and returns a clear handoff that promotion to `ready/` is owned by US-081 — MUST NOT promote/move pairs or invoke Flow A / LinkedIn publish.
- Extend Silverman Authority Manager UI to present pending drafts and expose approve/reject with clear rejected/blocked and error communication.
- Update ops / CURRENT-STATE / Flow B policy cross-links so approve/reject presentation is recorded as implemented (not Story accepted); BL-018 remains open.
- Tests covering list/present payload, approve decision without `ready/` writes, reject non-publishable invariant, auth, and UI/API failure communication (no real external publish calls).

## Capabilities

### New Capabilities

- `flow-b-blog-draft-approval`: Authenticated worker + Silverman Authority Manager presentation of `blog-posts/pending-approval/` drafts (title/topic, body, image, discovery summary, optional gap context); approve and reject actions; reject remains non-publishable; approve records decision without promote/move to `ready/`; no revision CMS or mandatory edit-apply loop; fail-closed operator-visible errors; no Flow A / LinkedIn publish side effects.

### Modified Capabilities

- `flow-b-simplified-process`: Cross-link that US-080 runtime approve/reject presentation now exists as a separate capability (policy process boundary unchanged; docs MUST NOT claim promote/spill/trigger implemented).
- `flow-b-blog-draft-generation`: Clarify that generated `pending-approval/` packages (including `.flow-b.json` sidecar fields) are the read/update surface for US-080 list/approve/reject; generation contracts unchanged.

## Impact

- **Code:** New Flow B pending-draft approval module(s); thin FastAPI routes under `/flow-b/…`; Authority Manager frontend extension (same console package as Gap settings / LinkedIn supervision); tests for list/approve/reject invariants.
- **APIs:** New authenticated Flow B endpoints for list/detail and approve/reject; existing `generate-blog-drafts`, `discover-topics`, `calendar-gaps`, and settings GET/PUT unchanged; no promote/trigger routes.
- **Deps:** Filesystem `pending-approval/` + existing sidecar shape from US-079; same worker API-key auth; no new mandatory external services.
- **Ops:** CURRENT-STATE + Flow B policy note that approve/reject presentation is implemented; Story accepted / BL-018 close remain operator gates.
- **Product:** **BL-018 / US-080** primary (present + approve/reject). Does not close BL-018; does not implement US-081–US-082.
- **Acceptance criteria addressed (US-080):** Present pending drafts in Authority Manager; approve and reject actions; no revision CMS / multi-round feedback / mandatory edit-apply; rejected non-publishable; outcome and failures communicated; no unintended duplication of US-076–US-079.
- **Acceptance criteria excluded / deferred:** Operator walkthrough Story accepted gate; US-081 promote + spill A; US-082 gap trigger; LinkedIn API publish; closing BL-018.

## Related backlog / stories

| ID | Role |
|----|------|
| **BL-018 / US-080** | Primary — present Flow B blog drafts for approve or reject |
| US-079 | Prerequisite — drafts in `pending-approval/` (deployed) |
| US-078 | Prerequisite — discovery summary fields in sidecar |
| US-076 / US-077 | Prerequisite — gap week / empty-days context when present |
| US-074 / US-075 / BL-016 | Prerequisite policy (Story accepted; closed) |
| US-081 | Later — promote to `ready/` + spill A (out of scope) |
| US-082 | Later — gap trigger (out of scope) |
