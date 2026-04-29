import { cn } from "@/lib/utils";
import type { RunStatus } from "@/lib/api";

const META: Record<RunStatus, { label: string; dot: string; pill: string }> = {
  idle:                  { label: "Idle",         dot: "bg-muted-foreground/40 border border-muted-foreground/40", pill: "bg-muted/60 text-muted-foreground" },
  queued:                { label: "Queued",       dot: "bg-blue-400 shadow-[0_0_5px_rgba(96,165,250,0.6)]",         pill: "bg-blue-500/15 text-blue-300" },
  scheduled:             { label: "Scheduled",    dot: "bg-blue-400 shadow-[0_0_5px_rgba(96,165,250,0.6)]",         pill: "bg-blue-500/15 text-blue-300" },
  running:               { label: "Running",      dot: "bg-primary shadow-[0_0_6px_hsl(var(--primary)/0.7)] animate-[hds-pulse_1.4s_ease-in-out_infinite]", pill: "bg-primary/18 text-primary" },
  "paused-needs-input":  { label: "Needs input",  dot: "bg-warning shadow-[0_0_5px_hsl(var(--warning)/0.6)] animate-pulse", pill: "bg-warning/18 text-warning" },
  success:               { label: "Success",      dot: "bg-success shadow-[0_0_5px_hsl(var(--success)/0.6)]",       pill: "bg-success/15 text-success" },
  failed:                { label: "Failed",       dot: "bg-destructive shadow-[0_0_5px_hsl(var(--destructive)/0.6)]", pill: "bg-destructive/15 text-destructive" },
  cancelled:             { label: "Cancelled",    dot: "bg-muted-foreground/50",                                    pill: "bg-muted/70 text-muted-foreground" },
  interrupted:           { label: "Interrupted",  dot: "bg-muted-foreground/50",                                    pill: "bg-muted/70 text-muted-foreground" },
};

export function StatusDot({ state }: { state: RunStatus }) {
  const m = META[state] ?? META.idle;
  return <span className={cn("inline-block h-2 w-2 rounded-full", m.dot)} aria-label={m.label} />;
}

export function StatusBadge({ state, className }: { state: RunStatus; className?: string }) {
  const m = META[state] ?? META.idle;
  return (
    <span className={cn(
      "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10.5px] font-bold uppercase tracking-[0.06em]",
      m.pill,
      className
    )}>
      <span className={cn("h-1.5 w-1.5 rounded-full", m.dot)} />
      {m.label}
    </span>
  );
}
