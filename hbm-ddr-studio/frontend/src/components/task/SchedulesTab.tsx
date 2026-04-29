import { useEffect, useState } from "react";
import { api, type Schedule } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Trash2 } from "lucide-react";

export function SchedulesTab({ taskId, refreshKey }: { taskId: string; refreshKey: number }) {
  const [items, setItems] = useState<Schedule[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    api.listSchedules(taskId).then(setItems).catch(() => setItems([]));
  }, [taskId, tick, refreshKey]);

  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left">Schedule</th>
            <th className="px-3 py-2 text-left">When</th>
            <th className="px-3 py-2 text-left">Next run</th>
            <th className="px-3 py-2 text-left">Enabled</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {items.length === 0 && (
            <tr><td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">No schedules yet. Use “Schedule…” next to Run.</td></tr>
          )}
          {items.map((s) => (
            <tr key={s.id} className="border-t border-border">
              <td className="px-3 py-2 font-mono text-[11px]">{s.id}</td>
              <td className="px-3 py-2">
                {s.when.kind === "once" ? <>Once at <span className="font-mono">{s.when.at}</span></> :
                  <>Cron <span className="font-mono">{s.when.cron}</span></>}
              </td>
              <td className="px-3 py-2 tabular-nums">{s.next_run_at ? new Date(s.next_run_at).toLocaleString() : "—"}</td>
              <td className="px-3 py-2">
                <Switch
                  checked={s.enabled}
                  onCheckedChange={async (v) => { await api.patchSchedule(s.id, { enabled: v }); setTick((t) => t + 1); }}
                />
              </td>
              <td className="px-3 py-2">
                <Button size="icon" variant="ghost" onClick={async () => { await api.deleteSchedule(s.id); setTick((t) => t + 1); }} aria-label="Delete">
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
