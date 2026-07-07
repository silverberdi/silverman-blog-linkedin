## Context

The importable workflow `n8n/workflows/silverman-blog-linkedin-draft-generation.json` orchestrates:

```
Manual Trigger
  → Set Configuration
  → Health Check (GET /health)
  → Process Ready (POST /process-ready)
  → [per candidate] Process File (POST /process-file)
  → IF Process File OK
       ├─ true  → Compute Source Public URL → Generate LinkedIn Draft (POST /generate-linkedin-draft)
       └─ false → (existing failure branch, unchanged)
```

Change `n8n-pass-public-url-to-linkedin-draft` added optional `source_public_url` and `topic_theme` to **Set Configuration** and conditional inclusion in **Generate LinkedIn Draft**. Smoke validation confirmed the worker accepts a configured URL and the draft includes it once.

The workflow does **not** publish to GitHub Pages. The publishing helper spec (`openspec/specs/github-pages-blog-publishing/spec.md`) defines the canonical public URL shape: `https://silverman.pro/YYYY/MM/DD/<public-slug>/`, where `<public-slug>` strips a leading numeric ordering prefix from the editorial filename (e.g. `01-why-i-did-not-start-with-the-database` → `why-i-did-not-start-with-the-database`).

`POST /process-file` returns `relative_path`, `filename`, `markdown_content`, and `content_sha256` but does not parse frontmatter into separate fields. Frontmatter `date` is available inside `markdown_content`.

The exported workflow currently has `"active": false` and must remain so.

## Goals / Non-Goals

**Goals:**

- Derive `source_public_url` per processed item using `site_base_url`, frontmatter `date`, and filename-based public slug.
- Wire derived URL into **Generate LinkedIn Draft**; keep `topic_theme` optional from **Set Configuration**.
- On derivation failure: omit `source_public_url` from the generate body; set `source_public_url_error` with a human-readable reason on the item.
- Never fall back to a fixed config URL or a value from a prior loop iteration.
- Preserve all existing nodes, branches, forbidden-node boundaries, and worker calls outside this insertion point.

**Non-Goals:**

- Worker endpoint or response changes.
- GitHub Pages publish execution, LinkedIn API, scheduling, workflow activation.
- Execute Command, SSH, Read/Write Binary File, filesystem, GitHub, LinkedIn, OpenAI, DeepSeek direct provider, or local LLM nodes in n8n.
- Passing publish-confirmed URLs from a future orchestration step.

## Decisions

### 1. Per-item compute node after Process File success

**Decision:** Add a node named **Compute Source Public URL** on the **IF Process File OK** success branch, between **Process File** and **Generate LinkedIn Draft**.

**Rationale:** URL is per candidate; computation must run inside the loop after `markdown_content` is available.

**Alternatives considered:**

| Alternative | Rejected because |
|---|---|
| Keep `source_public_url` in **Set Configuration** | Fixed value; stale across multiple posts |
| Worker returns public URL from process-file | Out of scope; worker has no publish state |
| Separate HTTP worker endpoint for URL compute | Over-engineered for string/date parsing |

### 2. Use n8n Code node for derivation logic

**Decision:** Implement derivation in `n8n-nodes-base.code` (typeVersion 2), reading `$('Set Configuration').first().json` and `$input.first().json` (Process File output).

**Rationale:** Frontmatter date parsing and slug normalization are clearer in JavaScript than a single Set expression. Code node is a standard n8n control node—not Execute Command—and keeps logic testable via exported `jsCode` string inspection.

**Alternatives considered:**

| Alternative | Rejected because |
|---|---|
| Giant Set node expression | Hard to read, test, and maintain |
| Split into multiple Set nodes | More nodes without clearer failure semantics |

### 3. Configuration: `site_base_url` replaces `source_public_url`

**Decision:** **Set Configuration** assignments:

| Field | Default | Purpose |
|---|---|---|
| `site_base_url` | `https://silverman.pro` | Canonical site root (trailing slash stripped in code) |
| `topic_theme` | `""` | Optional editorial hint (unchanged) |

Remove `source_public_url` from **Set Configuration** entirely.

**Rationale:** Prevents operators from accidentally leaving a smoke-test URL that would apply to every post.

### 4. URL derivation algorithm (align with publishing helper)

**Decision:** For each Process File success item:

1. **Public slug:** Take basename of `relative_path`, remove `.md`, apply `^(\d+)-(.+)$` → use capture group 2 when matched; otherwise use basename without extension.
2. **Date:** Parse YAML frontmatter from start of `markdown_content` (between `---` delimiters). Read `date:` value; extract date portion `YYYY-MM-DD` from values like `2026-07-06 00:00:00 -0500`.
3. **Validate:** Public slug MUST match `^[a-z0-9]+(?:-[a-z0-9]+)*$`. Date MUST parse to valid calendar `YYYY`, `MM`, `DD`.
4. **Compose:** `{site_base_url.replace(/\/$/, '')}/{YYYY}/{MM}/{DD}/{public_slug}/`

**Canonical error reasons** (non-exhaustive; use one per failure):

| Reason | When |
|---|---|
| `missing_relative_path` | `relative_path` missing or empty |
| `missing_frontmatter_date` | No frontmatter block, no `date:` key, or unparseable date |
| `invalid_public_slug` | Slug after normalization fails safe-slug pattern |

**Output fields on item JSON** (merge with pass-through of process-file fields):

| Field | When set |
|---|---|
| `source_public_url` | Non-empty string when derivation succeeds; empty string or `null` when it fails |
| `source_public_url_error` | **Required** non-empty reason string when derivation fails; absent or empty when derivation succeeds |

Do not carry forward `source_public_url` from **Set Configuration** or from any prior item in the loop.

**Rationale:** Matches publishing helper slug rules and Jekyll permalink layout without requiring publish execution.

### 5. Generate LinkedIn Draft body mapping

**Decision:** Update **Generate LinkedIn Draft** `jsonBody` IIFE to:

- Keep mapping `source_relative_path`, `markdown_content`, and `source_content_sha256` from **Process File** (unchanged; passed through by **Compute Source Public URL** on the current item).
- Read `source_public_url` from the current item produced by **Compute Source Public URL**—because **Compute Source Public URL** is wired directly before **Generate LinkedIn Draft** and passes through process-file fields plus `source_public_url` / `source_public_url_error`.
- Never read `source_public_url` from `$('Set Configuration')`, `config.source_public_url`, or a prior loop item.
- Trim and include `source_public_url` only when non-empty.
- Read `topic_theme` from **Set Configuration** (unchanged conditional pattern).

**Example shape:**

```javascript
const item = $json;
const url = (item.source_public_url || '').trim();
if (url) body.source_public_url = url;
```

**Rationale:** Eliminates stale config fallback and cross-node item lookup; each generate call uses the current item's derived value or omits the field.

### 6. Derivation failure behavior

**Decision:** When slug or date validation fails, **Compute Source Public URL** outputs process-file fields plus empty `source_public_url` and a descriptive `source_public_url_error` (e.g. `missing_frontmatter_date`, `invalid_public_slug`, `missing_relative_path`). **Generate LinkedIn Draft** proceeds without `source_public_url` in the body (worker allows omission).

Do **not** add a new failure branch solely for URL derivation failure—draft generation continues; the operator sees `source_public_url_error` on the item.

**Rationale:** Matches requirement to "omit intentionally" while exposing failure clearly; hard-stop would block draft generation for an optional CTA.

### 7. Workflow export invariants

**Decision:** Keep `"active": false` in exported JSON. Do not add forbidden node types. Do not change authenticated worker HTTP Request nodes except **Generate LinkedIn Draft** body mapping and new wiring through **Compute Source Public URL**.

## Risks / Trade-offs

- **[Frontmatter date missing or non-standard]** → Omit URL; set `source_public_url_error`; document required `date:` in editorial frontmatter.
- **[Slug mismatch vs actual publish]** → URL is *expected* per convention, not publish-confirmed; README must state this until publish orchestration exists.
- **[Timezone in date string]** → Use date portion only (`YYYY-MM-DD`); matches Jekyll post path date.
- **[Multi-item runs]** → Each iteration recomputes from current item; generate body must not read cached config URL.
- **[Re-import required]** → Document in README migration note for operators.

## Migration Plan

1. Merge updated workflow JSON, tests, and README.
2. Operator re-imports workflow in n8n (export remains `"active": false`).
3. Remove any manually set `source_public_url` from old **Set Configuration** (field removed).
4. Optional smoke: manual execute with a ready post containing frontmatter `date`; confirm derived URL in generate request and draft CTA.

**Rollback:** Re-import previous workflow JSON from git history; no worker or data migration.

## Open Questions

- None blocking implementation.
