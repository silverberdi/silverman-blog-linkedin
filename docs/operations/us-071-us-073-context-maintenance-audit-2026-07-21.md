# US-071 / US-072 / US-073 project & runtime context maintenance — depth-C audit 2026-07-21

**BANNER — no secrets in this file.** Env var **names**, path classes, asset filenames, and health booleans only.

**Normative procedure:** [project-runtime-context-maintenance.md](project-runtime-context-maintenance.md).

| Field | Value |
|-------|-------|
| Audit date (UTC) | `2026-07-21` |
| Live probe `verified_at_utc` | `2026-07-21T19:32:13Z` |
| Scope | BL-030 / US-071 + US-072 + US-073 (depth **C**) |
| Overall outcome | **remediated** — high/medium drifts fixed; live RUNTIME-STATE refreshed |
| Story accepted | operator-accepted 2026-07-21; **BL-030 closed** |
| Out of scope | **BL-029** CI / GitFlow (remains open); LinkedIn enablement mutation; worker redeploy |

---

## US-071 — CURRENT-STATE / RUNTIME-STATE

| ID | Check | Outcome | Notes |
|----|-------|---------|-------|
| R1 | Live `/health` on `192.168.0.194:8010` | `confirmed current` | `status=healthy`, `folders_ready=true`, calendar `postgres:silverman_linkedin_db` ready |
| R2 | Editorial mount path | `confirmed current` | Container `/data/silverman-blog-linkedin`; host durable worker data path (not compartido) |
| R3 | Console static assets in image | `confirmed current` | `index-Dd92hzfG.js` / `index-BRVrIP7S.css` |
| R4 | `BUILD_REVISION` / `.build_git_sha` | `finding — remediate` (documented) | Not on `/health`; host stamp missing → RUNTIME-STATE records **unknown** until next deploy |
| R5 | RUNTIME-STATE lean refresh | `confirmed current` | Rewritten snapshot; long closed-BL narrative stays in CURRENT-STATE |
| R6 | CURRENT-STATE section hygiene | `confirmed current` | Renamed detail section; slim Incomplete/open; BL-030 closure; BL-029 remains open |

---

## US-072 — Contradictions & historical demotion

| ID | Finding | Severity | Remediation |
|----|---------|----------|-------------|
| C1 | CURRENT-STATE Incomplete still listed closed hygiene / Flow work | high | Slim Incomplete; closed items pointed to upper sections |
| C2 | “Implemented but not operationally validated” title mismatched Story accepted contents | medium | Retitled to **Implemented / deployed / Story accepted (detail)** + note |
| C3 | `docs/context/*` missing Historical banners / sounding current | medium | Bootstrap banners + CURRENT-STATE / RUNTIME-STATE pointers |
| C4 | Ops headers claiming “not accepted / remains open” after Story accepted (e.g. US-024/025 SoT headers) | medium | Status headers aligned with CURRENT-STATE |
| C5 | Product progress vs CURRENT-STATE for BL-030 | medium | Closed in backlog / user-stories / checklist with this evidence |
| C6 | Archive cited as active requirements | — | Procedure forbids; no active archive citations introduced |

Vocabulary used: `confirmed current` / `finding — remediate` / `blocked`.

---

## US-073 — Cursor ↔ repo guidance

| ID | Check | Outcome |
|----|-------|---------|
| G1 | `.cursor/rules` link CONTEXT-AUTHORITY / CURRENT-STATE / GLOSSARY / RUNTIME-STATE | `confirmed current` |
| G2 | Rules subordinate to specs/ADRs; no volatile inventories embedded | `confirmed current` (no thin edit required) |

---

## Operator attestation

| Statement | Yes / No |
|-----------|----------|
| No secret values in this evidence file | Yes |
| Live RUNTIME-STATE probe attempted (not invented) | Yes |
| BL-029 left open / deferred | Yes |
| No `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` mutation | Yes |
| Depth-C remediations applied for high/medium drifts | Yes |

---

## Product note

US-071 + US-072 + US-073 Story accepted; **BL-030 closed 2026-07-21**. **BL-029 remains open.**
