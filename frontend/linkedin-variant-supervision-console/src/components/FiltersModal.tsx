import { useEffect, useId, useRef } from "react";
import { Filters } from "./Filters";

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Filters modal (US-040L) — hosts existing Filters controls with EventModal-aligned a11y.
 * Closing MUST NOT clear shared filter state.
 */
export function FiltersModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open || !dialogRef.current) {
      return;
    }
    closeBtnRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        onClose();
        return;
      }
      if (event.key !== "Tab" || !dialogRef.current) {
        return;
      }
      const focusables = Array.from(
        dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
      ).filter((el) => el.offsetParent !== null || el === document.activeElement);
      if (focusables.length === 0) {
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      if (event.shiftKey) {
        if (document.activeElement === first) {
          event.preventDefault();
          last.focus();
        }
      } else if (document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <div className="filters-modal-root" data-testid="filters-modal-root">
      <button
        type="button"
        className="filters-modal-backdrop"
        data-testid="filters-modal-backdrop"
        aria-label="Close filters modal"
        onClick={onClose}
      />
      <div
        ref={dialogRef}
        className="filters-modal"
        data-testid="filters-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="filters-modal-header drawer-header">
          <div>
            <p className="eyebrow">Focus</p>
            <h2 id={titleId}>Filters</h2>
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            className="secondary"
            data-testid="filters-modal-close"
            onClick={onClose}
          >
            Close
          </button>
        </div>
        <div className="filters-modal-body">
          <Filters />
        </div>
      </div>
    </div>
  );
}
