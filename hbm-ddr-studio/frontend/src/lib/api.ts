// Typed fetch wrappers for the FastAPI surface.

export type FormField = {
  key: string;
  type: "text" | "number" | "select" | "multiselect" | "boolean" | "textarea" | "password" | "path" | "file";
  label?: string;
  options?: string[];
  required?: boolean;
  default?: unknown;
  min?: number;
  max?: number;
  placeholder?: string;
  help?: string;
};
export type FormSection = { title: string; fields: FormField[] };

export type TaskDescriptor = {
  id: string;
  title: string;
  group: "rtl" | "dv" | "pm";
  icon?: string;
  description?: string;
  schedulable: boolean;
  script?: { type: string; path: string; arg_mode: string; timeout_s: number };
  form: { sections: FormSection[] };
  // dashboard
  adapter?: string;
  params?: Record<string, unknown>;
  layout?: any[];
  refresh_s?: number;
};

export type RunStatus =
  | "idle" | "queued" | "scheduled" | "running" | "paused-needs-input"
  | "success" | "failed" | "cancelled" | "interrupted";

export type RunSummary = {
  run_id: string;
  task_id: string;
  state: RunStatus;
  started_at: string | null;
  ended_at: string | null;
  exit_code: number | null;
  source: "manual" | "schedule";
  schedule_id?: string | null;
  pending_prompt_ids?: string[];
};

export type RunDetail = RunSummary & {
  stdout_tail: string[];
  stderr_tail: string[];
  open_prompts: PromptSpec[];
};

export type PromptSpec = {
  id: string;
  label: string;
  type: "text" | "password" | "select" | "boolean" | "number";
  options?: string[];
  required?: boolean;
};

export type Schedule = {
  id: string;
  task_id: string;
  config: Record<string, unknown>;
  when: { kind: "once" | "cron"; at?: string; cron?: string; tz?: string };
  next_run_at: string | null;
  enabled: boolean;
  name: string;
};

async function http<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail: any;
    try { detail = await res.json(); } catch { detail = await res.text(); }
    throw Object.assign(new Error(`HTTP ${res.status}`), { status: res.status, detail });
  }
  return res.json() as Promise<T>;
}

export const api = {
  listTasks: () => http<TaskDescriptor[]>("GET", "/api/tasks"),
  getTask: (id: string) => http<TaskDescriptor>("GET", `/api/tasks/${id}`),
  validate: (id: string, config: Record<string, unknown>) =>
    http<{ ok: boolean; missing: string[]; errors: string[] }>("POST", `/api/tasks/${id}/validate`, { config }),
  run: (id: string, config: Record<string, unknown>) =>
    http<{ run_id: string }>("POST", `/api/tasks/${id}/run`, { config }),
  schedule: (id: string, config: Record<string, unknown>, when: Schedule["when"]) =>
    http<Schedule>("POST", `/api/tasks/${id}/schedule`, { config, when }),
  listRuns: (taskId?: string) =>
    http<RunSummary[]>("GET", `/api/runs${taskId ? `?task_id=${encodeURIComponent(taskId)}` : ""}`),
  getRun: (rid: string) => http<RunDetail>("GET", `/api/runs/${rid}`),
  cancelRun: (rid: string) => http<{ ok: boolean }>("POST", `/api/runs/${rid}/cancel`),
  deleteRun: (rid: string) => http<{ ok: boolean }>("DELETE", `/api/runs/${rid}`),
  respond: (rid: string, prompt_id: string, value: unknown) =>
    http<{ ok: boolean }>("POST", `/api/runs/${rid}/respond`, { prompt_id, value }),
  listSchedules: (taskId?: string) =>
    http<Schedule[]>("GET", `/api/schedules${taskId ? `?task_id=${encodeURIComponent(taskId)}` : ""}`),
  patchSchedule: (sid: string, body: Partial<{ enabled: boolean }>) =>
    http<Schedule>("PATCH", `/api/schedules/${sid}`, body),
  deleteSchedule: (sid: string) => http<{ ok: boolean }>("DELETE", `/api/schedules/${sid}`),
  listDashboards: () => http<TaskDescriptor[]>("GET", "/api/dashboards"),
  getDashboard: (id: string) =>
    http<{ descriptor: TaskDescriptor; data: any }>("GET", `/api/dashboards/${id}`),
  getProjectConfig: () => http<ProjectConfig>("GET", "/api/project-config"),
  putProjectConfig: (cfg: ProjectConfig) =>
    http<{ ok: boolean; saved: ProjectConfig }>("PUT", "/api/project-config", cfg),
};

export type KV = { key: string; value: string };
export type ToolEntry = { name: string; path: string; version: string };
export type DocEntry = { label: string; path: string };
export type ProjectConfig = {
  name: string;
  subsystem: string;
  paths: { rtl: string; dv: string; docs: string; scripts: string; output: string };
  git: { url: string; branch: string; commit: string };
  env_vars: KV[];
  tools: ToolEntry[];
  documents: DocEntry[];
};
