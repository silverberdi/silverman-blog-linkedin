import { FormEvent, useCallback, useEffect, useId, useRef, useState } from "react";
import type { ApiError } from "../api/errors";
import type {
  GapOperatorSettingsDocument,
  GapOperatorSettingsResponse,
  GapScanMode,
  WeeklyRunLocalDay,
} from "../api/types";
import { useSupervisionStore } from "../models/store";

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const WEEKDAYS: WeeklyRunLocalDay[] = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
];

const SCAN_MODES: GapScanMode[] = ["next_week"];

function settingsFromResponse(
  response: GapOperatorSettingsResponse,
): GapOperatorSettingsDocument {
  return {
    operator_timezone: response.operator_timezone,
    gap_trigger_enabled: response.gap_trigger_enabled,
    gap_scan_mode: response.gap_scan_mode,
    weekly_run_local_day: response.weekly_run_local_day,
    weekly_run_local_time: response.weekly_run_local_time,
    min_lead_days: response.min_lead_days,
    gap_posts_threshold: response.gap_posts_threshold,
    max_drafts_per_weekly_run: response.max_drafts_per_weekly_run,
    density_max_per_local_day: response.density_max_per_local_day,
  };
}

function formatApiError(err: unknown): string {
  const apiErr = err as ApiError | undefined;
  if (apiErr?.kind === "validation") {
    return apiErr.message || "Validation failed.";
  }
  if (apiErr?.kind === "unauthorized" || apiErr?.kind === "auth_missing") {
    return "Sign in required to load or save gap settings.";
  }
  if (apiErr?.kind === "forbidden" || apiErr?.kind === "mutation_denied") {
    return "This session cannot mutate gap settings.";
  }
  if (apiErr?.message) {
    return apiErr.message;
  }
  return "Unable to load or save gap settings.";
}

/**
 * Flow B gap operator settings modal (US-076) — Authority Manager surface.
 * Save does not enable LinkedIn API publish; auto-trigger stays fail-closed when disabled.
 */
export function GapSettingsModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const { canMutate, sessionState, signIn, client } = useSupervisionStore();

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [source, setSource] = useState<string | null>(null);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [rowVersion, setRowVersion] = useState<number | null>(null);
  const [form, setForm] = useState<GapOperatorSettingsDocument | null>(null);

  const loadSettings = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.getGapOperatorSettings();
      setForm(settingsFromResponse(response));
      setSource(response.source);
      setUpdatedAt(response.updated_at_utc);
      setRowVersion(response.row_version);
    } catch (err) {
      setForm(null);
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    if (!open) {
      return;
    }
    void loadSettings();
  }, [open, loadSettings]);

  useEffect(() => {
    if (!open || !dialogRef.current) {
      return;
    }
    closeBtnRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) {
        return;
      }
      const focusables = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      ).filter((el) => el.offsetParent !== null || el === document.activeElement);
      if (focusables.length === 0) {
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey) {
        if (document.activeElement === first) {
          event.preventDefault();
          last.focus();
        }
      } else if (document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [open, onClose]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!form || !canMutate) {
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const response = await client.putGapOperatorSettings({
        ...form,
        expected_row_version: rowVersion ?? undefined,
      });
      setForm(settingsFromResponse(response));
      setSource(response.source);
      setUpdatedAt(response.updated_at_utc);
      setRowVersion(response.row_version);
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return null;
  }

  const needsReauth =
    sessionState === "anonymous" ||
    sessionState === "expired" ||
    sessionState === "forbidden";

  return (
    <div className="filters-modal-root" data-testid="gap-settings-modal-root">
      <button
        type="button"
        className="filters-modal-backdrop"
        data-testid="gap-settings-modal-backdrop"
        aria-label="Close gap settings modal"
        onClick={onClose}
      />
      <div
        ref={dialogRef}
        className="filters-modal gap-settings-modal"
        data-testid="gap-settings-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="filters-modal-header drawer-header">
          <div>
            <p className="eyebrow">Flow B</p>
            <h2 id={titleId}>Gap operator settings</h2>
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            className="secondary"
            data-testid="gap-settings-modal-close"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <div className="filters-modal-body">
          <p className="note" data-testid="gap-settings-publish-warning">
            Saving these settings does not publish to LinkedIn and does not turn
            on the LinkedIn API publish guard. Auto-trigger stays fail-closed
            while gap trigger is disabled; detect/trigger are separate
            capabilities.
          </p>

          {needsReauth && (
            <p className="note" data-testid="gap-settings-reauth-note">
              Sign in required to load or save settings.{" "}
              <button
                type="button"
                data-testid="gap-settings-sign-in"
                onClick={() => void signIn()}
              >
                Sign in
              </button>
            </p>
          )}

          {error && (
            <p className="form-error" role="alert" data-testid="gap-settings-error">
              {error}
            </p>
          )}

          {loading && (
            <p className="note" data-testid="gap-settings-loading">
              Loading settings…
            </p>
          )}

          {form && !loading && (
            <form
              className="gap-settings-form"
              data-testid="gap-settings-form"
              onSubmit={(e) => void onSubmit(e)}
            >
              <p className="meta-line" data-testid="gap-settings-meta">
                Source: {source ?? "—"}
                {updatedAt ? ` · Updated ${updatedAt}` : " · Using defaults until saved"}
              </p>

              <label className="field">
                <span>Operator timezone (IANA)</span>
                <input
                  type="text"
                  data-testid="gap-settings-timezone"
                  value={form.operator_timezone}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({ ...form, operator_timezone: e.target.value })
                  }
                  required
                />
              </label>

              <label className="check-row">
                <input
                  type="checkbox"
                  data-testid="gap-settings-trigger-enabled"
                  checked={form.gap_trigger_enabled}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({ ...form, gap_trigger_enabled: e.target.checked })
                  }
                />
                <span>Enable gap auto-trigger (fail-closed when off)</span>
              </label>

              <label className="field">
                <span>Gap scan mode</span>
                <select
                  data-testid="gap-settings-scan-mode"
                  value={form.gap_scan_mode}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      gap_scan_mode: e.target.value as GapScanMode,
                    })
                  }
                >
                  {SCAN_MODES.map((mode) => (
                    <option key={mode} value={mode}>
                      {mode}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Weekly run local day</span>
                <select
                  data-testid="gap-settings-run-day"
                  value={form.weekly_run_local_day}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      weekly_run_local_day: e.target.value as WeeklyRunLocalDay,
                    })
                  }
                >
                  {WEEKDAYS.map((day) => (
                    <option key={day} value={day}>
                      {day}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Weekly run local time (HH:MM)</span>
                <input
                  type="text"
                  data-testid="gap-settings-run-time"
                  value={form.weekly_run_local_time}
                  disabled={!canMutate || saving}
                  pattern="([01]\d|2[0-3]):[0-5]\d"
                  title="24-hour HH:MM"
                  onChange={(e) =>
                    setForm({ ...form, weekly_run_local_time: e.target.value })
                  }
                  required
                />
              </label>

              <label className="field">
                <span>Min lead days</span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  data-testid="gap-settings-min-lead-days"
                  value={form.min_lead_days}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      min_lead_days: Number(e.target.value),
                    })
                  }
                  required
                />
              </label>

              <label className="field">
                <span>Gap posts threshold</span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  data-testid="gap-settings-gap-threshold"
                  value={form.gap_posts_threshold}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      gap_posts_threshold: Number(e.target.value),
                    })
                  }
                  required
                />
              </label>

              <label className="field">
                <span>Max drafts per weekly run</span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  data-testid="gap-settings-max-drafts"
                  value={form.max_drafts_per_weekly_run}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      max_drafts_per_weekly_run: Number(e.target.value),
                    })
                  }
                  required
                />
              </label>

              <label className="field">
                <span>Density max per local day</span>
                <input
                  type="number"
                  min={0}
                  step={1}
                  data-testid="gap-settings-density-max"
                  value={form.density_max_per_local_day}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      density_max_per_local_day: Number(e.target.value),
                    })
                  }
                  required
                />
              </label>

              <div className="drawer-actions">
                <button
                  type="submit"
                  data-testid="gap-settings-save"
                  disabled={!canMutate || saving}
                >
                  {saving ? "Saving…" : "Save settings"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
