import { NavLink } from "react-router-dom";
import { useEffect, useState } from "react";
import { ChevronDown, Cpu, Layers, Play, FileText, ScrollText, BookOpen, ShieldCheck, Coins, BarChart3, GitBranch, ListChecks, LineChart, PieChart, Wrench, Activity, Zap, Sliders, Users } from "lucide-react";
import { api, type RunStatus, type TaskDescriptor } from "@/lib/api";
import { cn } from "@/lib/utils";

const ICONS: Record<string, any> = {
  cpu: Cpu, layers: Layers, play: Play, "file-text": FileText, "scroll-text": ScrollText,
  "book-open": BookOpen, "shield-check": ShieldCheck, coins: Coins, "bar-chart-3": BarChart3,
  "git-branch": GitBranch, "list-checks": ListChecks, "line-chart": LineChart, "pie-chart": PieChart,
  wrench: Wrench, activity: Activity, users: Users,
};

const GROUP_TITLES: Record<string, string> = {
  rtl: "RTL Toolkit",
  dv:  "DV Workbench",
  pm:  "PM Central",
};
const GROUP_ICONS: Record<string, any> = { rtl: Cpu, dv: Layers, pm: BarChart3 };
const COLLAPSE_KEY = "hds-sidebar-collapsed";

function statusDot(state?: RunStatus | "idle") {
  switch (state) {
    case "running":
    case "queued":
    case "scheduled":
    case "paused-needs-input":
      return "bg-primary shadow-[0_0_6px_hsl(var(--primary)/0.65)] animate-[hds-pulse_1.4s_ease-in-out_infinite]";
    case "success":
      return "bg-success shadow-[0_0_5px_hsl(var(--success)/0.6)]";
    case "failed":
    case "cancelled":
    case "interrupted":
      return "bg-destructive shadow-[0_0_5px_hsl(var(--destructive)/0.6)]";
    default:
      return "bg-muted-foreground/25 border border-muted-foreground/40";
  }
}

function loadCollapsed(): Record<string, boolean> {
  try { return JSON.parse(localStorage.getItem(COLLAPSE_KEY) || "{}"); } catch { return {}; }
}
function saveCollapsed(v: Record<string, boolean>) {
  try { localStorage.setItem(COLLAPSE_KEY, JSON.stringify(v)); } catch { /* noop */ }
}

export function AppSidebar({ tasks }: { tasks: TaskDescriptor[] }) {
  const groups: Record<string, TaskDescriptor[]> = { rtl: [], dv: [], pm: [] };
  for (const t of tasks) groups[t.group].push(t);

  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(loadCollapsed);
  useEffect(() => { saveCollapsed(collapsed); }, [collapsed]);
  const toggle = (g: string) => setCollapsed((p) => ({ ...p, [g]: !p[g] }));

  const [latest, setLatest] = useState<Record<string, RunStatus | "idle">>({});
  useEffect(() => {
    let mounted = true;
    const load = () => api.listRuns().then((rs) => {
      if (!mounted) return;
      const m: Record<string, RunStatus | "idle"> = {};
      for (const r of rs) if (!m[r.task_id]) m[r.task_id] = r.state;
      setLatest(m);
    }).catch(() => null);
    load();
    const i = setInterval(load, 4000);
    return () => { mounted = false; clearInterval(i); };
  }, []);

  return (
    <aside
      className="flex h-full w-[var(--sidebar-w)] shrink-0 flex-col border-r"
      style={{
        background: "hsl(var(--chrome))",
        color: "hsl(var(--chrome-foreground))",
        borderColor: "hsl(var(--chrome-border))",
      }}
    >
      {/* Brand */}
      <NavLink
        to="/"
        className="flex h-[var(--header-h)] shrink-0 items-center gap-2.5 border-b px-5 hover:bg-[hsl(var(--chrome-hover))]"
        style={{ borderColor: "hsl(var(--chrome-border))" }}
      >
        <div className="grid h-7 w-7 place-items-center rounded-md bg-primary text-primary-foreground glow-primary">
          <Zap className="h-3.5 w-3.5" strokeWidth={2.6} />
        </div>
        <div className="leading-tight">
          <div className="text-[15px] font-extrabold tracking-tight">HBM-DDR</div>
          <div className="text-[9px] font-bold uppercase tracking-[0.2em]" style={{ color: "hsl(var(--chrome-muted))" }}>Studio</div>
        </div>
      </NavLink>

      <nav className="flex-1 overflow-y-auto py-3 scrollbar-thin">
        {/* Project Config — fixed top entry */}
        <ul className="mb-3">
          <li>
            <NavLink
              to="/config"
              className={({ isActive }) =>
                cn(
                  "group relative mx-2.5 my-[1px] flex items-center gap-2.5 rounded-md border border-transparent px-3 py-1.5 text-sm transition-colors",
                  isActive
                    ? "border-primary/30 bg-primary/12 text-primary"
                    : "text-[hsl(var(--chrome-foreground))] hover:border-[hsl(var(--chrome-border))] hover:bg-[hsl(var(--chrome-hover))] hover:text-[hsl(var(--chrome-strong))]"
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && <span className="absolute -left-px top-1.5 bottom-1.5 w-[3px] rounded-r bg-primary" />}
                  <Sliders className={cn("h-3.5 w-3.5 shrink-0 opacity-80", isActive && "text-primary opacity-100")} />
                  <span className="truncate flex-1 font-semibold">Project Config</span>
                </>
              )}
            </NavLink>
          </li>
        </ul>

        <div className="mx-3 my-2 h-px bg-border/70" />

        {(["rtl", "dv", "pm"] as const).map((g) => {
          const isCollapsed = !!collapsed[g];
          const GroupIcon = GROUP_ICONS[g];
          return (
            <div key={g} className="mb-2">
              <div className="flex items-stretch px-2.5">
                <NavLink
                  to={`/${g}`}
                  end
                  className={({ isActive }) =>
                    cn(
                      "flex flex-1 items-center gap-2 rounded-md px-2.5 py-2 transition-colors",
                      isActive
                        ? "text-primary"
                        : "text-[hsl(var(--chrome-strong))] hover:bg-[hsl(var(--chrome-hover))]"
                    )
                  }
                >
                  {({ isActive }) => (
                    <>
                      <GroupIcon className={cn("h-4 w-4 shrink-0", isActive ? "text-primary" : "text-muted-foreground")} strokeWidth={2.2} />
                      <span className="flex-1 truncate text-[13px] font-bold tracking-tight">
                        {GROUP_TITLES[g]}
                      </span>
                      <span className={cn("rounded px-1.5 py-px text-[10px] font-mono", isActive ? "bg-primary/15 text-primary" : "bg-muted/60 text-muted-foreground")}>
                        {groups[g].length}
                      </span>
                    </>
                  )}
                </NavLink>
                <button
                  type="button"
                  aria-label={`${isCollapsed ? "Expand" : "Collapse"} ${GROUP_TITLES[g]}`}
                  onClick={() => toggle(g)}
                  className="ml-1 grid h-9 w-7 shrink-0 place-items-center rounded-md text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                >
                  <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", isCollapsed && "-rotate-90")} />
                </button>
              </div>

              {!isCollapsed && (
                <ul className="mt-1">
                  {groups[g].map((t) => {
                    const Icon = ICONS[t.icon || ""] || Wrench;
                    const to = `/${g}/${t.id}`;
                    const dot = statusDot(latest[t.id]);
                    return (
                      <li key={t.id}>
                        <NavLink
                          to={to}
                          className={({ isActive }) =>
                            cn(
                              "group relative mx-2.5 my-[1px] flex items-center gap-2.5 rounded-md border border-transparent px-3 py-1.5 text-sm transition-colors",
                              isActive
                                ? "border-primary/30 bg-primary/12 text-primary"
                                : "text-[hsl(var(--chrome-foreground))] hover:border-[hsl(var(--chrome-border))] hover:bg-[hsl(var(--chrome-hover))] hover:text-[hsl(var(--chrome-strong))]"
                            )
                          }
                        >
                          {({ isActive }) => (
                            <>
                              {isActive && <span className="absolute -left-px top-1.5 bottom-1.5 w-[3px] rounded-r bg-primary" />}
                              <Icon className={cn("h-3.5 w-3.5 shrink-0 opacity-80 group-hover:opacity-100", isActive && "text-primary opacity-100")} />
                              <span className="truncate flex-1">{t.title}</span>
                              {g !== "pm" && <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", dot)} />}
                            </>
                          )}
                        </NavLink>
                      </li>
                    );
                  })}
                  {groups[g].length === 0 && (
                    <li className="px-5 py-1 text-xs text-muted-foreground/70">No items</li>
                  )}
                </ul>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
