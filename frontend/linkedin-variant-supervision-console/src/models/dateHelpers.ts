/**
 * Operator-local day-bucketing and calendar helpers (US-040I).
 *
 * Primary Week/Month placement uses the local calendar date of scheduled_at_utc
 * in the browser timezone. UTC day keys remain for expandable diagnostics only.
 * Schedule-visibility still queries worker year/month windows; the console pads
 * local cursors so near-edge local days are not dropped (design D4).
 */

/** Short timezone cue for primary displays (e.g. CST / CDT). */
export function operatorTimezoneCue(at: Date = new Date()): string {
  try {
    const parts = new Intl.DateTimeFormat(undefined, {
      timeZoneName: "short",
    }).formatToParts(at);
    return parts.find((p) => p.type === "timeZoneName")?.value ?? "";
  } catch {
    return "";
  }
}

/** UTC calendar day of an ISO instant — diagnostics only after US-040I. */
export function utcDayKey(isoUtc: string | null | undefined): string | null {
  if (!isoUtc) {
    return null;
  }
  const ms = Date.parse(isoUtc);
  if (Number.isNaN(ms)) {
    return null;
  }
  const d = new Date(ms);
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, "0");
  const day = String(d.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

/** Operator-local calendar day of an ISO instant (primary placement key). */
export function localDayKey(isoUtc: string | null | undefined): string | null {
  if (!isoUtc) {
    return null;
  }
  const ms = Date.parse(isoUtc);
  if (Number.isNaN(ms)) {
    return null;
  }
  const d = new Date(ms);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function formatUtcDisplay(isoUtc: string | null | undefined): string {
  if (!isoUtc) {
    return "—";
  }
  return isoUtc.endsWith("Z") || /[+-]\d{2}:\d{2}$/.test(isoUtc)
    ? isoUtc
    : `${isoUtc}Z`;
}

export function formatLocalDisplay(isoUtc: string | null | undefined): string {
  if (!isoUtc) {
    return "—";
  }
  const ms = Date.parse(isoUtc);
  if (Number.isNaN(ms)) {
    return "—";
  }
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
      timeZoneName: "short",
    }).format(new Date(ms));
  } catch {
    return new Date(ms).toString();
  }
}

/** Local wall-clock time for event chips (day already shown in column header). */
export function formatLocalTime(isoUtc: string | null | undefined): string {
  if (!isoUtc) {
    return "—";
  }
  const ms = Date.parse(isoUtc);
  if (Number.isNaN(ms)) {
    return "—";
  }
  try {
    return new Intl.DateTimeFormat(undefined, {
      timeStyle: "short",
      timeZoneName: "short",
    }).format(new Date(ms));
  } catch {
    return new Date(ms).toString();
  }
}

export interface MonthCursor {
  year: number;
  month: number; // 1–12
}

/** Week cursor: Sunday-start local week identified by week-start day key. */
export interface WeekCursor {
  weekStartKey: string;
}

export function parseDayKey(dayKey: string): {
  year: number;
  month: number;
  day: number;
} {
  const [y, m, d] = dayKey.split("-").map(Number);
  return { year: y, month: m, day: d };
}

export function dayKeyFromParts(year: number, month: number, day: number): string {
  const m = String(month).padStart(2, "0");
  const d = String(day).padStart(2, "0");
  return `${year}-${m}-${d}`;
}

/** Abstract calendar-day arithmetic on YYYY-MM-DD keys (timezone-independent). */
export function addDays(dayKey: string, delta: number): string {
  const { year, month, day } = parseDayKey(dayKey);
  const ms = Date.UTC(year, month - 1, day + delta);
  const d = new Date(ms);
  return dayKeyFromParts(
    d.getUTCFullYear(),
    d.getUTCMonth() + 1,
    d.getUTCDate(),
  );
}

/** @deprecated Prefer addDays — kept as alias for call-site clarity during migration. */
export function addUtcDays(dayKey: string, delta: number): string {
  return addDays(dayKey, delta);
}

/** Sunday that starts the week containing dayKey (abstract calendar weekday). */
export function sundayLocalWeekStart(dayKey: string): string {
  const { year, month, day } = parseDayKey(dayKey);
  const d = new Date(Date.UTC(year, month - 1, day));
  const weekday = d.getUTCDay(); // 0 = Sunday
  return addDays(dayKey, -weekday);
}

/** @deprecated Prefer sundayLocalWeekStart. */
export function sundayUtcWeekStart(dayKey: string): string {
  return sundayLocalWeekStart(dayKey);
}

export function currentLocalMonth(): MonthCursor {
  const now = new Date();
  return { year: now.getFullYear(), month: now.getMonth() + 1 };
}

export function currentLocalWeek(): WeekCursor {
  return { weekStartKey: sundayLocalWeekStart(todayLocalDayKey()) };
}

/** @deprecated Prefer currentLocalMonth. */
export function currentUtcMonth(): MonthCursor {
  return currentLocalMonth();
}

/** @deprecated Prefer currentLocalWeek. */
export function currentUtcWeek(): WeekCursor {
  return currentLocalWeek();
}

export function shiftMonth(cursor: MonthCursor, delta: number): MonthCursor {
  const index = cursor.year * 12 + (cursor.month - 1) + delta;
  const year = Math.floor(index / 12);
  const month = (index % 12) + 1;
  return { year, month };
}

export function shiftWeek(cursor: WeekCursor, deltaWeeks: number): WeekCursor {
  return {
    weekStartKey: addDays(cursor.weekStartKey, deltaWeeks * 7),
  };
}

export function monthLabel(cursor: MonthCursor): string {
  // Noon UTC on the 1st avoids DST edge ambiguity for month/year labels.
  const d = new Date(Date.UTC(cursor.year, cursor.month - 1, 1, 12, 0, 0));
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}

export function weekLabel(cursor: WeekCursor): string {
  const start = cursor.weekStartKey;
  const end = addDays(start, 6);
  const startParts = parseDayKey(start);
  const endParts = parseDayKey(end);
  const startDate = new Date(
    Date.UTC(startParts.year, startParts.month - 1, startParts.day, 12, 0, 0),
  );
  const endDate = new Date(
    Date.UTC(endParts.year, endParts.month - 1, endParts.day, 12, 0, 0),
  );
  const startFmt = new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(startDate);
  const endFmt = new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(endDate);
  const tz = operatorTimezoneCue();
  return tz ? `${startFmt} – ${endFmt} (${tz})` : `${startFmt} – ${endFmt}`;
}

export function todayLocalDayKey(): string {
  return localDayKey(new Date().toISOString()) ?? "";
}

/** @deprecated Prefer todayLocalDayKey. */
export function todayUtcDayKey(): string {
  return todayLocalDayKey();
}

/** Seven consecutive day keys starting at weekStartKey (Sunday). */
export function buildWeekDayKeys(weekStartKey: string): string[] {
  return Array.from({ length: 7 }, (_, i) => addDays(weekStartKey, i));
}

export function buildLocalWeekDayKeys(weekStartKey: string): string[] {
  return buildWeekDayKeys(weekStartKey);
}

function daysInMonth(cursor: MonthCursor): number {
  return new Date(Date.UTC(cursor.year, cursor.month, 0)).getUTCDate();
}

/** Unique year/month cursors covering an inclusive day-key range. */
export function monthsCoveringDayKeyRange(
  startKey: string,
  endKey: string,
): MonthCursor[] {
  const seen = new Set<string>();
  const out: MonthCursor[] = [];
  let key = startKey;
  // Guard against inverted ranges.
  if (startKey > endKey) {
    return monthsCoveringDayKeyRange(endKey, startKey);
  }
  for (;;) {
    const { year, month } = parseDayKey(key);
    const id = `${year}-${month}`;
    if (!seen.has(id)) {
      seen.add(id);
      out.push({ year, month });
    }
    if (key === endKey) {
      break;
    }
    key = addDays(key, 1);
  }
  return out;
}

/**
 * UTC year/month queries needed for a Sunday-start local week, with ±1 day pad
 * so near-midnight local edge items are not dropped by worker month windows.
 */
export function monthsCoveringWeek(weekStartKey: string): MonthCursor[] {
  const paddedStart = addDays(weekStartKey, -1);
  const paddedEnd = addDays(weekStartKey, 7); // day after week end
  return monthsCoveringDayKeyRange(paddedStart, paddedEnd);
}

/**
 * UTC year/month queries needed for a local month cursor, with ±1 day pad
 * (design D4).
 */
export function monthsCoveringLocalMonth(cursor: MonthCursor): MonthCursor[] {
  const first = dayKeyFromParts(cursor.year, cursor.month, 1);
  const last = dayKeyFromParts(cursor.year, cursor.month, daysInMonth(cursor));
  return monthsCoveringDayKeyRange(addDays(first, -1), addDays(last, 1));
}

export function monthCursorFromDayKey(dayKey: string): MonthCursor {
  const { year, month } = parseDayKey(dayKey);
  return { year, month };
}

/** Build a Sunday-start grid of local day keys (or null for padding cells). */
export function buildMonthGrid(cursor: MonthCursor): Array<string | null> {
  return buildLocalMonthGrid(cursor);
}

export function buildLocalMonthGrid(cursor: MonthCursor): Array<string | null> {
  const first = new Date(Date.UTC(cursor.year, cursor.month - 1, 1));
  const startWeekday = first.getUTCDay(); // 0 = Sunday
  const dim = daysInMonth(cursor);
  const cells: Array<string | null> = [];
  for (let i = 0; i < startWeekday; i += 1) {
    cells.push(null);
  }
  for (let day = 1; day <= dim; day += 1) {
    cells.push(dayKeyFromParts(cursor.year, cursor.month, day));
  }
  while (cells.length % 7 !== 0) {
    cells.push(null);
  }
  return cells;
}

export function dayNumberFromKey(dayKey: string): number {
  return Number(dayKey.slice(-2));
}

export function weekdayShortLabel(dayKey: string): string {
  const { year, month, day } = parseDayKey(dayKey);
  const d = new Date(Date.UTC(year, month - 1, day, 12, 0, 0));
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    timeZone: "UTC",
  }).format(d);
}
