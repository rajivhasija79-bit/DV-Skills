import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, type RunStatus, type RunSummary, type TaskDescriptor } from "@/lib/api";
import { ArrowUpRight, Cpu, Layers, Play, FileText, ScrollText, BookOpen, ShieldCheck, Coins, BarChart3, GitBranch, ListChecks, LineChart, PieChart, Wrench, Activity, Search } from "lucide-react";
import { cn } from "@/lib/utils";

const ICONS: Record<string, any> = {
  cpu: Cpu, layers: Layers, play: Play, "file-text": FileText, "scroll-text": ScrollText,
  "book-open": BookOpen, "shield-check": ShieldCheck, coins: Coins, "bar-chart-3": BarChart3,
  "git-branch": GitBranch, "list-checks": ListChecks, "line-chart": LineChart, "pie-chart": PieChart,
  wrench: Wrench, activity: Activity,
};

const META: Record<string, { eyebrow: string; title: string; desc: string }> = {
  rtl: {
    eyebrow: "RTL track",
    title: "RTL Toolkit",
    desc: "Subsystem integration, SDC generation, and RTL review flows for the DDR/HBM subsystem.",
  },
  dv: {
    eyebrow: "DV track",
    title: "DV Workbench",
    desc: "Testplan, testbench, VIP integration, RAL, coverage, debug, and regression — full functional verification suite.",
  },
  pm: {
    eyebrow: "Program Management",
    title: "PM Central",
    desc: "RTL completion, milestones, regression health, JIRA trends, and a combined program overview.",
  },
};

function statusMeta(state?: RunStatus) {
  switch (state) {
    case "running":
    case "queued":
    case "scheduled":
    case "paused-needs-input":
      return { label: "Running",  bar: "bg-primary",     pill: "bg-primary/20 text-primary",      bgPulse: true };
    case "success":
      return { label: "Success",  bar: "bg-success",     pill: "bg-success/15 text-success",      bgPulse: false };
    case "failed":
    case "interrupted":
    case "cancelled":
      return { label: "Failed",   bar: "bg-destructive", pill: "bg-destructive/15 text-destructive", bgPulse: false };
    default:
      return { label: "Idle",     bar: "bg-transparent", pill: "bg-muted/70 text-muted-foreground", bgPulse: false };
  }
}

function GROUP_LABEL(g: string) {
  return g.toUpperCase();
}

function SkillCard({ task, latestState }: { task: TaskDescriptor; latestState?: RunStatus }) {
  const Icon = ICONS[task.icon || ""] || Wrench;
  const meta = statusMeta(latestState);
  const route = `/${task.group}/${task.id}`;
  return (
    <Link
      to={route}
      className="group relative flex flex-col overflow-hidden rounded-xl border border-border bg-card transition-colors hover:bg-card/70"
    >
      <div className={cn("h-[2px] w-full", meta.bar, meta.bgPulse && "animate-[hds-shimmer_1.2s_ease-in-out_infinite]")} />
      <span aria-hidden className="absolute left-0 top-0 h-full w-[3px] origin-bottom scale-y-0 bg-primary transition-transform duration-300 group-hover:scale-y-100" />
      <div className="flex flex-1 flex-col gap-3 p-5">
        <div className="flex items-start justify-between">
          <span className="inline-block rounded bg-primary/15 px-1.5 py-[3px] text-[9.5px] font-extrabold uppercase tracking-[0.12em] text-primary">
            {GROUP_LABEL(task.group)}
          </span>
          <span className="grid h-7 w-7 place-items-center rounded-md bg-muted/60 text-muted-foreground transition-colors group-hover:bg-primary/15 group-hover:text-primary">
            <Icon className="h-3.5 w-3.5" strokeWidth={2.4} />
          </span>
        </div>
        <div>
          <div className="text-[14px] font-extrabold leading-tight tracking-[-0.02em]">{task.title}</div>
          {task.description && (
            <div className="mt-1.5 line-clamp-2 text-[12px] leading-[1.55] text-muted-foreground">
              {task.description}
            </div>
          )}
        </div>
        <div className="mt-auto flex items-center justify-between pt-2">
          <span className={cn("inline-flex items-center gap-1 rounded-full px-2 py-[3px] text-[10px] font-bold uppercase tracking-[0.05em]", meta.pill)}>
            {meta.label}
          </span>
          <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground transition-all group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
        </div>
      </div>
    </Link>
  );
}

export function GroupPage({ group: groupProp }: { group?: "rtl" | "dv" | "pm" } = {}) {
  const params = useParams<{ group: string }>();
  const group = (groupProp ?? (params.group as "rtl" | "dv" | "pm")) || "rtl";
  const meta = META[group] || META.rtl;
  const [tasks, setTasks] = useState<TaskDescriptor[]>([]);
  const [latest, setLatest] = useState<Record<string, RunStatus>>({});
  const [filter, setFilter] = useState("");

  useEffect(() => {
    api.listTasks().then(setTasks).catch(() => setTasks([]));
    let mounted = true;
    const loadRuns = () => api.listRuns().then((rs: RunSummary[]) => {
      if (!mounted) return;
      const m: Record<string, RunStatus> = {};
      for (const r of rs) if (!m[r.task_id]) m[r.task_id] = r.state;
      setLatest(m);
    }).catch(() => null);
    loadRuns();
    const i = setInterval(loadRuns, 4000);
    return () => { mounted = false; clearInterval(i); };
  }, []);

  const items = useMemo(() => {
    const all = tasks.filter((t) => t.group === group);
    if (!filter.trim()) return all;
    const q = filter.toLowerCase();
    return all.filter((t) => t.title.toLowerCase().includes(q) || (t.description || "").toLowerCase().includes(q));
  }, [tasks, filter, group]);

  return (
    <div className="flex flex-col gap-6 px-8 py-10">
      <div className="flex items-end justify-between gap-4">
        <div className="max-w-2xl">
          <div className="uppercase-eyebrow text-primary">{meta.eyebrow}</div>
          <h1 className="mt-2 bg-gradient-to-br from-primary/90 via-warning/85 to-primary/80 bg-clip-text text-[clamp(28px,3.5vw,44px)] font-black leading-[1.05] tracking-[-0.035em] text-transparent">
            {meta.title}
          </h1>
          <p className="mt-3 text-[14px] leading-[1.55] text-muted-foreground">{meta.desc}</p>
        </div>
        <div className="relative w-72 shrink-0">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            type="text"
            placeholder={`Filter ${meta.title.toLowerCase()}…`}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="h-9 w-full rounded-md border border-input bg-muted/40 pl-8 pr-3 text-[13px] placeholder:text-muted-foreground/70 focus-visible:outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/20"
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-[11px] font-mono text-muted-foreground/70">
          {items.length} of {tasks.filter((t) => t.group === group).length} {group === "pm" ? "dashboards" : "tasks"}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {items.map((t) => (<SkillCard key={t.id} task={t} latestState={latest[t.id]} />))}
        {items.length === 0 && (
          <div className="col-span-full rounded-xl border border-dashed border-border p-8 text-center text-[13px] text-muted-foreground">
            No matches. Drop a YAML in <code className="font-mono">backend/tasks/{group}/</code> to add one.
          </div>
        )}
      </div>
    </div>
  );
}
