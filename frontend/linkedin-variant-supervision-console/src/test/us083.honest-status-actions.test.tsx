import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "../App";
import { SupervisionApiClient } from "../api/client";
import { MemoryBearerAuthProvider } from "../api/auth";
import type {
  PendingSupervisionResponse,
  ScheduleVisibilityResponse,
  ScheduleVisibilityItemDto,
} from "../api/types";
import {
  PUBLICATION_STATE_LABEL,
  STATUS_COLOR,
  publicationStateHelper,
  publicationStateLabel,
  type ScheduleItem,
} from "../models/supervision";
import { buildLinkedInActionMatrix } from "../models/actionAvailability";
import {
  dryRunModeBanner,
  mutationOutcomeToast,
  scheduleOutcomeToast,
} from "../models/mutationMode";

function scheduleItem(
  partial: Partial<ScheduleItem> & { itemId: string },
): ScheduleItem {
  return {
    itemId: partial.itemId,
    channel: partial.channel ?? "linkedin",
    campaignId: partial.campaignId ?? "camp-1",
    variantId: partial.variantId ?? "v1",
    title: partial.title ?? partial.itemId,
    audience: partial.audience ?? "eng",
    scheduledAtUtc: partial.scheduledAtUtc ?? "2026-07-22T15:00:00Z",
    publicationState: partial.publicationState ?? "pending",
    sourceState: partial.sourceState ?? partial.publicationState ?? "pending",
    blocked: partial.blocked ?? false,
    critical: partial.critical ?? false,
    linkedinApiPublished: partial.linkedinApiPublished ?? false,
    calendarItemId: partial.calendarItemId ?? null,
    scheduleEditable: partial.scheduleEditable ?? true,
    scheduleEditBlockReason: partial.scheduleEditBlockReason ?? null,
    cancelledAtUtc: partial.cancelledAtUtc ?? null,
    cancellationPhase: partial.cancellationPhase ?? null,
    cancellationReason: partial.cancellationReason ?? null,
    reopenEligible: partial.reopenEligible ?? false,
    actions: partial.actions ?? ["edit", "defer", "cancel"],
    statusColor:
      partial.statusColor ??
      STATUS_COLOR[partial.publicationState ?? "pending"],
  };
}

describe("US-083 operator-language LinkedIn labels", () => {
  it("maps LinkedIn lifecycle to Scheduled / Waiting to send / Live on LinkedIn / Failed / Cancelled", () => {
    expect(publicationStateLabel("pending")).toBe("Scheduled");
    expect(publicationStateLabel("queued")).toBe("Waiting to send");
    expect(publicationStateLabel("published")).toBe("Live on LinkedIn");
    expect(publicationStateLabel("queued", true)).toBe("Live on LinkedIn");
    expect(publicationStateLabel("failed")).toBe("Failed");
    expect(publicationStateLabel("cancelled")).toBe("Cancelled");
    expect(PUBLICATION_STATE_LABEL.queued).toBe("Waiting to send");
  });

  it("keeps blog Published on blog distinct from Live on LinkedIn", () => {
    expect(publicationStateLabel("completed")).toBe("Published on blog");
    expect(publicationStateLabel("completed", true)).toBe("Published on blog");
    expect(STATUS_COLOR.completed).not.toBe(STATUS_COLOR.published);
    expect(publicationStateLabel("published")).not.toBe(
      publicationStateLabel("completed"),
    );
  });

  it("helper makes Waiting to send unmistakably not LinkedIn API published", () => {
    const helper = publicationStateHelper("queued");
    expect(helper).toMatch(/not yet on LinkedIn/i);
    expect(helper).toMatch(/not LinkedIn API published/i);
    expect(helper).not.toMatch(/live on LinkedIn/i);
  });
});

describe("US-083 action availability matrix", () => {
  it("pending with supervision join lists edit/cancel/reschedule available and publish now unavailable", () => {
    const rows = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-pending",
        publicationState: "pending",
        actions: ["edit", "defer", "cancel"],
        scheduleEditable: true,
      }),
      hasSupervisionJoin: true,
      canMutate: true,
    });
    const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
    expect(byId.edit?.available).toBe(true);
    expect(byId.cancel_pending?.available).toBe(true);
    expect(byId.reschedule?.available).toBe(true);
    expect(byId.publish_now?.available).toBe(false);
    expect(byId.publish_now?.reason).toMatch(/US-086/);
    expect(byId.cancel_queued).toBeUndefined();
  });

  it("queued shows postpone available when schedule-editable; cancel-queued and publish now not yet", () => {
    const rows = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-queued",
        publicationState: "queued",
        actions: [],
        scheduleEditable: true,
      }),
      hasSupervisionJoin: false,
      canMutate: true,
    });
    const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
    expect(byId.reschedule?.available).toBe(true);
    expect(byId.reschedule?.label).toMatch(/Postpone/i);
    expect(byId.cancel_queued?.available).toBe(false);
    expect(byId.cancel_queued?.reason).toMatch(/US-085/);
    expect(byId.cancel_queued?.reason).toMatch(/not live on LinkedIn/i);
    expect(byId.publish_now?.available).toBe(false);
    expect(byId.publish_now?.reason).toMatch(/US-086/);
    expect(byId.edit?.available).toBe(false);
  });

  it("live on LinkedIn cannot postpone", () => {
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
    expect(rows.find((r) => r.id === "reschedule")).toBeUndefined();
    expect(rows.find((r) => r.id === "publish_now")).toBeUndefined();
  });

  it("blocked session explains cannot mutate", () => {
    const rows = buildLinkedInActionMatrix({
      item: scheduleItem({
        itemId: "li-pending",
        publicationState: "pending",
        scheduleEditable: true,
      }),
      hasSupervisionJoin: true,
      canMutate: false,
    });
    expect(rows.find((r) => r.id === "edit")?.reason).toMatch(/cannot mutate/i);
    expect(rows.find((r) => r.id === "reschedule")?.reason).toMatch(
      /cannot mutate/i,
    );
  });
});

describe("US-083 preview vs real outcome copy", () => {
  it("dry-run toast cannot be read as saved or live", () => {
    const text = mutationOutcomeToast("Edit", true, "c1 / v1");
    expect(text).toMatch(/Preview only/i);
    expect(text).toMatch(/No lasting change/i);
    expect(text).toMatch(/Not live on LinkedIn/i);
    expect(text).not.toMatch(/Saved:/);
    expect(text).not.toMatch(/went live/i);
    expect(text).not.toMatch(/Live on LinkedIn/);
  });

  it("real toast states saved without false LinkedIn live claim", () => {
    const text = mutationOutcomeToast("Cancel", false, "c1 / v1");
    expect(text).toMatch(/^Saved:/);
    expect(text).toMatch(/committed/);
    expect(text).toMatch(/Not live on LinkedIn/i);
    expect(text).not.toMatch(/Preview only/i);
  });

  it("schedule preview vs saved copy stays honest", () => {
    expect(scheduleOutcomeToast(true, "item-1", "")).toMatch(
      /Schedule was not saved/i,
    );
    expect(scheduleOutcomeToast(false, "item-1", "New: t.")).toMatch(/^Saved:/);
    expect(dryRunModeBanner(true)).toMatch(/Preview/);
    expect(dryRunModeBanner(false)).toMatch(/Make real change/);
  });
});

function weekAnchoredIso(daysFromMonday: number, hourUtc = 15): string {
  const now = new Date();
  const day = now.getUTCDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  const monday = new Date(
    Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()),
  );
  monday.setUTCDate(monday.getUTCDate() + mondayOffset + daysFromMonday);
  monday.setUTCHours(hourUtc, 0, 0, 0);
  return monday.toISOString().replace(/\.\d{3}Z$/, "Z");
}

describe("US-083 EventModal matrix UI", () => {
  function makeClient(scheduleItems: ScheduleVisibilityItemDto[]) {
    const pending: PendingSupervisionResponse = {
      status: "ok",
      observed_at_utc: "2026-07-18T12:00:00Z",
      read_only: false,
      linkedin_publication_enabled: false,
      variants: scheduleItems
        .filter((i) => i.publication_state === "pending")
        .map((i) => ({
          campaign_id: i.campaign_id!,
          variant_id: i.variant_id!,
          audience: i.audience,
          scheduled_at_utc: i.scheduled_at_utc,
          publish_state: "pending",
          calendar_item_id: i.calendar_item_id,
          calendar_title: i.title,
          calendar_due_at_utc: i.scheduled_at_utc,
          calendar_status: "planned",
          operator_supervision_last_action: null,
          auto_queue_eligible: true,
          operator_supervision_reason: null,
          draft_content: "Draft body",
        })),
      issues: [],
      integration_failures: [],
    };
    const schedule: ScheduleVisibilityResponse = {
      status: "ok",
      observed_at_utc: "2026-07-18T12:00:00Z",
      read_only: false,
      year: new Date().getUTCFullYear(),
      month: new Date().getUTCMonth() + 1,
      from_utc: "2026-07-01T00:00:00Z",
      to_utc: "2026-07-31T23:59:59Z",
      linkedin_publication_enabled: false,
      items: scheduleItems,
      issues: [],
    };
    const auth = new MemoryBearerAuthProvider();
    auth.setTokenForTests("test-token");
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
      return new Response("{}", { status: 404 });
    });
    return new SupervisionApiClient(auth, fetchImpl as typeof fetch);
  }

  it("shows Scheduled label, status helper, and action matrix for pending item (~1280)", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 1280,
    });
    const user = userEvent.setup();
    const when = weekAnchoredIso(2);
    const client = makeClient([
      {
        item_id: "linkedin:camp-1:v1",
        channel: "linkedin",
        campaign_id: "camp-1",
        variant_id: "v1",
        title: "Pending post",
        audience: "eng",
        scheduled_at_utc: when,
        publication_state: "pending",
        source_state: "pending",
        blocked: false,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
      },
    ]);
    render(<App client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => expect(screen.getByTestId("week-view")).toBeInTheDocument());
    expect(screen.getAllByText("Scheduled").length).toBeGreaterThan(0);
    await user.click((await screen.findAllByTestId("week-event-chip"))[0]);
    await waitFor(() => {
      expect(screen.getByTestId("event-modal-status")).toHaveTextContent(
        "Scheduled",
      );
    });
    expect(screen.getByTestId("event-modal-status-helper").textContent).toMatch(
      /not live on LinkedIn/i,
    );
    const matrix = screen.getByTestId("action-availability-matrix");
    expect(matrix).toHaveTextContent(/What you can do now/i);
    expect(screen.getByTestId("action-matrix-edit")).toHaveAttribute(
      "data-available",
      "true",
    );
    expect(screen.getByTestId("action-matrix-publish_now")).toHaveAttribute(
      "data-available",
      "false",
    );
    expect(screen.getByTestId("action-matrix-publish_now")).toHaveTextContent(
      /US-086/,
    );
  });

  it("queued chip/modal show Waiting to send and cancel-queued unavailable (~375)", async () => {
    Object.defineProperty(window, "innerWidth", {
      configurable: true,
      writable: true,
      value: 375,
    });
    const user = userEvent.setup();
    const when = weekAnchoredIso(3);
    const client = makeClient([
      {
        item_id: "linkedin:camp-1:queued",
        channel: "linkedin",
        campaign_id: "camp-1",
        variant_id: "queued",
        title: "Queued post",
        audience: "eng",
        scheduled_at_utc: when,
        publication_state: "queued",
        source_state: "queued",
        blocked: false,
        critical: false,
        linkedin_api_published: false,
        schedule_editable: true,
        schedule_edit_block_reason: null,
      },
    ]);
    render(<App client={client} />);
    await user.click(screen.getByTestId("load-btn"));
    await waitFor(() => expect(screen.getByTestId("week-view")).toBeInTheDocument());
    expect(screen.getAllByText("Waiting to send").length).toBeGreaterThan(0);
    await user.click((await screen.findAllByTestId("week-event-chip"))[0]);
    await waitFor(() => {
      expect(screen.getByTestId("event-modal-status")).toHaveTextContent(
        "Waiting to send",
      );
    });
    expect(screen.getByTestId("event-modal-status-helper").textContent).toMatch(
      /not LinkedIn API published/i,
    );
    expect(screen.getByTestId("action-matrix-reschedule")).toHaveAttribute(
      "data-available",
      "true",
    );
    expect(screen.getByTestId("row-defer")).toHaveTextContent(
      /Postpone \/ reschedule/i,
    );
    expect(screen.getByTestId("action-matrix-cancel_queued")).toHaveAttribute(
      "data-available",
      "false",
    );
    expect(screen.getByTestId("action-matrix-cancel_queued")).toHaveTextContent(
      /US-085/,
    );
    expect(screen.queryByTestId("row-cancel")).not.toBeInTheDocument();
  });
});
