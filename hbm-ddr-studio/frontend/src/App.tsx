import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import Home from "@/pages/Home";
import { GroupPage } from "@/pages/GroupPage";
import { ProjectConfigPage } from "@/pages/ProjectConfigPage";
import { TaskPage } from "@/components/task/TaskPage";
import { SubsystemIntegrationPage } from "@/pages/SubsystemIntegrationPage";
import { DashboardPage } from "@/pages/DashboardPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<AppShell />}>
        <Route index element={<Home />} />

        {/* project config */}
        <Route path="config" element={<ProjectConfigPage />} />

        {/* group landing pages */}
        <Route path="rtl" element={<GroupPage group="rtl" />} />
        <Route path="dv"  element={<GroupPage group="dv" />} />
        <Route path="pm"  element={<GroupPage group="pm" />} />

        {/* bespoke RTL page with live diagram */}
        <Route path="rtl/rtl_subsystem_integration" element={<SubsystemIntegrationPage />} />

        {/* generic per-task pages */}
        <Route path="rtl/:taskId" element={<TaskPage />} />
        <Route path="dv/:taskId"  element={<TaskPage />} />

        {/* per-dashboard page */}
        <Route path="pm/:dashId"  element={<DashboardPage />} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
