## ADDED Requirements

### Requirement: Incomplete-campaign recovery reuses operational recovery vocabulary and re-run rules

Incomplete Flow A campaign recovery (capability `flow-a-incomplete-campaign-recovery`) MUST reuse this capability’s canonical `source_file_status.recovery_classification` vocabulary and existing claim, stale, reclaim, requeue, and idempotent re-run rules rather than inventing a parallel recovery ontology.

When incomplete-campaign recovery inspect, resume, or repair sets or clears `recovery_classification`, the value MUST remain one of: `no_action`, `retryable`, `repair_required`, `requeue_required`, `manual_intervention_required`.

Resume of an incomplete campaign MUST follow the existing idempotent re-run rules for `queued` / `stale` / `processing` / `processed` / `error` sources: non-stale `processing` claims remain rejected; `error` requires explicit requeue before execution; partial side-effect campaigns resume from persisted pipeline evidence without appearing as a new campaign.

This requirement MUST NOT redefine LinkedIn API publication recovery classification or re-queue confirmation semantics.

#### Scenario: Recovery classification remains canonical during incomplete-campaign recovery

- **WHEN** incomplete-campaign recovery resume or repair updates `recovery_classification`
- **THEN** the persisted value is one of the five canonical enum values and no undocumented alias is written

#### Scenario: Non-stale processing claim still blocks duplicate execution through recovery resume

- **WHEN** incomplete-campaign recovery resume is requested for a source with `execution_state=processing` that is not stale
- **THEN** resume is rejected consistently with existing duplicate-claim protection and no second execution claim is created

#### Scenario: Error location still requires explicit requeue before recovery resume

- **WHEN** incomplete-campaign recovery resume is requested while `source_file_status.location=error`
- **THEN** resume does not implicitly requeue and reports `requeue_required` using the canonical classification vocabulary
