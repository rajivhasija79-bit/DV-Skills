import { ThemeToggle } from "./ThemeToggle";
import { RunHistoryDrawer } from "./RunHistoryDrawer";
import { Button } from "@/components/ui/button";
import { Settings, Search } from "lucide-react";

export function Topbar() {
  return (
    <header
      className="flex h-[var(--header-h)] shrink-0 items-center gap-3 border-b px-5"
      style={{
        background: "hsl(var(--chrome))",
        color: "hsl(var(--chrome-foreground))",
        borderColor: "hsl(var(--chrome-border))",
      }}
    >
      <div className="relative flex-1 max-w-2xl">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2" style={{ color: "hsl(var(--chrome-muted))" }} />
        <input
          type="text"
          placeholder="Search tasks, runs, dashboards…   ⌘K"
          className="h-9 w-full rounded-md border bg-[hsl(var(--chrome-hover))] pl-8 pr-3 text-[13px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:border-primary"
          style={{ borderColor: "hsl(var(--chrome-border))" }}
        />
      </div>
      <RunHistoryDrawer />
      <Button variant="ghost" size="icon" aria-label="Settings"><Settings className="h-4 w-4" /></Button>
      <ThemeToggle />
    </header>
  );
}
