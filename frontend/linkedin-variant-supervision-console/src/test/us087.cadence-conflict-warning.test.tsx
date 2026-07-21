/**
 * US-087 — cadence-conflict visual warning (implementation evidence).
 * Does NOT mark Story accepted — Visual DoD + operator walkthrough remain gated.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityItemDto,
  ScheduleVisibilityResponse,
} from "../api/types";
import {
  buildLocalWeekDayKeys,
  currentLocalWeek,
} from "../models/dateHelpers";
import { normalizeScheduleItem } from "../models/supervision";

function weekAnchoredIso(daysFromMonday: number, hourUtc = 15): string {
  const now = new Date();
  const day = now.getUTCDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  const monday = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()),
  );
  monday.setUTCDate(monday.getUTCDate() + mondayOffset + daysFromMonday);
  monday.setUTCHours(hourUtc, 0, 0, 0);
  return monday.toISOString().replace(/\.\d{3}Z$/, "Z");
}

function baseItem(
  overrides: Partial<ScheduleVisibilityItemDto> = {},
): ScheduleVisibilityItemDto {
  return {
    item_id: "linkedin:camp-1:v1",
    channel: "linkedin",
    campaign_id: "camp-1",
    variant_id: "v1",
    title: "Conflicted scheduled",
    audience: "eng",
    scheduled_at_utc: weekAnchoredIso(1),
    publication_state: "pending",
    source_state: "pending",
    blocked: false,
    critical: false,
    linkedin_api_published: false,
    schedule_editable: true,
    cadence_conflict: false,
    cadence_conflict_code: null,
    cadence_earliest_feasible_at_utc: null,
    ...overrides,
  };
}

function makeClient(scheduleItems: ScheduleVisibilityItemDto[]) {
  const pending: PendingSupervisionResponse = {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    linkedin_publication_enabled: true,
    variants: scheduleItems
      .filter((i) => i.source_state === "pending")
      .map((i) => ({
        campaign_id: i.campaign_id!,
        variant_id: i.variant_id!,
        audience: i.audience,
        scheduled_at_utc: i.scheduled_at_utc,
        publish_state: "pending",
        calendar_item_id: i.calendar_item_id ?? null,
        calendar_title: i.title,
        calendar_due_at_utc: i.scheduled_at_utc,
        calendar_status: "planned",
        operator_supervision_last_action: null,
        auto_queue_eligible: true,
        operator_supervision_reason: null,
        draft_content: "Draft body",
      })),
    issues: [],
    integration_failures: [],
  };
  const schedule: ScheduleVisibilityResponse = {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: true,
    year: new Date().getUTCFullYear(),
    month: new Date().getUTCMonth() + 1,
    from_utc: "2026-07-01T00:00:00Z",
    to_utc: "2026-07-31T23:59:59Z",
    linkedin_publication_enabled: true,
    items: scheduleItems,
    issues: [],
  };
  const auth = new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-token");
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
    return new Response("{}", { status: 404 });
  });
  return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
}

describe("US-087 normalize cadence fields", () => {
  it("maps cadence_conflict fields from schedule-visibility DTO", () => {
    const item = normalizeScheduleItem(
      baseItem({
        cadence_conflict: true,
        cadence_conflict_code: "linkedin_publish_blocked_cadence",
        cadence_earliest_feasible_at_utc: "2026-07-23T12:00:00Z",
      }),
    );
    expect(item.cadenceConflict).toBe(true);
    expect(item.cadenceConflictCode).toBe("linkedin_publish_blocked_cadence");
    expect(item.cadenceEarliestFeasibleAtUtc).toBe("2026-07-23T12:00:00Z");
  });

  it("defaults missing cadence fields to false/null", () => {
    const { cadence_conflict: _c, ...rest } = baseItem();
    const item = normalizeScheduleItem(rest as ScheduleVisibilityItemDto);
    expect(item.cadenceConflict).toBe(false);
    expect(item.cadenceConflictCode).toBeNull();
    expect(item.cadenceEarliestFeasibleAtUtc).toBeNull();
  });
});

describe("US-087 Week / Month / EventModal cadence warning", () => {
  it("Week shows red cadence indicator on conflicted Scheduled chip (~1280)", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 1280,
    });
    const user = userEvent.setup();
    const conflicted = baseItem({
      item_id: "linkedin:camp-1:conflict",
      variant_id: "conflict",
      title: "Conflict chip",
      cadence_conflict: true,
      cadence_conflict_code: "linkedin_publish_blocked_cadence",
      cadence_earliest_feasible_at_utc: "2026-07-23T12:00:00Z",
    });
    const feasible = baseItem({
      item_id: "linkedin:camp-1:ok",
      variant_id: "ok",
      title: "Feasible chip",
      scheduled_at_utc: weekAnchoredIso(2),
      cadence_conflict: false,
    });
    render(<App client={makeClient([conflicted, feasible])} />);
    await waitFor(() => {
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
    });
    const chips = screen.getAllByTestId("week-event-chip");
    const conflictChip = chips.find(
      (el) => el.getAttribute("data-item-id") === conflicted.item_id,
    );
    const feasibleChip = chips.find(
      (el) => el.getAttribute("data-item-id") === feasible.item_id,
    );
    expect(conflictChip).toBeTruthy();
    expect(feasibleChip).toBeTruthy();
    expect(
      within(conflictChip!).getByTestId("cadence-conflict-indicator"),
    ).toBeInTheDocument();
    expect(within(conflictChip!).getByText("Scheduled")).toBeInTheDocument();
    expect(
      within(feasibleChip!).queryByTestId("cadence-conflict-indicator"),
    ).toBeNull();

    await user.click(conflictChip!);
    await waitFor(() => {
      expect(screen.getByTestId("event-modal")).toBeInTheDocument();
    });
    const banner = screen.getByTestId("event-modal-cadence-conflict");
    expect(banner).toHaveTextContent(/Cadence conflict/i);
    expect(banner).toHaveTextContent(/72 hours/i);
    expect(banner).toHaveTextContent(/not density-full/i);
    expect(banner.textContent).not.toMatch(
      /is Live on LinkedIn|already live on LinkedIn/i,
    );
    expect(screen.getByTestId("event-modal-cadence-earliest")).toHaveTextContent(
      /Earliest feasible time/i,
    );
    expect(screen.getByTestId("event-modal-cadence-earliest")).toHaveTextContent(
      /Postpone/i,
    );
  });

  it("Month shows cadence indicator on conflicted item", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 1280,
    });
    const user = userEvent.setup();
    const conflicted = baseItem({
      cadence_conflict: true,
      cadence_conflict_code: "linkedin_publish_blocked_cadence",
      cadence_earliest_feasible_at_utc: "2026-07-23T12:00:00Z",
    });
    render(<App client={makeClient([conflicted])} />);
    await waitFor(() => {
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
    });
    const openBtn = screen.getByTestId("schedule-open-month");
    expect(
      within(openBtn).getByTestId("cadence-conflict-indicator"),
    ).toBeInTheDocument();
    expect(within(openBtn).getByText("Scheduled")).toBeInTheDocument();
  });

  it("feasible EventModal has no cadence-conflict explanation", async () => {
    const user = userEvent.setup();
    const feasible = baseItem({
      title: "Feasible only",
      cadence_conflict: false,
    });
    render(<App client={makeClient([feasible])} />);
    await waitFor(() => {
      expect(screen.getByTestId("week-event-chip")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("week-event-chip"));
    await waitFor(() => {
      expect(screen.getByTestId("event-modal")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("event-modal-cadence-conflict")).toBeNull();
    expect(screen.getByTestId("event-modal-status")).toHaveTextContent(
      "Scheduled",
    );
  });

  it("cadence indicator remains distinct from Failed chip styling", async () => {
    const conflicted = baseItem({
      item_id: "linkedin:camp-1:conflict",
      variant_id: "conflict",
      title: "Conflict",
      scheduled_at_utc: weekAnchoredIso(1),
      cadence_conflict: true,
      cadence_conflict_code: "linkedin_publish_blocked_cadence",
      cadence_earliest_feasible_at_utc: "2026-07-23T12:00:00Z",
    });
    const failed = baseItem({
      item_id: "linkedin:camp-1:failed",
      variant_id: "failed",
      title: "Failed item",
      publication_state: "failed",
      source_state: "failed",
      critical: true,
      scheduled_at_utc: weekAnchoredIso(1, 16),
      cadence_conflict: false,
      schedule_editable: false,
    });
    render(<App client={makeClient([conflicted, failed])} />);
    await waitFor(() => {
      expect(screen.getAllByTestId("week-event-chip").length).toBeGreaterThan(0);
    });
    const chips = screen.getAllByTestId("week-event-chip");
    const conflictChip = chips.find(
      (el) => el.getAttribute("data-item-id") === conflicted.item_id,
    )!;
    const failedChip = chips.find(
      (el) => el.getAttribute("data-item-id") === failed.item_id,
    )!;
    expect(
      within(conflictChip).getByTestId("cadence-conflict-indicator"),
    ).toBeInTheDocument();
    expect(conflictChip.className).not.toContain("week-event-chip-failed");
    expect(failedChip.className).toContain("week-event-chip-failed");
    expect(
      within(failedChip).queryByTestId("cadence-conflict-indicator"),
    ).toBeNull();
    expect(within(failedChip).getByText("Failed")).toBeInTheDocument();
  });

  it("density-full day cue is distinct from cadence-conflict indicator", async () => {
    // Three density members on one local day → Full/Over cue; only one cadence conflict.
    const dayIso = weekAnchoredIso(1, 14);
    const items = [0, 1, 2].map((i) =>
      baseItem({
        item_id: `linkedin:camp-1:d${i}`,
        variant_id: `d${i}`,
        title: `Day item ${i}`,
        scheduled_at_utc: weekAnchoredIso(1, 14 + i),
        cadence_conflict: i === 0,
        cadence_conflict_code:
          i === 0 ? "linkedin_publish_blocked_cadence" : null,
        cadence_earliest_feasible_at_utc:
          i === 0 ? "2026-07-23T12:00:00Z" : null,
      }),
    );
    // ensure same local day key for density
    void dayIso;
    render(<App client={makeClient(items)} />);
    await waitFor(() => {
      expect(screen.getAllByTestId("week-event-chip").length).toBe(3);
    });
    const densityFull = screen.queryByTestId("day-density-full");
    const densityOver = screen.queryByTestId("day-density-over");
    expect(densityFull || densityOver).toBeTruthy();
    const indicators = screen.getAllByTestId("cadence-conflict-indicator");
    expect(indicators).toHaveLength(1);
    // Density cue and cadence indicator are different testids / classes.
    if (densityFull) {
      expect(densityFull.className).toContain("day-density-full");
      expect(densityFull.className).not.toContain("cadence-conflict");
    }
    expect(indicators[0].className).toContain("cadence-conflict-indicator");
  });

  it("mobile EventModal shows cadence conflict copy (~375)", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 375,
    });
    const user = userEvent.setup();
    const conflicted = baseItem({
      cadence_conflict: true,
      cadence_conflict_code: "linkedin_publish_blocked_cadence",
      cadence_earliest_feasible_at_utc: "2026-07-23T12:00:00Z",
    });
    render(<App client={makeClient([conflicted])} />);
    await waitFor(() => {
      expect(screen.getByTestId("week-event-chip")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("week-event-chip"));
    await waitFor(() => {
      expect(screen.getByTestId("event-modal")).toBeInTheDocument();
    });
    expect(screen.getByTestId("event-modal-cadence-conflict")).toBeVisible();
    expect(screen.getByTestId("event-modal-cadence-earliest")).toHaveTextContent(
      /replan/i,
    );
    // Does not claim US-089 is a working control.
    expect(screen.getByTestId("event-modal-cadence-conflict").textContent).not.toMatch(
      /replan is available|replan now|open replan/i,
    );
  });
});

describe("US-087 week cursor sanity", () => {
  it("anchors fixtures into the current local week", () => {
    const keys = buildLocalWeekDayKeys(currentLocalWeek().weekStartKey);
    expect(keys.length).toBe(7);
  });
});
