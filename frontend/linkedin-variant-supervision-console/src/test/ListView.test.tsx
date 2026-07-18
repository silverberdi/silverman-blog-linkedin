import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import { SupervisionStoreProvider } from "../models/store";
import { ListView } from "../components/ListView";
import { AppShell } from "../components/AppShell";
import type { PendingSupervisionResponse } from "../api/types";

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

function renderList(client: SupervisionApiClient) {
  return render(
    <SupervisionStoreProvider client={client}>
      <AppShell>
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
    const fetchImpl = vi.fn(async () =>
      new Response(JSON.stringify(samplePayload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    const user = userEvent.setup();
    renderList(client);

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getAllByTestId("variant-row")).toHaveLength(1);
    });

    await user.click(screen.getByRole("button", { name: "Edit" }));
    expect(screen.getByTestId("edit-dry-run")).toBeChecked();

    await user.click(screen.getByRole("button", { name: "Close" }));
    await user.click(screen.getByRole("button", { name: "Defer" }));
    expect(screen.getByTestId("defer-dry-run")).toBeChecked();

    await user.click(screen.getByRole("button", { name: "Close" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.getByTestId("cancel-dry-run")).toBeChecked();
  });

  it("loads pending rows via typed client and wires edit action", async () => {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
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
      return new Response("not found", { status: 404 });
    });
    const client = new SupervisionApiClient(auth, fetchImpl as typeof fetch);
    const user = userEvent.setup();
    renderList(client);

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByText("camp-1")).toBeInTheDocument();
      expect(screen.getByText("engineering-leadership")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Edit" }));
    await user.click(screen.getByRole("button", { name: "Submit edit" }));
    await waitFor(() => {
      expect(screen.getByTestId("action-banner").textContent).toMatch(
        /validated \(dry-run, no mutation\)/,
      );
    });
  });
});
