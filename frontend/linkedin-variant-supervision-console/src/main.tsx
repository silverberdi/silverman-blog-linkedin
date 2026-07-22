import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { SupervisionApiClient } from "./api/client";
import { defaultAuthProvider } from "./api/auth";
import { ConfigBlockedScreen } from "./components/ConfigBlockedScreen";
import { validateApiEnvironmentPairing } from "./config/environmentPairing";
import {
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

  // Separated mode: env label already validated; confirm API advertises the same.
  const pairing = await validateApiEnvironmentPairing(
    config.apiBaseUrl,
    config.envLabel,
  );
  if (!pairing.ok) {
    renderBlocked(pairing);
    return;
  }

  renderApp(config.apiBaseUrl, pairing.environment);
}

void bootstrap();
