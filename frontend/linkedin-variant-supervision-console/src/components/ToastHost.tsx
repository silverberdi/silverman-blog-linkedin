import { useSupervisionStore, type ToastKind } from "../models/store";

function toastRole(kind: ToastKind): "status" | "alert" {
  return kind === "error" || kind === "warn" ? "alert" : "status";
}

/**
 * Fixed overlay toast host (US-040H). Does not push calendar document flow.
 */
export function ToastHost() {
  const { toasts, dismissToast } = useSupervisionStore();

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div
      className="toast-host"
      data-testid="toast-host"
      aria-live="polite"
      aria-relevant="additions text"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`toast toast-${toast.kind}`}
          data-testid="toast"
          data-toast-id={toast.id}
          data-toast-kind={toast.kind}
          role={toastRole(toast.kind)}
        >
          <p className="toast-text">{toast.text}</p>
          <button
            type="button"
            className="toast-dismiss"
            data-testid="toast-dismiss"
            aria-label="Dismiss notification"
            onClick={() => dismissToast(toast.id)}
          >
            Dismiss
          </button>
        </div>
      ))}
    </div>
  );
}
