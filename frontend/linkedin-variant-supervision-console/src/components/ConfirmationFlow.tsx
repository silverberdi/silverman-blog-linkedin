/**
 * Confirmation for real (non-dry-run) mutations.
 * Matches Stories 1–3: dry-run default on; real writes require confirm.
 */
export function confirmRealMutation(actionLabel: string): boolean {
  if (typeof window === "undefined" || typeof window.confirm !== "function") {
    return false;
  }
  return window.confirm(
    `Make a real ${actionLabel} (not preview)? This will save campaign metadata. It does not publish live to LinkedIn.`,
  );
}

export function newIdempotencyKey(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `console-${Date.now()}-${Math.random().toString().slice(2, 10)}`;
}
