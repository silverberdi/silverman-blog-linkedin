import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { MemoryBearerAuthProvider } from "../api/auth";
import { SupervisionApiClient } from "../api/client";

const __dirname = dirname(fileURLToPath(import.meta.url));

function createUxClient() {
  const auth = new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-key");
  const pending = {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    linkedin_publication_enabled: false,
    variants: [
      {
        campaign_id: "ux-campaign",
        variant_id: "operator-friendly-card",
        audience: "founders",
        scheduled_at_utc: "2026-07-20T15:00:00Z",
        publish_state: "pending",
        calendar_item_id: "cal-ux-1",
        calendar_title: "Modern console UX should make this item scannable",
        calendar_due_at_utc: "2026-07-20T15:00:00Z",
        calendar_status: "planned",
        operator_supervision_last_action: null,
        auto_queue_eligible: true,
        operator_supervision_reason: null,
        draft_content: "Draft body",
      },
    ],
    issues: [],
    integration_failures: [],
  };
  const schedule = {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    year: 2026,
    month: 7,
    from_utc: "2026-07-01T00:00:00Z",
    to_utc: "2026-07-31T23:59:59Z",
    linkedin_publication_enabled: false,
    items: [
      {
        item_id: "linkedin:ux-campaign:operator-friendly-card",
        channel: "linkedin",
        campaign_id: "ux-campaign",
        variant_id: "operator-friendly-card",
        title: "Modern console UX should make this item scannable",
        audience: "founders",
        scheduled_at_utc: "2026-07-20T15:00:00Z",
        publication_state: "pending",
        source_state: "pending",
        blocked: false,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
      },
      {
        item_id: "linkedin:ux-campaign:blocked-card",
        channel: "linkedin",
        campaign_id: "ux-campaign",
        variant_id: "blocked-card",
        title: "Blocked item needs immediate attention",
        audience: "founders",
        scheduled_at_utc: "2026-07-21T15:00:00Z",
        publication_state: "blocked",
        source_state: "pending",
        blocked: true,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
      },
    ],
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
  return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
}

describe("US-040F modern operational UX redesign", () => {
  it("renders a wide app workspace with modern shell controls and card triage", async () => {
    const user = userEvent.setup();
    render(<App client={createUxClient()} />);

    expect(screen.getByTestId("app-shell")).toHaveClass("console-shell");
    expect(document.querySelector(".app-bar")).not.toBeNull();
    expect(document.querySelector(".session-strip")).not.toBeNull();
    expect(document.querySelector(".filter-dock")).not.toBeNull();
    expect(screen.queryByText(/POST \//)).toBeNull();

    await user.click(screen.getByTestId("load-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("count-blocked")).toHaveAttribute("data-count", "1");
    });
    expect(document.querySelector(".triage-layout")).not.toBeNull();
    expect(document.querySelector(".variant-card-list")).not.toBeNull();
    expect(screen.getByTestId("variant-card")).toHaveClass("list-card");

    await user.click(screen.getByTestId("variant-row"));
    expect(screen.getByTestId("selected-detail")).toBeInTheDocument();
  });

  it("lets metric cards drive focus without manual filter setup", async () => {
    const user = userEvent.setup();
    render(<App client={createUxClient()} />);
    await user.click(screen.getByTestId("load-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("filter-blocked")).not.toBeChecked();
    });
    await user.click(screen.getByTestId("count-blocked"));
    expect(screen.getByTestId("filter-blocked")).toBeChecked();
  });

  it("resets prior metric focus before applying a new metric filter", async () => {
    const user = userEvent.setup();
    render(<App client={createUxClient()} />);
    await user.click(screen.getByTestId("load-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("count-pending")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("count-blocked"));
    expect(screen.getByTestId("filter-blocked")).toBeChecked();

    await user.click(screen.getByTestId("count-pending"));
    expect(screen.getByTestId("filter-blocked")).not.toBeChecked();
    expect(screen.getByTestId("filter-state-pending")).toBeChecked();

    await user.click(screen.getByTestId("count-upcoming"));
    expect(screen.getByTestId("filter-state-pending")).not.toBeChecked();
  });

  it("keeps UX-specific responsive and master-detail styles in CSS", () => {
    const css = readFileSync(
      resolve(__dirname, "../styles/console.css"),
      "utf-8",
    );
    expect(css).toMatch(/width:\s*min\(100%,\s*1680px\)/);
    expect(css).toMatch(/\.app-bar/);
    expect(css).toMatch(/\.triage-layout/);
    expect(css).toMatch(/\.detail-drawer/);
    expect(css).toMatch(/\.variant-card-list/);
    expect(css).toMatch(/@media\s*\(max-width:\s*860px\)/);
  });
});
