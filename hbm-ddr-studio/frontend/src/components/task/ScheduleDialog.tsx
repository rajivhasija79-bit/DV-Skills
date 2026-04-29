import { useState } from "react";
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Calendar, Clock } from "lucide-react";
import { api, type TaskDescriptor } from "@/lib/api";

const COMMON_CRONS = [
  { label: "Every 15 min",        value: "*/15 * * * *" },
  { label: "Hourly (at :07)",     value: "7 * * * *" },
  { label: "Nightly @ 22:00",     value: "0 22 * * *" },
  { label: "Weekdays @ 09:00",    value: "0 9 * * 1-5" },
  { label: "Weekly Mon @ 08:30",  value: "30 8 * * 1" },
];

export function ScheduleDialog({
  task,
  config,
  disabled,
  onCreated,
}: {
  task: TaskDescriptor;
  config: Record<string, unknown>;
  disabled?: boolean;
  onCreated?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [date, setDate] = useState("");
  const [time, setTime] = useState("21:00");
  const [cron, setCron] = useState("0 22 * * *");
  const [tz] = useState<string>(Intl.DateTimeFormat().resolvedOptions().timeZone);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(kind: "once" | "cron") {
    setError(null);
    setBusy(true);
    try {
      const when =
        kind === "once"
          ? { kind: "once" as const, at: new Date(`${date}T${time}:00`).toISOString(), tz }
          : { kind: "cron" as const, cron, tz };
      await api.schedule(task.id, config, when);
      onCreated?.();
      setOpen(false);
    } catch (e: any) {
      setError(e?.detail?.detail ? JSON.stringify(e.detail.detail) : e?.message || "failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" disabled={disabled || !task.schedulable}>
          <Clock className="mr-2 h-4 w-4" />Schedule…
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Schedule “{task.title}”</DialogTitle>
          <DialogDescription>
            Run once at a future time, or on a recurring cron cadence. Times use your timezone: <code className="font-mono">{tz}</code>
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="once">
          <TabsList>
            <TabsTrigger value="once"><Calendar className="mr-1.5 h-3.5 w-3.5" />One-shot</TabsTrigger>
            <TabsTrigger value="cron"><Clock className="mr-1.5 h-3.5 w-3.5" />Cron</TabsTrigger>
          </TabsList>

          <TabsContent value="once" className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Date</Label>
                <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label>Time</Label>
                <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
              </div>
            </div>
            <DialogFooter>
              <Button onClick={() => submit("once")} disabled={busy || !date}>Schedule</Button>
            </DialogFooter>
          </TabsContent>

          <TabsContent value="cron" className="space-y-3">
            <div className="space-y-1.5">
              <Label>Cron expression (5 fields, local time)</Label>
              <Input value={cron} onChange={(e) => setCron(e.target.value)} className="font-mono" />
              <div className="flex flex-wrap gap-1.5 pt-1">
                {COMMON_CRONS.map((p) => (
                  <button key={p.value} type="button" onClick={() => setCron(p.value)}
                    className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground hover:bg-accent">
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <DialogFooter>
              <Button onClick={() => submit("cron")} disabled={busy || !cron}>Schedule</Button>
            </DialogFooter>
          </TabsContent>
        </Tabs>
        {error && <div className="text-xs text-destructive">{error}</div>}
      </DialogContent>
    </Dialog>
  );
}
