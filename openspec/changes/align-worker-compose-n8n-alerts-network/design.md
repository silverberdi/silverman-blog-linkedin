## Context

Production worker compose (`deploy/server/silverman-worker.compose.yaml`) attaches to external network `local-ai-stack_backend` so alert emission can reach `http://n8n:5678/webhook/...` without the public gateway `X-Avatares-Api-Key` gate. Canonical isolation wording and `test_compose_does_not_reference_local_ai_stack` still ban any `local-ai-stack` string. US-035 restart retrigger test patches `publish_blog_post` / `ComfyUIHttpClient` inside two concurrent threads; mock patch/unpatch races leave MagicMocks on those module attributes.

## Goals / Non-Goals

**Goals:**

- Legalize Option A: external network join only, without putting the worker inside the local-ai-stack compose project or stopping shared services.
- Fix concurrent mock leakage in US-035.
- Keep deploy scripts from operating on local-ai-stack compose files.

**Non-Goals:**

- Removing the network (Option B).
- Changing alert webhook payload contracts.
- BL-015 console work.

## Decisions

### D1 — Isolation means project/lifecycle isolation, not zero DNS adjacency

**Decision:** Isolation SHALL mean: worker uses its own compose project/file; deploy MUST NOT stop/modify shared-stack containers; worker MAY attach to an **external** network named `local-ai-stack_backend` for n8n DNS only.

**Rejected:** Hard ban on the substring `local-ai-stack` in compose YAML.

### D2 — Test asserts the allowed shape

**Decision:** Replace the absolute ban with assertions that:
- compose may reference `local-ai-stack_backend` only as `external: true`
- compose does not include other local-ai-stack service definitions or `depends_on` shared services
- deploy script docker compose invocations still target only `silverman-worker.compose.yaml`

### D3 — Patch once outside threads

**Decision:** In US-035 concurrent retrigger test, apply `patch` once in the parent thread wrapping both workers, so start/stop of patches is single-threaded.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Spec readers confuse network join with stack ownership | Explicit scenarios: deploy does not modify shared stack; network is external-only |
| Other concurrent patches elsewhere | Scope fix to known failing US-035 pattern; full suite verification |

## Migration Plan

1. Approve → apply spec/test/doc + US-035 test fix.
2. Run deployment artifact tests + US-035 + markdown-only + full suite.
3. Sync/archive OpenSpec change.

## Open Questions

None — Option A selected by operator.
