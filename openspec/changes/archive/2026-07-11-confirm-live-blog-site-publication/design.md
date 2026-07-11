## Context

US-001 delivered guarded `git add` / `git commit` / `git push` in `github_pages_git_publication.py`, opt-in on `POST /publish-blog-post` and calendar Flow A execution, and operational validation with real remote push on `192.168.0.194`. Canonical spec `github-pages-git-publication` explicitly deferred US-002: no `git fetch`, no remote reconciliation, no live HTTP probe, and non-fast-forward push failures return `partial` with manual recovery only.

Campaign metadata records publish-confirmed `source_public_url` after successful blog handoff (bridge apply), but that URL is a convention-based path — not proof the page is HTTP-reachable after GitHub Pages deploy. LinkedIn package generation and editorial policy treat `source_public_url` as publish-confirmed for CTA eligibility; US-002 closes the gap between "pushed to `origin/main`" and "live on `silverman.pro`".

Constraints:

- ADR-0001: n8n orchestrates via HTTP only; Git and HTTP probes run inside the worker.
- Fail closed when disabled (mirror US-001 dual guard pattern).
- No secrets in responses, metadata, logs, or docs.
- Develop on Mac; deploy Docker on `192.168.0.194` with public blog mount `/public-blog`.
- US-001 behavior MUST remain unchanged when US-002 features are not opted in.

## Goals / Non-Goals

**Goals:**

- HTTP-probe `source_public_url` after successful Git push when enabled and opted in; persist `blog_live_site_publication` evidence.
- `git fetch` before push; fast-forward-only `git pull --ff-only` when local branch is behind remote and working tree is clean for scoped paths.
- Detect unsafe duplicate publication: scoped artifacts already committed on remote for a different campaign, equivalent remote content for same paths, repeat push when live confirmation already succeeded.
- Return structured JSON (`blog_live_site_publication`, extended errors) for n8n branching; `partial` when push succeeds but live confirmation fails.
- Injectable `HttpProbeClient` and extended `GitRunner` fakes for unit tests.
- Controlled operational validation script and evidence report on `192.168.0.194`.

**Non-Goals:**

- GitHub Pages deploy-status REST API or Actions polling.
- Force-push, merge commits, or rebase when checkout has conflicts or unrelated dirty files.
- Automatic recovery when unrelated local changes block ff-only pull (operator manual path).
- n8n workflow activation.
- Changing LinkedIn package CTA rules beyond existing publish-confirmed URL semantics.
- Flow B campaigns.

## Decisions

### 1. New module `blog_live_site_confirmation.py`

**Choice:** Isolate HTTP probe logic with injectable `HttpProbeClient` protocol (production uses `urllib` or `httpx` if already a dependency — prefer stdlib `urllib.request` to avoid new deps).

**Rationale:** Keeps `github_pages_git_publication.py` focused on Git; mirrors US-001 module split.

**Alternative considered:** Embed probe in Git module — rejected to keep responsibilities separable and testable.

### 2. Orchestration order in `publish_blog_post`

**Choice:** After successful blog handoff:

1. Git publication (when `git_publication: true` and enabled) — now includes fetch + ff-only reconciliation before push.
2. Live-site confirmation (when `live_site_confirmation: true` and enabled) — only after `blog_git_publication.status` is `pushed` or `already_published` in the same invocation, OR when campaign metadata proves prior successful push for this publication.

**Rationale:** Probe is meaningless before push; US-002 acceptance criteria tie live availability to remote publication.

**Alternative considered:** Probe without Git — rejected; handoff-only path does not claim site published/live per GLOSSARY.

### 3. Dual guard for live confirmation

**Choice:**

- `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED=true` (default false)
- Request `live_site_confirmation: true`

Both required. Requesting live confirmation without Git publication opt-in MUST fail with `blog_live_site_confirmation_git_required` when push evidence is absent.

**Rationale:** Matches US-001 guard pattern; prevents accidental production HTTP probes from dev workflows.

### 4. Remote reconciliation: fetch + ff-only pull

**Choice:** Before `git push`:

1. `git fetch <remote>`
2. Compare `HEAD` to `<remote>/<branch>`
3. If behind and ff-only merge possible with clean scoped paths: `git pull --ff-only`
4. If behind and ff-only not possible, or unrelated dirty files would be affected: fail with `blog_git_publication_remote_diverged` (partial after handoff)
5. If ahead or equal: proceed to commit (if needed) and push

**Rationale:** Satisfies US-002 divergence handling without merge/rebase conflict resolution. Conservative: never auto-merge when checkout has unstaged unrelated changes.

**Alternative considered:** Always fail on behind-remote — rejected; common case is another operator pushed unrelated content and ff-only is safe.

### 5. Cross-campaign duplicate detection

**Choice:** After fetch, before commit:

- `git log -- <scoped_paths>` on remote tracking branch
- If paths exist at remote tip with different `campaign_id` in last commit message (or blob hash mismatch vs local staged content for same paths): fail with `blog_git_publication_duplicate_artifacts`
- Per-campaign US-001 idempotency unchanged

**Rationale:** Prevents overwriting another campaign's live post files without operator awareness.

### 6. Live probe semantics

**Choice:**

- `GET source_public_url` with configurable timeout (default 10s), max retries (default 5), backoff (default 2s linear)
- Success: HTTP 200 and response body contains a stable marker (e.g. post `public_slug` or `<title>` from frontmatter) — configurable strictness: default require slug in body
- Record: `status` (`confirmed` | `failed` | `already_confirmed`), `http_status`, `final_url`, `attempts`, `confirmed_at`
- Redirects followed up to 5 hops; final URL recorded

**Rationale:** GitHub Pages may lag; retries handle propagation delay without deploy API.

**Alternative considered:** HEAD-only check — rejected; 200 on CDN miss or placeholder pages is insufficient.

### 7. Partial vs completed when probe fails

**Choice:**

- Push succeeded, probe failed → overall `status: partial`, `blog_git_publication.status` remains `pushed`, `blog_live_site_publication.status` `failed` with `blog_live_site_confirmation_unreachable`
- Push and probe succeeded → `status: completed`
- Idempotent: prior `blog_live_site_publication.status` `confirmed` → `already_confirmed` without new HTTP requests when within TTL (optional: 1h cache in metadata)

**Rationale:** Aligns with US-001 partial semantics; operator can retry probe without re-handoff.

### 8. Calendar connector passthrough

**Choice:** Extend `execute_due_editorial_calendar_flow_a(..., live_site_confirmation: bool = False)` and HTTP body field; pass to `publish_blog_post` during real execution only.

**Rationale:** Parity with `git_publication` from US-001.

### 9. Configuration surface

| Variable | Default | Purpose |
|----------|---------|---------|
| `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED` | false | Env guard |
| `SILVERMAN_BLOG_LIVE_SITE_PROBE_TIMEOUT_SECONDS` | 10 | Per-attempt timeout |
| `SILVERMAN_BLOG_LIVE_SITE_PROBE_MAX_ATTEMPTS` | 5 | Retry count |
| `SILVERMAN_BLOG_LIVE_SITE_PROBE_RETRY_DELAY_SECONDS` | 2 | Delay between attempts |
| `SILVERMAN_BLOG_GIT_FETCH_TIMEOUT_SECONDS` | 30 | Git fetch timeout (extend existing Git config module) |

### 10. GLOSSARY publication layers

**Choice:** When US-002 is operationally validated, update `docs/GLOSSARY.md` to distinguish four layers: blog handoff → blog Git publication → live-site confirmation → site published/live (confirmed).

**Rationale:** Prevents conflating `blog_git_publication.status` `pushed` with HTTP reachability; aligns terminology with campaign metadata fields introduced by US-001 and US-002.

**Target glossary rows (apply during docs sync):**

| Term | Definition |
|------|------------|
| **Blog handoff** | Worker wrote Jekyll files to `/public-blog` |
| **Blog Git publication** | Worker commit/push when opted in; evidence in `blog_git_publication` |
| **Live-site confirmation** | Worker HTTP probe after push when opted in; evidence in `blog_live_site_publication` |
| **Site published/live** | Public HTTP reachability — recorded by `blog_live_site_publication.status` `confirmed` or operator manual verification; Git push alone is not sufficient |

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| GitHub Pages propagation slower than retry window | Configurable attempts/delay; operational validation tunes defaults; partial status allows operator retry |
| False positive probe (200 but stale CDN) | Require slug marker in body; document limitation in ops report |
| ff-only pull fails on divergent history | Fail closed with `blog_git_publication_remote_diverged`; operator manual recovery documented |
| Unrelated dirty files block reconciliation | Do not auto-stash; fail with actionable error |
| HTTP probe from container to public internet | Required for US-002; validate in deploy smoke only during validation window |
| Probe abuse / SSRF if URL attacker-controlled | `source_public_url` only from worker-computed publish result; validate host against `site_base_url` allowlist (`silverman.pro`) |

## Migration Plan

1. Implement modules and tests on Mac.
2. Deploy worker image to `192.168.0.194`.
3. Enable `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED=true` only during validation window.
4. Run controlled smoke (isolated post or revertible commit) with `git_publication: true` and `live_site_confirmation: true`.
5. Capture evidence: container egress precheck, HTTP status, final URL, slug marker in body, probe attempts, campaign metadata, `git log` on remote.
6. Disable live confirmation env flag after validation unless operator approves production enablement.
7. Update GLOSSARY (publication layers), CURRENT-STATE, RUNTIME-STATE, progress checklist only after demonstrated criteria.

**Rollback:** Disable env flags; prior US-001 path unaffected. No schema migration — new metadata fields are additive.

## Open Questions

- Whether to add a dedicated `POST /confirm-blog-live-site` retry endpoint (deferred — retry via full publish with idempotency is sufficient for US-002 MVP).
- Default probe marker strictness: slug-only vs title+slug (recommend slug-only for stability).
