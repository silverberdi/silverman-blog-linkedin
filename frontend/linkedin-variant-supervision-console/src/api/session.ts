/**
 * Operator-facing session states (US-040D).
 *
 * Derived at the auth/client boundary — list / calendar / ScheduleEditor
 * consume capabilities and banners, not raw HTTP status parsing.
 */

import type { ApiError } from "./errors";

export type SessionState =
  | "anonymous"
  | "authenticated"
  | "expired"
  | "forbidden"
  | "service_unavailable";

export interface SessionCapabilities {
  canRead: boolean;
  canMutate: boolean;
}

/** Operator copy for each session state (qualified language; no LinkedIn API published claim). */
export function sessionBannerText(state: SessionState): string {
  switch (state) {
    case "anonymous":
      return (
        "Not authenticated. Sign in with your worker API key for this browser " +
        "session to load pending / queued supervision data. Pending, cancelled, " +
        "flow_a_complete, and blog handoff are not LinkedIn API published."
      );
    case "authenticated":
      return (
        "Authenticated for this browser session. Mutations use worker HTTP only " +
        "(ADR-0001). Pending, queued, cancelled, flow_a_complete, and blog " +
        "handoff are not LinkedIn API published."
      );
    case "expired":
      return (
        "Session expired (unauthorized). Visible list/calendar context may be " +
        "stale. Sign in again to continue. Unsaved schedule drafts are kept in " +
        "memory — they are not discarded by expiry alone."
      );
    case "forbidden":
      return (
        "Forbidden (not authorized for this action). Your credential was " +
        "accepted for identity but the worker rejected authorization. This is " +
        "not a successful schedule or content change."
      );
    case "service_unavailable":
      return (
        "Service unavailable: the worker did not respond successfully " +
        "(network failure or HTTP 5xx). This is distinct from missing or " +
        "expired authentication. Retry after the worker is reachable."
      );
    default: {
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}

export function sessionBannerKind(
  state: SessionState,
): "info" | "ok" | "warn" | "error" {
  switch (state) {
    case "authenticated":
      return "ok";
    case "anonymous":
      return "info";
    case "expired":
    case "forbidden":
      return "warn";
    case "service_unavailable":
      return "error";
    default: {
      const _exhaustive: never = state;
      return _exhaustive;
    }
  }
}

/**
 * Map a typed API error to a session state.
 * Returns null when the error is not session-related (e.g. 422 validation).
 */
export function sessionStateFromApiError(err: ApiError): SessionState | null {
  switch (err.kind) {
    case "auth_missing":
      return "anonymous";
    case "unauthorized":
      return "expired";
    case "forbidden":
      return "forbidden";
    case "mutation_denied":
      // Read-only capability — keep authenticated identity if already signed in;
      // caller decides whether to change session. Prefer leaving session alone.
      return null;
    case "network":
      return "service_unavailable";
    case "http":
      if (err.httpStatus != null && err.httpStatus >= 500) {
        return "service_unavailable";
      }
      return null;
    default:
      return null;
  }
}

/** Effective UI capabilities from provider + session. */
export function effectiveCapabilities(
  providerCanRead: boolean,
  providerCanMutate: boolean,
  session: SessionState,
): SessionCapabilities {
  if (session === "anonymous" || session === "expired") {
    return { canRead: false, canMutate: false };
  }
  if (session === "forbidden") {
    return { canRead: providerCanRead, canMutate: false };
  }
  // authenticated or service_unavailable: honor provider capabilities
  return {
    canRead: providerCanRead,
    canMutate: providerCanMutate && session === "authenticated",
  };
}
