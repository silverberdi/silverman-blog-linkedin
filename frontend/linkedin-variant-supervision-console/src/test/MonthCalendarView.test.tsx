import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import App from "../App";
import {
  applyFilters,
  defaultFilters,
  linkedinItemId,
  normalizeScheduleItem,
  normalizeVariant,
  type ScheduleItem,
} from "../models/supervision";
import {
  buildMonthGrid,
  localDayKey,
  monthsCoveringLocalMonth,
  shiftMonth,
  utcDayKey,
} from "../models/dateHelpers";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityResponse,
} from "../api/types";

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
      draft_content: "Hello draft",
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
      item_id: "blog:blog-1",
      channel: "blog",
      campaign_id: "camp-1",
      variant_id: null,
      title: "Blog post",
      audience: "exec",
      scheduled_at_utc: "2026-07-19T11:00:00Z",
      publication_state: "planned",
      source_state: "planned",
      blocked: false,
      critical: false,
      linkedin_api_published: false,
      calendar_item_id: "blog-1",
    },
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
    {
      item_id: "linkedin:camp-1:failed-variant",
      channel: "linkedin",
      campaign_id: "camp-1",
      variant_id: "failed-variant",
      title: "failed",
      audience: "eng",
      scheduled_at_utc: "2026-07-21T09:00:00Z",
      publication_state: "failed",
      source_state: "failed",
      blocked: false,
      critical: true,
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

describe("dateHelpers local day bucketing (US-040I)", () => {
  it("keeps utcDayKey for diagnostics only", () => {
    expect(utcDayKey("2026-07-20T15:00:00Z")).toBe("2026-07-20");
    expect(utcDayKey("2026-07-31T23:59:59Z")).toBe("2026-07-31");
    expect(utcDayKey("2026-08-01T00:00:00Z")).toBe("2026-08-01");
  });

  it("buckets scheduled_at_utc onto operator-local calendar days", () => {
    // America/Chicago (CDT, UTC−5): 04:00Z is still previous local evening.
    expect(localDayKey("2026-07-20T04:00:00Z")).toBe("2026-07-19");
    expect(utcDayKey("2026-07-20T04:00:00Z")).toBe("2026-07-20");
    expect(localDayKey("2026-07-20T15:00:00Z")).toBe("2026-07-20");
  });

  it("builds a Sunday-start month grid with empty padding", () => {
    const grid = buildMonthGrid({ year: 2026, month: 7 });
    expect(grid.filter((d) => d !== null).length).toBe(31);
    expect(grid.length % 7).toBe(0);
    expect(shiftMonth({ year: 2026, month: 7 }, 1)).toEqual({
      year: 2026,
      month: 8,
    });
  });

  it("pads local month fetch windows across adjacent UTC months", () => {
    const months = monthsCoveringLocalMonth({ year: 2026, month: 7 });
    expect(months).toEqual([
      { year: 2026, month: 6 },
      { year: 2026, month: 7 },
      { year: 2026, month: 8 },
    ]);
  });
});

describe("shared model identity", () => {
  it("uses the same LinkedIn item id across pending and schedule normalization", () => {
    const pending = normalizeVariant(pendingPayload.variants[0]);
    const schedule = normalizeScheduleItem(schedulePayload.items[1]);
    expect(pending.itemId).toBe(linkedinItemId("camp-1", "engineering-leadership"));
    expect(schedule.itemId).toBe(pending.itemId);
    expect(pending.campaignId).toBe(schedule.campaignId);
    expect(pending.variantId).toBe(schedule.variantId);
    expect(pending.scheduledAtUtc).toBe(schedule.scheduledAtUtc);
    expect(pending.publicationState).toBe(schedule.publicationState);
    expect(pending.statusColor).toBe(schedule.statusColor);
  });
});

describe("filters consistency", () => {
  it("applies channel filter the same way for list-shaped and calendar items", () => {
    const items: ScheduleItem[] = schedulePayload.items.map(normalizeScheduleItem);
    const linkedinOnly = applyFilters(items, {
      ...defaultFilters(),
      channel: "linkedin",
    });
    expect(linkedinOnly.every((i) => i.channel === "linkedin")).toBe(true);
    expect(linkedinOnly).toHaveLength(2);

    const failedOnly = applyFilters(items, {
      ...defaultFilters(),
      publicationStates: ["failed"],
    });
    expect(failedOnly).toHaveLength(1);
    expect(failedOnly[0].critical).toBe(true);
  });
});

describe("MonthCalendarView dual-view UX", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("navigates months, places items on local days, and focuses day chips", async () => {
    const client = createClient();
    const user = userEvent.setup();
    render(<App client={client} />);

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
    });

    expect(screen.getByTestId("calendar-tz-note").textContent).toMatch(
      /Local calendar date/,
    );
    expect(screen.getByTestId("calendar-tz-note").textContent).not.toMatch(
      /\(UTC\)/,
    );
    expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();

    const dayBtn = await screen.findByTestId("calendar-day-2026-07-20");
    expect(dayBtn.textContent).toMatch(/linkedin/i);
    await user.click(dayBtn);
    expect(dayBtn).toHaveClass("is-selected");
    expect(screen.queryByTestId("month-day-focus")).toBeNull();
    expect(screen.queryByTestId("month-day-chip-list")).toBeNull();
    expect(screen.queryByTestId("event-modal")).toBeNull();

    const emptyDay = screen.getByTestId("calendar-day-2026-07-05");
    await user.click(emptyDay);
    expect(emptyDay).toHaveClass("is-selected");
    expect(screen.queryByTestId("month-day-focus")).toBeNull();
    expect(screen.queryByTestId("event-modal")).toBeNull();

    await user.click(screen.getByTestId("calendar-next"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-month-label").textContent).toMatch(
        /August|2026/,
      );
    });
  });

  it("keeps filters when switching Week ↔ Month", async () => {
    const client = createClient();
    const user = userEvent.setup();
    render(<App client={client} />);

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("filters")).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByTestId("filter-channel"), "linkedin");
    await user.click(screen.getByTestId("view-month"));
    expect(screen.getByTestId("filter-channel")).toHaveValue("linkedin");

    await user.click(screen.getByTestId("view-week"));
    expect(screen.getByTestId("filter-channel")).toHaveValue("linkedin");
  });

  it("surfaces hidden critical failures when filters exclude them", async () => {
    const client = createClient();
    const user = userEvent.setup();
    render(<App client={client} />);

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("filters")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
    });

    // Filter to planned only — hides the failed critical item.
    const plannedCheckbox = screen.getByLabelText("Planned");
    await user.click(plannedCheckbox);

    await waitFor(() => {
      expect(screen.getByTestId("hidden-critical-banner")).toBeInTheDocument();
    });
    expect(screen.getByTestId("hidden-critical-banner").textContent).toMatch(
      /critical failure/,
    );
  });
});
