## ADDED Requirements

### Requirement: Variant objective persisted in campaign metadata at package generation

At LinkedIn derivative package generation, each `variants[]` entry in campaign metadata MUST include:

- `variant` — variant ID
- `audience` — human-readable audience description
- `objective` — publication purpose for the variant (distinct from voice `tone` if present)

For default variant IDs (`executive-recruiter`, `technical-architect`, `engineering-leadership`, `short-provocative`), `objective` MUST match the publication objective defined in editorial canon `#linkedin-derivative-package` variant definitions.

The system MAY continue to include `tone` for generation traceability; `tone` MUST NOT substitute for `objective` in metadata.

#### Scenario: Package metadata includes objective per variant

- **WHEN** Flow A generates a derivative package with default variants
- **THEN** each `variants[]` entry in campaign metadata includes both `audience` and `objective`

#### Scenario: Objective differs from tone

- **WHEN** an implementer inspects `variants[]` metadata for a generated package
- **THEN** `objective` encodes publication purpose and is not identical to the voice `tone` field when both are present
