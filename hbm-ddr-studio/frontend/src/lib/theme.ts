// Lightweight theme controller: persists 'light' | 'dark' | 'system' to localStorage.
import { useEffect, useState } from "react";

export type ThemeMode = "light" | "dark" | "system";
const KEY = "hds-theme";

function applyTheme(mode: ThemeMode) {
  const isDark =
    mode === "dark" ||
    (mode === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", isDark);
}

export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(() => (localStorage.getItem(KEY) as ThemeMode) || "dark");
  useEffect(() => {
    applyTheme(mode);
    localStorage.setItem(KEY, mode);
  }, [mode]);
  useEffect(() => {
    const m = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => mode === "system" && applyTheme("system");
    m.addEventListener("change", handler);
    return () => m.removeEventListener("change", handler);
  }, [mode]);
  return { mode, setMode };
}
