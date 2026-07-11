# Context Authority

How to read, trust, and update documentation in this repository. For **current project status**, see [CURRENT-STATE.md](CURRENT-STATE.md). For **terminology**, see [GLOSSARY.md](GLOSSARY.md).

## Authority hierarchy

| Layer | Role | Authority |
|-------|------|-----------|
| Canonical OpenSpec specs (`openspec/specs/`) | Normative requirements | Define what the system **MUST** do |
| Current implementation and tests (`src/`, `tests/`) | Evidence of real behavior | Demonstrate what the system **actually does** |
| [CURRENT-STATE.md](CURRENT-STATE.md) | Operational completeness and status | Records validated / manual / incomplete state and **known unresolved divergences** |
| Accepted ADRs (`docs/decisions/ADR-000*.md`) | Durable architectural decisions | Bind design choices |
| Operator/deployment documentation | Procedures and topology | Guide operations |
| Editorial canon (`content-strategy/silverman-editorial-system.md`) | Editorial policy | Govern content rules |
| Bootstrap/historical context (`docs/context/`) | Rationale and history | Lower authority; bannered when superseded |
| Archived OpenSpec changes (`openspec/changes/archive/`) | Historical evidence only | **MUST NOT** drive new work |
| [RUNTIME-STATE.md](RUNTIME-STATE.md) | Volatile operational snapshot | Live flags only; not architectural authority |
| `.cursor/rules/silverman-blog-linkedin-project.mdc` | Always-on Cursor project context | Orients agents to purpose, guardrails, and canonical doc links |
| `.cursor/rules/silverman-blog-linkedin-engineering.mdc` | Always-on Cursor execution guidance | Subordinate to canonical specs and project context; not normative product authority; governs engineering behavior and approval discipline |

## Conflict resolution

- Canonical specs and implementation/tests are **peers in tension**, not a silent override hierarchy: specs are normative; implementation/tests are evidence.
- **Neither silently overrides a discrepancy.** Any spec↔implementation mismatch MUST be recorded in [CURRENT-STATE.md](CURRENT-STATE.md) and resolved through a new OpenSpec change.
- Bootstrap or historical documents that disagree with a canonical spec or current implementation MUST NOT be treated as current truth. Record the discrepancy in CURRENT-STATE and open a change.
- Archived OpenSpec changes MUST NOT be cited as active requirements or implementation instructions.

## Historical and archived artifacts

Files under `docs/context/` with a **Historical bootstrap** banner retain rationale but are superseded by canonical docs. Files under `openspec/changes/archive/` are evidence of past decisions only.

When updating capabilities, topology, activation state, or completion criteria, update [CURRENT-STATE.md](CURRENT-STATE.md) (and [RUNTIME-STATE.md](RUNTIME-STATE.md) when live flags change) in the same change or an immediate follow-up docs-only change.

## Engineering lifecycle

1. **Propose** — `/opsx-propose <change-name>` creates proposal, design, specs, and tasks. Scope one coherent capability.
2. **Review** — Human approval before implementation. Do not implement application code without an approved OpenSpec change.
3. **Apply** — `/opsx-apply <change-name>` implements tasks from the change.
4. **Verify** — `/opsx-verify <change-name>` runs strict validation, artifact/task checks, and change-required tests before commit.
5. **Commit** — Approved implementation committed to git.
6. **Sync** — `/opsx-sync <change-name>` merges delta specs into canonical `openspec/specs/`.
7. **Archive** — `/opsx-archive <change-name>` finalizes the change after commit and sync.

**Approval gates:** proposal approval before apply; verification before commit; commit and sync before archive.

**Staleness rule:** Any code or artifact modification after a successful `/opsx-verify` makes that verification stale. Re-run verify before commit, sync, or archive.

## Cursor slash commands

Use hyphenated commands matching `.cursor/commands/opsx-*.md`:

| Command | Purpose |
|---------|---------|
| `/opsx-propose` | Create a new change with artifacts |
| `/opsx-explore` | Think through ideas before committing to a change |
| `/opsx-apply` | Implement tasks from an approved change |
| `/opsx-verify` | Validate change completeness before commit |
| `/opsx-sync` | Sync delta specs to canonical specs |
| `/opsx-archive` | Archive a completed change |

Do not use colon variants (e.g. `/opsx:propose`) as canonical syntax.

## Canonical references for agents

Before non-trivial implementation:

1. [CURRENT-STATE.md](CURRENT-STATE.md) — what is implemented, validated, manual, or deferred
2. [GLOSSARY.md](GLOSSARY.md) — precise terms (especially Flow A completion layers)
3. Relevant canonical specs in `openspec/specs/`
4. Accepted ADRs in `docs/decisions/`
5. [RUNTIME-STATE.md](RUNTIME-STATE.md) — only when live operational flags matter

Do not treat bulk `docs/context/` or all workflow documents as current authority. Consult explicit paths above.
