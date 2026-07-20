## Context

BL-015 closed as a calendar-first **pre-send supervision** console (US-038–US-040M Story accepted). The same Silverman Authority Manager surface already shows Week/Month calendars, EventModal, ScheduleEditor, and US-017 mutations (edit / defer / cancel-pending / reopen) via authenticated worker HTTP (`GET /flow-a/schedule-visibility`, `GET /flow-a/linkedin-variants/pending-supervision`, and existing POSTs).

Operator-facing gaps for **BL-032 / US-083**:

- Labels still read as jargon (“Pending review”, “Queued”, “Published (API evidence)”) rather than command language (scheduled / waiting to send / live on LinkedIn / failed / cancelled).
- `queued` is not LinkedIn API published (GLOSSARY), but the UI does not make that unmistakable as the primary message.
- EventModal shows available buttons (edit/cancel when `actions` includes them; schedule always) but does not present a full **available vs unavailable** matrix with plain-language reasons—especially for cancel-queued and publish-now that BL-032 will add later.
- Dry-run defaults exist, but success copy still leans on technical `publish_state=` phrasing; preview vs real must be impossible to confuse with a live LinkedIn send.
- Blog “Published on blog” (US-040M) must stay visually distinct from LinkedIn live.

Stakeholders: content operator commanding publication; engineering constrained by OpenSpec, ADR-0001, and LinkedIn enablement guards.

## Goals / Non-Goals

**Goals:**

- Operator-language status for LinkedIn variants across calendar + EventModal (+ summary chips where labels appear).
- Explicit queued ≠ LinkedIn API published.
- Per-opened-item action availability matrix (current controls + honest unavailable reasons for US-084/085/086).
- Unmistakable dry-run/preview vs real for existing mutations.
- Preserve blog published-on-site ≠ LinkedIn live.
- Smallest coherent console (+ optional read-model) delta; no new publish pipeline.

**Non-Goals:**

- US-084 postpone/reschedule redesign; US-085 cancel-queued mutation; US-086 publish-now.
- Unattended n8n/cron publish orchestration; Execute Command (ADR-0001).
- Reopening BL-015; Flow B blog approval / gap-trigger work.
- Bypassing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

## Decisions

### D1 — Operator-language label map (primary); technical state secondary

| Wire / display state (LinkedIn channel) | Primary operator label | Must communicate |
|----------------------------------------|------------------------|------------------|
| `pending` | **Scheduled** | Not yet authorized to send / still in pre-send window |
| `queued` (and in-flight `publishing` if shown) | **Waiting to send** | Authorized/queued — **not** on LinkedIn yet |
| `published` or `linkedin_api_published === true` | **Live on LinkedIn** | Confirmed API publication evidence |
| `failed` | **Failed** | Did not go live; blocked/failure context |
| `cancelled` | **Cancelled** | Will not send unless reopen restores pending |

- Technical `publish_state` / `publication_state` remain in EventModal diagnostics (secondary).
- Keep blog `completed` → **Published on blog** unchanged; never reuse “Live on LinkedIn” for blog.
- Deferred / blocked / planned remain existing secondary display states with clear non-live wording; do not invent new `publish_state` values.

**Alternatives considered:** Keep “Pending review” / “Queued” as primary — rejected (fails US-083 AC). Channel-aware reuse of a single “Published” string — rejected (blurs blog vs LinkedIn).

### D2 — Prefer console mapping over new worker endpoints

- Implement label + action-matrix presentation primarily in the frontend model (`publicationStateLabel`, EventModal, calendar chips).
- Reuse existing schedule-visibility fields: `publication_state`, `source_state`, `linkedin_api_published`, `actions`, `schedule_editable`, `schedule_edit_block_reason`, cancellation/reopen context, pending-supervision join for edit/cancel eligibility.
- Add worker read fields **only if** the console cannot truthfully derive availability (prefer none for US-083).

**Alternatives considered:** New `/control-center` aggregation endpoint — rejected as overkill for foundation story.

### D3 — Action availability matrix in EventModal (and related surfaces)

For each opened **LinkedIn** item, present a dedicated “What you can do now” section listing at least:

| Control | When available (US-083) | When unavailable — example reason |
|---------|-------------------------|-----------------------------------|
| Edit draft | Pending + pending-supervision join + `actions` includes edit + `canMutate` | Not in supervision window; session cannot mutate |
| Reschedule / defer | Existing schedule-editable path (pending / calendar rules) | Not schedule-editable — show `schedule_edit_block_reason` or plain equivalent |
| Cancel | Pending cancel path only (existing US-017) | Already live; or **queued: cancel not available yet (US-085)** |
| Reopen | Cancelled + `reopen_eligible` | Not reopen-eligible (recovery cancel, etc.) |
| Publish now | Never as a working control in US-083 | **Not available yet (US-086)** — publication enablement / story not shipped |
| Improved postpone clarity | N/A as new mutation | Point to existing reschedule/defer; note US-084 will clarify |

Unavailable rows MUST be visible (not silently omitted) when the operator would reasonably expect the control, with plain-language why.

**Alternatives considered:** Only hide unavailable buttons — rejected (spectator ambiguity). Ship cancel-queued/publish-now stubs that call APIs — rejected (out of scope; false capability).

### D4 — Dry-run / preview vs real is unmistakable

- Keep dry-run default `true` for existing mutations.
- Before commit: mode control labeled so **Preview (no change)** vs **Make real change** (or equivalent) is primary, not buried.
- After success: toast/outcome MUST state preview vs saved/committed; MUST NOT say “published to LinkedIn” or “went live” for dry-run or for non-publish mutations.
- Submit button labels already distinguish validate vs commit — strengthen surrounding copy where needed.

### D5 — Spec framing: control-center foundation, not publish-now

- Delta the console spec to require honest status + action matrix + dry-run clarity as **BL-032 / US-083 foundation**.
- Explicitly keep LinkedIn API publish-from-console as **out of scope for this change** (US-086).
- Do not reopen BL-015 requirements as “supervision only forever”; additive control-center foundation supersedes spectator-only interpretation for status/actions without deleting BL-015 historical requirements.

### D6 — Testing and docs

- Vitest: label map for pending/queued/published/failed/cancelled; queued never labeled live; blog completed distinct; EventModal matrix shows available + unavailable reasons; dry-run outcome copy.
- Pytest only if worker read fields change.
- After implementation: update `docs/CURRENT-STATE.md` if console product-role language changes; do not mark US-083 Story accepted by code alone.

## Risks / Trade-offs

- **[Risk] Filter checkboxes still say old jargon** → Mitigation: update filter labels to operator language while keeping wire `publication_state` values stable for filtering.
- **[Risk] “Scheduled” confuses with calendar `scheduled` / blog planned** → Mitigation: apply LinkedIn-channel labels; keep blog labels separate; short helper under status pill when needed.
- **[Risk] Showing unavailable publish-now/cancel-queued frustrates operators** → Mitigation: plain “not available yet” + story pointer; do not fake enabled buttons.
- **[Risk] Scope creep into US-084/085/086** → Mitigation: tasks checklist gates; no new mutation routes in this change.
- **[Risk] Spec Purpose still says “LinkedIn API publish … out of scope”** → Mitigation: ADDED requirements clarify foundation vs publish-now; leave historical BL-015 text intact where possible.

## Migration Plan

1. Approve OpenSpec change → `/opsx-apply`.
2. Console label + EventModal matrix + dry-run copy; Vitest; static rebuild into worker static assets.
3. Worker read tweaks only if required; pytest if touched.
4. Deploy on explicit approval; operator walkthrough for Story accepted.
5. Rollback: revert deploy/assets; no editorial data migration expected.

## Open Questions

- None blocking proposal. Exact button/section microcopy may be refined during apply as long as AC language (scheduled / waiting to send / live on LinkedIn / failed / cancelled) and dry-run honesty hold.
