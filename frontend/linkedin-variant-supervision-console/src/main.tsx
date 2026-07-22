import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { SupervisionApiClient } from "./api/client";
import { defaultAuthProvider } from "./api/auth";
import { ConfigBlockedScreen } from "./components/ConfigBlockedScreen";
import { resolveOperatorUiConfig } from "./config/operatorUiConfig";
import "./styles/console.css";

const rootEl = document.getElementById("root")!;
const configResult = resolveOperatorUiConfig();

if (!configResult.ok) {
  createRoot(rootEl).render(
    <StrictMode>
      <ConfigBlockedScreen result={configResult} />
    </StrictMode>,
  );
} else {
  const client = new SupervisionApiClient(
    defaultAuthProvider,
    fetch.bind(globalThis),
    configResult.config.apiBaseUrl,
  );
  createRoot(rootEl).render(
    <StrictMode>
      <App client={client} />
    </StrictMode>,
  );
}
