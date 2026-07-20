import type { ScheduleItem } from "./supervision";

/**
 * EventModal “What you can do now” matrix (US-083).
 * Available rows reflect real eligibility; unavailable expected controls stay visible
 * with plain-language reasons (including not-yet for US-085 / US-086).
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
  const isQueued = state === "queued";
  const isPendingLike =
    state === "pending" || state === "deferred" || state === "blocked";
  const canEdit =
    hasSupervisionJoin && item.actions.includes("edit") && isPendingLike;
  const canCancelPending =
    hasSupervisionJoin && item.actions.includes("cancel") && isPendingLike;
  const canReopen =
    isCancelled &&
    item.reopenEligible &&
    Boolean(item.campaignId && item.variantId);

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

  // Cancel pending (existing US-017) — show for pre-send; omit when cancelled/live.
  if (isPendingLike) {
    if (canCancelPending && canMutate) {
      rows.push({
        id: "cancel_pending",
        label: "Cancel (while scheduled)",
        available: true,
        reason: "Available — cancels before queue; not a LinkedIn API unpublish.",
      });
    } else if (canCancelPending && !canMutate) {
      rows.push({
        id: "cancel_pending",
        label: "Cancel (while scheduled)",
        available: false,
        reason:
          "Blocked — this session cannot mutate. Sign in with mutation permission.",
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

  // Cancel while waiting to send — expected when queued; always not shipped (US-085).
  if (isQueued) {
    rows.push({
      id: "cancel_queued",
      label: "Cancel (while waiting to send)",
      available: false,
      reason:
        "Not available yet (US-085) — Waiting to send is not live on LinkedIn, but cancel-from-console for queued is not shipped yet.",
    });
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

  // Publish now — expected whenever not already live; never a working control in US-083.
  if (!isLive) {
    const failedContext = item.critical || state === "failed";
    rows.push({
      id: "publish_now",
      label: "Publish now",
      available: false,
      reason: failedContext
        ? "Not available yet (US-086) — item failed or is critical and is not live on LinkedIn; publish-now from console is not shipped."
        : "Not available yet (US-086) — no LinkedIn API publish from this console in this story.",
    });
  }

  return rows;
}
