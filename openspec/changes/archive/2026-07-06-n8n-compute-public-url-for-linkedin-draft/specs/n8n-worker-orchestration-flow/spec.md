## ADDED Requirements

### Requirement: Per-item source public URL derivation

After `POST /process-file` succeeds for a candidate, the workflow SHALL derive an expected `source_public_url` for that item in **Compute Source Public URL** (n8n Code node) before calling `POST /generate-linkedin-draft`.

Derivation MUST use:

- `site_base_url` from **Set Configuration** (default `https://silverman.pro`; trailing slash stripped before compose)
- post date from YAML frontmatter in the process-file `markdown_content` (`date:` field; date portion `YYYY-MM-DD`, e.g. from `2026-07-06 00:00:00 -0500`)
- public slug from the basename of process-file `relative_path`: remove the `.md` extension, then strip a leading numeric ordering prefix matching `^\d+-` when present (e.g. `01-`, `02-`, `003-`; aligned with `openspec/specs/github-pages-blog-publishing/spec.md` public slug rules)

After prefix stripping, the public slug MUST match `^[a-z0-9]+(?:-[a-z0-9]+)*$`. If it does not, derivation fails.

The derived URL format MUST be:

`{site_base_url}/{YYYY}/{MM}/{DD}/{public-slug}/`

(with no duplicate slashes between base URL and path segments; trailing slash on the final URL)

The workflow MUST NOT reuse a fixed `source_public_url` from **Set Configuration** for generate requests.

The workflow MUST NOT reuse a `source_public_url` computed for a different candidate in the same run.

When derivation fails (missing `relative_path`, missing or unparseable frontmatter `date`, or invalid public slug after normalization), the workflow MUST:

- omit `source_public_url` from the generate request body (no fixed, stale, or prior-iteration fallback)
- set `source_public_url_error` on the current item to a non-empty machine-readable reason string (for example `missing_relative_path`, `missing_frontmatter_date`, `invalid_public_slug`)
- continue to **Generate LinkedIn Draft** without a new failure branch solely for URL derivation failure

#### Scenario: Derive URL from relative_path and frontmatter date

- **WHEN** process-file returns `relative_path` `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` and `markdown_content` contains frontmatter `date: 2026-07-06 00:00:00 -0500`
- **THEN** the workflow derives `source_public_url` `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/` before generate-linkedin-draft

#### Scenario: Public slug without numeric prefix

- **WHEN** process-file returns `relative_path` `blog-posts/ready/my-post.md` and frontmatter date parses to `2026-07-06`
- **THEN** the derived public slug is `my-post` and the URL path includes `/2026/07/06/my-post/`

#### Scenario: Derivation failure omits URL and sets error

- **WHEN** process-file succeeds but frontmatter `date` is missing or unparseable
- **THEN** generate-linkedin-draft is called without a `source_public_url` key, the current item has a non-empty `source_public_url_error` (for example `missing_frontmatter_date`), and no URL from **Set Configuration** or a prior candidate is used

#### Scenario: Invalid public slug fails derivation

- **WHEN** process-file returns a basename that, after `.md` removal and optional numeric prefix strip, does not match `^[a-z0-9]+(?:-[a-z0-9]+)*$`
- **THEN** the item has a non-empty `source_public_url_error` (for example `invalid_public_slug`) and generate-linkedin-draft is called without a `source_public_url` key

#### Scenario: Missing relative_path fails derivation

- **WHEN** process-file succeeds but `relative_path` is missing or empty on the item passed to **Compute Source Public URL**
- **THEN** the item has a non-empty `source_public_url_error` (for example `missing_relative_path`) and generate-linkedin-draft is called without a `source_public_url` key

#### Scenario: No stale URL from prior loop iteration

- **WHEN** the workflow processes multiple candidates in one run and derivation fails for the current candidate
- **THEN** generate-linkedin-draft for that candidate does not include a `source_public_url` taken from a previously processed candidate

#### Scenario: Compute step sits between process-file and generate

- **WHEN** the workflow export is inspected
- **THEN** **Compute Source Public URL** appears on the **IF Process File OK** success path immediately before **Generate LinkedIn Draft**

### Requirement: Site base URL in workflow configuration

The workflow **Set Configuration** node SHALL include a string field `site_base_url` for the canonical public blog site root.

The exported workflow JSON MUST default `site_base_url` to `https://silverman.pro`.

The exported workflow JSON MUST NOT include a `source_public_url` assignment in **Set Configuration**.

The workflow **Set Configuration** node SHALL retain an optional string field `topic_theme` with default empty string.

#### Scenario: Set Configuration exposes site_base_url not source_public_url

- **WHEN** the workflow export is inspected
- **THEN** **Set Configuration** assignments include `site_base_url` and do not include `source_public_url`

#### Scenario: Default site_base_url is safe for git

- **WHEN** the workflow JSON is reviewed in git without operator post-import edits
- **THEN** `site_base_url` is `https://silverman.pro`, not a per-article smoke-test URL

#### Scenario: topic_theme remains optional in Set Configuration

- **WHEN** the workflow export is inspected
- **THEN** **Set Configuration** assignments include `topic_theme` with default empty string

### Requirement: Workflow export remains inactive

The exported workflow JSON MUST keep `"active": false`.

This change MUST NOT activate the workflow in the repository export.

#### Scenario: Exported workflow is not active

- **WHEN** the workflow JSON is parsed
- **THEN** the top-level `active` field is `false`

## MODIFIED Requirements

### Requirement: HTTP-only orchestration boundary

The workflow MUST orchestrate worker integration exclusively through n8n **HTTP Request** nodes (plus standard n8n control nodes such as Manual Trigger, IF, Split In Batches / Loop, Set, Code, and No Operation).

The workflow MUST NOT use Execute Command, SSH, Read/Write Binary File, local filesystem nodes, or any node that reads or writes editorial Markdown on the n8n host.

The workflow MUST NOT call DeepSeek, OpenAI, ChatGPT, or local LLM provider APIs directly.

The workflow MUST NOT publish to LinkedIn or GitHub.

The workflow MUST treat the worker as the only filesystem and LLM boundary.

**Compute Source Public URL** MUST be implemented as an n8n Code node (`n8n-nodes-base.code`) that performs string and date parsing only on data already returned by `POST /process-file`; it MUST NOT read editorial files from the n8n host.

#### Scenario: Worker calls use HTTP Request nodes

- **WHEN** the workflow invokes `GET /health`, `POST /process-ready`, `POST /process-file`, or `POST /generate-linkedin-draft`
- **THEN** each invocation is performed by an HTTP Request node targeting the configured worker base URL

#### Scenario: Compute step uses Code node not filesystem access

- **WHEN** the workflow export is inspected
- **THEN** **Compute Source Public URL** is a Code node and the workflow does not use Execute Command, SSH, or filesystem nodes for URL derivation

#### Scenario: No Execute Command in workflow

- **WHEN** the workflow export is inspected
- **THEN** it does not contain an Execute Command node type

#### Scenario: No direct LLM provider nodes

- **WHEN** the workflow export is inspected
- **THEN** it does not contain HTTP Request nodes whose URLs target DeepSeek, OpenAI, or other LLM provider hosts

### Requirement: LinkedIn draft generation via worker endpoint

For each candidate where `POST /process-file` succeeded, the workflow SHALL call authenticated `POST /generate-linkedin-draft` with a JSON body containing at minimum:

- `source_relative_path` from the candidate / process-file response
- `markdown_content` from the process-file response
- `source_content_sha256` from the process-file `content_sha256` field when present

The body MAY include `title` when available or derivable from the blog Markdown (for example first `#` heading); otherwise `title` MAY be omitted.

The body MUST include static editorial hint fields configured in the workflow (for example `tone`, `audience`, `variant`) as documented constants—not dynamic secrets.

The body MAY include optional `source_public_url` when derived for the current item by **Compute Source Public URL** and non-empty after trimming. When the per-item derived value is empty or unavailable, the workflow MUST NOT include a `source_public_url` key in the JSON body.

The body MAY include optional `topic_theme` when configured in **Set Configuration** and non-empty after trimming. When `topic_theme` is empty or whitespace-only in configuration, the workflow MUST NOT include that key in the JSON body.

The workflow MUST NOT call `POST /write-linkedin-draft` unless a future change explicitly requires a separate write step; `POST /generate-linkedin-draft` persists the draft when generation succeeds.

#### Scenario: Generate request maps process-file output

- **WHEN** process-file returns `relative_path`, `markdown_content`, and `content_sha256`
- **THEN** generate-linkedin-draft is called with `source_relative_path`, `markdown_content`, and `source_content_sha256` mapped from those fields

#### Scenario: Editorial hints are static workflow configuration

- **WHEN** generate-linkedin-draft is called
- **THEN** `tone`, `audience`, and `variant` are supplied from fixed workflow configuration documented in README, not from n8n filesystem reads

#### Scenario: Derived source_public_url included when available

- **WHEN** **Compute Source Public URL** produces a non-empty `source_public_url` (for example `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/`)
- **THEN** generate-linkedin-draft is called with `source_public_url` in the JSON body with that trimmed value

#### Scenario: Derived source_public_url omitted when unavailable

- **WHEN** **Compute Source Public URL** produces an empty or missing `source_public_url`
- **THEN** the generate-linkedin-draft JSON body does not include a `source_public_url` key

#### Scenario: Generate reads source_public_url from current item after compute step

- **WHEN** **Generate LinkedIn Draft** `jsonBody` is inspected
- **THEN** it reads `source_public_url` from the current item produced by **Compute Source Public URL** (for example `const item = $json; const url = (item.source_public_url || '').trim();`), and does not read `source_public_url` from **Set Configuration**, `config.source_public_url`, or a prior candidate item

#### Scenario: Optional topic_theme included when configured

- **WHEN** **Set Configuration** has `topic_theme` set to a non-empty string after trimming (for example `domain-first architecture`)
- **THEN** generate-linkedin-draft is called with `topic_theme` in the JSON body with that trimmed value

#### Scenario: Optional topic_theme omitted when empty

- **WHEN** **Set Configuration** has `topic_theme` empty or whitespace-only
- **THEN** the generate-linkedin-draft JSON body does not include a `topic_theme` key

### Requirement: Workflow documentation in README

The repository README SHALL document:

- path to the workflow JSON file
- steps to import into n8n
- how to configure worker base URL and API key (variables or credentials)
- `site_base_url` in **Set Configuration** and how `source_public_url` is derived per post from frontmatter date and filename (expected URL convention—not publish-confirmed)
- optional `topic_theme` in **Set Configuration**
- explicit note that this workflow does not publish to GitHub Pages or LinkedIn and that future orchestration may pass publish-confirmed URLs automatically
- expected node flow summary including **Compute Source Public URL**
- explicit note that n8n does not touch editorial folders directly

#### Scenario: Operator can configure from README alone

- **WHEN** a new operator follows README instructions
- **THEN** they can import the workflow, set worker base URL and API key, optionally set `site_base_url` and `topic_theme`, and run a manual execution against a healthy worker without manually entering per-article URLs

### Requirement: Lightweight workflow validation

The repository MUST include lightweight automated validation that the workflow JSON file exists, parses as JSON, and contains expected node types or names (for example Manual Trigger, HTTP Request, IF)—without requiring a live n8n instance in CI.

Validation MUST NOT be over-engineered (no full n8n runtime integration required in phase 1).

Validation MUST assert that **Set Configuration** includes `site_base_url` and does not include `source_public_url`.

Validation MUST assert that **Compute Source Public URL** exists directly before **Generate LinkedIn Draft** and that **Generate LinkedIn Draft** request body mapping reads `source_public_url` from the current item produced by **Compute Source Public URL** (for example `$json` / `item.source_public_url`), not from **Set Configuration**, `config.source_public_url`, or prior items.

Validation MUST assert that **Set Configuration** includes optional `topic_theme` and that **Generate LinkedIn Draft** conditionally includes `topic_theme` (not blindly as empty strings).

Validation MUST assert the workflow export has `"active": false`.

Validation MUST assert that **Compute Source Public URL** is a Code node (`n8n-nodes-base.code`).

Validation MUST continue to assert the workflow contains no real secrets and no Execute Command, SSH, Read/Write Binary File, filesystem, GitHub, LinkedIn, OpenAI, DeepSeek direct provider, or local LLM nodes, and that authenticated worker calls use Bearer expressions from `worker_api_key`.

#### Scenario: CI or local check catches broken export

- **WHEN** the workflow JSON is accidentally corrupted or missing required nodes
- **THEN** the validation script or test fails with a clear message

#### Scenario: Validation catches hardcoded source_public_url in Set Configuration

- **WHEN** **Set Configuration** includes a `source_public_url` assignment
- **THEN** the validation test fails

#### Scenario: Validation catches missing compute step

- **WHEN** **Compute Source Public URL** is absent from the workflow export
- **THEN** the validation test fails

#### Scenario: Validation catches generate reading config source_public_url

- **WHEN** **Generate LinkedIn Draft** `jsonBody` reads `source_public_url` from **Set Configuration**
- **THEN** the validation test fails

#### Scenario: Validation catches active workflow export

- **WHEN** the workflow JSON has `"active": true`
- **THEN** the validation test fails

#### Scenario: Validation catches missing derivation error handling

- **WHEN** **Compute Source Public URL** `jsCode` does not set `source_public_url_error` on derivation failure
- **THEN** the validation test fails

#### Scenario: Validation catches unconditional empty optional fields

- **WHEN** **Generate LinkedIn Draft** always sends `topic_theme` as empty string literals without conditional omission
- **THEN** the validation test fails or detects the anti-pattern per test design

## REMOVED Requirements

### Requirement: Optional public blog URL context in workflow configuration

**Reason:** `source_public_url` is derived per item after process-file; a fixed optional field in **Set Configuration** caused stale smoke-test URLs and is replaced by `site_base_url` plus per-item derivation.

**Migration:** Re-import the updated workflow. Configure `site_base_url` if not using the default `https://silverman.pro`. Ensure editorial Markdown includes frontmatter `date` for CTA URLs. `topic_theme` remains optional in **Set Configuration**.
