## 1. At-a-glance counts and operator labels

- [x] 1.1 Add shared count derivation from the normalized model (upcoming, pending, due soon via existing 48h helper, deferred, blocked, failed, recently published within 7-day window using `published` / `linkedinApiPublished` evidence only — never `flow_a_complete` / blog handoff as published) (AC: at-a-glance counts; qualified language)
- [x] 1.2 Upgrade `StatusSummary` into an AppShell-visible count strip for both List and Month; zero counts understandable; filter-scope aware without silent loss of critical-failure discoverability (AC: at-a-glance counts; failures communicated)
- [x] 1.3 Add concise operator-facing labels for publication display states; keep raw diagnostic codes / issue text in expandable details on ItemDetail and failure surfaces (AC: concise labels + expandable diagnostics)

## 2. Visual priority and List vs Month job separation

- [x] 2.1 Strengthen blocked/failed/critical visual hierarchy in List for triage scanning without making every row critical (AC: actionable visual priority; List triage)
- [x] 2.2 Keep Month calendar schedule-comprehensible with compact status/badges (not full diagnostic walls in cells); preserve day placement, navigation, mobile agenda (AC: Month schedule comprehension; do not force one view to do both jobs poorly)
- [x] 2.3 Ensure long titles truncate or wrap understandably in List and Month without breaking layout (AC: visual validation long titles)

## 3. Affordances, destructive safety, and accessibility

- [x] 3.1 Clarify/group shell affordances: view switch, filters, inspect, reschedule/defer (ScheduleEditor), cancel (where supported), refresh, dry-run/commit — with consistent labels (AC: clear affordances)
- [x] 3.2 Keep real cancel (and other irreversible commits) behind confirmation; ensure cancel is not adjacent peer to routine view-switch/refresh navigation (AC: destructive safety)
- [x] 3.3 Preserve `canMutate` / session gating from US-040D on mutation controls (AC: preserve auth readiness; failures communicated)
- [x] 3.4 Keyboard accessibility: visible focus rings and logical focus order for primary shell/view/editor/confirmation controls; Escape closes overlays without silently discarding unsaved schedule drafts (AC: keyboard accessibility; preserve draft rules)
- [x] 3.5 Touch accessibility: maintain usable mobile touch targets for primary controls; no hover-only critical actions (AC: touch accessibility)

## 4. Dark theme and operational first screen

- [x] 4.1 Align loading, empty, error, detail, confirmation, and success surfaces to consistent dark-theme tokens/spacing (AC: dark theme consistency)
- [x] 4.2 Ensure first screen is the operational console shell (no marketing-style landing / promo hero); auth banners stay inside the operational shell (AC: no marketing landing; first screen usable console)

## 5. Frontend and worker verification

- [x] 5.1 Vitest: count derivation; labels; blocked/failed visual distinction smoke; ConfirmationFlow still required for real cancel; affordance placement smoke; a11y focus smoke where practical (AC: counts; labels; destructive safety; keyboard)
- [x] 5.2 Desktop + mobile visual validation (screenshots or equivalent UI checks) covering dense/empty lists, dense/empty months, blocked items, long titles, view switching, schedule editing (AC: visual validation matrix)
- [x] 5.3 Rebuild static assets into worker static path; console route still serves SPA same-origin; secrets audit on source + built assets passes (AC: static serving; secrets; ADR-0001)
- [x] 5.4 Run targeted frontend test/build and pytest for console route / secrets audit / any touched worker surfaces; fix warnings attributable to this change; run `git diff --check`
- [x] 5.5 Verify no public URL activation, no live Google IdP, no BFF/DB/user-mgmt, no new mutation SoT (unless thin additive read-only approved mid-apply), no LinkedIn API publish, no enablement bypass, no n8n Execute Command, no browser mount writes, US-040A–D preserved (AC: non-goals; preserve stack)

## 6. Docs and business progress (demonstrated only)

- [x] 6.1 Update `docs/CURRENT-STATE.md` for US-040E polish when demonstrated (preserve US-040A–D auth readiness; public URL + Google not activated; not Story accepted; not BL-015 closed)
- [x] 6.2 Update `docs/product/progress-checklist.md` US-040E marks only for criteria actually demonstrated (do not mark Story accepted or BL-015 closed from apply alone)
- [x] 6.3 Update `docs/product/user-stories.md` US-040E acceptance checkboxes only when each criterion is demonstrated with evidence
- [x] 6.4 Final business-validation pass against US-040E acceptance criteria in `docs/product/user-stories.md`: at-a-glance counts; actionable visual priority; concise labels + expandable diagnostics; clear affordances; List vs Month job separation; destructive confirmation/separation; keyboard + touch a11y; desktop/mobile visual matrix; dark theme state consistency; operational first screen (no marketing landing); understandable outcomes and clear failure/blocked communication; no unintentional duplication of US-040A–D / public activation / Flow B
