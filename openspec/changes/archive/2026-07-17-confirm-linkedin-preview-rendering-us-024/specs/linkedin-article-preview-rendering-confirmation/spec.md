# linkedin-article-preview-rendering-confirmation Delta Specification

Scope: BL-009 / US-024 — normative operator procedure to confirm how LinkedIn actually renders the article preview for a campaign's public blog URL, diagnose cache vs input issues, perform a safe re-scrape, and record confirmation evidence. Procedure capability only: no worker code, no LinkedIn API usage. Input verification is `linkedin-article-preview-verification` (US-023) and is consumed unchanged; fallback definition when the preview is incorrect is US-025 and out of scope.

## ADDED Requirements

### Requirement: Scope, actors, and boundaries

This capability SHALL define the normative operator procedure for confirming LinkedIn's actual rendering of a campaign's article preview (title, description, image) and for diagnosing LinkedIn cache issues, for one Flow A campaign with a generated LinkedIn package (BL-009 / US-024).

The procedure MUST be executable by a human operator using LinkedIn Post Inspector and the LinkedIn feed in a browser. It MUST NOT require worker code changes, new worker endpoints, new environment variables, n8n workflow changes, or deploy script changes.

The procedure MUST NOT involve LinkedIn API calls beyond capabilities that already exist (`linkedin-publication-integration`), MUST NOT automate or scrape LinkedIn's UI, and MUST NOT require storing LinkedIn session cookies or credentials in the repository.

The procedure MUST consume `linkedin-article-preview-verification` (US-023) as the sole source of input-correctness truth and MUST NOT redefine or duplicate any US-023 input check.

#### Scenario: No new automation surface

- **WHEN** this capability is applied
- **THEN** no worker endpoint, environment variable, n8n workflow, or deploy script is added or changed, and no LinkedIn API usage is introduced

#### Scenario: Input verification is not duplicated

- **WHEN** the procedure needs to establish whether preview inputs are correct
- **THEN** it references a `POST /validate-linkedin-article-preview` run (US-023) and its stable codes rather than defining its own input checks

### Requirement: Rendering confirmation procedure

The documented procedure SHALL define two observation points for a campaign's recorded `public_url`:

1. **Pre-publish confirmation** — inspecting the `public_url` in LinkedIn Post Inspector and comparing the retrieved title, description, and image against the campaign's recorded `linkedin_package.article_preview` metadata.
2. **Post-publish observation** — when the campaign has a `published` variant with stored `linkedin_post_urn` evidence, observing the actual LinkedIn post and recording whether and how an article preview card is rendered.

The procedure MUST order steps so that rendering is never assessed before a passing US-023 input verification run for the same campaign, and MUST require that live-site confirmation (blog reachable at `public_url`) precedes Post Inspector inspection.

The procedure MUST state explicitly that a Post Inspector re-scrape affects the preview of new posts only, and that already-published posts retain the card rendered at publication time.

#### Scenario: Pre-publish confirmation compares Post Inspector against recorded metadata

- **WHEN** the operator inspects a campaign's `public_url` in Post Inspector after a passing US-023 run
- **THEN** the procedure directs comparison of the retrieved title, description, and image against the recorded `article_preview` metadata and classification of the result per the decision matrix

#### Scenario: Rendering is not assessed before inputs pass

- **WHEN** US-023 input verification has not been run or is not operationally trusted for the campaign, or the live site is not yet confirmed reachable
- **THEN** the procedure reports the confirmation as `confirmation_blocked` with the named prerequisite instead of proceeding to LinkedIn observation

#### Scenario: Failed US-023 inputs are not blocked

- **WHEN** the US-023 run for the campaign is `failed`
- **THEN** the outcome class is `preview_inputs_incorrect` (not `confirmation_blocked`), LinkedIn observation is not performed, and remediation follows the reported US-023 stable codes

### Requirement: Cache vs input decision matrix

The documented procedure SHALL include a decision matrix that assigns every confirmation attempt exactly one outcome class from the US-023 input verification result combined with the observed LinkedIn rendering:

- **Confirmed** — inputs pass and the observed preview matches the recorded `article_preview` metadata.
- **Stale cache** — inputs pass but LinkedIn shows outdated or incorrect preview values; recovery is the safe re-scrape procedure.
- **Inputs incorrect** — US-023 verification fails; recovery is input remediation per US-023 stable codes, and rendering confirmation is repeated only after inputs pass.
- **Not rendered (post format)** — inputs pass but the API-created text post renders no article preview card; this MUST be recorded as an honest finding about the v1 text-only post format, and remediation (including any post-format change) is out of scope for this capability.
- **Blocked** — a named prerequisite or external condition prevents confirmation (input verification not run or not trusted, site not live, Post Inspector unavailable).

The matrix MUST make "inputs correct but LinkedIn shows stale/incorrect preview" distinguishable from "inputs wrong" in every case, and MUST name the next action for each class.

#### Scenario: Stale cache distinguished from wrong inputs

- **WHEN** a US-023 run for the campaign is `passed` and Post Inspector shows a title different from the recorded `article_title`
- **THEN** the outcome class is stale cache with the safe re-scrape as the next action, not an input-metadata failure

#### Scenario: Failed inputs route back to US-023 remediation

- **WHEN** the US-023 run for the campaign is `failed`
- **THEN** the outcome class is inputs incorrect, the next action references the reported `linkedin_preview_validation_*` codes, and no cache remediation is attempted

#### Scenario: Missing preview card is recorded honestly

- **WHEN** inputs pass and the published API-created text post shows no article preview card at all
- **THEN** the outcome class is not rendered (post format), recorded as a finding, and no fallback or post-format change is improvised within this procedure

### Requirement: Safe re-scrape procedure

The documented procedure SHALL define the safe re-scrape for the stale-cache class:

1. Re-confirm current inputs first via a US-023 verification run (dry-run acceptable) so a re-scrape never caches known-wrong inputs.
2. Force the re-scrape only by re-inspecting the `public_url` in LinkedIn Post Inspector.
3. Re-inspect and re-classify against the decision matrix after the re-scrape, allowing for propagation lag before concluding failure.

The procedure MUST forbid publishing additional LinkedIn posts as a means of testing or forcing a preview refresh, and MUST forbid altering the shared URL (for example cache-busting query parameters) as part of the standard procedure, because the canonical `public_url` is recorded in campaign metadata.

The procedure MUST state that LinkedIn's cache duration is not officially documented and MUST NOT present any specific TTL as normative.

#### Scenario: Re-scrape uses Post Inspector only

- **WHEN** the outcome class is stale cache
- **THEN** the documented remediation is re-inspection of `public_url` in Post Inspector, and publishing another LinkedIn post to force a refresh is explicitly forbidden

#### Scenario: Inputs re-confirmed before re-scrape

- **WHEN** the operator prepares to force a re-scrape
- **THEN** the procedure requires a current passing US-023 verification of the live inputs before the Post Inspector re-inspection

### Requirement: Outcome vocabulary and evidence record

The documented procedure SHALL define a fixed outcome vocabulary — `preview_confirmed`, `preview_stale_cache`, `preview_inputs_incorrect`, `preview_not_rendered_post_format`, `confirmation_blocked` — as documented checklist labels (no worker codes are introduced), used exactly and exclusively for recording confirmation outcomes.

Each confirmation attempt SHALL be recorded using an evidence template that captures at minimum: campaign id, `public_url`, the referenced US-023 verification run (timestamp or persisted `linkedin_article_preview_validation` reference), the Post Inspector observation (retrieved title, description, image reference, and observation timestamp in UTC), the post-publish observation and `linkedin_post_urn` reference when applicable, the outcome label, and the operator and UTC timestamp of the confirmation.

Evidence records MUST NOT contain LinkedIn session cookies, credentials, secrets, or variant body text. Campaign metadata files MUST NOT be edited to record confirmation outcomes under this capability.

#### Scenario: Confirmation recorded with fixed label and evidence

- **WHEN** the operator completes a confirmation attempt for a campaign
- **THEN** the evidence record contains the campaign id, the US-023 run reference, the LinkedIn observation, one outcome label from the fixed vocabulary, and the operator and UTC timestamp

#### Scenario: Campaign metadata untouched by confirmation

- **WHEN** a confirmation outcome is recorded
- **THEN** `metadata/campaigns/<campaign-id>.json` is not modified by the recording procedure

### Requirement: Blocked states and operator communication

The documented procedure SHALL enumerate blocked conditions with the named next action for each, including at minimum: US-023 input verification not run or not operationally trusted for the campaign; live site not confirmed reachable at `public_url`; LinkedIn Post Inspector unavailable or inaccessible; and no published variant when post-publish observation is required. A US-023 run with overall status `failed` MUST be classified as inputs incorrect (`preview_inputs_incorrect`), not as blocked.

Blocked confirmations MUST be recorded with the `confirmation_blocked` label and the specific blocking condition, and MUST NOT be recorded as failures of the preview inputs or of LinkedIn rendering.

#### Scenario: Post Inspector unavailable is blocked, not failed

- **WHEN** LinkedIn Post Inspector is unavailable during a confirmation attempt
- **THEN** the outcome is recorded as `confirmation_blocked` with the blocking condition and retry guidance, not as a rendering or input failure

### Requirement: Existing capabilities unchanged

This capability MUST NOT modify the behavior, requirements, or implementation of `linkedin-article-preview-verification` (US-023), `linkedin-article-preview-image-support`, `linkedin-derivative-package-generation`, `linkedin-publication-integration` (including US-018/US-019/US-020 contracts and the `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` guard), or `linkedin-retry-recovery-classification` (US-021/US-022).

Documentation updates for this capability MUST use qualified status language: procedure defined ≠ operationally validated ≠ story accepted; BL-009 remains open until its stories are demonstrated and accepted.

#### Scenario: No source, test, or workflow changes

- **WHEN** this change is applied
- **THEN** there are no changes under `src/`, `tests/`, `n8n/`, or `deploy/`, and all existing endpoint contracts are unchanged

#### Scenario: Qualified status language in documentation

- **WHEN** project documentation records this capability
- **THEN** it states the procedure is defined but not operationally validated, and BL-009 is not closed
