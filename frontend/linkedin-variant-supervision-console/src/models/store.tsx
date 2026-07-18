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
  normalizePendingSupervision,
  type ConsoleView,
  type SupervisionSnapshot,
} from "./supervision";

export type BannerKind = "info" | "ok" | "warn" | "error" | "";

export interface BannerState {
  kind: BannerKind;
  text: string;
}

interface SupervisionStoreValue {
  snapshot: SupervisionSnapshot | null;
  activeView: ConsoleView;
  setActiveView: (view: ConsoleView) => void;
  loading: boolean;
  statusBanner: BannerState;
  actionBanner: BannerState;
  setStatusBanner: (banner: BannerState) => void;
  setActionBanner: (banner: BannerState) => void;
  loadPending: (options?: { preserveActionBanner?: boolean }) => Promise<boolean>;
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
  const [activeView, setActiveView] = useState<ConsoleView>("list");
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

  const value = useMemo(
    () => ({
      snapshot,
      activeView,
      setActiveView,
      loading,
      statusBanner,
      actionBanner,
      setStatusBanner,
      setActionBanner,
      loadPending,
      clearAuth,
      client,
    }),
    [
      snapshot,
      activeView,
      loading,
      statusBanner,
      actionBanner,
      loadPending,
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
