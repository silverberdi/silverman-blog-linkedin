import type { SupervisionItem } from "../models/supervision";

/**
 * Item detail scaffold — hosts draft preview for list edit; US-040B may expand.
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
  return (
    <div data-testid="item-detail-scaffold">
      <p className="meta">
        Campaign <span className="mono">{item.campaignId}</span> · variant{" "}
        <span className="mono">{item.variantId}</span>
      </p>
      <label htmlFor="edit-content">Draft content</label>
      <textarea
        id="edit-content"
        data-testid="edit-content"
        spellCheck
        value={draftContent}
        onChange={(e) => onDraftChange(e.target.value)}
      />
    </div>
  );
}
