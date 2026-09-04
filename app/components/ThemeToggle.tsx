"use client";

import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

const emptySubscribe = () => () => {};

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const mounted = useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false,
  );

  if (!mounted) {
    return <div className="h-10 w-10 rounded-full border border-slate-300 dark:border-white/20" />;
  }

  return (
    <button
      type="button"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-300 bg-slate-100 text-lg transition hover:bg-slate-200 dark:border-white/20 dark:bg-white/10 dark:hover:bg-white/20"
      aria-label="Toggle theme"
    >
      {theme === "dark" ? "☀️" : "🌙"}
    </button>
  );
}

