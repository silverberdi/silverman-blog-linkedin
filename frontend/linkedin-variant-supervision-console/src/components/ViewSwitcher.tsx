import type { ConsoleView } from "../models/supervision";

/**
 * View switcher stub: list remains first-class; calendar scaffold is reachable.
 */
export function ViewSwitcher({
  activeView,
  onChange,
}: {
  activeView: ConsoleView;
  onChange: (view: ConsoleView) => void;
}) {
  return (
    <div className="view-switcher" role="tablist" aria-label="Console views">
      <button
        type="button"
        role="tab"
        aria-selected={activeView === "list"}
        className={activeView === "list" ? "active-view" : "secondary"}
        onClick={() => onChange("list")}
        data-testid="view-list"
      >
        List
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeView === "calendar"}
        className={activeView === "calendar" ? "active-view" : "secondary"}
        onClick={() => onChange("calendar")}
        data-testid="view-calendar"
      >
        Calendar (scaffold)
      </button>
    </div>
  );
}
