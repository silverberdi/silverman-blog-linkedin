/**
 * US-085 — Cancel LinkedIn variants that are not yet Live (pending + queued).
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import { SupervisionStoreProvider } from "../models/store";
import { MonthCalendarView } from "../components/MonthCalendarView";
import { EventModal } from "../components/EventModal";
import { AppShell } from "../components/AppShell";
import { buildLinkedInActionMatrix } from "../models/actionAvailability";
import { explainErrorCodes } from "../api/errors";
import { mutationOutcomeToast } from "../models/mutationMode";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityItemDto,
  ScheduleVisibilityResponse,
} from "../api/types";
import type { ScheduleItem } from "../models/supervision";

const ITEM_ID = "linkedin:camp-1:v1";
const SCHEDULED_UTC = "2026-07-20T15:00:00Z";

function scheduleItem(
  partial: Partial<ScheduleItem> & Pick<ScheduleItem, "itemId">,
): ScheduleItem {
  return {
    channel: "linkedin",
    campaignId: "camp-1",
    variantId: "v1",
    title: "Post",
    audience: "eng",
    scheduledAtUtc: SCHEDULED_UTC,
    publicationState: "pending",
    sourceState: "pending",
    blocked: false,
    critical: false,
    linkedinApiPublished: false,
    linkedinPostUrn: null,
    calendarItemId: null,
    scheduleEditable: true,
    scheduleEditBlockReason: null,
    cancelledAtUtc: null,
    cancellationPhase: null,
    cancellationReason: null,
    reopenEligible: false,
    cadenceConflict: false,
    cadenceConflictCode: null,
    cadenceEarliestFeasibleAtUtc: null,
    actions: ["edit", "defer", "cancel"],
    statusColor: "#888",
    ...partial,
  };
}

function baseScheduleItem(
  overrides: Partial<ScheduleVisibilityItemDto> = {},
): ScheduleVisibilityItemDto {
  return {
    item_id: ITEM_ID,
    channel: "linkedin",
    campaign_id: "camp-1",
    variant_id: "v1",
    title: "Cancel target",
    audience: "eng",
    scheduled_at_utc: SCHEDULED_UTC,
    publication_state: "pending",
    source_state: "pending",
    blocked: false,
    critical: false,
    linkedin_api_published: false,
    schedule_editable: true,
    schedule_edit_block_reason: null,
    ...overrides,
  };
}

describe("US-085 action matrix and refusal copy", () => {
  it("cancel-pending and cancel-queued available when eligible + canMutate", () => {
    const pending = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-pending",
        publicationState: "pending",
        scheduleEditable: true,
        actions: ["edit", "defer", "cancel"],
      }),
      hasSupervisionJoin: true,
      canMutate: true,
    });
    expect(pending.find((r) => r.id === "cancel_pending")?.available).toBe(true);
    expect(pending.find((r) => r.id === "publish_now")?.available).toBe(true);
    expect(pending.find((r) => r.id === "reschedule")?.available).toBe(true);

    const queued = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-queued",
        publicationState: "queued",
        scheduleEditable: true,
        actions: [],
      }),
      hasSupervisionJoin: false,
      canMutate: true,
    });
    expect(queued.find((r) => r.id === "cancel_queued")?.available).toBe(true);
    expect(queued.find((r) => r.id === "reschedule")?.available).toBe(true);
    expect(queued.find((r) => r.id === "publish_now")?.available).toBe(true);
  });

  it("session cannot mutate blocks cancel clearly", () => {
    const rows = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-queued",
        publicationState: "queued",
        actions: [],
      }),
      hasSupervisionJoin: false,
      canMutate: false,
    });
    expect(rows.find((r) => r.id === "cancel_queued")?.available).toBe(false);
    expect(rows.find((r) => r.id === "cancel_queued")?.reason).toMatch(
      /cannot mutate/i,
    );
  });

  it("live on LinkedIn has no cancel rows", () => {
    const rows = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-live",
        publicationState: "published",
        linkedinApiPublished: true,
        scheduleEditable: false,
        scheduleEditBlockReason: "linkedin_supervision_variant_not_pending",
      }),
      hasSupervisionJoin: false,
      canMutate: true,
    });
    expect(rows.find((r) => r.id === "cancel_pending")).toBeUndefined();
    expect(rows.find((r) => r.id === "cancel_queued")).toBeUndefined();
  });

  it("after cancelled, reopen remains and cancel-pending/queued withdrawn", () => {
    const rows = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-cancelled",
        publicationState: "cancelled",
        scheduleEditable: false,
        reopenEligible: true,
        cancellationPhase: "post_queue",
        actions: [],
      }),
      hasSupervisionJoin: false,
      canMutate: true,
    });
    expect(rows.find((r) => r.id === "cancel_pending")).toBeUndefined();
    expect(rows.find((r) => r.id === "cancel_queued")).toBeUndefined();
    expect(rows.find((r) => r.id === "reopen")?.available).toBe(true);
    expect(rows.find((r) => r.id === "publish_now")?.available).toBe(false);
  });

  it("cancel-not-allowed maps to plain language + next step", () => {
    expect(explainErrorCodes(["linkedin_publish_cancel_not_allowed"])).toMatch(
      /Live on LinkedIn/i,
    );
    expect(explainErrorCodes(["linkedin_publish_cancel_not_allowed"])).toMatch(
      /cannot be cancelled|Reload/i,
    );
  });

  it("preview cancel toast cannot be mistaken for completed cancel", () => {
    const preview = mutationOutcomeToast("Cancel", true, "camp-1 / v1");
    expect(preview).toMatch(/Preview only/i);
    expect(preview).toMatch(/Not Cancelled for real/i);
    expect(preview).not.toMatch(/^Saved:/);

    const real = mutationOutcomeToast("Cancel", false, "camp-1 / v1");
    expect(real).toMatch(/^Saved:/);
    expect(real).toMatch(/will not send/i);
    expect(real).toMatch(/reopen/i);
  });
});

describe("US-085 EventModal cancel for Scheduled and Waiting to send", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date("2026-07-19T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  function makeClient(opts: {
    publicationState: "pending" | "queued";
    mutateToCancelledOnReal?: boolean;
  }) {
    let publicationState: string = opts.publicationState;
    let cancelledAt: string | null = null;
    let cancellationPhase: string | null = null;
    let reopenEligible = false;
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-token");

    const pending: PendingSupervisionResponse = {
      status: "ok",
      observed_at_utc: "2026-07-18T12:00:00Z",
      read_only: false,
      linkedin_publication_enabled: false,
      variants:
        opts.publicationState === "pending" && publicationState === "pending"
          ? [
              {
                campaign_id: "camp-1",
                variant_id: "v1",
                audience: "eng",
                scheduled_at_utc: SCHEDULED_UTC,
                publish_state: "pending",
                calendar_item_id: null,
                calendar_title: "Cancel target",
                calendar_due_at_utc: null,
                calendar_status: null,
                operator_supervision_last_action: null,
                auto_queue_eligible: true,
                operator_supervision_reason: null,
                draft_content: "Draft",
              },
            ]
          : [],
      issues: [],
      integration_failures: [],
    };

    const fetchImpl = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.includes("pending-supervision")) {
        if (publicationState !== "pending") {
          pending.variants = [];
        }
        return new Response(JSON.stringify(pending), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("schedule-visibility")) {
        const schedule: ScheduleVisibilityResponse = {
          status: "ok",
          observed_at_utc: "2026-07-18T12:00:00Z",
          read_only: false,
          year: 2026,
          month: 7,
          from_utc: "2026-07-01T00:00:00Z",
          to_utc: "2026-07-31T23:59:59Z",
          linkedin_publication_enabled: false,
          calendar_fingerprint: "b".repeat(64),
          items: [
            baseScheduleItem({
              publication_state: publicationState as "pending" | "queued" | "cancelled",
              source_state: publicationState,
              cancelled_at_utc: cancelledAt,
              cancellation_phase: cancellationPhase,
              cancellation_reason: cancelledAt ? "operator_choice" : null,
              reopen_eligible: reopenEligible,
              schedule_editable: publicationState !== "cancelled",
              schedule_edit_block_reason:
                publicationState === "cancelled"
                  ? "linkedin_supervision_variant_not_pending"
                  : null,
            }),
          ],
          issues: [],
        };
        return new Response(JSON.stringify(schedule), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (url.includes("cancel-linkedin-publication")) {
        const body = JSON.parse(String(init?.body));
        expect(body.campaign_id).toBe("camp-1");
        expect(body.variant).toBe("v1");
        if (!body.dry_run && opts.mutateToCancelledOnReal !== false) {
          publicationState = "cancelled";
          cancelledAt = "2026-07-19T12:05:00Z";
          cancellationPhase =
            opts.publicationState === "queued" ? "post_queue" : "pre_queue";
          reopenEligible = true;
          pending.variants = [];
        }
        return new Response(
          JSON.stringify({
            status: "completed",
            campaign_id: "camp-1",
            variant: "v1",
            state: "distribution_scheduled",
            publish_state: body.dry_run ? opts.publicationState : "cancelled",
            dry_run: Boolean(body.dry_run),
            phase:
              opts.publicationState === "queued" ? "post_queue" : "pre_queue",
            errors: [],
            warnings: [],
            metadata_written: !body.dry_run,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("{}", { status: 404 });
    });

    return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
  }

  async function openCancelPanel(
    user: ReturnType<typeof userEvent.setup>,
    publicationState: "pending" | "queued",
  ) {
    const client = makeClient({ publicationState });
    render(
      <SupervisionStoreProvider client={client}>
        <AppShell>
          <EventModal />
          <MonthCalendarView />
        </AppShell>
      </SupervisionStoreProvider>,
    );
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-day-2026-07-20")).toBeInTheDocument();
    });
    const day = screen.getByTestId("calendar-day-2026-07-20");
    await user.click(within(day).getByTestId("schedule-open-month"));
    expect(screen.getByTestId("row-cancel")).toBeInTheDocument();
    await user.click(screen.getByTestId("row-cancel"));
    expect(screen.getByTestId("cancel-panel")).toBeInTheDocument();
    expect(screen.getByTestId("cancel-control-framing").textContent).toMatch(
      /not postpone/i,
    );
    expect(screen.getByTestId("cancel-mode-banner").textContent).toMatch(
      /Preview/i,
    );
    return client;
  }

  it("deliberate cancel for Scheduled (pending) with confirmation path", async () => {
    const user = userEvent.setup();
    await openCancelPanel(user, "pending");
    expect(screen.getByTestId("cancel-panel")).toHaveTextContent(
      /Cancel scheduled variant/i,
    );
  });

  it("deliberate cancel for Waiting to send (queued) without supervision join", async () => {
    const user = userEvent.setup();
    const client = makeClient({ publicationState: "queued" });
    render(
      <SupervisionStoreProvider client={client}>
        <AppShell>
          <EventModal />
          <MonthCalendarView />
        </AppShell>
      </SupervisionStoreProvider>,
    );
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-day-2026-07-20")).toBeInTheDocument();
    });
    const day = screen.getByTestId("calendar-day-2026-07-20");
    await user.click(within(day).getByTestId("schedule-open-month"));
    expect(screen.getByTestId("action-matrix-cancel_queued")).toHaveAttribute(
      "data-available",
      "true",
    );
    expect(screen.getByTestId("row-cancel")).toBeInTheDocument();
    await user.click(screen.getByTestId("row-cancel"));
    expect(screen.getByTestId("cancel-panel")).toHaveTextContent(
      /Cancel waiting-to-send variant/i,
    );
    expect(screen.getByTestId("cancel-control-framing").textContent).toMatch(
      /Waiting-to-send/i,
    );
  });

  it("preview cancel does not claim Cancelled and does not require confirm", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    await openCancelPanel(user, "queued");
    await user.click(screen.getByTestId("cancel-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast")).toHaveTextContent(/Preview only/i);
    });
    expect(screen.getByTestId("toast")).toHaveTextContent(
      /Not Cancelled for real/i,
    );
    expect(confirmSpy).not.toHaveBeenCalled();
    expect(screen.getByTestId("cancel-panel")).toBeInTheDocument();
  });

  it("real cancel requires confirmation and shows Cancelled after refresh", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const client = makeClient({
      publicationState: "queued",
      mutateToCancelledOnReal: true,
    });
    render(
      <SupervisionStoreProvider client={client}>
        <AppShell>
          <EventModal />
          <MonthCalendarView />
        </AppShell>
      </SupervisionStoreProvider>,
    );
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("calendar-day-2026-07-20")).toBeInTheDocument();
    });
    const day = screen.getByTestId("calendar-day-2026-07-20");
    await user.click(within(day).getByTestId("schedule-open-month"));
    await user.click(screen.getByTestId("row-cancel"));
    await user.click(screen.getByTestId("cancel-dry-run"));
    expect(screen.getByTestId("cancel-mode-banner").textContent).toMatch(
      /Make real change/i,
    );
    await user.click(screen.getByTestId("cancel-submit"));
    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByTestId("toast")).toHaveTextContent(/Saved:/);
    });
    expect(screen.getByTestId("toast")).toHaveTextContent(/will not send/i);

    await user.click(
      within(screen.getByTestId("calendar-day-2026-07-20")).getByTestId(
        "schedule-open-month",
      ),
    );
    await waitFor(() => {
      expect(screen.getByTestId("event-modal-status")).toHaveTextContent(
        /Cancelled/i,
      );
    });
    expect(screen.getByTestId("row-reopen")).toBeInTheDocument();
    expect(screen.queryByTestId("row-cancel")).not.toBeInTheDocument();
    expect(screen.getByTestId("action-matrix-publish_now")).toHaveAttribute(
      "data-available",
      "false",
    );
  });

  it("real cancel aborted when confirmation refused", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(false);
    await openCancelPanel(user, "pending");
    await user.click(screen.getByTestId("cancel-dry-run"));
    await user.click(screen.getByTestId("cancel-submit"));
    expect(screen.getByTestId("cancel-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("toast")).toBeNull();
  });
});
