## 1. Normative SoT

- [x] 1.1 Create `docs/operations/linkedin-token-management.md` covering US-060 (store, renew/expire, revoke) + US-061 (detect invalid, separate dev/prod, recovery) with healthy/action_required/blocked vocabulary; refresh-token gap callout; no secret values; independence from enablement mutation
- [x] 1.2 Add thin cross-links from `docs/deployment/linkedin-publication-prerequisites.md` and `docs/operations/operational-secrets-ownership-cadence.md` (LinkedIn token row) to the SoT

## 2. Glossary and status

- [x] 2.1 Add `docs/GLOSSARY.md` entry for LinkedIn token management (BL-025 / US-060+US-061)
- [x] 2.2 Update `docs/CURRENT-STATE.md`: SoT published; refresh-token gap remains noted; BL-025 closed when stories accepted
- [x] 2.3 Product pointers in backlog / user-stories for BL-025

## 3. Product progress

- [x] 3.1 Mark US-060 + US-061 Work started → Story accepted; close BL-025 in progress-checklist and backlog
- [x] 3.2 Check US-060 and US-061 acceptance criteria in user-stories.md
- [x] 3.3 Confirm no enablement mutation, no forced reauth, no Flow A/B code changes, no unrelated secret rotation

## 4. Verification

- [x] 4.1 Walk US-060/US-061 ACs against docs; `git diff --check`; secrets audit
- [x] 4.2 Optional: note current `oauth/status` metadata from prior US-058 evidence (token_present, refresh_token_present false) without re-printing secrets
