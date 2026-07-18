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
 * Desktop + mobile viewport validation evidence for List + Month calendar.
 */
describe("viewport validation", () => {
  const cssPath = resolve(__dirname, "../styles/console.css");
  const css = readFileSync(cssPath, "utf-8");

  it("includes mobile media query for list cards and calendar agenda patterns", () => {
    expect(css).toMatch(/@media\s*\(max-width:\s*720px\)/);
    expect(css).toMatch(/main\.console-shell/);
    expect(css).toMatch(/\.table-wrap/);
    expect(css).toMatch(/\.list-mobile-cards/);
    expect(css).toMatch(/\.calendar-agenda/);
    expect(css).toMatch(/\.calendar-grid/);
    expect(css).toMatch(/--bg:\s*#12151a/);
  });

  it("renders list and month calendar at desktop viewport width", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 1280,
    });
    const user = userEvent.setup();
    const { getByTestId, unmount } = render(<App client={createClient()} />);
    expect(getByTestId("app-shell")).toBeInTheDocument();
    expect(getByTestId("list-view")).toBeInTheDocument();
    expect(getByTestId("view-list")).toBeInTheDocument();
    expect(getByTestId("view-calendar")).toBeInTheDocument();

    await user.click(getByTestId("view-calendar"));
    expect(getByTestId("month-calendar-view")).toBeInTheDocument();
    expect(getByTestId("calendar-agenda")).toBeInTheDocument();
    unmount();
  });

  it("renders list and month calendar at mobile viewport width with agenda", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      value: 375,
    });
    const user = userEvent.setup();
    const { getByTestId, unmount } = render(<App client={createClient()} />);
    expect(getByTestId("app-shell")).toBeInTheDocument();
    expect(getByTestId("list-view")).toBeInTheDocument();
    expect(getByTestId("load-btn")).toBeInTheDocument();

    await user.click(getByTestId("load-btn"));
    await waitFor(() => {
      expect(getByTestId("list-mobile-cards")).toBeInTheDocument();
    });

    await user.click(getByTestId("view-calendar"));
    expect(getByTestId("month-calendar-view")).toBeInTheDocument();
    expect(screen.getByTestId("calendar-agenda")).toBeInTheDocument();
    unmount();
  });
});
