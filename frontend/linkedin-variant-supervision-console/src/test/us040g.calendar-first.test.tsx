import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import {
  buildWeekDayKeys,
  currentUtcWeek,
  sundayUtcWeekStart,
  todayUtcDayKey,
} from "../models/dateHelpers";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityResponse,
} from "../api/types";

function makeClient(scheduleItems: ScheduleVisibilityResponse["items"]) {
  const auth = new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-key");
  const pending: PendingSupervisionResponse = {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    linkedin_publication_enabled: false,
    variants: scheduleItems
      .filter((i) => i.channel === "linkedin" && i.variant_id)
      .map((i) => ({
        campaign_id: i.campaign_id!,
        variant_id: i.variant_id!,
        audience: i.audience,
        scheduled_at_utc: i.scheduled_at_utc,
        publish_state: "pending",
        calendar_item_id: i.calendar_item_id,
        calendar_title: i.title,
        calendar_due_at_utc: i.scheduled_at_utc,
        calendar_status: "planned",
        operator_supervision_last_action: null,
        auto_queue_eligible: true,
        operator_supervision_reason: null,
        draft_content: "Draft",
      })),
    issues: [],
    integration_failures: [],
  };
  const schedule: ScheduleVisibilityResponse = {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    year: 2026,
    month: 7,
    from_utc: "2026-07-01T00:00:00Z",
    to_utc: "2026-07-31T23:59:59Z",
    linkedin_publication_enabled: false,
    items: scheduleItems,
    issues: [],
  };
  const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes("pending-supervision")) {
      return new Response(JSON.stringify(pending), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("schedule-visibility")) {
      return new Response(JSON.stringify(schedule), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response("not found", { status: 404 });
  });
  return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
}

/**
 * US-040G Vitest viewport / Visual DoD scene matrix (implementation evidence).
 * Does NOT mark Story accepted — browser Visual DoD + walkthrough remain gated.
 */
describe("US-040G calendar-first Week + Month", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const todayKey = todayUtcDayKey();
  const weekStart = sundayUtcWeekStart(todayKey);
  const weekDays = buildWeekDayKeys(weekStart);

  const denseItems: ScheduleVisibilityResponse["items"] = weekDays.flatMap(
    (day, i) => [
      {
        item_id: `linkedin:camp:dense-${day}-a`,
        channel: "linkedin" as const,
        campaign_id: "camp",
        variant_id: `dense-${day}-a`,
        title: `Dense A ${day}`,
        audience: "eng",
        scheduled_at_utc: `${day}T10:00:00Z`,
        publication_state: i === 0 ? "blocked" : "pending",
        source_state: "pending",
        blocked: i === 0,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
      },
      {
        item_id: `linkedin:camp:dense-${day}-b`,
        channel: "linkedin" as const,
        campaign_id: "camp",
        variant_id: `dense-${day}-b`,
        title: `Dense B ${day}`,
        audience: "eng",
        scheduled_at_utc: `${day}T15:00:00Z`,
        publication_state: "pending",
        source_state: "pending",
        blocked: false,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
      },
    ],
  );

  async function assertAtWidths(
    run: (width: number) => Promise<void>,
  ): Promise<void> {
    for (const width of [1280, 375]) {
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        value: width,
      });
      await run(width);
    }
  }

  it("defaults to Week with Week|Month switcher and no List chrome", async () => {
    await assertAtWidths(async () => {
      const user = userEvent.setup();
      const { unmount } = render(<App client={makeClient(denseItems)} />);
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
      expect(screen.getByTestId("view-week")).toHaveAttribute(
        "aria-selected",
        "true",
      );
      expect(screen.getByTestId("view-month")).toBeInTheDocument();
      expect(screen.queryByTestId("view-list")).toBeNull();
      expect(screen.queryByTestId("list-view")).toBeNull();
      expect(screen.getByTestId("week-today")).toBeInTheDocument();

      await user.click(screen.getByTestId("view-month"));
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
      expect(screen.queryByTestId("list-view")).toBeNull();
      unmount();
    });
  });

  it("shows empty week/month intentional states and Today control", async () => {
    await assertAtWidths(async () => {
      const user = userEvent.setup();
      const { unmount } = render(<App client={makeClient([])} />);
      await user.click(screen.getByTestId("load-btn"));
      await waitFor(() => {
        expect(screen.getByTestId("week-empty-state")).toBeInTheDocument();
      });
      expect(screen.getByTestId("week-empty-state").textContent).toMatch(
        /No publications this week/,
      );
      await user.click(screen.getByTestId("week-today"));
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
      expect(currentUtcWeek().weekStartKey).toBe(weekStart);

      await user.click(screen.getByTestId("view-month"));
      await waitFor(() => {
        expect(screen.getByTestId("month-empty-state")).toBeInTheDocument();
      });
      expect(screen.getByTestId("month-empty-state").textContent).toMatch(
        /No publications this month/,
      );
      unmount();
    });
  });

  it("renders dense week chips and opens interim actions; metrics stay on calendar", async () => {
    await assertAtWidths(async () => {
      const user = userEvent.setup();
      const { unmount } = render(<App client={makeClient(denseItems)} />);
      await user.click(screen.getByTestId("load-btn"));
      await waitFor(() => {
        expect(
          screen.getAllByTestId("week-event-chip").length,
        ).toBeGreaterThan(0);
      });
      expect(screen.getByTestId("week-columns")).toBeInTheDocument();
      expect(document.querySelector(".week-day-column.is-today")).not.toBeNull();

      await user.click(screen.getAllByTestId("week-event-chip")[0]);
      await waitFor(() => {
        expect(screen.getByTestId("interim-event-panel")).toBeInTheDocument();
      });
      expect(screen.getByTestId("interim-h-hint").textContent).toMatch(/US-040H/);
      expect(screen.queryByTestId("list-view")).toBeNull();

      await user.click(screen.getByTestId("interim-close"));
      await user.click(screen.getByTestId("count-blocked"));
      expect(screen.getByTestId("filter-blocked")).toBeChecked();
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
      expect(screen.queryByTestId("list-view")).toBeNull();

      await user.click(screen.getByTestId("view-month"));
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
      expect(
        screen.queryAllByTestId("schedule-open-month").length,
      ).toBeGreaterThan(0);
      unmount();
    });
  });
});
