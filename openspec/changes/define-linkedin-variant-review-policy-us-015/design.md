## Context

BL-005 left Flow A campaigns at `flow_a_complete` / `distribution_scheduled` with LinkedIn variants in `publish_state` `pending`. The blog source is user-provided and pre-reviewed before `blog-posts/ready/`. LinkedIn variants are generated derivatives scheduled per `#linkedin-distribution-strategy` (audience, spacing, `scheduled_at_utc`).

What is missing is the **operator-visible business policy** for:

1. Whether scheduled variants are **expected to publish** per strategy (operator override only).
2. When human review is **mandatory** (Flow B) versus **optional supervision** (Flow A pre-send window).

BL-007 will eventually auto-queue and publish due variants. US-015 defines Flow A policy without implementing automation, console UI, or correction/rejection mechanics (US-016/US-017).

**Operator intent (confirmed):** Flow A is not conservative. The blog is pre-approved; LinkedIn derivatives follow the designed strategy and calendar. Before API send, the operator MAY supervise (edit, delay, cancel) in a future console; if they do not intervene, publication proceeds per schedule. Flow B will require mandatory review — not started.

Constraints: ADR-0001; US-011; no merge of local `auto_queue_pending` WIP; no permanent LinkedIn enablement flip; smallest docs/spec change.

## Goals / Non-Goals

**Goals:**

- Encode explicit defaults: **strategy-driven publication** (all scheduled variants expected to publish unless operator overrides) and **optional supervision window** while variants remain `pending` before API queue/send.
- Define **mandatory review only for Flow B**; Flow A does not require human approval after blog validation for package, schedule, or LinkedIn API publication.
- Publish operator-facing policy document; normatively require it via `linkedin-variant-review-process`.
- Align editorial-canon with Flow A automatic posture.
- Document how BL-007 should treat scheduled, non-cancelled `pending` variants.
- Communicate blocked/deferred states clearly.

**Non-Goals:**

- Operator console UI (deferred).
- Worker metadata for edit/delay/cancel decisions (US-017).
- Quality/differentiation criteria (US-016).
- Changing queue/publish/cancel endpoint behavior.
- BL-007 WIP merge.

## Decisions

### D1 — Policy artifact path

**Decision:** `docs/operations/linkedin-variant-review-policy.md` as operator source of truth for US-015.

### D2 — Strategy-driven publication (not selective-by-default)

**Decision:** Default policy is **publish per distribution strategy**. All variants scheduled by Flow A distribution scheduling are **expected to publish** at their `scheduled_at_utc` (subject to publication enablement and BL-007 automation when implemented).

Operator override is explicit intervention only: **cancel**, **defer/delay**, or **edit** (mechanics deferred to US-017). Absence of operator action does **not** mean “do not publish.”

**Rationale:** Matches operator intent: blog pre-reviewed, strategy already designed, calendar encodes audience and timing. BL-002 left siblings `pending` as controlled smoke choice, not as the default product posture.

**Rejected:** Selective-by-default (subset publish without strategy expectation).

### D3 — When review is mandatory vs optional

**Decision:**

| Flow | Review |
|------|--------|
| **Flow A blog** | Pre-approved by operator (human-authored `ready` post). No additional review after validation. |
| **Flow A package + schedule** | Automatic after validation. No human review required. |
| **Flow A LinkedIn API send** | **Not mandatory.** Optional **supervision window** while variant is `pending` (before queue/API send): operator MAY edit, delay, or cancel. If no intervention, publication proceeds per strategy when automation exists. |
| **Flow B** | **Mandatory** human review before any publish. Deferred implementation. |

**Rationale:** Satisfies US-015 “define when review is mandatory” by distinguishing Flow A (optional supervision) from Flow B (mandatory). Preserves BL-005 unattended Flow A. Does not add a per-variant approval gate before queue.

**Rejected:** Mandatory review before every `pending` → `queued` for Flow A.

### D4 — Supervision window (not approval gate)

**Decision:** While `publish_state` is `pending` and before real LinkedIn API send, the variant is in a **supervision window**: visible on editorial calendar / campaign metadata with `scheduled_at_utc`. Operator may intervene; no `review_state` or console is required in US-015.

Recording edits, delays, and cancellations in metadata or UI is **deferred to US-017**. Future console is noted as the intended supervision surface, not implemented here.

### D5 — Blocked / deferred states

| State | Meaning | Operator action |
|-------|---------|-----------------|
| `pending`, before `scheduled_at_utc` | Scheduled; supervision window open | Optional edit/delay/cancel (US-017) |
| `pending`, operator cancelled/deferred | Override; not eligible for auto-queue | None until US-017 mechanics |
| Publication enablement false | Technical fail-closed | Enable only for controlled windows |
| `failed` / OAuth action_required | Integration failure | Existing publication semantics; BL-008 later |
| US-016 / US-017 / console | Deferred | Not a worker defect for US-015 |
| BL-007 not implemented | No auto-queue yet | Manual queue/publish or wait |

### D6 — BL-007 future eligibility (documentation only)

**Decision:** Future BL-007 auto-queue SHOULD target Flow A variants that are `pending`, not operator-cancelled or deferred, and due per `scheduled_at_utc` / queue rules. It MUST NOT require a mandatory human review flag from US-015. Operator overrides (cancel/defer) constrain eligibility when US-017 defines them.

### D7 — No new HTTP surface

**Decision:** No new worker routes. ADR-0001 preserved.

### D8 — Editorial canon alignment

**Decision:** MODIFY `editorial-canon` so Flow A:

- Blog + package + schedule: automatic after validation (unchanged).
- LinkedIn API: automatic **per distribution strategy** when integration and enablement allow; optional operator supervision before send; **not** blocked on mandatory per-variant human approval.

Flow B: mandatory review before publish (unchanged).

### D9 — Glossary

**Decision:** Add **LinkedIn variant supervision window** (Flow A `pending` phase before API send) distinct from **`publish_state`** and from **mandatory review** (Flow B).

### D10 — Tests

Lightweight policy presence test; no LinkedIn API tests.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Generated LinkedIn text publishes without human read | US-016 quality criteria; US-017 edit/cancel; anti-AI rules at generation time |
| No enforcement of cancel/defer until US-017 | Policy + blocked-states table; BL-007 must respect overrides when defined |
| Confusion with Flow B | Explicit mandatory vs optional table in policy and canon |

## Migration Plan

Docs-only apply; no deploy or enablement change. BL-007 proposal references this policy.

## Open Questions

1. US-017: `review_state` in metadata vs folder moves — deferred.
2. Console UI backlog item — not assigned; policy references as future supervision surface.
