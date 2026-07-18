import {
  PUBLICATION_STATES,
  publicationStateLabel,
  type FilterState,
  type PublicationDisplayState,
} from "../models/supervision";
import { useSupervisionStore } from "../models/store";

/**
 * Shared filters applied to both List and Month calendar views (US-040B).
 */
export function Filters() {
  const {
    filters,
    setFilters,
    resetFilters,
    showHiddenCritical,
    hiddenCriticalCount,
  } = useSupervisionStore();

  function update(partial: Partial<FilterState>) {
    setFilters((prev) => ({ ...prev, ...partial }));
  }

  function toggleState(state: PublicationDisplayState) {
    setFilters((prev) => {
      const has = prev.publicationStates.includes(state);
      const publicationStates = has
        ? prev.publicationStates.filter((s) => s !== state)
        : [...prev.publicationStates, state];
      return { ...prev, publicationStates };
    });
  }

  return (
    <div className="panel filters-panel" data-testid="filters">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Focus</p>
          <h2>Filters</h2>
        </div>
        <button
          type="button"
          className="secondary"
          data-testid="filters-reset"
          onClick={resetFilters}
        >
          Reset
        </button>
      </div>

      <div className="filters-grid">
        <div>
          <label htmlFor="filter-channel">Channel</label>
          <select
            id="filter-channel"
            data-testid="filter-channel"
            value={filters.channel}
            onChange={(e) =>
              update({
                channel: e.target.value as FilterState["channel"],
              })
            }
          >
            <option value="all">All</option>
            <option value="blog">Blog</option>
            <option value="linkedin">LinkedIn</option>
          </select>
        </div>

        <div>
          <label htmlFor="filter-campaign">Campaign / label</label>
          <input
            id="filter-campaign"
            data-testid="filter-campaign"
            type="text"
            value={filters.campaignQuery}
            onChange={(e) => update({ campaignQuery: e.target.value })}
            placeholder="campaign id, variant, or title"
          />
        </div>

        <div className="check-row">
          <input
            type="checkbox"
            id="filter-blocked"
            data-testid="filter-blocked"
            checked={filters.blockedOnly}
            onChange={(e) => update({ blockedOnly: e.target.checked })}
          />
          <label htmlFor="filter-blocked">Blocked only</label>
        </div>

        <div className="check-row">
          <input
            type="checkbox"
            id="filter-due-soon"
            data-testid="filter-due-soon"
            checked={filters.dueSoonOnly}
            onChange={(e) => update({ dueSoonOnly: e.target.checked })}
          />
          <label htmlFor="filter-due-soon">Due soon (48h)</label>
        </div>
      </div>

      <fieldset className="filter-states" data-testid="filter-states">
        <legend>Publication state</legend>
        <div className="filter-state-chips">
          {PUBLICATION_STATES.map((state) => (
            <label key={state} className="filter-chip">
              <input
                type="checkbox"
                data-testid={`filter-state-${state}`}
                checked={filters.publicationStates.includes(state)}
                onChange={() => toggleState(state)}
              />
              <span>{publicationStateLabel(state)}</span>
            </label>
          ))}
        </div>
      </fieldset>

      {hiddenCriticalCount > 0 && (
        <div
          className="banner warn"
          data-testid="hidden-critical-banner"
          role="status"
        >
          {hiddenCriticalCount} critical failure
          {hiddenCriticalCount === 1 ? "" : "s"} hidden by current filters.{" "}
          <button
            type="button"
            className="secondary"
            data-testid="show-critical-btn"
            onClick={showHiddenCritical}
          >
            Show critical / reset filters
          </button>
        </div>
      )}
    </div>
  );
}
