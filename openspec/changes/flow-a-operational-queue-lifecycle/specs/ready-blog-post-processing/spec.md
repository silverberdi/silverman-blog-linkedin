## MODIFIED Requirements

### Requirement: Ready folder candidate discovery

The worker SHALL list candidate entries only from `blog-posts/ready/` under the configured base path.

Discovery MUST be non-recursive (direct children only). The worker MUST NOT accept arbitrary filesystem paths from the HTTP request body.

Discovery MUST ignore hidden filesystem artifacts: `.DS_Store`, files beginning with `._`, and any direct child whose basename begins with `.`.

Ignored hidden artifacts MUST be reported in `ignored_files` with reason `hidden_artifact`.

#### Scenario: Markdown files discovered

- **WHEN** `blog-posts/ready/` contains regular files with a `.md` extension that are not hidden artifacts
- **THEN** those files are considered Markdown candidates for validation

#### Scenario: Non-Markdown files ignored

- **WHEN** `blog-posts/ready/` contains regular files without a `.md` extension
- **THEN** those files are reported in `ignored_files` and are not validated as Markdown candidates

#### Scenario: Subdirectories ignored

- **WHEN** `blog-posts/ready/` contains subdirectories
- **THEN** those entries are reported in `ignored_files` and are not scanned recursively

#### Scenario: Path confinement

- **WHEN** the worker resolves a candidate path
- **THEN** the resolved path MUST remain under `blog-posts/ready/` relative to the configured base path

#### Scenario: Hidden macOS artifacts ignored

- **WHEN** `blog-posts/ready/` contains `.DS_Store` or `._companion.md`
- **THEN** those entries are in `ignored_files` with reason `hidden_artifact` and are not counted as Markdown candidates

## ADDED Requirements

### Requirement: Queued folder is not scanned by process-ready

`POST /process-ready` MUST NOT scan `blog-posts/queued/` for candidates.

`blog-posts/queued/` semantics are defined by `flow-a-operational-queue-lifecycle`.

#### Scenario: Process-ready scans ready only

- **WHEN** a client sends authenticated `POST /process-ready` and sources exist only under `blog-posts/queued/`
- **THEN** the response reports zero Markdown candidates from `ready/` and does not list queued sources
