# n8n-worker-orchestration-flow

## Purpose

Importable n8n workflow JSON that orchestrates the Silverman Blog LinkedIn worker over HTTP only—scanning ready blog posts, reading each Markdown candidate, generating one LinkedIn review draft per candidate via `POST /generate-linkedin-draft` (DeepSeek inside the worker), and branching on structured JSON responses—without Execute Command, direct filesystem access, direct LLM calls, publishing, or mutating source blog files.

## Requirements

### Requirement: Importable workflow artifact location

The repository SHALL include an importable n8n workflow export at `n8n/workflows/silverman-blog-linkedin-draft-generation.json`.

The JSON MUST be valid n8n workflow format suitable for import through the n8n UI.

The workflow name SHOULD clearly identify its purpose (for example, referencing Silverman blog LinkedIn draft generation).

#### Scenario: Workflow file present for import

- **WHEN** an operator opens the n8n import workflow dialog
- **THEN** they can import `n8n/workflows/silverman-blog-linkedin-draft-generation.json` without manual reconstruction of nodes

#### Scenario: Workflow JSON is parseable

- **WHEN** the workflow JSON file is parsed as JSON
- **THEN** parsing succeeds and the document contains n8n workflow node definitions

### Requirement: HTTP-only orchestration boundary

The workflow MUST orchestrate worker integration exclusively through n8n **HTTP Request** nodes (plus standard n8n control nodes such as Manual Trigger, IF, Split In Batches / Loop, Set, and No Operation).

The workflow MUST NOT use Execute Command, SSH, Read/Write Binary File, local filesystem nodes, or any node that reads or writes editorial Markdown on the n8n host.

The workflow MUST NOT call DeepSeek, OpenAI, ChatGPT, or local LLM provider APIs directly.

The workflow MUST NOT publish to LinkedIn or GitHub.

The workflow MUST treat the worker as the only filesystem and LLM boundary.

#### Scenario: Worker calls use HTTP Request nodes

- **WHEN** the workflow invokes `GET /health`, `POST /process-ready`, `POST /process-file`, or `POST /generate-linkedin-draft`
- **THEN** each invocation is performed by an HTTP Request node targeting the configured worker base URL

#### Scenario: No Execute Command in workflow

- **WHEN** the workflow export is inspected
- **THEN** it does not contain an Execute Command node type

#### Scenario: No direct LLM provider nodes

- **WHEN** the workflow export is inspected
- **THEN** it does not contain HTTP Request nodes whose URLs target DeepSeek, OpenAI, or other LLM provider hosts

### Requirement: Configurable worker base URL without hardcoded secrets

The workflow MUST make the worker base URL configurable without editing node URLs in multiple places—via workflow variables, a single clearly named placeholder, or equivalent n8n pattern documented in README.

The workflow JSON MUST NOT contain real API keys, Bearer tokens, or other production secrets.

Worker API authentication MUST use a placeholder expression or n8n credential pattern (for example `Authorization: Bearer {{$vars.worker_api_key}}` or Header Auth credential) documented for post-import configuration.

#### Scenario: Base URL is environment-portable

- **WHEN** an operator imports the workflow for local development versus Docker on the Linux server
- **THEN** they can point all worker HTTP Request nodes at the correct base URL by changing one variable or documented configuration step

#### Scenario: Exported JSON has no embedded secrets

- **WHEN** the workflow JSON is reviewed in git
- **THEN** it does not include literal values matching production API keys or Bearer tokens

### Requirement: Manual trigger entry point

The workflow SHALL start with a Manual Trigger node for local and manual execution.

#### Scenario: Manual execution

- **WHEN** an operator clicks Execute Workflow in n8n with this workflow open
- **THEN** execution begins at the Manual Trigger and proceeds to worker health check without requiring a cron or webhook

### Requirement: Health check before processing

After the Manual Trigger, the workflow SHALL call `GET /health` on the worker using an HTTP Request node.

The workflow SHOULD fail fast or stop cleanly when the health response indicates the worker or editorial layout is not ready (per worker-foundation health semantics).

#### Scenario: Health check precedes process-ready

- **WHEN** the workflow runs from Manual Trigger
- **THEN** `GET /health` is invoked before `POST /process-ready`

### Requirement: Ready-folder scan via process-ready

The workflow SHALL call authenticated `POST /process-ready` on the worker after the health check.

The HTTP Request MUST send `Authorization: Bearer <worker_api_key>` using the configured placeholder or credential pattern.

The workflow MUST NOT move, delete, or modify files under `blog-posts/ready/`, `blog-posts/processed/`, or `blog-posts/error/`.

#### Scenario: Process-ready uses Bearer authentication

- **WHEN** `POST /process-ready` is invoked from the workflow
- **THEN** the request includes an `Authorization` header with Bearer scheme and does not embed the key as a hardcoded literal in the exported JSON

#### Scenario: Process-ready failure stops orchestration

- **WHEN** `POST /process-ready` returns `status` failed (for example `folders_ready` false or metadata directory unavailable)
- **THEN** the workflow does not attempt per-file processing and exits with visible error context from the response

### Requirement: Clean stop when no valid candidates

When `POST /process-ready` completes successfully but `valid_count` is zero (or `valid_files` is empty), the workflow SHALL stop cleanly without calling `POST /process-file` or `POST /generate-linkedin-draft`.

#### Scenario: No candidates in ready folder

- **WHEN** `POST /process-ready` returns `status` completed with `valid_count` 0 and empty `valid_files`
- **THEN** the workflow ends without further worker calls and without error state attributable to missing files

#### Scenario: Valid candidates present

- **WHEN** `POST /process-ready` returns one or more entries in `valid_files`
- **THEN** the workflow proceeds to iterate over those candidates

### Requirement: Per-candidate file read via process-file

For each entry in `valid_files` from `POST /process-ready`, the workflow SHALL call authenticated `POST /process-file` with JSON body `{ "relative_path": "<candidate.relative_path>" }`.

The workflow MUST use the `relative_path` from the candidate object (not invent paths).

If `POST /process-file` returns `status` failed for a candidate, the workflow SHOULD record errors from the response and continue or branch per design without moving source blog files.

#### Scenario: Process-file receives candidate path

- **WHEN** a candidate has `relative_path` `blog-posts/ready/my-post.md`
- **THEN** `POST /process-file` is called with that exact `relative_path` in the JSON body

#### Scenario: Process-file success supplies markdown

- **WHEN** `POST /process-file` returns `status` completed
- **THEN** the workflow has access to `markdown_content` and `content_sha256` for the subsequent generate step

### Requirement: LinkedIn draft generation via worker endpoint

For each candidate where `POST /process-file` succeeded, the workflow SHALL call authenticated `POST /generate-linkedin-draft` with a JSON body containing at minimum:

- `source_relative_path` from the candidate / process-file response
- `markdown_content` from the process-file response
- `source_content_sha256` from the process-file `content_sha256` field when present

The body MAY include `title` when available or derivable from the blog Markdown (for example first `#` heading); otherwise `title` MAY be omitted.

The body MUST include static editorial hint fields configured in the workflow (for example `tone`, `audience`, `variant`) as documented constants—not dynamic secrets.

The workflow MUST NOT call `POST /write-linkedin-draft` unless a future change explicitly requires a separate write step; `POST /generate-linkedin-draft` persists the draft when generation succeeds.

#### Scenario: Generate request maps process-file output

- **WHEN** process-file returns `relative_path`, `markdown_content`, and `content_sha256`
- **THEN** generate-linkedin-draft is called with `source_relative_path`, `markdown_content`, and `source_content_sha256` mapped from those fields

#### Scenario: Editorial hints are static workflow configuration

- **WHEN** generate-linkedin-draft is called
- **THEN** `tone`, `audience`, and `variant` are supplied from fixed workflow configuration documented in README, not from n8n filesystem reads

### Requirement: Branch on generate-linkedin-draft status

After each `POST /generate-linkedin-draft` call, the workflow SHALL branch on the response `status` field using an IF node (or equivalent).

The workflow MUST handle at least:

- `status` `completed` — draft written under `linkedin-posts/review/` by the worker
- `status` `failed` — no draft written (or draft not successfully persisted per worker response)

#### Scenario: Completed generation branch

- **WHEN** `POST /generate-linkedin-draft` returns `status` `completed` and `draft_written` true
- **THEN** the workflow follows the success branch and exposes `draft_relative_path` and `metadata_path` from the response for operator visibility

#### Scenario: Failed generation branch

- **WHEN** `POST /generate-linkedin-draft` returns `status` `failed`
- **THEN** the workflow follows the failure branch and exposes `errors` and `metadata_path` when present in the response

### Requirement: Source blog files remain in ready

The workflow MUST NOT invoke any worker endpoint or n8n action that moves source blog posts to `blog-posts/processed/` or `blog-posts/error/`.

Blog posts remain canonical in `blog-posts/ready/` after workflow execution.

#### Scenario: No post-run file moves

- **WHEN** the workflow completes processing all candidates
- **THEN** source blog Markdown files remain in `blog-posts/ready/` unchanged by this workflow

### Requirement: Review drafts as human-review artifacts

On successful generation, the workflow SHALL rely on the worker to persist the draft under `linkedin-posts/review/`.

The workflow MUST NOT auto-approve or auto-publish drafts.

#### Scenario: Draft available for human review

- **WHEN** generation completes with `draft_written` true
- **THEN** the draft file exists under `linkedin-posts/review/` on the worker filesystem and the workflow output includes `draft_relative_path` for operator reference

### Requirement: Workflow documentation in README

The repository README SHALL document:

- path to the workflow JSON file
- steps to import into n8n
- how to configure worker base URL and API key (variables or credentials)
- expected node flow summary and branching behavior
- explicit note that n8n does not touch editorial folders directly

#### Scenario: Operator can configure from README alone

- **WHEN** a new operator follows README instructions
- **THEN** they can import the workflow, set base URL and API key, and run a manual execution against a healthy worker

### Requirement: Lightweight workflow validation

The repository MUST include lightweight automated validation that the workflow JSON file exists, parses as JSON, and contains expected node types or names (for example Manual Trigger, HTTP Request, IF)—without requiring a live n8n instance in CI.

Validation MUST NOT be over-engineered (no full n8n runtime integration required in phase 1).

#### Scenario: CI or local check catches broken export

- **WHEN** the workflow JSON is accidentally corrupted or missing required nodes
- **THEN** the validation script or test fails with a clear message
