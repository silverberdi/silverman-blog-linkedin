import {
  OPERATOR_UI_API_BASE_URL_KEY,
  type OperatorUiConfigResult,
} from "../config/operatorUiConfig";

/**
 * Fail-closed operator-visible panel when separated-UI config or pairing fails.
 * Names env keys only — never secret values.
 */
export function ConfigBlockedScreen({
  result,
}: {
  result: Extract<OperatorUiConfigResult, { ok: false }>;
}) {
  const heading =
    result.reason === "pairing"
      ? "Environment pairing failed"
      : "Configuration required";
  const detail =
    result.reason === "pairing"
      ? "Authenticated supervision and mutation calls are disabled until UI and API environments agree. Relative same-origin API fallback stays off in separated-UI mode."
      : "The console will not call relative same-origin API paths while this block is active.";

  return (
    <main
      className="console-shell config-blocked"
      data-testid="config-blocked-screen"
      role="alert"
    >
      <header className="app-bar">
        <div className="brand-lockup">
          <p className="eyebrow">Silverman Authority Manager</p>
          <h1>{heading}</h1>
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
          . {detail}
        </p>
      </section>
    </main>
  );
}
