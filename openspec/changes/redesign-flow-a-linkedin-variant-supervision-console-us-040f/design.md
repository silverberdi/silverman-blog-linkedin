## Context

US-040E archived 2026-07-18. A console-layer UX redesign (US-040F) landed in the working tree and main specs before an active change existed. This design restores normative decisions for that slice and records known gaps for follow-up UX work.

**Constraints:** ADR-0001 browser → worker HTTP only; preserve A–E; no public URL/Google; no BL-015 close from this change; prefer existing APIs.

## Goals / Non-Goals

**Goals:** modern operational app shell; interactive metrics; card triage + detail drawer; calendar schedule-first; technical prose secondary; OpenSpec continuity; honest “UX still iterating” status.

**Non-Goals:** final visual acceptance; public hosting/IdP; new mutation SoT; Flow B.

## Decisions

### D1 — Retroactive alignment, not a fake timeline

**Choice:** Proposal/design/tasks/delta explicitly state this is retroactive alignment of an already-demonstrated console-layer redesign. Sync to main is **parity** with requirements already present under US-040F in `openspec/specs/linkedin-variant-supervision-console/spec.md`.

### D2 — App shell structure

**Choice:** Top app bar (brand + view switch + refresh + dry-run/commit mode), session strip, alert stack, interactive metric strip, filter dock, content workspace. Remove endpoint-heavy footer from primary chrome; keep diagnostics in details.

### D3 — List = cards + selected detail drawer

**Choice:** Replace table-first desktop layout with card triage for all widths; selecting a card opens a contextual detail drawer (master-detail). Edit/cancel/schedule panels also use drawer chrome. Month remains first-class via view switcher.

### D4 — Metric → filter semantics (normative)

Each metric click **resets focus flags** (`blockedOnly`, `dueSoonOnly`, `publicationStates`) then applies:

| Metric | Filter effect |
|--------|----------------|
| Upcoming | Clear focus flags only (show full filtered universe; upcoming is a count lens, not a new filter field) |
| Pending | `publicationStates: ["pending"]` |
| Due soon | `dueSoonOnly: true` |
| Deferred | `publicationStates: ["deferred"]` |
| Blocked | `blockedOnly: true` |
| Failed | `publicationStates: ["failed"]` |
| Recently published | `publicationStates: ["published"]` (API-evidence display state; not `flow_a_complete` / handoff) |

Channel and campaign query are preserved across metric clicks.

### D5 — Schedule time labeling

**Choice:** List card schedule shows **local** wall time with timezone name, prefixed with clarity that day placement on Month remains UTC-based. Avoid bare ISO UTC-only strings as the only human schedule line.

### D6 — Further UX is expected

**Choice:** Do not mark Story accepted. Browser screenshot matrix may remain incomplete. Operator feedback continues in a follow-up change after visual direction is agreed.

### D7 — Local preview proxy (dev only)

**Choice:** Vite `server.proxy` may forward relative API paths to `VITE_WORKER_PROXY` or `http://192.168.0.194:8010` for local UX review. Production remains same-origin worker static serving.

## Risks / Trade-offs

- [Risk] Operator rejects first redesign pass → Mitigation: D6; hold deploy; follow-up UX change.
- [Risk] Metric “upcoming” cannot express future-only without new filter → Mitigation: D4 clear-focus semantics; follow-up may add dedicated upcoming filter if needed.
- [Risk] Main specs already contain F → Mitigation: D1 parity sync + archive for continuity.

## Open Questions

_None blocking alignment._ Further visual direction is an explicit post-archive conversation, not silent scope expansion here.
