import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, RadialBar, RadialBarChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { CheckCircle2, Circle, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import { api, type TaskDescriptor } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sparkline } from "@/components/charts/Sparkline";
import { cn } from "@/lib/utils";

// ---- shared style helpers -----------------------------------------------

const PIE_COLORS = [
  "hsl(var(--destructive))",
  "hsl(var(--warning))",
  "hsl(var(--primary))",
  "hsl(var(--success))",
  "hsl(var(--muted-foreground))",
];

const RAG_COLORS: Record<string, string> = {
  red: "hsl(var(--destructive))",
  amber: "hsl(var(--warning))",
  green: "hsl(var(--success))",
  blue: "hsl(var(--primary))",
};

function accentBorder(a?: string) {
  return a === "destructive" ? "border-l-destructive" :
         a === "success"     ? "border-l-success" :
         a === "warning"     ? "border-l-warning" :
         a === "muted"       ? "border-l-muted-foreground" :
         "border-l-primary";
}

const tooltipStyle = {
  background: "hsl(var(--popover))",
  border: "1px solid hsl(var(--border))",
  borderRadius: 8,
  fontSize: 12,
} as const;

// ---- widgets ------------------------------------------------------------

function KpiTile({ tile, data }: { tile: any; data: any }) {
  const value = data?.kpis?.[tile.metric];
  const delta = tile.delta ? data?.kpis?.[tile.delta] : 0;
  const up = (delta ?? 0) >= 0;
  const isGoodUp = tile.accent === "success" || /resolved/.test(tile.metric || "");
  const goodDirection = isGoodUp ? up : !up;
  return (
    <Card className={cn("border-l-4", accentBorder(tile.accent))}>
      <CardContent className="p-4">
        <div className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{tile.label}</div>
        <div className="mt-1 flex items-baseline gap-3">
          <div className="text-3xl font-semibold tabular-nums">{value ?? "—"}</div>
          {delta !== undefined && delta !== null && (
            <div className={cn(
              "inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[11px] font-semibold",
              goodDirection ? "bg-success/15 text-success" : "bg-destructive/15 text-destructive"
            )}>
              {up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
              {Math.abs(delta)}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function LineWidget({ block, data }: { block: any; data: any }) {
  const series = data?.[block.source] ?? [];
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader>
      <CardContent className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={series} margin={{ top: 6, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey={block.x} stroke="hsl(var(--muted-foreground))" fontSize={11} />
            <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {block.series.map((s: any, i: number) => (
              <Line key={s.key} type="monotone" dataKey={s.key} name={s.label}
                stroke={i === 0 ? "hsl(var(--primary))" : i === 1 ? "hsl(var(--success))" : "hsl(var(--warning))"}
                strokeWidth={1.5} dot={{ r: 2 }} isAnimationActive={false} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function BarWidget({ block, data }: { block: any; data: any }) {
  const series = data?.[block.source] ?? [];
  const stacked = !!block.stacked;
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader>
      <CardContent className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={series} margin={{ top: 6, right: 8, left: -16, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey={block.x} stroke="hsl(var(--muted-foreground))" fontSize={11} />
            <YAxis stroke="hsl(var(--muted-foreground))" fontSize={11} />
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
            {block.series.map((s: any, i: number) => (
              <Bar key={s.key} dataKey={s.key} name={s.label}
                stackId={stacked ? "a" : undefined}
                fill={
                  s.color === "success" ? "hsl(var(--success))" :
                  s.color === "destructive" ? "hsl(var(--destructive))" :
                  s.color === "warning" ? "hsl(var(--warning))" :
                  i === 0 ? "hsl(var(--primary))" : i === 1 ? "hsl(var(--success))" : "hsl(var(--warning))"
                }
                radius={stacked ? 0 : [4, 4, 0, 0]}
                isAnimationActive={false}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function PieWidget({ block, data }: { block: any; data: any }) {
  const arr = (data?.[block.source] ?? []).map((d: any) => ({ name: d[block.name], value: d[block.value] }));
  const inner = block.kind === "donut" ? 45 : 0;
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader>
      <CardContent className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={arr} dataKey="value" nameKey="name"
              cx="50%" cy="50%" innerRadius={inner} outerRadius={85}
              paddingAngle={inner ? 2 : 0} stroke="hsl(var(--background))" isAnimationActive={false}>
              {arr.map((_: any, i: number) => <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />)}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 11 }} />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function RadialWidget({ block, data }: { block: any; data: any }) {
  const arr = (data?.[block.source] ?? []).map((d: any, i: number) => ({
    name: d[block.name], value: d[block.value],
    fill: i % 2 === 0 ? "hsl(var(--primary))" : "hsl(var(--success))",
  }));
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader>
      <CardContent className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart innerRadius={20} outerRadius={110} data={arr} startAngle={90} endAngle={-270}>
            <RadialBar dataKey="value" cornerRadius={6} background isAnimationActive={false} />
            <Legend iconSize={8} layout="vertical" verticalAlign="middle" align="right" wrapperStyle={{ fontSize: 11 }} />
            <Tooltip contentStyle={tooltipStyle} />
          </RadialBarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function GanttWidget({ block, data }: { block: any; data: any }) {
  const items: any[] = data?.[block.source] ?? [];
  if (items.length === 0) return <Card><CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">No items.</CardContent></Card>;
  const min = Math.min(...items.map((i: any) => new Date(i.start).getTime()));
  const max = Math.max(...items.map((i: any) => new Date(i.end).getTime()));
  const today = Date.now();
  const span = Math.max(1, max - min);
  const tracks = Array.from(new Set(items.map((i) => i.track || "default")));
  const TRACK_COLOR = (t: string) => {
    if (t === "RTL") return "hsl(var(--primary))";
    if (t === "DV") return "hsl(var(--success))";
    if (t === "Emulation") return "hsl(var(--warning))";
    return "hsl(var(--muted-foreground))";
  };
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader>
      <CardContent>
        <div className="space-y-3">
          {tracks.map((t) => (
            <div key={t}>
              <div className="mb-1 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
                <span className="inline-block h-2 w-2 rounded-full" style={{ background: TRACK_COLOR(String(t)) }} />
                {t}
              </div>
              <div className="relative h-7 w-full rounded bg-muted/40">
                {/* today line */}
                <div className="absolute top-0 h-7 w-px bg-foreground/60"
                  style={{ left: `${((today - min) / span) * 100}%` }} />
                {items.filter((i: any) => (i.track || "default") === t).map((i: any, idx: number) => {
                  const s = new Date(i.start).getTime(), e = new Date(i.end).getTime();
                  const left = ((s - min) / span) * 100;
                  const width = Math.max(2, ((e - s) / span) * 100);
                  const color = i.status === "slipped" ? "hsl(var(--destructive))" :
                                i.status === "at-risk" ? "hsl(var(--warning))" :
                                TRACK_COLOR(String(t));
                  return (
                    <div key={idx}
                      title={`${i.label}: ${i.start} → ${i.end}`}
                      className="absolute top-1 h-5 rounded text-[10px] text-white px-1 leading-5 truncate"
                      style={{ left: `${left}%`, width: `${width}%`, background: color }}>
                      {i.label}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function HeatmapWidget({ block, data }: { block: any; data: any }) {
  const cells: number[] = data?.[block.source] ?? [];
  const weeks = Math.ceil(cells.length / 7);
  const max = Math.max(1, ...cells);
  const cellOf = (v: number) => {
    const a = Math.min(1, v / max);
    return v === 0 ? "hsl(var(--muted) / 0.4)" : `hsl(var(--primary) / ${0.2 + a * 0.7})`;
  };
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader>
      <CardContent>
        <div className="grid grid-flow-col gap-[3px]" style={{ gridTemplateRows: "repeat(7, 14px)", gridAutoColumns: "14px" }}>
          {cells.map((v, i) => (
            <div key={i} title={`${v} runs`} className="rounded-[3px]" style={{ background: cellOf(v) }} />
          ))}
        </div>
        <div className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground">
          <span>Less</span>
          {[0.2, 0.4, 0.6, 0.8, 1.0].map((a) => (
            <span key={a} className="h-3 w-3 rounded-[2px]" style={{ background: `hsl(var(--primary) / ${a})` }} />
          ))}
          <span>More</span>
          <span className="ml-2">{weeks} weeks</span>
        </div>
      </CardContent>
    </Card>
  );
}

function ChecklistWidget({ block, data }: { block: any; data: any }) {
  const tracks: any[] = data?.[block.source] ?? [];
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader>
      <CardContent>
        <div className="grid gap-3 md:grid-cols-3">
          {tracks.map((t: any) => {
            const done = (t.items || []).filter((i: any) => i.done).length;
            const total = (t.items || []).length;
            return (
              <div key={t.name} className="rounded-md border border-border p-3">
                <div className="flex items-center justify-between text-sm font-semibold">
                  <span>{t.name}</span>
                  <span className="text-muted-foreground tabular-nums">{done}/{total}</span>
                </div>
                <ul className="mt-2 space-y-1 text-xs">
                  {(t.items || []).map((i: any, idx: number) => (
                    <li key={idx} className="flex items-center gap-1.5">
                      {i.done ? <CheckCircle2 className="h-3.5 w-3.5 text-success" /> : <Circle className="h-3.5 w-3.5 text-muted-foreground" />}
                      <span className={i.done ? "text-muted-foreground line-through" : ""}>{i.label}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function RagWidget({ block, data }: { block: any; data: any }) {
  const arr: any[] = data?.[block.source] ?? [];
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-3">
          {arr.map((p: any) => (
            <div key={p.label}
              className="rounded-md border-l-4 px-3 py-2"
              style={{ borderLeftColor: RAG_COLORS[p.color || "blue"] }}>
              <div className="text-[10px] font-semibold uppercase tracking-widest text-muted-foreground">{p.label}</div>
              <div className="mt-0.5 text-2xl font-semibold tabular-nums">{p.count}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function TableWidget({ block, data }: { block: any; data: any }) {
  const rows: any[] = data?.[block.source] ?? [];
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs uppercase tracking-wide text-muted-foreground">
              <tr>{block.columns.map((c: any) => (
                <th key={c.key} className={cn("px-3 py-2", c.align === "right" ? "text-right" : "text-left")}>{c.label}</th>
              ))}</tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} className="border-t border-border">
                  {block.columns.map((c: any) => {
                    if (c.kind === "sparkline") {
                      return <td key={c.key} className="px-3 py-2"><Sparkline data={r[c.key] || []} /></td>;
                    }
                    if (c.kind === "status") {
                      const v = String(r[c.key] || "");
                      const tone = v === "open" ? "destructive" : v === "in_progress" ? "warning" : "success";
                      return <td key={c.key} className="px-3 py-2">
                        <span className={cn(
                          "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium",
                          tone === "destructive" && "bg-destructive/15 text-destructive",
                          tone === "warning" && "bg-warning/15 text-warning",
                          tone === "success" && "bg-success/15 text-success",
                        )}>{v}</span>
                      </td>;
                    }
                    return (
                      <td key={c.key} className={cn("px-3 py-2 tabular-nums", c.align === "right" && "text-right")}>
                        {String(r[c.key] ?? "")}
                      </td>
                    );
                  })}
                </tr>
              ))}
              {rows.length === 0 && <tr><td colSpan={block.columns.length} className="px-3 py-6 text-center text-muted-foreground">No rows.</td></tr>}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}

function FeedWidget({ block, data }: { block: any; data: any }) {
  const items: any[] = data?.[block.source] ?? [];
  return (
    <Card>
      <CardHeader className="pb-2"><CardTitle>{block.title}</CardTitle></CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {items.length === 0 && <li className="text-sm text-muted-foreground">No updates.</li>}
          {items.map((i: any, idx: number) => (
            <li key={idx} className="flex items-start gap-2 text-sm">
              <span className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
              <div>
                <div>{i.text}</div>
                <div className="text-[11px] text-muted-foreground">{i.when}</div>
              </div>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function renderBlock(block: any, data: any, idx: number, fullWidth = false) {
  const cls = fullWidth || block.full_width ? "lg:col-span-2" : "";
  const wrap = (el: any) => <div key={idx} className={cls}>{el}</div>;
  switch (block.kind) {
    case "line":      return wrap(<LineWidget   block={block} data={data} />);
    case "bar":       return wrap(<BarWidget    block={block} data={data} />);
    case "pie":
    case "donut":     return wrap(<PieWidget    block={block} data={data} />);
    case "radial":    return wrap(<RadialWidget block={block} data={data} />);
    case "gantt":     return <div key={idx} className="lg:col-span-2"><GanttWidget block={block} data={data} /></div>;
    case "heatmap":   return wrap(<HeatmapWidget block={block} data={data} />);
    case "checklist": return <div key={idx} className="lg:col-span-2"><ChecklistWidget block={block} data={data} /></div>;
    case "rag":       return wrap(<RagWidget    block={block} data={data} />);
    case "table":     return <div key={idx} className="lg:col-span-2"><TableWidget block={block} data={data} /></div>;
    case "feed":      return wrap(<FeedWidget   block={block} data={data} />);
    default:          return null;
  }
}

// ---- page ---------------------------------------------------------------

export function DashboardPage() {
  const { dashId } = useParams<{ dashId: string }>();
  const [desc, setDesc] = useState<TaskDescriptor | null>(null);
  const [data, setData] = useState<any>(null);
  const [loadedAt, setLoadedAt] = useState<string>("");

  async function load() {
    if (!dashId) return;
    const r = await api.getDashboard(dashId);
    setDesc(r.descriptor);
    setData(r.data);
    setLoadedAt(new Date().toLocaleTimeString());
  }
  useEffect(() => { load(); }, [dashId]); // eslint-disable-line

  const layout = desc?.layout || [];
  const kpiRow = useMemo(() => layout.find((b: any) => b.kind === "kpi_row"), [layout]);
  const others = useMemo(() => layout.filter((b: any) => b.kind !== "kpi_row"), [layout]);

  if (!desc) return <div className="p-8 text-muted-foreground">Loading…</div>;

  return (
    <div className="flex flex-col gap-4 p-6">
      <div className="flex items-end justify-between">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">PM Dashboard</div>
          <h1 className="text-2xl font-semibold">{desc.title}</h1>
          {desc.description && <div className="text-sm text-muted-foreground">{desc.description}</div>}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-muted-foreground">Refreshed {loadedAt}</span>
          <Button size="sm" variant="outline" onClick={load}><RefreshCw className="mr-1.5 h-3.5 w-3.5" />Refresh</Button>
        </div>
      </div>

      {kpiRow && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          {kpiRow.tiles.map((t: any) => <KpiTile key={t.label} tile={t} data={data} />)}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {others.map((b: any, i: number) => renderBlock(b, data, i))}
      </div>
    </div>
  );
}
