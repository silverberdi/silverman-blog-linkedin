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
 * Shared normalized frontend model for Week + Month calendar (US-040G).
 * LinkedIn identity: campaign_id + variant_id.
 * Blog identity: calendar_item_id (item_id).
 * Pending-supervision remains a data source for detail — not a List UI.
 */

export type ConsoleView = "week" | "month";

export type { PublicationDisplayState, ScheduleChannel };

export interface ScheduleEditorTarget {
  channel: ScheduleChannel;
  itemId: string;
  title: string | null;
  scheduledAtUtc: string | null;
  scheduleEditable: boolean;
  scheduleEditBlockReason: string | null;
  campaignId: string | null;
  variantId: string | null;
  calendarItemId: string | null;
  entry: "week" | "month" | "agenda";
}

export const PUBLICATION_STATES: PublicationDisplayState[] = [
  "planned",
  "pending",
  "queued",
  "published",
  "completed",
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
  /** Distinct from LinkedIn published green — calm teal for site/blog completion. */
  completed: "#2a9d8f",
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
  scheduleEditable: boolean;
  scheduleEditBlockReason: string | null;
  /** US-040J cancellation context from schedule-visibility (cancelled LinkedIn). */
  cancelledAtUtc: string | null;
  cancellationPhase: string | null;
  cancellationReason: string | null;
  reopenEligible: boolean;
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
  calendarFingerprint: string | null;
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

/** Recently-published window: last 7 days UTC from reference time. */
export const RECENTLY_PUBLISHED_DAYS = 7;

/**
 * Operator-facing primary labels (US-083 / US-040M).
 * LinkedIn lifecycle: Scheduled / Waiting to send / Live on LinkedIn / Failed / Cancelled.
 * Blog completed stays verbally distinct from Live on LinkedIn.
 */
export const PUBLICATION_STATE_LABEL: Record<PublicationDisplayState, string> =
  {
    planned: "Planned",
    pending: "Scheduled",
    queued: "Waiting to send",
    published: "Live on LinkedIn",
    completed: "Published on blog",
    deferred: "Deferred",
    cancelled: "Cancelled",
    blocked: "Blocked",
    failed: "Failed",
  };

export function publicationStateLabel(
  state: PublicationDisplayState,
  linkedinApiPublished = false,
): string {
  // Blog completed must never become Live on LinkedIn via API-evidence override.
  if (state === "completed") {
    return PUBLICATION_STATE_LABEL.completed;
  }
  if (linkedinApiPublished || state === "published") {
    return PUBLICATION_STATE_LABEL.published;
  }
  return PUBLICATION_STATE_LABEL[state];
}

/**
 * Short helper under status pills so Waiting to send / queued cannot be read as live.
 * Returns null when no extra helper is needed.
 */
export function publicationStateHelper(
  state: PublicationDisplayState,
  options?: {
    linkedinApiPublished?: boolean;
    channel?: ScheduleChannel;
  },
): string | null {
  const linkedinApiPublished = options?.linkedinApiPublished === true;
  const channel = options?.channel;

  if (channel === "blog" && state === "completed") {
    return "Live on the blog site — not LinkedIn API published.";
  }
  if (state === "completed") {
    return "Published on blog — not LinkedIn API published.";
  }
  if (linkedinApiPublished || state === "published") {
    return "Confirmed LinkedIn API publication evidence.";
  }
  if (state === "queued") {
    return "Authorized / waiting to send — not yet on LinkedIn (not LinkedIn API published).";
  }
  if (state === "pending") {
    return "Not yet authorized to send — not live on LinkedIn.";
  }
  if (state === "failed") {
    return "Did not go live on LinkedIn.";
  }
  if (state === "cancelled") {
    return "Will not send unless restored via reopen — not live on LinkedIn.";
  }
  return null;
}

export interface OperationalCounts {
  upcoming: number;
  pending: number;
  dueSoon: number;
  deferred: number;
  blocked: number;
  failed: number;
  recentlyPublished: number;
}

export function emptyOperationalCounts(): OperationalCounts {
  return {
    upcoming: 0,
    pending: 0,
    dueSoon: 0,
    deferred: 0,
    blocked: 0,
    failed: 0,
    recentlyPublished: 0,
  };
}

export function defaultFilters(): FilterState {
  return {
    channel: "all",
    campaignQuery: "",
    publicationStates: [],
    blockedOnly: false,
    dueSoonOnly: false,
  };
}

/**
 * Count of FilterState fields that diverge from defaultFilters() (US-040L D3).
 * Used for the calm active cue on the header Filters control.
 */
export function countActiveFilters(filters: FilterState): number {
  let count = 0;
  if (filters.channel !== "all") {
    count += 1;
  }
  if (filters.campaignQuery.trim() !== "") {
    count += 1;
  }
  if (filters.blockedOnly) {
    count += 1;
  }
  if (filters.dueSoonOnly) {
    count += 1;
  }
  if (filters.publicationStates.length > 0) {
    count += 1;
  }
  return count;
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
    value === "completed" ||
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
    (row.source_state === "pending" || publicationState === "pending") &&
    row.variant_id != null;
  const scheduleEditable =
    typeof row.schedule_editable === "boolean"
      ? row.schedule_editable
      : pendingLinkedIn ||
        (channel === "blog" &&
          row.source_state !== "completed" &&
          row.source_state !== "skipped" &&
          row.source_state !== "failed");
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
    scheduleEditable,
    scheduleEditBlockReason: row.schedule_edit_block_reason ?? null,
    cancelledAtUtc: row.cancelled_at_utc ?? null,
    cancellationPhase: row.cancellation_phase ?? null,
    cancellationReason: row.cancellation_reason ?? null,
    reopenEligible: row.reopen_eligible === true,
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
    calendarFingerprint: payload.calendar_fingerprint ?? null,
    items: items.map(normalizeScheduleItem),
    issues: Array.isArray(payload.issues) ? payload.issues : [],
  };
}

/** Merge multi-month schedule reads (week spanning month boundary). */
export function mergeScheduleSnapshots(
  primary: ScheduleSnapshot,
  extras: ScheduleSnapshot[],
): ScheduleSnapshot {
  const byId = new Map<string, ScheduleItem>();
  for (const item of primary.items) {
    byId.set(item.itemId, item);
  }
  const issues = [...primary.issues];
  let status = primary.status;
  let linkedinPublicationEnabled = primary.linkedinPublicationEnabled;
  let observedAtUtc = primary.observedAtUtc;
  for (const extra of extras) {
    for (const item of extra.items) {
      byId.set(item.itemId, item);
    }
    issues.push(...extra.issues);
    if (extra.status !== "ok" || status !== "ok") {
      status = status === "ok" ? extra.status : status;
    }
    linkedinPublicationEnabled =
      linkedinPublicationEnabled || extra.linkedinPublicationEnabled;
    if (extra.observedAtUtc > observedAtUtc) {
      observedAtUtc = extra.observedAtUtc;
    }
  }
  return {
    ...primary,
    status,
    observedAtUtc,
    linkedinPublicationEnabled,
    items: [...byId.values()],
    issues,
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
    scheduleEditable:
      item.publishState === "pending" || item.publishState === "queued",
    scheduleEditBlockReason:
      item.publishState === "pending" || item.publishState === "queued"
        ? null
        : "linkedin_supervision_variant_not_pending",
    cancelledAtUtc: null,
    cancellationPhase: null,
    cancellationReason: null,
    reopenEligible: false,
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

export function isDueSoon(
  scheduledAtUtc: string | null,
  nowMs: number = Date.now(),
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

/**
 * Recently published uses `published` display state and/or `linkedinApiPublished`
 * evidence within the last 7 days — never pending/queued/cancelled/flow_a_complete
 * or blog handoff alone.
 */
export function isRecentlyPublished(
  item: ScheduleItem,
  nowMs: number = Date.now(),
): boolean {
  const hasApiEvidence =
    item.publicationState === "published" || item.linkedinApiPublished === true;
  if (!hasApiEvidence) {
    return false;
  }
  if (!item.scheduledAtUtc) {
    return false;
  }
  const ms = Date.parse(item.scheduledAtUtc);
  if (Number.isNaN(ms)) {
    return false;
  }
  const windowMs = RECENTLY_PUBLISHED_DAYS * 24 * 60 * 60 * 1000;
  return ms >= nowMs - windowMs && ms <= nowMs;
}

function isUpcoming(item: ScheduleItem, nowMs: number): boolean {
  // Completed blogs and LinkedIn API-published items are finished work, not upcoming.
  if (
    item.publicationState === "cancelled" ||
    item.publicationState === "completed" ||
    item.publicationState === "published"
  ) {
    return false;
  }
  if (!item.scheduledAtUtc) {
    return false;
  }
  const ms = Date.parse(item.scheduledAtUtc);
  if (Number.isNaN(ms)) {
    return false;
  }
  return ms > nowMs;
}

/**
 * Deduplicate schedule + list filterables by itemId (prefer first occurrence).
 */
export function mergeCountUniverse(
  scheduleItems: readonly ScheduleItem[],
  listItems: readonly ScheduleItem[],
): ScheduleItem[] {
  const seen = new Set<string>();
  const out: ScheduleItem[] = [];
  for (const item of [...scheduleItems, ...listItems]) {
    if (seen.has(item.itemId)) {
      continue;
    }
    seen.add(item.itemId);
    out.push(item);
  }
  return out;
}

/**
 * At-a-glance operational counts from the shared filtered model (US-040E).
 * Failed count includes filtered failed items plus sibling integration failures
 * (display-only) when provided.
 */
export function deriveOperationalCounts(
  items: readonly ScheduleItem[],
  options?: {
    nowMs?: number;
    integrationFailureCount?: number;
  },
): OperationalCounts {
  const nowMs = options?.nowMs ?? Date.now();
  const counts = emptyOperationalCounts();
  for (const item of items) {
    if (isUpcoming(item, nowMs)) {
      counts.upcoming += 1;
    }
    if (item.publicationState === "pending") {
      counts.pending += 1;
    }
    // Due-soon is unfinished work only — exclude completed / published terminal display.
    if (
      item.publicationState !== "completed" &&
      item.publicationState !== "published" &&
      item.publicationState !== "cancelled" &&
      isDueSoon(item.scheduledAtUtc, nowMs)
    ) {
      counts.dueSoon += 1;
    }
    if (item.publicationState === "deferred") {
      counts.deferred += 1;
    }
    if (item.blocked || item.publicationState === "blocked") {
      counts.blocked += 1;
    }
    if (item.publicationState === "failed" || item.critical) {
      counts.failed += 1;
    }
    if (isRecentlyPublished(item, nowMs)) {
      counts.recentlyPublished += 1;
    }
  }
  const siblingFailures = options?.integrationFailureCount ?? 0;
  if (siblingFailures > 0) {
    counts.failed += siblingFailures;
  }
  return counts;
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
