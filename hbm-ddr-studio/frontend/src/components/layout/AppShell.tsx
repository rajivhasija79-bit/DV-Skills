import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";
import { TooltipProvider } from "@/components/ui/tooltip";
import { AppSidebar } from "./AppSidebar";
import { Topbar } from "./Topbar";
import { useTheme } from "@/lib/theme";
import { api, type TaskDescriptor } from "@/lib/api";

export function AppShell() {
  useTheme(); // applies theme on mount
  const [tasks, setTasks] = useState<TaskDescriptor[]>([]);
  useEffect(() => {
    api.listTasks().then(setTasks).catch(() => setTasks([]));
  }, []);
  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex h-screen w-screen overflow-hidden bg-background">
        <AppSidebar tasks={tasks} />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Topbar />
          <main className="flex-1 overflow-y-auto scrollbar-thin">
            <Outlet context={{ tasks }} />
          </main>
        </div>
      </div>
    </TooltipProvider>
  );
}
