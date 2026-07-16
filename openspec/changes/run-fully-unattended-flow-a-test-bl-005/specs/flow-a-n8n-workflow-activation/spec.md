## MODIFIED Requirements

### Requirement: US-011 and BL-005 remain out of scope

This activation capability MUST NOT own LinkedIn publication enablement and MUST NOT flip `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` as part of default US-010 implementation or evidence.

Closing US-011 (LinkedIn publication disabled until separately approved) is owned by capability `flow-a-linkedin-publication-guard` after demonstrated evidence — not by this activation capability.

Closing BL-005 (fully unattended Flow A test) is owned by capability `flow-a-unattended-e2e-validation` after demonstrated Manual and Schedule evidence — not by this activation capability.

#### Scenario: Activation does not close US-011 by itself

- **WHEN** US-010 activation validation passes without a separate `flow-a-linkedin-publication-guard` evidence report
- **THEN** product progress for US-011 remains incomplete

#### Scenario: LinkedIn publication flag not flipped by activation procedures

- **WHEN** default US-010 apply and evidence procedures run
- **THEN** they do not change `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`

#### Scenario: Activation does not close BL-005 by itself

- **WHEN** US-010 activation validation passes without a separate `flow-a-unattended-e2e-validation` evidence report
- **THEN** product progress for BL-005 remains incomplete
