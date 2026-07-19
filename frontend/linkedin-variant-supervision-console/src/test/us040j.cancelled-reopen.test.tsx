import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import { SUPERVISION_ERROR_MESSAGES } from "../api/errors";
import {
  buildLocalWeekDayKeys,
  currentLocalWeek,
  todayLocalDayKey,
} from "../models/dateHelpers";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityResponse,
} from "../api/types";

function cancelledItemsForCurrentWeek(): ScheduleVisibilityResponse["items"] {
  const today = todayLocalDayKey();
  const weekDays = buildLocalWeekDayKeys(currentLocalWeek().weekStartKey);
  const dayInWeek = weekDays.includes(today) ? today : weekDays[3];
  return [
    {
      item_id: "linkedin:camp-1:engineering-leadership",
      channel: "linkedin",
      campaign_id: "camp-1",
      variant_id: "engineering-leadership",
      title: "Cancelled Post",
      audience: "eng",
      scheduled_at_utc: `${dayInWeek}T15:00:00Z`,
      publication_state: "cancelled",
      source_state: "cancelled",
      blocked: false,
      critical: false,
      linkedin_api_published: false,
      schedule_editable: false,
      cancelled_at_utc: `${dayInWeek}T11:00:00Z`,
      cancellation_phase: "pre_queue",
      cancellation_reason: "operator_choice",
      reopen_eligible: true,
    },
    {
      item_id: "linkedin:camp-1:failed-cancel",
      channel: "linkedin",
      campaign_id: "camp-1",
      variant_id: "failed-cancel",
      title: "Recovery Cancel",
      audience: "eng",
      scheduled_at_utc: `${dayInWeek}T18:00:00Z`,
      publication_state: "cancelled",
      source_state: "cancelled",
      blocked: false,
      critical: false,
      linkedin_api_published: false,
      schedule_editable: false,
      cancelled_at_utc: `${dayInWeek}T12:00:00Z`,
      cancellation_phase: "recovery",
      cancellation_reason: "retry_budget_exhausted",
      reopen_eligible: false,
    },
  ];
}

function buildSchedule(
  items: ScheduleVisibilityResponse["items"] = cancelledItemsForCurrentWeek(),
): ScheduleVisibilityResponse {
  const day = items[0]?.scheduled_at_utc?.slice(0, 7) ?? "2026-07";
  const [year, month] = day.split("-").map(Number);
  return {
    status: "ok",
    observed_at_utc: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
    read_only: false,
    year: year || 2026,
    month: month || 7,
    from_utc: `${year}-${String(month).padStart(2, "0")}-01T00:00:00Z`,
    to_utc: `${year}-${String(month).padStart(2, "0")}-28T23:59:59Z`,
    linkedin_publication_enabled: true,
    items,
    issues: [],
  };
}

const emptyPending: PendingSupervisionResponse = {
  status: "ok",
  observed_at_utc: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
  read_only: false,
  linkedin_publication_enabled: true,
  variants: [],
  issues: [],
  integration_failures: [],
};

function mockFetch(
  handlers: (url: string, init?: RequestInit) => Response | null = () => null,
  schedule: ScheduleVisibilityResponse = buildSchedule(),
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("pending-supervision")) {
      return new Response(JSON.stringify(emptyPending), {
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
}

function makeClient(
  handlers?: (url: string, init?: RequestInit) => Response | null,
  options?: { canMutate?: boolean; schedule?: ScheduleVisibilityResponse },
) {
  const auth = new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-key");
  if (options?.canMutate === false) {
    vi.spyOn(auth, "canMutate").mockReturnValue(false);
  }
  return new SupervisionApiClient(
    auth,
    mockFetch(handlers, options?.schedule ?? buildSchedule()) as typeof fetch,
  );
}

/**
 * US-040J Vitest coverage (implementation evidence).
 * Does NOT mark Story accepted — Visual DoD + walkthrough remain gated.
 */
describe("US-040J cancelled visibility + reopen", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows calm cancelled chips on Week and Month (~1280 viewport)", async () => {
    const user = userEvent.setup();
    render(<App client={makeClient()} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
    });

    const weekChips = await screen.findAllByTestId("week-event-chip");
    const reopenable = weekChips.find(
      (el) => el.getAttribute("data-item-id") ===
        "linkedin:camp-1:engineering-leadership",
    );
    expect(reopenable).toBeTruthy();
    expect(reopenable).toHaveClass("week-event-chip-cancelled");
    expect(reopenable).not.toHaveClass("week-event-chip-failed");
    expect(reopenable).toHaveAttribute("data-publication-state", "cancelled");
    expect(within(reopenable!).getByText("Cancelled")).toBeInTheDocument();

    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
    });
    const monthBtn = await screen.findAllByTestId("schedule-open-month");
    const monthLi = monthBtn[0].closest("li");
    expect(monthLi).toHaveClass("cal-badge-cancelled");
    expect(monthLi).not.toHaveClass("cal-badge-failed");
    expect(monthLi).toHaveAttribute("data-risk", "cancelled");
  });

  it("cancelled EventModal answers what / why / what-next", async () => {
    const user = userEvent.setup();
    render(<App client={makeClient()} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => expect(screen.getByTestId("week-view")).toBeInTheDocument());
    const chip = (
      await screen.findAllByTestId("week-event-chip")
    ).find(
      (el) =>
        el.getAttribute("data-item-id") ===
        "linkedin:camp-1:engineering-leadership",
    );
    await user.click(chip!);
    await waitFor(() => {
      expect(screen.getByTestId("cancelled-event-view")).toBeInTheDocument();
    });

    expect(screen.getByTestId("cancelled-what")).toHaveTextContent(
      /cancelled planned LinkedIn publication/i,
    );
    expect(screen.getByTestId("cancelled-what")).toHaveTextContent(
      /not LinkedIn API published/i,
    );
    expect(screen.getByTestId("cancelled-why")).toHaveTextContent("operator_choice");
    expect(screen.getByTestId("cancelled-what-next")).toHaveTextContent(
      /reopen and choose a new local schedule/i,
    );
    expect(screen.getByTestId("row-reopen")).toBeInTheDocument();
    expect(screen.queryByTestId("row-edit")).not.toBeInTheDocument();
  });

  it("non-reopenable cancelled item has explicit next-step copy without fake Edit", async () => {
    const user = userEvent.setup();
    const items = cancelledItemsForCurrentWeek().filter(
      (i) => i.variant_id === "failed-cancel",
    );
    render(
      <App client={makeClient(undefined, { schedule: buildSchedule(items) })} />,
    );
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => expect(screen.getByTestId("week-view")).toBeInTheDocument());
    await user.click((await screen.findAllByTestId("week-event-chip"))[0]);
    await waitFor(() => {
      expect(screen.getByTestId("cancelled-event-view")).toBeInTheDocument();
    });
    expect(screen.getByTestId("cancelled-what-next")).toHaveTextContent(
      /not reopen-eligible/i,
    );
    expect(screen.queryByTestId("row-reopen")).not.toBeInTheDocument();
    expect(screen.queryByTestId("row-edit")).not.toBeInTheDocument();
  });

  it("reopen happy path: confirm → schedule → dry-run/confirm → toast", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    let reopenCalls = 0;
    const client = makeClient((url, init) => {
      if (url.includes("/reopen-linkedin-variant") && init?.method === "POST") {
        reopenCalls += 1;
        const body = JSON.parse(String(init.body));
        expect(body.new_scheduled_at_utc).toMatch(/Z$/);
        expect(body.source).toBe("linkedin_variant_supervision_console");
        return new Response(
          JSON.stringify({
            status: "completed",
            campaign_id: "camp-1",
            variant: "engineering-leadership",
            state: "distribution_scheduled",
            publish_state: body.dry_run ? "cancelled" : "pending",
            dry_run: body.dry_run !== false,
            phase: "pre_queue",
            scheduled_at_utc: body.new_scheduled_at_utc,
            errors: [],
            warnings: [],
            metadata_written: body.dry_run === false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return null;
    });

    render(<App client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    const chip = (
      await screen.findAllByTestId("week-event-chip")
    ).find(
      (el) =>
        el.getAttribute("data-item-id") ===
        "linkedin:camp-1:engineering-leadership",
    );
    await user.click(chip!);
    await waitFor(() => expect(screen.getByTestId("row-reopen")).toBeInTheDocument());
    await user.click(screen.getByTestId("row-reopen"));
    await waitFor(() => expect(screen.getByTestId("reopen-panel")).toBeInTheDocument());

    const datetime = screen.getByLabelText(/New scheduled time/i);
    await user.clear(datetime);
    // Far-future local wall time so absolute future check always passes.
    await user.type(datetime, "2099-08-20T10:00");

    expect(screen.getByTestId("reopen-dry-run")).toBeChecked();
    await user.click(screen.getByTestId("reopen-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast-host")).toHaveTextContent(/dry-run/i);
    });
    expect(reopenCalls).toBe(1);

    await user.click(screen.getByTestId("reopen-dry-run"));
    await user.click(screen.getByTestId("reopen-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast-host")).toHaveTextContent(/persisted/i);
    });
    expect(reopenCalls).toBe(2);
    expect(confirmSpy).toHaveBeenCalled();
  });

  it("reopen failure toast maps linkedin_reopen_not_allowed", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const client = makeClient((url, init) => {
      if (url.includes("/reopen-linkedin-variant") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            status: "failed",
            campaign_id: "camp-1",
            variant: "engineering-leadership",
            dry_run: false,
            errors: ["linkedin_reopen_not_allowed"],
            warnings: [],
            metadata_written: false,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return null;
    });

    render(<App client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    const chip = (
      await screen.findAllByTestId("week-event-chip")
    ).find(
      (el) =>
        el.getAttribute("data-item-id") ===
        "linkedin:camp-1:engineering-leadership",
    );
    await user.click(chip!);
    await user.click(await screen.findByTestId("row-reopen"));
    await waitFor(() => expect(screen.getByTestId("reopen-panel")).toBeInTheDocument());
    await user.clear(screen.getByLabelText(/New scheduled time/i));
    await user.type(screen.getByLabelText(/New scheduled time/i), "2099-08-20T10:00");
    await user.click(screen.getByTestId("reopen-dry-run"));
    await user.click(screen.getByTestId("reopen-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast-host")).toHaveTextContent(
        /linkedin_reopen_not_allowed/i,
      );
    });
    expect(SUPERVISION_ERROR_MESSAGES.linkedin_reopen_not_allowed).toMatch(
      /cannot be reopened/i,
    );
  });

  it("read-only session cannot commit reopen", async () => {
    const user = userEvent.setup();
    render(<App client={makeClient(undefined, { canMutate: false })} />);
    await user.click(screen.getByTestId("load-btn"));
    const chip = (
      await screen.findAllByTestId("week-event-chip")
    ).find(
      (el) =>
        el.getAttribute("data-item-id") ===
        "linkedin:camp-1:engineering-leadership",
    );
    await user.click(chip!);
    await waitFor(() => {
      expect(screen.getByTestId("cancelled-what-next")).toHaveTextContent(
        /cannot mutate/i,
      );
    });
    expect(screen.getByTestId("row-reopen")).toBeDisabled();
  });

  it("viewport matrix ~1280 and ~375 covers cancelled chip + modal scenes", async () => {
    const user = userEvent.setup();
    for (const width of [1280, 375]) {
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        writable: true,
        value: width,
      });
      window.dispatchEvent(new Event("resize"));
      const { unmount } = render(<App client={makeClient()} />);
      await user.click(screen.getByTestId("load-btn"));
      await waitFor(() => expect(screen.getByTestId("week-view")).toBeInTheDocument());
      const chip = (
        await screen.findAllByTestId("week-event-chip")
      ).find((el) => el.classList.contains("week-event-chip-cancelled"));
      expect(chip).toBeTruthy();
      await user.click(chip!);
      await waitFor(() => {
        expect(screen.getByTestId("cancelled-what")).toBeInTheDocument();
        expect(screen.getByTestId("cancelled-why")).toBeInTheDocument();
        expect(screen.getByTestId("cancelled-what-next")).toBeInTheDocument();
      });
      unmount();
    }
  });
});
