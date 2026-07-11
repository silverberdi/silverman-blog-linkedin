## Why

US-001 (`automate-live-blog-git-publication`) operationally validated guarded `git commit` and `git push` after blog handoff, but deliberately deferred **US-002** concerns: live-site reachability, remote-history reconciliation, and advanced duplicate prevention. Campaign metadata still records a publish-confirmed `source_public_url` after handoff/Git push without proving the page is HTTP-reachable on `silverman.pro`, and non-fast-forward push failures return `partial` with no safe recovery path. **BL-001** cannot close until operators can trust that a pushed publication is live and that repeat or divergent Git attempts fail safely without duplicate commits or unintended merges.

## What Changes

- Add an optional **live-site confirmation** step after successful Git push (when enabled and opted in) that HTTP-probes `source_public_url` with bounded retries and records structured evidence on the campaign.
- Introduce **remote reconciliation** before push: `git fetch` and compare local HEAD to remote; fail closed or apply a conservative fast-forward-only pull when the checkout is behind and clean.
- Extend **duplicate prevention** beyond US-001 per-campaign idempotency: detect equivalent scoped artifacts already on remote, cross-campaign path collisions, and reject unsafe duplicate publication attempts.
- Expose confirmation and reconciliation outcomes in publish HTTP responses (`blog_live_site_publication`, extended `blog_git_publication`) for n8n branching.
- Add env guards mirroring US-001 (`SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED` + per-request `live_site_confirmation: true`) so probes never run by default in dev/smoke.
- Document controlled operational validation on `192.168.0.194` with evidence artifacts (HTTP status, final URL, timing).
- Update product progress for **US-002** only when acceptance criteria are demonstrated with real live-site evidence; do not claim **BL-001** complete until all US-002 criteria pass.

### Goals

- Satisfy **US-002** acceptance criteria for live availability, safe divergence handling, and advanced duplicate prevention.
- Preserve US-001 handoff-only and Git-only paths when live confirmation is not opted in.
- Keep all Git and HTTP probe logic inside the worker (ADR-0001).

### Non-Goals

- GitHub Pages deploy-status API integration (HTTP probe to public URL is sufficient for US-002).
- Force-push, branch creation, or automatic conflict resolution via merge/rebase when the checkout has unrelated local changes.
- n8n workflow activation or scheduling changes.
- LinkedIn CTA gating changes beyond using existing publish-confirmed `source_public_url` semantics.
- Flow B paths.
- Claiming `flow_a_complete` or fully unattended Flow A.

## Capabilities

### New Capabilities

- `blog-live-site-confirmation`: Bounded HTTP reachability probe of `source_public_url` after successful Git push; campaign metadata `blog_live_site_publication`; structured errors and retry policy; env + per-request guards.

### Modified Capabilities

- `github-pages-git-publication`: Remove US-002 deferrals; add `git fetch` and fast-forward-only reconciliation before push; cross-campaign and equivalent-commit duplicate detection; extend idempotency and error codes.
- `flow-a-automatic-publishing`: Define US-002 blog publication layer (reconciliation + live confirmation); update BL-001 completion rules.
- `worker-blog-publishing-endpoint`: Optional `live_site_confirmation` request field; publish result includes live confirmation evidence; partial/failed semantics when push succeeds but probe fails.
- `editorial-calendar-flow-a-execution-connector`: Pass `live_site_confirmation` opt-in through calendar Flow A execution (parallel to `git_publication`).
- `repository-context-governance`: Extend `docs/GLOSSARY.md` with publication layers (blog Git publication, live-site confirmation, site published/live) so Git push alone is not conflated with confirmed live reachability.

## Impact

- **Code:** `github_pages_git_publication.py` (reconciliation), new `blog_live_site_confirmation.py` (or equivalent module), `blog_publish_flow.py`, `main.py`, `editorial_calendar_flow_a_execute.py`, campaign metadata writers.
- **APIs:** `POST /publish-blog-post` and `POST /editorial-calendar/execute-flow-a-due` request/response shapes.
- **Config:** New env vars for live confirmation enablement, probe timeout/retry tuning; possible Git fetch timeout settings.
- **Tests:** Injectable HTTP client fakes; Git runner scenarios for fetch/ff-only and divergence; no live network in unit tests.
- **Docs:** `docs/GLOSSARY.md`, `docs/CURRENT-STATE.md`, `docs/RUNTIME-STATE.md`, `docs/product/progress-checklist.md` (after validation), operational validation report.
- **Systems:** Public blog checkout on `192.168.0.194`, GitHub Pages at `https://silverman.pro/`, existing deploy key for fetch/push.

## Backlog mapping

| ID | Acceptance criteria addressed |
|----|-------------------------------|
| **BL-001** | Completion outcome depends on US-002 — not claimed by this proposal alone. |
| **US-002** | Live availability confirmation; duplicate commit/publication prevention (advanced); remote divergence handling; visible outcomes; clear failure communication; no unintentional duplication. |
| **US-001** | Not modified — remains validated; this change builds on top. |

### Intentionally excluded from this change

- Marking **BL-001** complete before operational US-002 validation evidence exists.
- Automatic merge/rebase when the public checkout has dirty unrelated files (operator manual recovery).
- GitHub Pages build/deploy API polling.
