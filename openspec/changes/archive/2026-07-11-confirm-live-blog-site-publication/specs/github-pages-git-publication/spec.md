## MODIFIED Requirements

### Requirement: Push to configured remote branch

After a successful local commit (or when there is nothing new to commit per idempotency rules), the worker MUST push to the configured remote and branch.

Default remote MUST be `origin`.

Default branch MUST be configurable via `SILVERMAN_BLOG_GIT_PUBLICATION_BRANCH` with fallback `main`.

The worker MUST NOT force-push.

Before push, the worker MUST run `git fetch <remote>` and reconcile the local branch with the remote tracking branch using fast-forward-only rules per the **Remote reconciliation before push** requirement in this spec.

Push failures after successful handoff MUST return overall publish `status: partial` with stable error code `blog_git_publication_push_failed` and a safe, actionable message without secrets.

Push failures before successful handoff MUST return overall publish `status: failed`.

Remote divergence that cannot be resolved via fast-forward-only pull MUST return overall publish `status: partial` with stable error code `blog_git_publication_remote_diverged` after successful handoff.

#### Scenario: Successful push to default branch

- **WHEN** local commit succeeds, fetch completes, branch is reconciled or already up to date, remote `origin` and branch `main` are configured, and push succeeds
- **THEN** Git publication returns overall `status: completed` with `blog_git_publication.status` `pushed` and records remote branch metadata

#### Scenario: Push failure after handoff is partial

- **WHEN** blog handoff succeeded, `git_publication` was requested, and `git push` fails
- **THEN** the worker returns overall `status: partial`, `blog_publish` preserves successful handoff evidence, `blog_git_publication.status` is `failed` with `blog_git_publication_push_failed`, and the response states files were written but remote Git publication did not complete

#### Scenario: Fetch before push

- **WHEN** Git publication runs against a public checkout
- **THEN** the worker invokes `git fetch` for the configured remote before `git push`

#### Scenario: Fast-forward pull when behind remote

- **WHEN** after fetch the local branch is behind `origin/main`, the working tree has no conflicts for ff-only merge, and unrelated dirty files are not affected
- **THEN** the worker runs `git pull --ff-only` and proceeds to push

#### Scenario: Non-fast-forward divergence fails closed

- **WHEN** after fetch the local and remote branches have diverged and fast-forward-only reconciliation is not possible
- **THEN** the worker returns overall `status: partial` with `blog_git_publication_remote_diverged` after successful handoff and does not force-push

### Requirement: Git publication idempotency and duplicate prevention

When campaign metadata records successful Git publication (`blog_git_publication.status` `pushed`) for the same `blog_publish.idempotency_key` with matching `commit_sha` and scoped artifact paths, and the working tree has no changes for those paths, a repeat Git publication request MUST:

- return overall `status: completed` with `blog_git_publication.status` `already_published`;
- NOT create another commit;
- NOT perform an unnecessary push;
- NOT overwrite prior successful Git evidence with weaker or ambiguous state.

When scoped artifact paths match the last successful Git publication metadata and `git diff` shows no changes for those paths, the worker MUST return `already_published` without creating an empty commit.

Before creating a new commit, the worker MUST detect cross-campaign duplicate publication attempts: when scoped artifact paths already exist on the remote tracking branch at a commit not attributable to the same campaign (per commit message `campaign_id` or matching blob content), Git publication MUST fail with `blog_git_publication_duplicate_artifacts` without overwriting remote content.

When remote history contains equivalent content for scoped paths from a prior successful push for the same campaign, the worker MUST return `already_published` without a duplicate commit.

#### Scenario: Repeat request after successful push

- **WHEN** Git publication already succeeded for a campaign with matching idempotency evidence and the client requests Git publication again
- **THEN** the worker returns `blog_git_publication.status` `already_published` without a new commit or push

#### Scenario: Clean tree with prior success

- **WHEN** scoped artifact paths match the last successful Git publication metadata and `git diff` shows no changes for those paths
- **THEN** the worker returns `already_published` without creating an empty commit

#### Scenario: Prior success evidence preserved

- **WHEN** a repeat request finds matching successful `blog_git_publication` evidence
- **THEN** campaign metadata retains the prior `commit_sha`, `remote`, `branch`, and `pushed` status

#### Scenario: Cross-campaign path collision blocked

- **WHEN** scoped artifact paths already exist on the remote branch for a different `campaign_id` and local content would collide
- **THEN** Git publication fails with `blog_git_publication_duplicate_artifacts` and does not push

### Requirement: Git publication automated tests

The repository SHALL include automated tests for Git publication using injectable Git subprocess fakes or temporary repositories.

Tests MUST cover: disabled guard, environment-only enablement does not publish, controlled staging scope, successful commit and push, fetch before push, fast-forward pull when behind, remote divergence failure, duplicate artifact detection, push failure after handoff returns partial, missing artifacts, `already_published` idempotency, unrelated dirty files untouched, and Flow B rejection.

Tests MUST NOT require real network access or live GitHub credentials.

#### Scenario: Disabled guard test

- **WHEN** tests run Git publication with enablement flag false
- **THEN** tests verify no subprocess calls occur and `blog_git_publication_disabled` is returned

#### Scenario: Environment enablement without opt-in test

- **WHEN** tests run publish with `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true` and `git_publication` false or omitted
- **THEN** tests verify no `git` subprocess calls occur

#### Scenario: Scoped staging test

- **WHEN** tests simulate unrelated dirty files in the public checkout
- **THEN** tests verify only the two artifact paths are passed to `git add` and unrelated files are not staged

#### Scenario: Idempotent rerun test

- **WHEN** tests simulate a prior successful push for the same campaign idempotency evidence
- **THEN** tests verify no new commit or push occurs and `already_published` is returned

#### Scenario: Fetch before push test

- **WHEN** tests run Git publication with a successful handoff
- **THEN** tests verify `git fetch` is invoked before `git push`

## ADDED Requirements

### Requirement: Remote reconciliation before push

Git publication MUST run `git fetch` for the configured remote before attempting `git push`.

After fetch, when the local branch is behind the remote tracking branch and `git merge-base --is-ancestor` confirms fast-forward is possible without touching unrelated dirty files, the worker MUST run `git pull --ff-only` for the configured remote and branch.

When fast-forward reconciliation is not possible, or unrelated unstaged changes would be at risk, the worker MUST NOT run merge or rebase and MUST fail with `blog_git_publication_remote_diverged` when handoff already succeeded.

Fetch timeout MUST be configurable via `SILVERMAN_BLOG_GIT_FETCH_TIMEOUT_SECONDS` with a sensible default.

#### Scenario: Behind remote fast-forward succeeds

- **WHEN** fetch shows local `main` is behind `origin/main` by commits that do not modify the scoped artifact paths and ff-only pull succeeds
- **THEN** Git publication proceeds to commit (if needed) and push

#### Scenario: Diverged history fails closed

- **WHEN** fetch shows local and remote branches have diverged
- **THEN** Git publication returns `blog_git_publication_remote_diverged` without force-push

## REMOVED Requirements

### Requirement: US-001 Git publication idempotency

**Reason**: Superseded by expanded **Git publication idempotency and duplicate prevention** requirement covering US-002 cross-campaign and equivalent-commit detection.

**Migration**: Use the renamed requirement; behavior for per-campaign idempotency is preserved and extended.

### Requirement: Git publication non-goals for US-002 deferral

**Reason**: US-002 is in scope for this change via `blog-live-site-confirmation` and updated Git publication requirements.

**Migration**: Live URL probing is implemented in `blog-live-site-confirmation`. Remote reconciliation and duplicate prevention are implemented in this spec. Non-fast-forward push now attempts fetch/ff-only before failing.
