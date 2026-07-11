# linkedin-oauth-token-lifecycle

## ADDED Requirements

### Requirement: OAuth preflight for US-003 controlled validation

The US-003 controlled validation script (`deploy/server/run-us003-linkedin-publication-validation-smoke.sh`) MUST invoke the safe OAuth diagnostic (`GET /linkedin/oauth/status` or documented equivalent) before any real LinkedIn publication HTTP call.

The preflight step MUST verify token store presence, member URN, expiry/action-required state, and publication enablement flag without printing or persisting token cleartext.

Preflight failure MUST block real queue and publish-due steps.

#### Scenario: US-003 aborts on missing member URN

- **WHEN** diagnostic reports member URN absent before validation window publish
- **THEN** US-003 script exits fail closed and variant `publish_state` remains unchanged

#### Scenario: US-003 records safe preflight summary

- **WHEN** preflight succeeds
- **THEN** script logs member URN, expiry metadata, and publication-enabled state suitable for Phase 3 report without token values

### Requirement: Operator documentation for validation-window OAuth

Operator documentation MUST state that US-003 real publish validation requires a valid OAuth token store (primary path) and that manual env token fallback is acceptable only when documented and operator-approved for the validation window.

Documentation MUST include reauthorization steps when diagnostic reports `action_required` before attempting real publish.

#### Scenario: Reauthorization guidance before US-003

- **WHEN** operator prepares US-003 validation and diagnostic shows expired token without refresh
- **THEN** documentation directs operator through authorize URL → callback → status recheck before enabling real publish
