/**
 * Runtime non-secret operator UI configuration (US-093 / US-094 / US-096 / BL-034).
 *
 * Separated UI only: config.js injects window.__SILVERMAN_OPERATOR_UI_CONFIG__ at
 * container start. Worker-embedded deliveryMode=embedded is decommissioned (US-096).
 */

export const OPERATOR_UI_API_BASE_URL_KEY = "SILVERMAN_OPERATOR_UI_API_BASE_URL";
export const OPERATOR_UI_ENV_LABEL_KEY = "SILVERMAN_OPERATOR_UI_ENV_LABEL";

/** Closed pairing vocabulary (US-094). */
export const DEPLOYMENT_ENVIRONMENTS = ["uat", "prod"] as const;
export type DeploymentEnvironment = (typeof DEPLOYMENT_ENVIRONMENTS)[number];

/** Supported production delivery after US-096 (embedded retired). */
export type OperatorUiDeliveryMode = "separated";

export interface OperatorUiRuntimeConfig {
  deliveryMode: OperatorUiDeliveryMode;
  /** Absolute worker origin required for separated UI. */
  apiBaseUrl: string;
  /** Required uat|prod for UI↔API pairing. */
  envLabel: DeploymentEnvironment;
}

export type OperatorUiConfigResult =
  | { ok: true; config: OperatorUiRuntimeConfig }
  | {
      ok: false;
      reason: "missing" | "invalid" | "pairing";
      message: string;
      requiredKeys: string[];
    };

declare global {
  interface Window {
    __SILVERMAN_OPERATOR_UI_CONFIG__?: {
      deliveryMode?: string;
      apiBaseUrl?: string;
      envLabel?: string;
    };
  }
}

/** Build-time delivery mode: separated UI image only (US-096). */
export function buildDeliveryMode(): OperatorUiDeliveryMode {
  return "separated";
}

export function isValidAbsoluteHttpUrl(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) {
    return false;
  }
  try {
    const url = new URL(trimmed);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      return false;
    }
    // Reject scheme-relative and empty hosts.
    if (!url.hostname) {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

/**
 * Normalize API base to origin form without a trailing slash (except root).
 * Paths on the worker are root-absolute (`/flow-a/...`).
 */
export function normalizeApiBaseUrl(value: string): string {
  const url = new URL(value.trim());
  // Drop any accidental path so route joins stay root-absolute on the worker.
  return url.origin;
}

/**
 * Join a root-relative worker path (may include query) with an API base.
 * Empty base is only for injectable unit tests; production config always fails
 * closed without an absolute base (resolveOperatorUiConfig).
 */
export function joinApiUrl(apiBaseUrl: string, path: string): string {
  if (!apiBaseUrl) {
    return path;
  }
  const base = apiBaseUrl.endsWith("/") ? apiBaseUrl : `${apiBaseUrl}/`;
  return new URL(path, base).toString();
}

export function normalizeDeploymentEnvironment(
  value: string,
): DeploymentEnvironment | null {
  const normalized = value.trim().toLowerCase();
  if (normalized === "uat" || normalized === "prod") {
    return normalized;
  }
  return null;
}

export function displayDeploymentEnvironment(
  env: DeploymentEnvironment,
): string {
  return env === "uat" ? "UAT" : "Prod";
}

export function resolveOperatorUiConfig(
  _deliveryMode: OperatorUiDeliveryMode = buildDeliveryMode(),
  windowConfig: Window["__SILVERMAN_OPERATOR_UI_CONFIG__"] | undefined = typeof window !==
  "undefined"
    ? window.__SILVERMAN_OPERATOR_UI_CONFIG__
    : undefined,
): OperatorUiConfigResult {
  const rawBase =
    typeof windowConfig?.apiBaseUrl === "string"
      ? windowConfig.apiBaseUrl.trim()
      : "";
  const rawEnvLabel =
    typeof windowConfig?.envLabel === "string" ? windowConfig.envLabel.trim() : "";

  if (!rawBase) {
    return {
      ok: false,
      reason: "missing",
      message:
        `Operator UI is blocked: set ${OPERATOR_UI_API_BASE_URL_KEY} to an absolute worker ` +
        `http(s) URL (for example http://192.168.0.194:8010). Relative same-origin API ` +
        `calls are disabled after US-096 (embedded worker console decommissioned).`,
      requiredKeys: [OPERATOR_UI_API_BASE_URL_KEY],
    };
  }

  if (!isValidAbsoluteHttpUrl(rawBase)) {
    return {
      ok: false,
      reason: "invalid",
      message:
        `Operator UI is blocked: ${OPERATOR_UI_API_BASE_URL_KEY} must be a valid absolute ` +
        `http or https URL (no secrets). Relative or malformed values are rejected.`,
      requiredKeys: [OPERATOR_UI_API_BASE_URL_KEY],
    };
  }

  if (!rawEnvLabel) {
    return {
      ok: false,
      reason: "missing",
      message:
        `Operator UI is blocked: set ${OPERATOR_UI_ENV_LABEL_KEY} to uat or prod so this ` +
        `console can pair with the matching worker API. Relative same-origin API calls ` +
        `remain disabled after US-096.`,
      requiredKeys: [OPERATOR_UI_ENV_LABEL_KEY],
    };
  }

  const envLabel = normalizeDeploymentEnvironment(rawEnvLabel);
  if (!envLabel) {
    return {
      ok: false,
      reason: "invalid",
      message:
        `Operator UI is blocked: ${OPERATOR_UI_ENV_LABEL_KEY} must be uat or prod ` +
        `(case-insensitive). Free-form labels are rejected.`,
      requiredKeys: [OPERATOR_UI_ENV_LABEL_KEY],
    };
  }

  return {
    ok: true,
    config: {
      deliveryMode: "separated",
      apiBaseUrl: normalizeApiBaseUrl(rawBase),
      envLabel,
    },
  };
}
