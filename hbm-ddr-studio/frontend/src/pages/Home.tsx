import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Cpu, Layers, BarChart3 } from "lucide-react";
import { api, type TaskDescriptor } from "@/lib/api";

const ENTRIES = [
  { g: "rtl" as const, title: "RTL Toolkit",   desc: "Subsystem integration, SDC, RTL review.",              Icon: Cpu },
  { g: "dv"  as const, title: "DV Workbench",  desc: "Testplan, TB, VIP, RAL, coverage, debug, regression.", Icon: Layers },
  { g: "pm"  as const, title: "PM Central",    desc: "Feature completion, milestones, regression, JIRA.",    Icon: BarChart3 },
];

export default function Home() {
  const [tasks, setTasks] = useState<TaskDescriptor[]>([]);
  useEffect(() => { api.listTasks().then(setTasks).catch(() => setTasks([])); }, []);
  const counts: Record<string, number> = { rtl: 0, dv: 0, pm: 0 };
  for (const t of tasks) counts[t.group] = (counts[t.group] || 0) + 1;

  return (
    <div className="flex flex-col gap-10 px-8 py-10">
      <div className="max-w-3xl">
        <div className="uppercase-eyebrow text-primary">DDR · HBM · LPDDR · GDDR</div>
        <h1 className="mt-2 bg-gradient-to-br from-primary/90 via-warning/85 to-primary/80 bg-clip-text text-[clamp(36px,5vw,56px)] font-black leading-[1.05] tracking-[-0.04em] text-transparent">
          Memory Subsystem<br />Studio
        </h1>
        <p className="mt-4 max-w-2xl text-[14px] leading-[1.55] text-muted-foreground">
          One cockpit for the memory subsystem — invoke RTL & DV tasks with form-driven inputs, see live logs and clear status, schedule jobs, and track program health across RTL, DV, Emulation and JIRA.
        </p>
      </div>

      <section>
        <div className="uppercase-eyebrow mb-3">Tracks</div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
          {ENTRIES.map(({ g, title, desc, Icon }) => (
            <Link
              key={g}
              to={`/${g}`}
              className="group relative flex flex-col overflow-hidden rounded-xl border border-border bg-card p-6 transition-colors hover:bg-card/70"
            >
              <span aria-hidden className="absolute left-0 top-0 h-full w-[3px] origin-bottom scale-y-0 bg-primary transition-transform duration-300 group-hover:scale-y-100" />
              <div className="flex items-start justify-between">
                <div className="grid h-10 w-10 place-items-center rounded-md bg-primary/15 text-primary">
                  <Icon className="h-5 w-5" strokeWidth={2.2} />
                </div>
                <ArrowUpRight className="h-4 w-4 text-muted-foreground transition-all group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-primary" />
              </div>
              <div className="mt-5">
                <div className="text-[18px] font-extrabold tracking-tight">{title}</div>
                <div className="mt-1.5 text-[13px] leading-[1.55] text-muted-foreground">{desc}</div>
              </div>
              <div className="mt-5 inline-flex items-center gap-1.5 text-[10.5px] font-bold uppercase tracking-[0.06em] text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                {counts[g] ?? 0} {counts[g] === 1 ? "item" : "items"}
              </div>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
