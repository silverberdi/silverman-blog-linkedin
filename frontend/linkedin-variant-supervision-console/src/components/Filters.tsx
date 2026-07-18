/**
 * Filters scaffold — props/state shape ready; no-op until US-040B.
 */
export function Filters({
  query,
  onQueryChange,
}: {
  query: string;
  onQueryChange: (value: string) => void;
}) {
  return (
    <div className="panel" data-testid="filters-scaffold" hidden={false}>
      <h2>Filters (scaffold)</h2>
      <p className="sup-meta">
        Filter controls are scaffolded for US-040B. List shows all pending rows
        from the shared model.
      </p>
      <label htmlFor="filter-query">Filter query (not applied yet)</label>
      <input
        id="filter-query"
        type="text"
        value={query}
        onChange={(e) => onQueryChange(e.target.value)}
        placeholder="campaign or variant id"
        aria-disabled="true"
      />
    </div>
  );
}
