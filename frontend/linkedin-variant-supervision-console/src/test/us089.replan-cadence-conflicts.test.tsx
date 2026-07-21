/**
 * US-089 — console replan cadence conflicts (implementation evidence).
 * Does NOT mark Story accepted.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import type {
  PendingSupervisionResponse,
  ReplanCadenceConflictsResult,
  ScheduleVisibilityItemDto,
  ScheduleVisibilityResponse,
} from "../api/types";
import { currentLocalWeek } from "../models/dateHelpers";

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
    cadence_conflict: true,
    cadence_conflict_code: "linkedin_publish_blocked_cadence",
    cadence_earliest_feasible_at_utc: "2026-07-23T12:00:00Z",
    ...overrides,
  };
}

function makeClient(options: {
  initialItems: ScheduleVisibilityItemDto[];
  afterReplanItems?: ScheduleVisibilityItemDto[];
  replanImpl?: (
    body: unknown,
  ) => Promise<ReplanCadenceConflictsResult>;
}) {
  let items = options.initialItems;
  const pending = (): PendingSupervisionResponse => ({
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    linkedin_publication_enabled: true,
    variants: items
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
  });
  const schedule = (): ScheduleVisibilityResponse => {
    const week = currentLocalWeek();
    return {
      status: "ok",
      observed_at_utc: "2026-07-18T12:00:00Z",
      read_only: true,
      year: week.year,
      month: week.month,
      from_utc: "2026-07-01T00:00:00Z",
      to_utc: "2026-07-31T23:59:59Z",
      linkedin_publication_enabled: true,
      items,
      issues: [],
    };
  };
  const auth = new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-token");
  const replanCalls: unknown[] = [];
  const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("pending-supervision")) {
      return new Response(JSON.stringify(pending()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("schedule-visibility")) {
      return new Response(JSON.stringify(schedule()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("replan-linkedin-cadence-conflicts")) {
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      replanCalls.push(body);
      const result = options.replanImpl
        ? await options.replanImpl(body)
        : ({
            status: "completed",
            dry_run: body.dry_run !== false,
            metadata_written: body.dry_run === false,
            targets: [
              {
                campaign_id: "camp-1",
                variant_id: "v1",
                previous_scheduled_at_utc: items[0]?.scheduled_at_utc,
                proposed_scheduled_at_utc: weekAnchoredIso(3),
                outcome: "moved",
                errors: [],
              },
            ],
            errors: [],
            warnings: [],
          } satisfies ReplanCadenceConflictsResult);
      if (body.dry_run === false && options.afterReplanItems) {
        items = options.afterReplanItems;
      }
      return new Response(JSON.stringify(result), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    return new Response("{}", { status: 404 });
  });
  const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
  return { client, replanCalls };
}

describe("US-089 EventModal replan cadence conflicts", () => {
  it("preview does not claim Live and does not move chips", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 1280,
    });
    const user = userEvent.setup();
    const conflicted = baseItem();
    const { client, replanCalls } = makeClient({ initialItems: [conflicted] });
    render(<App client={client} />);
    await waitFor(() => {
      expect(screen.getByTestId("week-event-chip")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("week-event-chip"));
    await waitFor(() => {
      expect(screen.getByTestId("event-modal-cadence-replan")).toBeInTheDocument();
    });
    const banner = screen.getByTestId("event-modal-cadence-conflict");
    expect(banner.textContent).not.toMatch(/wait for a later replan/i);
    expect(banner).toHaveTextContent(/Replan cadence conflicts/i);

    const checkbox = screen.getByTestId("replan-dry-run");
    expect(checkbox).toBeChecked();
    await user.click(screen.getByTestId("row-replan-cadence"));
    await waitFor(() => {
      expect(replanCalls.length).toBe(1);
    });
    expect(replanCalls[0]).toMatchObject({ dry_run: true });
    // Preview: chip still conflicted at old placement.
    expect(
      within(screen.getByTestId("week-event-chip")).getByTestId(
        "cadence-conflict-indicator",
      ),
    ).toBeInTheDocument();
  });

  it("real replan refreshes and clears conflict indicator when feasible", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 1280,
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    const conflicted = baseItem();
    const cleared = baseItem({
      scheduled_at_utc: weekAnchoredIso(3),
      cadence_conflict: false,
      cadence_conflict_code: null,
      cadence_earliest_feasible_at_utc: null,
    });
    const { client, replanCalls } = makeClient({
      initialItems: [conflicted],
      afterReplanItems: [cleared],
    });
    render(<App client={client} />);
    await waitFor(() => {
      expect(screen.getByTestId("week-event-chip")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("week-event-chip"));
    await waitFor(() => {
      expect(screen.getByTestId("replan-dry-run")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("replan-dry-run"));
    expect(screen.getByTestId("replan-dry-run")).not.toBeChecked();
    await user.click(screen.getByTestId("row-replan-cadence"));
    await waitFor(() => {
      expect(replanCalls.some((c) => (c as { dry_run?: boolean }).dry_run === false)).toBe(
        true,
      );
    });
    await waitFor(() => {
      expect(screen.queryByTestId("event-modal")).toBeNull();
    });
    await waitFor(() => {
      const chip = screen.getByTestId("week-event-chip");
      expect(
        within(chip).queryByTestId("cadence-conflict-indicator"),
      ).toBeNull();
    });
  });
});
