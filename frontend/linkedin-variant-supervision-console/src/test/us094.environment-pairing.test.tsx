import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ConfigBlockedScreen } from "../components/ConfigBlockedScreen";
import { AppShell } from "../components/AppShell";
import { validateApiEnvironmentPairing } from "../config/environmentPairing";
import {
  OPERATOR_UI_API_BASE_URL_KEY,
  OPERATOR_UI_ENV_LABEL_KEY,
  resolveOperatorUiConfig,
} from "../config/operatorUiConfig";
import { SupervisionStoreProvider } from "../models/store";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";

function renderShellWithEnv(env: "uat" | "prod") {
  const auth = new MemoryBearerAuthProvider();
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
          read_only: true,
          variants: [],
          issues: [],
          integration_failures: [],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
  );
  const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch, "");
  return render(
    <SupervisionStoreProvider client={client}>
      <AppShell deploymentEnvironment={env}>
        <div />
      </AppShell>
    </SupervisionStoreProvider>,
  );
}

describe("US-094 environment pairing config", () => {
  it("separated mode fails closed when env label is missing", () => {
    const result = resolveOperatorUiConfig("separated", {
      apiBaseUrl: "http://192.168.0.194:8010",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("missing");
      expect(result.requiredKeys).toContain(OPERATOR_UI_ENV_LABEL_KEY);
      expect(result.message).toContain(OPERATOR_UI_ENV_LABEL_KEY);
    }
  });

  it("separated mode fails closed when env label is invalid", () => {
    const result = resolveOperatorUiConfig("separated", {
      apiBaseUrl: "http://192.168.0.194:8010",
      envLabel: "lan",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("invalid");
      expect(result.requiredKeys).toContain(OPERATOR_UI_ENV_LABEL_KEY);
    }
  });

  it("separated mode accepts uat and prod labels (case-insensitive)", () => {
    for (const label of ["uat", "UAT", "prod", "Prod"] as const) {
      const result = resolveOperatorUiConfig("separated", {
        apiBaseUrl: "http://192.168.0.194:8010",
        envLabel: label,
      });
      expect(result.ok).toBe(true);
      if (result.ok) {
        expect(result.config.envLabel).toBe(label.toLowerCase());
      }
    }
  });

  it("does not support embedded delivery that skips env label (US-096)", () => {
    // Embedded mode is retired; missing env label always fails closed in separated mode.
    const result = resolveOperatorUiConfig("separated", {
      apiBaseUrl: "http://192.168.0.194:8010",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.requiredKeys).toContain(OPERATOR_UI_ENV_LABEL_KEY);
    }
  });
});

describe("US-094 validateApiEnvironmentPairing", () => {
  it("allows matching uat pair", async () => {
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify({ deployment_environment: "uat" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );
    const result = await validateApiEnvironmentPairing(
      "http://192.168.0.194:8010",
      "uat",
      fetchImpl as typeof fetch,
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.environment).toBe("uat");
    }
    expect(fetchImpl).toHaveBeenCalledWith(
      "http://192.168.0.194:8010/health",
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("allows matching prod pair", async () => {
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify({ deployment_environment: "prod" }), {
          status: 200,
        }),
    );
    const result = await validateApiEnvironmentPairing(
      "http://uat.example.local:8010",
      "prod",
      fetchImpl as typeof fetch,
    );
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.environment).toBe("prod");
    }
  });

  it("blocks mismatched environments", async () => {
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify({ deployment_environment: "prod" }), {
          status: 200,
        }),
    );
    const result = await validateApiEnvironmentPairing(
      "http://192.168.0.194:8010",
      "uat",
      fetchImpl as typeof fetch,
    );
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("pairing");
      expect(result.requiredKeys).toContain(OPERATOR_UI_ENV_LABEL_KEY);
      expect(result.requiredKeys).toContain("SILVERMAN_DEPLOYMENT_ENVIRONMENT");
      expect(result.message).toContain("does not match");
    }
  });

  it("blocks when health is missing deployment_environment", async () => {
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify({ status: "healthy" }), { status: 200 }),
    );
    const result = await validateApiEnvironmentPairing(
      "http://192.168.0.194:8010",
      "prod",
      fetchImpl as typeof fetch,
    );
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("pairing");
      expect(result.message).toContain("deployment_environment");
    }
  });

  it("blocks when health is unreachable", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });
    const result = await validateApiEnvironmentPairing(
      "http://192.168.0.194:8010",
      "prod",
      fetchImpl as typeof fetch,
    );
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.reason).toBe("pairing");
      expect(result.requiredKeys).toContain(OPERATOR_UI_API_BASE_URL_KEY);
    }
  });
});

describe("US-094 pairing blocked UX and env badge", () => {
  it("shows pairing-specific blocked heading", () => {
    render(
      <ConfigBlockedScreen
        result={{
          ok: false,
          reason: "pairing",
          message: "UI and API environments disagree",
          requiredKeys: [
            OPERATOR_UI_ENV_LABEL_KEY,
            "SILVERMAN_DEPLOYMENT_ENVIRONMENT",
          ],
        }}
      />,
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      /Environment pairing failed/i,
    );
    expect(screen.getByTestId("config-blocked-keys")).toHaveTextContent(
      OPERATOR_UI_ENV_LABEL_KEY,
    );
  });

  it("shows active environment badge when paired", () => {
    renderShellWithEnv("prod");
    expect(screen.getByTestId("deployment-environment-badge")).toHaveTextContent(
      "Prod",
    );
  });
});
