import { useEffect, useId, useRef, useState } from "react";
import type { ApiError } from "../api/errors";
import { explainErrorCodes } from "../api/errors";
import type { MutationResult } from "../api/types";
import {
  confirmRealMutation,
  newIdempotencyKey,
} from "./ConfirmationFlow";
import { ItemDetail } from "./ItemDetail";
import {
  CONSOLE_ACTOR,
  CONSOLE_SOURCE,
  ScheduleEditorFields,
  ScheduleEditorPanel,
  datetimeLocalToUtcIso,
  isStrictlyAfterNow,
  utcIsoToDatetimeLocal,
} from "./ScheduleEditor";
import { formatLocalDisplay, localDayKey, utcDayKey } from "../models/dateHelpers";
import {
  LOCAL_DAY_FULL_MESSAGE,
  excludeForScheduleItem,
  isLocalDayFull,
  operatorTimezone,
  othersOnLocalDay,
} from "../models/localDayDensity";
import {
  publicationStateHelper,
  publicationStateLabel,
  type ScheduleItem,
  type SupervisionItem,
} from "../models/supervision";
import { buildLinkedInActionMatrix } from "../models/actionAvailability";
import {
  PREVIEW_CHECKBOX_LABEL,
  dryRunModeBanner,
  mutationOutcomeToast,
} from "../models/mutationMode";
import { useSupervisionStore } from "../models/store";

type PanelMode = "view" | "edit" | "cancel" | "reopen";

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function cancellationPhaseLabel(phase: string | null): string {
  if (phase === "pre_queue") {
    return "Cancelled before queue (never queued for LinkedIn)";
  }
  if (phase === "post_queue") {
    return "Cancelled after queue (LinkedIn API was not called)";
  }
  if (phase === "recovery") {
    return "Cancelled from a failed publish recovery path";
  }
  return "Cancelled by operator";
}

/**
 * Focused event modal (US-040H / US-040J) — view/edit/reschedule/cancel/reopen.
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
  const [reopenSchedule, setReopenSchedule] = useState("");
  const [reopenReason, setReopenReason] = useState("");
  const [reopenDryRun, setReopenDryRun] = useState(dryRunDefault);
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
  const isCancelled = item.publicationState === "cancelled";
  const canReopen =
    isCancelled &&
    item.channel === "linkedin" &&
    item.reopenEligible &&
    Boolean(item.campaignId && item.variantId);

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
    const campaignId = item.campaignId;
    const variantId = item.variantId;
    if (!campaignId || !variantId || !requireMutate("cancel")) {
      return;
    }
    const isLive =
      item.publicationState === "published" ||
      item.linkedinApiPublished === true;
    if (isLive) {
      const text =
        "Cancel is not available — this variant is already Live on LinkedIn. Reload if status looks stale.";
      setModalError(text);
      pushToast({ kind: "error", text });
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

  function openReopen() {
    if (!canReopen || !requireMutate("reopen")) {
      return;
    }
    const confirmed = window.confirm(
      "Reopen this cancelled LinkedIn variant and choose a new schedule? It returns to editable pending (not queued, not LinkedIn API published). Cancel remains irreversible except through this reopen path.",
    );
    if (!confirmed) {
      return;
    }
    setReopenSchedule(utcIsoToDatetimeLocal(item.scheduledAtUtc));
    setReopenReason("");
    setReopenDryRun(dryRunDefault);
    setUnsavedEditDraft(false);
    setUnsavedScheduleDraft(false);
    setModalError("");
    closeScheduleEditor();
    setPanel("reopen");
  }

  function handleMutationResult(action: string, result: MutationResult): void {
    const dry = Boolean(result.dry_run);
    const identity = `${result.campaign_id} / ${result.variant}`;
    pushToast({
      kind: dry ? "info" : "ok",
      text: mutationOutcomeToast(action, dry, identity),
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
    const campaignId = item.campaignId;
    const variantId = item.variantId;
    if (!campaignId || !variantId || !requireMutate("cancel")) {
      return;
    }
    if (!cancelDryRun && !confirmRealMutation("cancel (withdraw — will not send)")) {
      return;
    }
    setSubmitting(true);
    setModalError("");
    try {
      const result = await client.cancelVariant({
        campaign_id: campaignId,
        variant: variantId,
        dry_run: cancelDryRun,
        reason: cancelReason.trim() || null,
        idempotency_key: cancelDryRun ? null : newIdempotencyKey(),
      });
      handleMutationResult("Cancel", result);
    } catch (err) {
      const apiErr = err as ApiError;
      const text =
        apiErr?.codes?.length
          ? explainErrorCodes(apiErr.codes)
          : apiErr?.message || String(err);
      setModalError(text);
      pushToast({ kind: "error", text });
    } finally {
      setSubmitting(false);
    }
  }

  async function submitReopen() {
    if (!canReopen || !requireMutate("reopen")) {
      return;
    }
    if (!item.campaignId || !item.variantId) {
      return;
    }
    const iso = datetimeLocalToUtcIso(reopenSchedule);
    if (!iso) {
      const text = "Provide a valid new scheduled time in your local timezone.";
      setModalError(text);
      pushToast({ kind: "error", text });
      return;
    }
    if (!isStrictlyAfterNow(iso)) {
      const text =
        "New schedule must be after now in your local time before reopen can proceed.";
      setModalError(text);
      pushToast({ kind: "error", text });
      return;
    }

    const targetDay = localDayKey(iso);
    const densityItems = scheduleSnapshot?.items ?? [];
    if (targetDay) {
      const exclude = excludeForScheduleItem(item);
      const others = othersOnLocalDay(densityItems, targetDay, exclude);
      if (isLocalDayFull(others)) {
        setModalError(LOCAL_DAY_FULL_MESSAGE);
        pushToast({ kind: "error", text: LOCAL_DAY_FULL_MESSAGE });
        return;
      }
    }

    if (!reopenDryRun && !confirmRealMutation("reopen")) {
      return;
    }
    setSubmitting(true);
    setModalError("");
    try {
      const result = await client.reopenVariant({
        campaign_id: item.campaignId,
        variant: item.variantId,
        new_scheduled_at_utc: iso,
        dry_run: reopenDryRun,
        reason: reopenReason.trim() || null,
        idempotency_key: reopenDryRun ? null : newIdempotencyKey(),
        actor: CONSOLE_ACTOR,
        source: CONSOLE_SOURCE,
        operator_timezone: operatorTimezone() || null,
      });
      if (result.status !== "completed") {
        const text = `Reopen failed: ${explainErrorCodes(result.errors || [])}`;
        setModalError(text);
        pushToast({ kind: "error", text });
        return;
      }
      handleMutationResult("Reopen", result);
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
  const statusHelper = publicationStateHelper(item.publicationState, {
    linkedinApiPublished: item.linkedinApiPublished,
    channel: item.channel,
  });
  const isLiveOnLinkedIn =
    item.publicationState === "published" ||
    item.linkedinApiPublished === true;
  const isQueuedWaiting = item.publicationState === "queued";
  const isPendingLike =
    item.publicationState === "pending" ||
    item.publicationState === "deferred" ||
    item.publicationState === "blocked";
  const hasCancelIdentity = Boolean(item.campaignId && item.variantId);
  const canEdit = Boolean(
    supervisionItem && item.actions.includes("edit"),
  );
  /** Pending cancel via supervision join; queued cancel via schedule identity (US-085). */
  const canCancelPending = Boolean(
    supervisionItem &&
      item.actions.includes("cancel") &&
      isPendingLike &&
      !isLiveOnLinkedIn,
  );
  const canCancelQueued = Boolean(
    isQueuedWaiting && hasCancelIdentity && !isLiveOnLinkedIn,
  );
  const canCancel = canCancelPending || canCancelQueued;
  const cancelPanelTitle = isQueuedWaiting
    ? "Cancel waiting-to-send variant"
    : "Cancel scheduled variant";
  const cancelCampaignId = item.campaignId;
  const cancelVariantId = item.variantId;
  const actionMatrix =
    item.channel === "linkedin"
      ? buildLinkedInActionMatrix({
          item,
          hasSupervisionJoin: Boolean(supervisionItem),
          canMutate,
        })
      : [];

  function renderStatusBlock(testId: string) {
    return (
      <>
        <p className="item-detail-status" data-testid={testId}>
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
        {statusHelper ? (
          <p className="sup-meta" data-testid="event-modal-status-helper">
            {statusHelper}
          </p>
        ) : null}
      </>
    );
  }

  function renderActionMatrix() {
    if (actionMatrix.length === 0) {
      return null;
    }
    return (
      <section
        className="action-matrix"
        data-testid="action-availability-matrix"
        aria-labelledby="action-matrix-title"
      >
        <h3 id="action-matrix-title">What you can do now</h3>
        <ul className="action-matrix-list">
          {actionMatrix.map((row) => (
            <li
              key={row.id}
              className={
                row.available
                  ? "action-matrix-row available"
                  : "action-matrix-row unavailable"
              }
              data-testid={`action-matrix-${row.id}`}
              data-available={row.available ? "true" : "false"}
            >
              <span className="action-matrix-label">{row.label}</span>
              <span
                className={
                  row.available
                    ? "action-matrix-badge available"
                    : "action-matrix-badge unavailable"
                }
              >
                {row.available ? "Available" : "Unavailable"}
              </span>
              <p className="action-matrix-reason">{row.reason}</p>
            </li>
          ))}
        </ul>
      </section>
    );
  }

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
                <label htmlFor="edit-dry-run">{PREVIEW_CHECKBOX_LABEL}</label>
              </div>
              <p className="meta" data-testid="edit-mode-banner">
                {dryRunModeBanner(editDryRun)}
              </p>
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
                  {editDryRun ? "Preview edit (no change)" : "Save edit"}
                </button>
              </div>
            </div>
          ) : panel === "cancel" && cancelCampaignId && cancelVariantId ? (
            <div
              data-testid="cancel-panel"
              role="group"
              aria-labelledby="cancel-panel-title"
            >
              <h3 id="cancel-panel-title">{cancelPanelTitle}</h3>
              <p className="meta">
                Campaign {cancelCampaignId} · variant {cancelVariantId}
              </p>
              <p
                className="sup-meta"
                data-testid="cancel-control-framing"
              >
                {isQueuedWaiting
                  ? "Withdraw this Waiting-to-send variant so it will not send. Cancel is not postpone (postpone keeps Waiting to send with a new time). It does not call LinkedIn and is not an unpublish of a live post."
                  : "Withdraw this Scheduled variant so it will not send. Cancel is not postpone (postpone keeps Scheduled with a new time). It does not call LinkedIn and is not an unpublish of a live post."}{" "}
                Sets worker <span className="mono">publish_state=cancelled</span>{" "}
                and excludes strategy-driven auto-queue. Restoration requires
                the approved reopen &amp; reschedule path. Real cancel requires
                confirmation.
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
                <label htmlFor="cancel-dry-run">{PREVIEW_CHECKBOX_LABEL}</label>
              </div>
              <p className="meta" data-testid="cancel-mode-banner">
                {dryRunModeBanner(cancelDryRun)}
              </p>
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
                    ? "Preview cancel (no change)"
                    : "Save cancel"}
                </button>
              </div>
            </div>
          ) : panel === "reopen" ? (
            <div
              data-testid="reopen-panel"
              role="group"
              aria-labelledby="reopen-panel-title"
            >
              <h3 id="reopen-panel-title">Reopen &amp; reschedule</h3>
              <p className="meta">
                Campaign {item.campaignId} · variant {item.variantId}
              </p>
              <p className="sup-meta">
                Reopen restores editable{" "}
                <span className="mono">pending</span> with a new future schedule.
                It does not auto-queue and does not call the LinkedIn API. Dry-run
                validates without mutating.
              </p>
              <ScheduleEditorFields
                value={reopenSchedule}
                onChange={(value) => {
                  setReopenSchedule(value);
                  setUnsavedScheduleDraft(true);
                }}
                idPrefix="reopen"
              />
              <label htmlFor="reopen-reason">Reason (optional)</label>
              <input
                id="reopen-reason"
                type="text"
                value={reopenReason}
                onChange={(e) => {
                  setReopenReason(e.target.value);
                  setUnsavedScheduleDraft(true);
                }}
                placeholder="e.g. operator_choice"
              />
              <div className="check-row">
                <input
                  type="checkbox"
                  id="reopen-dry-run"
                  data-testid="reopen-dry-run"
                  checked={reopenDryRun}
                  onChange={(e) => setReopenDryRun(e.target.checked)}
                />
                <label htmlFor="reopen-dry-run">{PREVIEW_CHECKBOX_LABEL}</label>
              </div>
              <p className="meta" data-testid="reopen-mode-banner">
                {dryRunModeBanner(reopenDryRun)}
              </p>
              <div className="panel-actions event-modal-actions">
                <button
                  type="button"
                  className="secondary"
                  onClick={() => {
                    if (unsavedScheduleDraft) {
                      const ok = window.confirm(
                        "You have an unsaved schedule draft. Discard and return?",
                      );
                      if (!ok) {
                        return;
                      }
                    }
                    setUnsavedScheduleDraft(false);
                    setPanel("view");
                  }}
                >
                  Back
                </button>
                <button
                  type="button"
                  data-testid="reopen-submit"
                  disabled={submitting || !canMutate}
                  onClick={() => void submitReopen()}
                >
                  {reopenDryRun
                    ? "Preview reopen (no change)"
                    : "Save reopen"}
                </button>
              </div>
            </div>
          ) : isCancelled ? (
            <div data-testid="cancelled-event-view">
              {renderStatusBlock("event-modal-status")}

              <section
                className="cancelled-what"
                data-testid="cancelled-what"
              >
                <h3>What is this?</h3>
                <p>
                  A cancelled planned LinkedIn publication
                  {item.campaignId ? (
                    <>
                      {" "}
                      for campaign <span className="mono">{item.campaignId}</span>
                    </>
                  ) : null}
                  {item.variantId ? (
                    <>
                      {" "}
                      / variant <span className="mono">{item.variantId}</span>
                    </>
                  ) : null}
                  {item.audience ? (
                    <>
                      {" "}
                      ({item.audience})
                    </>
                  ) : null}
                  . Cancelled is not LinkedIn API published.
                </p>
              </section>

              <section
                className="cancelled-why"
                data-testid="cancelled-why"
              >
                <h3>Why is it cancelled?</h3>
                <p>
                  {item.cancellationReason
                    ? item.cancellationReason
                    : "Cancelled by operator"}
                </p>
                <p className="meta">
                  {cancellationPhaseLabel(item.cancellationPhase)}
                  {item.cancelledAtUtc
                    ? ` · ${formatLocalDisplay(item.cancelledAtUtc)}`
                    : ""}
                </p>
              </section>

              {renderActionMatrix()}

              <div
                className="panel-actions event-modal-actions"
                data-testid="event-modal-actions"
              >
                {canReopen && (
                  <button
                    type="button"
                    className="row-action"
                    data-testid="row-reopen"
                    disabled={!canMutate}
                    onClick={openReopen}
                  >
                    Reopen &amp; reschedule
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
                  {item.cancelledAtUtc && (
                    <div>
                      <dt>cancelled_at_utc</dt>
                      <dd className="mono">{item.cancelledAtUtc}</dd>
                    </div>
                  )}
                  {item.cancellationPhase && (
                    <div>
                      <dt>cancellation_phase</dt>
                      <dd className="mono">{item.cancellationPhase}</dd>
                    </div>
                  )}
                  <div>
                    <dt>reopen_eligible</dt>
                    <dd className="mono">{String(item.reopenEligible)}</dd>
                  </div>
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
                </dl>
              </details>
            </div>
          ) : (
            <>
              {renderStatusBlock("event-modal-status")}
              {(item.blocked ||
                item.critical ||
                item.publicationState === "blocked" ||
                item.publicationState === "deferred" ||
                item.publicationState === "failed") && (
                <p className="meta" data-testid="event-modal-risk">
                  {item.critical || item.publicationState === "failed"
                    ? "Risk: failed / critical — not live on LinkedIn"
                    : item.blocked || item.publicationState === "blocked"
                      ? "Blocked — not live on LinkedIn"
                      : "Deferred — not live on LinkedIn"}
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
              {renderActionMatrix()}
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
                    ? "Postpone / reschedule"
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
                  {item.sourceState && (
                    <div>
                      <dt>source_state</dt>
                      <dd className="mono">{item.sourceState}</dd>
                    </div>
                  )}
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
