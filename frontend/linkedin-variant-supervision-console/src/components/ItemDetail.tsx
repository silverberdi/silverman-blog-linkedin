import { publicationStateLabel } from "../models/supervision";
import type { SupervisionItem } from "../models/supervision";

/**
 * Item detail — draft preview plus expandable diagnostics (US-040E).
 */
export function ItemDetail({
  item,
  draftContent,
  onDraftChange,
}: {
  item: SupervisionItem | null;
  draftContent: string;
  onDraftChange: (value: string) => void;
}) {
  if (!item) {
    return null;
  }
  const label = publicationStateLabel(
    item.publicationState,
    item.linkedinApiPublished,
  );
  return (
    <div className="item-detail" data-testid="item-detail-scaffold">
      <p className="meta">
        Campaign <span className="mono">{item.campaignId}</span> · variant{" "}
        <span className="mono">{item.variantId}</span>
      </p>
      <p className="item-detail-status">
        <span
          className="status-pill"
          style={{ backgroundColor: item.statusColor }}
        >
          {label}
        </span>{" "}
        <span className="meta">
          (not LinkedIn API published unless API evidence is present)
        </span>
      </p>
      <label htmlFor="edit-content">Draft content</label>
      <textarea
        id="edit-content"
        data-testid="edit-content"
        spellCheck
        value={draftContent}
        onChange={(e) => onDraftChange(e.target.value)}
      />
      <details className="diagnostics-details" data-testid="item-diagnostics">
        <summary>Diagnostics / technical details</summary>
        <dl className="diagnostics-dl">
          <div>
            <dt>Display state</dt>
            <dd className="mono">{item.publicationState}</dd>
          </div>
          <div>
            <dt>Source publish_state</dt>
            <dd className="mono">{item.publishState}</dd>
          </div>
          <div>
            <dt>linkedinApiPublished</dt>
            <dd className="mono">{String(item.linkedinApiPublished)}</dd>
          </div>
          <div>
            <dt>blocked / critical</dt>
            <dd className="mono">
              {String(item.blocked)} / {String(item.critical)}
            </dd>
          </div>
          {item.operatorSupervisionLastAction && (
            <div>
              <dt>operator_supervision_last_action</dt>
              <dd className="mono">{item.operatorSupervisionLastAction}</dd>
            </div>
          )}
          {typeof item.autoQueueEligible === "boolean" && (
            <div>
              <dt>auto_queue_eligible</dt>
              <dd className="mono">{String(item.autoQueueEligible)}</dd>
            </div>
          )}
          {item.operatorSupervisionReason && (
            <div>
              <dt>operator_supervision_reason</dt>
              <dd className="mono">{item.operatorSupervisionReason}</dd>
            </div>
          )}
          {item.calendarItemId && (
            <div>
              <dt>calendar_item_id</dt>
              <dd className="mono">{item.calendarItemId}</dd>
            </div>
          )}
          {item.calendarStatus && (
            <div>
              <dt>calendar_status</dt>
              <dd className="mono">{item.calendarStatus}</dd>
            </div>
          )}
        </dl>
      </details>
    </div>
  );
}
