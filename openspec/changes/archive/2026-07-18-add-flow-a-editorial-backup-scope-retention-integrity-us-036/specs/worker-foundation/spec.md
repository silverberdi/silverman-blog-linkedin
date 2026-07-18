## ADDED Requirements

### Requirement: metadata/backups is the editorial backup package root

The expected editorial folder `metadata/backups` under the configured base path MUST be treated as the designated root for editorial-state backup packages and manifests defined by `editorial-backup-scope-retention-integrity`.

Folder validation and `GET /health` MUST continue to treat `metadata/backups` as a required directory for aggregate folder readiness. Health and folder validation MUST remain read-only and MUST NOT create backup packages, verify backup integrity, prune retention, or restore editorial state.

#### Scenario: Backups folder remains part of readiness

- **WHEN** folder validation runs and `metadata/backups` exists as a directory
- **THEN** that path is reported ready as part of the existing expected-folder set

#### Scenario: Health does not perform backup operations

- **WHEN** a client calls `GET /health`
- **THEN** the worker does not create, verify, prune, or restore editorial backup packages as part of that request
