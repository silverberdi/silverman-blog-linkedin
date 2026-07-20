import type { ScheduleItem } from "./supervision";

/**
 * EventModal “What you can do now” matrix (US-083 / US-084 / US-085 / US-086).
 * Available rows reflect real eligibility; unavailable expected controls stay visible
 * with plain-language reasons.
 */

export type ActionAvailabilityId =
  | "edit"
  | "reschedule"
  | "cancel_pending"
  | "cancel_queued"
  | "reopen"
  | "publish_now";

export interface ActionAvailabilityRow {
  id: ActionAvailabilityId;
  label: string;
  available: boolean;
  reason: string;
}

export interface ActionAvailabilityInput {
  item: ScheduleItem;
  /** Pending-supervision join present (required for edit/cancel-pending). */
  hasSupervisionJoin: boolean;
  canMutate: boolean;
  /** Schedule-visibility enablement flag (worker remains authoritative on real publish). */
  linkedinPublicationEnabled?: boolean;
  /** Optional clock for deferred-future checks (tests). */
  nowMs?: number;
}

function blockReasonPlain(code: string | null): string {
  if (!code) {
    return "Schedule cannot be changed for this item. Choose a Scheduled or Waiting-to-send item, or use reopen for cancelled.";
  }
  if (code === "linkedin_supervision_variant_not_pending") {
    return "Cannot postpone — only Scheduled (pending) or Waiting to send (queued) can be rescheduled. Live, failed, cancelled, or in-flight items need another path (reopen for cancelled).";
  }
  if (code.startsWith("calendar_schedule")) {
    return `Schedule blocked: ${code.replace(/_/g, " ")}. Choose another editable item or fix the calendar status.`;
  }
  return `Schedule blocked: ${code}. Reload the item or choose another local day/time.`;
}

/** Underlying wire publish_state when display state is remapped (e.g. enablement-off → blocked). */
export function linkedInWirePublishState(item: ScheduleItem): string | null {
  if (item.sourceState) {
    return item.sourceState;
  }
  if (
    item.publicationState === "pending" ||
    item.publicationState === "queued" ||
    item.publicationState === "published" ||
    item.publicationState === "cancelled" ||
    item.publicationState === "failed"
  ) {
    return item.publicationState;
  }
  return null;
}

/**
 * Deferred with a future scheduled_at_utc — publish_now must not bypass (worker skips).
 */
export function isDeferredFutureNotDue(
  item: ScheduleItem,
  nowMs: number = Date.now(),
): boolean {
  if (item.publicationState !== "deferred") {
    return false;
  }
  if (!item.scheduledAtUtc) {
    return true;
  }
  const scheduledMs = Date.parse(item.scheduledAtUtc);
  if (Number.isNaN(scheduledMs)) {
    return true;
  }
  return scheduledMs > nowMs;
}

export type PublishNowEligibility =
  | { eligible: true; path: "queued" | "pending" }
  | { eligible: false; reason: string };

/**
 * Whether publish now is a working control for this LinkedIn item (US-086).
 */
export function publishNowEligibility(
  item: ScheduleItem,
  opts: { canMutate: boolean; nowMs?: number } = { canMutate: true },
): PublishNowEligibility {
  const nowMs = opts.nowMs ?? Date.now();
  const isLive =
    item.publicationState === "published" || item.linkedinApiPublished === true;
  if (isLive) {
    return {
      eligible: false,
      reason:
        "Unavailable — already Live on LinkedIn. Publish now is not offered for live posts (no duplicate send).",
    };
  }
  if (item.publicationState === "cancelled") {
    return {
      eligible: false,
      reason:
        "Unavailable — Cancelled. Use Reopen & reschedule first (US-040J), then publish when eligible.",
    };
  }
  const wire = linkedInWirePublishState(item);
  if (wire === "failed" || item.publicationState === "failed") {
    return {
      eligible: false,
      reason:
        "Unavailable — Failed / critical recovery is not the primary publish-now path. Use recovery or cancel paths as applicable; do not treat this as Live on LinkedIn.",
    };
  }
  if (!item.campaignId || !item.variantId) {
    return {
      eligible: false,
      reason:
        "Unavailable — campaign and variant identity are required to publish now. Reload schedule visibility.",
    };
  }
  if (!opts.canMutate) {
    return {
      eligible: false,
      reason:
        "Blocked — this session cannot mutate. Sign in with mutation permission, then publish now.",
    };
  }
  if (isDeferredFutureNotDue(item, nowMs)) {
    return {
      eligible: false,
      reason:
        "Unavailable — deferred time is not due yet. Publish now does not bypass a deferred schedule; wait until the new time or postpone again.",
    };
  }
  if (wire === "queued" || item.publicationState === "queued") {
    return { eligible: true, path: "queued" };
  }
  if (
    wire === "pending" ||
    item.publicationState === "pending" ||
    item.publicationState === "deferred" ||
    item.publicationState === "blocked"
  ) {
    // Enablement-off remaps pending/queued to blocked display; wire state still drives path.
    if (wire === "queued") {
      return { eligible: true, path: "queued" };
    }
    if (wire === "pending" || item.publicationState === "pending" || item.publicationState === "deferred") {
      return { eligible: true, path: "pending" };
    }
    // blocked without pending/queued wire — not a publish-now target
    return {
      eligible: false,
      reason:
        "Unavailable — this item is not in Scheduled (pending) or Waiting to send (queued). Reload if status looks stale.",
    };
  }
  return {
    eligible: false,
    reason:
      "Unavailable — this item is not in Scheduled (pending) or Waiting to send (queued). Reload if status looks stale.",
  };
}

/**
 * Build the LinkedIn action availability matrix for an opened EventModal item.
 * Blog items return an empty list (matrix is LinkedIn-only).
 */
export function buildLinkedInActionMatrix(
  input: ActionAvailabilityInput,
): ActionAvailabilityRow[] {
  const { item, hasSupervisionJoin, canMutate } = input;
  if (item.channel !== "linkedin") {
    return [];
  }

  const state = item.publicationState;
  const isLive =
    state === "published" || item.linkedinApiPublished === true;
  const isCancelled = state === "cancelled";
  const wire = linkedInWirePublishState(item);
  const isQueued = wire === "queued" || state === "queued";
  const isPendingLike =
    !isLive &&
    !isCancelled &&
    (state === "pending" ||
      state === "deferred" ||
      state === "blocked" ||
      wire === "pending");
  const canEdit =
    hasSupervisionJoin && item.actions.includes("edit") && isPendingLike && !isQueued;
  const canCancelPending =
    hasSupervisionJoin &&
    item.actions.includes("cancel") &&
    isPendingLike &&
    !isQueued &&
    wire !== "queued";
  const hasCancelIdentity = Boolean(item.campaignId && item.variantId);
  const canCancelQueued = isQueued && hasCancelIdentity;
  const canReopen =
    isCancelled &&
    item.reopenEligible &&
    hasCancelIdentity;

  const rows: ActionAvailabilityRow[] = [];

  // Edit draft — expected for pre-send; omit once cancelled/live (reopen path owns restore).
  if (!isCancelled && !isLive) {
    if (canEdit && canMutate) {
      rows.push({
        id: "edit",
        label: "Edit draft",
        available: true,
        reason: "Available — pending supervision window.",
      });
    } else if (canEdit && !canMutate) {
      rows.push({
        id: "edit",
        label: "Edit draft",
        available: false,
        reason:
          "Blocked — this session cannot mutate. Sign in with mutation permission.",
      });
    } else {
      rows.push({
        id: "edit",
        label: "Edit draft",
        available: false,
        reason: isQueued
          ? "Unavailable — Waiting to send is past the edit window (not live on LinkedIn)."
          : "Unavailable — not in the pending supervision window.",
      });
    }
  }

  // Postpone / reschedule — deliberate control for Scheduled + Waiting to send (US-084).
  if (!isLive) {
    if (item.scheduleEditable && canMutate) {
      rows.push({
        id: "reschedule",
        label: "Postpone / reschedule",
        available: true,
        reason:
          "Available — open the postpone control, pick a future local time, then Preview (no change) or Make real change. Does not cancel Waiting to send.",
      });
    } else if (item.scheduleEditable && !canMutate) {
      rows.push({
        id: "reschedule",
        label: "Postpone / reschedule",
        available: false,
        reason:
          "Blocked — schedule is editable, but this session cannot mutate. Sign in with mutation permission, then postpone.",
      });
    } else {
      rows.push({
        id: "reschedule",
        label: "Postpone / reschedule",
        available: false,
        reason: blockReasonPlain(item.scheduleEditBlockReason),
      });
    }
  }

  // Cancel while scheduled (US-017 / US-085) — show for pre-send; omit when cancelled/live.
  if (isPendingLike && !isQueued) {
    if (canCancelPending && canMutate) {
      rows.push({
        id: "cancel_pending",
        label: "Cancel (while scheduled)",
        available: true,
        reason:
          "Available — open Cancel, then Preview (no change) or Make real change with confirmation. Withdraws the variant (will not send); not postpone and not a LinkedIn API unpublish.",
      });
    } else if (canCancelPending && !canMutate) {
      rows.push({
        id: "cancel_pending",
        label: "Cancel (while scheduled)",
        available: false,
        reason:
          "Blocked — this session cannot mutate. Sign in with mutation permission, then cancel.",
      });
    } else {
      rows.push({
        id: "cancel_pending",
        label: "Cancel (while scheduled)",
        available: false,
        reason: "Unavailable — pending cancel requires supervision join.",
      });
    }
  }

  // Cancel while waiting to send — working control via schedule identity (US-085).
  if (isQueued) {
    if (canCancelQueued && canMutate) {
      rows.push({
        id: "cancel_queued",
        label: "Cancel (while waiting to send)",
        available: true,
        reason:
          "Available — open Cancel, then Preview (no change) or Make real change with confirmation. Withdraws via cancel endpoint (will not send); not postpone and not a LinkedIn API unpublish.",
      });
    } else if (canCancelQueued && !canMutate) {
      rows.push({
        id: "cancel_queued",
        label: "Cancel (while waiting to send)",
        available: false,
        reason:
          "Blocked — this session cannot mutate. Sign in with mutation permission, then cancel.",
      });
    } else {
      rows.push({
        id: "cancel_queued",
        label: "Cancel (while waiting to send)",
        available: false,
        reason:
          "Unavailable — campaign and variant identity are required to cancel Waiting to send. Reload schedule visibility.",
      });
    }
  }

  // Reopen — only when cancelled (omit otherwise).
  if (isCancelled) {
    if (canReopen && canMutate) {
      rows.push({
        id: "reopen",
        label: "Reopen & reschedule",
        available: true,
        reason:
          "Available — you can reopen and choose a new local schedule. Returns to editable Scheduled (pending); not queued, not live on LinkedIn.",
      });
    } else if (canReopen && !canMutate) {
      rows.push({
        id: "reopen",
        label: "Reopen & reschedule",
        available: false,
        reason:
          "Blocked — reopen is eligible, but this session cannot mutate. Sign in with mutation permission.",
      });
    } else {
      rows.push({
        id: "reopen",
        label: "Reopen & reschedule",
        available: false,
        reason:
          "Unavailable — this cancellation is not reopen-eligible (for example a recovery cancel).",
      });
    }
  }

  // Publish now — working control when eligible (US-086); omit when already Live.
  if (!isLive) {
    const pub = publishNowEligibility(item, {
      canMutate,
      nowMs: input.nowMs,
    });
    if (pub.eligible) {
      const enablementNote =
        input.linkedinPublicationEnabled === false
          ? " LinkedIn publication enablement is off — real publish will fail closed at the worker."
          : "";
      const pathNote =
        pub.path === "queued"
          ? "Sends via publish-due with publish_now (Waiting to send)."
          : "Queues then sends in one action (auto_queue_pending + publish_now) for Scheduled.";
      rows.push({
        id: "publish_now",
        label: "Publish now",
        available: true,
        reason: `Available — open Publish now, then Preview or Real with confirmation. ${pathNote} Distinct from postpone and cancel.${enablementNote}`,
      });
    } else {
      rows.push({
        id: "publish_now",
        label: "Publish now",
        available: false,
        reason: pub.reason,
      });
    }
  }

  return rows;
}
