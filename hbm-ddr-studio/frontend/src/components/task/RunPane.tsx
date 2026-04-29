import { useEffect, useRef, useState } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { StatusBadge } from "./StatusBadge";
import { Copy, Download, X as XIcon } from "lucide-react";
import { api, type RunStatus, type PromptSpec } from "@/lib/api";
import { subscribeRun } from "@/lib/ws";
import { cn } from "@/lib/utils";

type Line = { stream: "stdout" | "stderr"; line: string };

export function RunPane({ runId }: { runId: string | null }) {
  const [lines, setLines] = useState<Line[]>([]);
  const [state, setState] = useState<RunStatus>("idle");
  const [prompt, setPrompt] = useState<PromptSpec | null>(null);
  const [answer, setAnswer] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const scrollerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setLines([]);
    setState("idle");
    setPrompt(null);
    if (!runId) return;
    let cancelled = false;
    api.getRun(runId).then((r) => {
      if (cancelled) return;
      setState(r.state);
      setLines(r.stdout_tail.map((l) => ({ stream: "stdout", line: l })));
      if (r.open_prompts.length > 0) setPrompt(r.open_prompts[0]);
    });
    const unsub = subscribeRun(runId, (e) => {
      if (e.event === "log") setLines((prev) => [...prev, { stream: e.stream, line: e.line }]);
      if (e.event === "status") setState(e.state as RunStatus);
      if (e.event === "prompt") setPrompt(e.prompt as PromptSpec);
    });
    return () => { cancelled = true; unsub(); };
  }, [runId]);

  useEffect(() => {
    const el = scrollerRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [lines.length]);

  async function submitPrompt() {
    if (!runId || !prompt) return;
    setSubmitting(true);
    try {
      await api.respond(runId, prompt.id, answer);
      setPrompt(null);
      setAnswer("");
    } finally {
      setSubmitting(false);
    }
  }

  async function cancel() {
    if (!runId) return;
    await api.cancelRun(runId).catch(() => null);
  }

  const text = lines.map((l) => l.line).join("\n");

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 border-b border-border bg-card/40 px-3 py-2">
        <StatusBadge state={state} />
        <span className="font-mono text-[11px] text-muted-foreground">{runId ?? "no active run"}</span>
        <div className="ml-auto flex items-center gap-1">
          <Button variant="ghost" size="sm" disabled={!text} onClick={() => navigator.clipboard?.writeText(text)}>
            <Copy className="mr-1 h-3.5 w-3.5" />Copy
          </Button>
          <Button
            variant="ghost"
            size="sm"
            disabled={!text}
            onClick={() => {
              const blob = new Blob([text], { type: "text/plain" });
              const a = document.createElement("a");
              a.href = URL.createObjectURL(blob);
              a.download = `${runId || "run"}.log`;
              a.click();
            }}
          >
            <Download className="mr-1 h-3.5 w-3.5" />Save
          </Button>
          {(state === "running" || state === "paused-needs-input" || state === "queued") && (
            <Button variant="outline" size="sm" onClick={cancel}>
              <XIcon className="mr-1 h-3.5 w-3.5" />Cancel
            </Button>
          )}
        </div>
      </div>

      {prompt && (
        <div className="border-b border-warning/40 bg-warning/10 p-3">
          <div className="text-xs font-semibold text-warning">Script needs input</div>
          <div className="mt-2 flex items-end gap-2">
            <div className="flex-1 space-y-1">
              <Label>{prompt.label}</Label>
              <Input
                type={prompt.type === "password" ? "password" : "text"}
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                autoFocus
              />
            </div>
            <Button onClick={submitPrompt} disabled={submitting || (prompt.required && !answer)}>
              Send
            </Button>
          </div>
        </div>
      )}

      <ScrollArea className="flex-1 bg-[#070605]">
        <div ref={scrollerRef} className="h-full overflow-auto py-2 font-mono text-[12px] leading-[1.7]">
          {lines.length === 0 && (
            <div className="px-4 py-2 text-muted-foreground/70">No output yet. Submit the form to start a run.</div>
          )}
          {lines.map((l, i) => (
            <div key={i} className={cn(
              "flex gap-3 px-4 py-px",
              l.stream === "stderr" ? "text-[#E8A87C]" : "text-[#D4C9BC]"
            )}>
              <span className="w-12 shrink-0 text-right text-[9.5px] text-white/15 tabular-nums">{String(i + 1).padStart(4, "0")}</span>
              <span className="whitespace-pre-wrap break-words">{l.line || "\u00A0"}</span>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
