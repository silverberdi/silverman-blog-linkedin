import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { MemoryBearerAuthProvider, ReadOnlyBearerAuthProvider } from "../api/auth";
import { SupervisionApiClient } from "../api/client";

const DRAFT_SUMMARY = {
  draft_id: "draft-alpha",
  slug: "draft-alpha",
  title: "Authority framing for remote architects",
  topic_id: "topic-1",
  thesis: "Operators need clear authority framing",
  referent_positioning: "Senior architect referent",
  rationale: "Positions for leadership conversations",
  status: "pending_approval",
  blog_relative_path: "blog-posts/pending-approval/draft-alpha.md",
  image_relative_path: "blog-posts/pending-approval/draft-alpha.png",
  metadata_relative_path: "blog-posts/pending-approval/draft-alpha.flow-b.json",
  image_url: "/flow-b/pending-approval-drafts/draft-alpha/image",
  generated_at_utc: "2026-07-19T12:00:00Z",
  target_week: "2026-W30",
  empty_days: ["2026-07-20", "2026-07-22"],
};

const DRAFT_DETAIL = {
  ...DRAFT_SUMMARY,
  body_markdown: "# Authority framing for remote architects\n\nBody copy.",
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

function createAppClient(options?: {
  readonly?: boolean;
  onApprove?: (body: unknown) => Response;
  onReject?: (body: unknown) => Response;
  listDrafts?: () => Response;
}) {
  const auth = options?.readonly
    ? new ReadOnlyBearerAuthProvider()
    : new MemoryBearerAuthProvider();
  auth.setTokenForTests("test-key");

  let drafts = [DRAFT_SUMMARY];
  let detail = { ...DRAFT_DETAIL };

  const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method || "GET").toUpperCase();

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
      return new Response(JSON.stringify({ detail: "not needed" }), { status: 404 });
    }
    if (
      url.includes("/flow-b/pending-approval-drafts/draft-alpha/image") &&
      method === "GET"
    ) {
      return new Response(new Uint8Array([137, 80, 78, 71]), {
        status: 200,
        headers: { "Content-Type": "image/png" },
      });
    }
    if (
      url.includes("/flow-b/pending-approval-drafts/draft-alpha/approve") &&
      method === "POST"
    ) {
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      if (options?.onApprove) {
        return options.onApprove(body);
      }
      if (!body.dry_run) {
        detail = {
          ...detail,
          status: "approved",
          approved_at_utc: "2026-07-19T21:00:00Z",
        };
        drafts = drafts.map((d) =>
          d.draft_id === "draft-alpha" ? { ...d, status: "approved" } : d,
        );
      }
      return new Response(
        JSON.stringify({
          status: "approved",
          draft_id: "draft-alpha",
          promoted: false,
          promotion_pending: true,
          dry_run: Boolean(body.dry_run),
          operator_note:
            "Approved decision recorded. Promotion to blog-posts/ready/ remains US-081.",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    if (
      url.includes("/flow-b/pending-approval-drafts/draft-alpha/reject") &&
      method === "POST"
    ) {
      const body = init?.body ? JSON.parse(String(init.body)) : {};
      if (options?.onReject) {
        return options.onReject(body);
      }
      if (!body.dry_run) {
        drafts = [];
        detail = {
          ...detail,
          status: "rejected",
          rejection_reason: body.rejection_reason || null,
        };
      }
      return new Response(
        JSON.stringify({
          status: "rejected",
          draft_id: "draft-alpha",
          promoted: false,
          promotion_pending: false,
          dry_run: Boolean(body.dry_run),
          rejection_reason: body.rejection_reason || null,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    if (
      url.match(/\/flow-b\/pending-approval-drafts\/draft-alpha(\?|$)/) ||
      url.endsWith("/flow-b/pending-approval-drafts/draft-alpha")
    ) {
      return new Response(JSON.stringify(detail), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    }
    if (url.includes("/flow-b/pending-approval-drafts")) {
      if (options?.listDrafts) {
        return options.listDrafts();
      }
      return new Response(
        JSON.stringify({
          status: "ok",
          drafts,
          observed_at_utc: "2026-07-19T20:00:00Z",
          filter_status: null,
          count: drafts.length,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    }
    return new Response(JSON.stringify({ detail: "not found" }), { status: 404 });
  });

  return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
}

describe("US-080 Flow B pending drafts modal", () => {
  it("presents pending draft with discovery and gap fields", async () => {
    const user = userEvent.setup();
    const client = createAppClient();
    render(<App client={client} />);

    await waitFor(() => {
      expect(screen.getByTestId("header-flow-b-drafts-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("header-flow-b-drafts-btn"));

    const modal = await screen.findByTestId("flow-b-drafts-modal");
    expect(within(modal).getByTestId("flow-b-drafts-scope-note")).toHaveTextContent(
      /does not promote to ready/i,
    );
    expect(within(modal).getByTestId("flow-b-drafts-scope-note")).toHaveTextContent(
      /no revision-history CMS/i,
    );

    await waitFor(() => {
      expect(within(modal).getByTestId("flow-b-drafts-title")).toHaveTextContent(
        /Authority framing/i,
      );
    });
    expect(within(modal).getByTestId("flow-b-drafts-discovery")).toHaveTextContent(
      /Senior architect referent/i,
    );
    expect(within(modal).getByTestId("flow-b-drafts-gap-week")).toHaveTextContent(
      "2026-W30",
    );
    expect(within(modal).getByTestId("flow-b-drafts-empty-days")).toHaveTextContent(
      "2026-07-20",
    );
    expect(within(modal).getByTestId("flow-b-drafts-body")).toHaveTextContent(/Body copy/);
    expect(within(modal).getByTestId("flow-b-drafts-approve")).toBeInTheDocument();
    expect(within(modal).getByTestId("flow-b-drafts-reject")).toBeInTheDocument();
  });

  it("approve communicates promotion still pending and honors dry-run default", async () => {
    const user = userEvent.setup();
    let captured: unknown = null;
    const client = createAppClient({
      onApprove: (body) => {
        captured = body;
        return new Response(
          JSON.stringify({
            status: "approved",
            draft_id: "draft-alpha",
            promoted: false,
            promotion_pending: true,
            dry_run: true,
            operator_note: "Promotion remains US-081",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      },
    });
    render(<App client={client} />);

    await user.click(await screen.findByTestId("header-flow-b-drafts-btn"));
    const modal = await screen.findByTestId("flow-b-drafts-modal");
    await waitFor(() => {
      expect(within(modal).getByTestId("flow-b-drafts-approve")).toBeEnabled();
    });
    await user.click(within(modal).getByTestId("flow-b-drafts-approve"));

    await waitFor(() => {
      expect(within(modal).getByTestId("flow-b-drafts-outcome")).toHaveTextContent(
        /Promotion to ready\/ is still pending/i,
      );
    });
    expect(captured).toEqual({ dry_run: true });
  });

  it("reject communicates blocked state", async () => {
    const user = userEvent.setup();
    // Switch shell to Commit so reject persists in mock
    const client = createAppClient();
    render(<App client={client} />);

    await user.click(await screen.findByTestId("shell-dry-run-default"));
    await user.click(await screen.findByTestId("header-flow-b-drafts-btn"));
    const modal = await screen.findByTestId("flow-b-drafts-modal");
    await waitFor(() => {
      expect(within(modal).getByTestId("flow-b-drafts-reject")).toBeEnabled();
    });
    await user.type(
      within(modal).getByTestId("flow-b-drafts-reject-reason"),
      "Off voice",
    );
    await user.click(within(modal).getByTestId("flow-b-drafts-reject"));

    await waitFor(() => {
      expect(within(modal).getByTestId("flow-b-drafts-outcome")).toHaveTextContent(
        /Rejected \/ blocked/i,
      );
    });
  });

  it("shows failure states clearly", async () => {
    const user = userEvent.setup();
    const client = createAppClient({
      listDrafts: () =>
        new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 }),
    });
    render(<App client={client} />);
    await user.click(await screen.findByTestId("header-flow-b-drafts-btn"));
    const modal = await screen.findByTestId("flow-b-drafts-modal");
    await waitFor(() => {
      expect(within(modal).getByTestId("flow-b-drafts-error")).toBeInTheDocument();
    });
  });

  it("disables approve/reject for read-only sessions", async () => {
    const user = userEvent.setup();
    const client = createAppClient({ readonly: true });
    render(<App client={client} />);
    await user.click(await screen.findByTestId("header-flow-b-drafts-btn"));
    const modal = await screen.findByTestId("flow-b-drafts-modal");
    await waitFor(() => {
      expect(within(modal).getByTestId("flow-b-drafts-approve")).toBeDisabled();
    });
    expect(within(modal).getByTestId("flow-b-drafts-reject")).toBeDisabled();
  });
});
