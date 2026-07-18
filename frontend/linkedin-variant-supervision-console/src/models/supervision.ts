import type {
  IntegrationFailureDto,
  PendingSupervisionResponse,
  PendingSupervisionVariantDto,
  SupervisionIssueDto,
} from "../api/types";

/**
 * Shared normalized frontend model for list + calendar scaffolds.
 * Identity is campaign_id + variant_id — both views must use the same store.
 */

export type ConsoleView = "list" | "calendar";

export interface SupervisionItem {
  campaignId: string;
  variantId: string;
  audience: string | null;
  scheduledAtUtc: string | null;
  publishState: string;
  calendarItemId: string | null;
  calendarTitle: string | null;
  calendarDueAtUtc: string | null;
  calendarStatus: string | null;
  operatorSupervisionLastAction: string | null;
  autoQueueEligible: boolean | null;
  operatorSupervisionReason: string | null;
  draftContent: string | null;
  /** Actions available while in pending supervision window. */
  actions: ReadonlyArray<"edit" | "defer" | "cancel">;
  deferredOrIneligible: boolean;
}

export interface SupervisionSnapshot {
  status: string;
  observedAtUtc: string;
  readOnly: boolean;
  linkedinPublicationEnabled: boolean;
  items: SupervisionItem[];
  issues: SupervisionIssueDto[];
  integrationFailures: IntegrationFailureDto[];
}

export function itemKey(campaignId: string, variantId: string): string {
  return `${campaignId}::${variantId}`;
}

export function normalizeVariant(
  row: PendingSupervisionVariantDto,
): SupervisionItem {
  const deferredOrIneligible =
    row.operator_supervision_last_action === "defer" ||
    row.auto_queue_eligible === false;
  return {
    campaignId: row.campaign_id,
    variantId: row.variant_id,
    audience: row.audience,
    scheduledAtUtc: row.scheduled_at_utc,
    publishState: row.publish_state,
    calendarItemId: row.calendar_item_id,
    calendarTitle: row.calendar_title,
    calendarDueAtUtc: row.calendar_due_at_utc,
    calendarStatus: row.calendar_status,
    operatorSupervisionLastAction: row.operator_supervision_last_action,
    autoQueueEligible: row.auto_queue_eligible,
    operatorSupervisionReason: row.operator_supervision_reason,
    draftContent: row.draft_content,
    actions: ["edit", "defer", "cancel"],
    deferredOrIneligible,
  };
}

export function normalizePendingSupervision(
  payload: PendingSupervisionResponse,
): SupervisionSnapshot {
  const variants = Array.isArray(payload.variants) ? payload.variants : [];
  return {
    status: payload.status || "unknown",
    observedAtUtc: payload.observed_at_utc || "",
    readOnly: payload.read_only === true,
    linkedinPublicationEnabled: payload.linkedin_publication_enabled === true,
    items: variants.map(normalizeVariant),
    issues: Array.isArray(payload.issues) ? payload.issues : [],
    integrationFailures: Array.isArray(payload.integration_failures)
      ? payload.integration_failures
      : [],
  };
}

export function findItem(
  snapshot: SupervisionSnapshot | null,
  campaignId: string,
  variantId: string,
): SupervisionItem | null {
  if (!snapshot) {
    return null;
  }
  return (
    snapshot.items.find(
      (item) =>
        item.campaignId === campaignId && item.variantId === variantId,
    ) ?? null
  );
}
