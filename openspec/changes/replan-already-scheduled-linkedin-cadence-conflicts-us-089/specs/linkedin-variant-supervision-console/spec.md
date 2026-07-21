## ADDED Requirements

### Requirement: Console replan of cadence conflicts via worker HTTP (US-089)

When Silverman Authority Manager exposes a deliberate **Replan cadence conflicts** control (EventModal when `cadence_conflict` is true, and/or a bulk ops entry), it MUST call authenticated `POST /replan-linkedin-cadence-conflicts` through the typed injectable-auth client. Browser filesystem SoT and n8n Execute Command MUST NOT be used (ADR-0001). The console control is optional relative to HTTP: documented one-shot ops/curl against the same worker endpoint remains a valid operator path when the control is deferred; the HTTP contract remains the mutation SoT.

When the control is present:

- Preview / dry-run MUST be available and MUST default to non-mutating behavior consistent with US-083 (preview ≠ Live on LinkedIn; preview ≠ LinkedIn API published).
- Real replan MUST require explicit confirmation before `dry_run` false.
- After a **successful real** replan, the console MUST refresh schedule-visibility (and pending-supervision as applicable) so Week/Month placement and authoritative `scheduled_at_utc` agree on the new times.
- US-087 cadence-conflict indicators MUST clear for items whose new slot is cadence-feasible; the warning chrome itself MUST NOT be redesigned beyond clear-after-success and next-step honesty.

#### Scenario: Console replan uses worker HTTP only

- **WHEN** an operator runs Replan cadence conflicts from the console (preview or real)
- **THEN** the console calls `POST /replan-linkedin-cadence-conflicts` with injectable auth
- **AND** the browser does not write editorial mounts as schedule SoT

#### Scenario: Preview does not move calendar chips

- **WHEN** an operator runs replan preview / dry-run from the console
- **THEN** Week/Month placement for affected items does not change solely due to the preview
- **AND** the UI does not claim Live on LinkedIn

#### Scenario: After real replan calendar and warnings agree

- **WHEN** a real replan succeeds and the console refreshes schedule-visibility
- **THEN** affected items appear at their new local slots
- **AND** items that are cadence-feasible at the new slot do not show the US-087 cadence-conflict warning

### Requirement: US-089 preserves US-087 honesty and non-goals

US-089 MUST preserve US-083 preview-vs-real honesty, US-087 cadence-conflict meaning (projection fields unchanged except reflecting new `scheduled_at_utc` after replan), and BL-032 control-center labels. It MUST NOT mark US-089 / US-087 / US-088 / BL-021 Story accepted by implementation alone, MUST NOT change publish-time US-020 cadence math, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, MUST NOT expand into BL-022 metrics, and MUST NOT redesign US-087 warning chrome beyond clear-after-success / next-step honesty.

#### Scenario: Non-goals hold

- **WHEN** US-089 console or HTTP replan is implemented
- **THEN** LinkedIn publication enablement is not bypassed
- **AND** US-087 warning meaning is not redefined to density/sequence/OAuth/enablement
- **AND** Story accepted / BL-021 closure are not claimed by code alone

## MODIFIED Requirements

### Requirement: EventModal cadence-conflict explanation and next step (US-087)

When an operator opens a LinkedIn calendar/event item in EventModal (or equivalent detail) and `cadence_conflict` is true, the console MUST explain the conflict in **plain language** and provide a **usable next step**.

Plain language MUST convey that the current slot would be blocked for **same-campaign LinkedIn cadence** (72h since last successful publication in the campaign) — not that the item is Live on LinkedIn, not density-full alone, and not Failed/Cancelled as the conflict class.

Usable next step MUST include at least one actionable path such as:

- showing the **earliest feasible** time (operator-local interpretation of `cadence_earliest_feasible_at_utc` with timezone cue) and pointing to existing **Postpone / reschedule** (US-084), and/or
- offering or pointing to **Replan cadence conflicts** (US-089) via the authenticated worker path / console control when available — without claiming LinkedIn API published and without implying replan is still an unshipped future-only promise when the control/endpoint is present

Blocked/conflict states MUST be clearly communicated. Cadence-feasible opens MUST NOT show the cadence-conflict explanation as if conflicted.

#### Scenario: EventModal explains cadence conflict with next step

- **WHEN** an operator opens a LinkedIn item with `cadence_conflict` true in EventModal
- **THEN** the modal shows plain-language cadence-conflict copy and a usable next step (earliest feasible and/or postpone and/or replan)

#### Scenario: EventModal does not claim Live or density-full for cadence conflict

- **WHEN** EventModal shows a cadence-conflict explanation
- **THEN** the copy does not claim Live on LinkedIn and does not describe the condition as density-full alone

#### Scenario: Feasible item has no false cadence-conflict explanation

- **WHEN** an operator opens a LinkedIn item with `cadence_conflict` false
- **THEN** the EventModal does not present the cadence-conflict warning explanation as active for that item

#### Scenario: EventModal does not claim US-089 unshipped when replan exists

- **WHEN** US-089 replan HTTP (and optional console control) is available
- **THEN** EventModal next-step copy MUST NOT state that operators must only “wait for a later replan” as if US-089 were still unimplemented
