// Bespoke wrapper for the RTL Subsystem Integration task — adds the live diagram preview.
import { TaskPage } from "@/components/task/TaskPage";
import { DiagramSubsystem } from "@/components/diagrams/DiagramSubsystem";

export function SubsystemIntegrationPage() {
  return (
    <TaskPage
      taskId="rtl_subsystem_integration"
      extras={(cfg) => (
        <DiagramSubsystem
          protocol={(cfg as any).protocol}
          phyVendor={(cfg as any).phy_vendor}
          channels={Number((cfg as any).channels) || 4}
          noc={(cfg as any).noc}
          rasIp={(cfg as any).ras_ip}
          smmuIp={(cfg as any).smmu_ip}
        />
      )}
    />
  );
}
