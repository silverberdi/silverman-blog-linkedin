## 1. Canonical documents (creates 1–5)

- [x] 1.1 Create `docs/CONTEXT-AUTHORITY.md` per design D2: normative specs vs implementation evidence, conflict rules, historical handling, engineering lifecycle with approval gates, hyphenated slash-command reference, commit → sync → archive sequence
- [x] 1.2 Create `docs/GLOSSARY.md` with all required terms per design D3 (Flow A layers, handoff vs publication, LinkedIn implementation vs API validation, n8n import vs automation)
- [x] 1.3 Create `docs/CURRENT-STATE.md` with purpose, business goals, architecture summary, ownership matrix, runtime topology pointers, real validation evidence (post `04-a-bounded-context-is-not-a-folder.md`), separated roadmap sections, `last_verified_at_utc`, last verified baseline `88cd5bc` @ `2026-07-10T00:00:00Z` (not permanent runtime requirement), known divergences including `scripts/flow_a_readiness.py` stale `DEFAULT_EXPECTED_COMMITS` as follow-up
- [x] 1.4 Create `docs/RUNTIME-STATE.md` per design D9: `verified_at_utc`, evidence sources, `unknown` for unverified facts, initial snapshot (`BUILD_REVISION=88cd5bc`, topology, n8n inactive, `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=false`, ComfyUI enabled during validation—no secrets)
- [x] 1.5 Create `.cursor/commands/opsx-verify.md` per design D8: project-specific wrapper using `openspec validate <change-name> --strict`; artifact/task completion; change-required tests; traceability; staleness detection and rule; never recommend archive before commit + sync

## 2. Workflow split (creates 6–7, stub 8)

- [x] 2.1 Create `docs/workflows/flow-a-target-flow.md` — extract Flow A automation content from `phase-1-target-flow.md` (calendar connector, queue acceptance, publish/package/schedule/lifecycle, folder semantics)
- [x] 2.2 Create `docs/workflows/linkedin-draft-review-flow.md` — extract human review content (review → approved → published, manual publication boundary)
- [x] 2.3 Convert `docs/workflows/phase-1-target-flow.md` to historical compatibility stub explaining split; link rows 2.1 and 2.2 (do not simply rename)

## 3. Cursor and OpenSpec configuration (updates 9–10)

- [x] 3.1 Update `.cursor/rules/silverman-blog-linkedin-project.mdc`: concise guardrails, canonical doc links, engineering workflow, remove stale phasing; ban ambiguous "Flow A complete"; qualified completion layers
- [x] 3.2 Update `openspec/config.yaml`: post-Flow-A-core state, D2 authority semantics, explicit canonical paths only (CURRENT-STATE, CONTEXT-AUTHORITY, GLOSSARY, ADRs, canonical specs); no bulk `docs/context/` or workflow injection; RUNTIME-STATE consulted only when live state relevant; update proposal/design/tasks rules; context-drift checklist in tasks rules; specs rules block if schema supports

## 4. README (update 11)

- [x] 4.1 Update `README.md`: prominent links to canonical docs; accurate capability summary; blog handoff vs Git publication; LinkedIn implemented vs API-validated; n8n imported/inactive (not unattended); `BUILD_REVISION` (not `SILVERMAN_BUILD_REVISION`); do not treat `88cd5bc` as permanent expected commit

## 5. Bootstrap context (rows 12–18)

- [x] 5.1 `docs/context/project-overview.md` — historical banner; point to CURRENT-STATE
- [x] 5.2 `docs/context/backlog-and-phasing.md` — historical banner; link CURRENT-STATE roadmap
- [x] 5.3 `docs/context/worker-architecture.md` — update endpoints, boundaries, Flow A scope; link canonical docs
- [x] 5.4 `docs/context/deployment-context.md` — align paths; link deployment guide and RUNTIME-STATE
- [x] 5.5 `docs/context/n8n-integration-context.md` — distinguish implemented/imported/tested/active; state inactive
- [x] 5.6 `docs/context/openai-content-generation-context.md` — historical banner; DeepSeek not OpenAI; link spec
- [x] 5.7 `docs/context/editorial-operating-model.md` — update Flow A/B semantics; mark Phase 1 review-stop language historical

## 6. Related workflow and deployment docs (rows 19–24)

- [x] 6.1 Update `docs/workflows/blog-publishing-bridge.md` — handoff vs publication terminology
- [x] 6.2 Update `docs/workflows/editorial-calendar-orchestration.md` — Flow A terminology; cross-links
- [x] 6.3 Update `docs/workflows/editorial-calendar-flow-a-execution-connector.md` — queue/folder semantics; recovery classifications
- [x] 6.4 Update `docs/deployment/ubuntu-server-worker-deployment.md` — topology, BUILD_REVISION, manual Git steps
- [x] 6.5 Update `docs/deployment/linkedin-publication-prerequisites.md` — implemented vs API-validated publication
- [x] 6.6 Add historical banner to `docs/operations/n8n-server-worker-integration-2026-07-06.md`

## 7. Editorial canon and ADRs (rows 25–28)

- [x] 7.1 Update `content-strategy/silverman-editorial-system.md` metadata only: umbrella → `openspec/changes/archive/2026-07-07-flow-a-automatic-blog-linkedin-publishing-roadmap/`; runtime-loading claims; canonical references; Flow A vs Flow B approval semantics (preserve policy body)
- [x] 7.2 ADR-0001 — cross-link to canonical context (no decision change)
- [x] 7.3 ADR-0002 — cross-link to canonical context (no decision change)
- [x] 7.4 ADR-0003 — cross-link to canonical context (no decision change)

## 8. Inspect-only pass (rows 29–33)

- [x] 8.1 Inspect `docs/examples/editorial-calendar/calendar.example.json` — update only if stale Phase 1 claims found
- [x] 8.2 Inspect `scripts/flow_a_readiness.py` — do NOT change executable defaults/logic; document stale `DEFAULT_EXPECTED_COMMITS` in CURRENT-STATE as follow-up (D13)
- [x] 8.3 Inspect `deploy/server/*.sh` — update comments only if stale contextual claims
- [x] 8.4 Inspect `deploy/server/silverman-worker.env.example` and `silverman-worker.compose.yaml` — no change unless stale comment
- [x] 8.5 Grep repository for `phase-1-target-flow` references; update to split docs or stub as appropriate

## 9. Validation and audits

- [x] 9.1 Run `openspec validate align-project-context-and-current-state --strict` — must pass
- [x] 9.2 Verify all paths referenced in new/updated docs exist
- [x] 9.3 Parse `openspec/config.yaml` with YAML validator
- [x] 9.4 Grep: obsolete unmarked Phase 1 "current" claims in `docs/context/` bannered or removed
- [x] 9.5 Grep: no canonical `/opsx:` colon command syntax
- [x] 9.6 Grep: no unqualified "Flow A is complete" / "Flow A complete" outside glossary definitions
- [x] 9.7 Grep: no archived changes cited as active requirements
- [x] 9.8 Confirm no secrets in new documents
- [x] 9.9 Skip full `pytest` (docs-only change; no executable script modifications)

## File-action matrix reference

See `design.md` closed file-action matrix (rows 1–36) for path, action, reason, authority source, and validation required per file.

**Inventory:** 5 primary creates + 2 workflow-split creates = 7 creates; 1 compatibility stub; 13 substantive updates; 4 historical banners; 3 cross-link only; 5 inspect-only; 3 no change; 36 total.
