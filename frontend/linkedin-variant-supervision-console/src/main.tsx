import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { SupervisionApiClient } from "./api/client";
import { defaultAuthProvider } from "./api/auth";
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
  deploymentEnvironment?: DeploymentEnvironment,
): void {
  const client = new SupervisionApiClient(
    defaultAuthProvider,
    fetch.bind(globalThis),
    apiBaseUrl,
  );
  createRoot(rootEl).render(
    <StrictMode>
      <App client={client} deploymentEnvironment={deploymentEnvironment} />
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

  // Embedded compatibility: same-origin worker; pairing enforcement not required.
  if (config.deliveryMode === "embedded") {
    renderApp("");
    return;
  }

  // Separated mode: narrow envLabel to a proven DeploymentEnvironment before pairing.
  // resolveOperatorUiConfig already rejects empty/invalid labels; this is TypeScript
  // narrowing + defensive fail-closed if the empty union member somehow remains.
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

  renderApp(config.apiBaseUrl, pairing.environment);
}

void bootstrap();
