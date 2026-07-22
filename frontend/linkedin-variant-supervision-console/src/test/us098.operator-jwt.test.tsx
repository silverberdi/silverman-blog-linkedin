/**
 * US-098: Google path uses operator JWT cookie credential (not worker API key).
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
import { sessionBannerText } from "../api/session";
import { SupervisionStoreProvider, useSupervisionStore } from "../models/store";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function Probe() {
  const { sessionState, canMutate, sessionBanner, clearAuth, signIn } =
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

describe("US-098 operator JWT console path", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("Google path typed-client calls use credentials include and never send worker API key", async () => {
    const fetchFn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
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
      if (url.includes("/flow-a/linkedin-variants/pending-supervision")) {
        return new Response(
          JSON.stringify({
            status: "ok",
            observed_at_utc: "2026-07-22T12:00:00Z",
            read_only: true,
            linkedin_publication_enabled: false,
            variants: [],
            issues: [],
            integration_failures: [],
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
      vi.fn(),
    );
    await auth.restoreSession("?auth=ok");
    expect(auth.getCredentialsMode()).toBe("include");
    expect(await auth.getRequestHeaders()).toEqual({});

    const client = new SupervisionApiClient(
      auth,
      fetchFn as typeof fetch,
      "http://192.168.0.194:8010",
    );
    await client.getPendingSupervision();

    const capabilityCalls = fetchFn.mock.calls.filter(([input]) =>
      String(input).includes("/flow-a/linkedin-variants/pending-supervision"),
    );
    expect(capabilityCalls.length).toBe(1);
    const init = capabilityCalls[0][1] as RequestInit;
    expect(init.credentials).toBe("include");
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBeNull();
  });

  it("clear session stops operator credential and returns non-mutating anonymous state", async () => {
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
      vi.fn(),
    );
    await auth.restoreSession("?auth=ok");
    const client = new SupervisionApiClient(
      auth,
      fetchFn as typeof fetch,
      "http://192.168.0.194:8010",
    );

    render(
      <SupervisionStoreProvider
        client={client}
        initialSessionState="authenticated"
        googleAuthEnabled
      >
        <Probe />
      </SupervisionStoreProvider>,
    );

    expect(screen.getByTestId("probe-session").textContent).toBe("authenticated");
    expect(screen.getByTestId("probe-mutate").textContent).toBe("true");

    await userEvent.click(screen.getByTestId("probe-clear"));

    await waitFor(() => {
      expect(screen.getByTestId("probe-session").textContent).toBe("anonymous");
      expect(screen.getByTestId("probe-mutate").textContent).toBe("false");
    });
    expect(auth.hasCredential()).toBe(false);
    expect(auth.canMutate()).toBe(false);
    expect(
      fetchFn.mock.calls.some(([input]) => String(input).includes("/auth/logout")),
    ).toBe(true);
  });

  it("expired-session banner preserves unsaved-edit guidance (US-040D hold)", () => {
    const text = sessionBannerText("expired", { googleAuthEnabled: true });
    expect(text).toMatch(/Session expired/i);
    expect(text).toMatch(/unsaved schedule drafts/i);
    expect(text).toMatch(/not discarded/i);
  });

  it("MemoryBearer is not default when Google auth enabled", () => {
    const provider = createAuthProviderForConfig({
      googleAuthEnabled: true,
      apiBaseUrl: "http://192.168.0.194:8010",
    });
    expect(provider).toBeInstanceOf(GoogleOidcAuthProvider);
    expect(provider).not.toBeInstanceOf(MemoryBearerAuthProvider);

    const fallback = createAuthProviderForConfig({
      googleAuthEnabled: false,
      apiBaseUrl: "http://192.168.0.194:8010",
    });
    expect(fallback).toBeInstanceOf(MemoryBearerAuthProvider);
  });

  it("frontend source does not embed JWT signing secrets or API keys", () => {
    const authSrc = readFileSync(resolve(__dirname, "../api/auth.ts"), "utf8");
    const sessionSrc = readFileSync(
      resolve(__dirname, "../api/session.ts"),
      "utf8",
    );
    const mainSrc = readFileSync(resolve(__dirname, "../main.tsx"), "utf8");
    for (const blob of [authSrc, sessionSrc, mainSrc]) {
      expect(blob).not.toMatch(/CLIENT_SECRET\s*=\s*['\"][^'\"]+['\"]/);
      expect(blob).not.toMatch(/sk-[a-zA-Z0-9]{10,}/);
      expect(blob).not.toMatch(/CHANGE_ME_/);
      expect(blob).not.toContain("test-operator-session-secret");
      expect(blob).not.toContain("test-google-client-secret");
    }
  });
});
