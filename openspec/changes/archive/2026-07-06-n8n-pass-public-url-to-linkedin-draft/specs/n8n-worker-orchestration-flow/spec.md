## MODIFIED Requirements

### Requirement: LinkedIn draft generation via worker endpoint

For each candidate where `POST /process-file` succeeded, the workflow SHALL call authenticated `POST /generate-linkedin-draft` with a JSON body containing at minimum:

- `source_relative_path` from the candidate / process-file response
- `markdown_content` from the process-file response
- `source_content_sha256` from the process-file `content_sha256` field when present

The body MAY include `title` when available or derivable from the blog Markdown (for example first `#` heading); otherwise `title` MAY be omitted.

The body MUST include static editorial hint fields configured in the workflow (for example `tone`, `audience`, `variant`) as documented constants—not dynamic secrets.

The body MAY include optional `source_public_url` and `topic_theme` when configured in **Set Configuration** and non-empty after trimming. When either optional field is empty or whitespace-only in configuration, the workflow MUST NOT include that key in the JSON body.

The workflow MUST NOT call `POST /write-linkedin-draft` unless a future change explicitly requires a separate write step; `POST /generate-linkedin-draft` persists the draft when generation succeeds.

#### Scenario: Generate request maps process-file output

- **WHEN** process-file returns `relative_path`, `markdown_content`, and `content_sha256`
- **THEN** generate-linkedin-draft is called with `source_relative_path`, `markdown_content`, and `source_content_sha256` mapped from those fields

#### Scenario: Editorial hints are static workflow configuration

- **WHEN** generate-linkedin-draft is called
- **THEN** `tone`, `audience`, and `variant` are supplied from fixed workflow configuration documented in README, not from n8n filesystem reads

#### Scenario: Optional source_public_url included when configured

- **WHEN** **Set Configuration** has `source_public_url` set to a non-empty string after trimming (for example `https://silverman.pro/2026/07/06/my-post/`)
- **THEN** generate-linkedin-draft is called with `source_public_url` in the JSON body with that trimmed value

#### Scenario: Optional source_public_url omitted when empty

- **WHEN** **Set Configuration** has `source_public_url` empty or whitespace-only
- **THEN** the generate-linkedin-draft JSON body does not include a `source_public_url` key

#### Scenario: Optional topic_theme included when configured

- **WHEN** **Set Configuration** has `topic_theme` set to a non-empty string after trimming (for example `domain-first architecture`)
- **THEN** generate-linkedin-draft is called with `topic_theme` in the JSON body with that trimmed value

#### Scenario: Optional topic_theme omitted when empty

- **WHEN** **Set Configuration** has `topic_theme` empty or whitespace-only
- **THEN** the generate-linkedin-draft JSON body does not include a `topic_theme` key

### Requirement: Branch on generate-linkedin-draft status

After each `POST /generate-linkedin-draft` call, the workflow SHALL branch on the response `status` field using an IF node (or equivalent).

The workflow MUST handle at least:

- `status` `completed` — draft written under `linkedin-posts/review/` by the worker
- `status` `failed` — no draft written (or draft not successfully persisted per worker response)

#### Scenario: Completed generation branch

- **WHEN** `POST /generate-linkedin-draft` returns `status` `completed` and `draft_written` true
- **THEN** the workflow follows the success branch and exposes `draft_relative_path` and `metadata_path` from the response for operator visibility

#### Scenario: Completed generation exposes optional public context when echoed

- **WHEN** `POST /generate-linkedin-draft` returns `status` `completed` and the response includes `source_public_url` and/or `topic_theme`
- **THEN** the success branch exposes those fields from the worker response for operator visibility

#### Scenario: Failed generation branch

- **WHEN** `POST /generate-linkedin-draft` returns `status` `failed`
- **THEN** the workflow follows the failure branch and exposes `errors` and `metadata_path` when present in the response

### Requirement: Workflow documentation in README

The repository README SHALL document:

- path to the workflow JSON file
- steps to import into n8n
- how to configure worker base URL and API key (variables or credentials)
- optional `source_public_url` and `topic_theme` fields in **Set Configuration**, including that `source_public_url` should be supplied after the blog article has been published to the public site
- explicit note that this workflow does not publish to GitHub Pages and that future orchestration may pass `public_url` automatically from a publishing step
- expected node flow summary and branching behavior
- explicit note that n8n does not touch editorial folders directly

#### Scenario: Operator can configure from README alone

- **WHEN** a new operator follows README instructions
- **THEN** they can import the workflow, set base URL and API key, optionally set public URL context after publish, and run a manual execution against a healthy worker

### Requirement: Lightweight workflow validation

The repository MUST include lightweight automated validation that the workflow JSON file exists, parses as JSON, and contains expected node types or names (for example Manual Trigger, HTTP Request, IF)—without requiring a live n8n instance in CI.

Validation MUST NOT be over-engineered (no full n8n runtime integration required in phase 1).

Validation MUST assert that **Set Configuration** includes `source_public_url` and `topic_theme` configuration fields.

Validation MUST assert that **Generate LinkedIn Draft** request body mapping references `source_public_url` and `topic_theme` and conditionally includes them (not blindly as empty strings).

Validation MUST continue to assert the workflow contains no real secrets, no Execute Command, SSH, filesystem, GitHub, LinkedIn, OpenAI, DeepSeek direct provider, or local LLM nodes, and that authenticated worker calls use Bearer expressions from `worker_api_key`.

#### Scenario: CI or local check catches broken export

- **WHEN** the workflow JSON is accidentally corrupted or missing required nodes
- **THEN** the validation script or test fails with a clear message

#### Scenario: Validation catches missing optional public URL configuration

- **WHEN** **Set Configuration** omits `source_public_url` or `topic_theme` from the exported workflow
- **THEN** the validation test fails

#### Scenario: Validation catches unconditional empty optional fields

- **WHEN** **Generate LinkedIn Draft** always sends `source_public_url` or `topic_theme` as empty string literals without conditional omission
- **THEN** the validation test fails or detects the anti-pattern per test design

## ADDED Requirements

### Requirement: Optional public blog URL context in workflow configuration

The workflow **Set Configuration** node SHALL include optional string fields `source_public_url` and `topic_theme` alongside existing worker and editorial configuration.

The exported workflow JSON MUST use a safe default for `source_public_url` (empty string or documented placeholder—not a production-only secret or live article URL required for import).

The exported workflow JSON MUST NOT embed real API keys, Bearer tokens, or production secrets in these fields.

#### Scenario: Set Configuration exposes optional public URL fields

- **WHEN** the workflow export is inspected
- **THEN** **Set Configuration** assignments include `source_public_url` and `topic_theme`

#### Scenario: Default source_public_url is safe for git

- **WHEN** the workflow JSON is reviewed in git without operator post-import edits
- **THEN** `source_public_url` is empty or a non-secret placeholder documented in README, not a required production URL
