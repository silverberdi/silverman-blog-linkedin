import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import { SupervisionStoreProvider } from "../models/store";
import { ListView } from "../components/ListView";
import { ScheduleEditorPanel } from "../components/ScheduleEditor";
import { AppShell } from "../components/AppShell";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityResponse,
} from "../api/types";

const samplePayload: PendingSupervisionResponse = {
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

const emptySchedule: ScheduleVisibilityResponse = {
  status: "ok",
  observed_at_utc: "2026-07-18T12:00:00Z",
  read_only: true,
  year: 2026,
  month: 7,
  from_utc: "2026-07-01T00:00:00Z",
  to_utc: "2026-07-31T23:59:59Z",
  linkedin_publication_enabled: false,
  items: [],
  issues: [],
};

function mockFetch(
  handlers: (url: string, init?: RequestInit) => Response | null,
) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("schedule-visibility")) {
      return new Response(JSON.stringify(emptySchedule), {
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

function renderList(client: SupervisionApiClient) {
  return render(
    <SupervisionStoreProvider client={client}>
      <AppShell>
        <ScheduleEditorPanel />
        <ListView />
      </AppShell>
    </SupervisionStoreProvider>,
  );
}

describe("ListView", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("defaults dry-run checkboxes on when opening edit/defer/cancel", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const fetchImpl = mockFetch((url) => {
      if (url.includes("pending-supervision")) {
        return new Response(JSON.stringify(samplePayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return null;
    });
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    const user = userEvent.setup();
    renderList(client);

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getAllByTestId("variant-row").length).toBeGreaterThan(0);
    });

    await user.click(screen.getAllByRole("button", { name: "Edit" })[0]);
    expect(screen.getByTestId("edit-dry-run")).toBeChecked();

    await user.click(screen.getByRole("button", { name: "Close" }));
    await user.click(screen.getAllByRole("button", { name: "Defer" })[0]);
    expect(screen.getByTestId("schedule-editor-panel")).toHaveAttribute(
      "data-entry",
      "list",
    );
    expect(screen.getByTestId("schedule-dry-run")).toBeChecked();

    await user.click(screen.getByTestId("schedule-close"));
    await user.click(screen.getAllByRole("button", { name: "Cancel" })[0]);
    expect(screen.getByTestId("cancel-dry-run")).toBeChecked();
  });

  it("loads pending rows via typed client and wires edit action", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const fetchImpl = mockFetch((url, init) => {
      if (url.includes("pending-supervision")) {
        return new Response(JSON.stringify(samplePayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
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
    renderList(client);

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getAllByText("camp-1").length).toBeGreaterThan(0);
      expect(
        screen.getAllByText("engineering-leadership").length,
      ).toBeGreaterThan(0);
    });

    await user.click(screen.getAllByRole("button", { name: "Edit" })[0]);
    await user.click(screen.getByRole("button", { name: "Submit edit" }));
    await waitFor(() => {
      expect(screen.getByTestId("action-banner").textContent).toMatch(
        /validated \(dry-run, no mutation\)/,
      );
    });
  });
});
