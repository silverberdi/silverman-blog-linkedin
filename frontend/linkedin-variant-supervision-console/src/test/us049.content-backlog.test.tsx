import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { MemoryBearerAuthProvider, ReadOnlyBearerAuthProvider } from "../api/auth";
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
    linkedin_derivatives: [
      {
        audience_hint: "hiring managers",
        format_hint: "short post",
        notes: "Link to blog after review",
      },
    ],
    created_at_utc: "2026-07-20T12:00:00Z",
    updated_at_utc: "2026-07-20T12:00:00Z",
    row_version: 1,
    ...overrides,
  };
}

function createAppClient(options?: {
  readonly?: boolean;
  backlogList?: () => Response;
  backlogCreate?: (body: unknown) => Response;
  backlogUpdate?: (body: unknown) => Response;
}) {
  const auth = options?.readonly
    ? new ReadOnlyBearerAuthProvider()
    : new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-key");

  let items: EditorialContentBacklogItem[] = [];

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
    if (url.match(/\/editorial\/content-backlog\/[^/?]+/) && !url.endsWith("/content-backlog")) {
      const method = (init?.method || "GET").toUpperCase();
      if (method === "PUT") {
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        if (options?.backlogUpdate) {
          return options.backlogUpdate(body);
        }
        const updated = {
          ...sampleItem(),
          ...body,
          item_id: "item-1",
          row_version: 2,
          updated_at_utc: "2026-07-21T12:00:00Z",
        };
        items = [updated];
        return new Response(JSON.stringify(updated), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
    }
    if (url.includes("/editorial/content-backlog")) {
      const method = (init?.method || "GET").toUpperCase();
      if (method === "GET") {
        if (options?.backlogList) {
          return options.backlogList();
        }
        return new Response(
          JSON.stringify({ status: "ok", items, count: items.length }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      if (method === "POST") {
        const body = init?.body ? JSON.parse(String(init.body)) : {};
        if (options?.backlogCreate) {
          return options.backlogCreate(body);
        }
        const created = sampleItem({
          ...body,
          item_id: "item-created",
          row_version: 1,
        });
        items = [created, ...items];
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

describe("US-049 Content backlog modal", () => {
  it("shows empty state and creates an item", async () => {
    const user = userEvent.setup();
    const client = createAppClient();
    render(<App client={client} />);

    await user.click(screen.getByTestId("header-content-backlog-btn"));
    const modal = await screen.findByTestId("content-backlog-modal");
    expect(
      within(modal).getByTestId("content-backlog-optional-note"),
    ).toHaveTextContent(/does not publish to LinkedIn/i);
    expect(
      within(modal).getByTestId("content-backlog-optional-note"),
    ).toHaveTextContent(/does not start Flow B/i);

    await waitFor(() => {
      expect(within(modal).getByTestId("content-backlog-empty")).toBeInTheDocument();
    });

    await user.click(within(modal).getByTestId("content-backlog-new-btn"));
    await user.type(within(modal).getByTestId("content-backlog-topic"), "Topic A");
    await user.type(
      within(modal).getByTestId("content-backlog-audience"),
      "Audience A",
    );
    await user.type(
      within(modal).getByTestId("content-backlog-objective"),
      "Objective A",
    );
    await user.click(within(modal).getByTestId("content-backlog-save"));

    await waitFor(() => {
      expect(
        within(modal).getByTestId("content-backlog-outcome"),
      ).toHaveTextContent(/created/i);
    });
    expect(within(modal).getByText("Topic A")).toBeInTheDocument();
  });

  it("edits an existing item", async () => {
    const user = userEvent.setup();
    const client = createAppClient({
      backlogList: () =>
        new Response(
          JSON.stringify({
            status: "ok",
            items: [sampleItem()],
            count: 1,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
    });
    render(<App client={client} />);

    await user.click(screen.getByTestId("header-content-backlog-btn"));
    const modal = await screen.findByTestId("content-backlog-modal");
    await waitFor(() => {
      expect(
        within(modal).getByTestId("content-backlog-item-item-1"),
      ).toBeInTheDocument();
    });

    await user.click(within(modal).getByTestId("content-backlog-item-item-1"));
    const topic = within(modal).getByTestId("content-backlog-topic");
    await user.clear(topic);
    await user.type(topic, "Updated topic");
    await user.click(within(modal).getByTestId("content-backlog-save"));

    await waitFor(() => {
      expect(
        within(modal).getByTestId("content-backlog-outcome"),
      ).toHaveTextContent(/updated/i);
    });
  });

  it("shows validation errors in plain language", async () => {
    const user = userEvent.setup();
    const client = createAppClient({
      backlogCreate: () =>
        new Response(
          JSON.stringify({
            detail: {
              errors: [
                {
                  field: "topic",
                  code: "topic_required",
                  message: "topic must be a non-empty string",
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
    await user.click(within(modal).getByTestId("content-backlog-new-btn"));
    await user.type(within(modal).getByTestId("content-backlog-topic"), "x");
    await user.type(within(modal).getByTestId("content-backlog-audience"), "y");
    await user.type(within(modal).getByTestId("content-backlog-objective"), "z");
    await user.click(within(modal).getByTestId("content-backlog-save"));

    await waitFor(() => {
      expect(within(modal).getByTestId("content-backlog-error")).toHaveTextContent(
        /topic must be a non-empty string/i,
      );
    });
  });

  it("gates mutations for read-only sessions", async () => {
    const user = userEvent.setup();
    const client = createAppClient({ readonly: true });
    render(<App client={client} />);

    await user.click(screen.getByTestId("header-content-backlog-btn"));
    const modal = await screen.findByTestId("content-backlog-modal");
    await waitFor(() => {
      expect(within(modal).getByTestId("content-backlog-new-btn")).toBeDisabled();
    });
  });
});
