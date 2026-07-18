## MODIFIED Requirements

### Requirement: Last-valid-stage derivation uses existing lifecycle evidence without new states

Incomplete Flow A campaign recovery SHALL derive an operator-visible `last_valid_stage` from existing campaign pipeline `state`, `state_history`, and durable stage evidence defined by this lifecycle capability and related Flow A stage specs.

That derivation MUST use existing durable milestone state names only (`ready`, `validated`, `blog_published`, `derivatives_generated`, `distribution_scheduled`, `flow_a_complete`) and MUST NOT introduce additional lifecycle `state` enum values.

`state_history` remains append-only evidence of transitions already performed by lifecycle helpers. Incomplete-campaign recovery MUST NOT rewrite historical `state_history` entries to manufacture a last-valid-stage, and MUST NOT bypass `invalid_state_transition` enforcement when a resume path performs a real state transition through existing helpers.

Durable recovery attempt ledger entries under `flow_a_recovery.attempts` are distinct from `state_history`. Cancel and history writes MUST NOT append lifecycle transitions solely to invent milestones, MUST NOT treat ledger entries as proof of durable stage success, and MUST NOT change campaign `state` solely because recovery was cancelled.

Campaign state `flow_a_complete` continues to mean campaign lifecycle metadata completion only; derivation language MUST NOT equate it with site-live publication or LinkedIn API publication.

#### Scenario: Last-valid-stage uses existing durable state names

- **WHEN** incomplete-campaign recovery derives `last_valid_stage` for a Flow A campaign
- **THEN** the derived value is one of the existing durable milestone names and no new lifecycle state value is persisted as `state`

#### Scenario: Recovery does not rewrite state_history to invent milestones

- **WHEN** incomplete-campaign recovery inspects a campaign whose `state_history` lacks a durable milestone that stage evidence also does not confirm
- **THEN** recovery does not append or alter history entries solely to claim that milestone and instead reports the highest confirmed milestone or an ambiguity block

#### Scenario: Cancel and attempt history do not invent lifecycle success

- **WHEN** incomplete-campaign recovery cancel or attempt-history persistence runs for a campaign that is not `flow_a_complete`
- **THEN** campaign `state` is not rewritten to `flow_a_complete` and no `state_history` entry is appended solely to claim lifecycle completion
