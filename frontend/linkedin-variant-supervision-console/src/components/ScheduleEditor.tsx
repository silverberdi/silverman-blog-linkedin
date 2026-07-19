/**
 * Shared schedule editor — Week, Month, and interim agenda entry points
 * (US-040C / US-040G / US-040I). LinkedIn uses POST /defer-linkedin-variant; blog uses
 * POST /editorial-calendar/update-item-schedule. Browser never writes mounts.
 *
 * Picker digits are operator-local wall time; conversion to *_utc happens only
 * at the typed API client boundary (design D3).
 */
import { useEffect, useState } from "react";
import type { ApiError } from "../api/errors";
import { explainErrorCodes } from "../api/errors";
import type {
  CalendarScheduleUpdateResult,
  MutationResult,
} from "../api/types";
import { localDayKey, operatorTimezoneCue } from "../models/dateHelpers";
import {
  LOCAL_DAY_FULL_MESSAGE,
  excludeForScheduleItem,
  isLocalDayFull,
  operatorTimezone,
  othersOnLocalDay,
} from "../models/localDayDensity";
import { confirmRealMutation, newIdempotencyKey } from "./ConfirmationFlow";
import type { ScheduleEditorTarget } from "../models/supervision";
import { useSupervisionStore } from "../models/store";

export const CONSOLE_SOURCE = "linkedin_variant_supervision_console";
export const CONSOLE_ACTOR = "operator";

export type { ScheduleEditorTarget };

/**
 * Convert datetime-local value (operator-local wall clock) to UTC ISO Z
 * for new_scheduled_at_utc / new_due_at_utc wire fields.
 */
export function datetimeLocalToUtcIso(value: string): string | null {
  if (!value) {
    return null;
  }
  const match =
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/.exec(value);
  if (!match) {
    return null;
  }
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const hour = Number(match[4]);
  const minute = Number(match[5]);
  const sec = Number(match[6] || "00");
  const local = new Date(year, month - 1, day, hour, minute, sec);
  if (Number.isNaN(local.getTime())) {
    return null;
  }
  // Reject rollover from invalid calendar digits (e.g. Feb 31).
  if (
    local.getFullYear() !== year ||
    local.getMonth() !== month - 1 ||
    local.getDate() !== day ||
    local.getHours() !== hour ||
    local.getMinutes() !== minute ||
    local.getSeconds() !== sec
  ) {
    return null;
  }
  return local.toISOString().replace(/\.\d{3}Z$/, "Z");
}

/** Map a UTC ISO instant to datetime-local digits in operator-local wall time. */
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
    `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` +
    `T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
  );
}

/** True when the absolute instant is strictly after now. */
export function isStrictlyAfterNow(
  isoUtc: string,
  nowMs: number = Date.now(),
): boolean {
  const ms = Date.parse(isoUtc);
  if (Number.isNaN(ms)) {
    return false;
  }
  return ms > nowMs;
}

function formatRelatedOutcome(outcome: string | null | undefined): string {
  if (outcome === "unchanged_separate_overrides") {
    return "Related LinkedIn variants remained separate overrides (unchanged by this blog calendar write).";
  }
  if (outcome === "changed") {
    return "Related LinkedIn variants were changed.";
  }
  return "Related LinkedIn variants remained separate overrides.";
}

/**
 * Thin datetime field used inside the shared editor panel and list defer form.
 */
export function ScheduleEditorFields({
  value,
  onChange,
  disabled = false,
  idPrefix = "schedule",
}: {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  idPrefix?: string;
}) {
  const inputId = `${idPrefix}-datetime`;
  const tzCue = operatorTimezoneCue();
  return (
    <div data-testid="schedule-editor-fields">
      <label htmlFor={inputId}>
        New scheduled time{tzCue ? ` (${tzCue})` : ""}
      </label>
      <input
        id={inputId}
        data-testid="schedule-datetime"
        type="datetime-local"
        step={1}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      />
      <p className="sup-meta" data-testid="schedule-editor-help">
        Enter the time in your local timezone
        {tzCue ? ` (${tzCue})` : ""}. It must be after now. Schedule edit does
        not call LinkedIn publication API and does not publish blog content.
      </p>
    </div>
  );
}

/** @deprecated Prefer ScheduleEditorFields; kept for list scaffold compatibility. */
export function ScheduleEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <div data-testid="schedule-editor-scaffold">
      <ScheduleEditorFields value={value} onChange={onChange} idPrefix="defer" />
    </div>
  );
}

/**
 * Shared mutation panel — embedded in EventModal (US-040H) or standalone.
 */
export function ScheduleEditorPanel({
  embedded = false,
  onEmbeddedClose,
}: {
  embedded?: boolean;
  onEmbeddedClose?: () => void;
} = {}) {
  const {
    scheduleEditorTarget,
    closeScheduleEditor,
    closeEventModal,
    eventModalItemId,
    client,
    refreshAll,
    pushToast,
    setUnsavedScheduleDraft,
    unsavedScheduleDraft,
    dryRunDefault,
    scheduleSnapshot,
    canMutate,
    sessionState,
  } = useSupervisionStore();

  const target = scheduleEditorTarget;
  const [schedule, setSchedule] = useState("");
  const [reason, setReason] = useState("");
  const [dryRun, setDryRun] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!target) {
      return;
    }
    setSchedule(utcIsoToDatetimeLocal(target.scheduledAtUtc));
    setReason("");
    setDryRun(dryRunDefault);
    setUnsavedScheduleDraft(false);
  }, [target, dryRunDefault, setUnsavedScheduleDraft]);

  useEffect(() => {
    if (!target || embedded) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }
      event.preventDefault();
      if (unsavedScheduleDraft) {
        const ok = window.confirm(
          "You have an unsaved schedule draft. Close and discard it?",
        );
        if (!ok) {
          return;
        }
      }
      setUnsavedScheduleDraft(false);
      closeScheduleEditor();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [
    target,
    embedded,
    unsavedScheduleDraft,
    closeScheduleEditor,
    setUnsavedScheduleDraft,
  ]);

  if (!target) {
    return null;
  }

  // EventModal owns the schedule surface when open for the same item.
  if (
    !embedded &&
    eventModalItemId &&
    target.itemId === eventModalItemId
  ) {
    return null;
  }

  const active = target;
  const readOnly = !active.scheduleEditable;
  const mutationBlocked = !canMutate;

  function onScheduleChange(value: string) {
    setSchedule(value);
    setUnsavedScheduleDraft(true);
  }

  function feedbackError(text: string) {
    pushToast({ kind: "error", text });
  }

  function close() {
    if (unsavedScheduleDraft) {
      const ok = window.confirm(
        "You have an unsaved schedule draft. Close and discard it?",
      );
      if (!ok) {
        return;
      }
    }
    setUnsavedScheduleDraft(false);
    closeScheduleEditor();
    onEmbeddedClose?.();
  }

  async function submit() {
    if (mutationBlocked) {
      feedbackError(
        sessionState === "expired"
          ? "Session expired. Sign in again to commit. Your unsaved schedule draft is still here."
          : "Cannot commit schedule change: authentication with mutation permission is required. This is not a successful schedule update.",
      );
      return;
    }
    if (readOnly) {
      feedbackError(
        active.scheduleEditBlockReason ||
          "This item is read-only for schedule changes (published/historical).",
      );
      return;
    }
    const iso = datetimeLocalToUtcIso(schedule);
    if (!iso) {
      feedbackError("Provide a valid new scheduled time.");
      return;
    }
    if (!isStrictlyAfterNow(iso)) {
      feedbackError(
        "New schedule must be after now in your local time. Moving earlier than the previous schedule is allowed when the new time is still in the future.",
      );
      return;
    }

    const targetDay = localDayKey(iso);
    const densityItems = scheduleSnapshot?.items ?? [];
    if (targetDay) {
      const exclude = excludeForScheduleItem({
        itemId: active.itemId,
        channel: active.channel,
        campaignId: active.campaignId,
        variantId: active.variantId,
        calendarItemId: active.calendarItemId,
      });
      const others = othersOnLocalDay(densityItems, targetDay, exclude);
      if (isLocalDayFull(others)) {
        feedbackError(LOCAL_DAY_FULL_MESSAGE);
        return;
      }
    }

    if (!dryRun && !confirmRealMutation("schedule change")) {
      return;
    }

    setSubmitting(true);
    try {
      if (active.channel === "linkedin") {
        if (!active.campaignId || !active.variantId) {
          feedbackError(
            "LinkedIn schedule edit requires campaign and variant identity.",
          );
          return;
        }
        const previous = active.scheduledAtUtc;
        const result: MutationResult = await client.deferVariant({
          campaign_id: active.campaignId,
          variant: active.variantId,
          new_scheduled_at_utc: iso,
          dry_run: dryRun,
          reason: reason.trim() || null,
          idempotency_key: dryRun ? null : newIdempotencyKey(),
          actor: CONSOLE_ACTOR,
          source: CONSOLE_SOURCE,
          operator_timezone: operatorTimezone() || null,
        });
        if (result.status !== "completed") {
          feedbackError(
            `Schedule change failed: ${explainErrorCodes(result.errors || [])}`,
          );
          return;
        }
        if (dryRun || result.dry_run) {
          pushToast({
            kind: "info",
            text: `Dry-run schedule change validated for ${active.itemId}. Schedule was not persisted.`,
          });
          setUnsavedScheduleDraft(false);
          return;
        }
        await refreshAll({ preserveActionBanner: true });
        pushToast({
          kind: "ok",
          text:
            `Schedule updated for ${active.itemId} (${active.channel}). ` +
            `Previous: ${previous || "(none)"}. New: ${result.scheduled_at_utc || iso}. ` +
            `Affected item is this LinkedIn variant (self-change).`,
        });
        setUnsavedScheduleDraft(false);
        closeScheduleEditor();
        if (embedded) {
          closeEventModal();
        }
        return;
      }

      // Blog / editorial calendar path
      const calendarItemId = active.calendarItemId;
      if (!calendarItemId) {
        feedbackError("Blog schedule edit requires calendar_item_id.");
        return;
      }
      const previous = active.scheduledAtUtc;
      const result: CalendarScheduleUpdateResult =
        await client.updateCalendarItemSchedule({
          item_id: calendarItemId,
          new_due_at_utc: iso,
          dry_run: dryRun,
          reason: reason.trim() || null,
          idempotency_key: dryRun ? null : newIdempotencyKey(),
          actor: CONSOLE_ACTOR,
          source: CONSOLE_SOURCE,
          expected_calendar_fingerprint:
            scheduleSnapshot?.calendarFingerprint ?? null,
          operator_timezone: operatorTimezone() || null,
        });
      if (result.status !== "completed") {
        feedbackError(
          `Schedule change failed: ${explainErrorCodes(result.errors || [])}`,
        );
        return;
      }
      if (dryRun || result.dry_run) {
        pushToast({
          kind: "info",
          text:
            `Dry-run schedule change validated for ${active.itemId}. ` +
            `Previous ${result.previous_due_at_utc || previous || "(none)"} → ` +
            `proposed ${result.new_due_at_utc || iso}. Calendar was not written.`,
        });
        setUnsavedScheduleDraft(false);
        return;
      }
      await refreshAll({ preserveActionBanner: true });
      pushToast({
        kind: "ok",
        text:
          `Schedule updated for ${active.itemId} (${active.channel}). ` +
          `Previous: ${result.previous_due_at_utc || previous || "(none)"}. ` +
          `New: ${result.new_due_at_utc || iso}. ` +
          formatRelatedOutcome(result.related_linkedin_variants_outcome),
      });
      setUnsavedScheduleDraft(false);
      closeScheduleEditor();
      if (embedded) {
        closeEventModal();
      }
    } catch (err) {
      const apiErr = err as ApiError;
      feedbackError(apiErr?.message || String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className={
        embedded
          ? "schedule-drawer schedule-drawer-embedded"
          : "detail-drawer schedule-drawer"
      }
      data-testid="schedule-editor-panel"
      data-entry={active.entry}
      data-channel={active.channel}
      data-editable={active.scheduleEditable ? "true" : "false"}
      data-embedded={embedded ? "true" : "false"}
    >
      <div className="drawer-header">
        <div>
          <p className="eyebrow">Schedule</p>
          <h2>Schedule editor</h2>
        </div>
        <button
          type="button"
          className="secondary"
          data-testid="schedule-close"
          onClick={close}
        >
          Close
        </button>
      </div>
      <p className="meta">{active.title || active.itemId} · {active.channel}</p>
      {mutationBlocked && (
        <div className="banner warn" data-testid="schedule-editor-auth-blocked">
          {sessionState === "expired"
            ? "Session expired. Sign in to resume this draft — fields below are preserved."
            : "Sign in with mutation permission to commit. Draft fields stay visible; this is not a successful schedule change."}{" "}
          Pending, queued, cancelled, and flow_a_complete are not LinkedIn API
          published.
        </div>
      )}
      {readOnly ? (
        <div className="banner warn" data-testid="schedule-editor-readonly">
          Read-only for schedule.{" "}
          {active.scheduleEditBlockReason
            ? `Blocked: ${active.scheduleEditBlockReason}.`
            : "Published or historical items cannot be rescheduled."}{" "}
          This is not LinkedIn API published merely because the item appears here.
        </div>
      ) : (
        <>
          <ScheduleEditorFields
            value={schedule}
            onChange={onScheduleChange}
            idPrefix="shared-schedule"
          />
          <label htmlFor="schedule-reason">Reason (optional)</label>
          <input
            id="schedule-reason"
            data-testid="schedule-reason"
            type="text"
            value={reason}
            onChange={(e) => {
              setReason(e.target.value);
              setUnsavedScheduleDraft(true);
            }}
            placeholder="e.g. operator_choice"
          />
          <div className="check-row">
            <input
              type="checkbox"
              id="schedule-dry-run"
              data-testid="schedule-dry-run"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
            />
            <label htmlFor="schedule-dry-run">
              Dry-run (default on — validates without mutating)
            </label>
          </div>
        </>
      )}
      <div className="panel-actions">
        {!readOnly && (
          <button
            type="button"
            data-testid="schedule-submit"
            disabled={submitting || mutationBlocked}
            onClick={() => void submit()}
          >
            {dryRun ? "Validate schedule (dry-run)" : "Commit schedule change"}
          </button>
        )}
      </div>
    </div>
  );
}
