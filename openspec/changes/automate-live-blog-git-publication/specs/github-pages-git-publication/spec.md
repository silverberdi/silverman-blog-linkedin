## ADDED Requirements

### Requirement: Guarded Git publication enablement

The worker SHALL support guarded automated Git commit and push for the public GitHub Pages repository checkout configured by `SILVERMAN_GITHUB_PAGES_REPO_PATH`.

Git publication MUST be disabled by default and MUST require explicit enablement via environment variable `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true`.

Git publication MUST also require per-request opt-in `git_publication: true`. Environment enablement alone MUST NOT trigger Git publication.

When Git publication is disabled, any request that opts into Git publication MUST fail closed with stable error code `blog_git_publication_disabled` and MUST NOT invoke `git` subprocesses.

Git credentials, SSH keys, tokens, credential path contents, and authorization data MUST NOT appear in HTTP responses, campaign metadata, logs, operator documentation examples, or versioned files.

#### Scenario: Disabled Git publication rejects opt-in request

- **WHEN** a client requests Git publication and `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED` is unset or false
- **THEN** the worker returns `status: failed` with `blog_git_publication_disabled` and performs no `git` operations

#### Scenario: Enabled without request opt-in does not publish

- **WHEN** `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true` and a client calls publish or calendar execution without `git_publication: true`
- **THEN** the worker performs blog handoff only and performs no `git` operations

#### Scenario: Enabled Git publication allows opt-in request

- **WHEN** `SILVERMAN_BLOG_GIT_PUBLICATION_ENABLED=true` and a client opts into Git publication with `git_publication: true` after successful blog handoff
- **THEN** the worker MAY proceed to controlled commit and push for the campaign publication artifacts

#### Scenario: No secrets in Git publication response

- **WHEN** Git publication fails due to authentication or remote errors
- **THEN** the structured error does not include tokens, passwords, key material, or credential file contents

### Requirement: Git binary in worker container

The worker Docker image MUST include the `git` binary.

The repository MUST verify that `git` is available in the built container as part of this change (for example `git --version` during image build or documented deploy verification).

Git publication MUST NOT treat Git binary availability as optional.

#### Scenario: Built container provides git

- **WHEN** the worker image is built per this change
- **THEN** `git --version` succeeds inside the container

#### Scenario: Missing git surfaces failure

- **WHEN** Git publication is requested and the `git` binary is unavailable
- **THEN** the worker returns a stable Git publication error without leaking environment details

### Requirement: Deploy key operational prerequisite

Git publication MUST use a dedicated GitHub deploy key with repository-scoped access to the public GitHub Pages repository.

The deploy key private key MUST be mounted read-only from the worker secrets directory into the container for the worker process user.

The credential model MUST NOT reuse a personal interactive GitHub credential.

Operator documentation MUST describe deploy-key setup without embedding secrets, key material, or credential path contents.

Git credential configuration MUST be treated as an operational prerequisite before server validation of Git publication.

#### Scenario: Deploy key documented without secrets

- **WHEN** an operator reads deployment documentation for Git publication
- **THEN** the doc explains deploy-key creation, repository scope, and mount location without including key or token values

#### Scenario: Credential material absent from responses

- **WHEN** Git publication succeeds or fails
- **THEN** HTTP responses and campaign metadata contain no private key, token, or credential file contents

### Requirement: Controlled Git commit scope

Git publication MUST stage and commit only the blog publication artifact paths derived from a successful publish result for the campaign:

- `_posts/YYYY-MM-DD-<public-slug>.md`
- `assets/images/<public-slug>.png`

The worker MUST NOT stage unrelated modified files in the public checkout.

The worker MUST NOT use `git add -A`, `git add .`, or other broad staging commands.

The worker MUST NOT stage, commit, revert, or overwrite unrelated dirty files in the public checkout.

Before staging, the worker MUST verify both target paths exist as regular files under the configured public repo checkout.

If either target path is missing, Git publication MUST fail with `blog_git_publication_artifacts_missing` and MUST NOT create a commit.

#### Scenario: Only publication artifacts are staged

- **WHEN** Git publication runs after successful blog handoff for public slug `why-i-did-not-start-with-the-database` and publication date `2026-07-06`
- **THEN** the worker stages only `_posts/2026-07-06-why-i-did-not-start-with-the-database.md` and `assets/images/why-i-did-not-start-with-the-database.png`

#### Scenario: Unrelated dirty files are not staged

- **WHEN** the public checkout has unrelated modified files and Git publication runs for one campaign
- **THEN** the created commit contains only the two publication artifact paths for that campaign and unrelated files remain unstaged and unmodified by Git publication

#### Scenario: Missing artifact blocks commit

- **WHEN** Git publication is requested but the expected `_posts/` or `assets/images/` target is absent
- **THEN** the worker returns `status: failed` with `blog_git_publication_artifacts_missing` and does not push

### Requirement: Controlled commit message

Git publication MUST create exactly one commit per successful Git publication attempt for a campaign publication.

The commit message MUST be deterministic from campaign identity and MUST include at minimum the `public_slug` and `campaign_id`.

The worker MAY support a configurable message template via `SILVERMAN_BLOG_GIT_COMMIT_MESSAGE_TEMPLATE` with placeholders `{public_slug}`, `{campaign_id}`, and `{publication_date}`.

Commit messages MUST NOT embed secrets or full post body content.

#### Scenario: Commit message includes public slug

- **WHEN** Git publication succeeds for public slug `a-bounded-context-is-not-a-folder` and campaign `camp-20260710-abc`
- **THEN** the created commit message includes `a-bounded-context-is-not-a-folder` and is suitable for operator review in `git log`

#### Scenario: Default template when env unset

- **WHEN** `SILVERMAN_BLOG_GIT_COMMIT_MESSAGE_TEMPLATE` is unset and Git publication succeeds
- **THEN** the worker uses a stable default template referencing `public_slug` and `campaign_id`

### Requirement: Push to configured remote branch

After a successful local commit (or when there is nothing new to commit per US-001 idempotency rules), the worker MUST push to the configured remote and branch.

Default remote MUST be `origin`.

Default branch MUST be configurable via `SILVERMAN_BLOG_GIT_PUBLICATION_BRANCH` with fallback `main`.

The worker MUST NOT force-push.

The worker MUST NOT run `git pull`, `git fetch`, rebase, or merge as part of this capability (deferred to US-002).

Push failures after successful handoff MUST return overall publish `status: partial` with stable error code `blog_git_publication_push_failed` and a safe, actionable message without secrets.

Push failures before successful handoff MUST return overall publish `status: failed`.

#### Scenario: Successful push to default branch

- **WHEN** local commit succeeds, remote `origin` and branch `main` are configured, and push succeeds
- **THEN** Git publication returns overall `status: completed` with `blog_git_publication.status` `pushed` and records remote branch metadata

#### Scenario: Push failure after handoff is partial

- **WHEN** blog handoff succeeded, `git_publication` was requested, and `git push` fails
- **THEN** the worker returns overall `status: partial`, `blog_publish` preserves successful handoff evidence, `blog_git_publication.status` is `failed` with `blog_git_publication_push_failed`, and the response states files were written but remote Git publication did not complete

#### Scenario: No fetch or pull before push

- **WHEN** Git publication runs against a public checkout
- **THEN** the worker does not invoke `git fetch`, `git pull`, rebase, or merge before `git push`

### Requirement: US-001 Git publication idempotency

When campaign metadata records successful Git publication (`blog_git_publication.status` `pushed`) for the same `blog_publish.idempotency_key` with matching `commit_sha` and scoped artifact paths, and the working tree has no changes for those paths, a repeat Git publication request MUST:

- return overall `status: completed` with `blog_git_publication.status` `already_published`;
- NOT create another commit;
- NOT perform an unnecessary push;
- NOT overwrite prior successful Git evidence with weaker or ambiguous state.

When scoped artifact paths match the last successful Git publication metadata and `git diff` shows no changes for those paths, the worker MUST return `already_published` without creating an empty commit.

US-002 owns remote-history divergence reconciliation, equivalent commits after amend or rebase, cross-campaign duplicate detection, automatic fetch/pull/merge/rebase, GitHub Pages deployment confirmation, and live URL reachability.

#### Scenario: Repeat request after successful push

- **WHEN** Git publication already succeeded for a campaign with matching idempotency evidence and the client requests Git publication again
- **THEN** the worker returns `blog_git_publication.status` `already_published` without a new commit or push

#### Scenario: Clean tree with prior success

- **WHEN** scoped artifact paths match the last successful Git publication metadata and `git diff` shows no changes for those paths
- **THEN** the worker returns `already_published` without creating an empty commit

#### Scenario: Prior success evidence preserved

- **WHEN** a repeat request finds matching successful `blog_git_publication` evidence
- **THEN** campaign metadata retains the prior `commit_sha`, `remote`, `branch`, and `pushed` status

### Requirement: Git publication prerequisites

Git publication MUST run only after blog handoff succeeded for the same campaign in the same publish invocation or when campaign metadata proves `blog_publish.status` is `published` or `already_published` with matching `source_content_sha256` and known artifact paths.

Git publication MUST NOT run when blog publish failed or when campaign state is below successful blog handoff.

Git publication MUST NOT run for Flow B campaigns.

#### Scenario: Git publication after successful handoff in same request

- **WHEN** `publish_blog_post` completes handoff with `blog_publish.status` `published` and the client opted into Git publication
- **THEN** Git publication runs as the final step and results are included in the publish response

#### Scenario: Blog publish failure skips Git

- **WHEN** blog handoff fails during `publish_blog_post` with Git publication requested
- **THEN** Git publication is not attempted and no `git` commands run

#### Scenario: Flow B blocked

- **WHEN** Git publication is requested for a Flow B campaign
- **THEN** the operation fails with `blog_git_publication_flow_b_not_allowed`

### Requirement: Campaign metadata blog_git_publication

On Git publication attempt, the worker MUST persist `blog_git_publication` on the campaign with at minimum:

- `status`: one of `pending`, `committed`, `pushed`, `already_published`, `failed`, `skipped`
- `commit_sha` when a commit was created or identified
- `remote` and `branch` when push succeeds or is attempted
- `committed_at` and `pushed_at` as UTC ISO8601 timestamps when applicable
- `staged_paths[]` listing the artifact relative paths
- `error_code` when failed

Campaign metadata MUST NOT store credentials, key material, or full `git` stderr containing secrets.

Prior successful Git evidence MUST NOT be overwritten by weaker or ambiguous state on idempotent or failed retries.

#### Scenario: Successful Git publication metadata

- **WHEN** Git publication commits and pushes successfully
- **THEN** campaign metadata records `blog_git_publication.status` `pushed`, non-empty `commit_sha`, `remote`, `branch`, and `staged_paths` for the two artifacts

#### Scenario: Failed Git publication metadata after handoff

- **WHEN** Git publication fails at commit or push after successful handoff
- **THEN** campaign metadata records `blog_git_publication.status` `failed` and a stable `error_code` while `blog_publish` success evidence remains intact

### Requirement: Git publication result shape

Git publication results MUST be included in publish HTTP responses when Git publication is requested, with at minimum:

- `blog_git_publication.status`
- `blog_git_publication.commit_sha` when known
- `blog_git_publication.remote` and `blog_git_publication.branch` when known
- `blog_git_publication.staged_paths`
- `errors[]` with stable codes on failure

Responses MUST remain suitable for n8n branching without log parsing.

When handoff succeeds but Git commit or push fails, overall response `status` MUST be `partial`, `blog_publish` MUST reflect successful handoff, and the response MUST include an actionable recovery message stating that files were written but remote Git publication did not complete.

#### Scenario: Publish response includes Git evidence on success

- **WHEN** publish and Git publication both succeed
- **THEN** the HTTP response includes overall `status: completed`, `blog_git_publication.status` `pushed`, and `commit_sha`

#### Scenario: Git failure after handoff returns partial

- **WHEN** Git publication fails after successful handoff
- **THEN** response `status` is `partial`, `errors[]` includes the stable Git error code, `blog_publish` reflects successful handoff, and the response states remote Git publication did not complete

### Requirement: Git publication non-goals for US-002 deferral

This capability MUST NOT verify that GitHub Pages deployed or that `source_public_url` is HTTP-reachable.

This capability MUST NOT implement remote divergence detection, automatic pull/rebase, or conflict resolution.

This capability MUST NOT implement cross-campaign duplicate commit prevention beyond the US-001 idempotency requirement in this spec.

#### Scenario: No live URL probe

- **WHEN** Git publication push succeeds
- **THEN** the worker does not perform HTTP requests to `source_public_url` or GitHub Pages status endpoints

#### Scenario: Non-fast-forward push fails closed

- **WHEN** `git push` is rejected because the remote branch advanced after successful handoff
- **THEN** the worker returns overall `status: partial` with `blog_git_publication_push_failed` and does not attempt fetch/pull/rebase (deferred to US-002)

### Requirement: Git publication automated tests

The repository SHALL include automated tests for Git publication using injectable Git subprocess fakes or temporary repositories.

Tests MUST cover: disabled guard, environment-only enablement does not publish, controlled staging scope, successful commit and push, push failure after handoff returns partial, missing artifacts, `already_published` idempotency, unrelated dirty files untouched, and Flow B rejection.

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
