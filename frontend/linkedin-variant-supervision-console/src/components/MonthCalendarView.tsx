import { useEffect, useMemo } from "react";
import {
  buildMonthGrid,
  dayNumberFromKey,
  formatLocalDisplay,
  formatUtcDisplay,
  monthLabel,
  shiftMonth,
  todayUtcDayKey,
  utcDayKey,
} from "../models/dateHelpers";
import type { ScheduleItem } from "../models/supervision";
import { useSupervisionStore } from "../models/store";

function ScheduleChip({ item }: { item: ScheduleItem }) {
  return (
    <article
      className="calendar-chip"
      data-testid="calendar-chip"
      data-item-id={item.itemId}
      data-channel={item.channel}
      style={{ borderLeftColor: item.statusColor }}
    >
      <div className="calendar-chip-title">{item.title || item.itemId}</div>
      <div className="calendar-chip-meta">
        <span className="mono">{item.channel}</span>
        {" · "}
        <span
          className="status-pill"
          style={{ backgroundColor: item.statusColor }}
        >
          {item.publicationState}
        </span>
        {item.linkedinApiPublished ? (
          <span className="meta"> · LinkedIn API published</span>
        ) : (
          <span className="meta">
            {" "}
            · not LinkedIn API published
          </span>
        )}
      </div>
      <div className="calendar-chip-meta">
        {item.campaignId && (
          <>
            campaign <span className="mono">{item.campaignId}</span>
          </>
        )}
        {item.variantId && (
          <>
            {" · "}variant <span className="mono">{item.variantId}</span>
          </>
        )}
        {item.audience && <> · {item.audience}</>}
      </div>
      <div className="calendar-chip-meta">
        UTC <span className="mono">{formatUtcDisplay(item.scheduledAtUtc)}</span>
        {" · local "}
        <span className="mono">{formatLocalDisplay(item.scheduledAtUtc)}</span>
      </div>
    </article>
  );
}

/**
 * First-class Month calendar visibility (US-040B). Visibility only — no schedule writes.
 */
export function MonthCalendarView() {
  const {
    scheduleSnapshot,
    filteredScheduleItems,
    monthCursor,
    setMonthCursor,
    selectedDayKey,
    setSelectedDayKey,
    selectedItemId,
    setSelectedItemId,
    loadScheduleVisibility,
    loading,
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

  const selectedItems = selectedDayKey
    ? (itemsByDay.get(selectedDayKey) ?? [])
    : [];

  function goMonth(delta: number) {
    const next = shiftMonth(monthCursor, delta);
    setMonthCursor(next);
    setSelectedDayKey(null);
  }

  return (
    <section data-testid="month-calendar-view" className="month-calendar">
      <div className="calendar-nav">
        <button
          type="button"
          className="secondary"
          data-testid="calendar-prev"
          onClick={() => goMonth(-1)}
          disabled={loading}
        >
          Previous
        </button>
        <h2 className="section-title calendar-month-label" data-testid="calendar-month-label">
          {monthLabel(monthCursor)} (UTC)
        </h2>
        <button
          type="button"
          className="secondary"
          data-testid="calendar-next"
          onClick={() => goMonth(1)}
          disabled={loading}
        >
          Next
        </button>
      </div>

      <p className="sup-meta" data-testid="calendar-tz-note">
        Day placement uses the <strong>UTC calendar date</strong> of{" "}
        <span className="mono">scheduled_at_utc</span>. Each chip also shows
        operator-local time. Month calendar is visibility-only (no schedule
        writes — US-040C).
      </p>

      {scheduleSnapshot?.issues && scheduleSnapshot.issues.length > 0 && (
        <div className="banner warn" data-testid="calendar-issues">
          Partial schedule data:{" "}
          {scheduleSnapshot.issues
            .map((issue) => `${issue.source}:${issue.reason}`)
            .join("; ")}
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
            <button
              type="button"
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
              aria-pressed={isSelected}
              onClick={() => {
                setSelectedDayKey(dayKey);
                if (dayItems[0]) {
                  setSelectedItemId(dayItems[0].itemId);
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
                      className={
                        item.itemId === selectedItemId ? "is-selected-item" : ""
                      }
                      style={{ borderLeftColor: item.statusColor }}
                    >
                      <span className="mono">{item.channel}</span>{" "}
                      {item.title || item.variantId || item.campaignId}
                    </li>
                  ))}
                  {dayItems.length > 3 && (
                    <li className="calendar-more">+{dayItems.length - 3} more</li>
                  )}
                </ul>
              )}
            </button>
          );
        })}
      </div>

      <div
        className="calendar-agenda"
        data-testid="calendar-agenda"
        aria-live="polite"
      >
        <h3 className="section-title">
          {selectedDayKey
            ? `Agenda · ${selectedDayKey} (UTC day)`
            : "Select a day for agenda detail"}
        </h3>
        {!selectedDayKey && (
          <p className="meta">
            On mobile, selecting a day expands this agenda list instead of
            requiring horizontal table scrolling.
          </p>
        )}
        {selectedDayKey && selectedItems.length === 0 && (
          <p className="meta" data-testid="agenda-empty">
            Empty day — no schedule items after filters.
          </p>
        )}
        {selectedItems.length > 0 && (
          <div className="agenda-list" data-testid="agenda-list">
            {selectedItems.map((item) => (
              <ScheduleChip key={item.itemId} item={item} />
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
