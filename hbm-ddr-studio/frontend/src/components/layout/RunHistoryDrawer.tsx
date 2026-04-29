import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger, SheetClose } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { History, Eye } from "lucide-react";
import { api, type RunSummary } from "@/lib/api";
import { StatusBadge } from "@/components/task/StatusBadge";

function dur(a: string | null, b: string | null) {
  if (!a) return "—";
  const s = Math.max(0, Math.round(((b ? new Date(b).getTime() : Date.now()) - new Date(a).getTime()) / 1000));
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  return `${Math.floor(s / 3600)}h`;
}

export function RunHistoryDrawer() {
  const [open, setOpen] = useState(false);
  const [runs, setRuns] = useState<RunSummary[]>([]);

  useEffect(() => {
    if (!open) return;
    let mounted = true;
    const load = () => api.listRuns().then((r) => mounted && setRuns(r)).catch(() => null);
    load();
    const i = setInterval(load, 3000);
    return () => { mounted = false; clearInterval(i); };
  }, [open]);

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="sm">
          <History className="mr-2 h-4 w-4" />Run history
        </Button>
      </SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Recent runs</SheetTitle>
          <SheetDescription>All tasks across this Studio. Click a run to view its detail.</SheetDescription>
        </SheetHeader>
        <ScrollArea className="-mr-2 mt-2 flex-1 pr-2">
          <ul className="space-y-2">
            {runs.length === 0 && <li className="text-sm text-muted-foreground">No runs yet.</li>}
            {runs.slice(0, 50).map((r) => {
              const groupGuess = r.task_id.startsWith("rtl_") ? "rtl" : r.task_id.startsWith("dv_") ? "dv" : "pm";
              return (
                <li key={r.run_id} className="rounded-md border border-border bg-card/50 p-2.5">
                  <div className="flex items-start gap-3">
                    <StatusBadge state={r.state} />
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium">{r.task_id}</div>
                      <div className="font-mono text-[10px] text-muted-foreground">{r.run_id}</div>
                      <div className="mt-0.5 text-[11px] text-muted-foreground">
                        {r.started_at ? new Date(r.started_at).toLocaleString() : "—"} · {dur(r.started_at, r.ended_at)} · {r.source}
                      </div>
                    </div>
                    <SheetClose asChild>
                      <Link to={`/${groupGuess}/${r.task_id}`}>
                        <Button size="icon" variant="ghost" aria-label="Open"><Eye className="h-3.5 w-3.5" /></Button>
                      </Link>
                    </SheetClose>
                  </div>
                </li>
              );
            })}
          </ul>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
}
