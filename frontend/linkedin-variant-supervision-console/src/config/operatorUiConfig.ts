/**
 * Runtime non-secret operator UI configuration (US-093 / US-094 / US-096 / US-099 / BL-034).
 *
 * Separated UI only: config.js injects window.__SILVERMAN_OPERATOR_UI_CONFIG__ at
 * container start. Worker-embedded deliveryMode=embedded is decommissioned (US-096).
 *
 * US-099 front-only public topology: set apiBaseUrl to `/` or `same-origin` so the
 * browser uses a same-origin private hop (nginx proxies typed-client + /auth/* to
 * the private worker). Absolute LAN worker origins remain valid for non-tunnel use.
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
  /**
   * Absolute worker origin, or empty string for same-origin private hop (US-099).
   * Empty means relative typed-client paths on the UI origin (proxied privately).
   */
  apiBaseUrl: string;
  /** Required uat|prod for UI↔API pairing. */
  envLabel: DeploymentEnvironment;
  /**
   * When true, default AuthProvider is Google OIDC (US-097).
   * Non-secret flag only — never embed client secrets here.
   */
  googleAuthEnabled: boolean;
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
      googleAuthEnabled?: boolean | string;
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
 * US-099 same-origin private hop: `/` or `same-origin` (case-insensitive).
 * Empty remains "missing" so misconfigured LAN stacks still fail closed.
 */
export function isSameOriginApiBase(value: string): boolean {
  const trimmed = value.trim().toLowerCase();
  return trimmed === "/" || trimmed === "same-origin";
}

/**
 * Normalize API base to origin form without a trailing slash (except root).
 * Paths on the worker are root-absolute (`/flow-a/...`).
 * Same-origin private hop normalizes to empty string for relative joins.
 */
export function normalizeApiBaseUrl(value: string): string {
  if (isSameOriginApiBase(value)) {
    return "";
  }
  const url = new URL(value.trim());
  // Drop any accidental path so route joins stay root-absolute on the worker.
  return url.origin;
}

/**
 * Join a root-relative worker path (may include query) with an API base.
 * Empty base = same-origin private hop (US-099) or injectable unit tests —
 * returns the root-relative path so the browser stays on the UI origin.
 */
export function joinApiUrl(apiBaseUrl: string, path: string): string {
  if (!apiBaseUrl) {
    return path.startsWith("/") ? path : `/${path}`;
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

export function parseGoogleAuthEnabledFlag(
  value: boolean | string | undefined,
): boolean {
  if (typeof value === "boolean") {
    return value;
  }
  if (typeof value !== "string") {
    return false;
  }
  const normalized = value.trim().toLowerCase();
  return normalized === "1" || normalized === "true" || normalized === "yes";
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
  const googleAuthEnabled = parseGoogleAuthEnabledFlag(
    windowConfig?.googleAuthEnabled,
  );

  if (!rawBase) {
    return {
      ok: false,
      reason: "missing",
      message:
        `Operator UI is blocked: set ${OPERATOR_UI_API_BASE_URL_KEY} to an absolute worker ` +
        `http(s) URL (for example http://192.168.0.194:8010), or to / (same-origin private ` +
        `hop for US-099 front-only public UI). Empty values are rejected.`,
      requiredKeys: [OPERATOR_UI_API_BASE_URL_KEY],
    };
  }

  const sameOriginHop = isSameOriginApiBase(rawBase);
  if (!sameOriginHop && !isValidAbsoluteHttpUrl(rawBase)) {
    return {
      ok: false,
      reason: "invalid",
      message:
        `Operator UI is blocked: ${OPERATOR_UI_API_BASE_URL_KEY} must be a valid absolute ` +
        `http or https URL, or / (same-origin private hop). Malformed values are rejected.`,
      requiredKeys: [OPERATOR_UI_API_BASE_URL_KEY],
    };
  }

  if (!rawEnvLabel) {
    return {
      ok: false,
      reason: "missing",
      message:
        `Operator UI is blocked: set ${OPERATOR_UI_ENV_LABEL_KEY} to uat or prod so this ` +
        `console can pair with the matching worker API.`,
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
      apiBaseUrl: sameOriginHop ? "" : normalizeApiBaseUrl(rawBase),
      envLabel,
      googleAuthEnabled,
    },
  };
}
