import type { SupervisionItem, SupervisionSnapshot } from "../models/supervision";

/**
 * Month calendar scaffold — consumes shared model; full UX is US-040B.
 */
export function MonthCalendarView({
  snapshot,
}: {
  snapshot: SupervisionSnapshot | null;
}) {
  const items = snapshot?.items ?? [];
  return (
    <section data-testid="month-calendar-scaffold">
      <h2 className="section-title">Month calendar (scaffold — US-040B)</h2>
      <div className="scaffold-note">
        <p>
          Calendar chrome is a placeholder. Items below come from the same shared
          normalized model as the list view (
          <span className="mono">campaign_id</span> +{" "}
          <span className="mono">variant_id</span>). Full month visibility UX is
          not implemented in US-040A.
        </p>
        <p className="sup-meta">
          Pending items in shared model: {items.length}
        </p>
        <div className="calendar-grid-stub" aria-hidden="true">
          {Array.from({ length: 7 }, (_, i) => (
            <div key={i} className="calendar-cell-stub">
              Day {i + 1}
            </div>
          ))}
        </div>
        {items.length > 0 && (
          <ul className="issues" data-testid="calendar-model-items">
            {items.map((item: SupervisionItem) => (
              <li key={`${item.campaignId}::${item.variantId}`}>
                <span className="mono">{item.campaignId}</span> ·{" "}
                <span className="mono">{item.variantId}</span> · scheduled{" "}
                <span className="mono">{item.scheduledAtUtc || "—"}</span> ·
                actions [{item.actions.join(", ")}]
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
