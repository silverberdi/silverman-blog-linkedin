## Why

The n8n draft-generation workflow can pass `source_public_url` to `POST /generate-linkedin-draft`, but only as a fixed value in **Set Configuration**—valid for smoke tests, not for processing multiple blog posts. Each ready post needs its own expected public URL derived from post metadata and naming conventions. The workflow does not publish to GitHub Pages; it computes the permalink the post would have on [silverman.pro](https://silverman.pro) using the same slug and date conventions as the publishing helper.

## Goals

- Derive `source_public_url` per candidate after **Process File** succeeds and before **Generate LinkedIn Draft**.
- Use `site_base_url` from **Set Configuration** (default `https://silverman.pro`), frontmatter `date`, and public slug from the source filename (remove `.md`; strip leading numeric ordering prefix such as `01-`, `02-`, `003-` when present).
- Pass the derived URL to **Generate LinkedIn Draft** so LinkedIn drafts can include a blog CTA without manual URL entry per run.
- When derivation fails, omit `source_public_url` from the generate request and set `source_public_url_error` with a clear machine-readable reason on the item; do not add a new failure branch—draft generation continues.
- Never reuse a stale URL from **Set Configuration**, a prior loop iteration, or a smoke-test default.
- Keep `topic_theme` optional in **Set Configuration**.
- Preserve existing health, process-ready, process-file, generate success/failure branching, and worker/editorial configuration behavior.

## Non-Goals

- GitHub Pages publishing inside n8n or pretending the workflow receives a publish result.
- LinkedIn API publishing, scheduling, or activating the workflow in n8n or in the exported JSON.
- n8n Execute Command, SSH, Read/Write Binary File, filesystem, GitHub, LinkedIn, OpenAI, DeepSeek direct provider, or local LLM nodes.
- New worker endpoints or changes to `POST /process-file` or `POST /generate-linkedin-draft` contracts.
- Auto-wiring publish-confirmed URLs from a future orchestration step (document as future work only).

## Constraints (preserved)

The change MUST NOT alter these existing workflow boundaries:

- HTTP-only worker orchestration (`GET /health`, `POST /process-ready`, `POST /process-file`, `POST /generate-linkedin-draft`).
- **Set Configuration** fields: `worker_base_url`, `worker_api_key`, `tone`, `audience`, `variant` (behavior unchanged).
- Health check, process-ready, process-file, and generate success/failure branches.
- Exported workflow `"active": false`; no cron, webhook, or other scheduling trigger added.
- No editorial file moves under `blog-posts/`.

## What Changes

- Update `n8n/workflows/silverman-blog-linkedin-draft-generation.json`:
  - Remove `source_public_url` from **Set Configuration**; add `site_base_url` (default `https://silverman.pro`).
  - Insert **Compute Source Public URL** on the **IF Process File OK** success branch, before **Generate LinkedIn Draft**.
  - Update **Generate LinkedIn Draft** to read `source_public_url` from **Compute Source Public URL** (not **Set Configuration**); keep conditional `topic_theme` from **Set Configuration**.
- Update README n8n workflow section: dynamic URL derivation, `site_base_url`, expected-vs-confirmed URL note, updated node flow.
- Extend `tests/test_n8n_workflow.py`: no fixed `source_public_url` in config, compute step present, generate wired to compute output, `source_public_url_error` on failure path, no stale fallback, forbidden-node checks unchanged.

## Example (canonical)

| Input | Value |
|---|---|
| `relative_path` | `blog-posts/ready/01-why-i-did-not-start-with-the-database.md` |
| frontmatter `date` | `2026-07-06 00:00:00 -0500` |
| derived `source_public_url` | `https://silverman.pro/2026/07/06/why-i-did-not-start-with-the-database/` |

## Why a Dedicated HTTP Worker (Not n8n Execute Command)

URL derivation uses only data already returned by `POST /process-file` (`relative_path`, `markdown_content`). The worker continues to own validation, prompt construction, and draft persistence. n8n performs lightweight string/date parsing in a standard Code node—no shell access to the publishing CLI or editorial filesystem.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `n8n-worker-orchestration-flow`: Replace fixed `source_public_url` in **Set Configuration** with per-item derivation; add `site_base_url`; update generate request mapping, README, and lightweight validation.

## Impact

- **Repository**: `n8n/workflows/silverman-blog-linkedin-draft-generation.json`, `tests/test_n8n_workflow.py`, README n8n workflow section; OpenSpec delta under `openspec/changes/n8n-compute-public-url-for-linkedin-draft/specs/`.
- **Worker APIs**: No code changes; workflow consumes existing optional `source_public_url` on `POST /generate-linkedin-draft`.
- **n8n**: Operators configure `site_base_url` once; each run derives the article URL per post. Re-import required after merge; workflow remains inactive in export.
- **Editorial data**: Unchanged file layout; derived URL reflects expected silverman.pro permalink convention aligned with `openspec/specs/github-pages-blog-publishing/spec.md`.
- **Security**: No new secrets; exported JSON must not embed per-article URLs as fixed configuration.
