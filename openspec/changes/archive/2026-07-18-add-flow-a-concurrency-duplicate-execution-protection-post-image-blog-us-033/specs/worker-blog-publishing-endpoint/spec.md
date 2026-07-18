## ADDED Requirements

### Requirement: Concurrent and repeated publish honor already_published without duplicate artifacts

Under concurrent or repeated `publish_blog_post` calls for the same Flow A publish identity, the worker MUST continue to evaluate the `already_published` short-circuit before validation, image remediation, handoff, and public-repo mutating apply.

When the short-circuit applies, the worker MUST return `status=completed` with `blog_publish.status=already_published` without rewriting public `_posts/` or `assets/images/` targets and without clearing confirmed publish identity evidence.

When two overlapping first-time publish attempts race for the same unpublished identity, at most one attempt MAY successfully apply public artifacts; the other MUST end as `already_published` after the winner’s evidence is durable, or fail closed without overwrite if identity remains unproven (`blog_publish_target_exists` or equivalent).

This US-033 requirement covers worker checkout/handoff publish safety. It MUST NOT claim remote Git push or live-site confirmation as part of US-033 completion.

#### Scenario: Repeated publish after success is already_published

- **WHEN** `publish_blog_post` is called again for a campaign that already satisfies matching blog publish identity evidence
- **THEN** the response is completed with `blog_publish.status=already_published` and no public files are rewritten

#### Scenario: Concurrent loser does not create a second post file set

- **WHEN** two overlapping `publish_blog_post` calls race for the same previously unpublished Flow A identity and one apply succeeds
- **THEN** the other call does not leave a second distinct `_posts/` + image artifact set for that identity and does not overwrite the winner’s files

#### Scenario: Unproven existing targets still fail closed under concurrency

- **WHEN** public targets exist without matching stored blog publish idempotency proof during a concurrent or repeated publish attempt
- **THEN** the worker fails with `blog_publish_target_exists` (or equivalent) and does not overwrite
