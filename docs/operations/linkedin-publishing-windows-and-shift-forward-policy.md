# LinkedIn publishing windows and shift-forward policy (US-052)

**Scope:** BL-021 / US-052 — operator-facing preferred LinkedIn publishing windows (local-day / clock guidance), strategy-level audience balancing (variant packaging remains Flow A), shift-forward reschedule rules when a candidate slot is cadence-infeasible, residual US-087 warning obligation, and fail-closed “no feasible slot” bounds for US-088 / US-089.
**Status:** Policy defined (documentation). Console cadence-conflict warning (**US-087**), schedule-time shift-forward (**US-088**), and executable **replan** (**US-089** via `POST /replan-linkedin-cadence-conflicts`) are **implemented, deployed, and Story accepted**; **US-052 / BL-021 closed** — see [CURRENT-STATE.md](../CURRENT-STATE.md). This document does **not** redefine window/horizon numbers.
**Authority:** Complements [linkedin-cadence-spacing-policy.md](linkedin-cadence-spacing-policy.md) (US-051 cadence conflict / spacing), [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md#publish-time-sequence-and-cadence-guard-us-020) (US-020 publish-time guard — authoritative at send), editorial [`#linkedin-distribution-strategy`](../../content-strategy/silverman-editorial-system.md#linkedin-distribution-strategy), [GLOSSARY.md](../GLOSSARY.md), [CURRENT-STATE.md](../CURRENT-STATE.md), and [user-stories.md](../product/user-stories.md) US-052.
**OpenSpec:** `openspec/changes/define-linkedin-publishing-windows-and-shift-forward-policy-us-052` (capability `linkedin-publishing-windows-and-shift-forward-policy`). Executable schedule-time enforcement: OpenSpec change `schedule-linkedin-variants-with-cadence-aware-shift-forward-us-088` (US-088). Executable replan: OpenSpec change `replan-already-scheduled-linkedin-cadence-conflicts-us-089` (US-089).

This document is the shared written meaning of preferred LinkedIn publishing windows and shift-forward placement for calendar and scheduler implementers. **US-088** implements schedule-time enforcement of these rules for new placements (preferred windows and the **28** operator-local-day horizon numbers below are **not** redefined by US-088 or US-089). **US-089** owns executable replan of already-Scheduled / not-yet-Live cadence conflicts and MUST reuse the same feasibility module. It does **not** change worker publish-time cadence evaluation, env defaults, n8n, LinkedIn publish-due cron, OAuth, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

---

## 1. Preferred publishing windows (strategy level)

| Parameter | Normative guidance |
|-----------|-------------------|
| **Preferred local days** | **Tuesday, Wednesday, Thursday** |
| **Preferred local clock windows** | **08:00–10:00** or **16:00–18:00** |
| **Operator timezone** | **America/Bogota** |

**Source:** Adopted from editorial canon [`#linkedin-distribution-strategy`](../../content-strategy/silverman-editorial-system.md#linkedin-distribution-strategy) without inventing a new clock-math engine.

**Placement guidance only:** These windows guide where to place or shift `scheduled_at_utc` candidates. They are **not** a second publish-time cadence engine.

**Publish-time authority unchanged:** Same-campaign minimum **72 hours** between successful `published` evidence (US-020 / US-051) remains **authoritative at send**. Schedule-intent stagger (≥3 calendar days in editorial canon) remains planning guidance. This policy MUST NOT change or disagree with the 72h constant.

---

## 2. Audience balancing (strategy level; packaging stays Flow A)

Audience-segment balancing for LinkedIn variants is **strategy-level**:

- Use existing editorial audience sequencing / lenses in [`#audience-map`](../../content-strategy/silverman-editorial-system.md#audience-map) and [`#linkedin-distribution-strategy`](../../content-strategy/silverman-editorial-system.md#linkedin-distribution-strategy) (e.g. first-publish order: `executive-recruiter` → `technical-architect` → `short-provocative` / `engineering-leadership` as documented there).
- Variant **packaging** ownership remains **Flow A** (`generate-linkedin-package` / derivative package generation).

**MUST NOT:** Move packaging ownership to Flow B, invent a P4 / Flow B–owned audience balancer, or treat this policy as a packaging redesign.

---

## 3. Cadence-infeasible candidates and shift-forward

**Cadence-infeasible** means the candidate `scheduled_at_utc` (or proposed slot) is a **cadence conflict** under US-051 — the same gate as live `linkedin_publish_blocked_cadence` / related auto-queue cadence skip at that slot. Cadence conflict meaning: [linkedin-cadence-spacing-policy.md](linkedin-cadence-spacing-policy.md) §4. This policy does **not** redefine it.

### Feasible slot

A candidate slot is **feasible** only when **all** hold:

1. **Not cadence-conflicted** under the US-051 / US-020 meaning at that `scheduled_at_utc` (or proposed slot).
2. **Density capacity** remains under interim **US-040K** max **2** publications per operator-local day.
3. **Existing distribution strategy constraints** for the path in use remain satisfied (e.g. `flow_a_staggered` stagger / empty-day rules; Flow B `flow_b_spill_a` spill order as applicable).

Prefer placing inside preferred days/windows when scanning forward. US-088 MAY document an ordered preference (preferred window on preferred day → other clock on preferred day → next preferred day, etc.) as long as it does not contradict this policy.

### Shift-forward rules

When the preferred or candidate slot is **cadence-infeasible**:

| Rule | Normative meaning |
|------|-------------------|
| **Direction** | Move **forward in time** to the next **feasible** slot. |
| **Density** | Next slot MUST also respect US-040K max 2 / local day. |
| **Strategy** | Next slot MUST respect existing distribution strategy constraints for the path in use. |
| **Silent keep forbidden** | MUST **NOT** silently keep an infeasible `scheduled_at_utc` as if it will send. |
| **No second engine** | MUST **NOT** invent a second cadence engine, disagreeing 72h constant, or weaken/reimplement the US-020 publish-time guard as a competing authority. Reuse US-051 / US-020 conflict semantics for feasibility checks at schedule time (**US-088**) and replan (**US-089**). |

Density-full alone is **not** cadence conflict (US-051). Shift-forward still MUST respect density when choosing the next slot.

---

## 4. Fail-closed bounds (no feasible slot) — for US-088 / US-089

Forward search MUST be **finite**. Infinite scan is forbidden. Silent infeasible placement is forbidden.

| Bound | Default |
|-------|---------|
| **Horizon** | **28 operator-local days** measured from the original candidate’s operator-local calendar day. |
| **Day counting** | Treat the original candidate’s local day as **day 0**. Search may consider slots on day 0 (after the candidate clock, within preferred windows / strategy rules) and on subsequent local days **1…28** inclusive. Do not search past local day **28** relative to day 0. |
| **No slot within horizon** | Scheduling / replan MUST **fail closed** with a structured, operator-visible error. Exact error code/shape is owned by **US-088** / **US-089** (`linkedin_schedule_no_feasible_slot`). |

**US-088 / US-089 enforcement:** Forward search is implemented in `linkedin_schedule_feasibility` (schedule-time placement and US-089 replan). This policy document does **not** change the numeric horizon or preferred-window definitions; US-088 and US-089 consume them.

---

## 5. Residual cadence conflict and US-087

If after placement a Scheduled item remains **cadence-conflicted** (edge cases: race with newly published evidence, partial placement, operator override outside automation, etc.), the console MUST still show the **US-087** cadence-conflict warning.

This policy binds that obligation for US-087 / US-088 consumers. It does **not** implement the console warning UI.

---

## 6. Blocked-state vocabulary

Use plain language that distinguishes these classes (they are **not** interchangeable). Cadence / sequence / density / enablement / OAuth classes match US-051; this section adds schedule-placement outcomes.

| Class | Operator meaning |
|-------|------------------|
| **Cadence conflict / cadence block** | Would hit US-020 cadence refuse/skip at the slot (`linkedin_publish_blocked_cadence` / related cadence skip). See [US-051 policy §4–5](linkedin-cadence-spacing-policy.md). |
| **Density-full / local-day saturation** | Local day already at US-040K max 2 — **not** cadence conflict. |
| **No feasible slot** | Forward search within the documented 28 local-day horizon found no feasible slot — fail closed (US-088 schedule-time / US-089 replan). Distinct from a single-slot cadence conflict warning. |
| **Sequence / enablement / OAuth** | Distinct non-cadence classes — by reference to [US-051 blocked-state vocabulary](linkedin-cadence-spacing-policy.md#5-blocked-state-vocabulary). |

Operators MUST NOT treat a Scheduled (or proposed) time that is cadence-infeasible as a guaranteed send. Publish-time US-020 remains authoritative at send.

---

## 7. Non-goals (this policy document)

- Console cadence-conflict warning UI (**US-087** — implemented separately).
- Worker publish-time cadence math, env defaults, n8n, LinkedIn publish-due cron, OAuth, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` changes.
- A second cadence engine or disagreeing 72h constant.
- Weakening, duplicating, or reimplementing the US-020 / BL-007 publish-time cadence guard.
- Moving audience packaging ownership out of Flow A.
- Superseding US-040K density or BL-019 gap.
- Marking US-052 / BL-021 Story accepted or closing BL-021 by documentation alone.
- Redefining preferred-window or horizon **numbers** via US-088 or US-089.

**Note:** Executable schedule-time shift-forward for **new** placements is owned by **US-088**. Executable **replan** of already-Scheduled conflicts is owned by **US-089** (not this policy-only change).

---

## 8. US-089 ops path (authenticated HTTP; ADR-0001)

Replan already-Scheduled cadence conflicts via worker HTTP only — **no n8n Execute Command**.

Dry-run preview (default; zero metadata mutation):

```bash
curl -sS -X POST "$WORKER_BASE/replan-linkedin-cadence-conflicts" \
  -H "Authorization: Bearer $SILVERMAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id":"YOUR_CAMPAIGN_ID"}'
```

Real apply (explicit confirmation — `dry_run` false):

```bash
curl -sS -X POST "$WORKER_BASE/replan-linkedin-cadence-conflicts" \
  -H "Authorization: Bearer $SILVERMAN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"campaign_id":"YOUR_CAMPAIGN_ID","dry_run":false}'
```

Optional filters: `targets:[{"campaign_id":"...","variant_id":"..."}]`. Response includes previous→proposed `scheduled_at_utc` per target; fail-closed code `linkedin_schedule_no_feasible_slot` when any selected target cannot place. Does not publish to LinkedIn API and does not force-enable publication.

---

## 9. Preserved behavior

- US-020 / BL-007 publish-time sequence and cadence guard remain **closed** and authoritative at send.
- US-051 cadence conflict meaning and spacing ratification remain authoritative for “cadence-infeasible.”
- US-040K density and BL-019 gap controls remain as documented elsewhere until a later change supersedes them.
- ADR-0001 (n8n → worker HTTP only) and ADR-0002 (blog canonical; LinkedIn variants are distribution assets) unchanged.
- Flow A packaging ownership unchanged.
