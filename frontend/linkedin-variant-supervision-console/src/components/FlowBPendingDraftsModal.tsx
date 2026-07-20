import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { ApiError } from "../api/errors";
import type {
  FlowBDraftDecisionResponse,
  FlowBPendingDraftDetail,
  FlowBPendingDraftSummary,
  FlowBPromoteDraftResponse,
} from "../api/types";
import { useSupervisionStore } from "../models/store";

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function formatApiError(err: unknown): string {
  const apiErr = err as ApiError | undefined;
  if (apiErr?.kind === "validation") {
    return apiErr.message || "Validation failed.";
  }
  if (apiErr?.kind === "unauthorized" || apiErr?.kind === "auth_missing") {
    return "Sign in required to review Flow B drafts.";
  }
  if (apiErr?.kind === "forbidden" || apiErr?.kind === "mutation_denied") {
    return "This session cannot approve, reject, or promote drafts.";
  }
  if (apiErr?.message) {
    return apiErr.message;
  }
  return "Unable to load or update Flow B drafts.";
}

function statusLabel(status: string): string {
  switch (status) {
    case "pending_approval":
      return "Pending approval";
    case "pending_approval_image_failed":
      return "Pending (image failed)";
    case "approved":
      return "Approved (not promoted)";
    case "promoted":
      return "Promoted (Flow A eligible)";
    case "rejected":
      return "Rejected / blocked";
    default:
      return status;
  }
}

/**
 * Flow B pending-approval drafts panel (US-080/US-081) — Authority Manager surface.
 * Approve records decision only; Promote moves to ready/. No revision CMS.
 */
export function FlowBPendingDraftsModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const {
    canMutate,
    sessionState,
    signIn,
    client,
    dryRunDefault,
  } = useSupervisionStore();

  const [loading, setLoading] = useState(false);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<FlowBPendingDraftSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<FlowBPendingDraftDetail | null>(null);
  const [imageObjectUrl, setImageObjectUrl] = useState<string | null>(null);
  const [rejectionReason, setRejectionReason] = useState("");

  const revokeImageUrl = useCallback(() => {
    setImageObjectUrl((prev) => {
      if (prev) {
        URL.revokeObjectURL(prev);
      }
      return null;
    });
  }, []);

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.listPendingApprovalDrafts();
      setDrafts(response.drafts);
      if (response.drafts.length === 0) {
        setSelectedId(null);
        setDetail(null);
        revokeImageUrl();
      } else if (
        !selectedId ||
        !response.drafts.some((d) => d.draft_id === selectedId)
      ) {
        setSelectedId(response.drafts[0].draft_id);
      }
    } catch (err) {
      setDrafts([]);
      setDetail(null);
      revokeImageUrl();
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [client, revokeImageUrl, selectedId]);

  const loadDetail = useCallback(
    async (draftId: string) => {
      setLoading(true);
      setError(null);
      revokeImageUrl();
      try {
        const response = await client.getPendingApprovalDraft(draftId);
        setDetail(response);
        if (response.image_url) {
          try {
            const blob = await client.fetchPendingApprovalDraftImage(draftId);
            setImageObjectUrl(URL.createObjectURL(blob));
          } catch {
            // Image optional for review when image_failed
          }
        }
      } catch (err) {
        setDetail(null);
        setError(formatApiError(err));
      } finally {
        setLoading(false);
      }
    },
    [client, revokeImageUrl],
  );

  useEffect(() => {
    if (!open) {
      return;
    }
    setOutcome(null);
    setRejectionReason("");
    void loadList();
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps -- load once per open

  useEffect(() => {
    if (!open || !selectedId) {
      return;
    }
    void loadDetail(selectedId);
  }, [open, selectedId, loadDetail]);

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

  useEffect(() => {
    return () => {
      if (imageObjectUrl) {
        URL.revokeObjectURL(imageObjectUrl);
      }
    };
  }, [imageObjectUrl]);

  function applyDecisionOutcome(result: FlowBDraftDecisionResponse) {
    if (result.status === "approved") {
      const dry = result.dry_run ? " (dry-run — not saved)" : "";
      setOutcome(
        `Approved${dry}. Still not Flow A eligible — use Promote to move to ready/. ` +
          (result.operator_note || ""),
      );
    } else if (result.status === "rejected") {
      const dry = result.dry_run ? " (dry-run — not saved)" : "";
      setOutcome(
        `Rejected / blocked${dry}. Draft remains non-publishable under pending-approval/.`,
      );
    } else {
      setOutcome(result.error || result.operator_note || "Decision recorded.");
    }
  }

  function applyPromoteOutcome(result: FlowBPromoteDraftResponse) {
    if (result.status === "promoted") {
      const dry = result.dry_run ? " (dry-run — not moved)" : "";
      const already = result.already_promoted ? " Already promoted." : "";
      setOutcome(
        `Promoted to ready/${dry}.${already} Flow A eligible — does not publish blog or LinkedIn. ` +
          (result.operator_note || ""),
      );
    } else {
      setOutcome(result.error || result.operator_note || "Promote failed.");
    }
  }

  async function onApprove() {
    if (!selectedId || !canMutate) {
      return;
    }
    setMutating(true);
    setError(null);
    setOutcome(null);
    try {
      const result = await client.approvePendingApprovalDraft(selectedId, {
        dry_run: dryRunDefault,
      });
      applyDecisionOutcome(result);
      if (!result.dry_run) {
        await loadList();
        await loadDetail(selectedId);
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setMutating(false);
    }
  }

  async function onReject() {
    if (!selectedId || !canMutate) {
      return;
    }
    setMutating(true);
    setError(null);
    setOutcome(null);
    try {
      const result = await client.rejectPendingApprovalDraft(selectedId, {
        dry_run: dryRunDefault,
        rejection_reason: rejectionReason.trim() || undefined,
      });
      applyDecisionOutcome(result);
      if (!result.dry_run) {
        await loadList();
        setSelectedId(null);
        setDetail(null);
        revokeImageUrl();
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setMutating(false);
    }
  }

  async function onPromote() {
    if (!selectedId || !canMutate) {
      return;
    }
    setMutating(true);
    setError(null);
    setOutcome(null);
    try {
      const result = await client.promotePendingApprovalDraft(selectedId, {
        dry_run: dryRunDefault,
      });
      applyPromoteOutcome(result);
      if (!result.dry_run && result.promoted) {
        await loadList();
        setSelectedId(null);
        setDetail(null);
        revokeImageUrl();
      }
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setMutating(false);
    }
  }

  if (!open) {
    return null;
  }

  const needsReauth =
    sessionState === "anonymous" ||
    sessionState === "expired" ||
    sessionState === "forbidden";

  const canApproveReject =
    detail &&
    (detail.status === "pending_approval" ||
      detail.status === "pending_approval_image_failed" ||
      detail.status === "approved");

  const canPromote = detail && detail.status === "approved";

  return (
    <div className="filters-modal-root" data-testid="flow-b-drafts-modal-root">
      <button
        type="button"
        className="filters-modal-backdrop"
        data-testid="flow-b-drafts-modal-backdrop"
        aria-label="Close Flow B drafts modal"
        onClick={onClose}
      />
      <div
        ref={dialogRef}
        className="filters-modal flow-b-drafts-modal"
        data-testid="flow-b-drafts-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <div className="filters-modal-header drawer-header">
          <h2 id={titleId}>Flow B drafts</h2>
          <button
            ref={closeBtnRef}
            type="button"
            className="icon-button"
            data-testid="flow-b-drafts-close"
            aria-label="Close"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <p className="note" data-testid="flow-b-drafts-scope-note">
          Review pending AI blogs for approve or reject. Approve records a
          decision only. Promote moves an approved draft to ready/ (Flow A
          eligible) — it does not publish. Offline file edits remain out of
          band; there is no revision-history CMS or mandatory edit-apply loop.
        </p>

        {needsReauth && (
          <p className="note">
            Sign in to load drafts.{" "}
            <button
              type="button"
              data-testid="flow-b-drafts-sign-in"
              onClick={() => void signIn()}
            >
              Sign in
            </button>
          </p>
        )}

        {error && (
          <p className="form-error" data-testid="flow-b-drafts-error" role="alert">
            {error}
          </p>
        )}
        {outcome && (
          <p
            className="flow-b-drafts-outcome"
            data-testid="flow-b-drafts-outcome"
            role="status"
          >
            {outcome}
          </p>
        )}

        <div className="flow-b-drafts-layout">
          <aside className="flow-b-drafts-list" data-testid="flow-b-drafts-list">
            <div className="drawer-actions">
              <button
                type="button"
                className="secondary"
                data-testid="flow-b-drafts-refresh"
                disabled={loading}
                onClick={() => void loadList()}
              >
                Refresh
              </button>
            </div>
            {loading && drafts.length === 0 && (
              <p className="note" data-testid="flow-b-drafts-loading">
                Loading…
              </p>
            )}
            {!loading && drafts.length === 0 && (
              <p className="note" data-testid="flow-b-drafts-empty">
                No pending drafts in pending-approval/.
              </p>
            )}
            <ul>
              {drafts.map((draft) => (
                <li key={draft.draft_id}>
                  <button
                    type="button"
                    className={
                      draft.draft_id === selectedId
                        ? "flow-b-drafts-list-item is-selected"
                        : "flow-b-drafts-list-item"
                    }
                    data-testid={`flow-b-draft-item-${draft.draft_id}`}
                    onClick={() => setSelectedId(draft.draft_id)}
                  >
                    <span className="flow-b-drafts-item-title">{draft.title}</span>
                    <span className="flow-b-drafts-item-status">
                      {statusLabel(draft.status)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          <section
            className="flow-b-drafts-detail"
            data-testid="flow-b-drafts-detail"
            aria-live="polite"
          >
            {!detail && !loading && (
              <p className="note">Select a draft to review.</p>
            )}
            {detail && (
              <>
                <h3 data-testid="flow-b-drafts-title">{detail.title}</h3>
                <p
                  className={`flow-b-drafts-status-chip status-${detail.status}`}
                  data-testid="flow-b-drafts-status"
                >
                  {statusLabel(detail.status)}
                </p>
                {detail.image_warning && (
                  <p
                    className="note"
                    data-testid="flow-b-drafts-image-warning"
                  >
                    {detail.image_warning}
                  </p>
                )}

                <dl className="flow-b-drafts-discovery" data-testid="flow-b-drafts-discovery">
                  <div>
                    <dt>Topic</dt>
                    <dd>{detail.topic_id || "—"}</dd>
                  </div>
                  <div>
                    <dt>Thesis</dt>
                    <dd>{detail.thesis || "—"}</dd>
                  </div>
                  <div>
                    <dt>Referent positioning</dt>
                    <dd>{detail.referent_positioning || "—"}</dd>
                  </div>
                  <div>
                    <dt>Rationale</dt>
                    <dd>{detail.rationale || "—"}</dd>
                  </div>
                  {detail.target_week && (
                    <div data-testid="flow-b-drafts-gap-week">
                      <dt>Gap week</dt>
                      <dd>{detail.target_week}</dd>
                    </div>
                  )}
                  {detail.empty_days && detail.empty_days.length > 0 && (
                    <div data-testid="flow-b-drafts-empty-days">
                      <dt>Empty days</dt>
                      <dd>{detail.empty_days.join(", ")}</dd>
                    </div>
                  )}
                </dl>

                {imageObjectUrl && (
                  <figure className="flow-b-drafts-image" data-testid="flow-b-drafts-image">
                    <img src={imageObjectUrl} alt="" />
                  </figure>
                )}

                <pre
                  className="flow-b-drafts-body"
                  data-testid="flow-b-drafts-body"
                >
                  {detail.body_markdown}
                </pre>

                {(canApproveReject || canPromote) && (
                  <div className="flow-b-drafts-actions" data-testid="flow-b-drafts-actions">
                    <p className="note" data-testid="flow-b-drafts-dry-run-hint">
                      Mutations use the shell {dryRunDefault ? "Dry-run" : "Commit"}{" "}
                      mode.
                    </p>
                    {canApproveReject && (
                      <label className="field">
                        Reject reason (optional)
                        <input
                          type="text"
                          data-testid="flow-b-drafts-reject-reason"
                          value={rejectionReason}
                          onChange={(e) => setRejectionReason(e.target.value)}
                          maxLength={2000}
                          disabled={!canMutate || mutating}
                        />
                      </label>
                    )}
                    <div className="drawer-actions">
                      {canApproveReject && (
                        <button
                          type="button"
                          data-testid="flow-b-drafts-approve"
                          disabled={!canMutate || mutating}
                          onClick={() => void onApprove()}
                        >
                          Approve
                        </button>
                      )}
                      {canPromote && (
                        <button
                          type="button"
                          data-testid="flow-b-drafts-promote"
                          disabled={!canMutate || mutating}
                          onClick={() => void onPromote()}
                        >
                          Promote to ready/
                        </button>
                      )}
                      {canApproveReject && (
                        <button
                          type="button"
                          className="secondary"
                          data-testid="flow-b-drafts-reject"
                          disabled={!canMutate || mutating}
                          onClick={() => void onReject()}
                        >
                          Reject
                        </button>
                      )}
                    </div>
                  </div>
                )}
                {detail.status === "rejected" && (
                  <p
                    className="flow-b-drafts-rejected-banner"
                    data-testid="flow-b-drafts-rejected-banner"
                    role="status"
                  >
                    Rejected / blocked
                    {detail.rejection_reason
                      ? `: ${detail.rejection_reason}`
                      : ""}
                    . Not publishable — not promoted to ready/.
                  </p>
                )}
                {detail.status === "approved" && (
                  <p
                    className="note"
                    data-testid="flow-b-drafts-approved-not-promoted"
                    role="status"
                  >
                    Approved but not promoted — not Flow A eligible until
                    Promote moves the package to blog-posts/ready/.
                  </p>
                )}
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
