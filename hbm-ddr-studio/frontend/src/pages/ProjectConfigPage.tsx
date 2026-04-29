import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Textarea } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { api, type ProjectConfig, type DocEntry, type KV, type ToolEntry } from "@/lib/api";
import { Plus, Trash2, Save, FolderOpen, GitBranch, Cpu, Wrench, FileText, Box, CheckCircle2 } from "lucide-react";

const SUBSYSTEMS = ["DDR5", "DDR4", "LPDDR5", "LPDDR4", "HBM3", "HBM2E", "GDDR6", "GDDR7"];

const EMPTY: ProjectConfig = {
  name: "",
  subsystem: "DDR5",
  paths: { rtl: "", dv: "", docs: "", scripts: "", output: "" },
  git: { url: "", branch: "main", commit: "" },
  env_vars: [],
  tools: [],
  documents: [],
};

export function ProjectConfigPage() {
  const [cfg, setCfg] = useState<ProjectConfig>(EMPTY);
  const [savedAt, setSavedAt] = useState<string>("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.getProjectConfig().then((c) => setCfg({ ...EMPTY, ...c })).catch(() => null); }, []);

  function update<K extends keyof ProjectConfig>(k: K, v: ProjectConfig[K]) {
    setCfg((p) => ({ ...p, [k]: v }));
  }
  function updatePath(k: keyof ProjectConfig["paths"], v: string) {
    setCfg((p) => ({ ...p, paths: { ...p.paths, [k]: v } }));
  }
  function updateGit(k: keyof ProjectConfig["git"], v: string) {
    setCfg((p) => ({ ...p, git: { ...p.git, [k]: v } }));
  }

  async function save() {
    setBusy(true);
    try {
      await api.putProjectConfig(cfg);
      setSavedAt(new Date().toLocaleTimeString());
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 px-8 py-10">
      <div className="flex items-end justify-between gap-4">
        <div className="max-w-2xl">
          <div className="uppercase-eyebrow text-primary">Project</div>
          <h1 className="mt-2 text-primary text-[clamp(28px,3.5vw,44px)] font-black leading-[1.05] tracking-[-0.035em]">
            Project Config
          </h1>
          <p className="mt-3 text-[14px] leading-[1.55] text-muted-foreground">
            Single source of truth for paths, git, env, tools and documents. Every task run gets these merged into its config automatically.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {savedAt && (
            <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
              <CheckCircle2 className="h-3.5 w-3.5 text-success" /> Saved at {savedAt}
            </span>
          )}
          <Button onClick={save} disabled={busy}>
            <Save className="mr-2 h-4 w-4" />Save
          </Button>
        </div>
      </div>

      {/* Project basics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Box className="h-4 w-4 text-primary" />Project</CardTitle>
          <CardDescription>Name and subsystem flavor.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="name">Project name</Label>
              <Input id="name" value={cfg.name} placeholder="ddrss-1.0" onChange={(e) => update("name", e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Subsystem</Label>
              <Select value={cfg.subsystem} onValueChange={(v) => update("subsystem", v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {SUBSYSTEMS.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Paths */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FolderOpen className="h-4 w-4 text-primary" />Paths</CardTitle>
          <CardDescription>Filesystem locations injected into every task.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {(["rtl", "dv", "docs", "scripts", "output"] as const).map((k) => (
              <div key={k} className="space-y-1.5">
                <Label>{k}</Label>
                <Input value={cfg.paths[k]} placeholder={`./${k}`} onChange={(e) => updatePath(k, e.target.value)} />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Git */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><GitBranch className="h-4 w-4 text-primary" />Git</CardTitle>
          <CardDescription>Repository pinning.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="space-y-1.5 md:col-span-2">
              <Label>URL</Label>
              <Input value={cfg.git.url} placeholder="git@github.com:org/ddr-subsystem.git" onChange={(e) => updateGit("url", e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <Label>Branch</Label>
              <Input value={cfg.git.branch} onChange={(e) => updateGit("branch", e.target.value)} />
            </div>
            <div className="space-y-1.5 md:col-span-3">
              <Label>Commit (pin, optional)</Label>
              <Input value={cfg.git.commit} placeholder="abc1234…" className="font-mono" onChange={(e) => updateGit("commit", e.target.value)} />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Env vars */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Cpu className="h-4 w-4 text-primary" />Environment variables</CardTitle>
          <CardDescription>Exported into every task subprocess (KEY=value).</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2.5">
          {cfg.env_vars.map((e: KV, i: number) => (
            <div key={i} className="flex gap-2">
              <Input className="flex-1 font-mono" placeholder="KEY"
                value={e.key} onChange={(ev) => {
                  const next = [...cfg.env_vars]; next[i] = { ...e, key: ev.target.value }; update("env_vars", next);
                }} />
              <Input className="flex-[2]" placeholder="value"
                value={e.value} onChange={(ev) => {
                  const next = [...cfg.env_vars]; next[i] = { ...e, value: ev.target.value }; update("env_vars", next);
                }} />
              <Button size="icon" variant="ghost" aria-label="Remove"
                onClick={() => update("env_vars", cfg.env_vars.filter((_: KV, j: number) => j !== i))}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={() => update("env_vars", [...cfg.env_vars, { key: "", value: "" }])}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />Add variable
          </Button>
        </CardContent>
      </Card>

      {/* Tools */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><Wrench className="h-4 w-4 text-primary" />Tools</CardTitle>
          <CardDescription>Simulators, synth tools, lint, etc.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2.5">
          {cfg.tools.map((t: ToolEntry, i: number) => (
            <div key={i} className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_2fr_120px_auto]">
              <Input placeholder="name (vcs)" value={t.name}
                onChange={(ev) => { const next = [...cfg.tools]; next[i] = { ...t, name: ev.target.value }; update("tools", next); }} />
              <Input className="font-mono" placeholder="/tools/synopsys/vcs/bin"
                value={t.path}
                onChange={(ev) => { const next = [...cfg.tools]; next[i] = { ...t, path: ev.target.value }; update("tools", next); }} />
              <Input placeholder="2024.03" value={t.version}
                onChange={(ev) => { const next = [...cfg.tools]; next[i] = { ...t, version: ev.target.value }; update("tools", next); }} />
              <Button size="icon" variant="ghost" aria-label="Remove"
                onClick={() => update("tools", cfg.tools.filter((_: ToolEntry, j: number) => j !== i))}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={() => update("tools", [...cfg.tools, { name: "", path: "", version: "" }])}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />Add tool
          </Button>
        </CardContent>
      </Card>

      {/* Documents */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2"><FileText className="h-4 w-4 text-primary" />Documents</CardTitle>
          <CardDescription>PRD, spec, microarchitecture, review docs.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2.5">
          {cfg.documents.map((d: DocEntry, i: number) => (
            <div key={i} className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_2fr_auto]">
              <Input placeholder="label (PRD)" value={d.label}
                onChange={(ev) => { const next = [...cfg.documents]; next[i] = { ...d, label: ev.target.value }; update("documents", next); }} />
              <Input className="font-mono" placeholder="./docs/PRD.md" value={d.path}
                onChange={(ev) => { const next = [...cfg.documents]; next[i] = { ...d, path: ev.target.value }; update("documents", next); }} />
              <Button size="icon" variant="ghost" aria-label="Remove"
                onClick={() => update("documents", cfg.documents.filter((_: DocEntry, j: number) => j !== i))}>
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={() => update("documents", [...cfg.documents, { label: "", path: "" }])}>
            <Plus className="mr-1.5 h-3.5 w-3.5" />Add document
          </Button>
        </CardContent>
      </Card>

      {/* Save again at bottom */}
      <div className="flex items-center justify-end gap-3">
        {savedAt && (
          <span className="inline-flex items-center gap-1 text-[11px] text-muted-foreground">
            <CheckCircle2 className="h-3.5 w-3.5 text-success" /> Saved at {savedAt}
          </span>
        )}
        <Button onClick={save} disabled={busy}>
          <Save className="mr-2 h-4 w-4" />Save project config
        </Button>
      </div>
    </div>
  );
}
