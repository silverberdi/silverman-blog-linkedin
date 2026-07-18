import type { SupervisionSnapshot } from "../models/supervision";

/**
 * Status summary scaffold — counts/issues from the shared model.
 */
export function StatusSummary({
  snapshot,
}: {
  snapshot: SupervisionSnapshot | null;
}) {
  if (!snapshot) {
    return (
      <p className="meta" data-testid="status-summary">
        Supply your worker API key when prompted. It stays in memory only for
        this page session and is never embedded in this page or browser storage.
      </p>
    );
  }
  return (
    <p className="meta" data-testid="status-summary">
      Observed {snapshot.observedAtUtc || "(unknown)"} · status=
      {snapshot.status} · read_only={String(snapshot.readOnly)} · pending=
      {snapshot.items.length} · integration_failures=
      {snapshot.integrationFailures.length}
    </p>
  );
}
