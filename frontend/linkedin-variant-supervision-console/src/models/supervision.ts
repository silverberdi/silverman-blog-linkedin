import type {
  IntegrationFailureDto,
  PendingSupervisionResponse,
  PendingSupervisionVariantDto,
  PublicationDisplayState,
  ScheduleChannel,
  ScheduleVisibilityItemDto,
  ScheduleVisibilityResponse,
  SupervisionIssueDto,
} from "../api/types";

/**
 * Shared normalized frontend model for list + month calendar (US-040B).
 * LinkedIn identity: campaign_id + variant_id.
 * Blog identity: calendar_item_id (item_id).
 */

export type ConsoleView = "list" | "calendar";

export type { PublicationDisplayState, ScheduleChannel };

export const PUBLICATION_STATES: PublicationDisplayState[] = [
  "planned",
  "pending",
  "queued",
  "published",
  "deferred",
  "cancelled",
  "blocked",
  "failed",
];

/** Status color tokens keyed by operator-facing display state. */
export const STATUS_COLOR: Record<PublicationDisplayState, string> = {
  planned: "#6b8cae",
  pending: "#c9a227",
  queued: "#3d8bfd",
  published: "#3d9a6a",
  deferred: "#b07d4a",
  cancelled: "#8a8a8a",
  blocked: "#d97706",
  failed: "#e35d6a",
};

export interface ScheduleItem {
  itemId: string;
  channel: ScheduleChannel;
  campaignId: string | null;
  variantId: string | null;
  title: string | null;
  audience: string | null;
  scheduledAtUtc: string | null;
  publicationState: PublicationDisplayState;
  sourceState: string | null;
  blocked: boolean;
  critical: boolean;
  linkedinApiPublished: boolean;
  calendarItemId: string | null;
  /** Actions only for pending LinkedIn supervision rows. */
  actions: ReadonlyArray<"edit" | "defer" | "cancel">;
  statusColor: string;
}

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
  actions: ReadonlyArray<"edit" | "defer" | "cancel">;
  deferredOrIneligible: boolean;
  /** Shared-model fields for cross-view recognizability. */
  itemId: string;
  channel: ScheduleChannel;
  publicationState: PublicationDisplayState;
  title: string | null;
  blocked: boolean;
  critical: boolean;
  linkedinApiPublished: boolean;
  statusColor: string;
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

export interface ScheduleSnapshot {
  status: string;
  observedAtUtc: string;
  readOnly: boolean;
  year: number;
  month: number;
  fromUtc: string;
  toUtc: string;
  linkedinPublicationEnabled: boolean;
  items: ScheduleItem[];
  issues: SupervisionIssueDto[];
}

export interface FilterState {
  channel: "all" | ScheduleChannel;
  campaignQuery: string;
  publicationStates: PublicationDisplayState[];
  blockedOnly: boolean;
  dueSoonOnly: boolean;
}

/** Due-soon window: next 48 hours from reference time. */
export const DUE_SOON_HOURS = 48;

export function defaultFilters(): FilterState {
  return {
    channel: "all",
    campaignQuery: "",
    publicationStates: [],
    blockedOnly: false,
    dueSoonOnly: false,
  };
}

export function itemKey(campaignId: string, variantId: string): string {
  return `${campaignId}::${variantId}`;
}

export function linkedinItemId(campaignId: string, variantId: string): string {
  return `linkedin:${campaignId}:${variantId}`;
}

function asDisplayState(value: string | null | undefined): PublicationDisplayState {
  if (
    value === "planned" ||
    value === "pending" ||
    value === "queued" ||
    value === "published" ||
    value === "deferred" ||
    value === "cancelled" ||
    value === "blocked" ||
    value === "failed"
  ) {
    return value;
  }
  return "pending";
}

function displayStateFromPending(row: PendingSupervisionVariantDto): {
  publicationState: PublicationDisplayState;
  blocked: boolean;
  critical: boolean;
} {
  const deferred =
    row.operator_supervision_last_action === "defer" ||
    row.auto_queue_eligible === false;
  if (deferred) {
    return { publicationState: "deferred", blocked: false, critical: false };
  }
  return { publicationState: "pending", blocked: false, critical: false };
}

export function normalizeVariant(
  row: PendingSupervisionVariantDto,
): SupervisionItem {
  const deferredOrIneligible =
    row.operator_supervision_last_action === "defer" ||
    row.auto_queue_eligible === false;
  const { publicationState, blocked, critical } = displayStateFromPending(row);
  const title =
    row.calendar_title || row.audience || row.variant_id || row.campaign_id;
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
    itemId: linkedinItemId(row.campaign_id, row.variant_id),
    channel: "linkedin",
    publicationState,
    title,
    blocked,
    critical,
    linkedinApiPublished: false,
    statusColor: STATUS_COLOR[publicationState],
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

export function normalizeScheduleItem(
  row: ScheduleVisibilityItemDto,
): ScheduleItem {
  const channel: ScheduleChannel = row.channel === "blog" ? "blog" : "linkedin";
  const publicationState = asDisplayState(row.publication_state);
  const pendingLinkedIn =
    channel === "linkedin" &&
    publicationState === "pending" &&
    row.variant_id != null;
  return {
    itemId: row.item_id,
    channel,
    campaignId: row.campaign_id,
    variantId: row.variant_id,
    title: row.title,
    audience: row.audience,
    scheduledAtUtc: row.scheduled_at_utc,
    publicationState,
    sourceState: row.source_state,
    blocked: row.blocked === true,
    critical: row.critical === true,
    linkedinApiPublished: row.linkedin_api_published === true,
    calendarItemId: row.calendar_item_id ?? null,
    actions: pendingLinkedIn ? ["edit", "defer", "cancel"] : [],
    statusColor: STATUS_COLOR[publicationState],
  };
}

export function normalizeScheduleVisibility(
  payload: ScheduleVisibilityResponse,
): ScheduleSnapshot {
  const items = Array.isArray(payload.items) ? payload.items : [];
  return {
    status: payload.status || "unknown",
    observedAtUtc: payload.observed_at_utc || "",
    readOnly: payload.read_only === true,
    year: payload.year,
    month: payload.month,
    fromUtc: payload.from_utc || "",
    toUtc: payload.to_utc || "",
    linkedinPublicationEnabled: payload.linkedin_publication_enabled === true,
    items: items.map(normalizeScheduleItem),
    issues: Array.isArray(payload.issues) ? payload.issues : [],
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

export function supervisionToFilterable(item: SupervisionItem): ScheduleItem {
  return {
    itemId: item.itemId,
    channel: item.channel,
    campaignId: item.campaignId,
    variantId: item.variantId,
    title: item.title,
    audience: item.audience,
    scheduledAtUtc: item.scheduledAtUtc,
    publicationState: item.publicationState,
    sourceState: item.publishState,
    blocked: item.blocked,
    critical: item.critical,
    linkedinApiPublished: item.linkedinApiPublished,
    calendarItemId: item.calendarItemId,
    actions: item.actions,
    statusColor: item.statusColor,
  };
}

function matchesCampaignQuery(item: ScheduleItem, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) {
    return true;
  }
  const haystack = [
    item.campaignId,
    item.variantId,
    item.title,
    item.calendarItemId,
    item.itemId,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return haystack.includes(q);
}

function isDueSoon(
  scheduledAtUtc: string | null,
  nowMs: number,
): boolean {
  if (!scheduledAtUtc) {
    return false;
  }
  const ms = Date.parse(scheduledAtUtc);
  if (Number.isNaN(ms)) {
    return false;
  }
  const windowMs = DUE_SOON_HOURS * 60 * 60 * 1000;
  return ms >= nowMs && ms <= nowMs + windowMs;
}

export function itemMatchesFilters(
  item: ScheduleItem,
  filters: FilterState,
  nowMs: number = Date.now(),
): boolean {
  if (filters.channel !== "all" && item.channel !== filters.channel) {
    return false;
  }
  if (!matchesCampaignQuery(item, filters.campaignQuery)) {
    return false;
  }
  if (
    filters.publicationStates.length > 0 &&
    !filters.publicationStates.includes(item.publicationState)
  ) {
    return false;
  }
  if (filters.blockedOnly && !item.blocked) {
    return false;
  }
  if (filters.dueSoonOnly && !isDueSoon(item.scheduledAtUtc, nowMs)) {
    return false;
  }
  return true;
}

export function applyFilters<T extends ScheduleItem>(
  items: readonly T[],
  filters: FilterState,
  nowMs: number = Date.now(),
): T[] {
  return items.filter((item) => itemMatchesFilters(item, filters, nowMs));
}

export function countHiddenCritical(
  allItems: readonly ScheduleItem[],
  filteredItems: readonly ScheduleItem[],
): number {
  const visibleIds = new Set(filteredItems.map((item) => item.itemId));
  return allItems.filter(
    (item) =>
      (item.critical || item.publicationState === "failed") &&
      !visibleIds.has(item.itemId),
  ).length;
}
