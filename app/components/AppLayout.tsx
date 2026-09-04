"use client";

import { usePathname } from "next/navigation";
import Sidebar from "./sidebar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isFullWidthPage = pathname === "/" || pathname === "/login" || pathname === "/signup";

  if (isFullWidthPage) {
    return <main className="w-full min-h-screen">{children}</main>;
  }

  return (
    <div className="flex min-h-screen w-full bg-slate-50 text-slate-900 transition-colors duration-300 dark:bg-[#050d0a] dark:text-white">
      {/* Sticky Desktop Sidebar */}
      <div className="sticky top-0 h-screen shrink-0 z-40 hidden md:block">
        <Sidebar />
      </div>

      {/* Main Page Area */}
      <main className="flex-1 min-w-0 overflow-x-hidden">
        {children}
      </main>
    </div>
  );
}
