import { useState, type ReactNode } from "react";
import { Banner } from "./Banner";
import { Filters } from "./Filters";
import { StatusSummary } from "./StatusSummary";
import { ViewSwitcher } from "./ViewSwitcher";
import { useSupervisionStore } from "../models/store";

/**
 * App shell: dry-run default messaging, enablement display-only, qualified language.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const {
    snapshot,
    activeView,
    setActiveView,
    loading,
    statusBanner,
    actionBanner,
    loadPending,
    clearAuth,
  } = useSupervisionStore();
  const [filterQuery, setFilterQuery] = useState("");

  const enablementText = snapshot
    ? snapshot.linkedinPublicationEnabled
      ? "LinkedIn publication enablement is on (display-only blocked context; this page does not publish to LinkedIn and does not change SILVERMAN_LINKEDIN_PUBLICATION_ENABLED)."
      : "LinkedIn publication enablement is off (display-only blocked context for real API publish). Pending variants remain listed; this does not hide the supervision window or bypass the guard."
    : "";

  return (
    <main className="console-shell" data-testid="app-shell">
      <h1>LinkedIn variant supervision</h1>
      <p className="lede">
        Flow A LinkedIn variants in the optional supervision window (
        <span className="mono">publish_state=pending</span>). Edit, defer, and
        cancel persist through US-017 worker HTTP. Pending, cancelled, and
        campaign <span className="mono">flow_a_complete</span> are not LinkedIn
        API published.
      </p>

      <Banner
        kind={snapshot?.linkedinPublicationEnabled ? "ok" : "warn"}
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
          onClick={() => void loadPending()}
        >
          Load pending variants
        </button>
        <button
          type="button"
          className="secondary"
          data-testid="clear-key-btn"
          onClick={clearAuth}
        >
          Clear in-memory API key
        </button>
      </div>

      <StatusSummary snapshot={snapshot} />
      <ViewSwitcher activeView={activeView} onChange={setActiveView} />
      <Filters query={filterQuery} onQueryChange={setFilterQuery} />

      {children}

      <p className="note">
        Story 3 supports edit, defer, and cancel for pending variants via{" "}
        <span className="mono">POST /correct-linkedin-variant</span>,{" "}
        <span className="mono">POST /defer-linkedin-variant</span>, and{" "}
        <span className="mono">POST /cancel-linkedin-publication</span>. Dry-run
        is the default. Blocked-state context includes publication enablement,
        deferred / <span className="mono">auto_queue_eligible</span>, and sibling
        integration failures. US-040A modernizes the console layer (React +
        TypeScript + Vite); US-040B–US-040E remain out of scope.
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
        (US-017). Data source: authenticated{" "}
        <span className="mono">
          GET /flow-a/linkedin-variants/pending-supervision
        </span>{" "}
        (ADR-0001 worker HTTP).
      </footer>
    </main>
  );
}
