# Phase 2 Report: automate-live-blog-git-publication

**Date:** 2026-07-11  
**Server:** silverman@192.168.0.194  
**Change:** automate-live-blog-git-publication  
**Scope:** Phase 2 only (SSH/Git validation + remote URL migration). No deploy, no worker restart, no enablement.

---

## 1. GitHub SSH authentication

| Check | Result |
|-------|--------|
| Private key path | `/home/silverman/silverman-blog-linkedin-worker/secrets/github-pages-deploy-key` — present, mode `600` |
| known_hosts path | `/home/silverman/silverman-blog-linkedin-worker/secrets/known_hosts` — present, mode `644` |
| SSH options used | `IdentitiesOnly=yes`, `StrictHostKeyChecking=yes`, `UserKnownHostsFile=<known_hosts>` |
| Authentication | **PASS** — GitHub responded: authenticated as `silverberdi/silverberdi.github.io` (shell access denied, expected) |

## 2. git ls-remote (read-only, dedicated key)

| Check | Result |
|-------|--------|
| Command | `git ls-remote git@github.com:silverberdi/silverberdi.github.io.git` with `GIT_SSH_COMMAND` using dedicated key |
| Authentication | **PASS** |
| HEAD | `a227814f33f13a034a371553488f566524defb88` |
| refs/heads/main | `a227814f33f13a034a371553488f566524defb88` |
| Ref count | 2 |
| Remote mutations | **None** (read-only query) |

## 3. Deploy-key write access (operator-reported)

| Check | Result |
|-------|--------|
| GitHub deploy key on `silverberdi/silverberdi.github.io` | **Operator confirmed:** added with **Allow write access** enabled |
| Server-side write proof | **Not performed** (no commit/push in Phase 2) |

## 4. known_hosts verification

| Check | Result |
|-------|--------|
| github.com entry | **Present** |
| Key type | `ssh-ed25519` |
| StrictHostKeyChecking | **PASS** (no host-key prompt; connection succeeded) |

## 5. Public checkout remote migration

**Repository:** `/home/silverman/silverberdi.github.io`

| Item | Before | After |
|------|--------|-------|
| origin fetch URL | `https://github.com/silverberdi/silverberdi.github.io.git` | `git@github.com:silverberdi/silverberdi.github.io.git` |
| origin push URL | `https://github.com/silverberdi/silverberdi.github.io.git` | `git@github.com:silverberdi/silverberdi.github.io.git` (inherits fetch) |
| Branch | `main` | `main` (unchanged) |
| Working tree | clean (0 dirty entries) | clean (0 dirty entries) |
| fetch/pull/commit/push | **Not performed** | **Not performed** |

**Git config changed:** `remote.origin.url` only (via `git remote set-url origin`).

## 6. Dedicated-key read-only access from checkout

| Check | Result |
|-------|--------|
| Command | `git -C /home/silverman/silverberdi.github.io ls-remote origin HEAD` with `GIT_SSH_COMMAND` using dedicated key |
| Result | **PASS** — `a227814f33f13a034a371553488f566524defb88 HEAD` |
| Remote mutations | **None** |

## 7. Phase 3 — proposed Compose changes

**Current mount** (`silverman-worker.compose.yaml`):

```yaml
- /home/silverman/silverman-blog-linkedin-worker/secrets:/secrets
```

**Problem:** Broad writable mount exposes all secrets directory contents to the container with write access.

**LinkedIn OAuth inspection (before proposing removal):**

| Path | Host | Container | Notes |
|------|------|-----------|-------|
| `linkedin-oauth-tokens.json` | **Absent** | **Absent** | `SILVERMAN_LINKEDIN_TOKEN_STORE_PATH=/secrets/linkedin-oauth-tokens.json` configured in `.env` |
| `linkedin-oauth-state.json` | **Absent** | **Absent** | OAuth state file per deployment docs |
| `github-pages-deploy-key` | Present (600) | Present (600) | Phase 2 validated |
| `known_hosts` | Present (644) | Present (644) | Phase 2 validated |
| `github-pages-deploy-key.pub` | Present | Present | Public key; optional ro mount |

**Proposed replacement** (apply in Phase 3 with container recreate):

```yaml
volumes:
  - /home/silverman/compartido_mac/silverman-blog-linkedin:/data/silverman-blog-linkedin
  - ${SILVERMAN_PUBLIC_BLOG_REPO_PATH:-/home/silverman/silverberdi.github.io}:/public-blog
  # Git publication SSH — read-only
  - /home/silverman/silverman-blog-linkedin-worker/secrets/github-pages-deploy-key:/secrets/github-pages-deploy-key:ro
  - /home/silverman/silverman-blog-linkedin-worker/secrets/known_hosts:/secrets/known_hosts:ro
  # LinkedIn OAuth — writable file mounts (preserve existing container paths)
  - /home/silverman/silverman-blog-linkedin-worker/secrets/linkedin-oauth-tokens.json:/secrets/linkedin-oauth-tokens.json
  - /home/silverman/silverman-blog-linkedin-worker/secrets/linkedin-oauth-state.json:/secrets/linkedin-oauth-state.json
```

**Operator prerequisite before Phase 3 recreate:** create LinkedIn OAuth placeholder files on host if absent (Docker file bind-mounts require existing host files):

```bash
touch /home/silverman/silverman-blog-linkedin-worker/secrets/linkedin-oauth-tokens.json
touch /home/silverman/silverman-blog-linkedin-worker/secrets/linkedin-oauth-state.json
chmod 600 /home/silverman/silverman-blog-linkedin-worker/secrets/linkedin-oauth-tokens.json
chmod 600 /home/silverman/silverman-blog-linkedin-worker/secrets/linkedin-oauth-state.json
```

Do **not** remove LinkedIn OAuth mounts; narrow only the broad `/secrets` directory mount.

## 8. Phase 3 — proposed .env changes (not applied)

Add Git SSH command for worker subprocess Git operations (container paths):

```bash
GIT_SSH_COMMAND=ssh -i /secrets/github-pages-deploy-key -o IdentitiesOnly=yes -o UserKnownHostsFile=/secrets/known_hosts -o StrictHostKeyChecking=yes
```

Enable only after controlled validation (Phase 3+):

```bash
# SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true   # DO NOT enable in Phase 2
# SILVERMAN_BLOG_GIT_PUBLICATION_BRANCH=main    # default
# SILVERMAN_BLOG_GIT_PUBLICATION_REMOTE=origin  # default
```

**Current state:** No `GIT_SSH_COMMAND` or `SILVERMAN_BLOG_GIT_*` variables set in server `.env`.

## 9. Blockers for Phase 3

1. **Compose mount narrowing** — broad `/secrets` mount still active; must apply explicit ro/w mounts and recreate container.
2. **GIT_SSH_COMMAND** — not yet in server `.env`; required for container-side `git push` via deploy key.
3. **LinkedIn OAuth file bind-mount prep** — `linkedin-oauth-tokens.json` and `linkedin-oauth-state.json` absent on host; must exist before file-level Docker binds.
4. **Enablement flag** — `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` remains `false` (intentional until controlled validation).
5. **Write-access proof** — deploy key write access operator-confirmed but not exercised via worker `git push` yet.
6. **US-001 business validation** — tasks 8.2–8.6 (controlled `git_publication: true` smoke with real push evidence) not started.

## 10. Server files / Git config changed in Phase 2

| File | Change |
|------|--------|
| `/home/silverman/silverberdi.github.io/.git/config` | `remote.origin.url` changed HTTPS → SSH |

**Not changed:** worker compose, worker `.env`, deploy keys, known_hosts, worker container, application repository.

---

## Summary

| Phase 2 step | Status |
|--------------|--------|
| SSH authentication | PASS |
| git ls-remote (dedicated key) | PASS |
| Remote URL migration (checkout) | DONE |
| Branch main / clean working tree | CONFIRMED |
| Checkout ls-remote origin | PASS |
| Deploy / restart / enablement | NOT PERFORMED (per instructions) |

**Phase 2 complete.** Proceed to Phase 3 when ready: compose mount narrowing, `.env` `GIT_SSH_COMMAND`, container recreate, then controlled validation with `git_publication: true`.
