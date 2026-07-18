import { type ReactNode } from "react";
import { Banner } from "./Banner";
import { Filters } from "./Filters";
import { StatusSummary } from "./StatusSummary";
import { ViewSwitcher } from "./ViewSwitcher";
import { useSupervisionStore } from "../models/store";

/**
 * App shell: session banners (US-040D), dry-run default, enablement display-only,
 * Week | Month views (US-040G), operational count strip + affordance groups.
 * First screen is the operational console — no marketing landing.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const {
    snapshot,
    scheduleSnapshot,
    activeView,
    requestViewChange,
    loading,
    statusBanner,
    actionBanner,
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
  const enablementText = enablementSource
    ? enablementSource.linkedinPublicationEnabled
      ? "LinkedIn API publish guard is on. This console still only supervises."
      : "LinkedIn API publish guard is off. Supervision stays available."
    : "";

  const needsReauth =
    sessionState === "anonymous" ||
    sessionState === "expired" ||
    sessionState === "forbidden";

  return (
    <main className="console-shell" data-testid="app-shell">
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

      <div className="alert-stack">
        <Banner
          kind={enablementSource?.linkedinPublicationEnabled ? "ok" : "warn"}
          text={enablementText}
          testId="enablement-banner"
        />
        <Banner
          kind={statusBanner.kind}
          text={statusBanner.text}
          testId="status-banner"
        />
        <Banner
          kind={actionBanner.kind}
          text={actionBanner.text}
          testId="action-banner"
        />
      </div>

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
        diagnostics stay available in detail panels.
      </footer>
    </main>
  );
}
