import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import App from "../App";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityResponse,
} from "../api/types";

const __dirname = dirname(fileURLToPath(import.meta.url));

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
      calendar_due_at_utc: "2026-07-20T15:00:00Z",
      calendar_status: "planned",
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
    },
  ],
  issues: [],
};

function createClient() {
  const auth = new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-key");
  const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
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
  return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
}

/**
 * Desktop + mobile viewport validation evidence for Week + Month (US-040G).
 * Component/DOM evidence only — not Story accepted / Visual DoD capture.
 */
describe("viewport validation", () => {
  const cssPath = resolve(__dirname, "../styles/console.css");
  const css = readFileSync(cssPath, "utf-8");

  it("includes mobile media query for week columns and month patterns", () => {
    expect(css).toMatch(/@media\s*\(max-width:\s*860px\)/);
    expect(css).toMatch(/main\.console-shell/);
    expect(css).toMatch(/\.week-columns/);
    expect(css).toMatch(/\.week-event-chip/);
    expect(css).toMatch(/\.calendar-grid/);
    expect(css).toMatch(/--bg:\s*#12151a/);
  });

  it("renders Week default and Month at desktop viewport width", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 1280,
    });
    const user = userEvent.setup();
    const { getByTestId, unmount } = render(<App client={createClient()} />);
    expect(getByTestId("app-shell")).toBeInTheDocument();
    expect(getByTestId("week-view")).toBeInTheDocument();
    expect(getByTestId("view-week")).toBeInTheDocument();
    expect(getByTestId("view-month")).toBeInTheDocument();
    expect(screen.queryByTestId("view-list")).toBeNull();
    expect(screen.queryByTestId("list-view")).toBeNull();

    await user.click(getByTestId("view-month"));
    expect(getByTestId("month-calendar-view")).toBeInTheDocument();
    unmount();
  });

  it("renders Week and Month at mobile viewport width", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 375,
    });
    const user = userEvent.setup();
    const { getByTestId, unmount } = render(<App client={createClient()} />);
    expect(getByTestId("app-shell")).toBeInTheDocument();
    expect(getByTestId("week-view")).toBeInTheDocument();
    expect(getByTestId("load-btn")).toBeInTheDocument();
    expect(getByTestId("session-banner")).toBeInTheDocument();
    expect(getByTestId("week-today")).toBeInTheDocument();

    await user.click(getByTestId("load-btn"));
    await waitFor(() => {
      expect(getByTestId("week-view")).toBeInTheDocument();
    });

    await user.click(getByTestId("view-month"));
    expect(getByTestId("month-calendar-view")).toBeInTheDocument();
    unmount();
  });

  it("shows expired-session banner and keeps schedule editor draft at mobile width", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 375,
    });
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
    const { getByTestId, unmount } = render(<App client={client} />);

    await user.click(getByTestId("load-btn"));
    await waitFor(() => {
      expect(getByTestId("week-view")).toBeInTheDocument();
    });
    await user.click(getByTestId("view-month"));
    await waitFor(() => {
      expect(getByTestId("month-calendar-view")).toBeInTheDocument();
    });
    // Mobile hides in-cell chips — select day then open focus chip.
    await user.click(getByTestId("calendar-day-2026-07-20"));
    await waitFor(() => {
      expect(getByTestId("month-focus-chip")).toBeInTheDocument();
    });
    await user.click(getByTestId("month-focus-chip"));
    await waitFor(() => {
      expect(getByTestId("interim-event-panel")).toBeInTheDocument();
    });
    await user.click(getByTestId("row-defer"));
    await waitFor(() => {
      expect(getByTestId("schedule-editor-panel")).toBeInTheDocument();
    });
    const datetime = getByTestId("schedule-datetime") as HTMLInputElement;
    await user.clear(datetime);
    await user.type(datetime, "2026-09-01T09:00:00");

    allowReads = false;
    await user.click(getByTestId("load-btn"));
    await waitFor(() => {
      expect(getByTestId("session-banner").textContent).toMatch(/Session expired/i);
    });
    expect(getByTestId("schedule-editor-panel")).toBeInTheDocument();
    expect(
      (getByTestId("schedule-datetime") as HTMLInputElement).value,
    ).toContain("2026-09-01");
    expect(getByTestId("sign-in-btn")).toBeInTheDocument();
    expect(getByTestId("schedule-submit")).toBeDisabled();
    unmount();
  });
});
