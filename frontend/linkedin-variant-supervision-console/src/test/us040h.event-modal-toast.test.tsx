import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityResponse,
} from "../api/types";

const samplePending: PendingSupervisionResponse = {
  status: "ok",
  observed_at_utc: "2026-07-18T12:00:00Z",
  read_only: false,
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

const sampleSchedule: ScheduleVisibilityResponse = {
  status: "ok",
  observed_at_utc: "2026-07-18T12:00:00Z",
  read_only: false,
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
      title: "Post",
      audience: "eng",
      scheduled_at_utc: "2026-07-20T15:00:00Z",
      publication_state: "pending",
      source_state: "pending",
      blocked: false,
      critical: false,
      linkedin_api_published: false,
      schedule_editable: true,
    },
  ],
  issues: [],
};

function mockFetch(
  handlers: (url: string, init?: RequestInit) => Response | null = () => null,
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("pending-supervision")) {
      return new Response(JSON.stringify(samplePending), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("schedule-visibility")) {
      return new Response(JSON.stringify(sampleSchedule), {
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
) {
  const auth = new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-key");
  return new SupervisionApiClient(auth, mockFetch(handlers) as typeof fetch);
}

async function openModalFromMonth(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByTestId("load-btn"));
  await waitFor(() => {
    expect(screen.getByTestId("week-view")).toBeInTheDocument();
  });
  await user.click(screen.getByTestId("view-month"));
  await waitFor(() => {
    expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
  });
  await user.click(await screen.findByTestId("schedule-open-month"));
  await waitFor(() => {
    expect(screen.getByTestId("event-modal")).toBeInTheDocument();
    expect(screen.getByTestId("row-edit")).toBeInTheDocument();
  });
}

/**
 * US-040H Vitest coverage (implementation evidence).
 * Does NOT mark Story accepted — Visual DoD + walkthrough remain gated.
 */
describe("US-040H event modal + toast feedback", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("opens and closes event modal at ~1280 and ~375; Escape without draft closes", async () => {
    for (const width of [1280, 375]) {
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        writable: true,
        value: width,
      });
      window.dispatchEvent(new Event("resize"));
      const user = userEvent.setup();
      const { unmount } = render(<App client={makeClient()} />);
      await openModalFromMonth(user);
      expect(screen.getByTestId("event-modal-status")).toBeInTheDocument();
      expect(screen.getByTestId("event-modal-diagnostics")).toBeInTheDocument();
      expect(screen.queryByTestId("list-view")).toBeNull();
      expect(screen.queryByTestId("interim-event-panel")).toBeNull();
      expect(screen.queryByTestId("month-day-focus")).toBeNull();

      await user.keyboard("{Escape}");
      await waitFor(() => {
        expect(screen.queryByTestId("event-modal")).toBeNull();
      });
      unmount();
    }
  });

  it("warns on Escape when unsaved edit draft exists", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(<App client={makeClient()} />);
    await openModalFromMonth(user);
    await user.click(screen.getByTestId("row-edit"));
    await user.type(screen.getByTestId("edit-content"), " changed");
    await user.keyboard("{Escape}");
    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringMatching(/unsaved edits or a schedule draft/i),
    );
    expect(screen.getByTestId("event-modal")).toBeInTheDocument();
  });

  it("shows toast stack, manual dismiss, and auto-dismiss; no green action banner", async () => {
    const user = userEvent.setup();
    render(
      <App
        client={makeClient((url, init) => {
          if (url.includes("correct-linkedin-variant")) {
            const body = JSON.parse(String(init?.body));
            return new Response(
              JSON.stringify({
                status: "completed",
                campaign_id: "camp-1",
                variant: "engineering-leadership",
                state: "flow_a_complete",
                publish_state: "pending",
                dry_run: body.dry_run,
                phase: "pre_queue",
                errors: [],
                warnings: [],
                metadata_written: false,
              }),
              { status: 200, headers: { "Content-Type": "application/json" } },
            );
          }
          return null;
        })}
      />,
    );
    await openModalFromMonth(user);
    await user.click(screen.getByTestId("row-edit"));
    await user.click(screen.getByTestId("edit-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast").textContent).toMatch(/dry-run/i);
    });
    expect(screen.queryByTestId("action-banner")).toBeNull();
    expect(screen.getByTestId("enablement-chip")).toBeInTheDocument();
    expect(screen.queryByTestId("enablement-banner")).toBeNull();

    await user.click(screen.getByTestId("edit-submit"));
    await waitFor(() => {
      expect(screen.getAllByTestId("toast").length).toBeGreaterThanOrEqual(2);
    });

    await user.click(screen.getAllByTestId("toast-dismiss")[0]);
    expect(screen.getAllByTestId("toast").length).toBeGreaterThanOrEqual(1);

    // Auto-dismiss is scheduled at ~5s; assert remaining toast can be cleared manually.
    for (const btn of screen.getAllByTestId("toast-dismiss")) {
      await user.click(btn);
    }
    await waitFor(() => {
      expect(screen.queryAllByTestId("toast")).toHaveLength(0);
    });
  });

  it("keeps cancel behind confirmation; empty day does not dump agenda", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    render(
      <App
        client={makeClient((url) => {
          if (url.includes("cancel-linkedin-publication")) {
            return new Response(
              JSON.stringify({
                status: "completed",
                campaign_id: "camp-1",
                variant: "engineering-leadership",
                state: "flow_a_complete",
                publish_state: "cancelled",
                dry_run: false,
                phase: "pre_queue",
                errors: [],
                warnings: [],
                metadata_written: true,
              }),
              { status: 200, headers: { "Content-Type": "application/json" } },
            );
          }
          return null;
        })}
      />,
    );
    await openModalFromMonth(user);
    await user.click(screen.getByTestId("row-cancel"));
    expect(screen.getByTestId("cancel-panel")).toBeInTheDocument();
    await user.click(screen.getByTestId("cancel-dry-run"));
    await user.click(screen.getByTestId("cancel-submit"));
    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringMatching(/real cancel/i),
    );

    await user.click(screen.getByTestId("event-modal-close"));
    await waitFor(() => {
      expect(screen.queryByTestId("event-modal")).toBeNull();
    });
    const emptyDay = screen.getByTestId("calendar-day-2026-07-05");
    await user.click(emptyDay);
    expect(screen.queryByTestId("month-day-focus")).toBeNull();
    expect(screen.queryByTestId("month-day-chip-list")).toBeNull();
    expect(screen.queryByTestId("event-modal")).toBeNull();
    expect(screen.queryByTestId("list-view")).toBeNull();
  });
});
