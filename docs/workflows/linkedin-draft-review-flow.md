# LinkedIn Draft Review Flow

**Superseded product framing (2026-07-19):** Canonical Flow B is no longer “mandatory LinkedIn draft review.” Flow B is **AI blog discovery/draft → operator blog approval → Flow A**. Normative policy: [flow-b-simplified-policy.md](../operations/flow-b-simplified-policy.md). Planning: [planning-notes-flow-b-simplification.md](../product/planning-notes-flow-b-simplification.md). Backlog BL-016–BL-019 (US-074–US-082). Editorial: `#flow-a-vs-flow-b`.

This document remains useful as the **historical / adjacent** folder path for LinkedIn draft files (`review/` → `approved/` → `published/`) and draft-generation orchestration. It MUST NOT be read as requiring a second mandatory LinkedIn gate after an approved Flow B blog enters Flow A.

Flow A automatic distribution: [flow-a-target-flow.md](flow-a-target-flow.md).

Terminology: [GLOSSARY.md](../GLOSSARY.md). Editorial policy: `content-strategy/silverman-editorial-system.md`.

## Actors

- **Worker** — generates drafts (single variant or package metadata from Flow A)
- **Reviewer** — human operator (Silverio)
- **n8n** — optional draft-generation orchestration (`silverman-blog-linkedin-draft-generation.json`)

## Flow diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LINKEDIN DRAFT REVIEW (Flow B–adjacent)                   │
└─────────────────────────────────────────────────────────────────────────────┘

  Worker generation
      │
      ▼
  linkedin-posts/review/      ← drafts awaiting human review
      │
      │  approve acceptable variants
      ▼
  linkedin-posts/approved/
      │
      │  manual publish (current production path)
      ▼
  linkedin-posts/published/

  Future boundary: guarded POST /publish-linkedin-due-variants
  (implemented; not operationally validated — see CURRENT-STATE)
```

## Step summary

| Step | Location | Action |
|------|----------|--------|
| 1 | Worker | `POST /generate-linkedin-draft` or package from Flow A |
| 2 | `linkedin-posts/review/` | Draft files written by worker |
| 3 | Reviewer | Read, edit if needed, approve |
| 4 | `linkedin-posts/approved/` | Human moves or approves drafts |
| 5 | `linkedin-posts/published/` | Manual LinkedIn publish (copy/paste or future API) |

## Distinction from Flow A

| Aspect | Flow A | This flow |
|--------|--------|-----------|
| Primary output | Package + schedule metadata | Human-reviewed drafts |
| Folder emphasis | `generated/`, campaign metadata | `review/` → `approved/` → `published/` |
| Publication | Schedule metadata (`publish_state: pending`) | Manual or guarded API |
| Source lifecycle | Moves `ready` → `queued` → `processed` | Source may remain in `ready` for draft-only workflows |

## Manual publication boundary

Phase 1 production expectation: reviewer publishes manually on LinkedIn. Worker LinkedIn API endpoints exist but require `SILVERMAN_LINKEDIN_PUBLICATION_ENABLED=true` and are not operationally validated at last baseline.

Package `public_image_url` is link-preview metadata only — not LinkedIn media upload.

## Related documents

- [flow-a-target-flow.md](flow-a-target-flow.md)
- [linkedin-publication-prerequisites.md](../deployment/linkedin-publication-prerequisites.md)
- n8n draft workflow: `n8n/workflows/silverman-blog-linkedin-draft-generation.json`
