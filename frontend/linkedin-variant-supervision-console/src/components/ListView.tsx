import { useState, type ReactNode } from "react";
import type { ApiError } from "../api/errors";
import type { MutationResult } from "../api/types";
import {
  confirmRealMutation,
  newIdempotencyKey,
} from "./ConfirmationFlow";
import { ItemDetail } from "./ItemDetail";
import {
  datetimeLocalToUtcIso,
  ScheduleEditor,
  utcIsoToDatetimeLocal,
} from "./ScheduleEditor";
import { useSupervisionStore } from "../models/store";
import type { SupervisionItem } from "../models/supervision";

type PanelMode = "edit" | "defer" | "cancel" | null;

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
    setSelectedItemId,
  } = useSupervisionStore();

  const [panel, setPanel] = useState<PanelMode>(null);
  const [active, setActive] = useState<{
    campaignId: string;
    variantId: string;
  } | null>(null);
  const [draftContent, setDraftContent] = useState("");
  const [editReason, setEditReason] = useState("");
  const [editDryRun, setEditDryRun] = useState(dryRunDefault);
  const [deferSchedule, setDeferSchedule] = useState("");
  const [deferReason, setDeferReason] = useState("");
  const [deferDryRun, setDeferDryRun] = useState(dryRunDefault);
  const [cancelReason, setCancelReason] = useState("");
  const [cancelDryRun, setCancelDryRun] = useState(dryRunDefault);
  const [submitting, setSubmitting] = useState(false);

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
    setUnsavedScheduleDraft(false);
  }

  function openEdit(item: SupervisionItem) {
    setActive({ campaignId: item.campaignId, variantId: item.variantId });
    setSelectedItemId(item.itemId);
    setDraftContent(item.draftContent ?? "");
    setEditReason("");
    setEditDryRun(dryRunDefault);
    setUnsavedScheduleDraft(false);
    setPanel("edit");
  }

  function openDefer(item: SupervisionItem) {
    setActive({ campaignId: item.campaignId, variantId: item.variantId });
    setSelectedItemId(item.itemId);
    setDeferSchedule(utcIsoToDatetimeLocal(item.scheduledAtUtc));
    setDeferReason("");
    setDeferDryRun(dryRunDefault);
    setUnsavedScheduleDraft(false);
    setPanel("defer");
  }

  function openCancel(item: SupervisionItem) {
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

  async function submitDefer() {
    if (!active) {
      return;
    }
    const iso = datetimeLocalToUtcIso(deferSchedule);
    if (!iso) {
      setActionBanner({
        kind: "error",
        text: "Provide a valid new scheduled time (UTC).",
      });
      return;
    }
    if (!deferDryRun && !confirmRealMutation("defer")) {
      return;
    }
    setSubmitting(true);
    try {
      const result = await client.deferVariant({
        campaign_id: active.campaignId,
        variant: active.variantId,
        new_scheduled_at_utc: iso,
        dry_run: deferDryRun,
        reason: deferReason.trim() || null,
        idempotency_key: deferDryRun ? null : newIdempotencyKey(),
      });
      handleMutationResult("Defer", result);
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

  return (
    <div data-testid="list-view" className="list-view">
      {panel === "edit" && activeItem && (
        <div className="panel" data-testid="edit-panel">
          <h2>Edit draft content</h2>
          <ItemDetail
            item={activeItem}
            draftContent={draftContent}
            onDraftChange={setDraftContent}
          />
          <label htmlFor="edit-reason">Reason (optional)</label>
          <input
            id="edit-reason"
            type="text"
            value={editReason}
            onChange={(e) => setEditReason(e.target.value)}
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
              disabled={submitting}
              onClick={() => void submitEdit()}
            >
              Submit edit
            </button>
            <button
              type="button"
              className="secondary"
              onClick={closePanels}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {panel === "defer" && activeItem && (
        <div className="panel" data-testid="defer-panel">
          <h2>Defer / reschedule</h2>
          <p className="meta">
            Campaign {activeItem.campaignId} · variant {activeItem.variantId}
          </p>
          <ScheduleEditor
            value={deferSchedule}
            onChange={(value) => {
              setDeferSchedule(value);
              setUnsavedScheduleDraft(true);
            }}
          />
          <label htmlFor="defer-reason">Reason (optional)</label>
          <input
            id="defer-reason"
            type="text"
            value={deferReason}
            onChange={(e) => setDeferReason(e.target.value)}
            placeholder="e.g. operator_choice"
          />
          <div className="check-row">
            <input
              type="checkbox"
              id="defer-dry-run"
              data-testid="defer-dry-run"
              checked={deferDryRun}
              onChange={(e) => setDeferDryRun(e.target.checked)}
            />
            <label htmlFor="defer-dry-run">
              Dry-run (default on — validates without mutating)
            </label>
          </div>
          <div className="panel-actions">
            <button
              type="button"
              disabled={submitting}
              onClick={() => void submitDefer()}
            >
              Submit defer
            </button>
            <button
              type="button"
              className="secondary"
              onClick={closePanels}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {panel === "cancel" && activeItem && (
        <div className="panel" data-testid="cancel-panel">
          <h2>Cancel pending variant</h2>
          <p className="meta">
            Campaign {activeItem.campaignId} · variant {activeItem.variantId}
          </p>
          <p className="sup-meta">
            Cancel sets worker <span className="mono">publish_state=cancelled</span>{" "}
            and excludes the variant from strategy-driven auto-queue (BL-007
            eligibility). It does not call LinkedIn and is not LinkedIn API
            published or LinkedIn unpublish.
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
          <div className="panel-actions">
            <button
              type="button"
              disabled={submitting}
              onClick={() => void submitCancel()}
            >
              Submit cancel
            </button>
            <button
              type="button"
              className="secondary"
              onClick={closePanels}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {snapshot && items.length === 0 && (
        <div className="banner ok" data-testid="empty-state">
          No pending variants in the supervision window.
        </div>
      )}

      {items.length > 0 && (
        <div data-testid="results">
          <h2 className="section-title">Pending variants</h2>
          <div className="table-wrap list-desktop">
            <table>
              <thead>
                <tr>
                  <th>Campaign</th>
                  <th>Variant</th>
                  <th>Audience</th>
                  <th>Scheduled (UTC)</th>
                  <th>Publish state</th>
                  <th>Calendar</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr
                    key={item.itemId}
                    data-testid="variant-row"
                    data-item-id={item.itemId}
                  >
                    <td className="mono">{item.campaignId}</td>
                    <td>
                      <span className="mono">{item.variantId}</span>
                      <SupervisionMeta item={item} />
                    </td>
                    <td>{item.audience || ""}</td>
                    <td className="mono">{item.scheduledAtUtc || ""}</td>
                    <td>
                      <span
                        className="status-pill"
                        style={{ backgroundColor: item.statusColor }}
                      >
                        {item.publicationState}
                      </span>{" "}
                      <span className="meta">
                        (source {item.publishState}; not LinkedIn API published)
                      </span>
                    </td>
                    <td>
                      <CalendarCell item={item} />
                    </td>
                    <td>
                      <button
                        type="button"
                        className="row-action"
                        data-action="edit"
                        onClick={() => openEdit(item)}
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        className="row-action secondary"
                        data-action="defer"
                        onClick={() => openDefer(item)}
                      >
                        Defer
                      </button>
                      <button
                        type="button"
                        className="row-action secondary"
                        data-action="cancel"
                        onClick={() => openCancel(item)}
                      >
                        Cancel
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="list-mobile-cards" data-testid="list-mobile-cards">
            {items.map((item) => (
              <article
                key={`card-${item.itemId}`}
                className="list-card"
                data-testid="variant-card"
                data-item-id={item.itemId}
              >
                <header>
                  <span
                    className="status-pill"
                    style={{ backgroundColor: item.statusColor }}
                  >
                    {item.publicationState}
                  </span>{" "}
                  <span className="mono">{item.campaignId}</span>
                </header>
                <p>
                  variant <span className="mono">{item.variantId}</span>
                  {item.audience ? ` · ${item.audience}` : ""}
                </p>
                <p className="mono">UTC {item.scheduledAtUtc || "—"}</p>
                <SupervisionMeta item={item} />
                <div className="panel-actions">
                  <button
                    type="button"
                    className="row-action"
                    data-action="edit"
                    onClick={() => openEdit(item)}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    className="row-action secondary"
                    data-action="defer"
                    onClick={() => openDefer(item)}
                  >
                    Defer
                  </button>
                  <button
                    type="button"
                    className="row-action secondary"
                    data-action="cancel"
                    onClick={() => openCancel(item)}
                  >
                    Cancel
                  </button>
                </div>
              </article>
            ))}
          </div>
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
              >
                <span className="mono">{item.campaign_id}</span> ·{" "}
                <span className="mono">{item.variant_id}</span> ·{" "}
                <span className="mono">{item.publish_state || "failed"}</span>
                {item.last_error_code
                  ? ` · code ${item.last_error_code}`
                  : ""}
                {item.http_status != null
                  ? ` · HTTP ${item.http_status}`
                  : ""}
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
