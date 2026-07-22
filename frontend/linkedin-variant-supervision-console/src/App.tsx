import { AppShell } from "./components/AppShell";
import { EventModal } from "./components/EventModal";
import { MonthCalendarView } from "./components/MonthCalendarView";
import { WeekView } from "./components/WeekView";
import {
  SupervisionStoreProvider,
  useSupervisionStore,
} from "./models/store";
import type { SupervisionApiClient } from "./api/client";
import type { DeploymentEnvironment } from "./config/operatorUiConfig";

function ConsoleBody() {
  const { activeView } = useSupervisionStore();
  return (
    <>
      <EventModal />
      {activeView === "month" ? <MonthCalendarView /> : <WeekView />}
    </>
  );
}

export default function App({
  client,
  deploymentEnvironment,
}: {
  client?: SupervisionApiClient;
  /** Set when separated UI↔API pairing succeeds (US-094). */
  deploymentEnvironment?: DeploymentEnvironment;
} = {}) {
  return (
    <SupervisionStoreProvider client={client}>
      <AppShell deploymentEnvironment={deploymentEnvironment}>
        <ConsoleBody />
      </AppShell>
    </SupervisionStoreProvider>
  );
}
