# US-087 Visual DoD — capture plan

**Change:** `show-linkedin-console-cadence-conflict-warning-us-087`  
**Status:** Scheduled / pending operator — **not captured in apply environment** (same pattern as prior console stories). Vitest covers structural UX; Story accepted still requires desktop + mobile evidence unless the operator explicitly waives the formal pack.

## Required scenes (desktop + mobile)

1. **Week:** conflicted Scheduled chip with red `cadence-conflict-indicator` + primary **Scheduled** label still visible.
2. **Month:** same for a conflicted LinkedIn item (dense month if practical).
3. **EventModal:** open conflicted item — plain cadence-conflict explanation + earliest feasible / Postpone next step.
4. **Negative:** cadence-feasible Scheduled item — **no** cadence-conflict indicator.
5. **Distinctness:** Failed chip and density-full day cue remain visually different from the cadence-conflict warning.
6. **Mobile (~375):** EventModal sheet readable for conflict explanation.

## After deploy (task 5.2)

Operator walkthrough on live console that US-087 AC are visible. Do **not** mark Story accepted or close BL-021 from this apply alone.
