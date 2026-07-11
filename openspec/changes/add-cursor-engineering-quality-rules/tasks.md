## 1. Engineering rule creation

- [x] 1.1 Create `.cursor/rules/silverman-blog-linkedin-engineering.mdc` with valid YAML frontmatter (`description`, `alwaysApply: true`)
- [x] 1.2 Add intro linking to `.cursor/rules/silverman-blog-linkedin-project.mdc` and canonical docs (no volatile CURRENT-STATE embedding)
- [x] 1.3 Write section 1: Canonical context and authority (classify rule as Cursor execution guidance, subordinate to canonical specs)
- [x] 1.4 Write section 2: Precise status language (qualified Flow A; handoff vs publication; implementation vs validation)
- [x] 1.5 Write section 3: Inspect before editing
- [x] 1.6 Write section 4: Scope and anti-overengineering
- [x] 1.7 Write section 5: Python standards
- [x] 1.8 Write section 6: API and worker standards
- [x] 1.9 Write section 7: Filesystem and lifecycle safety
- [x] 1.10 Write section 8: External integration rules (ComfyUI, DeepSeek, LinkedIn, GitHub Pages, n8n)
- [x] 1.11 Write section 9: Testing standards
- [x] 1.12 Write section 10: Warning and quality discipline
- [x] 1.13 Write section 11: Documentation and drift prevention
- [x] 1.14 Write section 12: Security and secrets
- [x] 1.15 Write section 13: Git discipline
- [x] 1.16 Write section 14: Deployment and live-operation discipline
- [x] 1.17 Write section 15: Cursor response behavior
- [x] 1.18 Write section 16: Definition of done
- [x] 1.19 Encode full `/opsx-*` lifecycle with explicit approval gates (hyphenated commands only)
- [x] 1.20 Confirm rule does not create `.cursorrules.md`
- [x] 1.21 Confirm line count: 180–240 target; never above 280 hard maximum

## 2. Project rule complement

- [x] 2.1 Add cross-link from `.cursor/rules/silverman-blog-linkedin-project.mdc` to the engineering rule
- [x] 2.2 Replace duplicated detailed "Engineering workflow" block with concise pointer to engineering rule (retain brief guardrails)
- [x] 2.3 Verify project rule still links to `docs/CURRENT-STATE.md`, `docs/CONTEXT-AUTHORITY.md`, `docs/GLOSSARY.md`
- [x] 2.4 Confirm project rule does not duplicate the complete OpenSpec lifecycle

## 3. CONTEXT-AUTHORITY update

- [x] 3.1 Add narrow entry to `docs/CONTEXT-AUTHORITY.md` for `.cursor/rules/silverman-blog-linkedin-engineering.mdc`
- [x] 3.2 State: automatically loaded Cursor execution guidance; subordinate to canonical specs and project context; not normative product authority; governs engineering behavior and approval discipline
- [x] 3.3 Do not embed engineering rule full contents

## 4. OpenSpec skill command-syntax alignment

- [x] 4.1 Inspect `.cursor/skills/openspec-propose/SKILL.md` — fix obsolete `/opsx:` references (expected: lines 19, 94 → `/opsx-apply`)
- [x] 4.2 Inspect `.cursor/skills/openspec-explore/SKILL.md` — fix obsolete `/opsx:` reference (expected: line 203 → `/opsx-explore`)
- [x] 4.3 Inspect `.cursor/skills/openspec-apply-change/SKILL.md` — fix obsolete `/opsx:` reference (expected: line 25 → `/opsx-apply`)
- [x] 4.4 Inspect `.cursor/skills/openspec-sync-specs/SKILL.md` — confirm no colon syntax; no change expected
- [x] 4.5 Inspect `.cursor/skills/openspec-archive-change/SKILL.md` — confirm no colon syntax; no change expected
- [x] 4.6 Preserve each skill's responsibility and procedure; narrow syntax fixes only

## 5. Duplication and conflict audit

- [x] 5.1 Compare engineering rule against project rule; confirm locked ownership split
- [x] 5.2 Confirm no line-by-line duplication of guardrails beyond necessary cross-references
- [x] 5.3 Confirm both rules use `alwaysApply: true`
- [x] 5.4 Confirm `openspec/config.yaml` was not modified

## 6. Validation and verification

- [x] 6.1 Run `openspec validate add-cursor-engineering-quality-rules --strict`
- [x] 6.2 Validate Cursor rule frontmatter for both `.mdc` files (YAML parse; `description` string; `alwaysApply: true`)
- [x] 6.3 Verify engineering rule line count: 180–240 target; ≤280 hard maximum
- [x] 6.4 Verify all local markdown links in new/modified files resolve
- [x] 6.5 Grep active rules, commands, skills, and current docs for `/opsx:` colon syntax (zero matches outside archived changes)
- [x] 6.6 Confirm lifecycle order consistent across commands, skills, rules, and CONTEXT-AUTHORITY
- [x] 6.7 Grep new/modified rules for unqualified "Flow A complete" / "Flow A is complete"
- [x] 6.8 Grep new rule for broad warning suppression patterns
- [x] 6.9 Manual review: no speculative abstractions or vague generic rules in engineering rule
- [x] 6.10 Secrets audit: inspect new/modified files for API keys, tokens, passwords, or `.env` values
- [x] 6.11 Run `git diff --check`
- [x] 6.12 Exact-scope audit: only file-action matrix paths modified (engineering rule create; project rule; CONTEXT-AUTHORITY; up to 3 skill files)
- [x] 6.13 Skip full `pytest` (docs/rules-only change)
- [x] 6.14 Run `/opsx-verify add-cursor-engineering-quality-rules` before commit approval

## 7. Post-implementation lifecycle (manual gates)

- [ ] 7.1 Obtain explicit approval for implementation commit
- [ ] 7.2 Commit implementation (engineering rule, project rule, CONTEXT-AUTHORITY, skill fixes)
- [ ] 7.3 Run `/opsx-sync add-cursor-engineering-quality-rules` and review delta merge to `openspec/specs/repository-context-governance/spec.md`
- [ ] 7.4 Separate commit for canonical spec sync
- [ ] 7.5 Run `/opsx-archive add-cursor-engineering-quality-rules` after sync commit
- [ ] 7.6 Separate commit for archive
- [ ] 7.7 Obtain explicit approval before push, deploy, or live operational validation
