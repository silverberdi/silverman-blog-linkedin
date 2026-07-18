import type { ConsoleView } from "../models/supervision";

/**
 * Persistent desktop/mobile view switcher. Context preservation is owned by the
 * store; this control only requests a view change (which may warn on unsaved drafts).
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
        Month calendar
      </button>
    </div>
  );
}
