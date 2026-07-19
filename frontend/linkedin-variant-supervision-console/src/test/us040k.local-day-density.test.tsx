/**
 * US-040K — local-day density UX (implementation evidence).
 * Does NOT mark Story accepted — Visual DoD + operator walkthrough remain gated.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import {
  explainErrorCodes,
  explainErrorCodesPlain,
  SUPERVISION_ERROR_MESSAGES,
} from "../api/errors";
import {
  datetimeLocalToUtcIso,
  utcIsoToDatetimeLocal,
} from "../components/ScheduleEditor";
import {
  buildLocalWeekDayKeys,
  currentLocalWeek,
  localDayKey,
} from "../models/dateHelpers";
import {
  countDensityOnLocalDay,
  densityCueLevel,
  excludeForScheduleItem,
  isDensityMember,
  isLocalDayFull,
  LOCAL_DAY_FULL_MESSAGE,
  othersOnLocalDay,
} from "../models/localDayDensity";
import { normalizeScheduleItem, type ScheduleItem } from "../models/supervision";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityResponse,
} from "../api/types";

const NEAR_MIDNIGHT_UTC = "2026-07-20T04:00:00Z"; // Chicago CDT → local 2026-07-19 23:00

function dayInCurrentWeek(prefer = "2026-07-20"): string {
  const weekDays = buildLocalWeekDayKeys(currentLocalWeek().weekStartKey);
  if (weekDays.includes(prefer)) {
    return prefer;
  }
  return weekDays[1] ?? weekDays[0];
}

function makeItem(
  partial: Partial<ScheduleVisibilityResponse["items"][number]> & {
    item_id: string;
    channel: "blog" | "linkedin";
    scheduled_at_utc: string;
  },
): ScheduleVisibilityResponse["items"][number] {
  return {
    campaign_id: partial.campaign_id ?? "camp-1",
    variant_id:
      partial.variant_id ??
      (partial.channel === "linkedin" ? partial.item_id.split(":").pop()! : null),
    title: partial.title ?? partial.item_id,
    audience: partial.audience ?? "eng",
    publication_state: partial.publication_state ?? "pending",
    source_state: partial.source_state ?? partial.publication_state ?? "pending",
    blocked: partial.blocked ?? false,
    critical: partial.critical ?? false,
    linkedin_api_published: partial.linkedin_api_published ?? false,
    schedule_editable: partial.schedule_editable ?? true,
    calendar_item_id: partial.calendar_item_id ?? null,
    ...partial,
  };
}

function makeClient(
  scheduleItems: ScheduleVisibilityResponse["items"],
  handlers: (url: string, init?: RequestInit) => Response | null = () => null,
) {
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
        publish_state: String(i.source_state ?? "pending"),
        calendar_item_id: i.calendar_item_id ?? null,
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
  const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
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
    const custom = handlers(url, init);
    if (custom) {
      return custom;
    }
    return new Response("not found", { status: 404 });
  });
  return {
    client: new SupervisionApiClient(auth, fetchImpl as typeof fetch),
    fetchImpl,
  };
}

describe("US-040K local-day density helpers", () => {
  it("includes pending/queued/published LinkedIn and blog; excludes cancelled/failed", () => {
    const pending = normalizeScheduleItem(
      makeItem({
        item_id: "linkedin:c:a",
        channel: "linkedin",
        scheduled_at_utc: "2026-07-20T15:00:00Z",
        source_state: "pending",
      }),
    );
    const queued = normalizeScheduleItem(
      makeItem({
        item_id: "linkedin:c:b",
        channel: "linkedin",
        scheduled_at_utc: "2026-07-20T16:00:00Z",
        source_state: "queued",
      }),
    );
    const published = normalizeScheduleItem(
      makeItem({
        item_id: "linkedin:c:c",
        channel: "linkedin",
        scheduled_at_utc: "2026-07-20T17:00:00Z",
        source_state: "published",
        publication_state: "published",
      }),
    );
    const cancelled = normalizeScheduleItem(
      makeItem({
        item_id: "linkedin:c:d",
        channel: "linkedin",
        scheduled_at_utc: "2026-07-20T18:00:00Z",
        source_state: "cancelled",
        publication_state: "cancelled",
      }),
    );
    const failed = normalizeScheduleItem(
      makeItem({
        item_id: "linkedin:c:e",
        channel: "linkedin",
        scheduled_at_utc: "2026-07-20T19:00:00Z",
        source_state: "failed",
        publication_state: "failed",
      }),
    );
    const blog = normalizeScheduleItem(
      makeItem({
        item_id: "blog:cal-1",
        channel: "blog",
        scheduled_at_utc: "2026-07-20T12:00:00Z",
        calendar_item_id: "cal-1",
      }),
    );

    expect(isDensityMember(pending)).toBe(true);
    expect(isDensityMember(queued)).toBe(true);
    expect(isDensityMember(published)).toBe(true);
    expect(isDensityMember(cancelled)).toBe(false);
    expect(isDensityMember(failed)).toBe(false);
    expect(isDensityMember(blog)).toBe(true);
  });

  it("excludes self on same local day for others count", () => {
    const day = "2026-07-20";
    const items: ScheduleItem[] = [
      normalizeScheduleItem(
        makeItem({
          item_id: "linkedin:c:a",
          channel: "linkedin",
          campaign_id: "c",
          variant_id: "a",
          scheduled_at_utc: `${day}T15:00:00Z`,
        }),
      ),
      normalizeScheduleItem(
        makeItem({
          item_id: "linkedin:c:b",
          channel: "linkedin",
          campaign_id: "c",
          variant_id: "b",
          scheduled_at_utc: `${day}T16:00:00Z`,
        }),
      ),
    ];
    expect(countDensityOnLocalDay(items, day)).toBe(2);
    expect(
      othersOnLocalDay(
        items,
        day,
        excludeForScheduleItem(items[0]),
      ),
    ).toBe(1);
    expect(isLocalDayFull(1)).toBe(false);
    expect(isLocalDayFull(2)).toBe(true);
    expect(densityCueLevel(2)).toBe("full");
    expect(densityCueLevel(3)).toBe("over");
    expect(densityCueLevel(1)).toBe("none");
  });

  it("maps density and timezone codes to plain language", () => {
    expect(explainErrorCodes(["linkedin_supervision_local_day_density"])).toBe(
      "This day already has 2 publications.",
    );
    expect(explainErrorCodes(["calendar_schedule_local_day_density"])).toBe(
      "This day already has 2 publications.",
    );
    expect(explainErrorCodesPlain(["linkedin_supervision_local_day_density"])).toBe(
      "This day already has 2 publications.",
    );
    expect(explainErrorCodes(["operator_timezone_required"])).toContain(
      SUPERVISION_ERROR_MESSAGES.operator_timezone_required,
    );
    expect(explainErrorCodes(["operator_timezone_invalid"])).toContain(
      "invalid",
    );
    expect(LOCAL_DAY_FULL_MESSAGE).toMatch(/2 publications/i);
  });
});

describe("US-040K Week/Month density cues", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-07-19T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows calm full cue at 2 density members on Week", async () => {
    const day = dayInCurrentWeek("2026-07-20");
    const items = [
      makeItem({
        item_id: "linkedin:camp:a",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "a",
        title: "Alpha",
        scheduled_at_utc: `${day}T15:00:00Z`,
      }),
      makeItem({
        item_id: "linkedin:camp:b",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "b",
        title: "Beta",
        scheduled_at_utc: `${day}T17:00:00Z`,
      }),
    ];
    const { client } = makeClient(items);
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<App client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId(`week-day-${day}`)).toBeInTheDocument();
    });
    const col = screen.getByTestId(`week-day-${day}`);
    expect(within(col).getByTestId("day-density-full")).toHaveTextContent(
      /Full \(2\)/,
    );
    expect(col).toHaveClass("day-density-full");
    expect(within(col).queryByTestId("day-density-over")).toBeNull();
    expect(within(col).getAllByTestId("week-event-chip")).toHaveLength(2);
  });

  it("shows over-capacity cue at 3+ and keeps chips visible on Week", async () => {
    const day = dayInCurrentWeek("2026-07-20");
    const items = [
      makeItem({
        item_id: "linkedin:camp:a",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "a",
        title: "One",
        scheduled_at_utc: `${day}T14:00:00Z`,
      }),
      makeItem({
        item_id: "linkedin:camp:b",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "b",
        title: "Two",
        scheduled_at_utc: `${day}T15:00:00Z`,
      }),
      makeItem({
        item_id: "blog:cal-x",
        channel: "blog",
        title: "Blog",
        scheduled_at_utc: `${day}T16:00:00Z`,
        calendar_item_id: "cal-x",
      }),
    ];
    const { client } = makeClient(items);
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<App client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId(`week-day-${day}`)).toBeInTheDocument();
    });
    const col = screen.getByTestId(`week-day-${day}`);
    expect(within(col).getByTestId("day-density-over")).toHaveTextContent(
      /Over capacity \(3\)/,
    );
    expect(col).toHaveClass("day-density-over");
    expect(within(col).getAllByTestId("week-event-chip")).toHaveLength(3);
    // Fix path: chips still open EventModal with reschedule.
    await user.click(within(col).getAllByTestId("week-event-chip")[0]);
    await waitFor(() => {
      expect(screen.getByTestId("event-modal")).toBeInTheDocument();
    });
    expect(screen.getByTestId("row-defer")).toBeInTheDocument();
  });

  it("shows Month density full cue at 2", async () => {
    const day = "2026-07-20";
    const items = [
      makeItem({
        item_id: "linkedin:camp:a",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "a",
        title: "Alpha",
        scheduled_at_utc: `${day}T15:00:00Z`,
      }),
      makeItem({
        item_id: "linkedin:camp:b",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "b",
        title: "Beta",
        scheduled_at_utc: `${day}T17:00:00Z`,
      }),
    ];
    const { client } = makeClient(items);
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<App client={client} />);
    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId(`calendar-day-${day}`)).toBeInTheDocument();
    });
    const cell = screen.getByTestId(`calendar-day-${day}`);
    expect(within(cell).getByTestId("day-density-full")).toHaveTextContent(
      /Full \(2\)/,
    );
    expect(cell).toHaveClass("day-density-full");
  });

  it("local-midnight occupancy matches Week and Month (America/Chicago)", async () => {
    expect(localDayKey(NEAR_MIDNIGHT_UTC)).toBe("2026-07-19");
    const items = [
      makeItem({
        item_id: "linkedin:camp:near",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "near",
        title: "Near midnight",
        scheduled_at_utc: NEAR_MIDNIGHT_UTC,
      }),
      makeItem({
        item_id: "linkedin:camp:other",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "other",
        title: "Same local day",
        scheduled_at_utc: "2026-07-19T18:00:00Z",
      }),
    ];
    const { client } = makeClient(items);
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<App client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("week-day-2026-07-19")).toBeInTheDocument();
    });
    const weekDay = screen.getByTestId("week-day-2026-07-19");
    expect(within(weekDay).getByTestId("day-density-full")).toBeInTheDocument();
    expect(within(weekDay).getAllByTestId("week-event-chip")).toHaveLength(2);

    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-day-2026-07-19")).toBeInTheDocument();
    });
    const monthDay = screen.getByTestId("calendar-day-2026-07-19");
    expect(within(monthDay).getByTestId("day-density-full")).toBeInTheDocument();
  });
});

describe("US-040K ScheduleEditor / EventModal density block", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-07-19T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("blocks placing a 3rd item with plain-language message in ScheduleEditor", async () => {
    const fullDay = dayInCurrentWeek("2026-07-21");
    const moveDay = dayInCurrentWeek("2026-07-22");
    const items = [
      makeItem({
        item_id: "linkedin:camp:a",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "a",
        title: "A",
        scheduled_at_utc: `${fullDay}T14:00:00Z`,
      }),
      makeItem({
        item_id: "linkedin:camp:b",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "b",
        title: "B",
        scheduled_at_utc: `${fullDay}T15:00:00Z`,
      }),
      makeItem({
        item_id: "linkedin:camp:mover",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "mover",
        title: "Mover",
        scheduled_at_utc: `${moveDay}T16:00:00Z`,
      }),
    ];
    let deferCalled = false;
    const { client } = makeClient(items, (url) => {
      if (url.includes("/defer-linkedin-variant")) {
        deferCalled = true;
        return new Response(JSON.stringify({ status: "completed" }), {
          status: 200,
        });
      }
      return null;
    });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<App client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId(`week-day-${moveDay}`)).toBeInTheDocument();
    });
    const moverChip = within(
      screen.getByTestId(`week-day-${moveDay}`),
    ).getByTestId("week-event-chip");
    await user.click(moverChip);
    await waitFor(() => {
      expect(screen.getByTestId("row-defer")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("row-defer"));
    await waitFor(() => {
      expect(screen.getByTestId("schedule-editor-panel")).toBeInTheDocument();
    });

    const datetime = screen.getByTestId("schedule-datetime");
    await user.clear(datetime);
    // Local noon on the already-full day (far enough in future relative to pinned now).
    await user.type(datetime, `${fullDay}T12:00:00`);
    await user.click(screen.getByTestId("schedule-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("toast-host").textContent).toMatch(
        /This day already has 2 publications/i,
      );
    });
    expect(deferCalled).toBe(false);
  });

  it("sends operator_timezone on defer and maps worker density errors", async () => {
    const day = dayInCurrentWeek("2026-07-22");
    const items = [
      makeItem({
        item_id: "linkedin:camp:mover",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "mover",
        title: "Mover",
        scheduled_at_utc: `${day}T16:00:00Z`,
      }),
    ];
    let seenBody: Record<string, unknown> | null = null;
    const { client } = makeClient(items, (url, init) => {
      if (url.includes("/defer-linkedin-variant") && init?.method === "POST") {
        seenBody = JSON.parse(String(init.body));
        return new Response(
          JSON.stringify({
            status: "failed",
            campaign_id: "camp",
            variant: "mover",
            state: null,
            publish_state: "pending",
            dry_run: true,
            phase: null,
            errors: ["linkedin_supervision_local_day_density"],
            warnings: [],
            metadata_written: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return null;
    });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<App client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    const chip = await screen.findByTestId("week-event-chip");
    await user.click(chip);
    await user.click(await screen.findByTestId("row-defer"));
    const datetime = await screen.findByTestId("schedule-datetime");
    await user.clear(datetime);
    await user.type(datetime, "2099-08-20T10:00:00");
    await user.click(screen.getByTestId("schedule-submit"));
    await waitFor(() => {
      expect(seenBody?.operator_timezone).toBeTruthy();
      expect(screen.getByTestId("toast-host").textContent).toMatch(
        /This day already has 2 publications/i,
      );
    });
  });

  it("blocks reopen onto a full local day with plain language", async () => {
    const fullDay = dayInCurrentWeek("2026-07-21");
    const cancelDay = dayInCurrentWeek("2026-07-22");
    const items = [
      makeItem({
        item_id: "linkedin:camp:a",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "a",
        title: "A",
        scheduled_at_utc: `${fullDay}T14:00:00Z`,
      }),
      makeItem({
        item_id: "linkedin:camp:b",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "b",
        title: "B",
        scheduled_at_utc: `${fullDay}T15:00:00Z`,
      }),
      makeItem({
        item_id: "linkedin:camp:cancelled",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "cancelled",
        title: "Cancelled",
        scheduled_at_utc: `${cancelDay}T16:00:00Z`,
        publication_state: "cancelled",
        source_state: "cancelled",
        schedule_editable: false,
        reopen_eligible: true,
        cancelled_at_utc: `${cancelDay}T11:00:00Z`,
        cancellation_phase: "pre_queue",
        cancellation_reason: "operator_choice",
      }),
    ];
    let reopenCalled = false;
    const { client } = makeClient(items, (url) => {
      if (url.includes("/reopen-linkedin-variant")) {
        reopenCalled = true;
        return new Response(JSON.stringify({ status: "completed" }), {
          status: 200,
        });
      }
      return null;
    });
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<App client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId(`week-day-${cancelDay}`)).toBeInTheDocument();
    });
    const cancelChip = within(
      screen.getByTestId(`week-day-${cancelDay}`),
    ).getByTestId("week-event-chip");
    await user.click(cancelChip);
    await user.click(await screen.findByTestId("row-reopen"));
    await waitFor(() => {
      expect(screen.getByTestId("reopen-panel")).toBeInTheDocument();
    });
    const datetime = screen.getByLabelText(/New scheduled time/i);
    await user.clear(datetime);
    await user.type(datetime, `${fullDay}T12:00:00`);
    await user.click(screen.getByTestId("reopen-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("event-modal-error").textContent).toMatch(
        /This day already has 2 publications/i,
      );
    });
    expect(reopenCalled).toBe(false);
  });
});

describe("US-040K viewport matrix (~1280 / ~375) density scenes", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-07-19T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  for (const width of [1280, 375] as const) {
    it(`renders full and over density cues at ${width}px`, async () => {
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        value: width,
      });
      const fullDay = dayInCurrentWeek("2026-07-20");
      const overDay = dayInCurrentWeek("2026-07-21");
      const items = [
        makeItem({
          item_id: "linkedin:camp:a",
          channel: "linkedin",
          campaign_id: "camp",
          variant_id: "a",
          scheduled_at_utc: `${fullDay}T14:00:00Z`,
        }),
        makeItem({
          item_id: "linkedin:camp:b",
          channel: "linkedin",
          campaign_id: "camp",
          variant_id: "b",
          scheduled_at_utc: `${fullDay}T15:00:00Z`,
        }),
        makeItem({
          item_id: "linkedin:camp:c",
          channel: "linkedin",
          campaign_id: "camp",
          variant_id: "c",
          scheduled_at_utc: `${overDay}T14:00:00Z`,
        }),
        makeItem({
          item_id: "linkedin:camp:d",
          channel: "linkedin",
          campaign_id: "camp",
          variant_id: "d",
          scheduled_at_utc: `${overDay}T15:00:00Z`,
        }),
        makeItem({
          item_id: "blog:cal-o",
          channel: "blog",
          scheduled_at_utc: `${overDay}T16:00:00Z`,
          calendar_item_id: "cal-o",
        }),
      ];
      const { client } = makeClient(items);
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      const { unmount } = render(<App client={client} />);
      await user.click(screen.getByTestId("load-btn"));
      await waitFor(() => {
        expect(
          within(screen.getByTestId(`week-day-${fullDay}`)).getByTestId(
            "day-density-full",
          ),
        ).toBeInTheDocument();
      });
      expect(
        within(screen.getByTestId(`week-day-${overDay}`)).getByTestId(
          "day-density-over",
        ),
      ).toBeInTheDocument();
      expect(
        within(screen.getByTestId(`week-day-${overDay}`)).getAllByTestId(
          "week-event-chip",
        ),
      ).toHaveLength(3);

      await user.click(screen.getByTestId("view-month"));
      await waitFor(() => {
        expect(
          within(screen.getByTestId(`calendar-day-${fullDay}`)).getByTestId(
            "day-density-full",
          ),
        ).toBeInTheDocument();
      });
      unmount();
    });
  }
});

describe("US-040K datetime helpers still convert local → *_utc", () => {
  it("round-trips local picker digits to UTC wire fields", () => {
    const local = "2026-07-21T10:30:00";
    const utc = datetimeLocalToUtcIso(local);
    expect(utc).toMatch(/Z$/);
    expect(localDayKey(utc)).toBe("2026-07-21");
    expect(utcIsoToDatetimeLocal(utc!)).toBe(local);
  });
});
