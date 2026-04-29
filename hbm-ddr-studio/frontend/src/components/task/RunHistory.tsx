import { useEffect, useState } from "react";
import { api, type RunSummary } from "@/lib/api";
import { StatusBadge } from "./StatusBadge";
import { Button } from "@/components/ui/button";
import { Eye, RotateCw, Trash2 } from "lucide-react";

function fmt(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString();
}
function dur(a: string | null, b: string | null) {
  if (!a) return "—";
  const start = new Date(a).getTime();
  const end = b ? new Date(b).getTime() : Date.now();
  const s = Math.max(0, Math.round((end - start) / 1000));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

export function RunHistory({ taskId, activeRunId, onSelect }: {
  taskId: string;
  activeRunId: string | null;
  onSelect: (runId: string) => void;
}) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let mounted = true;
    const load = () => api.listRuns(taskId).then((r) => mounted && setRuns(r)).catch(() => null);
    load();
    const i = setInterval(load, 3000);
    return () => { mounted = false; clearInterval(i); };
  }, [taskId, tick]);

  return (
    <div className="overflow-x-auto rounded-md border border-border">
      <table className="w-full text-sm">
        <thead className="bg-muted/40 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            <th className="px-3 py-2 text-left">Status</th>
            <th className="px-3 py-2 text-left">Run ID</th>
            <th className="px-3 py-2 text-left">Started</th>
            <th className="px-3 py-2 text-left">Duration</th>
            <th className="px-3 py-2 text-left">Source</th>
            <th className="px-3 py-2"></th>
          </tr>
        </thead>
        <tbody>
          {runs.length === 0 && (
            <tr><td colSpan={6} className="px-3 py-8 text-center text-muted-foreground">No runs yet.</td></tr>
          )}
          {runs.map((r) => (
            <tr key={r.run_id} className={"border-t border-border " + (r.run_id === activeRunId ? "bg-accent/30" : "")}>
              <td className="px-3 py-2"><StatusBadge state={r.state} /></td>
              <td className="px-3 py-2 font-mono text-[11px]">{r.run_id}</td>
              <td className="px-3 py-2 tabular-nums">{fmt(r.started_at)}</td>
              <td className="px-3 py-2 tabular-nums">{dur(r.started_at, r.ended_at)}</td>
              <td className="px-3 py-2 text-muted-foreground capitalize">{r.source}</td>
              <td className="px-3 py-2">
                <div className="flex justify-end gap-1">
                  <Button size="icon" variant="ghost" onClick={() => onSelect(r.run_id)} aria-label="View"><Eye className="h-3.5 w-3.5" /></Button>
                  <Button size="icon" variant="ghost" disabled aria-label="Re-run"><RotateCw className="h-3.5 w-3.5" /></Button>
                  <Button size="icon" variant="ghost" onClick={async () => { await api.deleteRun(r.run_id); setTick((t) => t + 1); }} aria-label="Delete"><Trash2 className="h-3.5 w-3.5" /></Button>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
