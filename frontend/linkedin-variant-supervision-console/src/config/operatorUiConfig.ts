/**
 * Runtime non-secret operator UI configuration (US-093 / BL-034 Story 1).
 *
 * Separated UI: config.js injects window.__SILVERMAN_OPERATOR_UI_CONFIG__ at
 * container start. Embedded worker console: deliveryMode=embedded (build-time)
 * and relative same-origin API paths remain valid.
 */

export const OPERATOR_UI_API_BASE_URL_KEY = "SILVERMAN_OPERATOR_UI_API_BASE_URL";
export const OPERATOR_UI_ENV_LABEL_KEY = "SILVERMAN_OPERATOR_UI_ENV_LABEL";

export type OperatorUiDeliveryMode = "separated" | "embedded";

export interface OperatorUiRuntimeConfig {
  deliveryMode: OperatorUiDeliveryMode;
  /** Absolute worker origin, or empty for embedded same-origin mode. */
  apiBaseUrl: string;
  /** Reserved for US-094 pairing display; unused for enforcement in US-093. */
  envLabel: string;
}

export type OperatorUiConfigResult =
  | { ok: true; config: OperatorUiRuntimeConfig }
  | {
      ok: false;
      reason: "missing" | "invalid";
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

/** Build-time delivery mode: standalone image = separated; worker static = embedded. */
export function buildDeliveryMode(): OperatorUiDeliveryMode {
  const raw = import.meta.env.VITE_OPERATOR_UI_DELIVERY;
  return raw === "embedded" ? "embedded" : "separated";
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
 * Join a root-relative worker path (may include query) with an optional API base.
 * Empty base ⇒ return path unchanged (embedded same-origin compatibility).
 */
export function joinApiUrl(apiBaseUrl: string, path: string): string {
  if (!apiBaseUrl) {
    return path;
  }
  const base = apiBaseUrl.endsWith("/") ? apiBaseUrl : `${apiBaseUrl}/`;
  return new URL(path, base).toString();
}

export function resolveOperatorUiConfig(
  deliveryMode: OperatorUiDeliveryMode = buildDeliveryMode(),
  windowConfig: Window["__SILVERMAN_OPERATOR_UI_CONFIG__"] | undefined = typeof window !==
  "undefined"
    ? window.__SILVERMAN_OPERATOR_UI_CONFIG__
    : undefined,
): OperatorUiConfigResult {
  if (deliveryMode === "embedded") {
    return {
      ok: true,
      config: {
        deliveryMode: "embedded",
        apiBaseUrl: "",
        envLabel: "",
      },
    };
  }

  const rawBase =
    typeof windowConfig?.apiBaseUrl === "string"
      ? windowConfig.apiBaseUrl.trim()
      : "";
  const envLabel =
    typeof windowConfig?.envLabel === "string" ? windowConfig.envLabel.trim() : "";

  if (!rawBase) {
    return {
      ok: false,
      reason: "missing",
      message:
        `Operator UI is blocked: set ${OPERATOR_UI_API_BASE_URL_KEY} to an absolute worker ` +
        `http(s) URL (for example http://192.168.0.194:8010). Relative same-origin API ` +
        `calls are disabled in separated-UI mode.`,
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

  return {
    ok: true,
    config: {
      deliveryMode: "separated",
      apiBaseUrl: normalizeApiBaseUrl(rawBase),
      envLabel,
    },
  };
}
