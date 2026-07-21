# US-067 / US-068 warning and test quality baseline — evidence 2026-07-21

**BANNER — no secrets in this file.** Counts, test node ids, and warning message classes only.

**Normative procedure:** [warning-and-test-quality-baseline.md](warning-and-test-quality-baseline.md).

| Field | Value |
|-------|-------|
| Baseline date (UTC) | `2026-07-21` |
| Measured against git | `6bb4a90` (pre-BL-028 impl commit) |
| Host | Mac develop (repo `.venv`, Python 3.14) |
| Overall warning baseline | **1 inherited pytest warning**; Vitest green |
| Story accepted | operator-accepted 2026-07-21 (US-067 + US-068); **BL-028 closed** |

**Not performed:** GitHub Actions / CI (BL-029); LinkedIn enablement mutation; broad dependency upgrades to clear Starlette deprecation; fixing all known failing pytest nodes in this change.

---

## pytest (primary)

**Command:** `.venv/bin/python -m pytest -q -W default` (unrestricted runner; sandbox re-runs produce extra `PytestWarning` rm_rf noise — do not treat those as baseline).

| Metric | Value |
|--------|-------|
| Passed | 1404 |
| Failed | 11 |
| Warnings | **1** |

### Inherited warnings

| # | Category | Location / class | Notes |
|---|----------|------------------|-------|
| W1 | `StarletteDeprecationWarning` | `fastapi/testclient.py` → Starlette TestClient: using `httpx` deprecated; install `httpx2` | Third-party; **inherited**. Fix later via FastAPI/Starlette/`httpx2` upgrade — not filtered in this change. |

### Known suite failures (quality debt — not warnings)

Recorded so operators do not confuse red tests with the warning baseline:

| Test node id | Theme (short) |
|--------------|----------------|
| `tests/test_editorial_canon.py::test_flow_a_vs_flow_b_encodes_strategy_and_optional_supervision` | Missing expected Flow B / Flow A phrase in canon artifact |
| `tests/test_flow_a_markdown_only_image_generation.py::test_connector_markdown_only_happy_path_end_to_end` | Connector / claim / handoff expectations |
| `tests/test_flow_a_markdown_only_image_generation.py::test_connector_comfyui_transient_failure_releases_claim_once` | Claim release |
| `tests/test_flow_a_markdown_only_image_generation.py::test_connector_handoff_failure_releases_claim_once` | Claim release |
| `tests/test_flow_a_markdown_only_image_generation.py::test_connector_deterministic_validation_error_move_no_release` | Validation move / release |
| `tests/test_flow_a_markdown_only_image_generation.py::test_connector_deterministic_validation_error_move_failure_releases_once` | Validation move / release |
| `tests/test_flow_a_markdown_only_image_generation.py::test_connector_local_editorial_image_repair_failure_releases_once` | Repair / release |
| `tests/test_flow_a_markdown_only_image_generation.py::test_connector_hash_reconciliation_failure_releases_once` | Hash reconcile |
| `tests/test_linkedin_variant_pending_supervision.py::test_console_action_contract_wiring_in_static_html` | Stale dry-run copy string in static HTML bundle |
| `tests/test_server_deployment_artifacts.py::test_compose_editorial_volume_mount` | Compose editorial host path expectation stale vs current compose |
| `tests/test_server_deployment_artifacts.py::test_compose_allows_external_n8n_network_only` | False positive on `postgres:` substring in commented calendar URL example |

**Remediation:** deferred to **BL-033 / US-090** (update tests/docs or restore behavior **and** clear W1) — out of BL-028 warning-baseline scope. Prefer completing US-090 before relying on BL-029 as a hard gate.

### Cheap warning remediation attempted

- No project-code root cause for W1; left **inherited** without a broad `filterwarnings` suppression.

---

## Vitest (secondary)

**Command:** `cd frontend/linkedin-variant-supervision-console && npm test`

| Metric | Value |
|--------|-------|
| Test files | 25 passed |
| Tests | 173 passed |
| Failures | 0 |

Console may print React `act(...)` guidance during runs; treat as tooling noise unless Vitest reports a failed assertion. Not counted as pytest inherited warnings.

---

## Operator attestation

| Statement | Yes / No |
|-----------|----------|
| Warning inventory contains no secret values | Yes |
| Inherited vs new rule documented in SoT | Yes |
| BL-029 CI not established by this change | Yes |
| Known 11 pytest failures recorded as debt, not as “warnings” | Yes |

---

## Product note

US-067 + US-068 Story accepted; **BL-028 closed 2026-07-21**. Standing rule: **zero new warnings attributable to a change** vs this baseline (W1 inherited).
