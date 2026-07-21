import { FormEvent, useCallback, useEffect, useId, useRef, useState } from "react";
import type { ApiError } from "../api/errors";
import type {
  BacklogFormat,
  BacklogPriority,
  BacklogStatus,
  EditorialContentBacklogItem,
  EditorialContentBacklogWriteRequest,
  LinkedInDerivativeNote,
} from "../api/types";
import { useSupervisionStore } from "../models/store";

const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const FORMATS: BacklogFormat[] = ["blog", "linkedin", "both"];
const PRIORITIES: BacklogPriority[] = ["low", "medium", "high"];
const STATUSES: BacklogStatus[] = [
  "idea",
  "planned",
  "in_progress",
  "done",
  "dropped",
];

function emptyForm(): EditorialContentBacklogWriteRequest {
  return {
    topic: "",
    audience: "",
    objective: "",
    format: "both",
    priority: "medium",
    status: "idea",
    target_date: "",
    linkedin_derivatives: [
      { audience_hint: "", format_hint: "", notes: "" },
    ],
  };
}

function formFromItem(item: EditorialContentBacklogItem): EditorialContentBacklogWriteRequest {
  return {
    topic: item.topic,
    audience: item.audience,
    objective: item.objective,
    format: item.format,
    priority: item.priority,
    status: item.status,
    target_date: item.target_date ?? "",
    linkedin_derivatives:
      item.linkedin_derivatives.length > 0
        ? item.linkedin_derivatives.map((d) => ({ ...d }))
        : [{ audience_hint: "", format_hint: "", notes: "" }],
    expected_row_version: item.row_version,
  };
}

function formatApiError(err: unknown): string {
  const apiErr = err as ApiError | undefined;
  if (apiErr?.kind === "validation") {
    return apiErr.message || "Validation failed.";
  }
  if (apiErr?.kind === "unauthorized" || apiErr?.kind === "auth_missing") {
    return "Sign in required to load or save the content backlog.";
  }
  if (apiErr?.kind === "forbidden" || apiErr?.kind === "mutation_denied") {
    return "This session cannot create or edit backlog items.";
  }
  if (apiErr?.message) {
    return apiErr.message;
  }
  return "Unable to load or save the content backlog.";
}

/**
 * Editorial content backlog panel (US-049) — Authority Manager surface.
 * Optional enrichment only: save ≠ LinkedIn publish and ≠ Flow B trigger.
 */
export function ContentBacklogModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  const { canMutate, sessionState, signIn, client } = useSupervisionStore();

  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<string | null>(null);
  const [items, setItems] = useState<EditorialContentBacklogItem[]>([]);
  const [mode, setMode] = useState<"list" | "create" | "edit">("list");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<EditorialContentBacklogWriteRequest>(emptyForm());

  const needsReauth =
    sessionState === "anonymous" ||
    sessionState === "expired" ||
    sessionState === "forbidden";

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await client.listEditorialContentBacklog();
      setItems(response.items);
    } catch (err) {
      setItems([]);
      setError(formatApiError(err));
    } finally {
      setLoading(false);
    }
  }, [client]);

  useEffect(() => {
    if (!open) {
      return;
    }
    setMode("list");
    setEditingId(null);
    setForm(emptyForm());
    setOutcome(null);
    void loadList();
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps -- load once per open

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

  function startCreate() {
    setMode("create");
    setEditingId(null);
    setForm(emptyForm());
    setError(null);
    setOutcome(null);
  }

  function startEdit(item: EditorialContentBacklogItem) {
    setMode("edit");
    setEditingId(item.item_id);
    setForm(formFromItem(item));
    setError(null);
    setOutcome(null);
  }

  function backToList() {
    setMode("list");
    setEditingId(null);
    setForm(emptyForm());
    setError(null);
  }

  function updateDerivative(
    index: number,
    patch: Partial<LinkedInDerivativeNote>,
  ) {
    const next = [...(form.linkedin_derivatives ?? [])];
    next[index] = { ...next[index], ...patch };
    setForm({ ...form, linkedin_derivatives: next });
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!canMutate) {
      setError("Sign in with write permission to save backlog items.");
      return;
    }
    setSaving(true);
    setError(null);
    setOutcome(null);
    const payload: EditorialContentBacklogWriteRequest = {
      ...form,
      target_date: form.target_date?.trim() ? form.target_date.trim() : null,
      linkedin_derivatives: (form.linkedin_derivatives ?? []).filter(
        (d) =>
          d.audience_hint.trim() || d.format_hint.trim() || d.notes.trim(),
      ),
    };
    try {
      if (mode === "edit" && editingId) {
        await client.updateEditorialContentBacklogItem(editingId, payload);
        setOutcome("Backlog item updated.");
      } else {
        await client.createEditorialContentBacklogItem(payload);
        setOutcome("Backlog item created.");
      }
      setMode("list");
      setEditingId(null);
      setForm(emptyForm());
      await loadList();
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" data-testid="content-backlog-modal-backdrop">
      <div
        ref={dialogRef}
        className="modal-panel filters-modal content-backlog-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        data-testid="content-backlog-modal"
      >
        <div className="filters-modal-header">
          <div>
            <p className="eyebrow">Editorial</p>
            <h2 id={titleId}>Content backlog</h2>
          </div>
          <button
            ref={closeBtnRef}
            type="button"
            className="secondary"
            data-testid="content-backlog-modal-close"
            onClick={onClose}
          >
            Close
          </button>
        </div>

        <div className="filters-modal-body">
          <p className="note" data-testid="content-backlog-optional-note">
            Optional hand-curated topic queue. Saving here does not publish to
            LinkedIn and does not start Flow B discovery or gap trigger. Flow B
            still runs when this backlog is empty.
          </p>

          {needsReauth && (
            <p className="note" data-testid="content-backlog-reauth-note">
              Sign in required to load or save backlog items.{" "}
              <button
                type="button"
                data-testid="content-backlog-sign-in"
                onClick={() => void signIn()}
              >
                Sign in
              </button>
            </p>
          )}

          {error && (
            <p
              className="form-error"
              role="alert"
              data-testid="content-backlog-error"
            >
              {error}
            </p>
          )}

          {outcome && (
            <p className="note" data-testid="content-backlog-outcome">
              {outcome}
            </p>
          )}

          {loading && mode === "list" && (
            <p className="note" data-testid="content-backlog-loading">
              Loading backlog…
            </p>
          )}

          {mode === "list" && !loading && (
            <div data-testid="content-backlog-list-panel">
              <div className="drawer-actions content-backlog-list-actions">
                <button
                  type="button"
                  data-testid="content-backlog-new-btn"
                  disabled={!canMutate}
                  onClick={startCreate}
                >
                  New item
                </button>
              </div>

              {items.length === 0 ? (
                <p className="note" data-testid="content-backlog-empty">
                  No backlog items yet. Create one when you want a hand-curated
                  topic queue — this is not required for Flow B.
                </p>
              ) : (
                <ul
                  className="content-backlog-list"
                  data-testid="content-backlog-list"
                >
                  {items.map((item) => (
                    <li key={item.item_id}>
                      <button
                        type="button"
                        className="content-backlog-list-item"
                        data-testid={`content-backlog-item-${item.item_id}`}
                        onClick={() => startEdit(item)}
                      >
                        <strong>{item.topic}</strong>
                        <span>
                          {item.status} · {item.priority} · {item.format}
                        </span>
                        <span>{item.audience}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {(mode === "create" || mode === "edit") && (
            <form
              className="gap-settings-form content-backlog-form"
              data-testid="content-backlog-form"
              onSubmit={(e) => void onSubmit(e)}
            >
              <p className="meta-line">
                {mode === "edit" ? "Edit backlog item" : "Create backlog item"}
              </p>

              <label className="field">
                <span>Topic</span>
                <input
                  type="text"
                  data-testid="content-backlog-topic"
                  value={form.topic}
                  disabled={!canMutate || saving}
                  onChange={(e) => setForm({ ...form, topic: e.target.value })}
                  required
                />
              </label>

              <label className="field">
                <span>Audience</span>
                <input
                  type="text"
                  data-testid="content-backlog-audience"
                  value={form.audience}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({ ...form, audience: e.target.value })
                  }
                  required
                />
              </label>

              <label className="field">
                <span>Objective</span>
                <textarea
                  data-testid="content-backlog-objective"
                  value={form.objective}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({ ...form, objective: e.target.value })
                  }
                  required
                  rows={3}
                />
              </label>

              <label className="field">
                <span>Format</span>
                <select
                  data-testid="content-backlog-format"
                  value={form.format}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      format: e.target.value as BacklogFormat,
                    })
                  }
                >
                  {FORMATS.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Priority</span>
                <select
                  data-testid="content-backlog-priority"
                  value={form.priority}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      priority: e.target.value as BacklogPriority,
                    })
                  }
                >
                  {PRIORITIES.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Status</span>
                <select
                  data-testid="content-backlog-status"
                  value={form.status}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      status: e.target.value as BacklogStatus,
                    })
                  }
                >
                  {STATUSES.map((value) => (
                    <option key={value} value={value}>
                      {value}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span>Target date (optional YYYY-MM-DD)</span>
                <input
                  type="text"
                  data-testid="content-backlog-target-date"
                  value={form.target_date ?? ""}
                  disabled={!canMutate || saving}
                  onChange={(e) =>
                    setForm({ ...form, target_date: e.target.value })
                  }
                  placeholder="2026-08-01"
                />
              </label>

              <fieldset className="content-backlog-derivatives">
                <legend>LinkedIn derivative planning notes</legend>
                <p className="note">
                  Planning links only — does not package or publish LinkedIn
                  posts.
                </p>
                {(form.linkedin_derivatives ?? []).map((note, index) => (
                  <div
                    key={index}
                    className="content-backlog-derivative"
                    data-testid={`content-backlog-derivative-${index}`}
                  >
                    <label className="field">
                      <span>Audience hint</span>
                      <input
                        type="text"
                        data-testid={`content-backlog-derivative-audience-${index}`}
                        value={note.audience_hint}
                        disabled={!canMutate || saving}
                        onChange={(e) =>
                          updateDerivative(index, {
                            audience_hint: e.target.value,
                          })
                        }
                      />
                    </label>
                    <label className="field">
                      <span>Format hint</span>
                      <input
                        type="text"
                        data-testid={`content-backlog-derivative-format-${index}`}
                        value={note.format_hint}
                        disabled={!canMutate || saving}
                        onChange={(e) =>
                          updateDerivative(index, {
                            format_hint: e.target.value,
                          })
                        }
                      />
                    </label>
                    <label className="field">
                      <span>Notes</span>
                      <textarea
                        data-testid={`content-backlog-derivative-notes-${index}`}
                        value={note.notes}
                        disabled={!canMutate || saving}
                        rows={2}
                        onChange={(e) =>
                          updateDerivative(index, { notes: e.target.value })
                        }
                      />
                    </label>
                  </div>
                ))}
              </fieldset>

              <div className="drawer-actions">
                <button
                  type="button"
                  className="secondary"
                  data-testid="content-backlog-cancel-edit"
                  onClick={backToList}
                  disabled={saving}
                >
                  Back
                </button>
                <button
                  type="submit"
                  data-testid="content-backlog-save"
                  disabled={!canMutate || saving}
                >
                  {saving ? "Saving…" : "Save"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
