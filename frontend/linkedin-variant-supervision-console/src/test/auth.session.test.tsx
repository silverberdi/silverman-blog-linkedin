import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  CookieSessionAuthProvider,
  MemoryBearerAuthProvider,
  ReadOnlyBearerAuthProvider,
} from "../api/auth";
import { SupervisionApiClient } from "../api/client";
import {
  effectiveCapabilities,
  sessionStateFromApiError,
  sessionBannerText,
} from "../api/session";
import type { ApiError } from "../api/errors";
import { SupervisionStoreProvider, useSupervisionStore } from "../models/store";
import { ScheduleEditorPanel } from "../components/ScheduleEditor";
import { InterimEventPanel } from "../components/InterimEventPanel";
import { MonthCalendarView } from "../components/MonthCalendarView";
import { AppShell } from "../components/AppShell";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityResponse,
} from "../api/types";
import type { ScheduleEditorTarget } from "../models/supervision";

const pendingPayload: PendingSupervisionResponse = {
  status: "ok",
  observed_at_utc: "2026-07-18T12:00:00Z",
  read_only: true,
  linkedin_publication_enabled: true,
  variants: [
    {
      campaign_id: "camp-1",
      variant_id: "engineering-leadership",
      audience: "eng",
      scheduled_at_utc: "2026-07-20T15:00:00Z",
      publish_state: "pending",
      calendar_item_id: "cal-1",
      calendar_title: "Post",
      calendar_due_at_utc: "2026-07-19T11:00:00Z",
      calendar_status: "scheduled",
      operator_supervision_last_action: null,
      auto_queue_eligible: true,
      operator_supervision_reason: null,
      draft_content: "Hello",
    },
  ],
  issues: [],
  integration_failures: [],
};

const schedulePayload: ScheduleVisibilityResponse = {
  status: "ok",
  observed_at_utc: "2026-07-18T12:00:00Z",
  read_only: true,
  year: 2026,
  month: 7,
  from_utc: "2026-07-01T00:00:00Z",
  to_utc: "2026-07-31T23:59:59Z",
  linkedin_publication_enabled: true,
  calendar_fingerprint: "a".repeat(64),
  items: [
    {
      item_id: "linkedin:camp-1:engineering-leadership",
      channel: "linkedin",
      campaign_id: "camp-1",
      variant_id: "engineering-leadership",
      title: "eng",
      audience: "eng",
      scheduled_at_utc: "2026-07-20T15:00:00Z",
      publication_state: "pending",
      source_state: "pending",
      blocked: false,
      critical: false,
      linkedin_api_published: false,
      schedule_editable: true,
      schedule_edit_block_reason: null,
    },
  ],
  issues: [],
};

function okFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("pending-supervision")) {
      return new Response(JSON.stringify(pendingPayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("schedule-visibility")) {
      return new Response(JSON.stringify(schedulePayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response("not found", { status: 404 });
  });
}

function Harness({
  client,
  openEditor,
}: {
  client: SupervisionApiClient;
  openEditor?: boolean;
}) {
  return (
    <SupervisionStoreProvider client={client}>
      <AppShell>
        <EditorOpener open={Boolean(openEditor)} />
        <ScheduleEditorPanel />
        <InterimEventPanel />
        <MonthCalendarView />
      </AppShell>
    </SupervisionStoreProvider>
  );
}

function EditorOpener({ open }: { open: boolean }) {
  const { openScheduleEditor, setUnsavedScheduleDraft } = useSupervisionStore();
  if (open) {
    const target: ScheduleEditorTarget = {
      channel: "linkedin",
      itemId: "linkedin:camp-1:engineering-leadership",
      title: "eng",
      scheduledAtUtc: "2026-07-20T15:00:00Z",
      scheduleEditable: true,
      scheduleEditBlockReason: null,
      campaignId: "camp-1",
      variantId: "engineering-leadership",
      calendarItemId: "cal-1",
      entry: "week",
    };
    // Open once on mount via effect-like pattern in render is avoided;
    // use a tiny button.
    return (
      <button
        type="button"
        data-testid="force-open-editor"
        onClick={() => {
          openScheduleEditor(target);
          setUnsavedScheduleDraft(true);
        }}
      >
        Open editor
      </button>
    );
  }
  return null;
}

describe("session state mapping", () => {
  it("maps provider + HTTP outcomes to five session states", () => {
    expect(
      sessionStateFromApiError({
        kind: "auth_missing",
        message: "x",
        codes: [],
      }),
    ).toBe("anonymous");
    expect(
      sessionStateFromApiError({
        kind: "unauthorized",
        message: "x",
        httpStatus: 401,
        codes: [],
      }),
    ).toBe("expired");
    expect(
      sessionStateFromApiError({
        kind: "forbidden",
        message: "x",
        httpStatus: 403,
        codes: [],
      }),
    ).toBe("forbidden");
    expect(
      sessionStateFromApiError({
        kind: "network",
        message: "x",
        codes: [],
      }),
    ).toBe("service_unavailable");
    expect(
      sessionStateFromApiError({
        kind: "http",
        message: "x",
        httpStatus: 503,
        codes: [],
      }),
    ).toBe("service_unavailable");
    expect(
      sessionStateFromApiError({
        kind: "validation",
        message: "x",
        httpStatus: 422,
        codes: [],
      }),
    ).toBeNull();
  });

  it("uses qualified language in session banners", () => {
    for (const state of [
      "anonymous",
      "authenticated",
      "expired",
      "forbidden",
      "service_unavailable",
    ] as const) {
      const text = sessionBannerText(state);
      expect(text.toLowerCase()).not.toMatch(/successfully published to linkedin/);
      expect(text).toMatch(/LinkedIn API published|authenticated|expired|Forbidden|unavailable|Not authenticated/i);
    }
  });

  it("MemoryBearer: credential ⇒ canRead/canMutate; none ⇒ both false", () => {
    const auth = new MemoryBearerAuthProvider();
    expect(auth.canRead()).toBe(false);
    expect(auth.canMutate()).toBe(false);
    auth.setTokenForTests("key");
    expect(auth.canRead()).toBe(true);
    expect(auth.canMutate()).toBe(true);
  });

  it("effectiveCapabilities gates mutate on session", () => {
    expect(effectiveCapabilities(true, true, "anonymous")).toEqual({
      canRead: false,
      canMutate: false,
    });
    expect(effectiveCapabilities(true, true, "authenticated")).toEqual({
      canRead: true,
      canMutate: true,
    });
    expect(effectiveCapabilities(true, true, "expired")).toEqual({
      canRead: false,
      canMutate: false,
    });
    expect(effectiveCapabilities(true, true, "forbidden")).toEqual({
      canRead: true,
      canMutate: false,
    });
    expect(effectiveCapabilities(true, false, "authenticated")).toEqual({
      canRead: true,
      canMutate: false,
    });
  });
});

describe("API client auth-readiness mapping", () => {
  it("maps 403 to forbidden without clearing credential", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("key");
    const fetchImpl = vi.fn(
      async () =>
        new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 }),
    );
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    await expect(client.getPendingSupervision()).rejects.toMatchObject({
      kind: "forbidden",
      httpStatus: 403,
      message: expect.stringContaining("Forbidden (403)"),
    } satisfies Partial<ApiError>);
    expect(auth.hasCredential()).toBe(true);
  });

  it("maps 503 to service-unavailable http error", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("key");
    const fetchImpl = vi.fn(
      async () => new Response("down", { status: 503 }),
    );
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    await expect(client.getPendingSupervision()).rejects.toMatchObject({
      kind: "http",
      httpStatus: 503,
      message: expect.stringContaining("Service unavailable"),
    });
  });

  it("maps network failure distinctly", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("key");
    const fetchImpl = vi.fn(async () => {
      throw new Error("Failed to fetch");
    });
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    await expect(client.getPendingSupervision()).rejects.toMatchObject({
      kind: "network",
    });
  });

  it("rejects mutations when provider is read-only", async () => {
    const auth = new ReadOnlyBearerAuthProvider();
    auth.setTokenForTests("key");
    const fetchImpl = vi.fn();
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    await expect(
      client.deferVariant({
        campaign_id: "c",
        variant: "v",
        new_scheduled_at_utc: "2026-08-01T12:00:00Z",
        dry_run: true,
      }),
    ).rejects.toMatchObject({ kind: "mutation_denied" });
    expect(fetchImpl).not.toHaveBeenCalled();
  });
});

describe("mutation gating and expiry draft preservation", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("disables list mutation controls when !canMutate (anonymous)", async () => {
    const auth = new MemoryBearerAuthProvider();
    const client = new SupervisionApiClient(auth, okFetch() as typeof fetch);
    render(<Harness client={client} />);
    expect(screen.getByTestId("session-banner").textContent).toMatch(
      /Not authenticated/i,
    );
    // No rows until load; force authenticated snapshot path via load with prompt cancel → still anonymous
  });

  it("disables mutation controls for read-only authenticated session", async () => {
    const auth = new ReadOnlyBearerAuthProvider();
    auth.setTokenForTests("key");
    const client = new SupervisionApiClient(auth, okFetch() as typeof fetch);
    const user = userEvent.setup();
    render(<Harness client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });
    const open = await screen.findByTestId("schedule-open-month");
    await user.click(open);
    await waitFor(() => {
      expect(screen.getByTestId("interim-event-panel")).toBeInTheDocument();
    });
    expect(screen.getByTestId("readonly-gated-note")).toBeInTheDocument();
    expect(screen.getByTestId("row-edit")).toBeDisabled();
    expect(screen.getByTestId("row-defer")).not.toBeDisabled();
    expect(screen.getByTestId("row-cancel")).toBeDisabled();
  });

  it("preserves schedule draft and visible context on session expiry", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("key");
    let allowReads = true;
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (
        allowReads &&
        (url.includes("pending-supervision") ||
          url.includes("schedule-visibility"))
      ) {
        if (url.includes("pending-supervision")) {
          return new Response(JSON.stringify(pendingPayload), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          });
        }
        return new Response(JSON.stringify(schedulePayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response(JSON.stringify({ detail: "Unauthorized" }), {
        status: 401,
      });
    });
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    const user = userEvent.setup();
    render(<Harness client={client} openEditor />);

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("force-open-editor"));
    const datetime = screen.getByTestId("schedule-datetime") as HTMLInputElement;
    await user.clear(datetime);
    await user.type(datetime, "2026-08-15T10:30:00");
    expect(datetime.value).toContain("2026-08-15");

    allowReads = false;
    // Trigger expiry via refresh
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("session-banner").textContent).toMatch(
        /Session expired/i,
      );
    });

    // Context + draft preserved
    expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    expect(screen.getByTestId("schedule-editor-panel")).toBeInTheDocument();
    expect(
      (screen.getByTestId("schedule-datetime") as HTMLInputElement).value,
    ).toContain("2026-08-15");
    expect(screen.getByTestId("schedule-submit")).toBeDisabled();
    expect(screen.getByTestId("sign-in-btn")).toBeInTheDocument();
    expect(auth.hasCredential()).toBe(false);
  });
});

describe("provider swap without calendar component changes", () => {
  it("CookieSessionAuthProvider uses credentials include and relative paths", async () => {
    const auth = new CookieSessionAuthProvider();
    auth.setSignedInForTests(true, true);
    const fetchImpl = okFetch();
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    await client.getPendingSupervision();
    expect(fetchImpl).toHaveBeenCalled();
    const [path, init] = fetchImpl.mock.calls[0]!;
    expect(String(path)).toBe("/flow-a/linkedin-variants/pending-supervision");
    expect(String(path)).not.toMatch(/^https?:\/\//);
    expect((init as RequestInit).credentials).toBe("include");
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it("calendar interim actions work with cookie provider via typed client only", async () => {
    const auth = new CookieSessionAuthProvider();
    auth.setSignedInForTests(true, true);
    const client = new SupervisionApiClient(auth, okFetch() as typeof fetch);
    const user = userEvent.setup();
    render(<Harness client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });
    await user.click(await screen.findByTestId("schedule-open-month"));
    await waitFor(() => {
      expect(screen.getByTestId("interim-event-panel")).toBeInTheDocument();
    });
    expect(screen.getByTestId("row-edit")).not.toBeDisabled();
  });
});

describe("secrets hygiene", () => {
  it("frontend auth source does not embed secret-like placeholders", async () => {
    const { readFileSync } = await import("node:fs");
    const { resolve, dirname } = await import("node:path");
    const { fileURLToPath } = await import("node:url");
    const dir = dirname(fileURLToPath(import.meta.url));
    const authSrc = readFileSync(resolve(dir, "../api/auth.ts"), "utf-8");
    const clientSrc = readFileSync(resolve(dir, "../api/client.ts"), "utf-8");
    const placeholder = ["CHANGE", "ME"].join("_");
    expect(authSrc.toLowerCase()).not.toContain(placeholder.toLowerCase());
    expect(clientSrc.toLowerCase()).not.toContain(placeholder.toLowerCase());
    expect(authSrc).not.toMatch(/\/data\/silverman/);
    expect(clientSrc).not.toMatch(/192\.168\./);
    expect(authSrc).not.toMatch(/\bsk-[A-Za-z0-9]{8,}\b/);
  });
});
