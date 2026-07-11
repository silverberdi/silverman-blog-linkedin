## ADDED Requirements

### Requirement: Canonical current-state document

The repository MUST maintain `docs/CURRENT-STATE.md` as the canonical source for project purpose, business goals, architecture summary, ownership matrix, implemented vs operationally validated vs manual vs incomplete vs deferred roadmap, `last_verified_at_utc`, known spec↔implementation divergences, and pointers to deployment topology. The document MUST distinguish Flow A core implementation from fully unattended Flow A production operation and MUST NOT use ambiguous "Flow A is complete" language without qualifying the completion layer. The document MAY record a last verified baseline revision (e.g., `88cd5bc` at `2026-07-10T00:00:00Z`) with timestamp and MUST NOT treat that SHA as a permanent runtime requirement.

#### Scenario: New session reads current status

- **WHEN** a contributor or Cursor agent opens `docs/CURRENT-STATE.md`
- **THEN** they find separated roadmap sections for operationally validated capabilities, implemented-but-not-validated items, manual steps, incomplete work, and deferred scope without contradicting canonical OpenSpec specs

#### Scenario: Known divergence recorded

- **WHEN** implementation behavior differs from a canonical spec requirement
- **THEN** `docs/CURRENT-STATE.md` records the divergence explicitly and directs resolution through a new OpenSpec change rather than silent interpretation

#### Scenario: Real operational evidence recorded

- **WHEN** `docs/CURRENT-STATE.md` documents Flow A validation
- **THEN** it cites verifiable evidence (e.g., campaign `flow_a_complete`, publication idempotency, calendar reconciliation) and states that public-blog Git commit/push and LinkedIn real API publication remain manual or unvalidated as applicable

### Requirement: Canonical authority document

The repository MUST maintain `docs/CONTEXT-AUTHORITY.md` defining document authority hierarchy, document roles, conflict-resolution rules, handling of historical and archived artifacts, and canonical references for Cursor and OpenSpec. Canonical OpenSpec specs MUST be treated as normative requirements. Implementation and tests MUST be treated as evidence of real behavior. Neither layer MUST silently override a discrepancy; discrepancies MUST be resolved through a new OpenSpec change with divergence recorded in `docs/CURRENT-STATE.md`. Bootstrap context and archived changes MUST rank below canonical specs and CURRENT-STATE.

#### Scenario: Conflict between bootstrap doc and spec

- **WHEN** a bootstrap context file disagrees with a canonical spec or current implementation
- **THEN** `docs/CONTEXT-AUTHORITY.md` instructs contributors to record the discrepancy in `docs/CURRENT-STATE.md` and resolve it through a new OpenSpec change rather than silent interpretation

#### Scenario: Archived change cited as requirement

- **WHEN** a proposal references an archived OpenSpec change as an active requirement or implementation instruction
- **THEN** `docs/CONTEXT-AUTHORITY.md` and OpenSpec injected context direct authors to canonical specs and `docs/CURRENT-STATE.md` instead

### Requirement: Canonical glossary

The repository MUST maintain `docs/GLOSSARY.md` defining at minimum: Flow A, Flow A Core, `distribution_scheduled`, `flow_a_complete`, operational smoke pass, fully unattended Flow A, Flow B, `ready`/`queued`/`processed`/`error`, blog handoff, blog files written, site published/live, LinkedIn publication states (`pending`, `queued`, `publishing`, `published`), active OpenSpec change, canonical spec, archived change, reconciliation, and idempotency.

#### Scenario: Campaign state vs product complete

- **WHEN** documentation uses `flow_a_complete`
- **THEN** `docs/GLOSSARY.md` defines it strictly as a campaign lifecycle metadata state and distinguishes it from fully unattended Flow A or site published/live

#### Scenario: Blog handoff vs publication

- **WHEN** documentation describes blog output
- **THEN** `docs/GLOSSARY.md` separates worker file writes (blog handoff) from Git commit/push and GitHub Pages deployment (site published/live)

#### Scenario: LinkedIn implementation vs API validation

- **WHEN** documentation describes LinkedIn capabilities
- **THEN** `docs/GLOSSARY.md` distinguishes implemented package/scheduling support from operationally validated real LinkedIn API publication

### Requirement: Cursor always-on context alignment

The always-applied Cursor rule at `.cursor/rules/silverman-blog-linkedin-project.mdc` MUST remain concise, link to `docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, and `docs/GLOSSARY.md`, encode the approved engineering workflow with explicit approval gates, and prevent ambiguous Flow A completion claims. It MUST NOT duplicate full README or CURRENT-STATE content.

#### Scenario: Agent loads project rule

- **WHEN** Cursor applies the silverman-blog-linkedin project rule
- **THEN** the agent is directed to canonical status and authority documents before implementing non-trivial changes

### Requirement: OpenSpec injected context alignment

`openspec/config.yaml` injected context MUST describe the post-Flow-A-core state, reference canonical context documents explicitly (`docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, `docs/GLOSSARY.md`, accepted ADRs, canonical specs), state authority semantics and implemented/manual/incomplete distinctions, encode the engineering lifecycle and hyphenated slash-command names, and MUST NOT assert obsolete Phase 1 exclusions for capabilities already implemented. It MUST NOT inject all of `docs/context/` or all workflow documents as current context. Bootstrap and historical documents MUST be clearly lower authority.

#### Scenario: New OpenSpec proposal starts

- **WHEN** `openspec instructions` supplies project context for a new change
- **THEN** the context reflects current capabilities and warns against assuming automated Git push, LinkedIn real API publication, or unattended n8n automation

### Requirement: Historical document marking

Bootstrap and superseded context files that retain historical rationale MUST carry a prominent historical/bootstrap banner at the top pointing to canonical documents. Files MUST NOT present stale Phase 0/1 delivery status as current without the banner.

#### Scenario: Reader opens backlog-and-phasing

- **WHEN** a contributor opens `docs/context/backlog-and-phasing.md`
- **THEN** a visible banner indicates the file is historical/bootstrap and links to `docs/CURRENT-STATE.md` for current roadmap

### Requirement: Context drift prevention

When an approved change modifies capability implementation status, runtime topology, activation state, completion criteria, ownership boundaries, OpenSpec workflow, deployment procedures, or external integration readiness, the same change (or an immediate follow-up documentation change) MUST update `docs/CURRENT-STATE.md` and, when present, `docs/RUNTIME-STATE.md`.

#### Scenario: Capability becomes operationally validated

- **WHEN** a change completes operational validation of a previously unvalidated capability
- **THEN** `docs/CURRENT-STATE.md` roadmap sections are updated to reflect the new validation status with a `last_verified_at_utc` timestamp

### Requirement: Engineering command syntax standardization

Repository documentation MUST use hyphenated Cursor slash commands matching `.cursor/commands/opsx-*.md` filenames (`/opsx-propose`, `/opsx-apply`, `/opsx-sync`, `/opsx-archive`, `/opsx-explore`, `/opsx-verify`). Documentation MUST NOT prescribe unsupported colon variants (e.g., `/opsx:propose`) as canonical.

#### Scenario: Workflow documentation lists commands

- **WHEN** engineering workflow is documented in CONTEXT-AUTHORITY or OpenSpec config
- **THEN** command names match installed `.cursor/commands/` wrappers

### Requirement: Verification command wrapper

The repository MUST provide `.cursor/commands/opsx-verify.md` as a project-specific Cursor command wrapper (not a native OpenSpec CLI command). The wrapper MUST invoke `openspec validate <change-name> --strict`, inspect artifact and task completion, run change-required tests, assess spec-to-implementation traceability, detect modifications after a prior verification, state that any code or artifact modification makes a previous verification stale, follow the repository commit → sync → archive sequence, and NEVER recommend archive before approved implementation and sync commits.

#### Scenario: Operator verifies change before commit

- **WHEN** an operator runs `/opsx-verify align-project-context-and-current-state`
- **THEN** the wrapper runs strict validation and reports artifact/task completion status before recommending commit

#### Scenario: Post-verification modification

- **WHEN** any artifact or code file is modified after a successful verification
- **THEN** the wrapper reports the prior verification as stale and requires re-verification

### Requirement: Runtime state manifest separation

`docs/RUNTIME-STATE.md` MUST be a volatile point-in-time operational snapshot, NOT architectural authority. It MUST include `verified_at_utc`, evidence source per fact, and `unknown` for unverified facts. It MUST NOT contain secrets. It MUST be updated after deploys, activation changes, real smoke tests, external-integration validation, or confirmed deployed-revision changes. It MUST NOT be injected indiscriminately into every OpenSpec proposal and MUST be consulted only when live operational state is relevant.

#### Scenario: Reader consults runtime flags

- **WHEN** a contributor needs current LinkedIn publication guard status
- **THEN** they consult `docs/RUNTIME-STATE.md` or live verification, not ADRs or archived operations records

### Requirement: Workflow document split

The repository MUST split mixed workflow responsibilities from `docs/workflows/phase-1-target-flow.md` into `docs/workflows/flow-a-target-flow.md` (Flow A automation) and `docs/workflows/linkedin-draft-review-flow.md` (human LinkedIn review). `docs/workflows/phase-1-target-flow.md` MUST become a historical compatibility stub explaining the split and linking both current documents.

#### Scenario: Reader follows old workflow link

- **WHEN** a contributor opens `docs/workflows/phase-1-target-flow.md`
- **THEN** they see a compatibility stub directing them to the split documents

### Requirement: Executable script scope boundary

Context governance changes MUST NOT modify executable defaults, logic, or expected-commit behavior in `scripts/flow_a_readiness.py`. Documentation, comments, and help text MAY be corrected. Stale hardcoded revision defaults MUST be documented as a separate follow-up change.

#### Scenario: Readiness script defaults reviewed

- **WHEN** this change is applied
- **THEN** `scripts/flow_a_readiness.py` executable behavior is unchanged and any stale `DEFAULT_EXPECTED_COMMITS` are recorded as known divergence in `docs/CURRENT-STATE.md`

### Requirement: Anti-pattern prevention in canonical context

Canonical context documents MUST prevent: archived changes treated as active instructions; unqualified "Flow A complete" language; worker checkout writes described as site published/live; implemented LinkedIn support described as operationally validated API publication; and n8n workflow existence described as unattended automation.

#### Scenario: New proposal author reads CURRENT-STATE

- **WHEN** a contributor assesses Flow A completion status
- **THEN** they find qualified completion layers distinguishing campaign lifecycle, core validation, unattended operation, blog handoff, and site publication
