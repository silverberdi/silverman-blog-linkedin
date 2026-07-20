/**
 * Operator-facing API error mapping for 401/403/5xx/422 and known US-017 codes.
 * Secrets must never appear in messages or logs.
 */

export const SUPERVISION_ERROR_MESSAGES: Record<string, string> = {
  linkedin_supervision_variant_not_pending:
    "Cannot postpone this state. Only Scheduled (pending) or Waiting to send (queued) can be rescheduled — reload, or use reopen for cancelled.",
  linkedin_supervision_defer_time_invalid:
    "New schedule must be strictly after now in your local time. Pick a future time and try again.",
  linkedin_supervision_defer_duplicate_slot:
    "Another variant in this campaign already uses that exact schedule instant. Pick a different time.",
  linkedin_supervision_defer_saturation:
    "Interim cadence: another campaign variant is already scheduled that local day within 72h. Choose a different day or time outside that window.",
  linkedin_supervision_edit_unchanged:
    "Draft content is unchanged or empty after normalize. Edit was not applied.",
  linkedin_supervision_idempotency_conflict:
    "Idempotency conflict: same key with a different payload.",
  linkedin_supervision_action_not_allowed:
    "Action is not allowed for the current variant state. Reload the item, or use reopen if it is already Cancelled.",
  linkedin_publish_cancel_not_allowed:
    "Cancel is not allowed for this state (for example already Live on LinkedIn). Reload the item — Live posts cannot be cancelled from this console.",
  linkedin_reopen_not_allowed:
    "This cancelled variant cannot be reopened (recovery cancel or ineligible state). Use the recovery path when applicable — cancel remains irreversible except via reopen for eligible cancellations.",
  calendar_item_not_found: "Calendar item was not found.",
  calendar_schedule_time_invalid:
    "New calendar due time must be after now in your local time. Pick a future time and try again.",
  calendar_schedule_duplicate_slot:
    "Another blog calendar item already occupies that local day (interim 1/day). Choose another day.",
  calendar_schedule_saturation:
    "Target local day is saturated under interim blog density rules. Choose another day.",
  calendar_schedule_unsupported_state:
    "Calendar item status does not allow schedule mutation (published/historical).",
  calendar_schedule_idempotency_conflict:
    "Calendar schedule idempotency conflict: same key with a different payload.",
  calendar_completion_concurrent_update:
    "Calendar changed concurrently. Reload and retry the schedule update.",
  linkedin_supervision_local_day_density:
    "This day already has 2 publications. Choose another local day with capacity.",
  calendar_schedule_local_day_density:
    "This day already has 2 publications. Choose another local day with capacity.",
  operator_timezone_required:
    "Operator timezone is required. Schedule was not changed.",
  operator_timezone_invalid:
    "Operator timezone is invalid. Schedule was not changed.",
};

const DENSITY_CODES = new Set([
  "linkedin_supervision_local_day_density",
  "calendar_schedule_local_day_density",
]);

const LOCAL_DAY_FULL_PRIMARY =
  "This day already has 2 publications. Choose another local day with capacity.";

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

/**
 * Operator-facing explanation of worker error codes.
 * Density codes prefer the plain human sentence as the primary display
 * (raw codes remain available via ApiError.codes / diagnostics).
 */
export function explainErrorCodes(codes: string[]): string {
  if (!codes.length) {
    return "Request failed without a structured error code.";
  }
  if (codes.some((code) => DENSITY_CODES.has(code))) {
    const others = codes.filter((code) => !DENSITY_CODES.has(code));
    if (!others.length) {
      return LOCAL_DAY_FULL_PRIMARY;
    }
    const rest = others
      .map((code) => {
        const known = SUPERVISION_ERROR_MESSAGES[code];
        return known ? `${code} — ${known}` : code;
      })
      .join("; ");
    return `${LOCAL_DAY_FULL_PRIMARY} (${rest})`;
  }
  return codes
    .map((code) => {
      const known = SUPERVISION_ERROR_MESSAGES[code];
      return known ? `${code} — ${known}` : code;
    })
    .join("; ");
}

/** Plain-language primary toast text (density → full-day sentence). */
export function explainErrorCodesPlain(codes: string[]): string {
  if (!codes.length) {
    return "Request failed without a structured error code.";
  }
  if (codes.some((code) => DENSITY_CODES.has(code))) {
    return LOCAL_DAY_FULL_PRIMARY;
  }
  return explainErrorCodes(codes);
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
      "Read-only session: edit, defer, cancel, reopen, and calendar schedule-update are not allowed.",
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
        : "Authentication required before submitting an edit, defer, cancel, reopen, or calendar schedule-update.",
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
    if (
      detail &&
      typeof detail === "object" &&
      "errors" in detail &&
      Array.isArray((detail as { errors: unknown }).errors)
    ) {
      const parts = (detail as { errors: unknown[] }).errors
        .map((item) => {
          if (!item || typeof item !== "object") {
            return null;
          }
          const row = item as {
            field?: unknown;
            code?: unknown;
            message?: unknown;
          };
          if (typeof row.message === "string" && row.message.trim()) {
            return row.message;
          }
          if (typeof row.code === "string" && row.code.trim()) {
            return row.code;
          }
          return null;
        })
        .filter(Boolean);
      if (parts.length) {
        return `Validation failed (422): ${parts.join("; ")}`;
      }
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
