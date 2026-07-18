import { AppShell } from "./components/AppShell";
import { ListView } from "./components/ListView";
import { MonthCalendarView } from "./components/MonthCalendarView";
import { SupervisionStoreProvider, useSupervisionStore } from "./models/store";

function ConsoleBody() {
  const { activeView, snapshot } = useSupervisionStore();
  if (activeView === "calendar") {
    return <MonthCalendarView snapshot={snapshot} />;
  }
  return <ListView />;
}

export default function App() {
  return (
    <SupervisionStoreProvider>
      <AppShell>
        <ConsoleBody />
      </AppShell>
    </SupervisionStoreProvider>
  );
}
