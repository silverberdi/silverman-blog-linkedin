import { useEffect, useId, useRef, useState } from "react";
import type { ApiError } from "../api/errors";
import type { MutationResult } from "../api/types";
import {
  confirmRealMutation,
  newIdempotencyKey,
} from "./ConfirmationFlow";
import { ItemDetail } from "./ItemDetail";
import { ScheduleEditorPanel } from "./ScheduleEditor";
import { formatLocalDisplay, utcDayKey } from "../models/dateHelpers";
import {
  publicationStateLabel,
  type ScheduleItem,
  type SupervisionItem,
} from "../models/supervision";
import { useSupervisionStore } from "../models/store";

type PanelMode = "view" | "edit" | "cancel";

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Focused event modal (US-040H) — primary surface for view/edit/reschedule/cancel.
 */
export function EventModal() {
  const {
    snapshot,
    scheduleSnapshot,
    eventModalItemId,
    closeEventModal,
    client,
    refreshAll,
    pushToast,
    dryRunDefault,
    setUnsavedScheduleDraft,
    setUnsavedEditDraft,
    unsavedScheduleDraft,
    unsavedEditDraft,
    openScheduleEditor,
    closeScheduleEditor,
    scheduleEditorTarget,
    canMutate,
    eventModalEntry,
  } = useSupervisionStore();

  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  const [panel, setPanel] = useState<PanelMode>("view");
  const [draftContent, setDraftContent] = useState("");
  const [editReason, setEditReason] = useState("");
  const [editDryRun, setEditDryRun] = useState(dryRunDefault);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelDryRun, setCancelDryRun] = useState(dryRunDefault);
  const [submitting, setSubmitting] = useState(false);
  const [modalError, setModalError] = useState("");
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false);

  const scheduleItem: ScheduleItem | null =
    scheduleSnapshot?.items.find(
      (item) => item.itemId === eventModalItemId,
    ) ?? null;

  const supervisionItem: SupervisionItem | null =
    scheduleItem?.channel === "linkedin" &&
    scheduleItem.campaignId &&
    scheduleItem.variantId
      ? (snapshot?.items.find(
          (item) =>
            item.campaignId === scheduleItem.campaignId &&
            item.variantId === scheduleItem.variantId,
        ) ?? null)
      : null;

  const scheduleOpen =
    Boolean(scheduleEditorTarget) &&
    scheduleEditorTarget?.itemId === eventModalItemId;

  useEffect(() => {
    if (!eventModalItemId) {
      setPanel("view");
      setModalError("");
      setDiagnosticsOpen(false);
      setUnsavedEditDraft(false);
    }
  }, [eventModalItemId, setUnsavedEditDraft]);

  useEffect(() => {
    if (!eventModalItemId || !dialogRef.current) {
      return;
    }
    closeBtnRef.current?.focus();
  }, [eventModalItemId, panel, scheduleOpen]);

  function hasUnsavedDraft(): boolean {
    return unsavedEditDraft || unsavedScheduleDraft;
  }

  function requestClose() {
    if (hasUnsavedDraft()) {
      const ok = window.confirm(
        "You have unsaved edits or a schedule draft. Close and discard them?",
      );
      if (!ok) {
        return;
      }
    }
    setPanel("view");
    setUnsavedEditDraft(false);
    setUnsavedScheduleDraft(false);
    closeScheduleEditor();
    closeEventModal();
  }

  useEffect(() => {
    if (!eventModalItemId) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        requestClose();
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
    // requestClose closes over latest draft flags
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    eventModalItemId,
    panel,
    scheduleOpen,
    unsavedEditDraft,
    unsavedScheduleDraft,
  ]);

  if (!eventModalItemId || !scheduleItem) {
    return null;
  }

  const item = scheduleItem;

  function requireMutate(action: string): boolean {
    if (canMutate) {
      return true;
    }
    const text = `Cannot ${action}: authentication with mutation permission is required. This is not a successful schedule or content change.`;
    setModalError(text);
    pushToast({ kind: "error", text });
    return false;
  }

  function openEdit() {
    if (!supervisionItem || !requireMutate("edit")) {
      return;
    }
    setDraftContent(supervisionItem.draftContent ?? "");
    setEditReason("");
    setEditDryRun(dryRunDefault);
    setUnsavedEditDraft(false);
    setUnsavedScheduleDraft(false);
    setModalError("");
    closeScheduleEditor();
    setPanel("edit");
  }

  function openSchedule() {
    setPanel("view");
    setModalError("");
    openScheduleEditor({
      channel: item.channel,
      itemId: item.itemId,
      title: item.title,
      scheduledAtUtc: item.scheduledAtUtc,
      scheduleEditable: item.scheduleEditable,
      scheduleEditBlockReason: item.scheduleEditBlockReason,
      campaignId: item.campaignId,
      variantId: item.variantId,
      calendarItemId: item.calendarItemId,
      entry: eventModalEntry,
    });
  }

  function openCancel() {
    if (!supervisionItem || !requireMutate("cancel")) {
      return;
    }
    setCancelReason("");
    setCancelDryRun(dryRunDefault);
    setUnsavedEditDraft(false);
    setUnsavedScheduleDraft(false);
    setModalError("");
    closeScheduleEditor();
    setPanel("cancel");
  }

  function handleMutationResult(action: string, result: MutationResult): void {
    const dry = Boolean(result.dry_run);
    const mode = dry
      ? "validated (dry-run, no mutation)"
      : "persisted (real write)";
    pushToast({
      kind: dry ? "info" : "ok",
      text: `${action} ${mode} for ${result.campaign_id} / ${result.variant}. publish_state=${result.publish_state ?? "—"}. Pending, cancelled, and flow_a_complete are not LinkedIn API published.`,
    });
    if (!dry) {
      setUnsavedEditDraft(false);
      setUnsavedScheduleDraft(false);
      void refreshAll({ preserveActionBanner: true });
      setPanel("view");
      closeScheduleEditor();
      closeEventModal();
    }
  }

  async function submitEdit() {
    if (!supervisionItem || !requireMutate("edit")) {
      return;
    }
    if (!editDryRun && !confirmRealMutation("edit")) {
      return;
    }
    setSubmitting(true);
    setModalError("");
    try {
      const result = await client.correctVariant({
        campaign_id: supervisionItem.campaignId,
        variant: supervisionItem.variantId,
        draft_content: draftContent,
        dry_run: editDryRun,
        reason: editReason.trim() || null,
        idempotency_key: editDryRun ? null : newIdempotencyKey(),
      });
      handleMutationResult("Edit", result);
    } catch (err) {
      const apiErr = err as ApiError;
      const text = apiErr?.message || String(err);
      setModalError(text);
      pushToast({ kind: "error", text });
    } finally {
      setSubmitting(false);
    }
  }

  async function submitCancel() {
    if (!supervisionItem || !requireMutate("cancel")) {
      return;
    }
    if (!cancelDryRun && !confirmRealMutation("cancel")) {
      return;
    }
    setSubmitting(true);
    setModalError("");
    try {
      const result = await client.cancelVariant({
        campaign_id: supervisionItem.campaignId,
        variant: supervisionItem.variantId,
        dry_run: cancelDryRun,
        reason: cancelReason.trim() || null,
        idempotency_key: cancelDryRun ? null : newIdempotencyKey(),
      });
      handleMutationResult("Cancel", result);
    } catch (err) {
      const apiErr = err as ApiError;
      const text = apiErr?.message || String(err);
      setModalError(text);
      pushToast({ kind: "error", text });
    } finally {
      setSubmitting(false);
    }
  }

  const label = publicationStateLabel(
    item.publicationState,
    item.linkedinApiPublished,
  );
  const canEdit = Boolean(
    supervisionItem && item.actions.includes("edit"),
  );
  const canCancel = Boolean(
    supervisionItem && item.actions.includes("cancel"),
  );

  return (
    <div
      className="event-modal-root"
      data-testid="event-modal-root"
    >
      <button
        type="button"
        className="event-modal-backdrop"
        data-testid="event-modal-backdrop"
        aria-label="Close event modal"
        onClick={requestClose}
      />
      <div
        ref={dialogRef}
        className="event-modal"
        data-testid="event-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="event-modal-header drawer-header">
          <div>
            <p className="eyebrow">Event</p>
            <h2 id={titleId}>
              {item.title || item.variantId || item.itemId}
            </h2>
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            className="secondary"
            data-testid="event-modal-close"
            onClick={requestClose}
          >
            Close
          </button>
        </div>

        <div className="event-modal-body">
          {modalError && (
            <div className="banner error" data-testid="event-modal-error">
              {modalError}
            </div>
          )}

          {scheduleOpen ? (
            <ScheduleEditorPanel embedded onEmbeddedClose={() => undefined} />
          ) : panel === "edit" && supervisionItem ? (
            <div data-testid="edit-panel">
              <p className="meta">Edit draft content</p>
              <ItemDetail
                item={supervisionItem}
                draftContent={draftContent}
                onDraftChange={(value) => {
                  setDraftContent(value);
                  setUnsavedEditDraft(true);
                }}
              />
              <label htmlFor="edit-reason">Reason (optional)</label>
              <input
                id="edit-reason"
                type="text"
                value={editReason}
                onChange={(e) => {
                  setEditReason(e.target.value);
                  setUnsavedEditDraft(true);
                }}
                placeholder="e.g. operator_choice or criteria_failure"
              />
              <div className="check-row">
                <input
                  type="checkbox"
                  id="edit-dry-run"
                  data-testid="edit-dry-run"
                  checked={editDryRun}
                  onChange={(e) => setEditDryRun(e.target.checked)}
                />
                <label htmlFor="edit-dry-run">
                  Dry-run (default on — validates without mutating)
                </label>
              </div>
              <div className="panel-actions event-modal-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    if (unsavedEditDraft) {
                      const ok = window.confirm(
                        "You have unsaved edits. Discard and return to view?",
                      );
                      if (!ok) {
                        return;
                      }
                    }
                    setUnsavedEditDraft(false);
                    setPanel("view");
                  }}
                >
                  Back
                </button>
                <button
                  type="button"
                  data-testid="edit-submit"
                  disabled={submitting || !canMutate}
                  onClick={() => void submitEdit()}
                >
                  {editDryRun ? "Validate edit (dry-run)" : "Commit edit"}
                </button>
              </div>
            </div>
          ) : panel === "cancel" && supervisionItem ? (
            <div
              data-testid="cancel-panel"
              role="group"
              aria-labelledby="cancel-panel-title"
            >
              <h3 id="cancel-panel-title">Cancel pending variant</h3>
              <p className="meta">
                Campaign {supervisionItem.campaignId} · variant{" "}
                {supervisionItem.variantId}
              </p>
              <p className="sup-meta">
                Cancel sets worker{" "}
                <span className="mono">publish_state=cancelled</span> and
                excludes the variant from strategy-driven auto-queue. It does not
                call LinkedIn and is not LinkedIn API published. Real cancel
                requires confirmation.
              </p>
              <label htmlFor="cancel-reason">Reason (optional)</label>
              <input
                id="cancel-reason"
                type="text"
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="e.g. operator_choice"
              />
              <div className="check-row">
                <input
                  type="checkbox"
                  id="cancel-dry-run"
                  data-testid="cancel-dry-run"
                  checked={cancelDryRun}
                  onChange={(e) => setCancelDryRun(e.target.checked)}
                />
                <label htmlFor="cancel-dry-run">
                  Dry-run (default on — validates without mutating)
                </label>
              </div>
              <div className="panel-actions panel-actions-destructive event-modal-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => setPanel("view")}
                >
                  Back
                </button>
                <button
                  type="button"
                  data-testid="cancel-submit"
                  disabled={submitting || !canMutate}
                  onClick={() => void submitCancel()}
                >
                  {cancelDryRun
                    ? "Validate cancel (dry-run)"
                    : "Commit cancel"}
                </button>
              </div>
            </div>
          ) : (
            <>
              <p className="item-detail-status" data-testid="event-modal-status">
                <span
                  className="status-pill"
                  style={{ backgroundColor: item.statusColor }}
                >
                  {label}
                </span>{" "}
                <span className="mono">{item.channel}</span>
                {item.audience ? (
                  <>
                    {" · "}
                    <span className="mono">{item.audience}</span>
                  </>
                ) : null}
                {" · "}
                <span
                  className="mono"
                  data-testid="event-modal-schedule-local"
                >
                  {formatLocalDisplay(item.scheduledAtUtc)}
                </span>
              </p>
              {(item.blocked ||
                item.critical ||
                item.publicationState === "blocked" ||
                item.publicationState === "deferred" ||
                item.publicationState === "failed") && (
                <p className="meta" data-testid="event-modal-risk">
                  {item.critical || item.publicationState === "failed"
                    ? "Risk: failed / critical"
                    : item.blocked || item.publicationState === "blocked"
                      ? "Blocked"
                      : "Deferred"}
                </p>
              )}
              {supervisionItem?.draftContent && (
                <details
                  className="diagnostics-details"
                  data-testid="event-draft-preview"
                >
                  <summary>Draft preview</summary>
                  <pre className="draft-preview">
                    {supervisionItem.draftContent}
                  </pre>
                </details>
              )}
              <div
                className="panel-actions event-modal-actions"
                data-testid="event-modal-actions"
              >
                {canEdit && (
                  <button
                    type="button"
                    className="row-action"
                    data-testid="row-edit"
                    disabled={!canMutate}
                    onClick={openEdit}
                  >
                    Edit draft
                  </button>
                )}
                <button
                  type="button"
                  className="row-action"
                  data-testid="row-defer"
                  data-action="open-schedule"
                  onClick={openSchedule}
                >
                  {item.scheduleEditable
                    ? "Reschedule / defer"
                    : "View schedule"}
                </button>
                {canCancel && (
                  <button
                    type="button"
                    className="row-action"
                    data-testid="row-cancel"
                    disabled={!canMutate}
                    onClick={openCancel}
                  >
                    Cancel
                  </button>
                )}
              </div>
              <details
                className="diagnostics-details"
                data-testid="event-modal-diagnostics"
                open={diagnosticsOpen}
                onToggle={(e) =>
                  setDiagnosticsOpen((e.target as HTMLDetailsElement).open)
                }
              >
                <summary>Diagnostics / technical details</summary>
                <dl className="diagnostics-dl">
                  <div>
                    <dt>item_id</dt>
                    <dd className="mono">{item.itemId}</dd>
                  </div>
                  {item.campaignId && (
                    <div>
                      <dt>campaign_id</dt>
                      <dd className="mono">{item.campaignId}</dd>
                    </div>
                  )}
                  {item.variantId && (
                    <div>
                      <dt>variant_id</dt>
                      <dd className="mono">{item.variantId}</dd>
                    </div>
                  )}
                  {item.scheduledAtUtc && (
                    <div>
                      <dt>scheduled_at_utc</dt>
                      <dd className="mono" data-testid="event-modal-scheduled-at-utc">
                        {item.scheduledAtUtc}
                      </dd>
                    </div>
                  )}
                  {utcDayKey(item.scheduledAtUtc) && (
                    <div>
                      <dt>UTC day</dt>
                      <dd className="mono" data-testid="event-modal-utc-day">
                        {utcDayKey(item.scheduledAtUtc)}
                      </dd>
                    </div>
                  )}
                  <div>
                    <dt>publication_state</dt>
                    <dd className="mono">{item.publicationState}</dd>
                  </div>
                  <div>
                    <dt>linkedinApiPublished</dt>
                    <dd className="mono">
                      {String(item.linkedinApiPublished)}
                    </dd>
                  </div>
                  {item.calendarItemId && (
                    <div>
                      <dt>calendar_item_id</dt>
                      <dd className="mono">{item.calendarItemId}</dd>
                    </div>
                  )}
                  {supervisionItem?.publishState && (
                    <div>
                      <dt>source publish_state</dt>
                      <dd className="mono">{supervisionItem.publishState}</dd>
                    </div>
                  )}
                </dl>
              </details>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
