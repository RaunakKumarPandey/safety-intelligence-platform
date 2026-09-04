"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import ThemeToggle from "./ThemeToggle";
import { getStoredUser, clearStoredUser, UserSession } from "@/lib/auth";

const menuItems = [
  { name: "Public Portal", href: "/", icon: "🌐" },
  { name: "Submit Report", href: "/submit-report", icon: "📝" },
  { name: "Risk Analysis", href: "/analysis", icon: "📊" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<UserSession | null>(null);

  useEffect(() => {
    setUser(getStoredUser());
  }, [pathname]);

  const handleSignOut = () => {
    clearStoredUser();
    setUser(null);
    router.push("/login");
  };

  return (
    <aside className="flex h-full w-64 flex-col border-r border-slate-200 bg-white/90 p-5 backdrop-blur-xl transition-colors duration-300 dark:border-white/10 dark:bg-[#050d0a]/95">
      {/* Logo */}
      <Link href="/" className="mb-8 flex items-center gap-3 px-2">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500 to-amber-600 font-extrabold text-xl text-white shadow-lg shadow-orange-500/25">
          <span className="font-orbitron">OIL</span>
        </div>

        <div>
          <h1 className="text-base font-extrabold tracking-tight text-slate-900 dark:text-white">
            Suraksha<span className="text-orange-500">Setu</span>
          </h1>

          <p className="text-[9px] font-bold tracking-[0.2em] text-slate-400 dark:text-slate-400 uppercase">
            Oil India Limited
          </p>
        </div>
      </Link>

      {/* Navigation */}
      <nav className="flex flex-1 flex-col gap-1.5">
        <div className="px-3 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-400">
          Navigation
        </div>
        {menuItems.map((item) => {
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3.5 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                isActive
                  ? "bg-gradient-to-r from-orange-500 to-amber-500 text-white shadow-md shadow-orange-500/20"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-white/5 dark:hover:text-white"
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {item.name}
            </Link>
          );
        })}

        {/* User Account info item */}
        {user ? (
          <div className="mt-4 rounded-2xl border border-orange-500/20 bg-orange-500/5 p-3.5 dark:border-orange-500/30">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400">
                {user.role === "officer" ? "Safety Officer" : "Field Employee"}
              </span>
              <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
            </div>
            <p className="mt-1 truncate text-xs font-semibold text-slate-800 dark:text-slate-200">
              {user.email}
            </p>
            <button
              type="button"
              onClick={handleSignOut}
              className="mt-3 block w-full rounded-lg border border-slate-200 bg-white py-1.5 text-center text-xs font-medium text-red-500 transition hover:bg-red-50 dark:border-white/10 dark:bg-black/20 dark:hover:bg-red-500/10"
            >
              Sign Out
            </button>
          </div>
        ) : (
          <Link
            href="/login"
            className="mt-4 flex items-center gap-3.5 rounded-xl border border-orange-500/30 bg-orange-500/10 px-4 py-3 text-sm font-semibold text-orange-600 transition hover:bg-orange-500 hover:text-white dark:text-orange-400"
          >
            <span className="text-base">🛡️</span>
            Sign In / Access
          </Link>
        )}
      </nav>

      {/* Quick Theme + System active block */}
      <div className="space-y-3 pt-4">
        <div className="flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 dark:border-white/10 dark:bg-white/[0.02]">
          <span className="text-xs font-medium text-slate-600 dark:text-slate-400">Appearance</span>
          <ThemeToggle />
        </div>

        <div className="rounded-2xl border border-slate-200 bg-gradient-to-b from-slate-50 to-slate-100/80 p-4 dark:border-white/10 dark:from-white/[0.04] dark:to-transparent">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-slate-900 dark:text-white">
              AI SIF Radar
            </span>
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>

          <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
            Real-time NLP screening active for OIL rigs & pipeline reports.
          </p>
        </div>
      </div>
    </aside>
  );
}
