import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { MemoryBearerAuthProvider } from "../api/auth";
import { SupervisionApiClient } from "../api/client";
import { countActiveFilters, defaultFilters } from "../models/supervision";

function createClient() {
  const auth = new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-key");
  const pending = {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    linkedin_publication_enabled: false,
    variants: [
      {
        campaign_id: "l-campaign",
        variant_id: "pending-card",
        audience: "founders",
        scheduled_at_utc: "2026-07-20T15:00:00Z",
        publish_state: "pending",
        calendar_item_id: "cal-l-1",
        calendar_title: "Pending card for filters modal",
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
        item_id: "linkedin:l-campaign:pending-card",
        channel: "linkedin",
        campaign_id: "l-campaign",
        variant_id: "pending-card",
        title: "Pending card for filters modal",
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
        item_id: "linkedin:l-campaign:blocked-card",
        channel: "linkedin",
        campaign_id: "l-campaign",
        variant_id: "blocked-card",
        title: "Blocked item for chip focus",
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

async function openFiltersModal(
  user: ReturnType<typeof userEvent.setup>,
): Promise<HTMLElement> {
  await user.click(screen.getByTestId("header-filters-btn"));
  const modal = await screen.findByTestId("filters-modal");
  expect(modal).toHaveAttribute("role", "dialog");
  expect(modal).toHaveAttribute("aria-modal", "true");
  return modal;
}

describe("countActiveFilters (US-040L D3)", () => {
  it("returns 0 for defaults and counts each non-default field", () => {
    expect(countActiveFilters(defaultFilters())).toBe(0);
    expect(
      countActiveFilters({ ...defaultFilters(), channel: "linkedin" }),
    ).toBe(1);
    expect(
      countActiveFilters({ ...defaultFilters(), campaignQuery: "  camp  " }),
    ).toBe(1);
    expect(
      countActiveFilters({ ...defaultFilters(), blockedOnly: true }),
    ).toBe(1);
    expect(
      countActiveFilters({ ...defaultFilters(), dueSoonOnly: true }),
    ).toBe(1);
    expect(
      countActiveFilters({
        ...defaultFilters(),
        publicationStates: ["pending", "blocked"],
      }),
    ).toBe(1);
    expect(
      countActiveFilters({
        ...defaultFilters(),
        channel: "blog",
        blockedOnly: true,
        publicationStates: ["failed"],
      }),
    ).toBe(3);
  });
});

describe("US-040L Search/Filters header modal", () => {
  async function assertAtWidths(run: () => Promise<void>) {
    for (const width of [1280, 375] as const) {
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        value: width,
      });
      await run();
    }
  }

  it("omits permanent filter-dock; header Filters opens modal with full control set", async () => {
    await assertAtWidths(async () => {
      const user = userEvent.setup();
      const { unmount } = render(<App client={createClient()} />);

      expect(document.querySelector(".filter-dock")).toBeNull();
      expect(screen.queryByTestId("affordance-filters")).toBeNull();
      expect(screen.queryByTestId("filters")).toBeNull();
      expect(screen.getByTestId("header-filters-btn")).toBeInTheDocument();
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
      expect(screen.queryByTestId("list-view")).toBeNull();

      const modal = await openFiltersModal(user);
      const filters = within(modal).getByTestId("filters");
      expect(within(filters).getByTestId("filter-channel")).toBeInTheDocument();
      expect(within(filters).getByTestId("filter-campaign")).toBeInTheDocument();
      expect(within(filters).getByTestId("filter-blocked")).toBeInTheDocument();
      expect(within(filters).getByTestId("filter-due-soon")).toBeInTheDocument();
      expect(within(filters).getByTestId("filter-states")).toBeInTheDocument();
      expect(within(filters).getByTestId("filter-state-completed")).toBeInTheDocument();
      expect(within(filters).getByTestId("filters-reset")).toBeInTheDocument();
      unmount();
    });
  });

  it("shows calm active cue when filtered; cue clears on reset; dismiss keeps state", async () => {
    await assertAtWidths(async () => {
      const user = userEvent.setup();
      const { unmount } = render(<App client={createClient()} />);

      expect(screen.queryByTestId("filters-active-badge")).toBeNull();

      await openFiltersModal(user);
      await user.click(screen.getByTestId("filter-blocked"));
      expect(screen.getByTestId("filters-active-badge")).toHaveTextContent("1");
      expect(screen.getByTestId("header-filters-btn")).toHaveClass("is-active");

      await user.click(screen.getByTestId("filters-modal-close"));
      expect(screen.queryByTestId("filters-modal")).toBeNull();
      expect(screen.getByTestId("filters-active-badge")).toHaveTextContent("1");

      await openFiltersModal(user);
      expect(screen.getByTestId("filter-blocked")).toBeChecked();

      await user.click(screen.getByTestId("filters-reset"));
      expect(screen.queryByTestId("filters-active-badge")).toBeNull();
      expect(screen.getByTestId("filter-blocked")).not.toBeChecked();
      unmount();
    });
  });

  it("applies metric chip focus without modal; modal reflects chip state", async () => {
    await assertAtWidths(async () => {
      const user = userEvent.setup();
      const { unmount } = render(<App client={createClient()} />);
      await user.click(screen.getByTestId("load-btn"));
      await waitFor(() => {
        expect(screen.getByTestId("count-blocked")).toHaveAttribute(
          "data-count",
          "1",
        );
      });

      expect(screen.queryByTestId("filters-modal")).toBeNull();
      await user.click(screen.getByTestId("count-blocked"));
      expect(screen.queryByTestId("filters-modal")).toBeNull();
      expect(screen.getByTestId("filters-active-badge")).toHaveTextContent("1");
      expect(screen.getByTestId("week-view")).toBeInTheDocument();

      await openFiltersModal(user);
      expect(screen.getByTestId("filter-blocked")).toBeChecked();
      unmount();
    });
  });

  it("preserves Week/Month empty Clear filters without requiring the modal", async () => {
    await assertAtWidths(async () => {
      const user = userEvent.setup();
      const { unmount } = render(<App client={createClient()} />);
      await user.click(screen.getByTestId("load-btn"));
      await waitFor(() => {
        expect(
          screen.getAllByTestId("week-event-chip").length,
        ).toBeGreaterThan(0);
      });

      await openFiltersModal(user);
      await user.type(screen.getByTestId("filter-campaign"), "no-such-campaign");
      await user.click(screen.getByTestId("filters-modal-close"));

      await waitFor(() => {
        expect(screen.getByTestId("week-empty-state")).toBeInTheDocument();
      });
      expect(screen.getByTestId("filters-active-badge")).toBeInTheDocument();
      expect(screen.getByTestId("week-clear-filters")).toBeInTheDocument();

      await user.click(screen.getByTestId("week-clear-filters"));
      await waitFor(() => {
        expect(screen.queryByTestId("filters-active-badge")).toBeNull();
      });
      expect(screen.queryByTestId("week-empty-state")).toBeNull();

      await user.click(screen.getByTestId("view-month"));
      await openFiltersModal(user);
      await user.type(screen.getByTestId("filter-campaign"), "still-missing");
      await user.click(screen.getByTestId("filters-modal-close"));
      await waitFor(() => {
        expect(screen.getByTestId("month-empty-state")).toBeInTheDocument();
      });
      await user.click(screen.getByTestId("month-clear-filters"));
      await waitFor(() => {
        expect(screen.queryByTestId("filters-active-badge")).toBeNull();
      });
      unmount();
    });
  });

  it("dismisses via Escape and backdrop without clearing filters", async () => {
    const user = userEvent.setup();
    render(<App client={createClient()} />);
    await openFiltersModal(user);
    await user.click(screen.getByTestId("filter-due-soon"));
    expect(screen.getByTestId("filters-active-badge")).toHaveTextContent("1");

    await user.keyboard("{Escape}");
    expect(screen.queryByTestId("filters-modal")).toBeNull();
    expect(screen.getByTestId("filters-active-badge")).toHaveTextContent("1");

    await openFiltersModal(user);
    expect(screen.getByTestId("filter-due-soon")).toBeChecked();
    await user.click(screen.getByTestId("filters-modal-backdrop"));
    expect(screen.queryByTestId("filters-modal")).toBeNull();
    expect(screen.getByTestId("filters-active-badge")).toHaveTextContent("1");
  });
});
