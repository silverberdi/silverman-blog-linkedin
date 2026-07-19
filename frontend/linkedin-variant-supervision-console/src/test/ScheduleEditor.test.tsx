import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import { SupervisionStoreProvider } from "../models/store";
import { MonthCalendarView } from "../components/MonthCalendarView";
import { WeekView } from "../components/WeekView";
import { EventModal } from "../components/EventModal";
import { AppShell } from "../components/AppShell";
import { explainErrorCodes } from "../api/errors";
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
      item_id: "blog:cal-1",
      channel: "blog",
      campaign_id: "camp-1",
      variant_id: null,
      title: "Editable blog",
      audience: "eng",
      scheduled_at_utc: "2026-07-19T11:00:00Z",
      publication_state: "planned",
      source_state: "scheduled",
      blocked: false,
      critical: false,
      linkedin_api_published: false,
      calendar_item_id: "cal-1",
      schedule_editable: true,
      schedule_edit_block_reason: null,
    },
    {
      item_id: "blog:cal-done",
      channel: "blog",
      campaign_id: "camp-1",
      variant_id: null,
      title: "Completed blog",
      audience: "eng",
      scheduled_at_utc: "2026-07-22T09:00:00Z",
      publication_state: "planned",
      source_state: "completed",
      blocked: false,
      critical: false,
      linkedin_api_published: false,
      calendar_item_id: "cal-done",
      schedule_editable: false,
      schedule_edit_block_reason: "calendar_schedule_unsupported_state",
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
      schedule_editable: true,
      schedule_edit_block_reason: null,
    },
  ],
  issues: [],
};

function mockFetch(
  handlers: (url: string, init?: RequestInit) => Response | null,
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
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
    const custom = handlers(url, init);
    if (custom) {
      return custom;
    }
    return new Response("not found", { status: 404 });
  });
}

function renderConsole(
  client: SupervisionApiClient,
  view: "week" | "month",
) {
  return render(
    <SupervisionStoreProvider client={client}>
      <AppShell>
        <EventModal />
        {view === "month" ? <MonthCalendarView /> : <WeekView />}
      </AppShell>
    </SupervisionStoreProvider>,
  );
}

describe("ScheduleEditor US-040C / US-040G", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("opens shared editor from Week interim with dry-run default", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const client = new SupervisionApiClient(
      auth,
      mockFetch(() => null) as typeof fetch,
    );
    const user = userEvent.setup();
    renderConsole(client, "month");

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });
    const linkedinOpen = screen.getAllByTestId("schedule-open-month").find(
      (el) => el.getAttribute("data-item-id")?.includes("linkedin"),
    );
    expect(linkedinOpen).toBeTruthy();
    await user.click(linkedinOpen!);
    await waitFor(() => {
      expect(screen.getByTestId("event-modal")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("row-defer"));
    const panel = screen.getByTestId("schedule-editor-panel");
    expect(panel).toHaveAttribute("data-entry", "month");
    expect(panel).toHaveAttribute("data-channel", "linkedin");
    expect(screen.getByTestId("schedule-dry-run")).toBeChecked();
  });

  it("opens shared editor from month chip; published blog is read-only", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const client = new SupervisionApiClient(
      auth,
      mockFetch(() => null) as typeof fetch,
    );
    const user = userEvent.setup();
    renderConsole(client, "month");

    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });

    const day19 = screen.getByTestId("calendar-day-2026-07-19");
    const monthOpen = day19.querySelector(
      '[data-testid="schedule-open-month"]',
    ) as HTMLElement;
    expect(monthOpen).toBeTruthy();
    await user.click(monthOpen);
    await waitFor(() => {
      expect(screen.getByTestId("event-modal")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("row-defer"));
    expect(screen.getByTestId("schedule-editor-panel")).toHaveAttribute(
      "data-entry",
      "month",
    );
    expect(screen.getByTestId("schedule-editor-panel")).toHaveAttribute(
      "data-editable",
      "true",
    );
    await user.click(screen.getByTestId("schedule-close"));
    await user.click(screen.getByTestId("event-modal-close"));

    const day22 = screen.getByTestId("calendar-day-2026-07-22");
    const doneOpen = day22.querySelector(
      '[data-testid="schedule-open-month"]',
    ) as HTMLElement;
    await user.click(doneOpen);
    await waitFor(() => {
      expect(screen.getByTestId("event-modal")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("row-defer"));
    expect(screen.getByTestId("schedule-editor-readonly")).toBeInTheDocument();
  });

  it("dry-run LinkedIn defer validates without claiming persist; real requires confirm", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const deferBodies: unknown[] = [];
    const fetchImpl = mockFetch((url, init) => {
      if (url.includes("defer-linkedin-variant")) {
        const body = JSON.parse(String(init?.body));
        deferBodies.push(body);
        return new Response(
          JSON.stringify({
            status: "completed",
            campaign_id: "camp-1",
            variant: "engineering-leadership",
            state: "distribution_scheduled",
            publish_state: "pending",
            dry_run: body.dry_run,
            phase: "pre_queue",
            scheduled_at_utc: body.new_scheduled_at_utc,
            errors: [],
            warnings: [],
            metadata_written: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return null;
    });
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    const user = userEvent.setup();
    renderConsole(client, "month");

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });
    const linkedinOpen = screen.getAllByTestId("schedule-open-month").find(
      (el) => el.getAttribute("data-item-id")?.includes("linkedin"),
    );
    await user.click(linkedinOpen!);
    await user.click(screen.getByTestId("row-defer"));
    await user.click(screen.getByTestId("schedule-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast").textContent).toMatch(
        /Dry-run schedule change validated/,
      );
    });
    expect(deferBodies[0]).toMatchObject({
      dry_run: true,
      source: "linkedin_variant_supervision_console",
      actor: "operator",
    });

    await user.click(screen.getByTestId("schedule-dry-run"));
    await user.click(screen.getByTestId("schedule-submit"));
    expect(confirmSpy).toHaveBeenCalled();
    expect(deferBodies).toHaveLength(1);
  });

  it("real blog schedule success shows previous/new and separate overrides", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const fetchImpl = mockFetch((url, init) => {
      if (url.includes("update-item-schedule")) {
        const body = JSON.parse(String(init?.body));
        expect(body.dry_run).toBe(false);
        expect(body.expected_calendar_fingerprint).toBe("a".repeat(64));
        expect(body.source).toBe("linkedin_variant_supervision_console");
        return new Response(
          JSON.stringify({
            status: "completed",
            dry_run: false,
            item_id: "cal-1",
            previous_due_at_utc: "2026-07-19T11:00:00Z",
            new_due_at_utc: "2026-08-01T14:00:00Z",
            calendar_written: true,
            related_linkedin_variants_outcome: "unchanged_separate_overrides",
            errors: [],
            warnings: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return null;
    });
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    const user = userEvent.setup();
    renderConsole(client, "month");

    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
    });
    const day19 = screen.getByTestId("calendar-day-2026-07-19");
    const monthOpen = day19.querySelector(
      '[data-testid="schedule-open-month"]',
    ) as HTMLElement;
    await user.click(monthOpen);
    await user.click(screen.getByTestId("row-defer"));
    await user.click(screen.getByTestId("schedule-dry-run"));
    await user.clear(screen.getByTestId("schedule-datetime"));
    await user.type(screen.getByTestId("schedule-datetime"), "2026-08-01T14:00:00");
    await user.click(screen.getByTestId("schedule-submit"));
    await waitFor(() => {
      const text = screen.getByTestId("toast").textContent || "";
      expect(text).toMatch(/Previous: 2026-07-19T11:00:00Z/);
      expect(text).toMatch(/New: 2026-08-01T14:00:00Z/);
      expect(text).toMatch(/separate overrides/);
    });
  });

  it("maps calendar and LinkedIn schedule failure codes", () => {
    expect(explainErrorCodes(["calendar_schedule_time_invalid"])).toMatch(
      /after now in your local time/,
    );
    expect(explainErrorCodes(["linkedin_supervision_defer_saturation"])).toMatch(
      /72h/,
    );
    expect(explainErrorCodes(["calendar_completion_concurrent_update"])).toMatch(
      /concurrently/,
    );
  });
});
