## ADDED Requirements

### Requirement: Live-site confirmation opt-in on publish service entry point

The publish service entry point MUST accept optional `live_site_confirmation: bool = False` (default false).

When `live_site_confirmation: true` and enabled per canonical spec `blog-live-site-confirmation`, the entry point MUST run HTTP live-site confirmation after successful Git publication evidence exists in the same invocation or campaign metadata.

Overall publish `status` MUST be `partial` when Git push succeeded but live-site confirmation failed after `live_site_confirmation` was requested.

#### Scenario: Live confirmation opt-in after successful push

- **WHEN** `publish_blog_post` is called with `git_publication: true`, `live_site_confirmation: true`, both features enabled, handoff and push succeed
- **THEN** the function invokes live-site confirmation and includes `blog_live_site_publication` in the result

#### Scenario: Default publish without live confirmation

- **WHEN** `publish_blog_post` is called without `live_site_confirmation` opt-in
- **THEN** no HTTP probes run and the result omits successful `blog_live_site_publication.confirmed` state

#### Scenario: Push success with live confirmation failure is partial

- **WHEN** `publish_blog_post` is called with `live_site_confirmation: true`, push succeeds, and all probe attempts fail
- **THEN** the result has `status: partial`, `blog_git_publication` preserves push evidence, and `blog_live_site_publication.status` is `failed`

### Requirement: HTTP live-site confirmation opt-in on POST /publish-blog-post

`POST /publish-blog-post` MUST accept optional request field `live_site_confirmation` (boolean, default `false`).

When `live_site_confirmation` is `true` and `SILVERMAN_BLOG_LIVE_SITE_CONFIRMATION_ENABLED=true`, the worker MUST attempt live-site confirmation per `blog-live-site-confirmation` after successful Git publication in the same request.

When `live_site_confirmation` is `false` or omitted, publish behavior MUST NOT perform HTTP probes regardless of environment enablement.

#### Scenario: Opt-in triggers live confirmation

- **WHEN** a client sends `POST /publish-blog-post` with `git_publication: true`, `live_site_confirmation: true`, valid API key, and both features enabled
- **THEN** the response includes `blog_live_site_publication` after successful push and probe

#### Scenario: Omitted flag preserves no-probe behavior

- **WHEN** a client sends `POST /publish-blog-post` without `live_site_confirmation` even when live confirmation is enabled in the environment
- **THEN** no HTTP probes run

### Requirement: Extended blog publish error codes for live-site confirmation

The publish flow MUST surface stable live-site confirmation error codes from `blog-live-site-confirmation` in `errors[]` when live confirmation is requested, including at minimum:

- `blog_live_site_confirmation_disabled`
- `blog_live_site_confirmation_git_required`
- `blog_live_site_confirmation_invalid_url`
- `blog_live_site_confirmation_unreachable`

When push succeeded but live confirmation fails, `errors[]` MUST include actionable recovery guidance without secrets.

#### Scenario: Disabled live confirmation error code

- **WHEN** `live_site_confirmation` is true but enablement flag is false
- **THEN** `errors[]` includes `blog_live_site_confirmation_disabled`

#### Scenario: Probe failure after push uses partial status

- **WHEN** `live_site_confirmation` is true, push succeeds, and all probes fail
- **THEN** response `status` is `partial`, `errors[]` includes `blog_live_site_confirmation_unreachable`, and `blog_git_publication` reflects successful push

### Requirement: Publish HTTP tests for live-site confirmation

Automated tests MUST cover `POST /publish-blog-post` with `live_site_confirmation` opt-in, environment-only enablement without opt-in, partial response when push succeeds and probe fails, and git-required guard when push did not run.

#### Scenario: HTTP live confirmation opt-in test

- **WHEN** tests call `POST /publish-blog-post` with `git_publication: true`, `live_site_confirmation: true`, and HTTP client fake returns 200 with slug marker
- **THEN** tests verify `blog_live_site_publication.status` `confirmed` in the response

#### Scenario: HTTP partial probe failure test

- **WHEN** tests call `POST /publish-blog-post` with live confirmation opt-in, push succeeds, and HTTP client fake always fails
- **THEN** tests verify response `status` is `partial` and push evidence is preserved
