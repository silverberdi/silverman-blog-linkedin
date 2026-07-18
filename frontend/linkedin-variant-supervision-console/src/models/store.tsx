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
  client: SupervisionApiClient;
}

const SupervisionStoreContext = createContext<SupervisionStoreValue | null>(
  null,
);

function emptyBanner(): BannerState {
  return { kind: "", text: "" };
}

export function SupervisionStoreProvider({
  children,
  client = apiClient,
}: {
  children: ReactNode;
  client?: SupervisionApiClient;
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

  const clearAuth = useCallback(() => {
    client.clearAuth();
    setStatusBanner({
      kind: "info",
      text: "In-memory API key cleared. You will be prompted again on the next load.",
    });
  }, [client]);

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
        setStatusBanner({
          kind: "error",
          text: apiErr?.message || String(err),
        });
        setSnapshot(null);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [client],
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
        setStatusBanner({
          kind: "error",
          text: apiErr?.message || String(err),
        });
        // Soft-degrade: keep list usable if schedule GET fails.
        setScheduleSnapshot(null);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [client, monthCursor.month, monthCursor.year],
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
        setStatusBanner({
          kind: "error",
          text: apiErr?.message || String(err),
        });
        return false;
      } finally {
        setLoading(false);
      }
    },
    [client, monthCursor.month, monthCursor.year],
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
    // Prefer schedule universe for critical discoverability; fall back to list.
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
      setStatusBanner,
      setActionBanner,
      loadPending,
      loadScheduleVisibility,
      refreshAll,
      filteredListItems,
      filteredScheduleItems,
      hiddenCriticalCount,
      clearAuth,
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
      loadPending,
      loadScheduleVisibility,
      refreshAll,
      filteredListItems,
      filteredScheduleItems,
      hiddenCriticalCount,
      clearAuth,
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
