import {
  createContext,
  useCallback,
  useContext,
  useMemo,
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
import { currentUtcMonth, type MonthCursor } from "./dateHelpers";
import {
  applyFilters,
  countHiddenCritical,
  defaultFilters,
  normalizePendingSupervision,
  normalizeScheduleVisibility,
  supervisionToFilterable,
  type ConsoleView,
  type FilterState,
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
  selectedDayKey: string | null;
  setSelectedDayKey: (dayKey: string | null) => void;
  selectedItemId: string | null;
  setSelectedItemId: (itemId: string | null) => void;
  dryRunDefault: boolean;
  setDryRunDefault: (value: boolean) => void;
  unsavedScheduleDraft: boolean;
  setUnsavedScheduleDraft: (value: boolean) => void;
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
  loadPending: (options?: { preserveActionBanner?: boolean }) => Promise<boolean>;
  loadScheduleVisibility: (options?: {
    preserveActionBanner?: boolean;
    year?: number;
    month?: number;
  }) => Promise<boolean>;
  refreshAll: (options?: { preserveActionBanner?: boolean }) => Promise<boolean>;
  filteredListItems: SupervisionItem[];
  filteredScheduleItems: ScheduleItem[];
  hiddenCriticalCount: number;
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
  const [activeView, setActiveViewState] = useState<ConsoleView>("list");
  const [filters, setFilters] = useState<FilterState>(defaultFilters);
  const [monthCursor, setMonthCursor] = useState<MonthCursor>(currentUtcMonth);
  const [selectedDayKey, setSelectedDayKey] = useState<string | null>(null);
  const [selectedItemId, setSelectedItemId] = useState<string | null>(null);
  const [dryRunDefault, setDryRunDefault] = useState(true);
  const [unsavedScheduleDraft, setUnsavedScheduleDraft] = useState(false);
  const [scheduleEditorTarget, setScheduleEditorTarget] =
    useState<ScheduleEditorTarget | null>(null);
  const [loading, setLoading] = useState(false);
  const [statusBanner, setStatusBanner] = useState<BannerState>(emptyBanner);
  const [actionBanner, setActionBanner] = useState<BannerState>(emptyBanner);
  const [sessionState, setSessionState] = useState<SessionState>(
    () =>
      initialSessionState ??
      (client.hasCredential() ? "authenticated" : "anonymous"),
  );
  const [authEpoch, setAuthEpoch] = useState(0);

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
    // Do not clear snapshots or schedule-editor drafts — operator may re-auth.
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
            text: "Partial read: some campaign, calendar, or draft data could not be fully aligned. Successful pending rows are still shown below when available.",
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
        // Preserve visible list context on expiry / forbidden / unavailable.
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

  const loadScheduleVisibility = useCallback(
    async (options?: {
      preserveActionBanner?: boolean;
      year?: number;
      month?: number;
    }) => {
      const year = options?.year ?? monthCursor.year;
      const month = options?.month ?? monthCursor.month;
      setLoading(true);
      try {
        const payload = await client.getScheduleVisibility({ year, month });
        const next = normalizeScheduleVisibility(payload);
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
    [client, monthCursor.month, monthCursor.year, applySessionFromError, bumpAuth],
  );

  const refreshAll = useCallback(
    async (options?: { preserveActionBanner?: boolean }) => {
      setLoading(true);
      try {
        const [pendingPayload, schedulePayload] = await Promise.all([
          client.getPendingSupervision(),
          client.getScheduleVisibility({
            year: monthCursor.year,
            month: monthCursor.month,
          }),
        ]);
        const nextPending = normalizePendingSupervision(pendingPayload);
        const nextSchedule = normalizeScheduleVisibility(schedulePayload);
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
        // Keep last-loaded snapshots on auth/availability failures (expiry mid-edit).
        return false;
      } finally {
        setLoading(false);
      }
    },
    [
      client,
      monthCursor.month,
      monthCursor.year,
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
      selectedDayKey,
      setSelectedDayKey,
      selectedItemId,
      setSelectedItemId,
      dryRunDefault,
      setDryRunDefault,
      unsavedScheduleDraft,
      setUnsavedScheduleDraft,
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
      loadPending,
      loadScheduleVisibility,
      refreshAll,
      filteredListItems,
      filteredScheduleItems,
      hiddenCriticalCount,
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
      selectedDayKey,
      selectedItemId,
      dryRunDefault,
      unsavedScheduleDraft,
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
      loadPending,
      loadScheduleVisibility,
      refreshAll,
      filteredListItems,
      filteredScheduleItems,
      hiddenCriticalCount,
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
