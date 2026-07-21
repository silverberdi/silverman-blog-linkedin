## ADDED Requirements

### Requirement: Schedule-visibility cadence-conflict projection fields (US-087)

Authenticated `GET /flow-a/schedule-visibility` LinkedIn-channel items that are **not Live on LinkedIn** and carry a usable `scheduled_at_utc` MUST include additive cadence-conflict projection fields so the console can warn without browser filesystem SoT and without inventing a second cadence engine.

For each such LinkedIn item the worker MUST evaluate whether, at that item’s `scheduled_at_utc`, a real publish-due / auto-queue path would refuse or skip **for cadence** under the US-051 / US-020 meaning (same gate as live `linkedin_publish_blocked_cadence` / related cadence skip): same-campaign successful `published` evidence separated by a minimum real interval of **72 hours**, using the same interval constant as the publish-time guard.

Additive fields MUST include at least:

- `cadence_conflict` (boolean) — `true` only for the cadence refuse/skip condition at `scheduled_at_utc`
- `cadence_conflict_code` (`string` or null) — `linkedin_publish_blocked_cadence` when `cadence_conflict` is true; otherwise null
- `cadence_earliest_feasible_at_utc` (`string` or null) — earliest UTC instant at which same-campaign cadence would clear (`max(published_at) + 72h` among valid same-campaign `published` evidence) when computable; otherwise null

`cadence_conflict` MUST be **false** (and the warning fields MUST NOT claim conflict) when the slot is cadence-feasible, when the item is Live on LinkedIn, when the item is Cancelled, when the item is Failed (Failed remains a distinct status story), when the channel is blog, or when the condition is density-full alone, OAuth missing, publication enablement off, sequence block alone, or evidence-invalid alone.

The schedule-visibility read MUST remain **read-only** (no campaign metadata mutation, no LinkedIn API call, no change to `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`). The browser MUST obtain these fields through authenticated worker HTTP (typed client); MUST NOT read raw mounts.

#### Scenario: Cadence-infeasible Scheduled LinkedIn item is projected

- **WHEN** an authenticated client requests schedule-visibility for a range containing a not-yet-Live LinkedIn variant whose `scheduled_at_utc` would hit the US-020 cadence refuse/skip gate against same-campaign `published_at` evidence
- **THEN** that item’s `cadence_conflict` is true and `cadence_conflict_code` is `linkedin_publish_blocked_cadence`

#### Scenario: Cadence-feasible LinkedIn item is not projected as conflicted

- **WHEN** an authenticated client requests schedule-visibility for a not-yet-Live LinkedIn variant whose `scheduled_at_utc` satisfies same-campaign 72h cadence
- **THEN** that item’s `cadence_conflict` is false and `cadence_conflict_code` is null

#### Scenario: Live on LinkedIn is not cadence-conflict warned

- **WHEN** schedule-visibility returns a LinkedIn variant that is Live on LinkedIn
- **THEN** `cadence_conflict` is false for that item

#### Scenario: Density-full alone is not cadence conflict

- **WHEN** a LinkedIn item’s local day is at US-040K density capacity but the slot is cadence-feasible under US-020
- **THEN** `cadence_conflict` is false for that item

#### Scenario: Earliest feasible time is exposed when computable

- **WHEN** `cadence_conflict` is true and same-campaign published evidence yields a clear `published_at + 72h` instant
- **THEN** `cadence_earliest_feasible_at_utc` is that instant (UTC)

#### Scenario: Schedule-visibility cadence projection does not mutate or publish

- **WHEN** schedule-visibility evaluates cadence-conflict fields
- **THEN** no campaign metadata write, no LinkedIn API call, and no enablement bypass occurs

### Requirement: Week and Month cadence-conflict visual warning (US-087)

Silverman Authority Manager Week and Month views MUST show a **red or equivalent warning indicator** on LinkedIn-channel calendar items whose schedule-visibility (or shared model) `cadence_conflict` is true.

The indicator MUST:

- remain visible alongside the US-083 primary operator status (Scheduled / Waiting to send remain Scheduled / Waiting to send)
- MUST NOT imply Live on LinkedIn
- MUST NOT imply density-full alone
- MUST remain visually distinct from Failed, Cancelled, and Waiting to send primary status presentation
- MUST NOT appear on items with `cadence_conflict` false

Outcome MUST be readable on desktop and mobile calendar chips (or equivalent dense-month affordances).

#### Scenario: Week shows warning on cadence-conflicted Scheduled item

- **WHEN** Week view renders a LinkedIn item with `cadence_conflict` true and primary status Scheduled
- **THEN** a red or equivalent cadence-conflict warning indicator is visible on that chip and the primary status is not replaced by Live / Failed / Cancelled

#### Scenario: Month shows warning on cadence-conflicted item

- **WHEN** Month view renders a LinkedIn item with `cadence_conflict` true
- **THEN** a red or equivalent cadence-conflict warning indicator is visible for that item

#### Scenario: Feasible item has no cadence-conflict warning

- **WHEN** Week or Month renders a LinkedIn item with `cadence_conflict` false
- **THEN** the cadence-conflict warning indicator is not shown for that item

#### Scenario: Warning is distinct from Failed and density cues

- **WHEN** the console shows a Failed LinkedIn chip or a US-040K density-full day cue in the same view as a cadence-conflicted Scheduled item
- **THEN** the cadence-conflict indicator remains distinguishable from Failed status styling and from the density-full day cue

### Requirement: EventModal cadence-conflict explanation and next step (US-087)

When an operator opens a LinkedIn calendar/event item in EventModal (or equivalent detail) and `cadence_conflict` is true, the console MUST explain the conflict in **plain language** and provide a **usable next step**.

Plain language MUST convey that the current slot would be blocked for **same-campaign LinkedIn cadence** (72h since last successful publication in the campaign) — not that the item is Live on LinkedIn, not density-full alone, and not Failed/Cancelled as the conflict class.

Usable next step MUST include at least one actionable path such as:

- showing the **earliest feasible** time (operator-local interpretation of `cadence_earliest_feasible_at_utc` with timezone cue) and pointing to existing **Postpone / reschedule** (US-084), and/or
- stating that the operator may postpone or wait for a later **replan** capability (US-089) without claiming US-089 is already a working control in this change

Blocked/conflict states MUST be clearly communicated. Cadence-feasible opens MUST NOT show the cadence-conflict explanation as if conflicted.

#### Scenario: EventModal explains cadence conflict with next step

- **WHEN** an operator opens a LinkedIn item with `cadence_conflict` true in EventModal
- **THEN** the modal shows plain-language cadence-conflict copy and a usable next step (earliest feasible and/or postpone / wait for replan)

#### Scenario: EventModal does not claim Live or density-full for cadence conflict

- **WHEN** EventModal shows a cadence-conflict explanation
- **THEN** the copy does not claim Live on LinkedIn and does not describe the condition as density-full alone

#### Scenario: Feasible item has no false cadence-conflict explanation

- **WHEN** an operator opens a LinkedIn item with `cadence_conflict` false
- **THEN** the EventModal does not present the cadence-conflict warning explanation as active for that item

### Requirement: US-087 Visual DoD and non-duplication

US-087 Story accepted MUST be supported by **desktop + mobile** visual evidence (screenshots or equivalent browser-driven capture) for at least: Week conflicted chip; Month conflicted item; EventModal conflict explanation + next step; feasible item without warning; distinctness from Failed and density-full cues; mobile-readable EventModal conflict copy — unless the operator explicitly waives the formal screenshot pack as with prior console stories. Vitest alone is insufficient for Story accepted.

This change MUST NOT duplicate or weaken completed work: BL-032 control-center labels remain; no second publish pipeline; `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` untouched; US-020 publish-time cadence guard remains authoritative at send. This change MUST NOT implement US-088 schedule-time shift-forward or US-089 replan.

#### Scenario: Visual DoD scenes are required for Story accepted

- **WHEN** operators evaluate US-087 for Story accepted
- **THEN** desktop and mobile evidence for the listed conflict-warning scenes is available unless explicitly waived by the operator

#### Scenario: Non-goals hold — no shift-forward or enablement bypass

- **WHEN** US-087 implementation is complete
- **THEN** schedule-time shift-forward (US-088) and replan (US-089) are not shipped by this change, and LinkedIn publication enablement is not bypassed
