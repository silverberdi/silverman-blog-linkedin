## Why

BL-011 operational alerts emit to n8n over the internal compose DNS name `n8n`, which requires the worker to join the external Docker network `local-ai-stack_backend`. The canonical ubuntu-server-worker-deployment isolation requirement and its artifact test still forbid any `local-ai-stack` reference, so the live compose and the accepted alerts enablement disagree with the written contract. Separately, concurrent `unittest.mock.patch` usage inside two threads in a US-035 test can leave `MagicMock` objects installed on shared module attributes and contaminate later suites (including Flow A markdown-only connector tests).

## What Changes

- Update `ubuntu-server-worker-deployment` so isolation still forbids modifying/stopping shared-stack services, but **allows** an optional external network join to `local-ai-stack_backend` solely for n8n webhook DNS (Option A).
- Align `tests/test_server_deployment_artifacts.py` and operator deployment docs with that contract.
- Fix US-035 concurrent-patch leakage so full-suite order no longer flakes markdown-only connector tests.
- Do not change worker alert emit code paths, n8n workflows, or remove the existing compose network attachment.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `ubuntu-server-worker-deployment`: Clarify isolation vs permitted external network attachment for n8n alerts webhook reachability.

## Impact

- Specs/tests/docs for server compose isolation become consistent with the BL-011-enabled production topology.
- Full pytest suite reliability improves by removing cross-test mock pollution from US-035.
- No FastAPI route changes; no n8n Execute Command; no secrets in docs.
