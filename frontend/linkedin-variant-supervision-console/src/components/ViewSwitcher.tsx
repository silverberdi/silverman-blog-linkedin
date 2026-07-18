import type { ConsoleView } from "../models/supervision";

/**
 * Persistent desktop/mobile view switcher (US-040G): Week | Month only.
 * Context preservation is owned by the store; this control only requests a view
 * change (which may warn on unsaved drafts).
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
        aria-selected={activeView === "week"}
        className={activeView === "week" ? "active-view" : "secondary"}
        onClick={() => onChange("week")}
        data-testid="view-week"
      >
        Week
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={activeView === "month"}
        className={activeView === "month" ? "active-view" : "secondary"}
        onClick={() => onChange("month")}
        data-testid="view-month"
      >
        Month
      </button>
    </div>
  );
}
