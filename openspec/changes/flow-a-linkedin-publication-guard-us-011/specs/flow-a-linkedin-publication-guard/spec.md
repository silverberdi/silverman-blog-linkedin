## ADDED Requirements

### Requirement: Flow A activation independent of LinkedIn enablement

The system SHALL treat Flow A n8n activation and schedule as independent of LinkedIn API publication enablement. An active Flow A workflow with Schedule Trigger MUST NOT imply that `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is `true`, and MUST NOT call LinkedIn publication APIs.

`distribution_scheduled` (Flow A Core scheduling metadata) MUST NOT be treated as LinkedIn API published.

#### Scenario: Active Flow A does not imply LinkedIn enabled

- **WHEN** an operator reviews runtime state for activated Flow A (`silvermanFlowAPublish01` active with schedule)
- **THEN** documentation and verification distinguish Flow A active from LinkedIn publication enablement and do not treat them as the same flag

#### Scenario: Distribution scheduled is not LinkedIn API published

- **WHEN** a campaign reaches `distribution_scheduled` via Flow A schedule or Manual Trigger
- **THEN** variants remain at LinkedIn `publish_state` `pending` (or prior non-published states) unless a separate LinkedIn publication approval path succeeds

### Requirement: Fail-closed LinkedIn publication until separately approved

Real LinkedIn API publication MUST remain gated by `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`. When the flag is not `true`, real publish-due MUST fail closed with stable code `linkedin_publish_not_enabled` and MUST NOT mark the variant `failed` solely for disablement (reuse canonical `linkedin-publication-integration` behavior).

US-011 MUST NOT invent new LinkedIn publication endpoints.

#### Scenario: Disabled flag blocks real publish with stable code

- **WHEN** a real (`dry_run` false) publish-due request runs while `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` is not `true`
- **THEN** the response includes `linkedin_publish_not_enabled`, no LinkedIn API publication call occurs, and variant `publish_state` remains `queued` (not `failed`)

#### Scenario: No new LinkedIn publication routes for US-011

- **WHEN** this capability is applied
- **THEN** worker OpenAPI/route surface for LinkedIn publication remains the existing queue, publish-due, and cancel endpoints

### Requirement: Controlled evidence window with restore of prior enablement

Operator validation for US-011 SHALL support a controlled evidence window that may temporarily set `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false` to prove fail-closed behavior, then MUST restore the prior recorded operator-approved value (baseline captured before the window) unless the operator explicitly chooses and records a different lasting value.

US-011 MUST NOT be interpreted as a permanent requirement that LinkedIn publication remain `false` after validation.

Default Flow A evidence during the window MUST prefer empty `blog-posts/ready/` / non-mutating probes. Live LinkedIn posts MUST NOT be created as part of US-011 evidence.

#### Scenario: Temporary false then restore baseline

- **WHEN** an operator runs the US-011 evidence procedure with baseline flag `true`
- **THEN** the procedure sets `false`, proves fail-closed, restores `true` (the recorded baseline), and the evidence report records PASS for restore

#### Scenario: US-011 does not require lasting false

- **WHEN** US-011 acceptance is evaluated after a successful restore to the prior operator-approved value
- **THEN** product progress may mark US-011 complete without requiring RUNTIME-STATE LinkedIn publication remain `false`

#### Scenario: Empty ready preferred during guard evidence

- **WHEN** Flow A Manual or Schedule runs are used during US-011 evidence
- **THEN** operators prefer empty ready so the run is a clean no-op and no LinkedIn publication endpoints are invoked by the workflow

### Requirement: Operator-visible pass fail pending for publication guard

US-011 verification MUST emit human-readable overall status with distinct modes and remediation.

Supported overall states MUST include at minimum: `PASS`, `PENDING`, and `FAIL`.

Failure/pending modes MUST distinguish at minimum:

- LinkedIn flag baseline not recorded before window (`FAIL` or blocked start)
- Worker container env does not match intended flag during window (`FAIL`)
- Expected `linkedin_publish_not_enabled` not observed when disabled (`FAIL`)
- Flow A export contains LinkedIn API nodes or LinkedIn API hosts (`FAIL`)
- Restore did not match recorded baseline (`FAIL`)
- Evidence not yet run on server (`PENDING`)
- Secrets printed (`FAIL`)

Evidence MUST be written under `docs/operations/` (for example `us-011-linkedin-publication-guard-validation-YYYY-MM-DD.md`).

#### Scenario: Pass when fail-closed proven and baseline restored

- **WHEN** disable, fail-closed probe, Flow A no-LinkedIn-API check, and baseline restore all succeed
- **THEN** verification reports `PASS` and the ops report records each step

#### Scenario: Fail when restore mismatches baseline

- **WHEN** post-window `.env` or container flag does not match the recorded pre-window baseline and no explicit operator override was recorded
- **THEN** verification reports `FAIL` with remediation to restore the baseline value and recreate the worker

#### Scenario: Pending when evidence not yet collected

- **WHEN** docs and light assertions exist but server evidence for US-011 has not been run
- **THEN** verification reports `PENDING` with remediation to execute the evidence procedure on `192.168.0.194`

### Requirement: BL-004 closure without claiming BL-005

Successful US-011 validation SHALL allow closing backlog item BL-004 (all stories US-009, US-010, US-011 accepted). It MUST NOT mark BL-005 (fully unattended Flow A test) complete.

Product progress and CURRENT-STATE updates MUST occur only after demonstrated evidence.

#### Scenario: BL-004 closable after US-011 evidence

- **WHEN** US-009, US-010, and US-011 acceptance criteria are all demonstrated with evidence
- **THEN** product progress may close BL-004

#### Scenario: BL-005 remains open

- **WHEN** US-011 validation passes
- **THEN** BL-005 and its user stories remain incomplete / not claimed as fully unattended Flow A

### Requirement: No unintended change to completed Flow A activation work

US-011 implementation and evidence MUST NOT deactivate the canonical Flow A workflow, remove the Schedule Trigger, weaken single-flight, or flip LinkedIn enablement as a silent side effect outside the documented controlled window.

Unrelated WIP (BL-007 auto_queue / publish-pending) MUST NOT be mixed into this change.

#### Scenario: Flow A remains activated after US-011

- **WHEN** US-011 evidence completes successfully
- **THEN** `silvermanFlowAPublish01` remains the activated scheduled workflow unless the operator explicitly approved a separate deactivation

#### Scenario: BL-007 WIP excluded

- **WHEN** this change is applied and committed
- **THEN** it does not include auto_queue_pending publish-pending WIP as part of US-011 scope
