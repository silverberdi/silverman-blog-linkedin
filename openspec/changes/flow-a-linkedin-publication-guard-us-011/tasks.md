## 1. Docs and language (US-011 AC: outcome visible; no unintended reinterpretation)

- [x] 1.1 Clarify in deployment/README / CURRENT-STATE draft language that Flow A activation/schedule ≠ LinkedIn enablement and `distribution_scheduled` ≠ LinkedIn API published; US-011 is not permanent LinkedIn-off
- [x] 1.2 Document the controlled evidence procedure (record baseline → set false → prove fail-closed → restore baseline) with PASS/PENDING/FAIL + remediation; never print secrets
- [x] 1.3 Explicitly mark BL-005, BL-007 / auto_queue WIP, Flow B, and calendar execute-flow-a-due rewrite as out of scope

## 2. Light assertions (US-011 AC: disabled until approved; clear blocked states; no new endpoints)

- [x] 2.1 Confirm existing `tests/test_linkedin_publication.py` covers disabled flag → `linkedin_publish_not_enabled`; extend only if a gap remains
- [x] 2.2 Confirm Flow A n8n export assertions exclude LinkedIn API nodes/hosts (`tests/test_n8n_workflow.py` or equivalent); add thin assertion if missing
- [x] 2.3 Do not add new LinkedIn publication routes or OpenAPI surface
- [x] 2.4 Run targeted pytest for touched tests; `git diff --check`

## 3. Server evidence (US-011 AC: keep LinkedIn publication disabled until separately approved) — approval-gated

- [x] 3.1 On `192.168.0.194`, record baseline `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` from `.env` and worker container
- [x] 3.2 After explicit operator approval: set flag `false`, recreate worker, confirm container env `false`
- [x] 3.3 Prove fail-closed with existing real-mode publish gate → expect `linkedin_publish_not_enabled`; no variant marked `failed` solely for disablement; no LinkedIn API publish
- [x] 3.4 Confirm canonical Flow A workflow still has no LinkedIn API/nodes; prefer empty ready Manual/schedule no-op (no LinkedIn publication endpoints invoked)
- [x] 3.5 Restore recorded baseline flag, recreate worker, confirm match
- [x] 3.6 Write `docs/operations/us-011-linkedin-publication-guard-validation-YYYY-MM-DD.md` with pass/fail per step

## 4. Context and product progress (demonstrated outcomes only)

- [x] 4.1 Update `docs/CURRENT-STATE.md`: US-011 validated; BL-004 closable; BL-005 still open; qualified Flow A language
- [x] 4.2 Update `docs/RUNTIME-STATE.md`: record pre/during/post flag values; final value is restored baseline unless operator recorded a different lasting choice
- [x] 4.3 Update `docs/product/user-stories.md` US-011 ACs only when demonstrated
- [x] 4.4 Update `docs/product/progress-checklist.md`: complete US-011 and close BL-004; leave BL-005 open
- [x] 4.5 Update backlog wording if needed so BL-004 completion outcome matches validated state

## 5. Business validation

- [x] 5.1 Map evidence to every US-011 AC: disabled until separately approved; outcome visible; failures/blocked clear; no unintended change to US-009/US-010 work
- [x] 5.2 Confirm out of scope remains incomplete: BL-005, BL-007 WIP, Flow B, calendar rewrite, new LinkedIn endpoints, permanent LinkedIn-off misread
- [x] 5.3 Run `openspec validate flow-a-linkedin-publication-guard-us-011 --strict` after apply edits; prepare `/opsx-verify` before any commit request
