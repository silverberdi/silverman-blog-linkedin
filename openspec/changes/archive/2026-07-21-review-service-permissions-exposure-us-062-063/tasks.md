## 1. Normative SoT + live review

- [x] 1.1 Create `docs/operations/service-permissions-and-exposure.md` (US-062+US-063; accepted exposure table with OAuth exception option 1; ports/auth/paths; secrets ratify US-058; vocabulary; future console/Google out of scope)
- [x] 1.2 Run live review on `192.168.0.194` (listening ports, auth spot-check, mounts/paths) and write dated evidence under `docs/operations/` (no secrets)
- [x] 1.3 Thin cross-link from US-058 procedure to BL-026 SoT

## 2. Glossary and status

- [x] 2.1 GLOSSARY entry for service permissions and exposure (BL-026)
- [x] 2.2 CURRENT-STATE: SoT + live review; BL-026 closed when stories accepted
- [x] 2.3 Product backlog / user-stories pointers

## 3. Product progress

- [x] 3.1 Mark US-062 + US-063 Story accepted; close BL-026
- [x] 3.2 Check ACs in user-stories.md
- [x] 3.3 Confirm no public console exposure, no enablement mutation, no unrelated secret rotation forced

## 4. Verification

- [x] 4.1 Walk ACs; `git diff --check`; secrets audit
- [x] 4.2 Business validation: owner recognizes accepted exposure table (LAN + OAuth exception)
