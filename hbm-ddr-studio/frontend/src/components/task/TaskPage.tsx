import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useParams } from "react-router-dom";
import { api, type TaskDescriptor } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { Play } from "lucide-react";
import { SchemaForm, type SchemaFormHandle } from "./SchemaForm";
import { RunPane } from "./RunPane";
import { RunHistory } from "./RunHistory";
import { SchedulesTab } from "./SchedulesTab";
import { ScheduleDialog } from "./ScheduleDialog";
import { StatusBadge } from "./StatusBadge";

export function TaskPage({
  extras,
  taskId: taskIdProp,
}: {
  extras?: (cfg: Record<string, any>) => ReactNode;
  taskId?: string;
}) {
  const params = useParams<{ taskId: string }>();
  const taskId = taskIdProp ?? params.taskId;
  const [desc, setDesc] = useState<TaskDescriptor | null>(null);
  const [handle, setHandle] = useState<SchemaFormHandle>({ values: {}, isValid: false, missingKeys: [] });
  const [runId, setRunId] = useState<string | null>(null);
  const [runState, setRunState] = useState<"idle" | "queued" | "running" | "success" | "failed">("idle");
  const [tab, setTab] = useState("run");
  const [schedRefresh, setSchedRefresh] = useState(0);
  const [submitErr, setSubmitErr] = useState<string | null>(null);

  useEffect(() => {
    if (!taskId) return;
    api.getTask(taskId).then(setDesc).catch(() => setDesc(null));
    setRunId(null);
    setRunState("idle");
  }, [taskId]);

  const headerStatus = useMemo<any>(() => {
    if (runId) return runState as any;
    return "idle";
  }, [runId, runState]);

  async function submit() {
    if (!desc) return;
    setSubmitErr(null);
    try {
      const r = await api.run(desc.id, handle.values);
      setRunId(r.run_id);
      setRunState("running");
      setTab("run");
    } catch (e: any) {
      setSubmitErr(e?.detail?.detail ? JSON.stringify(e.detail.detail) : (e?.message || "failed"));
    }
  }

  if (!desc) return <div className="p-8 text-muted-foreground">Loading…</div>;

  const disabled = !handle.isValid;
  // Only regression run and debug get History + Schedules tabs.
  const showHistorySchedules = desc.id === "dv_regression_run" || desc.id === "dv_debug";

  return (
    <div className="grid h-full grid-cols-1 gap-4 p-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <section className="flex flex-col gap-4 min-w-0">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">{desc.group.toUpperCase()}</div>
            <h1 className="text-2xl font-semibold">{desc.title}</h1>
            {desc.description && <div className="text-sm text-muted-foreground">{desc.description}</div>}
          </div>
          <StatusBadge state={headerStatus} />
        </div>

        {extras && extras(handle.values)}

        <Card>
          <CardHeader>
            <CardTitle>Inputs</CardTitle>
            <CardDescription>Required fields are marked with *. Run is enabled once the form is valid.</CardDescription>
          </CardHeader>
          <CardContent>
            <SchemaForm descriptor={desc} onChange={setHandle} />
            <div className="mt-4 flex items-center gap-2">
              <Tooltip>
                <TooltipTrigger asChild>
                  <span>
                    <Button onClick={submit} disabled={disabled}>
                      <Play className="mr-2 h-4 w-4" />Run now
                    </Button>
                  </span>
                </TooltipTrigger>
                {disabled && (
                  <TooltipContent>
                    Missing: {handle.missingKeys.join(", ") || "(form invalid)"}
                  </TooltipContent>
                )}
              </Tooltip>
              {showHistorySchedules && (
                <ScheduleDialog
                  task={desc}
                  config={handle.values}
                  disabled={disabled}
                  onCreated={() => { setSchedRefresh((x) => x + 1); setTab("schedules"); }}
                />
              )}
              {submitErr && <span className="text-xs text-destructive">{submitErr}</span>}
            </div>
          </CardContent>
        </Card>
      </section>

      <section className="flex min-h-[480px] flex-col">
        <Tabs value={tab} onValueChange={setTab} className="flex flex-1 flex-col">
          <TabsList className="self-start">
            <TabsTrigger value="run">Run</TabsTrigger>
            {showHistorySchedules && <TabsTrigger value="history">History</TabsTrigger>}
            {showHistorySchedules && <TabsTrigger value="schedules">Schedules</TabsTrigger>}
          </TabsList>
          <TabsContent value="run" className="flex-1 min-h-0">
            <Card className="h-full overflow-hidden">
              <RunPane runId={runId} />
            </Card>
          </TabsContent>
          {showHistorySchedules && (
            <TabsContent value="history">
              <RunHistory taskId={desc.id} activeRunId={runId} onSelect={(rid) => { setRunId(rid); setTab("run"); }} />
            </TabsContent>
          )}
          {showHistorySchedules && (
            <TabsContent value="schedules">
              <SchedulesTab taskId={desc.id} refreshKey={schedRefresh} />
            </TabsContent>
          )}
        </Tabs>
      </section>
    </div>
  );
}
