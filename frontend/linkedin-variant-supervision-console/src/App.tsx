import { AppShell } from "./components/AppShell";
import { ListView } from "./components/ListView";
import { MonthCalendarView } from "./components/MonthCalendarView";
import { ScheduleEditorPanel } from "./components/ScheduleEditor";
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
      {activeView === "calendar" ? <MonthCalendarView /> : <ListView />}
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
