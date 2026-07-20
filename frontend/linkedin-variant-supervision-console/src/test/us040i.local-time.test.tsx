/**
 * US-040I — operator-local time experience (implementation evidence).
 * Does NOT mark Story accepted — Visual DoD + operator walkthrough remain gated.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import { explainErrorCodes, SUPERVISION_ERROR_MESSAGES } from "../api/errors";
import {
  datetimeLocalToUtcIso,
  isStrictlyAfterNow,
  ScheduleEditorFields,
  utcIsoToDatetimeLocal,
} from "../components/ScheduleEditor";
import {
  localDayKey,
  monthsCoveringLocalMonth,
  monthsCoveringWeek,
  utcDayKey,
} from "../models/dateHelpers";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityResponse,
} from "../api/types";

const NEAR_MIDNIGHT_UTC = "2026-07-20T04:00:00Z"; // Chicago CDT → local 2026-07-19 23:00

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
  return { client: new SupervisionApiClient(auth, fetchImpl as typeof fetch), fetchImpl };
}

describe("US-040I local-day bucketing and timezone cues", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("places near-midnight UTC instants on the local day (not UTC day)", () => {
    expect(utcDayKey(NEAR_MIDNIGHT_UTC)).toBe("2026-07-20");
    expect(localDayKey(NEAR_MIDNIGHT_UTC)).toBe("2026-07-19");
  });

  it("pads week and month visibility windows across adjacent months", () => {
    expect(monthsCoveringLocalMonth({ year: 2026, month: 7 })).toEqual([
      { year: 2026, month: 6 },
      { year: 2026, month: 7 },
      { year: 2026, month: 8 },
    ]);
    // Week of Sun 2026-07-26 → Sat 2026-08-01 with ±1 day pad includes July + August.
    expect(monthsCoveringWeek("2026-07-26")).toEqual([
      { year: 2026, month: 7 },
      { year: 2026, month: 8 },
    ]);
  });

  it("shows near-midnight item on local day column in Week and Month", async () => {
    const items: ScheduleVisibilityResponse["items"] = [
      {
        item_id: "linkedin:camp:near-midnight",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "near-midnight",
        title: "Near midnight",
        audience: "eng",
        scheduled_at_utc: NEAR_MIDNIGHT_UTC,
        publication_state: "pending",
        source_state: "pending",
        blocked: false,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
      },
    ];
    const { client } = makeClient(items);
    const user = userEvent.setup();
    render(<App client={client} />);

    await user.click(screen.getByTestId("load-btn"));
    // Navigate Week to the week containing 2026-07-19.
    // Default week is "today" (2026-07-19 per pinned test clock assumptions / local today).
    await waitFor(() => {
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
    });

    // Force month July 2026 and open Week day for local 2026-07-19.
    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
    });
    // Ensure we are on July 2026 — label should not say (UTC).
    const monthLabel = screen.getByTestId("calendar-month-label");
    expect(monthLabel.textContent).not.toMatch(/\(UTC\)/);
    expect(screen.getByTestId("calendar-tz-note").textContent).not.toMatch(
      /think in UTC|UTC calendar/i,
    );

    const localDay = screen.getByTestId("calendar-day-2026-07-19");
    expect(localDay.textContent).toMatch(/Near midnight|linkedin/i);
    expect(screen.queryByTestId("calendar-day-2026-07-20")?.textContent).not.toMatch(
      /Near midnight/,
    );
  });

  it("EventModal primary schedule is local; UTC only under diagnostics", async () => {
    const items: ScheduleVisibilityResponse["items"] = [
      {
        item_id: "linkedin:camp:eng",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "eng",
        title: "Eng post",
        audience: "eng",
        scheduled_at_utc: "2026-07-20T15:00:00Z",
        publication_state: "pending",
        source_state: "pending",
        blocked: false,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
      },
    ];
    const { client } = makeClient(items);
    const user = userEvent.setup();
    render(<App client={client} />);
    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });
    const open = screen.getByTestId("schedule-open-month");
    await user.click(open);
    await waitFor(() => {
      expect(screen.getByTestId("event-modal")).toBeInTheDocument();
    });
    const localLine = screen.getByTestId("event-modal-schedule-local");
    expect(localLine.textContent).toBeTruthy();
    expect(localLine.textContent).not.toMatch(/T15:00:00Z/);
    // Diagnostics collapsed by default — UTC day not required reading.
    expect(screen.getByTestId("event-modal-diagnostics")).not.toHaveAttribute(
      "open",
    );
    screen.getByTestId("event-modal-diagnostics").querySelector("summary")?.click();
    await waitFor(() => {
      expect(screen.getByTestId("event-modal-scheduled-at-utc").textContent).toBe(
        "2026-07-20T15:00:00Z",
      );
      expect(screen.getByTestId("event-modal-utc-day").textContent).toBe(
        "2026-07-20",
      );
    });
  });
});

describe("US-040I local-first ScheduleEditor", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("round-trips local picker digits to *_utc ISO at the boundary", () => {
    // America/Chicago CDT (UTC−5): 14:00 local → 19:00Z
    const iso = datetimeLocalToUtcIso("2026-08-01T14:00:00");
    expect(iso).toBe("2026-08-01T19:00:00Z");
    expect(utcIsoToDatetimeLocal(iso)).toBe("2026-08-01T14:00:00");
  });

  it("allows earlier-than-previous when still after now; rejects past-now", () => {
    const now = Date.parse("2026-07-19T12:00:00Z");
    const previous = "2026-07-25T18:00:00Z";
    const earlierButFuture = "2026-07-20T15:00:00Z";
    const past = "2026-07-18T15:00:00Z";
    expect(isStrictlyAfterNow(earlierButFuture, now)).toBe(true);
    expect(Date.parse(earlierButFuture) < Date.parse(previous)).toBe(true);
    expect(isStrictlyAfterNow(past, now)).toBe(false);
  });

  it("rejects past-now on submit with local-language toast", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-07-19T12:00:00Z"));

    const items: ScheduleVisibilityResponse["items"] = [
      {
        item_id: "linkedin:camp:eng",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "eng",
        title: "Eng post",
        audience: "eng",
        scheduled_at_utc: "2026-07-25T18:00:00Z",
        publication_state: "pending",
        source_state: "pending",
        blocked: false,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
      },
    ];
    const { client } = makeClient(items);
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<App client={client} />);
    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("schedule-open-month"));
    await user.click(screen.getByTestId("row-defer"));
    const input = screen.getByTestId("schedule-datetime");
    await user.clear(input);
    // Local past: 2026-07-18 10:00 CDT
    await user.type(input, "2026-07-18T10:00:00");
    await user.click(screen.getByTestId("schedule-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast").textContent).toMatch(
        /after now in your local time/i,
      );
    });
  });

  it("allows earlier-but-still-future dry-run reschedule", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-07-19T12:00:00Z"));

    const deferBodies: unknown[] = [];
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const items: ScheduleVisibilityResponse["items"] = [
      {
        item_id: "linkedin:camp:eng",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "eng",
        title: "Eng post",
        audience: "eng",
        scheduled_at_utc: "2026-07-25T18:00:00Z",
        publication_state: "pending",
        source_state: "pending",
        blocked: false,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
      },
    ];
    const pending: PendingSupervisionResponse = {
      status: "ok",
      observed_at_utc: "2026-07-19T12:00:00Z",
      read_only: false,
      linkedin_publication_enabled: false,
      variants: [
        {
          campaign_id: "camp",
          variant_id: "eng",
          audience: "eng",
          scheduled_at_utc: "2026-07-25T18:00:00Z",
          publish_state: "pending",
          calendar_item_id: null,
          calendar_title: "Eng post",
          calendar_due_at_utc: null,
          calendar_status: null,
          operator_supervision_last_action: null,
          auto_queue_eligible: true,
          operator_supervision_reason: null,
          draft_content: "Draft",
        },
      ],
      issues: [],
      integration_failures: [],
    };
    const schedule: ScheduleVisibilityResponse = {
      status: "ok",
      observed_at_utc: "2026-07-19T12:00:00Z",
      read_only: false,
      year: 2026,
      month: 7,
      from_utc: "2026-07-01T00:00:00Z",
      to_utc: "2026-07-31T23:59:59Z",
      linkedin_publication_enabled: false,
      items,
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
      if (url.includes("defer-linkedin-variant")) {
        const body = JSON.parse(String(init?.body));
        deferBodies.push(body);
        return new Response(
          JSON.stringify({
            status: "completed",
            campaign_id: "camp",
            variant: "eng",
            state: "distribution_scheduled",
            publish_state: "pending",
            dry_run: true,
            phase: "pre_queue",
            scheduled_at_utc: body.new_scheduled_at_utc,
            errors: [],
            warnings: [],
            metadata_written: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("not found", { status: 404 });
    });
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    render(<App client={client} />);
    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("schedule-open-month"));
    await user.click(screen.getByTestId("row-defer"));
    const input = screen.getByTestId("schedule-datetime");
    await user.clear(input);
    // Earlier than previous (25th) but still after now (19th): local Jul 20 10:00 CDT → 15:00Z
    await user.type(input, "2026-07-20T10:00:00");
    await user.click(screen.getByTestId("schedule-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast").textContent).toMatch(
        /Preview only \(dry-run\).*schedule change validated/i,
      );
    });
    expect(deferBodies[0]).toMatchObject({
      dry_run: true,
      new_scheduled_at_utc: "2026-07-20T15:00:00Z",
    });
  });

  it("ScheduleEditor and error strings do not coach thinking in UTC", () => {
    render(
      <ScheduleEditorFields value="" onChange={() => undefined} />,
    );
    const fields = screen.getByTestId("schedule-editor-fields");
    expect(fields.textContent).not.toMatch(/think in UTC/i);
    expect(fields.textContent).not.toMatch(/\(UTC\)/);
    expect(screen.getByTestId("schedule-editor-help").textContent).toMatch(
      /local timezone/i,
    );

    expect(SUPERVISION_ERROR_MESSAGES.linkedin_supervision_defer_time_invalid).not.toMatch(
      /\(UTC\)|think in UTC/i,
    );
    expect(SUPERVISION_ERROR_MESSAGES.calendar_schedule_time_invalid).not.toMatch(
      /canonical UTC|think in UTC/i,
    );
    expect(explainErrorCodes(["calendar_schedule_time_invalid"])).toMatch(
      /after now in your local time/,
    );
  });
});

describe("US-040I viewport matrix (implementation evidence, not Story accepted)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

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

  it("Week and Month show local cues without (UTC) at desktop and mobile widths", async () => {
    const items: ScheduleVisibilityResponse["items"] = [
      {
        item_id: "linkedin:camp:eng",
        channel: "linkedin",
        campaign_id: "camp",
        variant_id: "eng",
        title: "Eng post",
        audience: "eng",
        scheduled_at_utc: "2026-07-20T15:00:00Z",
        publication_state: "pending",
        source_state: "pending",
        blocked: false,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
      },
    ];
    await assertAtWidths(async () => {
      const { client } = makeClient(items);
      const user = userEvent.setup();
      const { unmount } = render(<App client={client} />);
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
      expect(screen.getByTestId("week-tz-note").textContent).toMatch(/Local calendar/);
      expect(screen.getByTestId("week-tz-note").textContent).not.toMatch(/\(UTC\)/);
      expect(screen.getByTestId("week-label").textContent).not.toMatch(/\(UTC\)/);

      await user.click(screen.getByTestId("view-month"));
      expect(screen.getByTestId("calendar-month-label").textContent).not.toMatch(
        /\(UTC\)/,
      );
      expect(screen.getByTestId("calendar-tz-note").textContent).not.toMatch(
        /think in UTC/i,
      );
      unmount();
    });
  });
});
