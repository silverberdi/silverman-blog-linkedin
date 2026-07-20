/**
 * US-086 — Publish a LinkedIn variant immediately from the console.
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
import {
  buildLinkedInActionMatrix,
  isDeferredFutureNotDue,
  publishNowEligibility,
} from "../models/actionAvailability";
import { explainErrorCodes } from "../api/errors";
import {
  publishDryRunModeBanner,
  publishOutcomeToast,
} from "../models/mutationMode";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityItemDto,
  ScheduleVisibilityResponse,
} from "../api/types";
import type { ScheduleItem } from "../models/supervision";

const ITEM_ID = "linkedin:camp-1:v1";
const SCHEDULED_UTC = "2026-07-20T15:00:00Z";
const LIVE_URN = "urn:li:share:us086-test-urn";

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
    title: "Publish target",
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

describe("US-086 action matrix and refusal copy", () => {
  it("publish now available for Waiting to send and Scheduled when eligible + canMutate", () => {
    const queued = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-queued",
        publicationState: "queued",
        sourceState: "queued",
        actions: [],
      }),
      hasSupervisionJoin: false,
      canMutate: true,
    });
    expect(queued.find((r) => r.id === "publish_now")?.available).toBe(true);
    expect(queued.find((r) => r.id === "cancel_queued")?.available).toBe(true);
    expect(queued.find((r) => r.id === "reschedule")?.available).toBe(true);

    const pending = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-pending",
        publicationState: "pending",
        actions: ["edit", "defer", "cancel"],
      }),
      hasSupervisionJoin: true,
      canMutate: true,
    });
    expect(pending.find((r) => r.id === "publish_now")?.available).toBe(true);
    expect(pending.find((r) => r.id === "cancel_pending")?.available).toBe(true);
    expect(pending.find((r) => r.id === "reschedule")?.available).toBe(true);
  });

  it("Live on LinkedIn omits publish-now row", () => {
    const rows = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-live",
        publicationState: "published",
        linkedinApiPublished: true,
        linkedinPostUrn: LIVE_URN,
        scheduleEditable: false,
      }),
      hasSupervisionJoin: false,
      canMutate: true,
    });
    expect(rows.find((r) => r.id === "publish_now")).toBeUndefined();
  });

  it("deferred future schedule blocks publish now with plain reason", () => {
    const item = scheduleItem({
      itemId: "li-deferred",
      publicationState: "deferred",
      sourceState: "pending",
      scheduledAtUtc: "2026-07-25T15:00:00Z",
    });
    const nowMs = Date.parse("2026-07-19T12:00:00Z");
    expect(isDeferredFutureNotDue(item, nowMs)).toBe(true);
    const eligibility = publishNowEligibility(item, { canMutate: true, nowMs });
    expect(eligibility.eligible).toBe(false);
    if (!eligibility.eligible) {
      expect(eligibility.reason).toMatch(/deferred time/i);
    }
  });

  it("enablement / cadence / sequence codes are plain language", () => {
    expect(explainErrorCodes(["linkedin_publish_not_enabled"])).toMatch(
      /not enabled/i,
    );
    expect(explainErrorCodes(["linkedin_publish_blocked_cadence"])).toMatch(
      /cadence/i,
    );
    expect(explainErrorCodes(["linkedin_publish_blocked_sequence"])).toMatch(
      /sequence/i,
    );
  });

  it("preview publish toast cannot be mistaken for Live on LinkedIn", () => {
    const preview = publishOutcomeToast({
      dryRun: true,
      identity: "camp-1 / v1",
      urn: null,
    });
    expect(preview).toMatch(/Preview only/i);
    expect(preview).toMatch(/Not Live on LinkedIn/i);
    expect(preview).not.toMatch(/^Live on LinkedIn/);

    const real = publishOutcomeToast({
      dryRun: false,
      identity: "camp-1 / v1",
      urn: LIVE_URN,
    });
    expect(real).toMatch(/^Live on LinkedIn/);
    expect(real).toContain(LIVE_URN);
  });

  it("real publish mode banner states LinkedIn API send", () => {
    expect(publishDryRunModeBanner(true)).toMatch(/Preview/i);
    expect(publishDryRunModeBanner(false)).toMatch(/LinkedIn API/i);
  });
});

describe("US-086 EventModal publish now for Waiting to send and Scheduled", () => {
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
    linkedinPublicationEnabled?: boolean;
    realPublishOutcome?: "success" | "not_enabled" | "cadence";
  }) {
    let publicationState: string = opts.publicationState;
    let linkedinApiPublished = false;
    let linkedinPostUrn: string | null = null;
    const enablement = opts.linkedinPublicationEnabled !== false;
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-token");

    const pending: PendingSupervisionResponse = {
      status: "ok",
      observed_at_utc: "2026-07-18T12:00:00Z",
      read_only: false,
      linkedin_publication_enabled: enablement,
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
                calendar_title: "Publish target",
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
          linkedin_publication_enabled: enablement,
          calendar_fingerprint: "b".repeat(64),
          items: [
            baseScheduleItem({
              publication_state: publicationState as
                | "pending"
                | "queued"
                | "published",
              source_state: publicationState,
              linkedin_api_published: linkedinApiPublished,
              linkedin_post_urn: linkedinPostUrn,
              schedule_editable: publicationState !== "published",
              schedule_edit_block_reason:
                publicationState === "published"
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
      if (url.includes("publish-linkedin-due-variants")) {
        const body = JSON.parse(String(init?.body));
        expect(body.campaign_id).toBe("camp-1");
        expect(body.variant).toBe("v1");
        expect(body.publish_now).toBe(true);
        if (opts.publicationState === "pending") {
          expect(body.auto_queue_pending).toBe(true);
        } else {
          expect(body.auto_queue_pending).toBeFalsy();
        }
        if (body.dry_run) {
          return new Response(
            JSON.stringify({
              status: "completed",
              dry_run: true,
              publish_now: true,
              results: [
                {
                  campaign_id: "camp-1",
                  variant: "v1",
                  publish_state: opts.publicationState === "queued" ? "queued" : "queued",
                  status: "completed",
                  warnings: ["linkedin_publish_dry_run"],
                  linkedin_post_urn: null,
                },
              ],
              errors: [],
              warnings: [],
              ...(body.auto_queue_pending
                ? {
                    auto_queue_pending: true,
                    auto_queue_results: [
                      {
                        campaign_id: "camp-1",
                        variant: "v1",
                        publish_state: "queued",
                        status: "completed",
                        skipped: false,
                      },
                    ],
                  }
                : {}),
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        const outcome = opts.realPublishOutcome ?? "success";
        if (outcome === "not_enabled") {
          return new Response(
            JSON.stringify({
              status: "failed",
              dry_run: false,
              publish_now: true,
              results: [
                {
                  campaign_id: "camp-1",
                  variant: "v1",
                  publish_state: "queued",
                  status: "failed",
                  errors: ["linkedin_publish_not_enabled"],
                },
              ],
              errors: ["linkedin_publish_not_enabled"],
              warnings: [],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        if (outcome === "cadence") {
          return new Response(
            JSON.stringify({
              status: "completed",
              dry_run: false,
              publish_now: true,
              results: [
                {
                  campaign_id: "camp-1",
                  variant: "v1",
                  publish_state: "queued",
                  status: "completed",
                  skipped: true,
                  skip_reason: "linkedin_publish_blocked_cadence",
                },
              ],
              errors: [],
              warnings: [],
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          );
        }
        publicationState = "published";
        linkedinApiPublished = true;
        linkedinPostUrn = LIVE_URN;
        pending.variants = [];
        return new Response(
          JSON.stringify({
            status: "completed",
            dry_run: false,
            publish_now: true,
            results: [
              {
                campaign_id: "camp-1",
                variant: "v1",
                publish_state: "published",
                status: "completed",
                linkedin_post_urn: LIVE_URN,
                published_at: "2026-07-19T12:05:00Z",
              },
            ],
            errors: [],
            warnings: [],
            ...(body.auto_queue_pending
              ? {
                  auto_queue_pending: true,
                  auto_queue_results: [
                    {
                      campaign_id: "camp-1",
                      variant: "v1",
                      publish_state: "published",
                      status: "completed",
                      linkedin_post_urn: LIVE_URN,
                    },
                  ],
                }
              : {}),
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }
      return new Response("{}", { status: 404 });
    });

    return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
  }

  async function openPublishPanel(
    user: ReturnType<typeof userEvent.setup>,
    publicationState: "pending" | "queued",
    clientOpts: Parameters<typeof makeClient>[0] = { publicationState },
  ) {
    const client = makeClient({ ...clientOpts, publicationState });
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
    expect(screen.getByTestId("row-publish")).toBeInTheDocument();
    expect(screen.getByTestId("row-cancel")).toBeInTheDocument();
    expect(screen.getByTestId("row-defer")).toBeInTheDocument();
    await user.click(screen.getByTestId("row-publish"));
    expect(screen.getByTestId("publish-panel")).toBeInTheDocument();
    expect(screen.getByTestId("publish-control-framing").textContent).toMatch(
      /LinkedIn API/i,
    );
    expect(screen.getByTestId("publish-mode-banner").textContent).toMatch(
      /Preview/i,
    );
    return client;
  }

  it("deliberate publish for Waiting to send (queued) with preview ≠ Live", async () => {
    const user = userEvent.setup();
    await openPublishPanel(user, "queued");
    expect(screen.getByTestId("publish-panel")).toHaveTextContent(
      /waiting-to-send/i,
    );
    await user.click(screen.getByTestId("publish-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("toast-host").textContent).toMatch(
        /Preview only/i,
      );
    });
    expect(screen.getByTestId("toast-host").textContent).toMatch(
      /Not Live on LinkedIn/i,
    );
    expect(screen.getByTestId("publish-panel")).toBeInTheDocument();
  });

  it("deliberate publish for Scheduled uses auto_queue_pending + publish_now", async () => {
    const user = userEvent.setup();
    await openPublishPanel(user, "pending");
    expect(screen.getByTestId("publish-control-framing").textContent).toMatch(
      /auto_queue|Queues then sends/i,
    );
  });

  it("real publish shows Live on LinkedIn + URN and withdraws publish-now", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    await openPublishPanel(user, "queued", {
      publicationState: "queued",
      realPublishOutcome: "success",
    });
    await user.click(screen.getByTestId("publish-dry-run"));
    expect(screen.getByTestId("publish-mode-banner").textContent).toMatch(
      /Real publish/i,
    );
    await user.click(screen.getByTestId("publish-submit"));
    expect(confirmSpy).toHaveBeenCalled();
    await waitFor(() => {
      expect(screen.getByTestId("toast-host").textContent).toMatch(
        /Live on LinkedIn/i,
      );
    });
    expect(screen.getByTestId("toast-host").textContent).toContain(LIVE_URN);
    await waitFor(() => {
      expect(screen.getByTestId("event-modal-status")).toHaveTextContent(
        /Live on LinkedIn/i,
      );
    });
    expect(screen.getByTestId("event-modal-linkedin-urn").textContent).toContain(
      LIVE_URN,
    );
    expect(screen.queryByTestId("row-publish")).not.toBeInTheDocument();
    expect(screen.queryByTestId("action-matrix-publish_now")).not.toBeInTheDocument();
  });

  it("real publish fails closed when not enabled with plain language", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    await openPublishPanel(user, "queued", {
      publicationState: "queued",
      linkedinPublicationEnabled: false,
      realPublishOutcome: "not_enabled",
    });
    expect(screen.getByTestId("publish-enablement-warn")).toBeInTheDocument();
    await user.click(screen.getByTestId("publish-dry-run"));
    await user.click(screen.getByTestId("publish-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("event-modal-error").textContent).toMatch(
        /not enabled/i,
      );
    });
    expect(screen.getByTestId("event-modal-error").textContent).not.toMatch(
      /^Live on LinkedIn/,
    );
  });

  it("cadence block is plain language and does not claim Live", async () => {
    const user = userEvent.setup();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    await openPublishPanel(user, "queued", {
      publicationState: "queued",
      realPublishOutcome: "cadence",
    });
    await user.click(screen.getByTestId("publish-dry-run"));
    await user.click(screen.getByTestId("publish-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("event-modal-error").textContent).toMatch(
        /cadence/i,
      );
    });
    expect(screen.getByTestId("event-modal-error").textContent).toMatch(
      /not Live on LinkedIn/i,
    );
    expect(screen.getByTestId("publish-panel")).toBeInTheDocument();
  });
});
