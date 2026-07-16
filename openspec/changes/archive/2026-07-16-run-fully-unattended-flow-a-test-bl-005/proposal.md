## Why

BL-004 is closed (Flow A n8n identified, activated on schedule, LinkedIn publication independently gated). **BL-005** still open: prove a real approved Markdown post can complete the full Flow A path **without technical intervention**, with operator-visible evidence. Operator has placed two editorial posts and approved live blog side effects; we will demonstrate both a Manual Trigger run and a separate Schedule Trigger run (serialized ready inbox). Closing US-012 / US-013 / US-014 closes BL-005.

## What Changes

- Define and execute an evidence-first unattended Flow A validation for **two serialized posts**:
  - Post A: `05-keep-contracts-boring.md` via **Manual Trigger** (only this file in `blog-posts/ready/`).
  - Post B: `06-search-is-not-one-model.md` via **Schedule Trigger** (placed in ready only after Post A completes; wait for daily 09:00 UTC or next schedule fire).
- Front-matter / ready-gate remediation as required so posts pass editorial validation (current files miss required fields: `layout`, `date`, `categories`, `tags`, `description`, `image`; remove AppleDouble `._*` junk).
- Prefer existing worker + activated n8n path (`silvermanFlowAPublish01`); no new Flow A endpoints; HTTP-only (ADR-0001).
- Capture PASS/PENDING/FAIL evidence under `docs/operations/` for Manual and Schedule runs; update CURRENT-STATE / RUNTIME-STATE / product progress only after demonstrated outcomes.
- LinkedIn API publication remains **out of scope** (Flow A must not call LinkedIn publication endpoints; flag independence preserved per US-011).

## Goals

- Satisfy **US-012**, **US-013**, **US-014** under **BL-005** with two real Flow A executions (Manual + Schedule).
- Demonstrate: accept ready Markdown → image generate/validate → blog publish to live site → LinkedIn package → distribution schedule → source lifecycle → campaign + calendar records → no technical intervention during each run once started.
- Keep outcomes operator-visible; failures/blocked clear; no unintended duplication of completed campaigns.

## Non-Goals

- **BL-006** LinkedIn variant review process definition.
- **BL-007** scheduled LinkedIn API publication / `auto_queue_pending` WIP.
- Flow B draft-generation changes.
- Calendar rewrite to make `execute-flow-a-due` the Flow A n8n body.
- Publishing posts to LinkedIn via API as part of this test.
- Permanently changing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.
- n8n Execute Command.

## Capabilities

### New Capabilities

- `flow-a-unattended-e2e-validation`: Operator and system requirements for proving fully unattended Flow A with real ready content — Manual and Schedule Trigger evidence windows, ready-gate prerequisites, live blog side effects, package/schedule/lifecycle/calendar completion, PASS/PENDING/FAIL ops reporting, and BL-005 closure without claiming LinkedIn API publication or BL-007 (US-012–US-014).

### Modified Capabilities

- `n8n-flow-a-blog-publish-orchestration`: Cross-reference unattended E2E validation; reaffirm Schedule/Manual empty-ready vs real-ready behavior and that success through schedule does not require LinkedIn publication enablement.
- `flow-a-n8n-workflow-activation`: Clarify that activation (US-010) is prerequisite evidence owner remains separate from BL-005 unattended E2E closure via `flow-a-unattended-e2e-validation`.

## Impact

- **Ops evidence:** New `docs/operations/bl-005-unattended-flow-a-validation-YYYY-MM-DD.md` (Manual + Schedule sections).
- **Editorial filesystem:** Temporary ready-folder serialization; front-matter remediation on two posts; AppleDouble cleanup; live writes to public blog checkout + git push when enabled; campaign/calendar metadata.
- **n8n:** Manual Trigger execution + natural Schedule fire; no workflow redesign expected.
- **Worker:** Reuse existing Flow A HTTP endpoints; ComfyUI if image remediation required; no new routes expected.
- **Product:** Close US-012–US-014 / BL-005 only after both runs demonstrate ACs; leave BL-006/BL-007 open.

## Acceptance criteria addressed

| Story | AC covered by this change |
|-------|---------------------------|
| **US-012** | Ready accept; image generate/validate; publish to live site; visible outcomes; clear failures; no unintended change |
| **US-013** | LinkedIn variants/package; schedule distribution; source lifecycle; visible outcomes; clear failures; no unintended change |
| **US-014** | Campaign + calendar records; no technical intervention during execution once started; visible outcomes; clear failures |

## Acceptance criteria intentionally excluded

- LinkedIn API real publish of variants (BL-002/BL-007).
- Variant review process policy (BL-006).
- Permanent enablement or disablement of LinkedIn publication flag.
