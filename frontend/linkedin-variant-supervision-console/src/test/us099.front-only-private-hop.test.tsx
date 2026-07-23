/**
 * US-099 — front-only public UI + same-origin private hop holds.
 *
 * Does not claim Story accepted, live tunnel activation, or public worker API.
 * Preserves US-093 absolute-base path and US-097/US-098 auth vocabulary.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { GoogleOidcAuthProvider, MemoryBearerAuthProvider } from "../api/auth";
import { SupervisionApiClient } from "../api/client";
import {
  OPERATOR_UI_API_BASE_URL_KEY,
  isSameOriginApiBase,
  joinApiUrl,
  resolveOperatorUiConfig,
} from "../config/operatorUiConfig";
import {
  PENDING_SUPERVISION_PATH,
  SCHEDULE_VISIBILITY_PATH,
} from "../api/types";

describe("US-099 same-origin private hop config", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("recognizes / and same-origin as private-hop bases", () => {
    expect(isSameOriginApiBase("/")).toBe(true);
    expect(isSameOriginApiBase("same-origin")).toBe(true);
    expect(isSameOriginApiBase("Same-Origin")).toBe(true);
    expect(isSameOriginApiBase("")).toBe(false);
    expect(isSameOriginApiBase("http://192.168.0.194:8010")).toBe(false);
    expect(isSameOriginApiBase("/relative-only")).toBe(false);
  });

  it("resolves / to empty apiBaseUrl with pairing label (no public API hostname)", () => {
    const result = resolveOperatorUiConfig("separated", {
      apiBaseUrl: "/",
      envLabel: "prod",
      googleAuthEnabled: true,
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.config.apiBaseUrl).toBe("");
      expect(result.config.envLabel).toBe("prod");
      expect(result.config.googleAuthEnabled).toBe(true);
    }
  });

  it("joinApiUrl with empty base stays same-origin (no public worker host)", () => {
    expect(joinApiUrl("", SCHEDULE_VISIBILITY_PATH)).toBe(
      SCHEDULE_VISIBILITY_PATH,
    );
    expect(joinApiUrl("", PENDING_SUPERVISION_PATH)).toBe(
      PENDING_SUPERVISION_PATH,
    );
    expect(joinApiUrl("", "/auth/google/start")).toBe("/auth/google/start");
    expect(joinApiUrl("", "/health")).toBe("/health");
  });

  it("typed client schedule visibility uses relative path under private hop", async () => {
    const fetchFn = vi.fn(async () =>
      Response.json({
        status: "ok",
        observed_at_utc: "2026-07-22T00:00:00Z",
        read_only: true,
        year: 2026,
        month: 7,
        from_utc: "2026-07-01T00:00:00Z",
        to_utc: "2026-08-01T00:00:00Z",
        linkedin_publication_enabled: false,
        items: [],
        issues: [],
      }),
    );
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-operator-token");
    const client = new SupervisionApiClient(auth, fetchFn, "");
    await client.getScheduleVisibility(2026, 7);
    expect(fetchFn).toHaveBeenCalled();
    const calledUrl = String(fetchFn.mock.calls[0]?.[0]);
    expect(calledUrl.startsWith(SCHEDULE_VISIBILITY_PATH)).toBe(true);
    expect(calledUrl).not.toContain("8010");
    expect(calledUrl).not.toMatch(/^https?:\/\/api\./);
  });

  it("Google sign-in start stays on same-origin /auth/google/start", async () => {
    const navigate = vi.fn();
    const fetchFn = vi.fn();
    const provider = new GoogleOidcAuthProvider("", fetchFn, navigate);
    await provider.signIn();
    expect(navigate).toHaveBeenCalledWith("/auth/google/start");
    expect(String(navigate.mock.calls[0]?.[0])).not.toContain("8010");
  });

  it("empty apiBaseUrl still fails closed (missing — not accidental same-origin)", () => {
    const result = resolveOperatorUiConfig("separated", {
      apiBaseUrl: "",
      envLabel: "prod",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("missing");
      expect(result.requiredKeys).toContain(OPERATOR_UI_API_BASE_URL_KEY);
    }
  });

  it("does not embed tunnel tokens or API keys in config resolution messages", () => {
    const result = resolveOperatorUiConfig("separated", undefined);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.message).not.toMatch(/eyJ|sk-|tunnel|Bearer /i);
      expect(result.message).toContain(OPERATOR_UI_API_BASE_URL_KEY);
    }
  });
});

describe("US-099 fail-closed public URL vocabulary (holds)", () => {
  it("anonymous Google provider cannot mutate", async () => {
    const fetchFn = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/auth/google/status")) {
        return Response.json({ enabled: true, configured: true });
      }
      if (url.includes("/auth/me")) {
        return Response.json({ authenticated: false }, { status: 401 });
      }
      return new Response("not found", { status: 404 });
    });
    const auth = new GoogleOidcAuthProvider("", fetchFn);
    await auth.restoreSession("");
    expect(auth.canMutate()).toBe(false);
    expect(auth.getIdentityState()).toBe("anonymous");
  });

  it("non-allowlisted Google identity is forbidden and non-mutating", async () => {
    const auth = new GoogleOidcAuthProvider("", vi.fn(), vi.fn());
    const restored = await auth.restoreSession("?auth=forbidden");
    expect(restored).toBe("forbidden");
    expect(auth.canMutate()).toBe(false);
    expect(auth.getIdentityState()).toBe("forbidden");
    expect(auth.hasCredential()).toBe(false);
  });

  it("allowlisted Google session can mutate via private hop without worker API key", async () => {
    const fetchFn = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/auth/google/status")) {
        return Response.json({ enabled: true, configured: true });
      }
      if (url.includes("/auth/me")) {
        return Response.json({
          authenticated: true,
          email: "silverio.bernal@gmail.com",
          can_mutate: true,
        });
      }
      return new Response("not found", { status: 404 });
    });
    const auth = new GoogleOidcAuthProvider("", fetchFn);
    const restored = await auth.restoreSession("?auth=ok");
    expect(restored).toBe("authenticated");
    expect(auth.canMutate()).toBe(true);
    const headers = await auth.getRequestHeaders();
    expect(headers.Authorization).toBeUndefined();
    expect(JSON.stringify(headers)).not.toMatch(/sk-|api[_-]?key/i);
  });
});
