# LinkedIn cadence spacing policy (US-051)

**Scope:** BL-021 / US-051 — operator-facing ratification of LinkedIn campaign spacing, frequency planning assumptions, density/gap coexistence, and the **cadence conflict** definition consumed by later BL-021 stories (US-087 → US-088 → US-089).
**Status:** Policy defined (documentation). Console warning (US-087), schedule-time shift-forward (US-088), and replan (US-089) are **not implemented** by this document. **US-051 / BL-021 Story accepted and backlog closure require operator review beyond this docs change.**
**Authority:** Complements [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md#publish-time-sequence-and-cadence-guard-us-020) (US-020 publish-time guard — authoritative at send), [GLOSSARY.md](../GLOSSARY.md), [CURRENT-STATE.md](../CURRENT-STATE.md), and [user-stories.md](../product/user-stories.md) US-051.
**OpenSpec:** `openspec/changes/ratify-linkedin-cadence-spacing-policy-us-051` (capability `linkedin-cadence-spacing-policy`).

This document is the shared written meaning of LinkedIn cadence spacing and frequency for calendar, scheduler, and console implementers. It does **not** change worker publish-time cadence evaluation, env defaults, n8n, LinkedIn publish-due cron, OAuth, or `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED`.

---

## 1. Normative campaign spacing (US-020 ratification)

| Rule | Normative meaning |
|------|-------------------|
| **Same-campaign minimum interval** | Successful LinkedIn publications within **one** campaign (`publish_state` `published` with valid stored `published_at` evidence) MUST be separated by a real minimum of **72 hours** (3 days). |
| **Measurement** | Anchored to stored `published_at` evidence — **not** schedule intent (`scheduled_at_utc` alone). |
| **Cross-campaign independence** | One campaign’s publications MUST NOT gate another campaign’s. |
| **Authoritative enforcement** | Worker publish-due / auto-queue path (US-020 / BL-007). Live block reason: `linkedin_publish_blocked_cadence` (and related auto-queue cadence skip). |
| **Operator contract** | Full guard mechanics (sequence + cadence + evidence fail-closed): [Publish-time sequence and cadence guard (US-020)](../deployment/linkedin-publication-prerequisites.md#publish-time-sequence-and-cadence-guard-us-020). |

**MUST NOT:** Introduce a second cadence engine, weaken the US-020 guard, invent a disagreeing interval constant, or document a different “authoritative” spacing that conflicts with the worker.

**Schedule-intent stagger vs publish-time cadence:** Editorial canon may describe planning stagger (≥3 calendar days between scheduled variants). That is **schedule planning guidance**. Publish-time cadence (this section / US-020) remains **authoritative at send**.

---

## 2. Frequency planning assumptions

### LinkedIn

Default planning assumption: fill toward approximately **two** LinkedIn publications per **operator-local** calendar day via the interim **US-040K** density cap (max 2 / local day).

- US-051 does **not** change or supersede that number.
- A later approved OpenSpec change MAY supersede the max-2 figure explicitly; until then, treat US-040K as the fill ceiling for planning and console/scheduler density checks.

### Blog (strategy level)

Blog frequency is **strategy-level**, not an automated daily blog cadence engine:

- Blogs are paced to support LinkedIn filling (Flow A packaging of ready blogs; Flow B weekly gap fills bounded by `max_drafts_per_weekly_run`, default **2**).
- US-051 does **not** require automating a blog cadence engine.

Preferred publishing windows / clock guidance remain deferred to **US-052** (not defined as executable policy here).

---

## 3. Interim coexistence: density and gap (not cadence)

| Control | Role | Relationship to cadence |
|---------|------|-------------------------|
| **US-020 cadence (72h)** | Same-campaign minimum real interval between successful `published` variants | Normative spacing; enforced at publish / auto-queue |
| **US-040K density** | Max **2** publications per operator-local day (plan / console / schedule placement) | **Interim coexisting** control — **density ≠ cadence 72h** |
| **BL-019 gap trigger** | Weekly sensor / fill of empty local days (Flow B upstream drafts) | **Interim coexisting** control — gap trigger does **not** bypass publish-time cadence |

US-051 **ratifies** density and gap as interim coexisting controls. It does **not** supersede US-040K or BL-019.

---

## 4. Cadence conflict (for US-087 / US-088 / US-089)

**Cadence conflict** means: at the variant’s `scheduled_at_utc` (or a proposed slot), a real publish-due / auto-queue path would **refuse or skip for cadence** — the same gate operators observe as `linkedin_publish_blocked_cadence` and related auto-queue cadence skip — evaluated against same-campaign successful `published` evidence timing.

| Is cadence conflict? | Condition |
|----------------------|-----------|
| **Yes** | Would hit US-020 cadence refuse/skip at that slot |
| **No** | Density-full alone (US-040K local-day saturation) |
| **No** | OAuth missing / reauthorization required |
| **No** | `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED` off |
| **No** | Sequence block alone (`linkedin_publish_blocked_sequence` / auto-queue sequence skip) |

**Sequence remains distinct** from cadence conflict unless a later approved story expands conflict UX to include sequence.

This policy does **not** require a new worker evaluator for US-051. Later stories (US-087+) MAY add read-only projection HTTP if needed, but MUST reuse the same rule semantics as US-020 — not invent a second 72h constant.

---

## 5. Blocked-state vocabulary

Use plain language that distinguishes these classes (they are **not** interchangeable):

| Class | Typical codes / cues | Operator meaning |
|-------|----------------------|------------------|
| **Cadence block** | `linkedin_publish_blocked_cadence`; related auto-queue cadence skip | Same-campaign 72h not yet elapsed vs last successful `published_at` |
| **Sequence block** | `linkedin_publish_blocked_sequence`; `linkedin_publish_auto_queue_skipped_sequence` | Earlier audience variant still awaiting publication — **distinct** from cadence |
| **Density-full** | e.g. `linkedin_supervision_local_day_density` / `calendar_schedule_local_day_density` | Local day already at US-040K max 2 — **not** cadence conflict |
| **Enablement off** | `linkedin_publish_not_enabled` (and related) | Real API publish fail-closed; not a cadence judgment |
| **OAuth / credentials** | `linkedin_oauth_reauthorization_required`, token `action_required`, etc. | Fix auth; not cadence |

Blocked outcomes leave `publish_state` non-`published` without falsely claiming LinkedIn API success. Full publish-time guard contract: [US-020 prerequisites section](../deployment/linkedin-publication-prerequisites.md#publish-time-sequence-and-cadence-guard-us-020).

---

## 6. Non-goals (this change)

- Console cadence-conflict warning UI (**US-087**).
- Schedule-time shift-forward mechanics (**US-088**) or replan of already-Scheduled conflicts (**US-089**).
- Full **US-052** publishing windows / rescheduling policy.
- Any worker cadence math, env default, n8n, cron, OAuth, or enablement change.
- A second cadence engine or disagreeing spacing constant.
- Marking US-051 / BL-021 Story accepted or closing BL-021 by documentation alone.

---

## 7. Preserved behavior

- US-020 / BL-007 publish-time sequence and cadence guard remain **closed** and authoritative at send.
- US-040K density and BL-019 gap controls remain as documented elsewhere until a later change supersedes them.
- ADR-0001 (n8n → worker HTTP only) and ADR-0002 (blog canonical) unchanged.
