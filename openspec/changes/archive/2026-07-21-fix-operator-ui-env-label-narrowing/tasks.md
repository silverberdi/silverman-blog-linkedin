## 1. Type narrowing fix

- [x] 1.1 In `frontend/linkedin-variant-supervision-console/src/main.tsx`, after separated-mode config ok and embedded early-return, narrow `envLabel` to a proven `DeploymentEnvironment` before calling `validateApiEnvironmentPairing`
- [x] 1.2 Fail closed with operator-visible blocked UI (name `SILVERMAN_OPERATOR_UI_ENV_LABEL`, no secrets) if label is empty after config ok; do not call pairing

## 2. Local verification

- [x] 2.1 Run `npx tsc -b` and `npm run build` in `frontend/linkedin-variant-supervision-console` successfully
- [x] 2.2 Keep US-093 / US-094 / US-095 / `auth.session` Vitest suites green
- [x] 2.3 `git diff --check` clean; secrets audit clean; do not mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`

## 3. Commit and push

- [x] 3.1 Commit the fix on `feat/us-095-regress-separated-operator-ui`
- [ ] 3.2 Push the branch

## 4. Redeploy and live checks

- [ ] 4.1 Redeploy on `192.168.0.194` from `/home/silverman/silverman-blog-linkedin-src` with LAN prod pairing/CORS (`SILVERMAN_OPERATOR_UI_ORIGINS=http://192.168.0.194:8011`, env label/deployment_environment `prod`, API base `:8010`)
- [ ] 4.2 Verify `GET http://127.0.0.1:8010/health` includes `deployment_environment` and `BUILD_REVISION` matching the fix commit; UI listens on `:8011`; UI↔API pairing can proceed (no public-exposure claim beyond BL-026)

## 5. Docs and business honesty

- [ ] 5.1 Update CURRENT-STATE / RUNTIME-STATE only for what is actually live after redeploy
- [ ] 5.2 Do not mark US-093/US-094/US-095 Story accepted solely because build/deploy succeeded; update progress-checklist only for demonstrated deploy/build unblock facts if any
