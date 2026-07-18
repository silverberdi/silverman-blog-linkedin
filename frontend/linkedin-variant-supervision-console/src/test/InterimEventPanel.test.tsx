import { describe, expect, it, vi, beforeEach } from "vitest";
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
  read_only: true,
  linkedin_publication_enabled: false,
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
  read_only: true,
  year: 2026,
  month: 7,
  from_utc: "2026-07-01T00:00:00Z",
  to_utc: "2026-07-31T23:59:59Z",
  linkedin_publication_enabled: false,
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
  handlers: (url: string, init?: RequestInit) => Response | null,
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

async function openInterimFromMonth(user: ReturnType<typeof userEvent.setup>) {
  if (!screen.queryByTestId("month-calendar-view")) {
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("view-month"));
  }
  await waitFor(() => {
    expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
  });
  const open = await screen.findByTestId("schedule-open-month");
  await user.click(open);
  await waitFor(() => {
    expect(screen.getByTestId("interim-event-panel")).toBeInTheDocument();
  });
}

describe("Interim calendar actions (US-040G)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("defaults dry-run checkboxes on when opening edit/defer/cancel from interim", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const client = new SupervisionApiClient(
      auth,
      mockFetch(() => null) as typeof fetch,
    );
    const user = userEvent.setup();
    render(<App client={client} />);
    await openInterimFromMonth(user);

    expect(screen.getByTestId("interim-h-hint").textContent).toMatch(/US-040H/);
    expect(screen.getByTestId("interim-h-hint").textContent).not.toMatch(
      /event modal product shipped/i,
    );

    await user.click(screen.getByTestId("row-edit"));
    expect(screen.getByTestId("edit-dry-run")).toBeChecked();

    await user.click(screen.getByRole("button", { name: "Close" }));
    await openInterimFromMonth(user);
    await user.click(screen.getByTestId("row-defer"));
    expect(screen.getByTestId("schedule-editor-panel")).toHaveAttribute(
      "data-entry",
      "month",
    );
    expect(screen.getByTestId("schedule-dry-run")).toBeChecked();

    await user.click(screen.getByTestId("schedule-close"));
    await user.click(screen.getByTestId("row-cancel"));
    expect(screen.getByTestId("cancel-dry-run")).toBeChecked();
  });

  it("loads pending rows via typed client and wires edit action from calendar", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const fetchImpl = mockFetch((url, init) => {
      if (url.includes("correct-linkedin-variant")) {
        expect(init?.method).toBe("POST");
        const body = JSON.parse(String(init?.body));
        expect(body.dry_run).toBe(true);
        expect(body.draft_content).toBe("Hello draft");
        return new Response(
          JSON.stringify({
            status: "completed",
            campaign_id: "camp-1",
            variant: "engineering-leadership",
            state: "flow_a_complete",
            publish_state: "pending",
            dry_run: true,
            phase: "pre_queue",
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
    render(<App client={client} />);
    await openInterimFromMonth(user);

    await user.click(screen.getByTestId("row-edit"));
    await user.click(screen.getByRole("button", { name: "Submit edit" }));
    await waitFor(() => {
      expect(screen.getByTestId("action-banner").textContent).toMatch(
        /validated \(dry-run, no mutation\)/,
      );
    });
  });
});
