import { describe, expect, it, vi } from "vitest";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import {
  SUPERVISION_ERROR_MESSAGES,
  explainErrorCodes,
} from "../api/errors";

describe("API client error mapping", () => {
  it("maps 401 to Unauthorized (401) and clears auth", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("bad-key");
    const fetchImpl = vi.fn(
      async () => new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 }),
    );
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);

    await expect(client.getPendingSupervision()).rejects.toMatchObject({
      kind: "unauthorized",
      message: expect.stringContaining("Unauthorized (401)"),
      httpStatus: 401,
    });
    expect(auth.hasCredential()).toBe(false);
  });

  it("maps 403 to Forbidden and keeps credential", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("key");
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 }),
    );
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);

    await expect(client.getPendingSupervision()).rejects.toMatchObject({
      kind: "forbidden",
      message: expect.stringContaining("Forbidden (403)"),
      httpStatus: 403,
    });
    expect(auth.hasCredential()).toBe(true);
  });

  it("maps 5xx to service-unavailable style http error", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("key");
    const fetchImpl = vi.fn(
      async () => new Response("unavailable", { status: 503 }),
    );
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);

    await expect(client.getPendingSupervision()).rejects.toMatchObject({
      kind: "http",
      httpStatus: 503,
      message: expect.stringContaining("Service unavailable"),
    });
  });

  it("maps 422 to validation ApiError", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("key");
    const fetchImpl = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            detail: [{ loc: ["body", "draft_content"], msg: "Field required", type: "missing" }],
          }),
          { status: 422 },
        ),
    );
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);

    await expect(
      client.correctVariant({
        campaign_id: "c",
        variant: "v",
        draft_content: "",
      }),
    ).rejects.toMatchObject({
      kind: "validation",
      httpStatus: 422,
      message: expect.stringContaining("422"),
    });
  });

  it("maps known US-017 business failure codes from HTTP 200 status=failed", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("key");
    const fetchImpl = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            status: "failed",
            campaign_id: "c",
            variant: "v",
            state: null,
            publish_state: "published",
            dry_run: true,
            phase: null,
            errors: ["linkedin_publish_cancel_not_allowed"],
            warnings: [],
            metadata_written: false,
          }),
          { status: 200 },
        ),
    );
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);

    await expect(
      client.cancelVariant({
        campaign_id: "c",
        variant: "v",
        dry_run: true,
      }),
    ).rejects.toMatchObject({
      kind: "business",
      codes: ["linkedin_publish_cancel_not_allowed"],
      message: expect.stringContaining("linkedin_publish_cancel_not_allowed"),
    });
  });

  it("explains known supervision codes for operator display", () => {
    expect(
      explainErrorCodes(["linkedin_supervision_variant_not_pending"]),
    ).toContain(SUPERVISION_ERROR_MESSAGES.linkedin_supervision_variant_not_pending);
    expect(
      explainErrorCodes(["linkedin_supervision_defer_time_invalid"]),
    ).toContain("after now in your local time");
    expect(
      explainErrorCodes(["linkedin_supervision_idempotency_conflict"]),
    ).toContain("Idempotency conflict");
  });
});
