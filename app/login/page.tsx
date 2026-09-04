"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import { setStoredUser } from "@/lib/auth";
import FloatingParticles from "../components/FloatingParticles";

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect");

  const roleParam = searchParams.get("role");
  const [role, setRole] = useState<"employee" | "officer">(() => {
    if (roleParam === "officer") return "officer";
    if (redirectUrl === "/analysis") return "officer";
    return "employee";
  });
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();

    const userEmail = email.trim() || (role === "employee" ? "employee@oilindia.in" : "officer@oilindia.in");

    // Save session
    setStoredUser({
      email: userEmail,
      role,
      name: userEmail.split("@")[0].toUpperCase(),
      loggedInAt: Date.now(),
    });

    if (redirectUrl) {
      router.push(redirectUrl);
    } else if (role === "employee") {
      router.push("/submit-report");
    } else {
      router.push("/analysis");
    }
  };

  return (
    <div className="grid w-full max-w-5xl overflow-hidden rounded-3xl border border-white/15 bg-white/10 shadow-2xl backdrop-blur-xl lg:grid-cols-2">
      {/* LEFT SIDE */}
      <div className="hidden flex-col justify-between border-r border-white/10 p-12 text-white lg:flex">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-orange-500 text-xl font-bold">
              S
            </div>

            <div>
              <h1 className="text-2xl font-bold">
                Suraksha<span className="text-orange-400">Setu</span>
              </h1>

              <p className="text-xs tracking-[0.18em] text-slate-300">
                SAFETY INTELLIGENCE PLATFORM
              </p>
            </div>
          </div>

          <h2 className="mt-16 text-4xl font-bold leading-tight">
            Safety starts with
            <span className="block text-orange-400">speaking up.</span>
          </h2>

          <p className="mt-6 max-w-md leading-8 text-slate-300">
            Report unsafe acts, unsafe conditions and near-miss events. Our
            AI helps identify patterns and potential risks before they
            escalate.
          </p>
        </div>

        <div className="border-t border-white/15 pt-6">
          <p className="text-sm text-slate-400">
            AI-powered proactive safety intelligence
          </p>
        </div>
      </div>

      {/* RIGHT SIDE - LOGIN */}
      <div className="bg-white p-8 sm:p-12 dark:bg-[#0a1915]">
        <div className="mb-8">
          <p className="text-sm font-semibold tracking-[0.2em] text-orange-500">
            SECURE ACCESS
          </p>

          <h2 className="mt-3 text-3xl font-bold text-slate-900 dark:text-white">
            Welcome back
          </h2>

          <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
            {redirectUrl
              ? "Please sign in to access the requested portal."
              : "Sign in to access the Safety Intelligence Platform."}
          </p>
        </div>

        {/* Role Selection */}
        <div className="mb-7">
          <p className="mb-3 text-sm font-medium text-slate-700 dark:text-slate-300">
            Select your role
          </p>

          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => setRole("employee")}
              className={`rounded-xl border p-4 text-left transition ${
                role === "employee"
                  ? "border-orange-500 bg-orange-50 dark:bg-orange-500/10"
                  : "border-slate-200 hover:border-orange-300 dark:border-white/10"
              }`}
            >
              <p className="font-semibold text-slate-900 dark:text-white">
                Employee
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Submit reports
              </p>
            </button>

            <button
              type="button"
              onClick={() => setRole("officer")}
              className={`rounded-xl border p-4 text-left transition ${
                role === "officer"
                  ? "border-orange-500 bg-orange-50 dark:bg-orange-500/10"
                  : "border-slate-200 hover:border-orange-300 dark:border-white/10"
              }`}
            >
              <p className="font-semibold text-slate-900 dark:text-white">
                Safety Officer
              </p>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                Dashboard access
              </p>
            </button>
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Official Email
            </label>

            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder={role === "employee" ? "employee@oilindia.in" : "officer@oilindia.in"}
              required
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5 dark:text-white"
            />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
              Password
            </label>

            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
              required
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5 dark:text-white"
            />
          </div>

          <button
            type="submit"
            className="w-full rounded-xl bg-orange-500 py-3.5 font-semibold text-white transition hover:bg-orange-600"
          >
            Sign In →
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
          New to SurakshaSetu?{" "}
          <Link
            href={redirectUrl ? `/signup?redirect=${encodeURIComponent(redirectUrl)}` : "/signup"}
            className="font-semibold text-orange-500 hover:text-orange-600"
          >
            Create an account
          </Link>
        </p>

        {/* Demo Note */}
        <div className="mt-6 rounded-xl border border-orange-200 bg-orange-50 p-4 text-xs leading-6 text-orange-700 dark:border-orange-500/20 dark:bg-orange-500/10 dark:text-orange-300">
          Demo Prototype: Select a role and enter any valid email and
          password to continue.
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-100 transition-colors duration-300 dark:bg-[#06120f]">
      {/* Light Mode Oil India Daylight Background */}
      <div
        className="absolute inset-0 bg-cover bg-center block dark:hidden transition-opacity duration-700 filter brightness-105 contrast-105"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=2560&q=90')",
        }}
      />
      <div className="absolute inset-0 block dark:hidden bg-gradient-to-r from-amber-500/20 via-orange-400/15 to-emerald-500/20 mix-blend-multiply pointer-events-none" />
      <div className="absolute inset-0 block dark:hidden bg-slate-900/40 backdrop-blur-sm pointer-events-none" />

      {/* Dark Mode Oil India Night Refinery Background */}
      <div
        className="absolute inset-0 bg-cover bg-center hidden dark:block transition-opacity duration-700 filter brightness-95 contrast-125"
        style={{
          backgroundImage:
            "url('https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=2560&q=90')",
        }}
      />
      <div className="absolute inset-0 hidden dark:block bg-[#030907]/80 backdrop-blur-sm pointer-events-none" />

      {/* Dynamic Ambient Particles */}
      <FloatingParticles />

      {/* Back Button */}
      <Link
        href="/"
        className="absolute left-6 top-6 z-20 rounded-xl border border-white/30 bg-black/40 px-5 py-3 text-sm font-semibold text-white backdrop-blur-md transition hover:bg-black/60 shadow-lg"
      >
        ← Back to Home
      </Link>

      {/* Main Content */}
      <div className="relative z-10 flex min-h-screen items-center justify-center px-6 py-20">
        <Suspense fallback={<div className="text-white font-bold">Loading...</div>}>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
