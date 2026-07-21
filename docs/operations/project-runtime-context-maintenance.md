# Project and runtime context maintenance (US-071 / US-072 / US-073 / BL-030)

**Scope:** Keep **CURRENT-STATE**, **RUNTIME-STATE**, historical/bootstrap docs, and Cursor guidance aligned with reality.
**Status:** Procedure **published**. Depth-C audit evidence: [us-071-us-073-context-maintenance-audit-2026-07-21.md](us-071-us-073-context-maintenance-audit-2026-07-21.md).
**Authority:** [CONTEXT-AUTHORITY.md](../CONTEXT-AUTHORITY.md), [CURRENT-STATE.md](../CURRENT-STATE.md), [RUNTIME-STATE.md](../RUNTIME-STATE.md), [GLOSSARY.md](../GLOSSARY.md).
**OpenSpec:** capability `project-runtime-context-maintenance` (change `maintain-project-runtime-context-us-071-073`).

Does **not** establish CI (**BL-029** remains open), GitFlow, or mutate `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

---

## 1. US-071 — When to update CURRENT-STATE / RUNTIME-STATE

| Trigger | Update |
|---------|--------|
| Capability, topology, or completion-layer change | **CURRENT-STATE** in the same change (or immediate docs follow-up) |
| Deploy, activation, live smoke, flag change | **RUNTIME-STATE** (secret-safe facts only) |
| Spec↔implementation divergence | Record in CURRENT-STATE; resolve via new OpenSpec change |

**RUNTIME-STATE** is volatile and **not** architectural authority. Prefer a lean live snapshot; durable narrative belongs in CURRENT-STATE / ops evidence.

---

## 2. US-072 — Contradiction checklist

1. CURRENT-STATE internal: no “Story accepted” + “remains open” on the same item.
2. CURRENT-STATE vs RUNTIME-STATE: mounts, flags, console assets, verification dates.
3. `docs/context/` and superseded ops headers: Historical banner or “see CURRENT-STATE” — not sounding current if superseded.
4. `openspec/changes/archive/` — never cite as active requirements (use `openspec/specs/` or explicit archive paths).
5. Product progress vs CURRENT-STATE for open/closed BLs.

Vocabulary: `confirmed current` / `finding — remediate` / `blocked` (e.g. no LAN for live refresh).

---

## 3. US-073 — Cursor ↔ repo guidance

Always-on rules MUST:

- Link CONTEXT-AUTHORITY / CURRENT-STATE / GLOSSARY / RUNTIME-STATE
- Stay subordinate to specs and ADRs
- **Not** embed volatile inventories (ports, open BL lists, live SHAs)

Update rules when hierarchy or document roles change — not on every status bullet.

---

## 4. Related

- Audit evidence: [us-071-us-073-context-maintenance-audit-2026-07-21.md](us-071-us-073-context-maintenance-audit-2026-07-21.md)
- CI (deferred): BL-029 / US-069–070
