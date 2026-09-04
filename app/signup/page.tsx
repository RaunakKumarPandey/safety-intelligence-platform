"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, Suspense } from "react";
import { setStoredUser } from "@/lib/auth";
import FloatingParticles from "../components/FloatingParticles";

function SignupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get("redirect");

  const [role, setRole] = useState<"employee" | "officer">("employee");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [department, setDepartment] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const handleSignup = (e: React.FormEvent) => {
    e.preventDefault();

    const userEmail = email.trim() || (role === "employee" ? "employee@oilindia.in" : "officer@oilindia.in");

    setStoredUser({
      email: userEmail,
      role,
      name: (name.trim() || userEmail.split("@")[0]).toUpperCase(),
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
    <div className="w-full max-w-xl rounded-3xl border border-white/15 bg-white p-8 shadow-2xl sm:p-12 dark:bg-[#0a1915]">
      <div className="mb-8 text-center">
        <p className="text-sm font-semibold tracking-[0.2em] text-orange-500">
          CREATE ACCOUNT
        </p>

        <h1 className="mt-3 text-3xl font-bold text-slate-900 dark:text-white">
          Join Suraksha<span className="text-orange-500">Setu</span>
        </h1>

        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          Create your account to access the Safety Intelligence Platform.
        </p>
      </div>

      {/* Role */}
      <div className="mb-6">
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
              Report safety observations
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
              Monitor risks and reports
            </p>
          </button>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSignup} className="space-y-4">
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Full Name
          </label>
          <input
            required
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter your full name"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5 dark:text-white"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Employee ID
          </label>
          <input
            required
            type="text"
            value={employeeId}
            onChange={(e) => setEmployeeId(e.target.value)}
            placeholder="OIL-EMP-2026"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5 dark:text-white"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Official Email
          </label>
          <input
            required
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={role === "employee" ? "employee@oilindia.in" : "officer@oilindia.in"}
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5 dark:text-white"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Department
          </label>
          <input
            required
            type="text"
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            placeholder="e.g. Drilling Operations"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5 dark:text-white"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Password
          </label>
          <input
            required
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Create a password"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5 dark:text-white"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
            Confirm Password
          </label>
          <input
            required
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            placeholder="Confirm your password"
            className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5 dark:text-white"
          />
        </div>

        <button
          type="submit"
          className="mt-3 w-full rounded-xl bg-orange-500 py-3.5 font-semibold text-white transition hover:bg-orange-600"
        >
          Create Account →
        </button>
      </form>

      {/* Login Link */}
      <p className="mt-6 text-center text-sm text-slate-500 dark:text-slate-400">
        Already have an account?{" "}
        <Link
          href={redirectUrl ? `/login?redirect=${encodeURIComponent(redirectUrl)}` : "/login"}
          className="font-semibold text-orange-500 hover:text-orange-600"
        >
          Sign In
        </Link>
      </p>
    </div>
  );
}

export default function SignupPage() {
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

      {/* Back to Home */}
      <Link
        href="/"
        className="absolute left-6 top-6 z-20 rounded-xl border border-white/30 bg-black/40 px-5 py-3 text-sm font-semibold text-white backdrop-blur-md transition hover:bg-black/60 shadow-lg"
      >
        ← Back to Home
      </Link>

      {/* Main */}
      <div className="relative z-10 flex min-h-screen items-center justify-center px-6 py-20">
        <Suspense fallback={<div className="text-white font-bold">Loading...</div>}>
          <SignupForm />
        </Suspense>
      </div>
    </main>
  );
}
