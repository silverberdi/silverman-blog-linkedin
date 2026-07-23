import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import { ConfigBlockedScreen } from "../components/ConfigBlockedScreen";
import {
  OPERATOR_UI_API_BASE_URL_KEY,
  isValidAbsoluteHttpUrl,
  joinApiUrl,
  normalizeApiBaseUrl,
  resolveOperatorUiConfig,
} from "../config/operatorUiConfig";
import { SCHEDULE_VISIBILITY_PATH } from "../api/types";

describe("operator UI API base URL config", () => {
  it("joins absolute apiBaseUrl with root-relative worker paths", () => {
    expect(
      joinApiUrl("http://192.168.0.194:8010", SCHEDULE_VISIBILITY_PATH),
    ).toBe("http://192.168.0.194:8010/flow-a/schedule-visibility");
    expect(
      joinApiUrl(
        "http://192.168.0.194:8010",
        `${SCHEDULE_VISIBILITY_PATH}?year=2026&month=7`,
      ),
    ).toBe(
      "http://192.168.0.194:8010/flow-a/schedule-visibility?year=2026&month=7",
    );
  });

  it("returns relative paths when apiBaseUrl is empty (same-origin private hop / tests)", () => {
    expect(joinApiUrl("", SCHEDULE_VISIBILITY_PATH)).toBe(
      SCHEDULE_VISIBILITY_PATH,
    );
  });

  it("accepts only absolute http(s) URLs (same-origin uses isSameOriginApiBase)", () => {
    expect(isValidAbsoluteHttpUrl("http://192.168.0.194:8010")).toBe(true);
    expect(isValidAbsoluteHttpUrl("https://api.example.local")).toBe(true);
    expect(isValidAbsoluteHttpUrl("")).toBe(false);
    expect(isValidAbsoluteHttpUrl("/flow-a")).toBe(false);
    expect(isValidAbsoluteHttpUrl("ftp://example.com")).toBe(false);
    expect(isValidAbsoluteHttpUrl("not-a-url")).toBe(false);
  });

  it("normalizes base URL to origin (drops path)", () => {
    expect(normalizeApiBaseUrl("http://192.168.0.194:8010/extra")).toBe(
      "http://192.168.0.194:8010",
    );
  });

  it("always resolves as separated delivery (embedded retired US-096)", () => {
    const result = resolveOperatorUiConfig("separated", {
      apiBaseUrl: "http://192.168.0.194:8010",
      envLabel: "prod",
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.config.deliveryMode).toBe("separated");
      expect(result.config.apiBaseUrl).toBe("http://192.168.0.194:8010");
    }
  });

  it("separated mode fails closed when API base URL is missing", () => {
    const result = resolveOperatorUiConfig("separated", undefined);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("missing");
      expect(result.requiredKeys).toContain(OPERATOR_UI_API_BASE_URL_KEY);
      expect(result.message).toContain(OPERATOR_UI_API_BASE_URL_KEY);
    }
  });

  it("separated mode fails closed when API base URL is invalid", () => {
    const result = resolveOperatorUiConfig("separated", {
      apiBaseUrl: "/relative-only",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("invalid");
      expect(result.requiredKeys).toContain(OPERATOR_UI_API_BASE_URL_KEY);
    }
  });

  it("separated mode accepts a valid absolute API base URL with env label", () => {
    const result = resolveOperatorUiConfig("separated", {
      apiBaseUrl: "http://192.168.0.194:8010",
      envLabel: "uat",
    });
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.config.apiBaseUrl).toBe("http://192.168.0.194:8010");
      expect(result.config.envLabel).toBe("uat");
    }
  });

  it("separated mode fails closed when env label is missing (US-094)", () => {
    const result = resolveOperatorUiConfig("separated", {
      apiBaseUrl: "http://192.168.0.194:8010",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.requiredKeys).toContain("SILVERMAN_OPERATOR_UI_ENV_LABEL");
    }
  });
});

describe("ConfigBlockedScreen", () => {
  it("shows operator-visible blocked state naming required keys", () => {
    render(
      <ConfigBlockedScreen
        result={{
          ok: false,
          reason: "missing",
          message: `Operator UI is blocked: set ${OPERATOR_UI_API_BASE_URL_KEY}`,
          requiredKeys: [OPERATOR_UI_API_BASE_URL_KEY],
        }}
      />,
    );
    expect(screen.getByTestId("config-blocked-screen")).toBeInTheDocument();
    expect(screen.getByTestId("config-blocked-keys")).toHaveTextContent(
      OPERATOR_UI_API_BASE_URL_KEY,
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      OPERATOR_UI_API_BASE_URL_KEY,
    );
  });
});

describe("SupervisionApiClient apiBaseUrl", () => {
  it("prefixes schedule visibility with injectable absolute base URL", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("key");
    const fetchImpl = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            status: "ok",
            observed_at_utc: "2026-07-21T00:00:00Z",
            year: 2026,
            month: 7,
            items: [],
            linkedin_publication_enabled: false,
          }),
          { status: 200 },
        ),
    );
    const client = new SupervisionApiClient(
      auth,
      fetchImpl as typeof fetch,
      "http://192.168.0.194:8010",
    );

    await client.getScheduleVisibility({ year: 2026, month: 7 });

    expect(fetchImpl).toHaveBeenCalledWith(
      "http://192.168.0.194:8010/flow-a/schedule-visibility?year=2026&month=7",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("keeps auth-gated calls when apiBaseUrl is empty (injectable unit test)", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("key");
    const fetchImpl = vi.fn(
      async () =>
        new Response(
          JSON.stringify({
            status: "ok",
            observed_at_utc: "2026-07-21T00:00:00Z",
            read_only: true,
            linkedin_publication_enabled: false,
            variants: [],
            issues: [],
            integration_failures: [],
          }),
          { status: 200 },
        ),
    );
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch, "");

    await client.getPendingSupervision();

    expect(fetchImpl).toHaveBeenCalledWith(
      "/flow-a/linkedin-variants/pending-supervision",
      expect.objectContaining({ method: "GET" }),
    );
  });
});
