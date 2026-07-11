# blog-live-site-confirmation

## Purpose

Guarded HTTP confirmation that a publish-confirmed `source_public_url` is reachable on the public site after successful Git publication. Complements `github-pages-git-publication` (commit and push) by optionally probing the live URL when explicitly enabled and opted in per request.

## Requirements

### Requirement: Guarded live-site confirmation enablement

The worker SHALL support guarded HTTP confirmation that `source_public_url` is reachable after successful Git publication.

Live-site confirmation MUST be disabled by default and MUST require explicit enablement via environment variable `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED=true`.

Live-site confirmation MUST also require per-request opt-in `live_site_confirmation: true`. Environment enablement alone MUST NOT trigger HTTP probes.

When live-site confirmation is disabled, any request that opts in MUST fail closed with stable error code `blog_live_site_confirmation_disabled` and MUST NOT perform outbound HTTP requests.

Live-site confirmation MUST require successful Git publication evidence (`blog_git_publication.status` `pushed` or `already_published`) for the same campaign in the same publish invocation or from prior campaign metadata. When Git publication was not requested or did not succeed, live-site confirmation MUST fail with `blog_live_site_confirmation_git_required`.

#### Scenario: Disabled live confirmation rejects opt-in request

- **WHEN** a client requests live-site confirmation and `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED` is unset or false
- **THEN** the worker returns `blog_live_site_confirmation_disabled` and performs no HTTP probes

#### Scenario: Enabled without request opt-in does not probe

- **WHEN** `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED=true` and a client calls publish without `live_site_confirmation: true`
- **THEN** the worker performs no HTTP probes to `source_public_url`

#### Scenario: Live confirmation without Git evidence fails

- **WHEN** a client requests `live_site_confirmation: true` but Git publication did not succeed in the same invocation and campaign metadata lacks prior `blog_git_publication.status` `pushed` or `already_published`
- **THEN** the worker returns `blog_live_site_confirmation_git_required` and performs no HTTP probes

### Requirement: HTTP probe of source_public_url

When live-site confirmation runs, the worker MUST perform HTTP `GET` requests to the campaign's publish-confirmed `source_public_url`.

The probe MUST use only URLs computed or stored by the worker from successful blog publish (`source_public_url` on campaign metadata). The probe MUST NOT accept arbitrary operator-supplied URLs.

The probe host MUST match the configured site base URL host (default `silverman.pro`).

The worker MUST follow redirects up to 5 hops and record the final URL.

Probe timeout per attempt MUST be configurable via `SILVERMAN_BLOG_LIVE_SITE_PROBE_TIMEOUT_SECONDS` with default 10 seconds.

The worker MUST retry failed probes up to `SILVERMAN_BLOG_LIVE_SITE_PROBE_MAX_ATTEMPTS` (default 5) with delay `SILVERMAN_BLOG_LIVE_SITE_PROBE_RETRY_DELAY_SECONDS` (default 2) between attempts.

Probe success MUST require HTTP status 200 and response body containing the campaign `public_slug` as a stable content marker.

Probe failures MUST return stable error code `blog_live_site_confirmation_unreachable`.

#### Scenario: Successful probe after push

- **WHEN** Git publication succeeded, live confirmation is enabled and opted in, and `GET source_public_url` returns HTTP 200 with body containing `public_slug`
- **THEN** `blog_live_site_publication.status` is `confirmed` with `http_status` 200 and `final_url` recorded

#### Scenario: Probe retries on propagation delay

- **WHEN** the first probe attempt fails with timeout or non-200 and a later attempt within the configured retry budget returns HTTP 200 with the slug marker
- **THEN** live confirmation succeeds and records the successful attempt count

#### Scenario: Probe fails after retries exhausted

- **WHEN** all probe attempts fail or return non-200
- **THEN** `blog_live_site_publication.status` is `failed` with `blog_live_site_confirmation_unreachable`

#### Scenario: Foreign host blocked

- **WHEN** `source_public_url` host does not match the configured site base URL host
- **THEN** live confirmation fails with `blog_live_site_confirmation_invalid_url` without network access

### Requirement: Live-site confirmation idempotency

When campaign metadata records successful live confirmation (`blog_live_site_publication.status` `confirmed`) for the same `source_public_url` and `blog_git_publication.commit_sha`, a repeat live confirmation request MUST:

- return `blog_live_site_publication.status` `already_confirmed`;
- NOT perform unnecessary HTTP probes;
- NOT overwrite prior successful confirmation evidence with weaker state.

#### Scenario: Repeat confirmation after prior success

- **WHEN** live confirmation already succeeded for the campaign URL and commit SHA and the client requests live confirmation again
- **THEN** the worker returns `already_confirmed` without new HTTP requests

### Requirement: Campaign metadata blog_live_site_publication

On live-site confirmation attempt, the worker MUST persist `blog_live_site_publication` on the campaign with at minimum:

- `status`: one of `pending`, `confirmed`, `already_confirmed`, `failed`, `skipped`
- `source_public_url` probed
- `http_status` when known
- `final_url` when known
- `attempts` count
- `confirmed_at` as UTC ISO8601 when applicable
- `error_code` when failed

Campaign metadata MUST NOT store full response bodies or secrets.

#### Scenario: Successful confirmation metadata

- **WHEN** live-site confirmation succeeds
- **THEN** campaign metadata records `blog_live_site_publication.status` `confirmed`, `source_public_url`, `http_status`, `final_url`, and `confirmed_at`

#### Scenario: Failed confirmation metadata after successful push

- **WHEN** Git push succeeded but live confirmation fails
- **THEN** campaign metadata records `blog_live_site_publication.status` `failed` with `blog_live_site_confirmation_unreachable` while `blog_git_publication` push evidence remains intact

### Requirement: Live-site confirmation result shape

Live-site confirmation results MUST be included in publish HTTP responses when live confirmation is requested, with at minimum:

- `blog_live_site_publication.status`
- `blog_live_site_publication.source_public_url`
- `blog_live_site_publication.http_status` when known
- `blog_live_site_publication.final_url` when known
- `blog_live_site_publication.attempts` when known
- `errors[]` with stable codes on failure

When Git push succeeded but live confirmation fails, overall response `status` MUST be `partial`, `blog_git_publication` MUST preserve push evidence, and the response MUST state that remote Git publication completed but live-site confirmation did not.

#### Scenario: Publish response includes confirmation on success

- **WHEN** publish, Git publication, and live confirmation all succeed
- **THEN** the HTTP response includes overall `status: completed` and `blog_live_site_publication.status` `confirmed`

#### Scenario: Push success with probe failure is partial

- **WHEN** Git push succeeded, live confirmation was requested, and all probe attempts fail
- **THEN** response `status` is `partial`, `blog_git_publication.status` remains `pushed`, and `errors[]` includes `blog_live_site_confirmation_unreachable`

### Requirement: Live-site confirmation automated tests

The repository SHALL include automated tests for live-site confirmation using injectable HTTP client fakes.

Tests MUST cover: disabled guard, environment-only enablement does not probe, git-required guard, successful confirmation, retry then success, exhausted retries failure, idempotent `already_confirmed`, invalid host rejection, and partial response when push succeeded but probe failed.

Tests MUST NOT require real network access.

#### Scenario: Disabled guard test

- **WHEN** tests run live confirmation with enablement flag false
- **THEN** tests verify no HTTP client calls occur and `blog_live_site_confirmation_disabled` is returned

#### Scenario: Injectable HTTP fake test

- **WHEN** tests simulate HTTP 200 with slug in body on the second attempt
- **THEN** tests verify `confirmed` status and `attempts` equals 2
