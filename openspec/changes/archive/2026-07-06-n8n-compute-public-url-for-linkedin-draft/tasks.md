## 1. Set Configuration updates

- [x] 1.1 Remove `source_public_url` assignment from **Set Configuration**
- [x] 1.2 Add `site_base_url` assignment with default `https://silverman.pro`
- [x] 1.3 Keep optional `topic_theme` assignment (default empty string)
- [x] 1.4 Update **Set Configuration** notes: `site_base_url`, per-item URL derivation, no manual article URL

## 2. Compute Source Public URL node

- [x] 2.1 Add **Compute Source Public URL** Code node (`n8n-nodes-base.code`) on **IF Process File OK** success branch after **Process File**
- [x] 2.2 Derive public slug from basename of `relative_path`: remove `.md`; strip leading `^(\d+)-` prefix when present (e.g. `01-`, `003-`)
- [x] 2.3 Parse frontmatter `date` from `markdown_content`; extract `YYYY`, `MM`, `DD` from date portion
- [x] 2.4 Compose URL `{site_base_url}/{YYYY}/{MM}/{DD}/{public-slug}/`; validate slug pattern `^[a-z0-9]+(?:-[a-z0-9]+)*$`
- [x] 2.5 On success: set non-empty `source_public_url`; omit or clear `source_public_url_error`. On failure: set empty `source_public_url` and non-empty `source_public_url_error` (`missing_relative_path`, `missing_frontmatter_date`, or `invalid_public_slug`); pass through process-file fields; do not branch away from generate
- [x] 2.6 Wire: **IF Process File OK** (true) → **Compute Source Public URL** → **Generate LinkedIn Draft** (replace any direct Process File → Generate link on success branch)

## 3. Generate LinkedIn Draft mapping

- [x] 3.1 Update **Generate LinkedIn Draft** `jsonBody` to read `source_public_url` from the current item produced by **Compute Source Public URL** (e.g. `const item = $json; const url = (item.source_public_url || '').trim();`)—not from **Set Configuration**, `config.source_public_url`, or prior items
- [x] 3.2 Include `source_public_url` in body only when trimmed value is non-empty
- [x] 3.3 Keep conditional `topic_theme` from **Set Configuration** (unchanged)
- [x] 3.4 Confirm **Set Generate Success** still exposes echoed `source_public_url` / `topic_theme` from worker response

## 4. Workflow export invariants

- [x] 4.1 Keep top-level `"active": false` in workflow JSON
- [x] 4.2 Confirm no forbidden node types added (Execute Command, SSH, filesystem, GitHub, LinkedIn, OpenAI, DeepSeek, local LLM)
- [x] 4.3 Preserve existing health, process-ready, process-file, and generate success/failure branches unchanged except success-path wiring above
- [x] 4.4 Confirm Manual Trigger remains the only entry point (no cron or webhook trigger added)

## 5. README documentation

- [x] 5.1 Replace manual `source_public_url` config row with `site_base_url` and derivation rules
- [x] 5.2 Document canonical example (`01-…` slug strip, frontmatter date, URL format)
- [x] 5.3 State expected URL vs publish-confirmed URL; no GitHub Pages or LinkedIn publish in this workflow
- [x] 5.4 Update node flow summary to include **Compute Source Public URL** after **IF Process File OK**
- [x] 5.5 Note re-import after merge; export remains inactive

## 6. Lightweight workflow tests

- [x] 6.1 Assert **Set Configuration** has no `source_public_url` assignment
- [x] 6.2 Assert **Set Configuration** includes `site_base_url` default `https://silverman.pro`
- [x] 6.3 Assert **Compute Source Public URL** in expected node names and node type `n8n-nodes-base.code`
- [x] 6.4 Assert **Generate LinkedIn Draft** reads `source_public_url` from the current item (`$json` / `item.source_public_url`); reject **Set Configuration**, `config.source_public_url`, and stale cross-item references
- [x] 6.5 Assert Code node `jsCode` contains slug strip, date parse, URL compose, and `source_public_url_error` on failure
- [x] 6.6 Assert `topic_theme` optional in **Set Configuration** and conditionally mapped in generate body
- [x] 6.7 Assert workflow `"active": false` and forbidden-node checks still pass
- [x] 6.8 Run focused tests (`pytest tests/test_n8n_workflow.py -v`), then full test suite

## 7. Validation and smoke

- [x] 7.1 Run `openspec validate n8n-compute-public-url-for-linkedin-draft --strict`
- [x] 7.2 Manual smoke (operator, post-merge): re-import workflow, manual execute against ready post with frontmatter `date`; confirm derived URL in generate request and draft CTA—do not set `"active": true` in repo export
