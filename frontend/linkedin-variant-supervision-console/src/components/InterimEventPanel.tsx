import { useEffect, useState } from "react";
import type { ApiError } from "../api/errors";
import type { MutationResult } from "../api/types";
import {
  confirmRealMutation,
  newIdempotencyKey,
} from "./ConfirmationFlow";
import { ItemDetail } from "./ItemDetail";
import { formatLocalDisplay, utcDayKey } from "../models/dateHelpers";
import {
  publicationStateLabel,
  type ScheduleItem,
  type SupervisionItem,
} from "../models/supervision";
import { useSupervisionStore } from "../models/store";

type PanelMode = "edit" | "cancel" | null;

/**
 * Interim event detail / ScheduleEditor entry (US-040G design D3).
 * Preserves edit / defer / cancel until US-040H event modal — not claimed as H.
 */
export function InterimEventPanel() {
  const {
    snapshot,
    scheduleSnapshot,
    interimDetailItemId,
    closeInterimDetail,
    client,
    refreshAll,
    setActionBanner,
    dryRunDefault,
    setUnsavedScheduleDraft,
    openScheduleEditor,
    canMutate,
    interimEntry,
  } = useSupervisionStore();

  const [panel, setPanel] = useState<PanelMode>(null);
  const [draftContent, setDraftContent] = useState("");
  const [editReason, setEditReason] = useState("");
  const [editDryRun, setEditDryRun] = useState(dryRunDefault);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelDryRun, setCancelDryRun] = useState(dryRunDefault);
  const [submitting, setSubmitting] = useState(false);
  const [editDirty, setEditDirty] = useState(false);

  const scheduleItem: ScheduleItem | null =
    scheduleSnapshot?.items.find(
      (item) => item.itemId === interimDetailItemId,
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

  useEffect(() => {
    if (!interimDetailItemId) {
      setPanel(null);
      setEditDirty(false);
    }
  }, [interimDetailItemId]);

  useEffect(() => {
    if (!interimDetailItemId) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }
      event.preventDefault();
      requestClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
    // requestClose closes over latest panel/editDirty
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [interimDetailItemId, panel, editDirty]);

  function closePanels() {
    setPanel(null);
    setEditDirty(false);
    setUnsavedScheduleDraft(false);
  }

  function requestClose() {
    if (panel === "edit" && editDirty) {
      const ok = window.confirm(
        "You have unsaved draft edits. Close and discard them?",
      );
      if (!ok) {
        return;
      }
    }
    closePanels();
    closeInterimDetail();
  }

  if (!interimDetailItemId || !scheduleItem) {
    return null;
  }

  const item = scheduleItem;

  function requireMutate(action: string): boolean {
    if (canMutate) {
      return true;
    }
    setActionBanner({
      kind: "error",
      text: `Cannot ${action}: authentication with mutation permission is required. This is not a successful schedule or content change.`,
    });
    return false;
  }

  function openEdit() {
    if (!supervisionItem || !requireMutate("edit")) {
      return;
    }
    setDraftContent(supervisionItem.draftContent ?? "");
    setEditReason("");
    setEditDryRun(dryRunDefault);
    setEditDirty(false);
    setUnsavedScheduleDraft(false);
    setPanel("edit");
  }

  function openSchedule() {
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
      entry: interimEntry,
    });
  }

  function openCancel() {
    if (!supervisionItem || !requireMutate("cancel")) {
      return;
    }
    setCancelReason("");
    setCancelDryRun(dryRunDefault);
    setUnsavedScheduleDraft(false);
    setPanel("cancel");
  }

  function handleMutationResult(action: string, result: MutationResult): void {
    const mode = result.dry_run
      ? "validated (dry-run, no mutation)"
      : "persisted (real write)";
    setActionBanner({
      kind: "ok",
      text: `${action} ${mode} for ${result.campaign_id} / ${result.variant}. publish_state=${result.publish_state ?? "—"}. Pending, cancelled, and flow_a_complete are not LinkedIn API published.`,
    });
    if (!result.dry_run) {
      setUnsavedScheduleDraft(false);
      void refreshAll({ preserveActionBanner: true });
      closePanels();
      closeInterimDetail();
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
      setActionBanner({
        kind: "error",
        text: apiErr?.message || String(err),
      });
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
      setActionBanner({
        kind: "error",
        text: apiErr?.message || String(err),
      });
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

  if (panel === "edit" && supervisionItem) {
    return (
      <aside className="detail-drawer panel-inspect" data-testid="edit-panel">
        <div className="drawer-header">
          <div>
            <p className="eyebrow">Draft review</p>
            <h2>Inspect and edit</h2>
          </div>
          <button type="button" className="secondary" onClick={requestClose}>
            Close
          </button>
        </div>
        <p className="meta interim-h-hint" data-testid="interim-h-hint">
          Interim event actions until a focused event modal ships (US-040H). This
          drawer is not that modal product.
        </p>
        <ItemDetail
          item={supervisionItem}
          draftContent={draftContent}
          onDraftChange={(value) => {
            setDraftContent(value);
            setEditDirty(true);
          }}
        />
        <label htmlFor="edit-reason">Reason (optional)</label>
        <input
          id="edit-reason"
          type="text"
          value={editReason}
          onChange={(e) => {
            setEditReason(e.target.value);
            setEditDirty(true);
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
        <div className="panel-actions">
          <button
            type="button"
            data-testid="edit-submit"
            disabled={submitting || !canMutate}
            onClick={() => void submitEdit()}
          >
            Submit edit
          </button>
        </div>
      </aside>
    );
  }

  if (panel === "cancel" && supervisionItem) {
    return (
      <aside
        className="detail-drawer panel-destructive"
        data-testid="cancel-panel"
        role="dialog"
        aria-labelledby="cancel-panel-title"
      >
        <div className="drawer-header">
          <div>
            <p className="eyebrow">Destructive action</p>
            <h2 id="cancel-panel-title">Cancel pending variant</h2>
          </div>
          <button type="button" className="secondary" onClick={requestClose}>
            Close
          </button>
        </div>
        <p className="meta">
          Campaign {supervisionItem.campaignId} · variant{" "}
          {supervisionItem.variantId}
        </p>
        <p className="sup-meta">
          Cancel sets worker <span className="mono">publish_state=cancelled</span>{" "}
          and excludes the variant from strategy-driven auto-queue. It does not
          call LinkedIn and is not LinkedIn API published. Real cancel requires
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
          <label htmlFor="cancel-dry-run">
            Dry-run (default on — validates without mutating)
          </label>
        </div>
        <div className="panel-actions panel-actions-destructive">
          <button
            type="button"
            data-testid="cancel-submit"
            disabled={submitting || !canMutate}
            onClick={() => void submitCancel()}
          >
            Submit cancel
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside
      className="detail-drawer panel-inspect"
      data-testid="interim-event-panel"
      role="dialog"
      aria-labelledby="interim-event-title"
    >
      <div className="drawer-header">
        <div>
          <p className="eyebrow">Event</p>
          <h2 id="interim-event-title">
            {item.title || item.variantId || item.itemId}
          </h2>
        </div>
        <button
          type="button"
          className="secondary"
          data-testid="interim-close"
          onClick={requestClose}
        >
          Close
        </button>
      </div>
      <p className="meta interim-h-hint" data-testid="interim-h-hint">
        Interim event actions until a focused event modal ships (US-040H). This
        panel is not that modal product.
      </p>
      <p className="item-detail-status">
        <span
          className="status-pill"
          style={{ backgroundColor: item.statusColor }}
        >
          {label}
        </span>{" "}
        <span className="mono">{item.channel}</span>
        {" · "}
        <span className="mono">
          {formatLocalDisplay(item.scheduledAtUtc)}
        </span>
      </p>
      <p className="meta">
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
        {utcDayKey(item.scheduledAtUtc) && (
          <>
            {" · "}UTC day{" "}
            <span className="mono">
              {utcDayKey(item.scheduledAtUtc)}
            </span>
          </>
        )}
      </p>
      {supervisionItem?.draftContent && (
        <details className="diagnostics-details" data-testid="interim-draft-preview">
          <summary>Draft preview</summary>
          <pre className="draft-preview">{supervisionItem.draftContent}</pre>
        </details>
      )}
      <div className="panel-actions" data-testid="interim-actions">
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
    </aside>
  );
}
