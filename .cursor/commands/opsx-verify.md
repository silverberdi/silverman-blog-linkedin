---
name: /opsx-verify
id: opsx-verify
category: Workflow
description: Verify an OpenSpec change before commit (project-specific wrapper)
---

Verify an OpenSpec change before commit. **Not** a native OpenSpec CLI command — this wrapper orchestrates validation steps.

**Input**: Optionally specify a change name (e.g. `/opsx-verify align-project-context-and-current-state`). If omitted, infer from conversation context or auto-select if only one active change exists.

**Steps**

1. **Select the change** — Announce: "Verifying change: <name>"

2. **Strict validation**
   ```bash
   openspec validate <change-name> --strict
   ```
   Must pass before proceeding.

3. **Artifact completion**
   ```bash
   openspec status --change "<name>" --json
   ```
   Confirm all `applyRequires` artifacts have `status: "done"`.

4. **Task completion** — Parse `tasks.md` in the change directory. Report incomplete checkboxes (`- [ ]`).

5. **Change-required tests** — Run tests scoped to the change per `tasks.md`. For docs-only changes, skip full `pytest` unless tasks require otherwise.

6. **Spec-to-implementation traceability** — For behavioral changes, confirm delta spec requirements have corresponding implementation/test evidence. Flag gaps.

7. **Staleness detection** — Compare working tree to last verification marker if present. Report modifications since prior verification.

8. **Staleness rule** — State explicitly: **any code or artifact modification after a prior verification makes that verification stale.** Re-run `/opsx-verify` before commit, sync, or archive.

9. **Lifecycle guidance** — Repository sequence: **commit (approved implementation) → `/opsx-sync` → `/opsx-archive`**

10. **Archive gate** — NEVER recommend `/opsx-archive` before approved implementation is committed and delta specs are synced.

**Output on success**

```
## Verification passed

**Change:** <name>
**Strict validation:** pass
**Artifacts:** complete
**Tasks:** N/N complete
**Tests:** <summary>

Ready to commit. After commit: `/opsx-sync <name>`, then `/opsx-archive <name>`.
```

**Output on failure**

```
## Verification failed

**Change:** <name>
**Failed step:** <step>
**Details:** <output>

Fix issues and re-run `/opsx-verify <name>`.
```

**Guardrails**

- Do not recommend archive before commit + sync
- Report stale verification if working tree changed after last verify
- Use hyphenated command names in guidance (`/opsx-sync`, not `/opsx:sync`)
