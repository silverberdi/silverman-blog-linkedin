## 1. Spec and artifact alignment (Option A)

- [x] 1.1 Update canonical `openspec/specs/ubuntu-server-worker-deployment/spec.md` isolation requirement to allow external `local-ai-stack_backend` only, while forbidding defining/depends_on shared-stack services and forbidding deploy lifecycle mutation of that stack.
- [x] 1.2 Replace `test_compose_does_not_reference_local_ai_stack` with assertions matching Option A (external network allowed; no shared service defs/depends_on; deploy script still compose-isolated).
- [x] 1.3 Update operator deployment docs that still imply a hard ban on any `local-ai-stack` compose reference, pointing to alerts enablement rationale.

## 2. US-035 concurrent patch flake

- [x] 2.1 Move `unittest.mock.patch` for `publish_blog_post` / `ComfyUIHttpClient` outside the two concurrent threads in `test_concurrent_retrigger_immediately_after_restart_loses_to_non_stale_claim`.
- [x] 2.2 Confirm US-035 then markdown-only connector tests pass in that order.

## 3. Verification

- [x] 3.1 Run deployment artifact tests, US-035, markdown-only module, and a broader/full pytest pass without the prior 7 markdown connector failures.
- [x] 3.2 Run `git diff --check` on touched paths.
