/**
 * Schedule editor scaffold — list defer uses this thin form; US-040C will converge.
 */
export function ScheduleEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div data-testid="schedule-editor-scaffold">
      <label htmlFor="defer-schedule">New scheduled time (UTC)</label>
      <input
        id="defer-schedule"
        data-testid="defer-schedule"
        type="datetime-local"
        step={1}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <p className="sup-meta">
        Stored as <span className="mono">new_scheduled_at_utc</span>. Must be
        strictly in the future. Defer does not auto-update the editorial
        calendar.
      </p>
    </div>
  );
}

/** Convert datetime-local value (interpreted as UTC wall clock) to ISO Z. */
export function datetimeLocalToUtcIso(value: string): string | null {
  if (!value) {
    return null;
  }
  const match =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
  if (!match) {
    return null;
  }
  const sec = match[6] || "00";
  return `${match[1]}-${match[2]}-${match[3]}T${match[4]}:${match[5]}:${sec}Z`;
}

export function utcIsoToDatetimeLocal(iso: string | null): string {
  if (!iso) {
    return "";
  }
  const parsed = Date.parse(iso);
  if (Number.isNaN(parsed)) {
    return "";
  }
  const d = new Date(parsed);
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())}` +
    `T${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}:${pad(d.getUTCSeconds())}`
  );
}
