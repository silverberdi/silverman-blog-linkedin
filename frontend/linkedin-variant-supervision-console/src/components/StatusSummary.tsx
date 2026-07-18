import type { OperationalCounts } from "../models/supervision";
import { useSupervisionStore } from "../models/store";

const COUNT_DEFS: Array<{
  key: keyof OperationalCounts;
  label: string;
  hint: string;
  tone?: "actionable" | "success" | "neutral";
}> = [
  {
    key: "upcoming",
    label: "Upcoming",
    hint: "Future scheduled items (not cancelled)",
    tone: "neutral",
  },
  {
    key: "pending",
    label: "Pending",
    hint: "Pending review — not LinkedIn API published",
    tone: "neutral",
  },
  {
    key: "dueSoon",
    label: "Due soon",
    hint: "Within next 48 hours",
    tone: "neutral",
  },
  {
    key: "deferred",
    label: "Deferred",
    hint: "Operator-deferred / not auto-queue eligible",
    tone: "neutral",
  },
  {
    key: "blocked",
    label: "Blocked",
    hint: "Actionable blocked items",
    tone: "actionable",
  },
  {
    key: "failed",
    label: "Failed",
    hint: "Failed items + sibling integration failures",
    tone: "actionable",
  },
  {
    key: "recentlyPublished",
    label: "Recently published",
    hint: "API evidence in last 7 days — not flow_a_complete or blog handoff",
    tone: "success",
  },
];

/**
 * At-a-glance operational count strip (US-040E) — filter-scope aware.
 */
export function StatusSummary() {
  const {
    snapshot,
    scheduleSnapshot,
    operationalCounts,
    hiddenCriticalCount,
    showHiddenCritical,
    loading,
  } = useSupervisionStore();

  const hasData = snapshot != null || scheduleSnapshot != null;

  if (!hasData) {
    return (
      <section
        className="status-summary status-summary-empty"
        data-testid="status-summary"
        aria-label="Operational status"
      >
        <p className="meta">
          {loading
            ? "Loading supervision data…"
            : "Supply your worker API key when prompted. It stays in memory only for this page session and is never embedded in this page or browser storage. Refresh to load the operational console counts."}
        </p>
      </section>
    );
  }

  const observed =
    snapshot?.observedAtUtc || scheduleSnapshot?.observedAtUtc || "(unknown)";

  return (
    <section
      className="status-summary"
      data-testid="status-summary"
      aria-label="At-a-glance operational counts"
    >
      <div className="count-strip" data-testid="count-strip" role="list">
        {COUNT_DEFS.map((def) => {
          const value = operationalCounts[def.key];
          return (
            <div
              key={def.key}
              className={[
                "count-chip",
                def.tone === "actionable" ? "count-chip-actionable" : "",
                def.tone === "success" ? "count-chip-success" : "",
                value === 0 ? "count-chip-zero" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              role="listitem"
              title={def.hint}
              data-testid={`count-${def.key}`}
              data-count={value}
            >
              <span className="count-chip-value">{value}</span>
              <span className="count-chip-label">{def.label}</span>
            </div>
          );
        })}
      </div>
      <p className="meta status-summary-meta">
        Observed {observed}
        {snapshot ? ` · pending window ${snapshot.status}` : ""}
        {scheduleSnapshot
          ? ` · schedule ${scheduleSnapshot.year}-${String(scheduleSnapshot.month).padStart(2, "0")} ${scheduleSnapshot.status}`
          : ""}
        {" · "}
        Counts follow current filters. Zero is empty, not a system failure.
        Pending / queued / cancelled / flow_a_complete / blog handoff are not
        LinkedIn API published.
      </p>
      {hiddenCriticalCount > 0 && (
        <div
          className="banner warn"
          data-testid="status-hidden-critical"
          role="status"
        >
          {hiddenCriticalCount} critical failure
          {hiddenCriticalCount === 1 ? "" : "s"} hidden by filters.{" "}
          <button
            type="button"
            className="secondary"
            data-testid="status-show-critical-btn"
            onClick={showHiddenCritical}
          >
            Show critical / reset filters
          </button>
        </div>
      )}
    </section>
  );
}
