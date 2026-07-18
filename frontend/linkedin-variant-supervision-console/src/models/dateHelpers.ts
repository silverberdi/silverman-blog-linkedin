/**
 * UTC day-bucketing and calendar helpers for Week + Month (US-040B / US-040G).
 *
 * Day placement (Week columns and Month cells) uses the UTC calendar date of
 * scheduled_at_utc. Chips display local wall time. Operator-local day bucketing
 * is deferred to US-040I — known debt: an item near local midnight may appear on
 * a different UTC day than the operator's local calendar day.
 */

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

/** Week cursor: Sunday-start UTC week identified by week-start day key. */
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

export function addUtcDays(dayKey: string, delta: number): string {
  const { year, month, day } = parseDayKey(dayKey);
  const ms = Date.UTC(year, month - 1, day + delta);
  const d = new Date(ms);
  return dayKeyFromParts(
    d.getUTCFullYear(),
    d.getUTCMonth() + 1,
    d.getUTCDate(),
  );
}

/** Sunday (UTC) that starts the week containing dayKey. */
export function sundayUtcWeekStart(dayKey: string): string {
  const { year, month, day } = parseDayKey(dayKey);
  const d = new Date(Date.UTC(year, month - 1, day));
  const weekday = d.getUTCDay(); // 0 = Sunday
  return addUtcDays(dayKey, -weekday);
}

export function currentUtcMonth(): MonthCursor {
  const now = new Date();
  return { year: now.getUTCFullYear(), month: now.getUTCMonth() + 1 };
}

export function currentUtcWeek(): WeekCursor {
  return { weekStartKey: sundayUtcWeekStart(todayUtcDayKey()) };
}

export function shiftMonth(cursor: MonthCursor, delta: number): MonthCursor {
  const index = cursor.year * 12 + (cursor.month - 1) + delta;
  const year = Math.floor(index / 12);
  const month = (index % 12) + 1;
  return { year, month };
}

export function shiftWeek(cursor: WeekCursor, deltaWeeks: number): WeekCursor {
  return {
    weekStartKey: addUtcDays(cursor.weekStartKey, deltaWeeks * 7),
  };
}

export function monthLabel(cursor: MonthCursor): string {
  const d = new Date(Date.UTC(cursor.year, cursor.month - 1, 1));
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}

export function weekLabel(cursor: WeekCursor): string {
  const start = cursor.weekStartKey;
  const end = addUtcDays(start, 6);
  const startParts = parseDayKey(start);
  const endParts = parseDayKey(end);
  const startDate = new Date(
    Date.UTC(startParts.year, startParts.month - 1, startParts.day),
  );
  const endDate = new Date(
    Date.UTC(endParts.year, endParts.month - 1, endParts.day),
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
  return `${startFmt} – ${endFmt} (UTC)`;
}

export function todayUtcDayKey(): string {
  return utcDayKey(new Date().toISOString()) ?? "";
}

/** Seven consecutive UTC day keys starting at weekStartKey (Sunday). */
export function buildWeekDayKeys(weekStartKey: string): string[] {
  return Array.from({ length: 7 }, (_, i) => addUtcDays(weekStartKey, i));
}

/** Unique UTC months covering a Sunday-start week (for schedule-visibility loads). */
export function monthsCoveringWeek(weekStartKey: string): MonthCursor[] {
  const keys = buildWeekDayKeys(weekStartKey);
  const seen = new Set<string>();
  const out: MonthCursor[] = [];
  for (const key of keys) {
    const { year, month } = parseDayKey(key);
    const id = `${year}-${month}`;
    if (!seen.has(id)) {
      seen.add(id);
      out.push({ year, month });
    }
  }
  return out;
}

export function monthCursorFromDayKey(dayKey: string): MonthCursor {
  const { year, month } = parseDayKey(dayKey);
  return { year, month };
}

/** Build a Sunday-start grid of UTC day keys (or null for padding cells). */
export function buildMonthGrid(cursor: MonthCursor): Array<string | null> {
  const first = new Date(Date.UTC(cursor.year, cursor.month - 1, 1));
  const startWeekday = first.getUTCDay(); // 0 = Sunday
  const daysInMonth = new Date(
    Date.UTC(cursor.year, cursor.month, 0),
  ).getUTCDate();
  const cells: Array<string | null> = [];
  for (let i = 0; i < startWeekday; i += 1) {
    cells.push(null);
  }
  for (let day = 1; day <= daysInMonth; day += 1) {
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
  const d = new Date(Date.UTC(year, month - 1, day));
  return new Intl.DateTimeFormat(undefined, {
    weekday: "short",
    timeZone: "UTC",
  }).format(d);
}
