## Context

The worker change `linkedin-draft-public-blog-url` is complete: `POST /generate-linkedin-draft` accepts optional `source_public_url` and `topic_theme`, validates URLs, echoes fields in responses, and persists them in run metadata. The importable n8n workflow (`silverman-blog-linkedin-draft-generation.json`) orchestrates health → process-ready → process-file → generate-linkedin-draft but only passes `source_relative_path`, `markdown_content`, `source_content_sha256`, `tone`, `audience`, and `variant`.

GitHub Pages publishing is a separate CLI bridge (`docs/workflows/blog-publishing-bridge.md`), not an n8n HTTP step. Operators publish manually, obtain the public URL (e.g. `https://silverman.pro/2026/07/06/.../`), then run draft generation. This design wires optional public URL context through workflow configuration—not through a non-existent publishing node.

ADR-0001 (HTTP-only orchestration) and ADR-0002 (blog canonical, LinkedIn as distribution) remain unchanged.

## Goals / Non-Goals

**Goals:**

- Add `source_public_url` and `topic_theme` to **Set Configuration** with safe exported defaults.
- Conditionally include optional fields in **Generate LinkedIn Draft** `jsonBody` only when trimmed non-empty.
- Surface echoed optional fields on success output when the worker returns them.
- Document operator workflow: configure URL after publish; note future auto-pass from publishing orchestration.
- Extend `tests/test_n8n_workflow.py` without requiring a live n8n instance.

**Non-Goals:**

- GitHub Pages publish in n8n, Execute Command, or CLI invocation from n8n.
- Worker code, new endpoints, or inferring public URLs inside n8n.
- Per-candidate dynamic URLs (v1 uses workflow-level config for all candidates in one run).
- Multi-variant generation loops.

## Decisions

### 1. Workflow-level configuration (Set Configuration node)

**Decision:** Add two string assignments to the existing **Set Configuration** node:

| Field | Exported default | Purpose |
|-------|------------------|---------|
| `source_public_url` | `""` (empty string) | Public article URL after GitHub Pages publish |
| `topic_theme` | `""` (empty string) | Optional CTA wording hint (e.g. `domain-first architecture`) |

**Rationale:** Matches existing pattern for `tone`, `audience`, `variant`, and `worker_*` fields—one edit point before manual runs. Empty defaults preserve backward compatibility and avoid embedding production URLs in git.

**Alternatives considered:**

- **Default `topic_theme` to `domain-first architecture`:** Rejected for export safety; empty default avoids unintended CTA phrasing when no URL is configured. README may suggest example values.
- **Per-item URL from process-file response:** Rejected—worker does not return public URLs; would require publishing integration not in scope.

### 2. Conditional jsonBody expression in Generate LinkedIn Draft

**Decision:** Replace the static `JSON.stringify({...})` with an expression that:

1. Builds a base object with required fields from **Process File** and **Set Configuration** (unchanged mapping).
2. Reads `source_public_url` and `topic_theme` from `$('Set Configuration').first().json`.
3. Trims each optional value (`.trim()` in JavaScript expression).
4. Spreads `source_public_url` into the body only when trimmed value is non-empty; same for `topic_theme`.

Example pattern (implementation may vary slightly for n8n expression syntax):

```javascript
={{ (() => {
  const config = $('Set Configuration').first().json;
  const pf = $('Process File').item.json;
  const body = {
    source_relative_path: pf.relative_path,
    markdown_content: pf.markdown_content,
    source_content_sha256: pf.content_sha256,
    tone: config.tone,
    audience: config.audience,
    variant: config.variant,
  };
  const url = (config.source_public_url || '').trim();
  const theme = (config.topic_theme || '').trim();
  if (url) body.source_public_url = url;
  if (theme) body.topic_theme = theme;
  return JSON.stringify(body);
})() }}
```

**Rationale:** Worker rejects empty/whitespace-only optional strings with HTTP 422. Omitting keys when unset matches worker backward-compatibility contract and existing client behavior.

**Alternatives considered:**

- **Always send keys with empty strings:** Rejected—causes 422 from worker validators.
- **Separate IF node before generate:** Rejected—unnecessary graph complexity for two optional fields.

### 3. Success output visibility

**Decision:** Extend **Set Generate Success** assignments with optional passthrough:

- `source_public_url`: `={{ $json.source_public_url }}` (when present in worker response)
- `topic_theme`: `={{ $json.topic_theme }}`

Failure branch (**Set Generate Failed**): optional same fields if useful; not required—errors and `metadata_path` remain primary.

**Rationale:** Operators verifying CTA configuration see echoed values without opening metadata files. n8n Set nodes tolerate undefined expressions as empty when keys absent.

### 4. No publishing step pretense

**Decision:** README explicitly states:

- This workflow does **not** publish to GitHub Pages.
- `source_public_url` must be set manually in **Set Configuration** after the article is live.
- Future orchestration may chain publish → generate and pass URL automatically.

**Rationale:** Aligns with user constraint; avoids misleading operators that import alone will produce URL-bearing drafts without configuration.

### 5. Test strategy

**Decision:** Extend `tests/test_n8n_workflow.py` with string/structure checks on exported JSON:

- **Set Configuration** assignments include `source_public_url` and `topic_theme`.
- **Generate LinkedIn Draft** `jsonBody` references both field names and conditional logic (trim and/or spread pattern).
- Existing forbidden-node, secret, Bearer, and endpoint tests remain passing.
- No real production URLs or API keys in workflow text.

**Rationale:** Consistent with phase-1 lightweight validation; catches regression without n8n runtime.

### 6. No worker changes

**Decision:** Workflow + docs + tests only.

**Rationale:** Worker capability already shipped and smoke-tested.

## Risks / Trade-offs

- **[Invalid URL in Set Configuration]** → Worker returns HTTP 422; failure branch exposes errors. README warns to use full `https://` URL after publish.
- **[Same URL for all candidates in one run]** → Acceptable for v1 manual runs (typically one post). Per-candidate URLs deferred to future orchestration.
- **[n8n expression syntax drift]** → Keep IIFE pattern readable; document in README; validate via pytest on exported JSON string.
- **[Operator forgets to set URL]** → Behavior unchanged from today (no CTA in draft); README callout.

## Migration Plan

1. Merge change with updated workflow JSON, README, and tests.
2. Re-import or diff-merge workflow in n8n (operators may prefer re-import on clean instance).
3. After publishing a blog post via CLI bridge, set `source_public_url` in **Set Configuration** before manual execute.
4. Confirm success output echoes URL/theme and draft under `linkedin-posts/review/` includes single CTA.

Rollback: revert workflow JSON import or clear optional fields to empty strings; no worker deployment change.

## Open Questions

- None blocking implementation. Optional: whether README should show an example `source_public_url` placeholder like `https://silverman.pro/YYYY/MM/DD/your-slug/` (document only, not in exported JSON default).
