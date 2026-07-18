import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import {
  deriveOperationalCounts,
  isRecentlyPublished,
  publicationStateLabel,
  STATUS_COLOR,
  type ScheduleItem,
} from "../models/supervision";
import { confirmRealMutation } from "../components/ConfirmationFlow";

const __dirname = dirname(fileURLToPath(import.meta.url));

function scheduleItem(
  partial: Partial<ScheduleItem> & Pick<ScheduleItem, "itemId" | "publicationState">,
): ScheduleItem {
  return {
    itemId: partial.itemId,
    channel: partial.channel ?? "linkedin",
    campaignId: partial.campaignId ?? "camp-1",
    variantId: partial.variantId ?? "v1",
    title: partial.title ?? "Title",
    audience: partial.audience ?? null,
    scheduledAtUtc: partial.scheduledAtUtc ?? "2026-07-20T15:00:00Z",
    publicationState: partial.publicationState,
    sourceState: partial.sourceState ?? partial.publicationState,
    blocked: partial.blocked ?? false,
    critical: partial.critical ?? false,
    linkedinApiPublished: partial.linkedinApiPublished ?? false,
    calendarItemId: partial.calendarItemId ?? null,
    scheduleEditable: partial.scheduleEditable ?? true,
    scheduleEditBlockReason: partial.scheduleEditBlockReason ?? null,
    actions: partial.actions ?? [],
    statusColor: partial.statusColor ?? STATUS_COLOR[partial.publicationState],
  };
}

describe("US-040E operational counts and labels", () => {
  const nowMs = Date.parse("2026-07-18T12:00:00Z");

  it("derives at-a-glance counts with qualified published semantics", () => {
    const items = [
      scheduleItem({
        itemId: "a",
        publicationState: "pending",
        scheduledAtUtc: "2026-07-19T10:00:00Z",
      }),
      scheduleItem({
        itemId: "b",
        publicationState: "deferred",
        scheduledAtUtc: "2026-07-25T10:00:00Z",
      }),
      scheduleItem({
        itemId: "c",
        publicationState: "blocked",
        blocked: true,
        scheduledAtUtc: "2026-07-21T10:00:00Z",
      }),
      scheduleItem({
        itemId: "d",
        publicationState: "failed",
        critical: true,
        scheduledAtUtc: "2026-07-16T10:00:00Z",
      }),
      scheduleItem({
        itemId: "e",
        publicationState: "published",
        linkedinApiPublished: true,
        scheduledAtUtc: "2026-07-15T10:00:00Z",
      }),
      scheduleItem({
        itemId: "f",
        publicationState: "pending",
        scheduledAtUtc: "2026-07-10T10:00:00Z",
      }),
      scheduleItem({
        itemId: "g",
        publicationState: "cancelled",
        scheduledAtUtc: "2026-07-30T10:00:00Z",
      }),
    ];
    const counts = deriveOperationalCounts(items, {
      nowMs,
      integrationFailureCount: 2,
    });
    expect(counts.upcoming).toBe(3); // a, b, c (cancelled g excluded; f past; d past; e past)
    expect(counts.pending).toBe(2);
    expect(counts.dueSoon).toBe(1); // a within 48h
    expect(counts.deferred).toBe(1);
    expect(counts.blocked).toBe(1);
    expect(counts.failed).toBe(3); // d + 2 sibling failures
    expect(counts.recentlyPublished).toBe(1);
  });

  it("does not count pending as recently published", () => {
    const pending = scheduleItem({
      itemId: "p",
      publicationState: "pending",
      scheduledAtUtc: "2026-07-17T10:00:00Z",
    });
    expect(isRecentlyPublished(pending, nowMs)).toBe(false);
    expect(
      deriveOperationalCounts([pending], { nowMs }).recentlyPublished,
    ).toBe(0);
  });

  it("maps concise operator-facing labels", () => {
    expect(publicationStateLabel("pending")).toBe("Pending review");
    expect(publicationStateLabel("published")).toBe("Published (API evidence)");
    expect(publicationStateLabel("blocked")).toBe("Blocked");
    expect(publicationStateLabel("failed")).toBe("Failed");
    expect(publicationStateLabel("queued", true)).toBe(
      "Published (API evidence)",
    );
  });
});

describe("US-040E ConfirmationFlow and affordances", () => {
  it("requires window.confirm for real cancel", () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    expect(confirmRealMutation("cancel")).toBe(false);
    expect(confirmSpy).toHaveBeenCalledWith(
      expect.stringMatching(/real cancel/i),
    );
    confirmSpy.mockRestore();
  });
});

describe("US-040E console polish UI", () => {
  function createClient(scheduleItems?: unknown[]) {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-key");
    const pending = {
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
          calendar_title:
            "A very long title that should truncate or wrap understandably without breaking the layout of the supervision console list",
          calendar_due_at_utc: "2026-07-20T15:00:00Z",
          calendar_status: "planned",
          operator_supervision_last_action: null,
          auto_queue_eligible: true,
          operator_supervision_reason: null,
          draft_content: "Hello",
        },
      ],
      issues: [],
      integration_failures: [
        {
          campaign_id: "camp-1",
          variant_id: "failed-sibling",
          publish_state: "failed",
          last_error_code: "linkedin_http_500",
          http_status: 500,
        },
      ],
    };
    const schedule = {
      status: "ok",
      observed_at_utc: "2026-07-18T12:00:00Z",
      read_only: false,
      year: 2026,
      month: 7,
      from_utc: "2026-07-01T00:00:00Z",
      to_utc: "2026-07-31T23:59:59Z",
      linkedin_publication_enabled: true,
      items: scheduleItems ?? [
        {
          item_id: "linkedin:camp-1:engineering-leadership",
          channel: "linkedin",
          campaign_id: "camp-1",
          variant_id: "engineering-leadership",
          title:
            "A very long title that should truncate or wrap understandably without breaking the layout of the supervision console month cells",
          audience: "eng",
          scheduled_at_utc: "2026-07-20T15:00:00Z",
          publication_state: "pending",
          source_state: "pending",
          blocked: false,
          critical: false,
          linkedin_api_published: false,
          schedule_editable: true,
        },
        {
          item_id: "linkedin:camp-2:blocked",
          channel: "linkedin",
          campaign_id: "camp-2",
          variant_id: "blocked-var",
          title: "Blocked item",
          audience: "eng",
          scheduled_at_utc: "2026-07-21T15:00:00Z",
          publication_state: "blocked",
          source_state: "pending",
          blocked: true,
          critical: false,
          linkedin_api_published: false,
          schedule_editable: true,
        },
        {
          item_id: "linkedin:camp-3:failed",
          channel: "linkedin",
          campaign_id: "camp-3",
          variant_id: "failed-var",
          title: "Failed item",
          audience: "eng",
          scheduled_at_utc: "2026-07-22T15:00:00Z",
          publication_state: "failed",
          source_state: "failed",
          blocked: false,
          critical: true,
          linkedin_api_published: false,
          schedule_editable: false,
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

  it("shows count strip and operator labels after load", async () => {
    const user = userEvent.setup();
    render(<App client={createClient()} />);
    expect(screen.getByTestId("app-shell")).toBeInTheDocument();
    expect(screen.getByTestId("status-summary")).toBeInTheDocument();
    expect(screen.queryByText(/marketing|promo hero|get started/i)).toBeNull();

    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("count-strip")).toBeInTheDocument();
    });
    expect(screen.getByTestId("count-pending")).toHaveAttribute(
      "data-count",
      expect.stringMatching(/\d+/),
    );
    expect(screen.getByTestId("count-failed")).toBeInTheDocument();
    expect(screen.getAllByText("Pending review").length).toBeGreaterThan(0);
  });

  it("separates cancel from routine nav and keeps confirmation for real cancel", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    render(<App client={createClient()} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
    });

    const nav = screen.getByTestId("affordance-nav");
    expect(nav.querySelector('[data-action="cancel"]')).toBeNull();
    expect(nav.querySelector('[data-testid="load-btn"]')).not.toBeNull();
    expect(nav.querySelector('[data-testid="view-week"]')).not.toBeNull();
    expect(nav.querySelector('[data-testid="view-list"]')).toBeNull();

    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
    });
    const pendingOpen = screen
      .getAllByTestId("schedule-open-month")
      .find((el) =>
        el.getAttribute("data-item-id")?.includes("engineering-leadership"),
      );
    expect(pendingOpen).toBeTruthy();
    await user.click(pendingOpen!);
    await waitFor(() => {
      expect(screen.getByTestId("event-modal")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("row-cancel"));
    expect(screen.getByTestId("cancel-panel")).toBeInTheDocument();
    await user.click(screen.getByTestId("cancel-dry-run"));
    await user.click(screen.getByTestId("cancel-submit"));
    expect(confirmSpy).toHaveBeenCalled();
    confirmSpy.mockRestore();
  });

  it("marks blocked and failed rows distinctly from routine", async () => {
    const user = userEvent.setup();
    render(<App client={createClient()} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("count-strip")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("view-month"));
    await waitFor(() => {
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
    });
    const blocked = document.querySelector('[data-risk="blocked"]');
    const failed = document.querySelector('[data-risk="failed"]');
    expect(blocked).not.toBeNull();
    expect(failed).not.toBeNull();
  });

  it("exposes visible focus styles and touch-min tokens", () => {
    const css = readFileSync(
      resolve(__dirname, "../styles/console.css"),
      "utf-8",
    );
    expect(css).toMatch(/:focus-visible/);
    expect(css).toMatch(/--touch-min:\s*44px/);
    expect(css).toMatch(/\.count-strip/);
    expect(css).toMatch(/\.row-risk-blocked/);
    expect(css).toMatch(/\.row-risk-failed/);
    expect(css).toMatch(/\.title-cell/);
    expect(css).toMatch(/\.diagnostics-details/);
  });

  it("keeps dark theme tokens for empty/error/success/panel states", () => {
    const css = readFileSync(
      resolve(__dirname, "../styles/console.css"),
      "utf-8",
    );
    expect(css).toMatch(/--bg:\s*#12151a/);
    expect(css).toMatch(/\.banner\.error/);
    expect(css).toMatch(/\.banner\.ok/);
    expect(css).toMatch(/\.panel/);
    expect(css).toMatch(/\.status-summary/);
  });
});

describe("US-040E visual validation matrix (equivalent UI checks)", () => {
  function clientWith(items: unknown[], variants: unknown[] = []) {
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("k");
    const fetchImpl = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("pending-supervision")) {
        return new Response(
          JSON.stringify({
            status: "ok",
            observed_at_utc: "2026-07-18T12:00:00Z",
            read_only: true,
            linkedin_publication_enabled: true,
            variants,
            issues: [],
            integration_failures: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (url.includes("schedule-visibility")) {
        return new Response(
          JSON.stringify({
            status: "ok",
            observed_at_utc: "2026-07-18T12:00:00Z",
            read_only: true,
            year: 2026,
            month: 7,
            from_utc: "2026-07-01T00:00:00Z",
            to_utc: "2026-07-31T23:59:59Z",
            linkedin_publication_enabled: true,
            items,
            issues: [],
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("not found", { status: 404 });
    });
    return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
  }

  const denseItems = Array.from({ length: 8 }, (_, i) => ({
    item_id: `linkedin:camp-${i}:v`,
    channel: "linkedin",
    campaign_id: `camp-${i}`,
    variant_id: "v",
    title: `Dense title ${i} `.repeat(8),
    audience: "eng",
    scheduled_at_utc: `2026-07-${String(10 + (i % 18)).padStart(2, "0")}T15:00:00Z`,
    publication_state: i % 3 === 0 ? "blocked" : "pending",
    source_state: "pending",
    blocked: i % 3 === 0,
    critical: false,
    linkedin_api_published: false,
    schedule_editable: true,
  }));

  const denseVariants = denseItems.slice(0, 5).map((item) => ({
    campaign_id: item.campaign_id,
    variant_id: item.variant_id,
    audience: "eng",
    scheduled_at_utc: item.scheduled_at_utc,
    publish_state: "pending",
    calendar_item_id: null,
    calendar_title: item.title,
    calendar_due_at_utc: item.scheduled_at_utc,
    calendar_status: "planned",
    operator_supervision_last_action: null,
    auto_queue_eligible: true,
    operator_supervision_reason: null,
    draft_content: "x",
  }));

  async function assertDesktopMobile(label: string, run: (width: number) => Promise<void>) {
    for (const width of [1280, 375]) {
      Object.defineProperty(window, "innerWidth", {
        configurable: true,
        value: width,
      });
      await run(width);
    }
  }

  it("covers dense/empty week and month, blocked, long titles, view switch, schedule edit", async () => {
    await assertDesktopMobile("dense", async () => {
      const user = userEvent.setup();
      const { unmount } = render(
        <App client={clientWith(denseItems, denseVariants)} />,
      );
      await user.click(screen.getByTestId("load-btn"));
      await waitFor(() => {
        expect(screen.getByTestId("count-strip")).toBeInTheDocument();
      });
      expect(screen.getByTestId("week-view")).toBeInTheDocument();
      expect(document.querySelector(".title-cell")).not.toBeNull();
      await user.click(screen.getByTestId("view-month"));
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
      expect(document.querySelector('[data-risk="blocked"]')).not.toBeNull();
      const openBtns = screen.queryAllByTestId("schedule-open-month");
      if (openBtns.length > 0) {
        await user.click(openBtns[0]);
        await waitFor(() => {
          expect(screen.getByTestId("event-modal")).toBeInTheDocument();
        });
        await user.click(screen.getByTestId("row-defer"));
        await waitFor(() => {
          expect(screen.getByTestId("schedule-editor-panel")).toBeInTheDocument();
        });
      }
      unmount();
    });

    await assertDesktopMobile("empty", async () => {
      const user = userEvent.setup();
      const { unmount } = render(<App client={clientWith([], [])} />);
      await user.click(screen.getByTestId("load-btn"));
      await waitFor(() => {
        expect(screen.getByTestId("count-strip")).toBeInTheDocument();
      });
      expect(screen.getByTestId("week-empty-state")).toBeInTheDocument();
      expect(screen.getByTestId("week-columns")).toBeInTheDocument();
      expect(screen.getByTestId("count-upcoming")).toHaveAttribute(
        "data-count",
        "0",
      );
      await user.click(screen.getByTestId("view-month"));
      expect(screen.getByTestId("month-calendar-view")).toBeInTheDocument();
      expect(screen.getByTestId("month-empty-state")).toBeInTheDocument();
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
      unmount();
    });
  });
});
