import { type ReactNode } from "react";
import { Banner } from "./Banner";
import { Filters } from "./Filters";
import { StatusSummary } from "./StatusSummary";
import { ViewSwitcher } from "./ViewSwitcher";
import { useSupervisionStore } from "../models/store";

/**
 * App shell: session banners (US-040D), dry-run default, enablement display-only,
 * dual views (US-040B).
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
    loadPending,
    clearAuth,
    signIn,
    dryRunDefault,
    setDryRunDefault,
    canMutate,
  } = useSupervisionStore();

  const enablementSource = snapshot ?? scheduleSnapshot;
  const enablementText = enablementSource
    ? enablementSource.linkedinPublicationEnabled
      ? "LinkedIn publication enablement is on (display-only blocked context; this page does not publish to LinkedIn and does not change SILVERMAN_LINKEDIN_PUBLICATION_ENABLED)."
      : "LinkedIn publication enablement is off (display-only blocked context for real API publish). Pending variants remain listed; this does not hide the supervision window or bypass the guard."
    : "";

  const needsReauth =
    sessionState === "anonymous" ||
    sessionState === "expired" ||
    sessionState === "forbidden";

  return (
    <main className="console-shell" data-testid="app-shell">
      <h1>LinkedIn variant supervision</h1>
      <p className="lede">
        Flow A dual views: <strong>List</strong> for pending LinkedIn supervision
        (Stories 1–3) and <strong>Month calendar</strong> for blog + LinkedIn
        schedule visibility. Pending, queued, cancelled, blog handoff, and
        campaign <span className="mono">flow_a_complete</span> are not LinkedIn
        API published.
      </p>

      <Banner
        kind={sessionBanner.kind}
        text={sessionBanner.text}
        testId="session-banner"
      />
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

      <div className="toolbar">
        <button
          type="button"
          data-testid="load-btn"
          disabled={loading}
          onClick={() => void refreshAll()}
        >
          Refresh list + calendar
        </button>
        <button
          type="button"
          className="secondary"
          data-testid="load-pending-btn"
          disabled={loading}
          onClick={() => void loadPending()}
        >
          Load pending only
        </button>
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
        <div className="check-row toolbar-dry-run">
          <input
            type="checkbox"
            id="shell-dry-run-default"
            data-testid="shell-dry-run-default"
            checked={dryRunDefault}
            onChange={(e) => setDryRunDefault(e.target.checked)}
          />
          <label htmlFor="shell-dry-run-default">
            Dry-run default (survives view switch)
          </label>
        </div>
      </div>

      {!canMutate && sessionState !== "authenticated" && (
        <p className="note" data-testid="mutation-gated-note">
          Schedule mutations (edit / defer / cancel / calendar schedule-update)
          are disabled until you are authenticated with mutation permission.
          The worker remains the authoritative rejector for unauthenticated
          requests.
        </p>
      )}
      {sessionState === "authenticated" && !canMutate && (
        <p className="note" data-testid="readonly-gated-note">
          Read-only session: schedule mutations are not allowed. Visible
          pending / queued context is for inspection only.
        </p>
      )}

      <StatusSummary snapshot={snapshot} />
      <ViewSwitcher activeView={activeView} onChange={requestViewChange} />
      <Filters />

      {children}

      <p className="note">
        List mutations use{" "}
        <span className="mono">POST /correct-linkedin-variant</span>,{" "}
        <span className="mono">POST /defer-linkedin-variant</span>, and{" "}
        <span className="mono">POST /cancel-linkedin-publication</span>. Month
        calendar schedule updates use{" "}
        <span className="mono">POST /editorial-calendar/update-item-schedule</span>{" "}
        (blog) or defer (LinkedIn). Reads:{" "}
        <span className="mono">GET /flow-a/schedule-visibility</span>. Public
        URL hosting and Google/OIDC activation remain deferred (US-040D
        readiness only). US-040E polish remains out of scope.
      </p>

      <footer>
        Guidance (repo docs — not mutation endpoints):{" "}
        <span className="mono">
          docs/operations/linkedin-variant-review-policy.md
        </span>{" "}
        (US-015),{" "}
        <span className="mono">
          docs/operations/linkedin-variant-quality-criteria.md
        </span>{" "}
        (US-016),{" "}
        <span className="mono">
          docs/operations/linkedin-variant-supervision-mechanics.md
        </span>{" "}
        (US-017). Data: authenticated{" "}
        <span className="mono">
          GET /flow-a/linkedin-variants/pending-supervision
        </span>{" "}
        and{" "}
        <span className="mono">GET /flow-a/schedule-visibility</span> (ADR-0001
        worker HTTP).
      </footer>
    </main>
  );
}
