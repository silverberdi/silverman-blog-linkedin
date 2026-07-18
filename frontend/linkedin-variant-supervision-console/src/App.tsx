import { AppShell } from "./components/AppShell";
import { EventModal } from "./components/EventModal";
import { MonthCalendarView } from "./components/MonthCalendarView";
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
      <EventModal />
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
