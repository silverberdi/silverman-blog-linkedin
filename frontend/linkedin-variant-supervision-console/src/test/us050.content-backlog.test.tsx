import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { MemoryBearerAuthProvider } from "../api/auth";
import { SupervisionApiClient } from "../api/client";
import type { EditorialContentBacklogItem } from "../api/types";

const DEFAULT_SETTINGS = {
  settings_id: "default",
  source: "defaults",
  updated_at_utc: null,
  row_version: null,
  operator_timezone: "America/Chicago",
  gap_trigger_enabled: false,
  gap_scan_mode: "next_week",
  weekly_run_local_day: "friday",
  weekly_run_local_time: "15:00",
  min_lead_days: 5,
  gap_posts_threshold: 0,
  max_drafts_per_weekly_run: 2,
  density_max_per_local_day: 2,
};

function basePending() {
  return {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    linkedin_publication_enabled: false,
    variants: [],
    issues: [],
    integration_failures: [],
  };
}

function baseSchedule() {
  return {
    status: "ok",
    observed_at_utc: "2026-07-18T12:00:00Z",
    read_only: false,
    year: 2026,
    month: 7,
    from_utc: "2026-07-01T00:00:00Z",
    to_utc: "2026-07-31T23:59:59Z",
    linkedin_publication_enabled: false,
    items: [],
    issues: [],
  };
}

function sampleItem(
  overrides?: Partial<EditorialContentBacklogItem>,
): EditorialContentBacklogItem {
  return {
    item_id: "item-1",
    topic: "Domain-first API boundaries",
    audience: "Senior engineering leaders",
    objective: "Show practical trade-offs",
    format: "both",
    priority: "high",
    status: "idea",
    target_date: "2026-08-01",
    linkedin_derivatives: [],
    depends_on_item_ids: [],
    queue_rank: 0,
    created_at_utc: "2026-07-20T12:00:00Z",
    updated_at_utc: "2026-07-20T12:00:00Z",
    row_version: 1,
    ...overrides,
  };
}

function createAppClient(options?: {
  initialItems?: EditorialContentBacklogItem[];
  backlogUpdate?: (body: unknown) => Response;
  backlogReorder?: (body: unknown) => Response;
}) {
  const auth = new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-key");

  let items: EditorialContentBacklogItem[] = [...(options?.initialItems ?? [])];

  const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/flow-a/linkedin-variants/pending-supervision")) {
      return new Response(JSON.stringify(basePending()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("/flow-a/schedule-visibility")) {
      return new Response(JSON.stringify(baseSchedule()), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("/flow-b/gap-operator-settings")) {
      return new Response(JSON.stringify(DEFAULT_SETTINGS), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("/flow-b/pending-approval-drafts")) {
      return new Response(
        JSON.stringify({
          status: "ok",
          drafts: [],
          observed_at_utc: "2026-07-20T12:00:00Z",
          filter_status: null,
          count: 0,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    if (url.endsWith("/editorial/content-backlog/reorder")) {
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      if (options?.backlogReorder) {
        return options.backlogReorder(body);
      }
      const orderedIds: string[] = body.ordered_item_ids ?? [];
      const byId = new Map(items.map((row) => [row.item_id, row]));
      items = orderedIds.map((id, rank) => {
        const current = byId.get(id)!;
        return { ...current, queue_rank: rank, row_version: current.row_version + 1 };
      });
      return new Response(
        JSON.stringify({ status: "ok", items, count: items.length }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    if (url.match(/\/editorial\/content-backlog\/[^/?]+/) && !url.endsWith("/content-backlog")) {
      const method = (init?.method || "GET").toUpperCase();
      if (method === "PUT") {
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        if (options?.backlogUpdate) {
          return options.backlogUpdate(body);
        }
        const itemId = url.split("/").pop()!;
        const updated = {
          ...sampleItem(),
          ...body,
          item_id: itemId,
          depends_on_item_ids: body.depends_on_item_ids ?? [],
          queue_rank: body.queue_rank ?? 0,
          row_version: 2,
          updated_at_utc: "2026-07-21T12:00:00Z",
        };
        items = items.map((row) => (row.item_id === itemId ? updated : row));
        return new Response(JSON.stringify(updated), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    if (url.includes("/editorial/content-backlog")) {
      const method = (init?.method || "GET").toUpperCase();
      if (method === "GET") {
        return new Response(
          JSON.stringify({ status: "ok", items, count: items.length }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (method === "POST") {
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        const created = sampleItem({
          ...body,
          item_id: `item-created-${items.length + 1}`,
          depends_on_item_ids: body.depends_on_item_ids ?? [],
          queue_rank: items.length,
          row_version: 1,
        });
        items = [...items, created];
        return new Response(JSON.stringify(created), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    return new Response(JSON.stringify({ detail: "not found" }), { status: 404 });
  });

  return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
}

describe("US-050 Content backlog dependencies and prioritization", () => {
  it("edits dependencies and shows resolved labels", async () => {
    const user = userEvent.setup();
    const client = createAppClient({
      initialItems: [
        sampleItem({ item_id: "item-a", topic: "Foundation", queue_rank: 0 }),
        sampleItem({
          item_id: "item-b",
          topic: "Follow-on",
          queue_rank: 1,
          depends_on_item_ids: [],
        }),
      ],
    });
    render(<App client={client} />);

    await user.click(screen.getByTestId("header-content-backlog-btn"));
    const modal = await screen.findByTestId("content-backlog-modal");
    await waitFor(() => {
      expect(within(modal).getByTestId("content-backlog-item-item-b")).toBeInTheDocument();
    });

    await user.click(within(modal).getByTestId("content-backlog-item-item-b"));
    const depCheckbox = within(modal).getByTestId("content-backlog-dep-item-a");
    await user.click(depCheckbox);
    await user.click(within(modal).getByTestId("content-backlog-save"));

    await waitFor(() => {
      expect(within(modal).getByTestId("content-backlog-outcome")).toHaveTextContent(
        /updated/i,
      );
    });
    expect(within(modal).getByTestId("content-backlog-item-item-b")).toHaveTextContent(
      /Depends on: Foundation/i,
    );
  });

  it("reprioritizes via move earlier and priority change", async () => {
    const user = userEvent.setup();
    const client = createAppClient({
      initialItems: [
        sampleItem({ item_id: "item-a", topic: "Alpha", priority: "low", queue_rank: 0 }),
        sampleItem({
          item_id: "item-b",
          topic: "Beta",
          priority: "medium",
          queue_rank: 1,
        }),
      ],
    });
    render(<App client={client} />);

    await user.click(screen.getByTestId("header-content-backlog-btn"));
    const modal = await screen.findByTestId("content-backlog-modal");
    await waitFor(() => {
      expect(within(modal).getByTestId("content-backlog-item-item-a")).toBeInTheDocument();
    });

    await user.click(within(modal).getByTestId("content-backlog-move-earlier-item-b"));
    await waitFor(() => {
      expect(within(modal).getByTestId("content-backlog-outcome")).toHaveTextContent(
        /earlier/i,
      );
    });
    const list = within(modal).getByTestId("content-backlog-list");
    const topics = within(list)
      .getAllByRole("button")
      .filter((btn) => btn.className.includes("content-backlog-list-item"))
      .map((btn) => btn.querySelector("strong")?.textContent);
    expect(topics[0]).toBe("Beta");
    expect(topics[1]).toBe("Alpha");

    await user.click(within(modal).getByTestId("content-backlog-item-item-a"));
    await user.selectOptions(
      within(modal).getByTestId("content-backlog-priority"),
      "high",
    );
    await user.click(within(modal).getByTestId("content-backlog-save"));
    await waitFor(() => {
      expect(within(modal).getByTestId("content-backlog-outcome")).toHaveTextContent(
        /updated/i,
      );
    });
  });

  it("shows plain-language cycle dependency failures", async () => {
    const user = userEvent.setup();
    const client = createAppClient({
      initialItems: [
        sampleItem({ item_id: "item-a", topic: "A", queue_rank: 0 }),
        sampleItem({
          item_id: "item-b",
          topic: "B",
          queue_rank: 1,
          depends_on_item_ids: ["item-a"],
        }),
      ],
      backlogUpdate: () =>
        new Response(
          JSON.stringify({
            detail: {
              errors: [
                {
                  field: "depends_on_item_ids",
                  code: "dependency_cycle",
                  message:
                    "dependencies would create a cycle among backlog items; remove the cycle and retry",
                },
              ],
            },
          }),
          { status: 422, headers: { "Content-Type": "application/json" } },
        ),
    });
    render(<App client={client} />);

    await user.click(screen.getByTestId("header-content-backlog-btn"));
    const modal = await screen.findByTestId("content-backlog-modal");
    await user.click(within(modal).getByTestId("content-backlog-item-item-a"));
    await user.click(within(modal).getByTestId("content-backlog-dep-item-b"));
    await user.click(within(modal).getByTestId("content-backlog-save"));

    await waitFor(() => {
      expect(within(modal).getByTestId("content-backlog-error")).toHaveTextContent(
        /cycle/i,
      );
    });
    expect(within(modal).queryByTestId("content-backlog-outcome")).not.toBeInTheDocument();
  });
});
