## Why

P7 **BL-030 / US-071 + US-072 + US-073** still lack a single operator-facing maintenance contract for keeping CURRENT-STATE, RUNTIME-STATE, historical banners, and Cursor guidance aligned with reality. Depth-C audit is required because accumulated status drift (especially RUNTIME-STATE frozen at 2026-07-19 vs later accepted work) undermines trust in project context. BL-029 CI remains deferred/out of scope.

## What Changes

- Publish `docs/operations/project-runtime-context-maintenance.md` covering when/how to update CURRENT-STATE and RUNTIME-STATE, how to detect contradictions, how to banner historical docs, and how to keep `.cursor/rules` aligned with CONTEXT-AUTHORITY.
- Run a depth-C contradiction audit; remediate high/medium drifts (RUNTIME-STATE live refresh, CURRENT-STATE internal contradictions, context banners, key ops status headers).
- Refresh RUNTIME-STATE from live worker on `192.168.0.194` (secret-safe).
- Close US-071 + US-072 + US-073 and **BL-030**; leave **BL-029 open**.
- Introduce capability `project-runtime-context-maintenance`.

## Capabilities

### New Capabilities
- `project-runtime-context-maintenance`: Operator SoT + audit/evidence for maintaining current project and runtime context (US-071–US-073).

### Modified Capabilities
- *(none)*

## Impact

- Docs under `docs/` (CURRENT-STATE, RUNTIME-STATE, CONTEXT-AUTHORITY pointers, `docs/context/` banners, selected ops/product status headers).
- Cursor rules only if hierarchy/pointers drift (prefer thin cross-links; avoid volatile inventories in rules).
- No worker runtime behavior, CI, or LinkedIn enablement mutation.
