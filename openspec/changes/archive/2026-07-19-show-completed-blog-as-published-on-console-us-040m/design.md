## Context

Live calendar (Postgres `silverman_linkedin_db`) already has six Flow A blog items with `status: completed`, `blog_publish_status: completed`, and live `public_url` values on silverman.pro. `GET /flow-a/schedule-visibility` currently maps blog `completed` → display `publication_state: planned` and appends a long title qualifier so operators do not confuse blog handoff with LinkedIn API publish. That mapping now undercuts calendar truthfulness: completed blogs look unfinished.

BL-015 aesthetic closure (before Flow B) needs this display fix as **US-040M**. US-040L (filters modal) remains a separate follow-up.

## Goals / Non-Goals

**Goals:**

- Surfacing completed blog calendar items as a distinct, operator-clear “published on blog” display state.
- Keeping `linkedin_api_published: false` for blog channel always.
- Smallest worker + console + test delta; no DB backfill required for current completed items.

**Non-Goals:**

- Flow B; US-040L; mutating calendar `status`; LinkedIn display remapping; Google/OIDC; closing BL-015 Story accepted gates for G–K.

## Decisions

### D1 — New display state `completed` for blogs (not reuse LinkedIn `published`)

- **Choice:** Add schedule-visibility / console display value `completed` for editorial-calendar blog items whose calendar `status` is `completed`.
- **Rationale:** LinkedIn `published` already means API evidence (`linkedin_api_published: true` + label “Published (API evidence)”). Reusing `published` for blogs would blur glossary boundaries unless every label becomes channel-aware. A dedicated `completed` value keeps wire semantics honest.
- **Alternatives considered:**
  - Reuse `published` + channel-aware labels — rejected as higher confusion risk in filters/metrics (“Published” mixing site vs API).
  - Keep `planned` + shorter title only — rejected; still fails operator mental model.

### D2 — Operator label

- Console label for `completed`: **“Published on blog”**.
- EventModal/Week/Month MAY show short helper text that this is not LinkedIn API published (existing qualified language), without the long title suffix.

### D3 — Title suffix removal

- Remove `(blog handoff completed — not LinkedIn API published)` from schedule-visibility blog titles once `publication_state: completed` + label carry meaning.
- Keep original calendar `title` unchanged in the payload.

### D4 — Filters and density

- Add `completed` to `PUBLICATION_STATES` / filter checkboxes and status color map (calm distinct color, not LinkedIn published green if that implies API).
- Density membership (US-040K) MUST continue to include blog items that participate in schedule-visibility for the local day regardless of whether display is `planned` or `completed` (completed blogs already count today via channel/source inclusion rules — do not drop them from density).

### D5 — Read-only / editability unchanged

- Blog schedule editability remains gated by calendar `source_state` / status (`completed` stays non-editable). No change to mutation endpoints.

### D6 — Product story

- Add **US-040M** under BL-015; Shared UX DoD extends to include US-040M for Story accepted walkthrough expectations when this story is accepted (same Visual DoD gate pattern as G–L).

## Risks / Trade-offs

- **[Risk] Filters “Published (API evidence)” vs “Published on blog” confuse operators** → Mitigation: distinct state `completed` + distinct label; keep LinkedIn `published` unchanged.
- **[Risk] Metric chips / Upcoming counts include completed blogs as “upcoming”** → Mitigation: review count helpers; completed blogs SHOULD NOT inflate Upcoming/Pending; adjust if current helpers key only on `planned`/`pending` (verify in apply).
- **[Risk] Spec sync with US-040B historical “planned” language** → Mitigation: additive requirement; do not rewrite all US-040B history.

## Migration Plan

1. Implement worker mapping + tests.
2. Frontend enum/labels/filters/tests + static rebuild.
3. Deploy worker; no calendar DB migration.
4. Smoke: July 2026 schedule-visibility shows six blogs as `publication_state: completed`, `linkedin_api_published: false`.
5. Rollback: revert deploy; DB unchanged.

## Open Questions

- None blocking apply. Visual DoD / walkthrough for Story accepted remains operator-gated after deploy (same BL-015 pattern).
