import { useEffect, useState, type ReactNode } from "react";
import type { ApiError } from "../api/errors";
import type { MutationResult } from "../api/types";
import {
  confirmRealMutation,
  newIdempotencyKey,
} from "./ConfirmationFlow";
import { ItemDetail } from "./ItemDetail";
import { useSupervisionStore } from "../models/store";
import {
  publicationStateLabel,
  type SupervisionItem,
} from "../models/supervision";

function rowRiskClass(item: SupervisionItem): string {
  if (item.critical || item.publicationState === "failed") {
    return "row-risk-failed";
  }
  if (item.blocked || item.publicationState === "blocked") {
    return "row-risk-blocked";
  }
  if (item.deferredOrIneligible || item.publicationState === "deferred") {
    return "row-risk-deferred";
  }
  return "row-risk-routine";
}

type PanelMode = "edit" | "cancel" | null;

function CalendarCell({ item }: { item: SupervisionItem }) {
  if (
    !item.calendarItemId &&
    !item.calendarTitle &&
    !item.calendarDueAtUtc
  ) {
    return <span className="meta">(no calendar join)</span>;
  }
  return (
    <>
      {item.calendarItemId && (
        <>
          <span className="mono">{item.calendarItemId}</span>
          <br />
        </>
      )}
      {item.calendarTitle && (
        <>
          {item.calendarTitle}
          <br />
        </>
      )}
      {item.calendarDueAtUtc && (
        <>
          <span className="mono">due {item.calendarDueAtUtc}</span>
          <br />
        </>
      )}
      {item.calendarStatus && (
        <span className="mono">{item.calendarStatus}</span>
      )}
    </>
  );
}

function formatSchedule(value: string | null): string {
  if (!value) {
    return "Unscheduled";
  }
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return value;
  }
  const local = new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(parsed));
  // Design D5: local wall clock for triage; Month day placement remains UTC-based.
  return `${local} (local)`;
}

function itemSummary(item: SupervisionItem): string {
  return item.title || item.audience || item.variantId || item.campaignId;
}

function SupervisionMeta({ item }: { item: SupervisionItem }) {
  const parts: ReactNode[] = [];
  if (item.deferredOrIneligible) {
    parts.push(
      <span key="defer-warn" className="sup-meta warn">
        Deferred / not auto-queue eligible until due (strategy-driven BL-007 will
        not pick this up while ineligible).
      </span>,
    );
  }
  const bits: string[] = [];
  if (item.operatorSupervisionLastAction) {
    bits.push(`last: ${item.operatorSupervisionLastAction}`);
  }
  if (typeof item.autoQueueEligible === "boolean") {
    bits.push(`auto_queue_eligible=${String(item.autoQueueEligible)}`);
  }
  if (item.operatorSupervisionReason) {
    bits.push(`reason: ${item.operatorSupervisionReason}`);
  }
  if (bits.length) {
    parts.push(
      <div key="bits" className="sup-meta">
        {bits.map((b, i) => (
          <span key={b}>
            {i > 0 ? " · " : ""}
            <span className="mono">{b}</span>
          </span>
        ))}
      </div>,
    );
  }
  if (!parts.length) {
    return null;
  }
  return <>{parts}</>;
}

/**
 * First-class list-oriented pending-variant supervision (Stories 1–3 parity).
 */
export function ListView() {
  const {
    snapshot,
    client,
    refreshAll,
    setActionBanner,
    filteredListItems,
    dryRunDefault,
    setUnsavedScheduleDraft,
    selectedItemId,
    setSelectedItemId,
    openScheduleEditor,
    canMutate,
  } = useSupervisionStore();

  const [panel, setPanel] = useState<PanelMode>(null);
  const [active, setActive] = useState<{
    campaignId: string;
    variantId: string;
  } | null>(null);
  const [draftContent, setDraftContent] = useState("");
  const [editReason, setEditReason] = useState("");
  const [editDryRun, setEditDryRun] = useState(dryRunDefault);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelDryRun, setCancelDryRun] = useState(dryRunDefault);
  const [submitting, setSubmitting] = useState(false);
  const [editDirty, setEditDirty] = useState(false);

  const activeItem =
    snapshot && active
      ? snapshot.items.find(
          (i) =>
            i.campaignId === active.campaignId &&
            i.variantId === active.variantId,
        ) ?? null
      : null;

  function closePanels() {
    setPanel(null);
    setActive(null);
    setEditDirty(false);
    setUnsavedScheduleDraft(false);
  }

  function requestClosePanels() {
    if (panel === "edit" && editDirty) {
      const ok = window.confirm(
        "You have unsaved draft edits. Close and discard them?",
      );
      if (!ok) {
        return;
      }
    }
    closePanels();
  }

  useEffect(() => {
    if (!panel) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") {
        return;
      }
      event.preventDefault();
      if (panel === "edit" && editDirty) {
        const ok = window.confirm(
          "You have unsaved draft edits. Close and discard them?",
        );
        if (!ok) {
          return;
        }
      }
      setPanel(null);
      setActive(null);
      setEditDirty(false);
      setUnsavedScheduleDraft(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [panel, editDirty, setUnsavedScheduleDraft]);

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

  function openEdit(item: SupervisionItem) {
    if (!requireMutate("edit")) {
      return;
    }
    setActive({ campaignId: item.campaignId, variantId: item.variantId });
    setSelectedItemId(item.itemId);
    setDraftContent(item.draftContent ?? "");
    setEditReason("");
    setEditDryRun(dryRunDefault);
    setEditDirty(false);
    setUnsavedScheduleDraft(false);
    setPanel("edit");
  }

  function openDefer(item: SupervisionItem) {
    if (!requireMutate("defer")) {
      return;
    }
    setPanel(null);
    setActive(null);
    openScheduleEditor({
      channel: "linkedin",
      itemId: item.itemId,
      title: item.title,
      scheduledAtUtc: item.scheduledAtUtc,
      scheduleEditable: item.publishState === "pending",
      scheduleEditBlockReason:
        item.publishState === "pending"
          ? null
          : "linkedin_supervision_variant_not_pending",
      campaignId: item.campaignId,
      variantId: item.variantId,
      calendarItemId: item.calendarItemId,
      entry: "list",
    });
  }

  function openCancel(item: SupervisionItem) {
    if (!requireMutate("cancel")) {
      return;
    }
    setActive({ campaignId: item.campaignId, variantId: item.variantId });
    setSelectedItemId(item.itemId);
    setCancelReason("");
    setCancelDryRun(dryRunDefault);
    setUnsavedScheduleDraft(false);
    setPanel("cancel");
  }

  function handleMutationResult(
    action: string,
    result: MutationResult,
  ): void {
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
    }
  }

  async function submitEdit() {
    if (!active) {
      return;
    }
    if (!requireMutate("edit")) {
      return;
    }
    if (!editDryRun && !confirmRealMutation("edit")) {
      return;
    }
    setSubmitting(true);
    try {
      const body = {
        campaign_id: active.campaignId,
        variant: active.variantId,
        draft_content: draftContent,
        dry_run: editDryRun,
        reason: editReason.trim() || null,
        idempotency_key: editDryRun ? null : newIdempotencyKey(),
      };
      const result = await client.correctVariant(body);
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
    if (!active) {
      return;
    }
    if (!requireMutate("cancel")) {
      return;
    }
    if (!cancelDryRun && !confirmRealMutation("cancel")) {
      return;
    }
    setSubmitting(true);
    try {
      const result = await client.cancelVariant({
        campaign_id: active.campaignId,
        variant: active.variantId,
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

  const items = filteredListItems;
  const issues = snapshot?.issues ?? [];
  const failures = snapshot?.integrationFailures ?? [];
  const selectedItem =
    (activeItem ||
      items.find((item) => item.itemId === selectedItemId) ||
      null) ??
    null;

  return (
    <div data-testid="list-view" className="list-view operational-workspace">
      {panel === "edit" && activeItem && (
        <aside className="detail-drawer panel-inspect" data-testid="edit-panel">
          <div className="drawer-header">
            <div>
              <p className="eyebrow">Draft review</p>
              <h2>Inspect and edit</h2>
            </div>
            <button type="button" className="secondary" onClick={requestClosePanels}>
              Close
            </button>
          </div>
          <ItemDetail
            item={activeItem}
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
      )}

      {panel === "cancel" && activeItem && (
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
            <button type="button" className="secondary" onClick={closePanels}>
              Close
            </button>
          </div>
          <p className="meta">
            Campaign {activeItem.campaignId} · variant {activeItem.variantId}
          </p>
          <p className="sup-meta">
            Cancel sets worker <span className="mono">publish_state=cancelled</span>{" "}
            and excludes the variant from strategy-driven auto-queue (BL-007
            eligibility). It does not call LinkedIn and is not LinkedIn API
            published or LinkedIn unpublish. Real cancel requires confirmation.
          </p>
          <details className="diagnostics-details" data-testid="cancel-diagnostics">
            <summary>Diagnostics / technical details</summary>
            <p className="mono">
              action=cancel · campaign={activeItem.campaignId} · variant=
              {activeItem.variantId} · source_state={activeItem.publishState}
            </p>
          </details>
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
      )}

      {snapshot && items.length === 0 && (
        <div className="banner ok" data-testid="empty-state">
          No pending variants in the supervision window.
        </div>
      )}

      {items.length > 0 && (
        <div data-testid="results" className="triage-layout">
          <section className="triage-list" aria-label="Pending variant triage">
            <div className="section-heading">
              <div>
                <p className="eyebrow">Triage queue</p>
                <h2 className="section-title">Pending variants</h2>
              </div>
              <span className="queue-count">{items.length} items</span>
            </div>
            <div className="variant-card-list" data-testid="list-mobile-cards">
              {items.map((item) => {
                const label = publicationStateLabel(
                  item.publicationState,
                  item.linkedinApiPublished,
                );
                return (
                  <article
                    key={item.itemId}
                    className={`list-card ${rowRiskClass(item)}`}
                    data-testid="variant-card"
                    data-item-id={item.itemId}
                    data-risk={rowRiskClass(item)}
                  >
                    <button
                      type="button"
                      className="card-main"
                      data-testid="variant-row"
                      onClick={() => {
                        setActive({
                          campaignId: item.campaignId,
                          variantId: item.variantId,
                        });
                        setSelectedItemId(item.itemId);
                      }}
                    >
                      <span
                        className="status-pill"
                        style={{ backgroundColor: item.statusColor }}
                      >
                        {label}
                      </span>
                      <span className="card-title title-cell" title={itemSummary(item)}>
                        {itemSummary(item)}
                      </span>
                      <span className="card-meta">
                        {item.audience || "Audience not set"} ·{" "}
                        {formatSchedule(item.scheduledAtUtc)}
                      </span>
                      <span className="card-identity">
                        <span className="mono">{item.campaignId}</span>
                        {" / "}
                        <span className="mono">{item.variantId}</span>
                      </span>
                      <SupervisionMeta item={item} />
                    </button>
                    <div className="row-actions-cell">
                      <button
                        type="button"
                        className="row-action"
                        aria-label="Inspect / edit"
                        data-action="edit"
                        data-testid="row-edit"
                        disabled={!canMutate}
                        onClick={() => openEdit(item)}
                      >
                        Review
                      </button>
                      <button
                        type="button"
                        className="row-action secondary"
                        aria-label="Reschedule / defer"
                        data-action="defer"
                        data-testid="row-defer"
                        disabled={!canMutate}
                        onClick={() => openDefer(item)}
                      >
                        Schedule
                      </button>
                      <button
                        type="button"
                        className="row-action row-action-destructive"
                        data-action="cancel"
                        data-testid="row-cancel"
                        disabled={!canMutate}
                        onClick={() => openCancel(item)}
                      >
                        Cancel
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          </section>

          {selectedItem && !panel && (
            <aside className="detail-drawer" data-testid="selected-detail">
              <div className="drawer-header">
                <div>
                  <p className="eyebrow">Selected item</p>
                  <h2>{itemSummary(selectedItem)}</h2>
                </div>
              </div>
              <div className="detail-metadata">
                <span className="meta-label">Campaign</span>
                <span className="mono">{selectedItem.campaignId}</span>
                <span className="meta-label">Variant</span>
                <span className="mono">{selectedItem.variantId}</span>
                <span className="meta-label">Schedule</span>
                <span>{formatSchedule(selectedItem.scheduledAtUtc)}</span>
              </div>
              <p className="section-title">Calendar context</p>
              <p className="meta">
                <CalendarCell item={selectedItem} />
              </p>
              <details className="diagnostics-details">
                <summary>Technical diagnostics</summary>
                <p className="mono">
                  source={selectedItem.publishState} ·
                  linkedin_api_published={String(selectedItem.linkedinApiPublished)}
                </p>
              </details>
              <div className="panel-actions">
                <button
                  type="button"
                  className="row-action"
                  aria-label="Inspect / edit"
                  disabled={!canMutate}
                  onClick={() => openEdit(selectedItem)}
                >
                  Review draft
                </button>
                <button
                  type="button"
                  className="row-action secondary"
                  aria-label="Reschedule / defer"
                  disabled={!canMutate}
                  onClick={() => openDefer(selectedItem)}
                >
                  Change schedule
                </button>
                <button
                  type="button"
                  className="row-action row-action-destructive"
                  disabled={!canMutate}
                  onClick={() => openCancel(selectedItem)}
                >
                  Cancel
                </button>
              </div>
            </aside>
          )}
        </div>
      )}

      {failures.length > 0 && (
        <div data-testid="failures-panel">
          <h2 className="section-title">Integration failures (sibling context)</h2>
          <p className="meta">
            Failed siblings from campaigns that still have pending variants.
            Display-only blocked context — no cancel/edit/defer on failed rows
            from this console.
          </p>
          <ul className="issues">
            {failures.map((item) => (
              <li
                key={`${item.campaign_id}::${item.variant_id}::${item.publish_state}`}
                className="row-risk-failed"
              >
                <span className="status-pill status-pill-failed">Failed</span>{" "}
                <span className="mono">{item.campaign_id}</span> ·{" "}
                <span className="mono">{item.variant_id}</span>
                <details className="diagnostics-details inline-diagnostics">
                  <summary>Diagnostics</summary>
                  <span className="mono">
                    publish_state={item.publish_state || "failed"}
                    {item.last_error_code
                      ? ` · code ${item.last_error_code}`
                      : ""}
                    {item.http_status != null
                      ? ` · HTTP ${item.http_status}`
                      : ""}
                  </span>
                </details>
              </li>
            ))}
          </ul>
        </div>
      )}

      {issues.length > 0 && (
        <div data-testid="issues-panel">
          <h2 className="section-title">Read issues</h2>
          <ul className="issues">
            {issues.map((issue) => (
              <li key={`${issue.source}:${issue.identifier}:${issue.reason}`}>
                <span className="mono">{issue.source}</span>
                {issue.identifier ? (
                  <>
                    {" "}
                    · <span className="mono">{issue.identifier}</span>
                  </>
                ) : null}{" "}
                — {issue.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
