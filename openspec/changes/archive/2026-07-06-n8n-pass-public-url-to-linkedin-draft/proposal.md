## Why

The worker now accepts optional `source_public_url` and `topic_theme` on `POST /generate-linkedin-draft` (implemented, deployed, and smoke-tested), but the importable n8n workflow still sends only the original editorial hints. Operators who publish articles to https://silverman.pro must manually craft HTTP bodies or edit nodes outside the version-controlled workflow to pass the public URL into draft generation. This change closes that orchestration gap so LinkedIn drafts can include a natural blog CTA when the operator configures a published article URL—without pretending n8n already receives that URL from a publishing step.

## Goals

- Extend **Set Configuration** with optional `source_public_url` and `topic_theme` fields (safe placeholders in exported JSON).
- Extend **Generate LinkedIn Draft** HTTP Request body to conditionally include those fields only when configured and non-empty after trimming.
- Preserve backward compatibility: empty optional fields are omitted from the request body; existing runs without public URL config behave as today.
- Optionally expose `source_public_url` and `topic_theme` from worker responses on success (and failure when useful) for operator visibility.
- Update README workflow documentation with configuration guidance and publishing-context notes.
- Extend lightweight workflow tests to validate configuration fields, conditional body mapping, and existing security boundaries.

## Non-Goals

- GitHub Pages publishing inside n8n (publishing remains the CLI bridge).
- Execute Command, SSH, filesystem nodes, GitHub API, LinkedIn API, or direct LLM provider calls from n8n.
- Moving or mutating files under `blog-posts/ready/`.
- New worker endpoints or changes to worker request/response behavior.
- Hardcoded production URLs, API keys, or secrets in workflow JSON.
- Auto-wiring `public_url` from a future publishing step (document as future orchestration only).

## What Changes

- Update `n8n/workflows/silverman-blog-linkedin-draft-generation.json`:
  - Add `source_public_url` (default empty string) and `topic_theme` (default empty string or safe editorial placeholder) to **Set Configuration**.
  - Update **Generate LinkedIn Draft** `jsonBody` expression to build required fields plus conditionally spread `source_public_url` and `topic_theme` when trimmed values are non-empty.
  - Optionally update **Set Generate Success** (and failure branch if useful) to surface echoed fields from the worker response.
- Update README **n8n workflow: draft generation orchestration** section with new configuration table rows, publishing guidance, and explicit note that this workflow does not publish to GitHub Pages.
- Extend `tests/test_n8n_workflow.py` with assertions for new config fields, conditional body mapping, and unchanged forbidden-node/secret checks.
- Delta spec for `n8n-worker-orchestration-flow` describing optional public URL context in workflow configuration and generate requests.

## Why a Dedicated HTTP Worker (Not n8n Execute Command)

Public URL validation, prompt construction, metadata persistence, and DeepSeek calls remain in the version-controlled worker. n8n only maps optional configuration into an HTTP Request body. Operators supply `source_public_url` after publish (manually today; automatically in a future orchestration change)—n8n never shells out to the publishing CLI or validates URLs on the host.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `n8n-worker-orchestration-flow`: Extend workflow configuration, generate-linkedin-draft request mapping, README documentation requirements, success visibility, and lightweight validation to support optional `source_public_url` and `topic_theme` with backward-compatible conditional inclusion.

## Impact

- **Repository**: `n8n/workflows/silverman-blog-linkedin-draft-generation.json`, `tests/test_n8n_workflow.py`, README n8n workflow section; OpenSpec delta under `openspec/changes/n8n-pass-public-url-to-linkedin-draft/specs/`.
- **Worker APIs**: No code changes; workflow consumes existing optional fields on `POST /generate-linkedin-draft`.
- **n8n**: Operators edit **Set Configuration** after import to supply a published article URL before running generation with blog CTA; empty defaults preserve current behavior.
- **Editorial data**: Unchanged file layout; worker metadata may include `source_public_url` and `topic_theme` when passed through.
- **Security**: Exported JSON must not contain real secrets or production-only URLs; conditional omission avoids sending empty strings that would trigger worker HTTP 422.
