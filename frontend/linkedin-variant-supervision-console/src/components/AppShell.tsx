import { type ReactNode } from "react";
import { Banner } from "./Banner";
import { Filters } from "./Filters";
import { StatusSummary } from "./StatusSummary";
import { ToastHost } from "./ToastHost";
import { ViewSwitcher } from "./ViewSwitcher";
import { useSupervisionStore } from "../models/store";

/**
 * App shell: quiet session + enablement chip (US-040H), dry-run default,
 * Week | Month views, operational count strip. Happy-path success uses toasts.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const {
    snapshot,
    scheduleSnapshot,
    activeView,
    requestViewChange,
    loading,
    statusBanner,
    sessionBanner,
    sessionState,
    refreshAll,
    clearAuth,
    signIn,
    dryRunDefault,
    setDryRunDefault,
    canMutate,
  } = useSupervisionStore();

  const enablementSource = snapshot ?? scheduleSnapshot;
  const publishGuardOn = Boolean(enablementSource?.linkedinPublicationEnabled);
  const enablementText = enablementSource
    ? publishGuardOn
      ? "Publish guard on — console supervises only"
      : "Publish guard off — supervision still available"
    : "";

  const needsReauth =
    sessionState === "anonymous" ||
    sessionState === "expired" ||
    sessionState === "forbidden";

  // Structural warn/error only — happy-path ok stays off the primary scan path.
  const showStatusBanner =
    Boolean(statusBanner.text) &&
    (statusBanner.kind === "warn" || statusBanner.kind === "error");

  return (
    <main className="console-shell" data-testid="app-shell">
      <ToastHost />
      <header className="app-bar">
        <div className="brand-lockup">
          <p className="eyebrow">Flow A operations</p>
          <h1>LinkedIn supervision</h1>
        </div>

        <section
          className="app-controls"
          data-testid="affordance-nav"
          aria-label="View and refresh"
        >
          <ViewSwitcher activeView={activeView} onChange={requestViewChange} />
          <button
            type="button"
            className="icon-button"
            aria-label="Refresh pending and schedule data"
            data-testid="load-btn"
            disabled={loading}
            onClick={() => void refreshAll()}
          >
            Refresh
          </button>
          <div className="mode-toggle toolbar-dry-run">
            <input
              type="checkbox"
              id="shell-dry-run-default"
              data-testid="shell-dry-run-default"
              checked={dryRunDefault}
              onChange={(e) => setDryRunDefault(e.target.checked)}
            />
            <label htmlFor="shell-dry-run-default">
              {dryRunDefault ? "Dry-run" : "Commit"}
            </label>
          </div>
          {enablementText && (
            <span
              className={`enablement-chip ${publishGuardOn ? "is-on" : "is-off"}`}
              data-testid="enablement-chip"
              title={
                publishGuardOn
                  ? "LinkedIn API publish guard is on. This console still only supervises."
                  : "LinkedIn API publish guard is off. Supervision stays available."
              }
            >
              {enablementText}
            </span>
          )}
        </section>
      </header>

      <section
        className="session-strip"
        data-testid="affordance-session"
        aria-label="Session"
      >
        <div>
          <span className={`session-dot session-${sessionState}`} aria-hidden="true" />
          <span data-testid="session-banner">{sessionBanner.text}</span>
        </div>
        <div className="toolbar toolbar-session">
          {needsReauth && (
            <button
              type="button"
              data-testid="sign-in-btn"
              disabled={loading}
              onClick={() => void signIn()}
            >
              Sign in
            </button>
          )}
          <button
            type="button"
            className="secondary"
            data-testid="clear-key-btn"
            onClick={clearAuth}
          >
            Clear session credential
          </button>
        </div>
      </section>

      {showStatusBanner && (
        <div className="alert-stack">
          <Banner
            kind={statusBanner.kind}
            text={statusBanner.text}
            testId="status-banner"
          />
        </div>
      )}

      {!canMutate && sessionState !== "authenticated" && (
        <p className="note" data-testid="mutation-gated-note">
          Mutations are disabled until you sign in with write permission.
        </p>
      )}
      {sessionState === "authenticated" && !canMutate && (
        <p className="note" data-testid="readonly-gated-note">
          Read-only session: review is available, mutations are disabled.
        </p>
      )}

      <StatusSummary />

      <section
        className="filter-dock"
        data-testid="affordance-filters"
        aria-label="Filters"
      >
        <Filters />
      </section>

      <section
        className="affordance-group affordance-content"
        data-testid="affordance-content"
        aria-label={
          activeView === "month" ? "Month schedule view" : "Week schedule view"
        }
      >
        {children}
      </section>

      <footer>
        Public URL hosting and Google/OIDC activation remain deferred. Technical
        diagnostics stay available in the event modal.
      </footer>
    </main>
  );
}
