import {
  OPERATOR_UI_API_BASE_URL_KEY,
  type OperatorUiConfigResult,
} from "../config/operatorUiConfig";

/**
 * Fail-closed operator-visible panel when separated-UI API config is missing/invalid.
 * Names env keys only — never secret values.
 */
export function ConfigBlockedScreen({
  result,
}: {
  result: Extract<OperatorUiConfigResult, { ok: false }>;
}) {
  return (
    <main
      className="console-shell config-blocked"
      data-testid="config-blocked-screen"
      role="alert"
    >
      <header className="app-bar">
        <div className="brand-lockup">
          <p className="eyebrow">Silverman Authority Manager</p>
          <h1>Configuration required</h1>
        </div>
      </header>
      <section className="config-blocked-panel" data-testid="config-blocked-panel">
        <div className="banner error" role="status">
          {result.message}
        </div>
        <p className="config-blocked-detail">
          Required configuration key(s):{" "}
          <code data-testid="config-blocked-keys">
            {result.requiredKeys.join(", ") || OPERATOR_UI_API_BASE_URL_KEY}
          </code>
          . The console will not call relative same-origin API paths while this
          block is active.
        </p>
      </section>
    </main>
  );
}
