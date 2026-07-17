# US-025 — LinkedIn preview fallback decision: keep-contracts-boring (2026-07-17)

Evidence records per the template in [linkedin-preview-fallback-policy.md](linkedin-preview-fallback-policy.md). Two decisions were made for the same triggering US-024 outcome: the post-publish default (accept and record) and the explicit escalation choice (format change deferred).

## Decision 1 — accept and record (post-publish default)

- **Campaign id:** `flow-a-2026-07-15-keep-contracts-boring`
- **Affected variant(s) and `publish_state` at decision time:** `executive-recruiter` — `published` (urn `urn:li:share:7483953784612786177`, `published_at` `2026-07-17T18:40:27Z`); siblings `engineering-leadership` / `technical-architect` / `short-provocative` — `pending` (not affected by this decision).
- **Referenced US-024 evidence record:** `preview_not_rendered_post_format`, UTC `2026-07-17T18:41Z` — [us-024 confirmation](us-024-preview-confirmation-keep-contracts-boring-2026-07-17.md).
- **Referenced US-023 verification run:** real run `validated_at_utc` `2026-07-17T18:11:32Z`, overall `passed` — [us-023 validation](us-023-linkedin-preview-input-validation-2026-07-17.md).
- **Chosen action and classification:** **accept and record** — supported (operator decision, no additional approval). The published post remains; the blog URL in commentary works; the missing article card is a v1 text-post format behavior, not an input defect.
- **Worker endpoint calls made:** none (dry-run or real). Accept-and-record makes no calls by definition.
- **Resulting variant `publish_state`:** `executive-recruiter` remains `published`; all publication evidence untouched.
- **Safeguard verification:** campaign document sha256 `39adf644d3574c624464fa04325b2e4003fe59c77669ce1d60eea5ba68273015` unchanged by this decision (no calls made); `publication_attempt_count` stays 1, `manual_retries_used` stays 0 — zero retry-budget consumption; no `recovery_confirmation` used (variant is not `failed`); US-020 cadence remains anchored to stored `published_at`.
- **Outcome label:** `fallback_accept_rendering`
- **Operator:** Silverio Bernal — **decision at (UTC):** 2026-07-17T18:42:00Z

## Decision 2 — format-change escalation deferred

- **Campaign id:** `flow-a-2026-07-15-keep-contracts-boring` (same trigger as Decision 1).
- **Referenced US-024 / US-023 records:** same as Decision 1.
- **Chosen action and classification:** escalation of the post-format finding to a **deferred future-change candidate** — supported (documentation decision; no endpoint action). Per policy, an explicit article post format (for example `content.article`) requires: at least one operationally recorded triggering US-024 evidence record (now satisfied by this campaign's record), verification against current official LinkedIn API documentation, and its own OpenSpec change with unchanged guard, dry-run, idempotency, retry-budget, and evidence contracts. No change to current publication behavior.
- **Worker endpoint calls made:** none.
- **Resulting variant `publish_state`:** unchanged (`published`).
- **Outcome label:** `fallback_format_change_deferred`
- **Operator:** Silverio Bernal — **decision at (UTC):** 2026-07-17T18:42:00Z

## Scope note

Campaign metadata was not edited to record these outcomes (recorded here only, per policy). No LinkedIn API calls, no UI actions, no automatic execution. The same-day `domain-first-is-not-anti-infrastructure` post (no card, `article_preview` skipped) is corroborating context outside this record's scope.
