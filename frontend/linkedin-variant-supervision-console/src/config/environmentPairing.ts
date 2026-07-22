/**
 * US-094: separated UI ↔ worker API environment pairing.
 *
 * After base-URL + env-label validation, compare UI label to
 * GET {apiBaseUrl}/health deployment_environment. Fail closed on mismatch
 * or unreadable identity — no authenticated API use and no relative fallback.
 */

import {
  OPERATOR_UI_API_BASE_URL_KEY,
  OPERATOR_UI_ENV_LABEL_KEY,
  joinApiUrl,
  normalizeDeploymentEnvironment,
  type DeploymentEnvironment,
  type OperatorUiConfigResult,
} from "./operatorUiConfig";

const WORKER_DEPLOYMENT_ENVIRONMENT_KEY = "SILVERMAN_DEPLOYMENT_ENVIRONMENT";

export type EnvironmentPairingResult =
  | { ok: true; environment: DeploymentEnvironment }
  | Extract<OperatorUiConfigResult, { ok: false }>;

/**
 * Unauthenticated health read + environment agreement check.
 * Does not send Authorization — pairing must not depend on Bearer paste.
 */
export async function validateApiEnvironmentPairing(
  apiBaseUrl: string,
  envLabel: DeploymentEnvironment,
  fetchImpl: typeof fetch = fetch.bind(globalThis),
): Promise<EnvironmentPairingResult> {
  const healthUrl = joinApiUrl(apiBaseUrl, "/health");
  let response: Response;
  try {
    response = await fetchImpl(healthUrl, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
  } catch {
    return {
      ok: false,
      reason: "pairing",
      message:
        `Operator UI is blocked: could not reach worker health at the configured ` +
        `${OPERATOR_UI_API_BASE_URL_KEY} origin to verify environment pairing. ` +
        `Check network/CORS and that the worker advertises ${WORKER_DEPLOYMENT_ENVIRONMENT_KEY}.`,
      requiredKeys: [
        OPERATOR_UI_API_BASE_URL_KEY,
        OPERATOR_UI_ENV_LABEL_KEY,
        WORKER_DEPLOYMENT_ENVIRONMENT_KEY,
      ],
    };
  }

  if (!response.ok) {
    return {
      ok: false,
      reason: "pairing",
      message:
        `Operator UI is blocked: worker health returned HTTP ${response.status}. ` +
        `Environment pairing cannot proceed without a readable deployment_environment.`,
      requiredKeys: [
        OPERATOR_UI_API_BASE_URL_KEY,
        WORKER_DEPLOYMENT_ENVIRONMENT_KEY,
      ],
    };
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return {
      ok: false,
      reason: "pairing",
      message:
        `Operator UI is blocked: worker health response was not JSON, so ` +
        `deployment_environment could not be read for pairing.`,
      requiredKeys: [WORKER_DEPLOYMENT_ENVIRONMENT_KEY],
    };
  }

  const raw =
    body &&
    typeof body === "object" &&
    "deployment_environment" in body &&
    typeof (body as { deployment_environment: unknown }).deployment_environment ===
      "string"
      ? (body as { deployment_environment: string }).deployment_environment
      : "";

  const apiEnvironment = normalizeDeploymentEnvironment(raw);
  if (!apiEnvironment) {
    return {
      ok: false,
      reason: "pairing",
      message:
        `Operator UI is blocked: worker health is missing a valid deployment_environment ` +
        `(uat or prod). Set ${WORKER_DEPLOYMENT_ENVIRONMENT_KEY} on the worker to match ` +
        `${OPERATOR_UI_ENV_LABEL_KEY}.`,
      requiredKeys: [
        OPERATOR_UI_ENV_LABEL_KEY,
        WORKER_DEPLOYMENT_ENVIRONMENT_KEY,
      ],
    };
  }

  if (apiEnvironment !== envLabel) {
    return {
      ok: false,
      reason: "pairing",
      message:
        `Operator UI is blocked: UI environment (${OPERATOR_UI_ENV_LABEL_KEY}=${envLabel}) ` +
        `does not match API deployment_environment (${apiEnvironment}). ` +
        `Align ${OPERATOR_UI_ENV_LABEL_KEY}, ${OPERATOR_UI_API_BASE_URL_KEY}, and ` +
        `${WORKER_DEPLOYMENT_ENVIRONMENT_KEY} — no cross-environment API use is allowed.`,
      requiredKeys: [
        OPERATOR_UI_ENV_LABEL_KEY,
        OPERATOR_UI_API_BASE_URL_KEY,
        WORKER_DEPLOYMENT_ENVIRONMENT_KEY,
      ],
    };
  }

  return { ok: true, environment: envLabel };
}
