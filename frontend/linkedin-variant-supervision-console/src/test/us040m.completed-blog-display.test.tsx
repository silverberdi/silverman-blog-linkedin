import { describe, expect, it } from "vitest";
import {
  PUBLICATION_STATE_LABEL,
  PUBLICATION_STATES,
  STATUS_COLOR,
  applyFilters,
  defaultFilters,
  deriveOperationalCounts,
  normalizeScheduleItem,
  publicationStateLabel,
  type ScheduleItem,
} from "../models/supervision";
import type { ScheduleVisibilityItemDto } from "../api/types";

function scheduleItem(partial: Partial<ScheduleItem> & { itemId: string }): ScheduleItem {
  return {
    itemId: partial.itemId,
    channel: partial.channel ?? "blog",
    campaignId: partial.campaignId ?? null,
    variantId: partial.variantId ?? null,
    title: partial.title ?? partial.itemId,
    audience: partial.audience ?? null,
    scheduledAtUtc: partial.scheduledAtUtc ?? "2026-07-22T09:00:00Z",
    publicationState: partial.publicationState ?? "planned",
    sourceState: partial.sourceState ?? partial.publicationState ?? "planned",
    blocked: partial.blocked ?? false,
    critical: partial.critical ?? false,
    linkedinApiPublished: partial.linkedinApiPublished ?? false,
    linkedinPostUrn: partial.linkedinPostUrn ?? null,
    calendarItemId: partial.calendarItemId ?? partial.itemId,
    scheduleEditable: partial.scheduleEditable ?? false,
    scheduleEditBlockReason: partial.scheduleEditBlockReason ?? null,
    cancelledAtUtc: partial.cancelledAtUtc ?? null,
    cancellationPhase: partial.cancellationPhase ?? null,
    cancellationReason: partial.cancellationReason ?? null,
    reopenEligible: partial.reopenEligible ?? false,
    actions: partial.actions ?? [],
    statusColor: partial.statusColor ?? STATUS_COLOR[partial.publicationState ?? "planned"],
  };
}

describe("US-040M completed blog display", () => {
  const nowMs = Date.parse("2026-07-18T12:00:00Z");

  it("labels completed as Published on blog, distinct from LinkedIn published", () => {
    expect(PUBLICATION_STATES).toContain("completed");
    expect(PUBLICATION_STATE_LABEL.completed).toBe("Published on blog");
    expect(publicationStateLabel("completed")).toBe("Published on blog");
    expect(publicationStateLabel("published")).toBe("Live on LinkedIn");
    expect(STATUS_COLOR.completed).not.toBe(STATUS_COLOR.published);
  });

  it("normalizes schedule-visibility completed blog without API published claim", () => {
    const row: ScheduleVisibilityItemDto = {
      item_id: "blog:blog-completed",
      channel: "blog",
      campaign_id: "flow-a-2026-07-18",
      variant_id: null,
      title: "Completed handoff post",
      audience: null,
      scheduled_at_utc: "2026-07-22T09:00:00Z",
      publication_state: "completed",
      source_state: "completed",
      blocked: false,
      critical: false,
      linkedin_api_published: false,
      calendar_item_id: "blog-completed",
      schedule_editable: false,
      schedule_edit_block_reason: "calendar_schedule_unsupported_state",
    };
    const item = normalizeScheduleItem(row);
    expect(item.publicationState).toBe("completed");
    expect(item.linkedinApiPublished).toBe(false);
    expect(item.scheduleEditable).toBe(false);
    expect(publicationStateLabel(item.publicationState, item.linkedinApiPublished)).toBe(
      "Published on blog",
    );
  });

  it("filters include completed / Published on blog without matching LinkedIn published", () => {
    const completed = scheduleItem({
      itemId: "blog-completed",
      channel: "blog",
      publicationState: "completed",
      linkedinApiPublished: false,
    });
    const linkedinPublished = scheduleItem({
      itemId: "li-published",
      channel: "linkedin",
      publicationState: "published",
      linkedinApiPublished: true,
      campaignId: "c1",
      variantId: "v1",
    });
    const filters = {
      ...defaultFilters(),
      publicationStates: ["completed" as const],
    };
    const filtered = applyFilters([completed, linkedinPublished], filters, nowMs);
    expect(filtered.map((i) => i.itemId)).toEqual(["blog-completed"]);
  });

  it("does not count completed blogs as upcoming, pending, or due soon", () => {
    const completedFuture = scheduleItem({
      itemId: "blog-completed",
      channel: "blog",
      publicationState: "completed",
      scheduledAtUtc: "2026-07-19T10:00:00Z", // within 48h and future
      linkedinApiPublished: false,
    });
    const pendingFuture = scheduleItem({
      itemId: "li-pending",
      channel: "linkedin",
      publicationState: "pending",
      scheduledAtUtc: "2026-07-19T10:00:00Z",
    });
    const counts = deriveOperationalCounts([completedFuture, pendingFuture], {
      nowMs,
    });
    expect(counts.upcoming).toBe(1); // pending only
    expect(counts.pending).toBe(1);
    expect(counts.dueSoon).toBe(1); // pending only
    expect(counts.recentlyPublished).toBe(0);
  });
});
