import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { ApiError } from "../api/errors";
import type { SupervisionApiClient } from "../api/client";
import { apiClient } from "../api/client";
import {
  effectiveCapabilities,
  sessionBannerKind,
  sessionBannerText,
  sessionStateFromApiError,
  type SessionState,
} from "../api/session";
import {
  currentLocalMonth,
  currentLocalWeek,
  localDayKey,
  monthCursorFromDayKey,
  monthsCoveringLocalMonth,
  monthsCoveringWeek,
  sundayLocalWeekStart,
  type MonthCursor,
  type WeekCursor,
} from "./dateHelpers";
import {
  applyFilters,
  countHiddenCritical,
  defaultFilters,
  deriveOperationalCounts,
  emptyOperationalCounts,
  mergeCountUniverse,
  mergeScheduleSnapshots,
  normalizePendingSupervision,
  normalizeScheduleVisibility,
  supervisionToFilterable,
  type ConsoleView,
  type FilterState,
  type OperationalCounts,
  type ScheduleEditorTarget,
  type ScheduleItem,
  type ScheduleSnapshot,
  type SupervisionItem,
  type SupervisionSnapshot,
} from "./supervision";

export type BannerKind = "info" | "ok" | "warn" | "error" | "";

export interface BannerState {
  kind: BannerKind;
  text: string;
}

/** Toast kinds for ephemeral overlay feedback (US-040H). */
export type ToastKind = "ok" | "info" | "warn" | "error";

export interface ToastItem {
  id: string;
  kind: ToastKind;
  text: string;
}

export interface PushToastInput {
  kind: ToastKind;
  text: string;
}

const TOAST_AUTO_DISMISS_MS = 5000;
const TOAST_MAX_VISIBLE = 3;

function newToastId(): string {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `toast-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export type MetricFocusKey =
  | "upcoming"
  | "pending"
  | "dueSoon"
  | "deferred"
  | "blocked"
  | "failed"
  | "recentlyPublished";

interface SupervisionStoreValue {
  snapshot: SupervisionSnapshot | null;
  scheduleSnapshot: ScheduleSnapshot | null;
  activeView: ConsoleView;
  setActiveView: (view: ConsoleView) => void;
  requestViewChange: (view: ConsoleView) => void;
  filters: FilterState;
  setFilters: (next: FilterState | ((prev: FilterState) => FilterState)) => void;
  resetFilters: () => void;
  showHiddenCritical: () => void;
  monthCursor: MonthCursor;
  setMonthCursor: (cursor: MonthCursor) => void;
  weekCursor: WeekCursor;
  setWeekCursor: (cursor: WeekCursor) => void;
  selectedDayKey: string | null;
  setSelectedDayKey: (dayKey: string | null) => void;
  selectedItemId: string | null;
  setSelectedItemId: (itemId: string | null) => void;
  eventModalItemId: string | null;
  eventModalEntry: "week" | "month";
  openEventModal: (itemId: string, entry?: "week" | "month") => void;
  closeEventModal: () => void;
  /** @deprecated US-040H — alias for eventModalItemId */
  interimDetailItemId: string | null;
  /** @deprecated US-040H — alias for eventModalEntry */
  interimEntry: "week" | "month";
  /** @deprecated US-040H — use openEventModal */
  openInterimDetail: (itemId: string, entry?: "week" | "month") => void;
  /** @deprecated US-040H — use closeEventModal */
  closeInterimDetail: () => void;
  dryRunDefault: boolean;
  setDryRunDefault: (value: boolean) => void;
  unsavedScheduleDraft: boolean;
  setUnsavedScheduleDraft: (value: boolean) => void;
  unsavedEditDraft: boolean;
  setUnsavedEditDraft: (value: boolean) => void;
  scheduleEditorTarget: ScheduleEditorTarget | null;
  openScheduleEditor: (target: ScheduleEditorTarget) => void;
  closeScheduleEditor: () => void;
  loading: boolean;
  statusBanner: BannerState;
  actionBanner: BannerState;
  sessionBanner: BannerState;
  sessionState: SessionState;
  canRead: boolean;
  canMutate: boolean;
  setStatusBanner: (banner: BannerState) => void;
  setActionBanner: (banner: BannerState) => void;
  toasts: ToastItem[];
  pushToast: (toast: PushToastInput) => void;
  dismissToast: (id: string) => void;
  loadPending: (options?: { preserveActionBanner?: boolean }) => Promise<boolean>;
  loadScheduleVisibility: (options?: {
    preserveActionBanner?: boolean;
    year?: number;
    month?: number;
  }) => Promise<boolean>;
  loadScheduleForMonths: (
    months: MonthCursor[],
    options?: { preserveActionBanner?: boolean },
  ) => Promise<boolean>;
  refreshAll: (options?: { preserveActionBanner?: boolean }) => Promise<boolean>;
  navigateMetricFocus: (metric: MetricFocusKey) => void;
  filteredListItems: SupervisionItem[];
  filteredScheduleItems: ScheduleItem[];
  hiddenCriticalCount: number;
  operationalCounts: OperationalCounts;
  clearAuth: () => void;
  signIn: () => Promise<boolean>;
  client: SupervisionApiClient;
}

const SupervisionStoreContext = createContext<SupervisionStoreValue | null>(
  null,
);

function emptyBanner(): BannerState {
  return { kind: "", text: "" };
}

function sessionBannerFromState(state: SessionState): BannerState {
  return {
    kind: sessionBannerKind(state),
    text: sessionBannerText(state),
  };
}

function isPreservingAuthFailure(err: ApiError): boolean {
  return (
    err.kind === "unauthorized" ||
    err.kind === "forbidden" ||
    err.kind === "network" ||
    (err.kind === "http" &&
      err.httpStatus != null &&
      err.httpStatus >= 500)
  );
}

function itemMatchesMetric(item: ScheduleItem, metric: MetricFocusKey, nowMs: number): boolean {
  if (metric === "upcoming") {
    if (
      !item.scheduledAtUtc ||
      item.publicationState === "cancelled" ||
      item.publicationState === "completed" ||
      item.publicationState === "published"
    ) {
      return false;
    }
    return Date.parse(item.scheduledAtUtc) >= nowMs;
  }
  if (metric === "blocked") {
    return item.blocked || item.publicationState === "blocked";
  }
  if (metric === "dueSoon") {
    if (
      !item.scheduledAtUtc ||
      item.publicationState === "cancelled" ||
      item.publicationState === "completed" ||
      item.publicationState === "published"
    ) {
      return false;
    }
    const t = Date.parse(item.scheduledAtUtc);
    return t >= nowMs && t <= nowMs + 48 * 60 * 60 * 1000;
  }
  if (metric === "failed") {
    return item.critical || item.publicationState === "failed";
  }
  if (metric === "pending") {
    return item.publicationState === "pending";
  }
  if (metric === "deferred") {
    return item.publicationState === "deferred";
  }
  if (metric === "recentlyPublished") {
    return item.publicationState === "published" && item.linkedinApiPublished;
  }
  return false;
}

export function SupervisionStoreProvider({
  children,
  client = apiClient,
  initialSessionState,
}: {
  children: ReactNode;
  client?: SupervisionApiClient;
  initialSessionState?: SessionState;
}) {
  const [snapshot, setSnapshot] = useState<SupervisionSnapshot | null>(null);
  const [scheduleSnapshot, setScheduleSnapshot] =
    useState<ScheduleSnapshot | null>(null);
  const [activeView, setActiveViewState] = useState<ConsoleView>("week");
  const [filters, setFilters] = useState<FilterState>(defaultFilters);
  const [monthCursor, setMonthCursor] = useState<MonthCursor>(currentLocalMonth);
  const [weekCursor, setWeekCursor] = useState<WeekCursor>(currentLocalWeek);
  const [selectedDayKey, setSelectedDayKey] = useState<string | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [eventModalItemId, setEventModalItemId] = useState<string | null>(null);
  const [eventModalEntry, setEventModalEntry] = useState<"week" | "month">(
    "week",
  );
  const [dryRunDefault, setDryRunDefault] = useState(true);
  const [unsavedScheduleDraft, setUnsavedScheduleDraft] = useState(false);
  const [unsavedEditDraft, setUnsavedEditDraft] = useState(false);
  const [scheduleEditorTarget, setScheduleEditorTarget] =
    useState<ScheduleEditorTarget | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusBanner, setStatusBanner] = useState<BannerState>(emptyBanner);
  const [actionBanner, setActionBanner] = useState<BannerState>(emptyBanner);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const toastTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(
    new Map(),
  );
  const [sessionState, setSessionState] = useState<SessionState>(
    () =>
      initialSessionState ??
      (client.hasCredential() ? "authenticated" : "anonymous"),
  );
  const [authEpoch, setAuthEpoch] = useState(0);

  const dismissToast = useCallback((id: string) => {
    const timer = toastTimersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      toastTimersRef.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const pushToast = useCallback(
    (input: PushToastInput) => {
      const id = newToastId();
      setToasts((prev) => {
        const next = [{ id, kind: input.kind, text: input.text }, ...prev];
        return next.slice(0, TOAST_MAX_VISIBLE);
      });
      const timer = setTimeout(() => {
        dismissToast(id);
      }, TOAST_AUTO_DISMISS_MS);
      toastTimersRef.current.set(id, timer);
    },
    [dismissToast],
  );

  useEffect(() => {
    return () => {
      for (const timer of toastTimersRef.current.values()) {
        clearTimeout(timer);
      }
      toastTimersRef.current.clear();
    };
  }, []);

  const bumpAuth = useCallback(() => {
    setAuthEpoch((n) => n + 1);
  }, []);

  const applySessionFromError = useCallback((err: ApiError) => {
    const next = sessionStateFromApiError(err);
    if (next) {
      setSessionState(next);
    }
  }, []);

  const clearAuth = useCallback(() => {
    client.clearAuth();
    bumpAuth();
    setSessionState("anonymous");
    setStatusBanner({
      kind: "info",
      text: "Credential cleared for this browser session. Sign in again to load or mutate. Visible context and unsaved drafts are kept until you discard them.",
    });
  }, [client, bumpAuth]);

  const signIn = useCallback(async () => {
    const ok = await client.signIn();
    bumpAuth();
    if (ok) {
      setSessionState("authenticated");
      setStatusBanner({
        kind: "ok",
        text: "Signed in. Refresh to reload pending and schedule data. Unsaved schedule drafts remain available.",
      });
    } else {
      setSessionState("anonymous");
      setStatusBanner({
        kind: "warn",
        text: "Sign-in cancelled or empty credential. Still not authenticated.",
      });
    }
    return ok;
  }, [client, bumpAuth]);

  const setActiveView = useCallback((view: ConsoleView) => {
    setActiveViewState(view);
  }, []);

  const requestViewChange = useCallback(
    (view: ConsoleView) => {
      if (view === activeView) {
        return;
      }
      if (unsavedScheduleDraft) {
        const ok = window.confirm(
          "You have an unsaved schedule draft. Switch views and discard it?",
        );
        if (!ok) {
          return;
        }
        setUnsavedScheduleDraft(false);
        setScheduleEditorTarget(null);
      }
      setActiveViewState(view);
    },
    [activeView, unsavedScheduleDraft],
  );

  const openEventModal = useCallback(
    (itemId: string, entry: "week" | "month" = "week") => {
      setSelectedItemId(itemId);
      setEventModalItemId(itemId);
      setEventModalEntry(entry);
    },
    [],
  );

  const closeEventModal = useCallback(() => {
    setEventModalItemId(null);
    setUnsavedEditDraft(false);
  }, []);

  const openInterimDetail = openEventModal;
  const closeInterimDetail = closeEventModal;

  const openScheduleEditor = useCallback((target: ScheduleEditorTarget) => {
    setScheduleEditorTarget(target);
    setSelectedItemId(target.itemId);
  }, []);

  const closeScheduleEditor = useCallback(() => {
    setScheduleEditorTarget(null);
    setUnsavedScheduleDraft(false);
  }, []);

  const resetFilters = useCallback(() => {
    setFilters(defaultFilters());
  }, []);

  const showHiddenCritical = useCallback(() => {
    setFilters((prev) => ({
      ...prev,
      channel: "all",
      campaignQuery: "",
      publicationStates: [],
      blockedOnly: false,
      dueSoonOnly: false,
    }));
  }, []);

  const loadPending = useCallback(
    async (options?: { preserveActionBanner?: boolean }) => {
      setLoading(true);
      try {
        const payload = await client.getPendingSupervision();
        const next = normalizePendingSupervision(payload);
        setSnapshot(next);
        bumpAuth();
        setSessionState("authenticated");
        if (next.status === "partial" || next.issues.length) {
          setStatusBanner({
            kind: "warn",
            text: "Partial read: some campaign, calendar, or draft data could not be fully aligned. Successful pending rows are still shown when available.",
          });
        } else {
          setStatusBanner({
            kind: "ok",
            text: "Read completed without data issues.",
          });
        }
        if (!options?.preserveActionBanner) {
          setActionBanner(emptyBanner());
        }
        return true;
      } catch (err) {
        const apiErr = err as ApiError;
        applySessionFromError(apiErr);
        bumpAuth();
        setStatusBanner({
          kind: "error",
          text: apiErr?.message || String(err),
        });
        if (!isPreservingAuthFailure(apiErr)) {
          setSnapshot(null);
        }
        return false;
      } finally {
        setLoading(false);
      }
    },
    [client, applySessionFromError, bumpAuth],
  );

  const loadScheduleForMonths = useCallback(
    async (
      months: MonthCursor[],
      options?: { preserveActionBanner?: boolean },
    ) => {
      if (months.length === 0) {
        return false;
      }
      setLoading(true);
      try {
        const payloads = await Promise.all(
          months.map((m) =>
            client.getScheduleVisibility({ year: m.year, month: m.month }),
          ),
        );
        const normalized = payloads.map(normalizeScheduleVisibility);
        const next =
          normalized.length === 1
            ? normalized[0]
            : mergeScheduleSnapshots(normalized[0], normalized.slice(1));
        setScheduleSnapshot(next);
        bumpAuth();
        setSessionState("authenticated");
        if (next.status === "partial" || next.issues.length) {
          setStatusBanner({
            kind: "warn",
            text: "Partial schedule read: calendar or campaign data may be incomplete. Available schedule items are still shown.",
          });
        } else if (!options?.preserveActionBanner) {
          setStatusBanner({
            kind: "ok",
            text: "Schedule visibility read completed without data issues.",
          });
        }
        if (!options?.preserveActionBanner) {
          setActionBanner(emptyBanner());
        }
        return true;
      } catch (err) {
        const apiErr = err as ApiError;
        applySessionFromError(apiErr);
        bumpAuth();
        setStatusBanner({
          kind: "error",
          text: apiErr?.message || String(err),
        });
        if (!isPreservingAuthFailure(apiErr)) {
          setScheduleSnapshot(null);
        }
        return false;
      } finally {
        setLoading(false);
      }
    },
    [client, applySessionFromError, bumpAuth],
  );

  const loadScheduleVisibility = useCallback(
    async (options?: {
      preserveActionBanner?: boolean;
      year?: number;
      month?: number;
    }) => {
      const year = options?.year ?? monthCursor.year;
      const month = options?.month ?? monthCursor.month;
      return loadScheduleForMonths(monthsCoveringLocalMonth({ year, month }), {
        preserveActionBanner: options?.preserveActionBanner,
      });
    },
    [monthCursor.month, monthCursor.year, loadScheduleForMonths],
  );

  const refreshAll = useCallback(
    async (options?: { preserveActionBanner?: boolean }) => {
      setLoading(true);
      try {
        const months =
          activeView === "week"
            ? monthsCoveringWeek(weekCursor.weekStartKey)
            : monthsCoveringLocalMonth(monthCursor);
        const [pendingPayload, ...schedulePayloads] = await Promise.all([
          client.getPendingSupervision(),
          ...months.map((m) =>
            client.getScheduleVisibility({ year: m.year, month: m.month }),
          ),
        ]);
        const nextPending = normalizePendingSupervision(pendingPayload);
        const normalized = schedulePayloads.map(normalizeScheduleVisibility);
        const nextSchedule =
          normalized.length === 1
            ? normalized[0]
            : mergeScheduleSnapshots(normalized[0], normalized.slice(1));
        setSnapshot(nextPending);
        setScheduleSnapshot(nextSchedule);
        bumpAuth();
        setSessionState("authenticated");
        const partial =
          nextPending.status === "partial" ||
          nextPending.issues.length > 0 ||
          nextSchedule.status === "partial" ||
          nextSchedule.issues.length > 0;
        if (partial) {
          setStatusBanner({
            kind: "warn",
            text: "Partial coordinated refresh: some pending or schedule data could not be fully aligned.",
          });
        } else {
          setStatusBanner({
            kind: "ok",
            text: "Pending and schedule visibility refreshed.",
          });
        }
        if (!options?.preserveActionBanner) {
          setActionBanner(emptyBanner());
        }
        return true;
      } catch (err) {
        const apiErr = err as ApiError;
        applySessionFromError(apiErr);
        bumpAuth();
        setStatusBanner({
          kind: "error",
          text: apiErr?.message || String(err),
        });
        return false;
      } finally {
        setLoading(false);
      }
    },
    [
      client,
      activeView,
      weekCursor.weekStartKey,
      monthCursor,
      applySessionFromError,
      bumpAuth,
    ],
  );

  const filteredListItems = useMemo(() => {
    const items = snapshot?.items ?? [];
    const nowMs = Date.now();
    return items.filter((item) =>
      applyFilters([supervisionToFilterable(item)], filters, nowMs).length > 0,
    );
  }, [snapshot, filters]);

  const filteredScheduleItems = useMemo(() => {
    return applyFilters(scheduleSnapshot?.items ?? [], filters);
  }, [scheduleSnapshot, filters]);

  const navigateMetricFocus = useCallback(
    (metric: MetricFocusKey) => {
      // Design D4: reset focus flags then apply target; navigate Week/Month only.
      setFilters((prev) => {
        const cleared = {
          ...prev,
          blockedOnly: false,
          dueSoonOnly: false,
          publicationStates: [] as typeof prev.publicationStates,
        };
        if (metric === "blocked") {
          return { ...cleared, blockedOnly: true };
        }
        if (metric === "dueSoon") {
          return { ...cleared, dueSoonOnly: true };
        }
        if (metric === "failed") {
          return { ...cleared, publicationStates: ["failed"] };
        }
        if (metric === "pending") {
          return { ...cleared, publicationStates: ["pending"] };
        }
        if (metric === "deferred") {
          return { ...cleared, publicationStates: ["deferred"] };
        }
        if (metric === "recentlyPublished") {
          return { ...cleared, publicationStates: ["published"] };
        }
        return cleared;
      });

      const nowMs = Date.now();
      const universe = scheduleSnapshot?.items ?? [];
      const channelOk = (item: ScheduleItem) =>
        filters.channel === "all" || item.channel === filters.channel;
      const campaignOk = (item: ScheduleItem) => {
        const q = filters.campaignQuery.trim().toLowerCase();
        if (!q) {
          return true;
        }
        return (
          (item.campaignId ?? "").toLowerCase().includes(q) ||
          (item.title ?? "").toLowerCase().includes(q) ||
          (item.variantId ?? "").toLowerCase().includes(q)
        );
      };
      const matches = universe
        .filter(
          (item) =>
            channelOk(item) &&
            campaignOk(item) &&
            itemMatchesMetric(item, metric, nowMs),
        )
        .sort((a, b) =>
          (a.scheduledAtUtc ?? "").localeCompare(b.scheduledAtUtc ?? ""),
        );

      if (matches.length === 0) {
        return;
      }

      const next = matches[0];
      const dayKey = localDayKey(next.scheduledAtUtc);
      if (!dayKey) {
        return;
      }

      if (activeView === "month") {
        setMonthCursor(monthCursorFromDayKey(dayKey));
        setSelectedDayKey(dayKey);
      } else {
        setWeekCursor({ weekStartKey: sundayLocalWeekStart(dayKey) });
        setMonthCursor(monthCursorFromDayKey(dayKey));
        setSelectedDayKey(dayKey);
      }
      setSelectedItemId(next.itemId);
    },
    [scheduleSnapshot, filters.channel, filters.campaignQuery, activeView],
  );

  const hiddenCriticalCount = useMemo(() => {
    const scheduleAll = scheduleSnapshot?.items ?? [];
    const listAsSchedule = (snapshot?.items ?? []).map(supervisionToFilterable);
    const universe = scheduleAll.length > 0 ? scheduleAll : listAsSchedule;
    const visible =
      scheduleAll.length > 0
        ? filteredScheduleItems
        : filteredListItems.map(supervisionToFilterable);
    return countHiddenCritical(universe, visible);
  }, [
    scheduleSnapshot,
    snapshot,
    filteredScheduleItems,
    filteredListItems,
  ]);

  const operationalCounts = useMemo(() => {
    if (!snapshot && !scheduleSnapshot) {
      return emptyOperationalCounts();
    }
    const filteredUniverse = mergeCountUniverse(
      filteredScheduleItems,
      filteredListItems.map(supervisionToFilterable),
    );
    return deriveOperationalCounts(filteredUniverse, {
      integrationFailureCount: snapshot?.integrationFailures.length ?? 0,
    });
  }, [snapshot, scheduleSnapshot, filteredScheduleItems, filteredListItems]);

  const caps = useMemo(
    () =>
      effectiveCapabilities(
        client.canRead(),
        client.canMutate(),
        sessionState,
      ),
    [client, sessionState, authEpoch],
  );

  const sessionBanner = useMemo(
    () => sessionBannerFromState(sessionState),
    [sessionState],
  );

  const value = useMemo(
    () => ({
      snapshot,
      scheduleSnapshot,
      activeView,
      setActiveView,
      requestViewChange,
      filters,
      setFilters,
      resetFilters,
      showHiddenCritical,
      monthCursor,
      setMonthCursor,
      weekCursor,
      setWeekCursor,
      selectedDayKey,
      setSelectedDayKey,
      selectedItemId,
      setSelectedItemId,
      eventModalItemId,
      eventModalEntry,
      openEventModal,
      closeEventModal,
      interimDetailItemId: eventModalItemId,
      interimEntry: eventModalEntry,
      openInterimDetail,
      closeInterimDetail,
      dryRunDefault,
      setDryRunDefault,
      unsavedScheduleDraft,
      setUnsavedScheduleDraft,
      unsavedEditDraft,
      setUnsavedEditDraft,
      scheduleEditorTarget,
      openScheduleEditor,
      closeScheduleEditor,
      loading,
      statusBanner,
      actionBanner,
      sessionBanner,
      sessionState,
      canRead: caps.canRead,
      canMutate: caps.canMutate,
      setStatusBanner,
      setActionBanner,
      toasts,
      pushToast,
      dismissToast,
      loadPending,
      loadScheduleVisibility,
      loadScheduleForMonths,
      refreshAll,
      navigateMetricFocus,
      filteredListItems,
      filteredScheduleItems,
      hiddenCriticalCount,
      operationalCounts,
      clearAuth,
      signIn,
      client,
    }),
    [
      snapshot,
      scheduleSnapshot,
      activeView,
      setActiveView,
      requestViewChange,
      filters,
      resetFilters,
      showHiddenCritical,
      monthCursor,
      weekCursor,
      selectedDayKey,
      selectedItemId,
      eventModalItemId,
      eventModalEntry,
      openEventModal,
      closeEventModal,
      openInterimDetail,
      closeInterimDetail,
      dryRunDefault,
      unsavedScheduleDraft,
      unsavedEditDraft,
      scheduleEditorTarget,
      openScheduleEditor,
      closeScheduleEditor,
      loading,
      statusBanner,
      actionBanner,
      sessionBanner,
      sessionState,
      caps.canRead,
      caps.canMutate,
      toasts,
      pushToast,
      dismissToast,
      loadPending,
      loadScheduleVisibility,
      loadScheduleForMonths,
      refreshAll,
      navigateMetricFocus,
      filteredListItems,
      filteredScheduleItems,
      hiddenCriticalCount,
      operationalCounts,
      clearAuth,
      signIn,
      client,
    ],
  );

  return (
    <SupervisionStoreContext.Provider value={value}>
      {children}
    </SupervisionStoreContext.Provider>
  );
}

export function useSupervisionStore(): SupervisionStoreValue {
  const ctx = useContext(SupervisionStoreContext);
  if (!ctx) {
    throw new Error("useSupervisionStore must be used within SupervisionStoreProvider");
  }
  return ctx;
}
