// Bespoke wrapper for the RTL Subsystem Integration task. Two tabs:
//   - Form:    the existing SchemaForm-driven flow + live preview diagram
//   - Diagram: a React Flow canvas where the user draws the subsystem and
//              clicks "Apply to Form" to populate the form from the diagram.
import { useState } from "react";
import { TaskPage } from "@/components/task/TaskPage";
import { DiagramSubsystem } from "@/components/diagrams/DiagramSubsystem";
import { DiagramBuilder } from "@/components/diagrams/DiagramBuilder";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function SubsystemIntegrationPage() {
  const [tab, setTab] = useState("form");
  const [overrideDefaults, setOverrideDefaults] = useState<Record<string, any> | undefined>(undefined);
  // Bumping this key remounts TaskPage so the new defaults are picked up.
  const [formKey, setFormKey] = useState(0);

  function applyDiagramToForm(values: Record<string, any>) {
    setOverrideDefaults(values);
    setFormKey((k) => k + 1);
    setTab("form");
  }

  return (
    <div className="flex h-full flex-col">
      <Tabs value={tab} onValueChange={setTab} className="flex flex-1 flex-col">
        <div className="px-6 pt-4">
          <TabsList>
            <TabsTrigger value="form">Form</TabsTrigger>
            <TabsTrigger value="diagram">Diagram Builder</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="form" className="flex-1 min-h-0">
          <TaskPage
            key={formKey}
            taskId="rtl_subsystem_integration"
            overrideDefaults={overrideDefaults}
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
        </TabsContent>

        <TabsContent value="diagram" className="flex-1 min-h-0 overflow-auto p-6">
          <div className="mb-3">
            <h1 className="text-2xl font-semibold">Subsystem Diagram Builder</h1>
            <p className="text-sm text-muted-foreground">
              Drag blocks onto the canvas, connect them, and click <em>Apply to Form</em> to
              populate the integration form from your design.
            </p>
          </div>
          <DiagramBuilder onApply={applyDiagramToForm} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
