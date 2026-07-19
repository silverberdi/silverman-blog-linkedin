/**
 * US-040K client-side local-day density helpers (aligned with worker D1).
 *
 * Max 2 density members per operator-local day. Uses localDayKey (US-040I).
 * Inclusion: LinkedIn pending|queued|published; blog items shown on schedule.
 * Cancelled and failed are excluded. Self-move excludes the item being edited.
 */

import { localDayKey } from "./dateHelpers";
import type { ScheduleItem } from "./supervision";

export const LOCAL_DAY_FULL_MESSAGE = "This day already has 2 publications";

export const MAX_DENSITY_MEMBERS_PER_LOCAL_DAY = 2;

const LINKEDIN_DENSITY_SOURCE_STATES = new Set([
  "pending",
  "queued",
  "published",
]);

export type DensityCueLevel = "none" | "full" | "over";

export type DensityExclude =
  | { itemId: string }
  | { campaignId: string; variantId: string }
  | { calendarItemId: string };

/** IANA timezone from the browser (sent as operator_timezone on mutations). */
export function operatorTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "";
  } catch {
    return "";
  }
}

/** True when the item occupies a density slot (D1). */
export function isDensityMember(item: ScheduleItem): boolean {
  if (item.channel === "blog") {
    return true;
  }
  if (item.channel === "linkedin") {
    const source = (item.sourceState ?? "").toLowerCase();
    return LINKEDIN_DENSITY_SOURCE_STATES.has(source);
  }
  return false;
}

function matchesExclude(item: ScheduleItem, exclude?: DensityExclude): boolean {
  if (!exclude) {
    return false;
  }
  if ("itemId" in exclude) {
    return item.itemId === exclude.itemId;
  }
  if ("calendarItemId" in exclude) {
    return (
      item.calendarItemId !== null &&
      item.calendarItemId === exclude.calendarItemId
    );
  }
  return (
    item.campaignId === exclude.campaignId &&
    item.variantId === exclude.variantId
  );
}

/** Count density members on a local day key, optionally excluding a moving item. */
export function countDensityOnLocalDay(
  items: readonly ScheduleItem[],
  dayKey: string,
  exclude?: DensityExclude,
): number {
  let count = 0;
  for (const item of items) {
    if (!isDensityMember(item)) {
      continue;
    }
    if (matchesExclude(item, exclude)) {
      continue;
    }
    if (localDayKey(item.scheduledAtUtc) !== dayKey) {
      continue;
    }
    count += 1;
  }
  return count;
}

/**
 * Occupancy of others on the target local day when moving `exclude`
 * (excludes the item being edited from the count).
 */
export function othersOnLocalDay(
  items: readonly ScheduleItem[],
  dayKey: string,
  exclude?: DensityExclude,
): number {
  return countDensityOnLocalDay(items, dayKey, exclude);
}

/** True when placing another item would exceed the max-2 cap. */
export function isLocalDayFull(others: number): boolean {
  return others >= MAX_DENSITY_MEMBERS_PER_LOCAL_DAY;
}

/** True when the day already shows over-capacity (3+). */
export function isLocalDayOverCapacity(count: number): boolean {
  return count >= 3;
}

/** Cue level from total density count (not others). */
export function densityCueLevel(count: number): DensityCueLevel {
  if (count >= 3) {
    return "over";
  }
  if (count >= MAX_DENSITY_MEMBERS_PER_LOCAL_DAY) {
    return "full";
  }
  return "none";
}

/** Build exclude identity for schedule-editor / reopen self-move. */
export function excludeForScheduleItem(
  item: Pick<
    ScheduleItem,
    "itemId" | "channel" | "campaignId" | "variantId" | "calendarItemId"
  >,
): DensityExclude {
  if (
    item.channel === "linkedin" &&
    item.campaignId &&
    item.variantId
  ) {
    return { campaignId: item.campaignId, variantId: item.variantId };
  }
  if (item.channel === "blog" && item.calendarItemId) {
    return { calendarItemId: item.calendarItemId };
  }
  return { itemId: item.itemId };
}
