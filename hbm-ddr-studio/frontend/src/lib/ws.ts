// WebSocket client for /ws/runs/<run_id>

export type WsEvent =
  | { event: "log"; stream: "stdout" | "stderr"; line: string }
  | { event: "status"; state: string; exit_code?: number }
  | { event: "prompt"; prompt: { id: string; label: string; type: string; options?: string[]; required?: boolean } };

export function subscribeRun(runId: string, onEvent: (e: WsEvent) => void): () => void {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const url = `${proto}://${location.host}/ws/runs/${encodeURIComponent(runId)}`;
  const ws = new WebSocket(url);
  ws.onmessage = (m) => {
    try { onEvent(JSON.parse(m.data)); } catch { /* noop */ }
  };
  return () => { try { ws.close(); } catch { /* noop */ } };
}
