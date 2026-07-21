## MODIFIED Requirements

### Requirement: LinkedIn and blog frequency planning assumptions

Normative docs SHALL reaffirm the LinkedIn frequency planning assumption as filling toward approximately **two** LinkedIn publications per operator-local day via the interim **US-040K** density cap, unless a later approved OpenSpec change explicitly supersedes that number. Normative docs SHALL also reaffirm blog frequency at **strategy level**: blogs are paced to support LinkedIn filling (Flow A packaging of ready blogs; Flow B weekly gap fills bounded by `max_drafts_per_weekly_run`, default 2) and this story MUST NOT require automating a blog cadence engine. Normative docs SHALL point preferred LinkedIn publishing windows / clock guidance and shift-forward reschedule rules to the **US-052** operator policy at `docs/operations/linkedin-publishing-windows-and-shift-forward-policy.md` (capability `linkedin-publishing-windows-and-shift-forward-policy`) and MUST NOT leave those rules documented as permanently deferred once that policy exists.

#### Scenario: Frequency assumptions documented without automation

- **WHEN** an operator reads the frequency section of the LinkedIn cadence spacing policy
- **THEN** LinkedIn planning ≈ fill toward ~2 publications per operator-local day via US-040K is stated
- **AND** blog frequency is stated as strategy-level (supporting LinkedIn fill; no blog cadence automation required by US-051)
- **AND** the policy does not claim US-051 supersedes the US-040K max-2 number
- **AND** preferred publishing windows / shift-forward rules are pointed to the US-052 policy (not left as permanently deferred)
