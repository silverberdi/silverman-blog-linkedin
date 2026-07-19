## ADDED Requirements

### Requirement: Max two publications per operator-local day (US-040K interim)

The worker MUST enforce an interim product rule: at most **2 density members** may occupy the same **operator-local calendar day** in the live Flow A supervision plan.

A density member is defined as follows (MUST match console counting):

- LinkedIn variants with `publish_state` `pending` or `queued` (including deferred pending with a schedule)
- LinkedIn variants with `publish_state` `published` that still appear on schedule-visibility for that local day
- Blog editorial-calendar items returned by schedule-visibility for that local day
- LinkedIn `cancelled` MUST NOT count
- LinkedIn `failed` MUST NOT count

When evaluating a schedule placement or move, the worker MUST exclude the item being mutated from the target-day count (self-move within the same local day MUST remain allowed when the resulting occupancy would be ≤ 2).

This rule is **additive** to existing interim duplicate-slot and same-UTC-day/72h saturation checks (LinkedIn) and interim blog max-1-per-UTC-day checks. It MUST NOT replace publish-time US-020 cadence. **BL-021 MAY later supersede** this interim 2/local-day rule via an approved OpenSpec change.

Enforcement MUST NOT call the LinkedIn publication API and MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

#### Scenario: Third density member on a local day is refused

- **WHEN** defer or reopen would place a LinkedIn variant onto an operator-local day that already has 2 density members (excluding the item being moved)
- **THEN** the operation fails with a stable local-day density code and metadata is unchanged

#### Scenario: Self-move on the same local day remains allowed

- **WHEN** defer moves a pending variant to a new UTC instant that falls on the same operator-local day and that day has exactly 2 density members including this variant
- **THEN** the density check does not refuse solely because of self-occupancy (other validations may still apply)

#### Scenario: Cancelled variants do not occupy density slots

- **WHEN** a local day has two cancelled LinkedIn chips and zero other density members
- **THEN** defer or reopen MAY place a pending variant onto that local day without failing the max-2 density rule (subject to other validations)

#### Scenario: Published items on the calendar count toward density

- **WHEN** a local day already shows 2 published LinkedIn items on schedule-visibility
- **THEN** placing an additional pending variant onto that local day fails the max-2 density rule

#### Scenario: Density enforcement does not call LinkedIn

- **WHEN** a density refusal or successful density-validated defer/reopen occurs
- **THEN** no LinkedIn publication API call is made as part of density evaluation

### Requirement: Operator timezone required for local-day density

Worker density evaluation MUST compute local day keys using an IANA timezone supplied on the mutation request (preferred field name `operator_timezone`) or, when absent, a configured `SILVERMAN_OPERATOR_TIMEZONE` env fallback.

If neither a valid request timezone nor a valid env fallback is available, the worker MUST fail closed with a stable timezone-required or timezone-invalid code and MUST NOT silently use UTC calendar days as a substitute for the US-040K product rule.

Schedule wire fields remain `*_utc`. Dry-run MUST validate density and timezone rules without mutating metadata.

#### Scenario: Request timezone drives local-day boundary

- **WHEN** defer supplies a valid `operator_timezone` and `new_scheduled_at_utc` near a local midnight boundary
- **THEN** density membership for the target day follows that timezone’s local calendar date, not the UTC date alone

#### Scenario: Missing timezone fails closed

- **WHEN** a density-gated mutation omits `operator_timezone` and no valid `SILVERMAN_OPERATOR_TIMEZONE` is configured
- **THEN** the operation fails with a stable timezone-required/invalid code and schedule is unchanged

### Requirement: Local-day density on defer and reopen

Authenticated `POST /defer-linkedin-variant` and `POST /reopen-linkedin-variant` MUST run the max-2 operator-local-day density check (in addition to existing eligibility, future-time, duplicate-slot, and interim saturation checks) before committing a real schedule change.

Dry-run MUST surface density failures without writing campaign metadata.

Stable density failure code for LinkedIn paths MUST be distinct from `linkedin_supervision_defer_saturation` and `linkedin_supervision_defer_duplicate_slot` (exact code fixed at apply, e.g. `linkedin_supervision_local_day_density`).

#### Scenario: Dry-run defer reports density without mutation

- **WHEN** dry-run defer targets a local day that already has 2 density members
- **THEN** the worker returns a density failure code and does not change `scheduled_at_utc`

#### Scenario: Real reopen onto a full local day is refused

- **WHEN** reopen requests a future `new_scheduled_at_utc` on a local day that already has 2 density members
- **THEN** the operation fails with the LinkedIn local-day density code and the variant remains `cancelled`

### Requirement: Local-day density on blog calendar schedule-update

Editorial calendar schedule-update for blog items that participate in schedule-visibility MUST enforce the same shared max-2 operator-local-day density rule (blog + LinkedIn density members), additive to the existing interim blog max-1-per-UTC-day check.

Stable density failure code for the blog path MUST be distinct from `calendar_schedule_saturation` / `calendar_schedule_duplicate_slot` (exact code fixed at apply, e.g. `calendar_schedule_local_day_density`).

#### Scenario: Blog move onto a day with two LinkedIn items is refused

- **WHEN** blog schedule-update would place a blog item onto an operator-local day that already has 2 LinkedIn density members
- **THEN** the operation fails with the blog local-day density code and the calendar row is unchanged

### Requirement: Grandfathered over-capacity days are not destroyed

Existing local days that already have 3 or more density members MUST remain readable via schedule-visibility. Density enforcement MUST NOT delete, hide, or silently reschedule those items.

Mutations that would **increase** occupancy above 2 on a day MUST fail closed. Mutations that **reduce** occupancy by moving an item to an under-capacity day MUST be allowed when otherwise valid.

#### Scenario: Over-full day remains visible on read

- **WHEN** schedule-visibility is queried for a range containing a local day with 3+ density members
- **THEN** all those items are still returned (subject to existing visibility rules)

#### Scenario: Moving one item off an over-full day is allowed

- **WHEN** defer moves one pending variant from a local day with 3 density members to a local day with 0 density members
- **THEN** the density rule does not refuse the move solely because the source day was over capacity

### Requirement: US-040K scope preserves baselines and defers Story accepted

US-040K MUST NOT mark BL-015 closed or US-040K Story accepted by implementation alone.

US-040K MUST preserve:

- US-017 defer/correct/cancel contracts except additive density/timezone fields and additive refusal codes
- US-040J reopen contract except additive density/timezone validation
- interim duplicate-slot and UTC-day+72h saturation behavior (additive coexistence)
- `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` fail-closed publish guards
- n8n → worker HTTP only (ADR-0001)

US-040K MUST NOT activate public URL hosting, MUST NOT integrate live Google/OIDC, MUST NOT introduce a BFF/user-management product, MUST NOT call LinkedIn API for density enforcement, and MUST NOT close US-040G/H/I/J Story accepted as a side effect.

#### Scenario: Prior mutation baselines remain

- **WHEN** US-040K is implemented
- **THEN** defer, reopen, and blog schedule-update remain authenticated worker HTTP mutations with dry-run default semantics and `*_utc` schedule fields

#### Scenario: BL-015 and prior Story accepted remain open

- **WHEN** US-040K implementation lands
- **THEN** status language does not mark BL-015 closed or US-040G/H/I/J/K Story accepted by implementation alone

## MODIFIED Requirements

### Requirement: Interim LinkedIn schedule saturation and duplicate-slot checks on defer

In addition to requiring `new_scheduled_at_utc` strictly in the future, defer MUST reject requests that violate interim US-040C cadence/reschedule safeguards for LinkedIn schedule **intent** (until an approved BL-021 definition supersedes them):

- duplicate slot: another variant in the same campaign already has the same `scheduled_at_utc` instant (`linkedin_supervision_defer_duplicate_slot` or equivalent stable code)
- saturation: the new time would place two or more variants of the same campaign on the same UTC day and within 72 hours of another variant’s `scheduled_at_utc` in that campaign (`linkedin_supervision_defer_saturation` or equivalent)

These checks MUST NOT call LinkedIn APIs, MUST NOT bypass `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`, and MUST NOT change publish-time US-020 cadence enforcement (publish-time cadence remains authoritative at send).

Dry-run MUST validate these rules without mutating metadata.

These interim checks remain **additive** to the US-040K max-2 operator-local-day density rule. US-040K density MUST use a distinct stable error code and MUST NOT be implemented by overloading `linkedin_supervision_defer_saturation`.

#### Scenario: Duplicate scheduled instant is rejected

- **WHEN** defer requests `new_scheduled_at_utc` equal to another variant’s `scheduled_at_utc` in the same campaign
- **THEN** the operation fails with a stable duplicate-slot code and schedule is unchanged

#### Scenario: Interim same-day saturation is rejected

- **WHEN** defer would place a second campaign variant on the same UTC day within 72 hours of a sibling’s `scheduled_at_utc`
- **THEN** the operation fails with a stable saturation code and schedule is unchanged

#### Scenario: Local-day density remains a separate refusal

- **WHEN** defer would place a third density member on an operator-local day under US-040K rules without necessarily violating same-campaign UTC-day+72h saturation
- **THEN** the operation fails with the distinct local-day density code (not solely `linkedin_supervision_defer_saturation`)

### Requirement: Reopen eligibility and fail-closed refusals

Reopen MUST accept only variants whose `publish_state` is `cancelled` and whose cancellation provenance is reopen-eligible:

- `operator_supervision.cancellation.phase` `pre_queue` — eligible
- `operator_supervision.cancellation.phase` `post_queue` (queued then cancelled before LinkedIn API publish) — eligible; result state MUST still be `pending`, not `queued`
- cancellation originating from the failed-state recovery cancel path (`failed` → `cancelled` / recovery cancellation evidence) — **not** eligible

Reopen MUST refuse `published`, `pending`, `queued`, and `failed` variants, and MUST refuse ineligible cancelled variants, with a stable machine-readable code such as `linkedin_reopen_not_allowed` (exact code fixed at apply and mapped in console errors).

Reopen MUST reject `new_scheduled_at_utc` that is not strictly after now with a stable time-invalid code (reuse or mirror defer’s time-invalid family).

Interim duplicate-slot / same-campaign saturation checks already applied to defer MUST also apply to reopen’s new schedule with stable codes.

Reopen MUST additionally enforce the US-040K max-2 operator-local-day density rule (with operator timezone) using the distinct local-day density code. This interim density rule MAY later be superseded by BL-021.

#### Scenario: Pre-queue cancelled variant can be reopened

- **WHEN** reopen is requested for a `cancelled` variant with cancellation phase `pre_queue` and a future schedule
- **THEN** the operation is allowed (subject to dry-run/auth/idempotency/density) and can restore `pending`

#### Scenario: Post-queue cancelled variant reopens to pending not queued

- **WHEN** a real reopen succeeds for a `cancelled` variant with cancellation phase `post_queue`
- **THEN** `publish_state` becomes `pending` and is not `queued`

#### Scenario: Failed-cancellation reopen is refused

- **WHEN** reopen is requested for a variant cancelled from `failed` via the recovery cancellation path
- **THEN** the operation fails with a stable reopen-not-allowed code and metadata is unchanged

#### Scenario: Past schedule on reopen is refused

- **WHEN** reopen supplies `new_scheduled_at_utc` that is not strictly after now
- **THEN** the operation fails with a stable time-invalid code and metadata is unchanged

#### Scenario: Reopen onto a full local day is refused by density

- **WHEN** reopen targets a future schedule on an operator-local day that already has 2 density members
- **THEN** the operation fails with the LinkedIn local-day density code and the variant remains `cancelled`
