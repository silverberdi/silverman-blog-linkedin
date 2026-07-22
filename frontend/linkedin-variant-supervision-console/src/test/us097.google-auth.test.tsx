/**
 * US-097 Google OIDC AuthProvider + session vocabulary holds.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  GoogleOidcAuthProvider,
  MemoryBearerAuthProvider,
  createAuthProviderForConfig,
} from "../api/auth";
import { SupervisionApiClient } from "../api/client";
import {
  effectiveCapabilities,
  sessionBannerText,
} from "../api/session";
import { SupervisionStoreProvider, useSupervisionStore } from "../models/store";
import { AppShell } from "../components/AppShell";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function Probe() {
  const { sessionState, canMutate, sessionBanner, signIn, clearAuth } =
    useSupervisionStore();
  return (
    <div>
      <span data-testid="probe-session">{sessionState}</span>
      <span data-testid="probe-mutate">{String(canMutate)}</span>
      <span data-testid="probe-banner">{sessionBanner.text}</span>
      <button type="button" data-testid="probe-signin" onClick={() => void signIn()}>
        Sign in
      </button>
      <button type="button" data-testid="probe-clear" onClick={() => clearAuth()}>
        Clear
      </button>
    </div>
  );
}

describe("US-097 Google OIDC AuthProvider", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("allowlisted Google session establishes authenticated + canMutate without API-key paste", async () => {
    const navigate = vi.fn();
    const fetchFn = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/auth/google/status")) {
        return new Response(JSON.stringify({ enabled: true, configured: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("/auth/me")) {
        return new Response(
          JSON.stringify({
            authenticated: true,
            email: "silverio.bernal@gmail.com",
            can_mutate: true,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.includes("/auth/logout")) {
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      }
      return new Response("not found", { status: 404 });
    });

    const auth = new GoogleOidcAuthProvider(
      "http://192.168.0.194:8010",
      fetchFn,
      navigate,
    );
    const restored = await auth.restoreSession("?auth=ok");
    expect(restored).toBe("authenticated");
    expect(auth.hasCredential()).toBe(true);
    expect(auth.canMutate()).toBe(true);
    expect(auth.getIdentityState()).toBe("authenticated");

    // signIn must redirect — never prompt for API key.
    const promptSpy = vi.spyOn(window, "prompt");
    await auth.signIn();
    expect(navigate).toHaveBeenCalledWith(
      "http://192.168.0.194:8010/auth/google/start",
    );
    expect(promptSpy).not.toHaveBeenCalled();

    const client = new SupervisionApiClient(auth, fetchFn, "http://192.168.0.194:8010");
    render(
      <SupervisionStoreProvider
        client={client}
        initialSessionState="authenticated"
        googleAuthEnabled
      >
        <Probe />
      </SupervisionStoreProvider>,
    );
    expect(screen.getByTestId("probe-session")).toHaveTextContent("authenticated");
    expect(screen.getByTestId("probe-mutate")).toHaveTextContent("true");
    expect(screen.getByTestId("probe-banner").textContent).toMatch(/allowlisted Google/i);

    await userEvent.click(screen.getByTestId("probe-clear"));
    await waitFor(() => {
      expect(screen.getByTestId("probe-session")).toHaveTextContent("anonymous");
      expect(screen.getByTestId("probe-mutate")).toHaveTextContent("false");
    });
  });

  it("non-allowlisted Google identity maps to forbidden, not authenticated empty console", async () => {
    const auth = new GoogleOidcAuthProvider(
      "http://192.168.0.194:8010",
      vi.fn(async () => new Response("{}", { status: 200 })),
      vi.fn(),
    );
    const restored = await auth.restoreSession("?auth=forbidden");
    expect(restored).toBe("forbidden");
    expect(auth.hasCredential()).toBe(false);
    expect(auth.canMutate()).toBe(false);
    expect(auth.getIdentityState()).toBe("forbidden");

    const caps = effectiveCapabilities(
      auth.canRead(),
      auth.canMutate(),
      "forbidden",
    );
    expect(caps.canMutate).toBe(false);

    const client = new SupervisionApiClient(
      auth,
      fetch.bind(globalThis),
      "http://192.168.0.194:8010",
    );
    render(
      <SupervisionStoreProvider
        client={client}
        initialSessionState="forbidden"
        googleAuthEnabled
      >
        <AppShell>
          <div data-testid="body">body</div>
        </AppShell>
      </SupervisionStoreProvider>,
    );
    const banner = screen.getByTestId("session-banner");
    expect(banner.textContent).toMatch(/not on the operator allowlist/i);
    expect(banner.textContent).not.toMatch(/Authenticated with an allowlisted/i);
    expect(screen.getByTestId("sign-in-btn")).toBeInTheDocument();
  });

  it("anonymous Google-path visitor cannot mutate", () => {
    const auth = new GoogleOidcAuthProvider("http://192.168.0.194:8010");
    expect(auth.getIdentityState()).toBe("anonymous");
    expect(auth.canMutate()).toBe(false);
    const caps = effectiveCapabilities(false, false, "anonymous");
    expect(caps.canMutate).toBe(false);
    expect(sessionBannerText("anonymous", { googleAuthEnabled: true })).toMatch(
      /Sign in with Google/i,
    );
  });

  it("wires Google provider when configured; MemoryBearer remains for fallback", () => {
    const google = createAuthProviderForConfig({
      googleAuthEnabled: true,
      apiBaseUrl: "http://192.168.0.194:8010",
    });
    expect(google).toBeInstanceOf(GoogleOidcAuthProvider);

    const fallback = createAuthProviderForConfig({
      googleAuthEnabled: false,
      apiBaseUrl: "http://192.168.0.194:8010",
    });
    expect(fallback).toBeInstanceOf(MemoryBearerAuthProvider);
  });

  it("frontend auth artifacts contain no client secrets or API keys", () => {
    const authSrc = readFileSync(
      resolve(__dirname, "../api/auth.ts"),
      "utf8",
    );
    const mainSrc = readFileSync(
      resolve(__dirname, "../main.tsx"),
      "utf8",
    );
    const entry = readFileSync(
      resolve(__dirname, "../../docker/docker-entrypoint.sh"),
      "utf8",
    );
    for (const blob of [authSrc, mainSrc, entry]) {
      expect(blob).not.toMatch(/CLIENT_SECRET\s*=\s*['\"][^'\"]+['\"]/);
      expect(blob).not.toMatch(/sk-[a-zA-Z0-9]{10,}/);
      expect(blob).not.toMatch(/CHANGE_ME_/);
      expect(blob).not.toMatch(/refresh_token\s*[:=]/);
      expect(blob).not.toContain("test-google-client-secret");
    }
  });
});
