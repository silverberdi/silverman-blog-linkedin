## Why

BL-015 delivered a calendar-first **pre-send supervision** console; that work stays closed. Operators still cannot confidently command LinkedIn publication from the same surface: labels like “Pending review” / “Queued” / “Published (API evidence)” hide that `queued` is not LinkedIn API live, action affordances appear or disappear without a clear available-vs-unavailable matrix, and dry-run can still be mistaken for a real schedule or publish. US-083 is the BL-032 foundation so later postpone, cancel-queued, and publish-now stories build on honest status and action truth—not spectator UX.

## What Changes

- Replace (or demote) jargon-first LinkedIn status presentation with **operator-language** primary labels for at least: scheduled (not yet authorized to send), waiting to send (authorized, not yet on LinkedIn), live on LinkedIn, failed, and cancelled — across calendar chips, EventModal, and related summary surfaces. Technical `publish_state` / `publication_state` MAY remain secondary (diagnostics).
- Make unmistakable that **waiting-to-send / `queued` is not LinkedIn API published**.
- For each opened LinkedIn item, show a clear **control-action availability matrix**: what the console can do now vs unavailable, with plain-language blocked reasons (including honest “not available yet” for US-084/US-085/US-086 controls this story does not implement).
- Strengthen **preview/dry-run vs real** UX for existing mutations (edit / defer-reschedule / cancel-pending / reopen) so operators never believe a schedule or publish happened when only a preview ran.
- Preserve **blog “Published on blog”** as visually and verbally distinct from LinkedIn live (US-040M intent).
- Frame the console product role toward **operator control center foundation** (status + action honesty) without implementing postpone redesign, cancel-queued mutation, or publish-now.
- Prefer smallest coherent console + read-model changes; reuse `GET /flow-a/schedule-visibility` and `GET /flow-a/linkedin-variants/pending-supervision`. Add worker fields only if required for truthful action availability.

## Goals

- Satisfy **US-083** acceptance criteria (honest status, queued ≠ live, available vs unavailable actions with reasons, unmistakable dry-run vs real, blog ≠ LinkedIn live, understandable outcomes/failures).
- Keep **BL-015** Story accepted / closed; do not reopen it as “supervision only.”
- Leave a clear foundation for **US-084 → US-085 → US-086** without shipping those mutations as done.
- Never claim LinkedIn API published unless `publish_state` / `linkedin_api_published` (or equivalent evidence) supports it.
- Respect ADR-0001 (n8n → worker HTTP only), `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` fail-closed, and secret-safety.

## Non-goals

- **US-084** — Postpone/reschedule behavior redesign and calendar write-back beyond honest labels / availability display.
- **US-085** — Implementing cancel for `queued` (MAY show as unavailable/coming with reason).
- **US-086** — Publish now / LinkedIn API publish path from the console.
- Unattended cron/n8n publish orchestration changes.
- Reopening BL-015 as supervision-only product scope.
- Bypassing `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, ADR-0001, or secret-safety rules.
- Flow B gap trigger / blog approval work.
- Marking US-083 or BL-032 complete by implementation alone (Story accepted remains operator-gated).

## Capabilities

### New Capabilities

- (none)

### Modified Capabilities

- `linkedin-variant-supervision-console`: extend from pre-send supervision presentation toward control-center **foundation** — operator-language LinkedIn publication status, explicit action availability (including unavailable-with-reason for later BL-032 controls), and unmistakable dry-run vs real for existing mutations — without implementing publish-now, cancel-queued, or US-084 reschedule redesign. Preserve blog published-on-site ≠ LinkedIn live.

## Impact

- Frontend: `frontend/linkedin-variant-supervision-console/` — labels (`publicationStateLabel` / calendar chips), EventModal action matrix, dry-run/real confirm copy, Vitest coverage (~1280/~375 where applicable).
- Worker (only if needed for honest availability): schedule-visibility / pending-supervision read fields — prefer no new mutation endpoints.
- Specs: delta under `openspec/specs/linkedin-variant-supervision-console/`.
- Docs after implementation (not in this proposal commit): `docs/CURRENT-STATE.md` if console product-role language changes; product checklist/story progress only when criteria are demonstrated.
- **No** n8n Execute Command; **no** LinkedIn API publish from console in this change.

## Related backlog / stories

- **BL-032** — Turn the LinkedIn Console Into an Operator Control Center
- **US-083** — Show Honest LinkedIn Publication Status and Available Actions (this change only)
- Apply order: US-083 → US-084 → US-085 → US-086
- Addresses all US-083 acceptance criteria listed in `docs/product/user-stories.md`
- Intentionally excluded criteria: those belonging to US-084, US-085, US-086
