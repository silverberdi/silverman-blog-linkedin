import { AppShell } from "./components/AppShell";
import { InterimEventPanel } from "./components/InterimEventPanel";
import { MonthCalendarView } from "./components/MonthCalendarView";
import { ScheduleEditorPanel } from "./components/ScheduleEditor";
import { WeekView } from "./components/WeekView";
import {
  SupervisionStoreProvider,
  useSupervisionStore,
} from "./models/store";
import type { SupervisionApiClient } from "./api/client";

function ConsoleBody() {
  const { activeView } = useSupervisionStore();
  return (
    <>
      <ScheduleEditorPanel />
      <InterimEventPanel />
      {activeView === "month" ? <MonthCalendarView /> : <WeekView />}
    </>
  );
}

export default function App({
  client,
}: {
  client?: SupervisionApiClient;
} = {}) {
  return (
    <SupervisionStoreProvider client={client}>
      <AppShell>
        <ConsoleBody />
      </AppShell>
    </SupervisionStoreProvider>
  );
}
