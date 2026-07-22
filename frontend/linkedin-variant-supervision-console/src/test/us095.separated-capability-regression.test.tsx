/**
 * US-095 / BL-034 Story 3 — focused separated-UI capability regression (R1–R8).
 *
 * Proves schedule visibility, pending-supervision, dry-run defer, and US-040D
 * auth session gating use absolute SILVERMAN_OPERATOR_UI_API_BASE_URL with no
 * relative same-origin fallback when separated config is valid. Does not
 * implement Google/OIDC (BL-035). After US-096, holds must not depend on the
 * worker serving the former embedded console SPA.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryBearerAuthProvider,
  type AuthProvider,
} from "../api/auth";
import { SupervisionApiClient } from "../api/client";
import {
  DEFER_PATH,
  PENDING_SUPERVISION_PATH,
  SCHEDULE_VISIBILITY_PATH,
  type MutationResult,
  type PendingSupervisionResponse,
  type ScheduleVisibilityResponse,
} from "../api/types";
import { ConfigBlockedScreen } from "../components/ConfigBlockedScreen";
import {
  joinApiUrl,
  OPERATOR_UI_API_BASE_URL_KEY,
  OPERATOR_UI_ENV_LABEL_KEY,
  resolveOperatorUiConfig,
} from "../config/operatorUiConfig";
import App from "../App";

const WORKER_ORIGIN = "http://192.168.0.194:8010";
const UI_ORIGIN = "http://192.168.0.194:8011";

const emptySchedule: ScheduleVisibilityResponse = {
  status: "ok",
  observed_at_utc: "2026-07-21T18:00:00Z",
  read_only: true,
  year: 2026,
  month: 7,
  from_utc: "2026-07-01T00:00:00Z",
  to_utc: "2026-07-31T23:59:59Z",
  linkedin_publication_enabled: false,
  calendar_fingerprint: "b".repeat(64),
  items: [],
  issues: [],
};

const emptyPending: PendingSupervisionResponse = {
  status: "ok",
  observed_at_utc: "2026-07-21T18:00:00Z",
  read_only: true,
  linkedin_publication_enabled: false,
  variants: [],
  issues: [],
  integration_failures: [],
};

const dryRunDeferResult: MutationResult = {
  status: "completed",
  campaign_id: "camp-1",
  variant: "engineering-leadership",
  state: "pending",
  publish_state: "pending",
  dry_run: true,
  phase: "defer",
  errors: [],
  warnings: [],
  metadata_written: false,
};

function separatedClient(
  auth: AuthProvider,
  fetchImpl: typeof fetch,
): SupervisionApiClient {
  return new SupervisionApiClient(auth, fetchImpl, WORKER_ORIGIN);
}

describe("US-095 R1 — absolute base URL join (no relative fallback)", () => {
  it("joinApiUrl prefixes worker paths with absolute origin when separated", () => {
    expect(joinApiUrl(WORKER_ORIGIN, SCHEDULE_VISIBILITY_PATH)).toBe(
      `${WORKER_ORIGIN}${SCHEDULE_VISIBILITY_PATH}`,
    );
    expect(joinApiUrl(WORKER_ORIGIN, PENDING_SUPERVISION_PATH)).toBe(
      `${WORKER_ORIGIN}${PENDING_SUPERVISION_PATH}`,
    );
    expect(joinApiUrl(WORKER_ORIGIN, DEFER_PATH)).toBe(
      `${WORKER_ORIGIN}${DEFER_PATH}`,
    );
  });

  it("resolveUrl on separated client never yields UI-origin-relative paths", () => {
    const auth = new MemoryBearerAuthProvider();
    const client = separatedClient(auth, vi.fn() as unknown as typeof fetch);
    const scheduleUrl = client.resolveUrl(SCHEDULE_VISIBILITY_PATH);
    const pendingUrl = client.resolveUrl(PENDING_SUPERVISION_PATH);
    expect(scheduleUrl.startsWith(WORKER_ORIGIN)).toBe(true);
    expect(pendingUrl.startsWith(WORKER_ORIGIN)).toBe(true);
    expect(scheduleUrl.startsWith("/")).toBe(false);
    expect(pendingUrl.startsWith("/")).toBe(false);
    expect(scheduleUrl.includes(UI_ORIGIN)).toBe(false);
  });

  it("separated mode config requires absolute API base URL", () => {
    const ok = resolveOperatorUiConfig("separated", {
      apiBaseUrl: WORKER_ORIGIN,
      envLabel: "prod",
    });
    expect(ok.ok).toBe(true);
    if (ok.ok) {
      expect(ok.config.apiBaseUrl).toBe(WORKER_ORIGIN);
    }
  });
});

describe("US-095 R2 — schedule visibility absolute GET", () => {
  it("getScheduleVisibility issues GET {apiBaseUrl}/flow-a/schedule-visibility?...", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify(emptySchedule), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );
    const client = separatedClient(auth, fetchImpl as typeof fetch);

    await client.getScheduleVisibility({ year: 2026, month: 7 });

    expect(fetchImpl).toHaveBeenCalledTimes(1);
    expect(fetchImpl).toHaveBeenCalledWith(
      `${WORKER_ORIGIN}/flow-a/schedule-visibility?year=2026&month=7`,
      expect.objectContaining({ method: "GET" }),
    );
    const calledUrl = String(fetchImpl.mock.calls[0][0]);
    expect(calledUrl.startsWith("/")).toBe(false);
    expect(calledUrl).not.toContain(":8011");
  });
});

describe("US-095 R3 — pending-supervision absolute GET", () => {
  it("getPendingSupervision issues GET {apiBaseUrl}/flow-a/linkedin-variants/pending-supervision", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify(emptyPending), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );
    const client = separatedClient(auth, fetchImpl as typeof fetch);

    await client.getPendingSupervision();

    expect(fetchImpl).toHaveBeenCalledWith(
      `${WORKER_ORIGIN}/flow-a/linkedin-variants/pending-supervision`,
      expect.objectContaining({ method: "GET" }),
    );
    const calledUrl = String(fetchImpl.mock.calls[0][0]);
    expect(calledUrl.startsWith("/")).toBe(false);
  });
});

describe("US-095 R4 — dry-run defer mutation absolute POST", () => {
  it("deferVariant with dry_run:true posts to {apiBaseUrl}/defer-linkedin-variant", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify(dryRunDeferResult), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );
    const client = separatedClient(auth, fetchImpl as typeof fetch);

    expect(client.canMutate()).toBe(true);

    const result = await client.deferVariant({
      campaign_id: "camp-1",
      variant: "engineering-leadership",
      new_scheduled_at_utc: "2026-08-01T15:00:00Z",
      dry_run: true,
    });

    expect(result.dry_run).toBe(true);
    expect(fetchImpl).toHaveBeenCalledWith(
      `${WORKER_ORIGIN}${DEFER_PATH}`,
      expect.objectContaining({ method: "POST" }),
    );
    const init = fetchImpl.mock.calls[0][1] as RequestInit;
    const body = JSON.parse(String(init.body)) as {
      dry_run: boolean;
      campaign_id: string;
    };
    expect(body.dry_run).toBe(true);
    expect(body.campaign_id).toBe("camp-1");
    expect(String(fetchImpl.mock.calls[0][0]).startsWith("/")).toBe(false);
  });

  it("does not invent a new mutation endpoint", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify(dryRunDeferResult), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );
    const client = separatedClient(auth, fetchImpl as typeof fetch);
    await client.deferVariant({
      campaign_id: "camp-1",
      variant: "engineering-leadership",
      new_scheduled_at_utc: "2026-08-01T15:00:00Z",
      dry_run: true,
    });
    expect(String(fetchImpl.mock.calls[0][0])).toBe(
      `${WORKER_ORIGIN}/defer-linkedin-variant`,
    );
  });
});

describe("US-095 R5 — US-040D auth session gating on separated client", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("sign-in enables canMutate without Google/OIDC; clear returns non-mutating", async () => {
    const promptFn = vi.fn(() => "session-key");
    const auth = new MemoryBearerAuthProvider(promptFn);
    const fetchImpl = vi.fn();
    const client = separatedClient(auth, fetchImpl as typeof fetch);

    expect(client.canMutate()).toBe(false);
    expect(client.hasCredential()).toBe(false);

    const signedIn = await client.signIn();
    expect(signedIn).toBe(true);
    expect(promptFn).toHaveBeenCalled();
    expect(client.canMutate()).toBe(true);
    expect(client.hasCredential()).toBe(true);
    // Injectable AuthProvider boundary preserved (not Google/OIDC).
    expect(client.getAuth()).toBe(auth);
    expect(auth).toBeInstanceOf(MemoryBearerAuthProvider);

    client.clearAuth();
    expect(client.canMutate()).toBe(false);
    expect(client.hasCredential()).toBe(false);
  });

  it("rejects dry-run defer when anonymous even with absolute base URL", async () => {
    const auth = new MemoryBearerAuthProvider(() => null);
    const fetchImpl = vi.fn();
    const client = separatedClient(auth, fetchImpl as typeof fetch);

    await expect(
      client.deferVariant({
        campaign_id: "camp-1",
        variant: "engineering-leadership",
        new_scheduled_at_utc: "2026-08-01T15:00:00Z",
        dry_run: true,
      }),
    ).rejects.toMatchObject({ kind: "auth_missing" });
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});

describe("US-095 R6/R7 hold — config and pairing blocks stay visible", () => {
  it("missing API base URL still fail-closed (US-093 hold)", () => {
    const result = resolveOperatorUiConfig("separated", undefined);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.requiredKeys).toContain(OPERATOR_UI_API_BASE_URL_KEY);
    }
    render(<ConfigBlockedScreen result={result as never} />);
    expect(screen.getByTestId("config-blocked-screen")).toBeInTheDocument();
    expect(screen.getByTestId("config-blocked-keys")).toHaveTextContent(
      OPERATOR_UI_API_BASE_URL_KEY,
    );
  });

  it("pairing mismatch block names env vars only (US-094 hold)", () => {
    render(
      <ConfigBlockedScreen
        result={{
          ok: false,
          reason: "pairing",
          message:
            "UI and API environments disagree (SILVERMAN_OPERATOR_UI_ENV_LABEL vs SILVERMAN_DEPLOYMENT_ENVIRONMENT)",
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
    expect(screen.getByRole("alert").textContent).not.toMatch(
      /Bearer |sk-|password|secret/i,
    );
  });
});

describe("US-095 R8 — operator-visible paired empty outcomes", () => {
  it("paired separated shell shows env badge and loads empty schedule/pending understandably", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      expect(url.startsWith(WORKER_ORIGIN)).toBe(true);
      if (url.includes("pending-supervision")) {
        return new Response(JSON.stringify(emptyPending), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("schedule-visibility")) {
        // Week/month loads may request adjacent months; echo year/month from query.
        const u = new URL(url);
        const year = Number(u.searchParams.get("year") || "2026");
        const month = Number(u.searchParams.get("month") || "7");
        return new Response(
          JSON.stringify({ ...emptySchedule, year, month }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        );
      }
      return new Response("not found", { status: 404 });
    });
    const client = separatedClient(auth, fetchImpl as typeof fetch);
    const user = userEvent.setup();

    render(<App client={client} deploymentEnvironment="prod" />);

    expect(
      screen.getByTestId("deployment-environment-badge"),
    ).toHaveTextContent("Prod");
    expect(screen.getByTestId("session-banner")).toBeInTheDocument();

    // Default view is week; empty state must be understandable.
    await waitFor(() => {
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
    });
    expect(screen.getByTestId("week-empty-state")).toHaveTextContent(
      /No publications this week/i,
    );

    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      const calledUrls = fetchImpl.mock.calls.map((c) => String(c[0]));
      expect(
        calledUrls.some((u) =>
          u.startsWith(`${WORKER_ORIGIN}/flow-a/schedule-visibility`),
        ),
      ).toBe(true);
      expect(
        calledUrls.some(
          (u) =>
            u ===
            `${WORKER_ORIGIN}/flow-a/linkedin-variants/pending-supervision`,
        ),
      ).toBe(true);
      expect(calledUrls.every((u) => !u.startsWith("/flow-a"))).toBe(true);
    });
  });
});
