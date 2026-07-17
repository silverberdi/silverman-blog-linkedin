## 1. US-029 candidate derivation

- [x] 1.1 Extend `OperationalAlert` (or equivalent) with optional `calendar_item_id` and ensure payload serialization omits unset optional fields
- [x] 1.2 Derive `partial_calendar_execution` alerts from operational-status `delayed_calendar_items` (one per `item_id`, severity `warning`, reason `calendar_item_past_due`, no calendar title in payload)
- [x] 1.3 Derive `linkedin_token_or_publication_failure` alerts from `linkedin` dependency-bucket attributions and campaign LinkedIn `failure_codes` (merge codes per artifact, `dependency=linkedin`, severity `error`; exclude preview-only checkout codes)
- [x] 1.4 Derive `stale_campaign` alerts from campaigns with `stale=true` (one per `campaign_id`, severity `warning`)
- [x] 1.5 Update summary counts and alert-type constants to include all six types (US-028 + US-029) while preserving existing US-028 derivation behavior and deterministic ordering

## 2. Emission and contract reuse

- [x] 2.1 Confirm evaluate/emit HTTP contract, auth, fail-closed env flags, webhook adapter, and `metadata/operational-alerts/emissions.json` ledger remain unchanged except for accepting new fingerprints
- [x] 2.2 Ensure evaluate-only still performs no ledger write and no campaign/run/calendar/editorial lifecycle mutation; emit still writes only the alerts ledger after HTTP 2xx

## 3. Tests

- [x] 3.1 Add focused tests for each US-029 alert type from controlled fixtures (delayed calendar item, linkedin dependency / progress failure codes, stale campaign)
- [x] 3.2 Add tests for LinkedIn preview-checkout exclusion from `linkedin_token_or_publication_failure`, six-type `summary.counts`, severity assignments, and safe omission of calendar titles/secrets
- [x] 3.3 Add coexistence regression: US-028 types still produced; evaluate-only zero lifecycle mutation; fail-closed emit and idempotent ledger behavior for new fingerprints
- [x] 3.4 Assert US-030 alert types remain absent; run targeted operational-alerts tests plus operational-status regression; resolve warnings attributable to this change

## 4. Documentation and progress

- [x] 4.1 Update `docs/operations/flow-a-operational-alerts.md` for the three US-029 alert types, severities, derivation sources, and unchanged evaluate/emit/ledger contract
- [x] 4.2 Update `docs/CURRENT-STATE.md` to the demonstrated US-029 implementation level only; do not claim US-029 acceptance, US-028 re-acceptance, or BL-011 closure
- [x] 4.3 Update `docs/product/user-stories.md` US-029 status and `docs/product/progress-checklist.md` only for criteria actually demonstrated; leave US-030 and BL-011 closure unchanged

## 5. Business validation

- [x] 5.1 Demonstrate against controlled fixtures that an authenticated operator/n8n client can evaluate alerts for partial calendar execution, LinkedIn token/publication failure, and stale campaigns with understandable secret-safe payloads
- [x] 5.2 Confirm failures/blocked/attention states are clearly communicated (including warning vs error severity) and that evaluate-only does not mutate existing completed lifecycle work
- [x] 5.3 Confirm out-of-scope items remain absent (US-030 types, BL-015 UI, Slack/email SDK, deploy/live mutation, US-028 re-acceptance, BL-011 closure) and record remaining acceptance gaps explicitly
