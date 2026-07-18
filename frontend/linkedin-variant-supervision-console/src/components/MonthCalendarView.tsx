import { useEffect, useMemo } from "react";
import {
  buildMonthGrid,
  currentUtcMonth,
  dayNumberFromKey,
  monthLabel,
  shiftMonth,
  sundayUtcWeekStart,
  todayUtcDayKey,
  utcDayKey,
} from "../models/dateHelpers";
import {
  publicationStateLabel,
  type ScheduleItem,
} from "../models/supervision";
import { useSupervisionStore } from "../models/store";

function compactBadgeClass(item: ScheduleItem): string {
  if (item.critical || item.publicationState === "failed") {
    return "cal-badge cal-badge-failed";
  }
  if (item.blocked || item.publicationState === "blocked") {
    return "cal-badge cal-badge-blocked";
  }
  return "cal-badge";
}

/**
 * First-class Month calendar density view (US-040B / US-040G secondary).
 * Event chips open interim detail (D3); day click is light focus only — not a
 * list-like multi-item diagnostic dump as the primary action surface.
 */
export function MonthCalendarView() {
  const {
    scheduleSnapshot,
    filteredScheduleItems,
    filters,
    resetFilters,
    monthCursor,
    setMonthCursor,
    setWeekCursor,
    selectedDayKey,
    setSelectedDayKey,
    selectedItemId,
    setSelectedItemId,
    loadScheduleVisibility,
    loading,
    openInterimDetail,
  } = useSupervisionStore();

  useEffect(() => {
    void loadScheduleVisibility({
      year: monthCursor.year,
      month: monthCursor.month,
      preserveActionBanner: true,
    });
  }, [monthCursor.year, monthCursor.month, loadScheduleVisibility]);

  const todayKey = todayUtcDayKey();
  const grid = useMemo(() => buildMonthGrid(monthCursor), [monthCursor]);

  const itemsByDay = useMemo(() => {
    const map = new Map<string, ScheduleItem[]>();
    for (const item of filteredScheduleItems) {
      const key = utcDayKey(item.scheduledAtUtc);
      if (!key) {
        continue;
      }
      const list = map.get(key) ?? [];
      list.push(item);
      map.set(key, list);
    }
    return map;
  }, [filteredScheduleItems]);

  const monthItemCount = filteredScheduleItems.length;
  const filtersActive =
    filters.channel !== "all" ||
    filters.campaignQuery.trim() !== "" ||
    filters.publicationStates.length > 0 ||
    filters.blockedOnly ||
    filters.dueSoonOnly;

  function goMonth(delta: number) {
    const next = shiftMonth(monthCursor, delta);
    setMonthCursor(next);
    setSelectedDayKey(null);
  }

  function goThisMonth() {
    const today = todayUtcDayKey();
    setMonthCursor(currentUtcMonth());
    setSelectedDayKey(today);
    setWeekCursor({ weekStartKey: sundayUtcWeekStart(today) });
  }

  return (
    <section data-testid="month-calendar-view" className="month-calendar">
      <div className="section-heading calendar-heading">
        <div>
          <p className="eyebrow">Publication plan</p>
          <h2 className="section-title">Month</h2>
        </div>
        <span className="queue-count">{monthItemCount} items</span>
      </div>

      <div className="calendar-nav" data-testid="month-nav">
        <button
          type="button"
          className="secondary"
          data-testid="calendar-prev"
          onClick={() => goMonth(-1)}
          disabled={loading}
        >
          Previous
        </button>
        <h3 className="calendar-month-label" data-testid="calendar-month-label">
          {monthLabel(monthCursor)} (UTC)
        </h3>
        <button
          type="button"
          className="secondary"
          data-testid="calendar-next"
          onClick={() => goMonth(1)}
          disabled={loading}
        >
          Next
        </button>
        <button
          type="button"
          className="week-today-btn"
          data-testid="month-today"
          onClick={goThisMonth}
          disabled={loading}
        >
          Today
        </button>
      </div>

      <p className="sup-meta compact-help" data-testid="calendar-tz-note">
        UTC calendar date placement; local time on event detail. Select a chip to
        open interim actions (US-040H modal is a follow-up).
      </p>

      {scheduleSnapshot?.issues && scheduleSnapshot.issues.length > 0 && (
        <div className="banner warn" data-testid="calendar-issues">
          Partial schedule data:{" "}
          {scheduleSnapshot.issues
            .map((issue) => `${issue.source}:${issue.reason}`)
            .join("; ")}
        </div>
      )}

      {monthItemCount === 0 && (
        <div
          className="calendar-empty-state calendar-empty-cue"
          data-testid="month-empty-state"
          role="status"
        >
          <p className="empty-state-title">No publications this month</p>
          <p className="meta">
            {filtersActive
              ? "Active filters hid every item in this month."
              : "Nothing is scheduled in this UTC month after the current read."}
          </p>
          {filtersActive && (
            <button
              type="button"
              className="secondary"
              data-testid="month-clear-filters"
              onClick={resetFilters}
            >
              Clear filters
            </button>
          )}
        </div>
      )}

      <div className="calendar-weekdays" aria-hidden="true">
        {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((d) => (
          <div key={d} className="calendar-weekday">
            {d}
          </div>
        ))}
      </div>

      <div
        className="calendar-grid"
        data-testid="calendar-grid"
        role="grid"
        aria-label={`Month calendar ${monthLabel(monthCursor)}`}
      >
        {grid.map((dayKey, index) => {
          if (!dayKey) {
            return (
              <div
                key={`pad-${index}`}
                className="calendar-cell calendar-cell-pad"
                aria-hidden="true"
              />
            );
          }
          const dayItems = itemsByDay.get(dayKey) ?? [];
          const isToday = dayKey === todayKey;
          const isSelected = dayKey === selectedDayKey;
          const isEmpty = dayItems.length === 0;
          return (
            <div
              key={dayKey}
              className={[
                "calendar-cell",
                isToday ? "is-today" : "",
                isSelected ? "is-selected" : "",
                isEmpty ? "is-empty" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              data-testid={`calendar-day-${dayKey}`}
              data-day={dayKey}
              role="button"
              tabIndex={0}
              aria-pressed={isSelected}
              onClick={() => {
                setSelectedDayKey(dayKey);
                if (dayItems[0]) {
                  setSelectedItemId(dayItems[0].itemId);
                }
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  setSelectedDayKey(dayKey);
                  if (dayItems[0]) {
                    setSelectedItemId(dayItems[0].itemId);
                  }
                }
              }}
            >
              <span className="calendar-day-num">
                {dayNumberFromKey(dayKey)}
                {isToday ? " · today" : ""}
              </span>
              {isEmpty ? (
                <span className="calendar-empty">No items</span>
              ) : (
                <ul className="calendar-day-items">
                  {dayItems.slice(0, 3).map((item) => (
                    <li
                      key={item.itemId}
                      className={[
                        item.itemId === selectedItemId
                          ? "is-selected-item"
                          : "",
                        compactBadgeClass(item),
                      ]
                        .filter(Boolean)
                        .join(" ")}
                      style={{ borderLeftColor: item.statusColor }}
                      data-risk={
                        item.critical || item.publicationState === "failed"
                          ? "failed"
                          : item.blocked ||
                              item.publicationState === "blocked"
                            ? "blocked"
                            : "routine"
                      }
                    >
                      <button
                        type="button"
                        className="calendar-day-item-btn"
                        data-testid="schedule-open-month"
                        data-item-id={item.itemId}
                        title={
                          item.title ||
                          item.variantId ||
                          item.campaignId ||
                          item.itemId
                        }
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedDayKey(dayKey);
                          openInterimDetail(item.itemId, "month");
                        }}
                      >
                        <span
                          className="status-pill status-pill-compact"
                          style={{ backgroundColor: item.statusColor }}
                        >
                          {publicationStateLabel(
                            item.publicationState,
                            item.linkedinApiPublished,
                          )}
                        </span>{" "}
                        <span className="mono">{item.channel}</span>{" "}
                        <span className="title-cell">
                          {item.title || item.variantId || item.campaignId}
                        </span>
                      </button>
                    </li>
                  ))}
                  {dayItems.length > 3 && (
                    <li className="calendar-more">
                      +{dayItems.length - 3} more
                    </li>
                  )}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      {selectedDayKey && (
        <div
          className="month-day-focus"
          data-testid="month-day-focus"
        >
          <p className="meta">
            Focused day {selectedDayKey} (UTC) —{" "}
            {(itemsByDay.get(selectedDayKey) ?? []).length} item
            {(itemsByDay.get(selectedDayKey) ?? []).length === 1
              ? ""
              : "s"}
            . Open a chip for interim actions.
          </p>
          <div
            className="month-day-chip-list"
            data-testid="month-day-chip-list"
          >
            {(itemsByDay.get(selectedDayKey) ?? []).map((item) => (
              <button
                key={item.itemId}
                type="button"
                className="week-event-chip"
                data-testid="month-focus-chip"
                data-item-id={item.itemId}
                style={{ borderLeftColor: item.statusColor }}
                onClick={() => openInterimDetail(item.itemId, "month")}
              >
                <span className="week-chip-title">
                  {item.title ||
                    item.variantId ||
                    item.campaignId ||
                    item.itemId}
                </span>
                <span className="week-chip-meta">
                  <span className="mono">{item.channel}</span>
                  {" · "}
                  {publicationStateLabel(
                    item.publicationState,
                    item.linkedinApiPublished,
                  )}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
