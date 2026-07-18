/**
 * Operator-facing API error mapping for 401/403/5xx/422 and known US-017 codes.
 * Secrets must never appear in messages or logs.
 */

export const SUPERVISION_ERROR_MESSAGES: Record<string, string> = {
  linkedin_supervision_variant_not_pending:
    "Variant is no longer in the pending supervision window. Reload the list.",
  linkedin_supervision_defer_time_invalid:
    "New schedule must be strictly in the future (UTC).",
  linkedin_supervision_defer_duplicate_slot:
    "Another variant in this campaign already uses that exact schedule instant.",
  linkedin_supervision_defer_saturation:
    "Interim cadence: another campaign variant is already on that UTC day within 72h.",
  linkedin_supervision_edit_unchanged:
    "Draft content is unchanged or empty after normalize. Edit was not applied.",
  linkedin_supervision_idempotency_conflict:
    "Idempotency conflict: same key with a different payload.",
  linkedin_supervision_action_not_allowed:
    "Action is not allowed for the current variant state.",
  linkedin_publish_cancel_not_allowed:
    "Cancel is not allowed for this variant state (for example already published).",
  calendar_item_not_found: "Calendar item was not found.",
  calendar_schedule_time_invalid:
    "New calendar due time must be canonical UTC Z and strictly in the future.",
  calendar_schedule_duplicate_slot:
    "Another blog calendar item already occupies that UTC day (interim 1/day).",
  calendar_schedule_saturation:
    "Target UTC day is saturated under interim blog density rules.",
  calendar_schedule_unsupported_state:
    "Calendar item status does not allow schedule mutation (published/historical).",
  calendar_schedule_idempotency_conflict:
    "Calendar schedule idempotency conflict: same key with a different payload.",
  calendar_completion_concurrent_update:
    "Calendar changed concurrently. Reload and retry the schedule update.",
};

export type ApiErrorKind =
  | "unauthorized"
  | "forbidden"
  | "mutation_denied"
  | "validation"
  | "business"
  | "http"
  | "network"
  | "auth_missing";

export interface ApiError {
  kind: ApiErrorKind;
  message: string;
  httpStatus?: number;
  codes: string[];
}

export function explainErrorCodes(codes: string[]): string {
  if (!codes.length) {
    return "Request failed without a structured error code.";
  }
  return codes
    .map((code) => {
      const known = SUPERVISION_ERROR_MESSAGES[code];
      return known ? `${code} — ${known}` : code;
    })
    .join("; ");
}

export function unauthorizedError(): ApiError {
  return {
    kind: "unauthorized",
    message:
      "Unauthorized (401). Session expired or credential rejected. Sign in again and retry.",
    httpStatus: 401,
    codes: [],
  };
}

export function forbiddenError(): ApiError {
  return {
    kind: "forbidden",
    message:
      "Forbidden (403). Authenticated but not authorized for this action. This is not a successful schedule or content change.",
    httpStatus: 403,
    codes: [],
  };
}

export function mutationDeniedError(): ApiError {
  return {
    kind: "mutation_denied",
    message:
      "Read-only session: edit, defer, cancel, and calendar schedule-update are not allowed.",
    codes: [],
  };
}

export function validationError(detail: string): ApiError {
  return {
    kind: "validation",
    message: detail || "Validation failed (422).",
    httpStatus: 422,
    codes: [],
  };
}

export function businessFailureError(codes: string[]): ApiError {
  return {
    kind: "business",
    message: explainErrorCodes(codes),
    codes,
  };
}

export function httpError(status: number): ApiError {
  if (status >= 500) {
    return {
      kind: "http",
      message: `Service unavailable (HTTP ${status}). The worker did not complete the request.`,
      httpStatus: status,
      codes: [],
    };
  }
  return {
    kind: "http",
    message: `Request failed with HTTP ${status}`,
    httpStatus: status,
    codes: [],
  };
}

export function networkError(reason: string): ApiError {
  return {
    kind: "network",
    message:
      reason ||
      "Network request failed. Service unavailable — distinct from missing authentication.",
    codes: [],
  };
}

export function authMissingError(context: "load" | "mutate"): ApiError {
  return {
    kind: "auth_missing",
    message:
      context === "load"
        ? "Authentication required. Sign in to load pending supervision or schedule visibility."
        : "Authentication required before submitting an edit, defer, cancel, or calendar schedule-update.",
    codes: [],
  };
}

/** Parse FastAPI 422 detail into a short operator message (no secrets). */
export function format422Detail(body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return `Validation failed (422): ${detail}`;
    }
    if (Array.isArray(detail)) {
      const parts = detail
        .map((item) => {
          if (item && typeof item === "object" && "msg" in item) {
            return String((item as { msg: unknown }).msg);
          }
          return null;
        })
        .filter(Boolean);
      if (parts.length) {
        return `Validation failed (422): ${parts.join("; ")}`;
      }
    }
  }
  return "Validation failed (422).";
}
