/**
 * US-084 — Postpone / reschedule LinkedIn variants (pending + queued) from console.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import { SupervisionStoreProvider } from "../models/store";
import { MonthCalendarView } from "../components/MonthCalendarView";
import { EventModal } from "../components/EventModal";
import { AppShell } from "../components/AppShell";
import { buildLinkedInActionMatrix } from "../models/actionAvailability";
import { explainErrorCodes } from "../api/errors";
import { LOCAL_DAY_FULL_MESSAGE } from "../models/localDayDensity";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityItemDto,
  ScheduleVisibilityResponse,
} from "../api/types";
import type { ScheduleItem } from "../models/supervision";

const ITEM_ID = "linkedin:camp-1:v1";
const OLD_UTC = "2026-07-20T15:00:00Z";
/** Local 2026-07-28T14:00 in America/Chicago (test TZ) → 19:00Z. */
const NEW_LOCAL = "2026-07-28T14:00:00";
const NEW_UTC_CHICAGO = "2026-07-28T19:00:00Z";

function scheduleItem(
  partial: Partial<ScheduleItem> & Pick<ScheduleItem, "itemId">,
): ScheduleItem {
  return {
    channel: "linkedin",
    campaignId: "camp-1",
    variantId: "v1",
    title: "Post",
    audience: "eng",
    scheduledAtUtc: OLD_UTC,
    publicationState: "pending",
    sourceState: "pending",
    blocked: false,
    critical: false,
    linkedinApiPublished: false,
    linkedinPostUrn: null,
    calendarItemId: null,
    scheduleEditable: true,
    scheduleEditBlockReason: null,
    cancelledAtUtc: null,
    cancellationPhase: null,
    cancellationReason: null,
    reopenEligible: false,
    cadenceConflict: false,
    cadenceConflictCode: null,
    cadenceEarliestFeasibleAtUtc: null,
    actions: ["edit", "defer", "cancel"],
    statusColor: "#888",
    ...partial,
  };
}

function baseScheduleItem(
  overrides: Partial<ScheduleVisibilityItemDto> = {},
): ScheduleVisibilityItemDto {
  return {
    item_id: ITEM_ID,
    channel: "linkedin",
    campaign_id: "camp-1",
    variant_id: "v1",
    title: "Postpone target",
    audience: "eng",
    scheduled_at_utc: OLD_UTC,
    publication_state: "pending",
    source_state: "pending",
    blocked: false,
    critical: false,
    linkedin_api_published: false,
    schedule_editable: true,
    schedule_edit_block_reason: null,
    ...overrides,
  };
}

describe("US-084 action matrix and refusal copy", () => {
  it("deliberate postpone label for pending and queued when editable", () => {
    for (const state of ["pending", "queued"] as const) {
      const rows = buildLinkedInActionMatrix({
        item: scheduleItem({
          itemId: `li-${state}`,
          publicationState: state,
          scheduleEditable: true,
          actions: state === "pending" ? ["edit", "defer", "cancel"] : [],
        }),
        hasSupervisionJoin: state === "pending",
        canMutate: true,
      });
      const reschedule = rows.find((r) => r.id === "reschedule");
      expect(reschedule?.available).toBe(true);
      expect(reschedule?.label).toBe("Postpone / reschedule");
      expect(reschedule?.reason).toMatch(/Preview \(no change\)|Make real change/i);
    }
  });

  it("density refusal includes usable next step", () => {
    expect(LOCAL_DAY_FULL_MESSAGE).toMatch(/Choose another local day/i);
    expect(explainErrorCodes(["linkedin_supervision_local_day_density"])).toMatch(
      /Choose another local day with capacity/i,
    );
    expect(explainErrorCodes(["linkedin_supervision_defer_time_invalid"])).toMatch(
      /future time/i,
    );
    expect(explainErrorCodes(["linkedin_supervision_defer_saturation"])).toMatch(
      /Choose a different day/i,
    );
  });

  it("keeps cancel-queued and publish-now available as distinct controls (US-085 / US-086)", () => {
    const rows = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-queued",
        publicationState: "queued",
        scheduleEditable: true,
        actions: [],
      }),
      hasSupervisionJoin: false,
      canMutate: true,
    });
    expect(rows.find((r) => r.id === "cancel_queued")?.available).toBe(true);
    expect(rows.find((r) => r.id === "publish_now")?.available).toBe(true);
    expect(rows.find((r) => r.id === "reschedule")?.available).toBe(true);
  });
});

describe("US-084 calendar agreement after real postpone", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-07-19T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function makeClient(opts: {
    publicationState: "pending" | "queued";
    mutateScheduleOnRefresh?: boolean;
  }) {
    let scheduledAt = OLD_UTC;
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-token");

    const pending: PendingSupervisionResponse = {
      status: "ok",
      observed_at_utc: "2026-07-18T12:00:00Z",
      read_only: false,
      linkedin_publication_enabled: false,
      variants:
        opts.publicationState === "pending"
          ? [
              {
                campaign_id: "camp-1",
                variant_id: "v1",
                audience: "eng",
                scheduled_at_utc: scheduledAt,
                publish_state: "pending",
                calendar_item_id: null,
                calendar_title: "Postpone target",
                calendar_due_at_utc: null,
                calendar_status: null,
                operator_supervision_last_action: null,
                auto_queue_eligible: true,
                operator_supervision_reason: null,
                draft_content: "Draft",
              },
            ]
          : [],
      issues: [],
      integration_failures: [],
    };

    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("pending-supervision")) {
        if (opts.publicationState === "pending" && pending.variants[0]) {
          pending.variants[0] = {
            ...pending.variants[0],
            scheduled_at_utc: scheduledAt,
          };
        }
        return new Response(JSON.stringify(pending), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("schedule-visibility")) {
        const schedule: ScheduleVisibilityResponse = {
          status: "ok",
          observed_at_utc: "2026-07-18T12:00:00Z",
          read_only: false,
          year: 2026,
          month: 7,
          from_utc: "2026-07-01T00:00:00Z",
          to_utc: "2026-07-31T23:59:59Z",
          linkedin_publication_enabled: false,
          calendar_fingerprint: "b".repeat(64),
          items: [
            baseScheduleItem({
              publication_state: opts.publicationState,
              source_state: opts.publicationState,
              scheduled_at_utc: scheduledAt,
            }),
          ],
          issues: [],
        };
        return new Response(JSON.stringify(schedule), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("defer-linkedin-variant")) {
        const body = JSON.parse(String(init?.body));
        if (!body.dry_run && opts.mutateScheduleOnRefresh !== false) {
          scheduledAt = body.new_scheduled_at_utc;
        }
        return new Response(
          JSON.stringify({
            status: "completed",
            campaign_id: "camp-1",
            variant: "v1",
            state: "distribution_scheduled",
            publish_state: opts.publicationState,
            dry_run: Boolean(body.dry_run),
            phase:
              opts.publicationState === "queued" ? "post_queue" : "pre_queue",
            scheduled_at_utc: body.new_scheduled_at_utc,
            errors: [],
            warnings: [],
            metadata_written: !body.dry_run,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("{}", { status: 404 });
    });

    return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
  }

  it("deliberate postpone control framing for Scheduled item", async () => {
    const user = userEvent.setup();
    const client = makeClient({ publicationState: "pending" });
    render(
      <SupervisionStoreProvider client={client}>
        <AppShell>
          <EventModal />
          <MonthCalendarView />
        </AppShell>
      </SupervisionStoreProvider>,
    );
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-day-2026-07-20")).toBeInTheDocument();
    });
    const oldDay = screen.getByTestId("calendar-day-2026-07-20");
    await user.click(
      within(oldDay).getByTestId("schedule-open-month"),
    );
    expect(screen.getByTestId("row-defer")).toHaveTextContent(
      /Postpone \/ reschedule/i,
    );
    await user.click(screen.getByTestId("row-defer"));
    expect(screen.getByTestId("postpone-control-framing")).toBeInTheDocument();
    expect(screen.getByTestId("schedule-mode-banner").textContent).toMatch(
      /Preview/i,
    );
    expect(screen.getByTestId("schedule-submit")).toHaveTextContent(
      /Preview \(no change\)/i,
    );
  });

  it("preview postpone does not move Month placement", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const client = makeClient({
      publicationState: "queued",
      mutateScheduleOnRefresh: false,
    });
    render(
      <SupervisionStoreProvider client={client}>
        <AppShell>
          <EventModal />
          <MonthCalendarView />
        </AppShell>
      </SupervisionStoreProvider>,
    );
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(
        within(screen.getByTestId("calendar-day-2026-07-20")).getByTestId(
          "schedule-open-month",
        ),
      ).toBeInTheDocument();
    });
    await user.click(
      within(screen.getByTestId("calendar-day-2026-07-20")).getByTestId(
        "schedule-open-month",
      ),
    );
    await user.click(screen.getByTestId("row-defer"));
    await user.clear(screen.getByTestId("schedule-datetime"));
    await user.type(screen.getByTestId("schedule-datetime"), NEW_LOCAL);
    await user.click(screen.getByTestId("schedule-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast").textContent).toMatch(
        /Schedule was not saved/i,
      );
    });
    expect(
      within(screen.getByTestId("calendar-day-2026-07-20")).queryByTestId(
        "schedule-open-month",
      ),
    ).toBeTruthy();
    expect(
      screen.queryByTestId("calendar-day-2026-07-28")?.textContent,
    ).not.toMatch(/Postpone target/);
  });

  it("real postpone moves Month placement to new local day (pending)", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const client = makeClient({ publicationState: "pending" });
    render(
      <SupervisionStoreProvider client={client}>
        <AppShell>
          <EventModal />
          <MonthCalendarView />
        </AppShell>
      </SupervisionStoreProvider>,
    );
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(
        within(screen.getByTestId("calendar-day-2026-07-20")).getByTestId(
          "schedule-open-month",
        ),
      ).toBeInTheDocument();
    });
    await user.click(
      within(screen.getByTestId("calendar-day-2026-07-20")).getByTestId(
        "schedule-open-month",
      ),
    );
    await user.click(screen.getByTestId("row-defer"));
    await user.click(screen.getByTestId("schedule-dry-run"));
    expect(screen.getByTestId("schedule-submit")).toHaveTextContent(
      /Make real change/i,
    );
    await user.clear(screen.getByTestId("schedule-datetime"));
    await user.type(screen.getByTestId("schedule-datetime"), NEW_LOCAL);
    await user.click(screen.getByTestId("schedule-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast").textContent).toMatch(/^Saved:/);
      expect(screen.getByTestId("toast").textContent).toMatch(NEW_UTC_CHICAGO);
    });
    await waitFor(() => {
      expect(
        within(screen.getByTestId("calendar-day-2026-07-28")).getByTestId(
          "schedule-open-month",
        ),
      ).toBeInTheDocument();
    });
    expect(
      within(screen.getByTestId("calendar-day-2026-07-20")).queryByTestId(
        "schedule-open-month",
      ),
    ).toBeNull();
  });

  it("real postpone for queued also moves Month placement", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const client = makeClient({ publicationState: "queued" });
    render(
      <SupervisionStoreProvider client={client}>
        <AppShell>
          <EventModal />
          <MonthCalendarView />
        </AppShell>
      </SupervisionStoreProvider>,
    );
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(
        within(screen.getByTestId("calendar-day-2026-07-20")).getByTestId(
          "schedule-open-month",
        ),
      ).toBeInTheDocument();
    });
    await user.click(
      within(screen.getByTestId("calendar-day-2026-07-20")).getByTestId(
        "schedule-open-month",
      ),
    );
    await user.click(screen.getByTestId("row-defer"));
    await user.click(screen.getByTestId("schedule-dry-run"));
    await user.clear(screen.getByTestId("schedule-datetime"));
    await user.type(screen.getByTestId("schedule-datetime"), NEW_LOCAL);
    await user.click(screen.getByTestId("schedule-submit"));
    await waitFor(() => {
      expect(
        within(screen.getByTestId("calendar-day-2026-07-28")).getByTestId(
          "schedule-open-month",
        ),
      ).toBeInTheDocument();
    });
  });
});
