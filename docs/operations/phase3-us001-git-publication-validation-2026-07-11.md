# Phase 3 Report: US-001 Git publication validation

**Date:** 2026-07-11  
**Server:** silverman@192.168.0.194  
**Change:** automate-live-blog-git-publication  
**Script:** `deploy/server/run-us001-git-publication-smoke.sh`

## Preconditions applied

- Compose secrets mounts narrowed (deploy key + known_hosts read-only; LinkedIn OAuth file binds)
- `GIT_SSH_COMMAND` in server `.env`
- `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true` during validation window
- Container image includes `git`, `openssh-client`, `safe.directory`, and Git user identity

## Smoke outcome

| Check | Result |
|-------|--------|
| `POST /publish-blog-post` with `git_publication: true` | **PASS** — `status: completed`, `blog_git_publication.status: pushed` |
| Remote `origin/main` advanced | **PASS** — `a227814` → `53d0a26` |
| `commit_sha` in response/metadata | **PASS** — `53d0a26f872df8879686c6f78314e79d3d265202` |
| Repeat request idempotency | **PASS** — `blog_git_publication.status: already_published`, remote unchanged |
| Scoped artifacts only | **PASS** — post + image paths only; no unrelated files staged |
| Partial after handoff (pre-fix failures) | **Observed** — `status: partial` with `blog_git_publication_commit_failed` / `blog_git_publication_push_failed` while `blog_publish` preserved |

## Operational fixes discovered during validation

1. Git `safe.directory` for mounted `/public-blog` checkout
2. `openssh-client` package required for `GIT_SSH_COMMAND`
3. Push-only path records `commit_sha` for idempotent reruns

## Post-validation cleanup (completed)

Validation used an isolated smoke post (not editorial content). After evidence was recorded:

- Public site: removal commit `b128c57` on `silverberdi.github.io` (2026-07-11)
- Editorial mount: smoke ready sources removed
- Campaign metadata: `flow-a-2026-07-11-us001-git-smoke-validation` removed

Smoke validation posts MUST NOT remain on `silverman.pro`.

## US-002 / BL-001

US-001 acceptance criteria demonstrated with real remote push evidence. US-002 live-site confirmation validated separately; see [phase3-us002-live-site-confirmation-validation-2026-07-11.md](phase3-us002-live-site-confirmation-validation-2026-07-11.md). BL-001 closed when both are demonstrated.
