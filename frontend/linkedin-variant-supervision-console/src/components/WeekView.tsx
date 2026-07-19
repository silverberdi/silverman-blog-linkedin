import { useEffect, useMemo } from "react";
import {
  buildLocalWeekDayKeys,
  currentLocalWeek,
  dayNumberFromKey,
  formatLocalTime,
  localDayKey,
  monthsCoveringWeek,
  monthCursorFromDayKey,
  operatorTimezoneCue,
  shiftWeek,
  todayLocalDayKey,
  weekdayShortLabel,
  weekLabel,
} from "../models/dateHelpers";
import {
  densityCueLevel,
  isDensityMember,
} from "../models/localDayDensity";
import {
  publicationStateLabel,
  type ScheduleItem,
} from "../models/supervision";
import { useSupervisionStore } from "../models/store";

function chipClass(item: ScheduleItem): string {
  const parts = ["week-event-chip"];
  if (item.critical || item.publicationState === "failed") {
    parts.push("week-event-chip-failed");
  } else if (item.blocked || item.publicationState === "blocked") {
    parts.push("week-event-chip-blocked");
  } else if (item.publicationState === "cancelled") {
    parts.push("week-event-chip-cancelled");
  }
  return parts.join(" ");
}

/**
 * Week day-column calendar (US-040G design D1) — not an hour time-grid.
 * Operator-local day placement with local time + timezone cue on chips (US-040I).
 */
export function WeekView() {
  const {
    scheduleSnapshot,
    filteredScheduleItems,
    filters,
    resetFilters,
    weekCursor,
    setWeekCursor,
    setMonthCursor,
    setSelectedDayKey,
    openEventModal,
    loadScheduleForMonths,
    loading,
  } = useSupervisionStore();

  useEffect(() => {
    const months = monthsCoveringWeek(weekCursor.weekStartKey);
    setMonthCursor(monthCursorFromDayKey(weekCursor.weekStartKey));
    void loadScheduleForMonths(months, { preserveActionBanner: true });
  }, [
    weekCursor.weekStartKey,
    loadScheduleForMonths,
    setMonthCursor,
  ]);

  const todayKey = todayLocalDayKey();
  const tzCue = operatorTimezoneCue();
  const dayKeys = useMemo(
    () => buildLocalWeekDayKeys(weekCursor.weekStartKey),
    [weekCursor.weekStartKey],
  );

  const itemsByDay = useMemo(() => {
    const map = new Map<string, ScheduleItem[]>();
    for (const key of dayKeys) {
      map.set(key, []);
    }
    for (const item of filteredScheduleItems) {
      const key = localDayKey(item.scheduledAtUtc);
      if (!key || !map.has(key)) {
        continue;
      }
      map.get(key)!.push(item);
    }
    for (const list of map.values()) {
      list.sort((a, b) =>
        (a.scheduledAtUtc ?? "").localeCompare(b.scheduledAtUtc ?? ""),
      );
    }
    return map;
  }, [filteredScheduleItems, dayKeys]);

  /** Density cues use unfiltered snapshot for honesty (US-040K). */
  const densityByDay = useMemo(() => {
    const map = new Map<string, number>();
    for (const key of dayKeys) {
      map.set(key, 0);
    }
    const allItems = scheduleSnapshot?.items ?? filteredScheduleItems;
    for (const item of allItems) {
      if (!isDensityMember(item)) {
        continue;
      }
      const key = localDayKey(item.scheduledAtUtc);
      if (!key || !map.has(key)) {
        continue;
      }
      map.set(key, (map.get(key) ?? 0) + 1);
    }
    return map;
  }, [scheduleSnapshot?.items, filteredScheduleItems, dayKeys]);

  const weekItemCount = useMemo(() => {
    let n = 0;
    for (const key of dayKeys) {
      n += itemsByDay.get(key)?.length ?? 0;
    }
    return n;
  }, [dayKeys, itemsByDay]);

  const filtersActive =
    filters.channel !== "all" ||
    filters.campaignQuery.trim() !== "" ||
    filters.publicationStates.length > 0 ||
    filters.blockedOnly ||
    filters.dueSoonOnly;

  function goWeek(delta: number) {
    setWeekCursor(shiftWeek(weekCursor, delta));
    setSelectedDayKey(null);
  }

  function goThisWeek() {
    const today = todayLocalDayKey();
    setWeekCursor(currentLocalWeek());
    setSelectedDayKey(today);
  }

  return (
    <section data-testid="week-view" className="week-view">
      <div className="section-heading calendar-heading">
        <div>
          <p className="eyebrow">This week&apos;s plan</p>
          <h2 className="section-title">Week</h2>
        </div>
        <span className="queue-count">{weekItemCount} items</span>
      </div>

      <div className="calendar-nav week-nav" data-testid="week-nav">
        <button
          type="button"
          className="secondary"
          data-testid="week-prev"
          onClick={() => goWeek(-1)}
          disabled={loading}
        >
          Previous week
        </button>
        <h3 className="calendar-month-label" data-testid="week-label">
          {weekLabel(weekCursor)}
        </h3>
        <button
          type="button"
          className="secondary"
          data-testid="week-next"
          onClick={() => goWeek(1)}
          disabled={loading}
        >
          Next week
        </button>
        <button
          type="button"
          className="week-today-btn"
          data-testid="week-today"
          onClick={goThisWeek}
          disabled={loading}
        >
          Today / This week
        </button>
      </div>

      <p className="sup-meta compact-help" data-testid="week-tz-note">
        Local calendar days
        {tzCue ? ` (${tzCue})` : ""}; chips show local time.
      </p>

      {scheduleSnapshot?.issues && scheduleSnapshot.issues.length > 0 && (
        <div className="banner warn" data-testid="week-issues">
          Partial schedule data:{" "}
          {scheduleSnapshot.issues
            .map((issue) => `${issue.source}:${issue.reason}`)
            .join("; ")}
        </div>
      )}

      {weekItemCount === 0 && (
        <div
          className="calendar-empty-state calendar-empty-cue"
          data-testid="week-empty-state"
          role="status"
        >
          <p className="empty-state-title">No publications this week</p>
          <p className="meta">
            {filtersActive
              ? "Active filters hid every item in this week."
              : "Nothing is scheduled in this week after the current read."}
          </p>
          {filtersActive && (
            <button
              type="button"
              className="secondary"
              data-testid="week-clear-filters"
              onClick={resetFilters}
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      <div
        className="week-columns"
        data-testid="week-columns"
        role="grid"
        aria-label={`Week ${weekLabel(weekCursor)}`}
      >
        {dayKeys.map((dayKey) => {
          const dayItems = itemsByDay.get(dayKey) ?? [];
          const isToday = dayKey === todayKey;
          const densityCount = densityByDay.get(dayKey) ?? 0;
          const cue = densityCueLevel(densityCount);
          return (
            <div
              key={dayKey}
              className={[
                "week-day-column",
                isToday ? "is-today" : "",
                cue === "full" ? "day-density-full" : "",
                cue === "over" ? "day-density-over" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              data-testid={`week-day-${dayKey}`}
              data-day={dayKey}
              data-density={cue}
            >
              <header className="week-day-header">
                <span className="week-day-name">
                  {weekdayShortLabel(dayKey)}
                </span>
                <span className="week-day-num">
                  {dayNumberFromKey(dayKey)}
                  {isToday ? " · today" : ""}
                </span>
                {cue === "full" && (
                  <span
                    className="day-density-cue day-density-full"
                    data-testid="day-density-full"
                  >
                    Full (2)
                  </span>
                )}
                {cue === "over" && (
                  <span
                    className="day-density-cue day-density-over"
                    data-testid="day-density-over"
                  >
                    Over capacity ({densityCount})
                  </span>
                )}
              </header>
              <div className="week-day-chips">
                {dayItems.length === 0 ? (
                  <span className="calendar-empty">No items</span>
                ) : (
                  dayItems.map((item) => {
                    const label = publicationStateLabel(
                      item.publicationState,
                      item.linkedinApiPublished,
                    );
                    return (
                      <button
                        key={item.itemId}
                        type="button"
                        className={chipClass(item)}
                        data-testid="week-event-chip"
                        data-item-id={item.itemId}
                        data-channel={item.channel}
                        data-publication-state={item.publicationState}
                        style={{ borderLeftColor: item.statusColor }}
                        onClick={() => openEventModal(item.itemId, "week")}
                      >
                        <span className="week-chip-title title-cell">
                          {item.title ||
                            item.variantId ||
                            item.campaignId ||
                            item.itemId}
                        </span>
                        <span className="week-chip-meta">
                          <span className="mono">{item.channel}</span>
                          {" · "}
                          <span className="mono">
                            {formatLocalTime(item.scheduledAtUtc)}
                          </span>
                        </span>
                        <span
                          className="status-pill status-pill-compact"
                          style={{ backgroundColor: item.statusColor }}
                        >
                          {label}
                        </span>
                      </button>
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
