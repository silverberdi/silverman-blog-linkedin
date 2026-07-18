/**
 * UTC day-bucketing and month-grid helpers for Month calendar (US-040B).
 * Calendar day placement uses the UTC calendar date of scheduled_at_utc.
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

export interface MonthCursor {
  year: number;
  month: number; // 1–12
}

export function currentUtcMonth(): MonthCursor {
  const now = new Date();
  return { year: now.getUTCFullYear(), month: now.getUTCMonth() + 1 };
}

export function shiftMonth(cursor: MonthCursor, delta: number): MonthCursor {
  const index = cursor.year * 12 + (cursor.month - 1) + delta;
  const year = Math.floor(index / 12);
  const month = (index % 12) + 1;
  return { year, month };
}

export function monthLabel(cursor: MonthCursor): string {
  const d = new Date(Date.UTC(cursor.year, cursor.month - 1, 1));
  return new Intl.DateTimeFormat(undefined, {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(d);
}

export function todayUtcDayKey(): string {
  return utcDayKey(new Date().toISOString()) ?? "";
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
    const m = String(cursor.month).padStart(2, "0");
    const d = String(day).padStart(2, "0");
    cells.push(`${cursor.year}-${m}-${d}`);
  }
  while (cells.length % 7 !== 0) {
    cells.push(null);
  }
  return cells;
}

export function dayNumberFromKey(dayKey: string): number {
  return Number(dayKey.slice(-2));
}
