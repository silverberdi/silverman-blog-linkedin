import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { SupervisionApiClient } from "./api/client";
import {
  createAuthProviderForConfig,
  GoogleOidcAuthProvider,
  type AuthProvider,
} from "./api/auth";
import type { SessionState } from "./api/session";
import { ConfigBlockedScreen } from "./components/ConfigBlockedScreen";
import { validateApiEnvironmentPairing } from "./config/environmentPairing";
import {
  OPERATOR_UI_ENV_LABEL_KEY,
  resolveOperatorUiConfig,
  type DeploymentEnvironment,
} from "./config/operatorUiConfig";
import "./styles/console.css";

const rootEl = document.getElementById("root")!;

function renderBlocked(
  result: Parameters<typeof ConfigBlockedScreen>[0]["result"],
): void {
  createRoot(rootEl).render(
    <StrictMode>
      <ConfigBlockedScreen result={result} />
    </StrictMode>,
  );
}

function renderApp(
  apiBaseUrl: string,
  auth: AuthProvider,
  options: {
    deploymentEnvironment?: DeploymentEnvironment;
    initialSessionState?: SessionState;
    googleAuthEnabled?: boolean;
  } = {},
): void {
  const client = new SupervisionApiClient(
    auth,
    fetch.bind(globalThis),
    apiBaseUrl,
  );
  createRoot(rootEl).render(
    <StrictMode>
      <App
        client={client}
        deploymentEnvironment={options.deploymentEnvironment}
        initialSessionState={options.initialSessionState}
        googleAuthEnabled={options.googleAuthEnabled}
      />
    </StrictMode>,
  );
}

async function bootstrap(): Promise<void> {
  const configResult = resolveOperatorUiConfig();
  if (!configResult.ok) {
    renderBlocked(configResult);
    return;
  }

  const { config } = configResult;

  // Separated mode only (US-096): narrow envLabel before pairing.
  const envLabel = config.envLabel;
  if (envLabel !== "uat" && envLabel !== "prod") {
    renderBlocked({
      ok: false,
      reason: "invalid",
      message:
        `Operator UI is blocked: ${OPERATOR_UI_ENV_LABEL_KEY} must be uat or prod. ` +
        `Separated bootstrap cannot proceed without a proven deployment environment.`,
      requiredKeys: [OPERATOR_UI_ENV_LABEL_KEY],
    });
    return;
  }

  const pairing = await validateApiEnvironmentPairing(
    config.apiBaseUrl,
    envLabel,
  );
  if (!pairing.ok) {
    renderBlocked(pairing);
    return;
  }

  const auth = createAuthProviderForConfig({
    googleAuthEnabled: config.googleAuthEnabled,
    apiBaseUrl: config.apiBaseUrl,
  });

  let initialSessionState: SessionState | undefined;
  if (auth instanceof GoogleOidcAuthProvider) {
    const restored = await auth.restoreSession();
    initialSessionState = restored;
    const configError = auth.getConfigError();
    if (configError) {
      renderBlocked({
        ok: false,
        reason: "invalid",
        message: configError,
        requiredKeys: [
          "SILVERMAN_OPERATOR_GOOGLE_AUTH_ENABLED",
          "SILVERMAN_OPERATOR_GOOGLE_CLIENT_ID",
          "SILVERMAN_OPERATOR_GOOGLE_CLIENT_SECRET",
          "SILVERMAN_OPERATOR_GOOGLE_REDIRECT_URI",
          "SILVERMAN_OPERATOR_SESSION_SECRET",
          "SILVERMAN_OPERATOR_UI_SUCCESS_REDIRECT",
        ],
      });
      return;
    }
  }

  renderApp(config.apiBaseUrl, auth, {
    deploymentEnvironment: pairing.environment,
    initialSessionState,
    googleAuthEnabled: config.googleAuthEnabled,
  });
}

void bootstrap();
