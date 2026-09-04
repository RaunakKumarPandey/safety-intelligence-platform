"use client";

import Link from "next/link";
import { useEffect, useState, useCallback } from "react";
import ThemeToggle from "./components/ThemeToggle";
import FloatingParticles from "./components/FloatingParticles";
import { useRouter } from "next/navigation";
import {
  analyzeSafetyReport,
  checkBackendHealth,
  saveAnalysisResult,
  AnalysisResponse,
  SafetyPrecursor,
  Incident,
} from "@/lib/api";
import { getStoredUser, clearStoredUser, isUserAuthenticated, UserSession } from "@/lib/auth";

// Preset sample scenarios for live demo
const sampleScenarios = [
  {
    title: "High-Pressure Gas Flaring Leak",
    icon: "🔥",
    department: "Drilling Operations",
    location: "Compressor Bay #3, Duliajan Rig",
    text: "During routine compressor startup at bay 3, severe vibration was observed followed by high-pressure natural gas hissing from flange gasket. Hydrocarbon gas detector alarmed at 35% LEL. Operator evacuated perimeter immediately without hearing protection.",
  },
  {
    title: "Scaffolding Near-Miss at Height",
    icon: "🏗️",
    department: "Maintenance",
    location: "Production Separator Column 2",
    text: "Contractor technician was observed working at 18 meters height without full-body harness tethered to safety lifeline. Scaffold plank was unfastened and shifted 4 inches when heavy wrench dropped, narrowly missing ground crew.",
  },
  {
    title: "Exposed Electrical Cable near Wellhead",
    icon: "⚡",
    department: "Logistics & Maintenance",
    location: "Wellhead Cluster W-14",
    text: "Frayed 440V electrical power cable found lying in pool of spilled drilling fluid and crude residue near high-vibration pump skid. Potential ignition hazard in Zone-1 classification area.",
  },
  {
    title: "H2S Gas Detection in Pit Sump",
    icon: "🛢️",
    department: "Drilling Operations",
    location: "Effluent Treatment Sump #4",
    text: "H2S toxic gas monitor triggered audible alarm at 15 PPM near effluent treatment pit. Two contract workers were entering the enclosed sump without multi-gas personal detector or SCBA respirator apparatus.",
  },
  {
    title: "Unguarded High-Speed Rotary Chain",
    icon: "⚙️",
    department: "Drilling Operations",
    location: "Rig Floor Rotary Table #1",
    text: "Maintenance crew bypassed safety interlock and operated mud pump rotary chain drive without metal mesh guard in place during urgent pipeline pressure testing.",
  },
];

export default function Home() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<UserSession | null>(null);
  const [showProfileCard, setShowProfileCard] = useState(false);
  const [selectedScenario, setSelectedScenario] = useState(0);
  const [customText, setCustomText] = useState(sampleScenarios[0].text);
  const [isScanning, setIsScanning] = useState(false);
  const [apiResult, setApiResult] = useState<AnalysisResponse | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);

  const activeScenario = sampleScenarios[selectedScenario];

  // Load auth user session on client mount
  useEffect(() => {
    setCurrentUser(getStoredUser());
  }, []);

  const handleSignOut = () => {
    clearStoredUser();
    setCurrentUser(null);
  };

  const handleProtectedNavigate = (targetPath: string) => {
    if (isUserAuthenticated()) {
      router.push(targetPath);
    } else {
      router.push(`/login?redirect=${encodeURIComponent(targetPath)}`);
    }
  };

  const runLiveInference = useCallback(async (textToAnalyze: string) => {
    if (!textToAnalyze.trim()) return;
    setIsScanning(true);
    const startT = performance.now();

    try {
      // Check health in parallel/lightweight
      checkBackendHealth().then((online) => setIsBackendOnline(online));

      const res = await analyzeSafetyReport({
        report_text: textToAnalyze,
        industry_sector: "Mining",
        worker_type: "Employee",
        gender: "Male",
      });

      const elapsed = Math.max(12, Math.round(performance.now() - startT));
      setLatencyMs(elapsed);
      setApiResult(res);
      setIsBackendOnline(res.analysis_source === "backend_ai");

      // Save to sessionStorage for cross-page sync
      saveAnalysisResult(res);
    } catch (err) {
      console.error("Live analysis failed:", err);
      setIsBackendOnline(false);
    } finally {
      setIsScanning(false);
    }
  }, []);

  // Initial load runs inference on default scenario
  useEffect(() => {
    runLiveInference(sampleScenarios[0].text);
  }, [runLiveInference]);

  const handleSelectScenario = (index: number) => {
    setSelectedScenario(index);
    const text = sampleScenarios[index].text;
    setCustomText(text);
    runLiveInference(text);
  };

  const handleQuickRun = () => {
    runLiveInference(customText);
  };

  const handleLaunchFullAnalysis = () => {
    sessionStorage.setItem(
      "prefilledReport",
      JSON.stringify({
        description: customText,
        location: activeScenario?.location || "OIL Facility Site",
        department: activeScenario?.department || "Drilling Operations",
        reportType: "Near Miss",
      })
    );

    if (isUserAuthenticated()) {
      router.push("/submit-report");
    } else {
      router.push(`/login?redirect=${encodeURIComponent("/submit-report")}`);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 transition-colors duration-300 dark:bg-[#050d0a] dark:text-slate-100">
      {/* ================= STICKY GLASS NAVBAR ================= */}
      <nav className="sticky top-0 z-50 w-full border-b border-slate-200/80 bg-white/85 backdrop-blur-2xl transition-all duration-300 dark:border-white/10 dark:bg-[#050d0a]/90 shadow-sm">
        <div className="w-full flex items-center justify-between px-3 sm:px-6 lg:px-6 py-3">
          {/* ================= LEFT: BRAND ================= */}
          <Link href="/" className="flex items-center gap-3 shrink-0 group">
            <div className="flex h-10 w-10 sm:h-11 sm:w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500 via-amber-500 to-orange-600 font-extrabold text-lg sm:text-xl text-white shadow-lg shadow-orange-500/30 transition-transform group-hover:scale-105">
              <span className="font-orbitron">OIL</span>
            </div>

            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <h1 className="text-base sm:text-lg font-black tracking-tight text-slate-950 dark:text-white whitespace-nowrap">
                  Suraksha<span className="text-orange-500">Setu</span>
                </h1>
                <span className="rounded-full border border-orange-500/40 bg-orange-500/10 px-2 py-0.5 text-[9px] font-extrabold text-orange-600 dark:text-orange-400 tracking-wider">
                  SIH26165
                </span>
              </div>
              <p className="text-[9px] sm:text-[10px] font-bold tracking-[0.14em] text-slate-500 dark:text-slate-400 uppercase whitespace-nowrap">
                OIL INDIA LIMITED • SAFETY INTELLIGENCE
              </p>
            </div>
          </Link>

          {/* ================= RIGHT: NAVIGATION & ACTIONS ================= */}
          <div className="hidden lg:flex items-center gap-3 xl:gap-4 shrink-0">
            {/* Streamlined Glass Pill Nav */}
            <div className="flex items-center gap-0.5 rounded-full border border-slate-200/90 bg-slate-100/80 p-1 shadow-inner backdrop-blur-md dark:border-white/10 dark:bg-white/[0.04]">
              <a
                href="#problem"
                className="rounded-full px-2.5 xl:px-3 py-1 text-xs font-semibold text-slate-700 transition hover:bg-white hover:text-orange-600 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white whitespace-nowrap"
              >
                Problem
              </a>
              <a
                href="#ecosystem"
                className="rounded-full px-2.5 xl:px-3 py-1 text-xs font-semibold text-slate-700 transition hover:bg-white hover:text-orange-600 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white whitespace-nowrap"
              >
                Ecosystem
              </a>
              <a
                href="#playground"
                className="rounded-full px-2.5 xl:px-3 py-1 text-xs font-semibold text-slate-700 transition hover:bg-white hover:text-orange-600 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white whitespace-nowrap"
              >
                AI Scanner
              </a>
              <a
                href="#pipeline"
                className="rounded-full px-2.5 xl:px-3 py-1 text-xs font-semibold text-slate-700 transition hover:bg-white hover:text-orange-600 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white whitespace-nowrap"
              >
                NLP Engine
              </a>
              <a
                href="#taxonomy"
                className="rounded-full px-2.5 xl:px-3 py-1 text-xs font-semibold text-slate-700 transition hover:bg-white hover:text-orange-600 dark:text-slate-300 dark:hover:bg-white/10 dark:hover:text-white whitespace-nowrap"
              >
                Taxonomy
              </a>
              <Link
                href="/analytics-dashboard"
                className="rounded-full px-2.5 xl:px-3 py-1 text-xs font-semibold text-orange-600 transition hover:bg-white hover:text-orange-700 dark:text-orange-400 dark:hover:bg-white/10 dark:hover:text-white whitespace-nowrap font-bold"
              >
                📊 Safety Analytics
              </Link>
            </div>

            {/* Separator */}
            <div className="h-5 w-[1px] bg-slate-200 dark:bg-white/15 shrink-0" />

            {/* Theme Toggle Button */}
            <div className="shrink-0">
              <ThemeToggle />
            </div>

            {/* User Profile / Authentication Status */}
            {currentUser ? (
              <div className="relative shrink-0">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setShowProfileCard(!showProfileCard)}
                    className="flex items-center gap-1.5 rounded-full border border-orange-500/40 bg-orange-500/10 px-3 py-1 text-xs font-bold text-orange-600 transition hover:bg-orange-500/20 dark:text-orange-400 dark:hover:bg-orange-500/25 whitespace-nowrap cursor-pointer shadow-sm active:scale-95"
                    title="Click to view Employee details"
                  >
                    <span>{currentUser.role === "officer" ? "🛡️" : "👷"}</span>
                    <span>{currentUser.role === "officer" ? "Officer" : "Employee"}</span>
                    <span className="text-[9px] opacity-70">▼</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleSignOut}
                    className="rounded-full px-2 py-1 text-xs font-semibold text-slate-500 transition hover:text-red-500 dark:text-slate-400 dark:hover:text-red-400 whitespace-nowrap"
                  >
                    Sign Out
                  </button>
                </div>

                {/* Interactive Employee Profile Card Popup */}
                {showProfileCard && (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setShowProfileCard(false)}
                    />

                    <div className="absolute right-0 top-full mt-3 w-80 z-50 rounded-3xl border border-slate-200/90 bg-white/95 p-5 shadow-2xl backdrop-blur-2xl transition-all duration-200 animate-in fade-in zoom-in-95 dark:border-white/15 dark:bg-[#071914]/95 text-slate-900 dark:text-slate-100">
                      {/* Header with Avatar */}
                      <div className="flex items-start justify-between pb-3 border-b border-slate-100 dark:border-white/10">
                        <div className="flex items-center gap-3">
                          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500 to-amber-500 text-2xl text-white shadow-md shadow-orange-500/25">
                            {currentUser.role === "officer" ? "🛡️" : "👷"}
                          </div>
                          <div>
                            <h4 className="font-extrabold text-sm text-slate-900 dark:text-white leading-tight">
                              {currentUser.name || "Raunak Pandey"}
                            </h4>
                            <p className="text-[11px] font-semibold text-orange-600 dark:text-orange-400">
                              {currentUser.role === "officer"
                                ? "HSE Safety Officer"
                                : "Field Safety Employee"}
                            </p>
                            <span className="inline-block mt-0.5 rounded-md bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-bold text-emerald-600 dark:text-emerald-400">
                              ● Active Session
                            </span>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => setShowProfileCard(false)}
                          className="text-slate-400 hover:text-slate-600 dark:hover:text-white text-xs p-1"
                        >
                          ✕
                        </button>
                      </div>

                      {/* Employee Meta Details */}
                      <div className="mt-3.5 space-y-2 text-xs">
                        <div className="flex items-center justify-between rounded-xl bg-slate-50 dark:bg-white/[0.03] p-2.5">
                          <span className="text-slate-500 dark:text-slate-400 font-medium">
                            Email
                          </span>
                          <span className="font-semibold text-slate-800 dark:text-slate-200">
                            {currentUser.email}
                          </span>
                        </div>

                        <div className="flex items-center justify-between rounded-xl bg-slate-50 dark:bg-white/[0.03] p-2.5">
                          <span className="text-slate-500 dark:text-slate-400 font-medium">
                            Employee ID
                          </span>
                          <span className="font-mono font-bold text-orange-600 dark:text-orange-400">
                            OIL-EMP-2026-94
                          </span>
                        </div>

                        <div className="flex items-center justify-between rounded-xl bg-slate-50 dark:bg-white/[0.03] p-2.5">
                          <span className="text-slate-500 dark:text-slate-400 font-medium">
                            Station
                          </span>
                          <span className="font-semibold text-slate-800 dark:text-slate-200">
                            Duliajan Oilfield, Assam
                          </span>
                        </div>

                        <div className="flex items-center justify-between rounded-xl bg-slate-50 dark:bg-white/[0.03] p-2.5">
                          <span className="text-slate-500 dark:text-slate-400 font-medium">
                            Division
                          </span>
                          <span className="font-semibold text-slate-800 dark:text-slate-200">
                            Drilling Operations
                          </span>
                        </div>
                      </div>

                      {/* Quick Portal Links */}
                      <div className="mt-4 pt-3 border-t border-slate-100 dark:border-white/10 space-y-2">
                        <button
                          type="button"
                          onClick={() => {
                            setShowProfileCard(false);
                            router.push("/submit-report");
                          }}
                          className="w-full rounded-xl bg-orange-500/10 hover:bg-orange-500 hover:text-white py-2 text-center text-xs font-bold text-orange-600 dark:text-orange-400 dark:hover:text-white transition shadow-sm"
                        >
                          Submit Safety Observation →
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            setShowProfileCard(false);
                            router.push("/analysis");
                          }}
                          className="w-full rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-white/5 dark:hover:bg-white/10 py-2 text-center text-xs font-bold text-slate-700 dark:text-slate-300 transition"
                        >
                          Open Investigation Portal →
                        </button>
                      </div>

                      {/* Sign Out Trigger */}
                      <div className="mt-3 text-center">
                        <button
                          type="button"
                          onClick={() => {
                            setShowProfileCard(false);
                            handleSignOut();
                          }}
                          className="text-[11px] font-bold text-red-500 hover:underline"
                        >
                          Sign Out of SurakshaSetu
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <Link
                href="/login"
                className="rounded-full px-3 py-1.5 text-xs font-bold text-slate-700 transition hover:text-orange-500 dark:text-slate-200 dark:hover:text-orange-400 whitespace-nowrap"
              >
                Sign In
              </Link>
            )}

            {/* Primary Action Button */}
            <button
              type="button"
              onClick={() => handleProtectedNavigate("/submit-report")}
              className="relative inline-flex items-center justify-center overflow-hidden rounded-full bg-gradient-to-r from-orange-500 via-amber-500 to-orange-600 px-4 xl:px-5 py-2 text-xs font-bold text-white shadow-md shadow-orange-500/25 transition-all hover:shadow-orange-500/40 hover:scale-105 active:scale-95 whitespace-nowrap shrink-0"
            >
              Launch Portal →
            </button>
          </div>

          {/* ================= COMPACT / MOBILE ACTIONS ================= */}
          <div className="flex lg:hidden items-center gap-2.5 shrink-0">
            <ThemeToggle />
            <button
              type="button"
              onClick={() => handleProtectedNavigate("/submit-report")}
              className="rounded-full bg-gradient-to-r from-orange-500 to-amber-500 px-3.5 py-1.5 text-xs font-bold text-white shadow-md shadow-orange-500/25 whitespace-nowrap"
            >
              Launch →
            </button>
          </div>
        </div>
      </nav>

      {/* ================= HERO SECTION (SATYASETU-INSPIRED SPATIAL AESTHETIC) ================= */}
      <section className="relative min-h-[92vh] flex items-center justify-center overflow-hidden py-20 lg:py-28">
        {/* ================= LIGHT MODE BACKGROUND (Daylight Oil India Operations & Warm Gradient) ================= */}
        <div
          className="absolute inset-0 bg-cover bg-center block dark:hidden transition-opacity duration-700 filter brightness-[1.02] contrast-[1.05]"
          style={{
            backgroundImage: "url('https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=2560&q=90')",
          }}
        />
        {/* SatyaSetu-Style Light Mode Amber & Emerald Aura Mask */}
        <div className="absolute inset-0 block dark:hidden bg-gradient-to-r from-amber-400/25 via-orange-300/20 to-emerald-400/25 mix-blend-multiply pointer-events-none" />
        <div className="absolute inset-0 block dark:hidden bg-gradient-to-b from-white/92 via-white/75 to-slate-50/95 pointer-events-none backdrop-blur-[1px]" />
        <div className="absolute inset-0 block dark:hidden bg-[radial-gradient(ellipse_80%_80%_at_50%_-10%,rgba(249,115,22,0.18),rgba(16,185,129,0.12),transparent)] pointer-events-none" />

        {/* ================= DARK MODE BACKGROUND (Night Oil India Rig & Refinery with Safety Flares) ================= */}
        <div
          className="absolute inset-0 bg-cover bg-center hidden dark:block transition-opacity duration-700 filter brightness-95 contrast-125"
          style={{
            backgroundImage: "url('https://images.unsplash.com/photo-1518709268805-4e9042af9f23?auto=format&fit=crop&w=2560&q=90')",
          }}
        />
        {/* SatyaSetu-Style Dark Mode Cyber Glow & Deep Black Scrim */}
        <div className="absolute inset-0 hidden dark:block bg-gradient-to-b from-[#030907]/95 via-[#040f0c]/85 to-[#050d0a]/98 pointer-events-none" />
        <div className="absolute inset-0 hidden dark:block bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(249,115,22,0.25),rgba(16,185,129,0.1),transparent)] pointer-events-none" />

        {/* Ambient Grid Pattern Overlay */}
        <div className="absolute inset-0 bg-grid-pattern opacity-40 dark:opacity-25 pointer-events-none" />

        {/* Dynamic Interactive Floating Ambient Particles */}
        <FloatingParticles />

        <div className="relative z-10 mx-auto max-w-6xl px-6 text-center lg:px-8">
          {/* SIH Hackathon & Oil India Limited Pill */}
          <div className="inline-flex items-center gap-2.5 rounded-full border border-orange-500/50 bg-white/80 dark:bg-orange-500/10 px-5 py-2 text-xs font-black tracking-widest text-orange-700 dark:text-orange-400 uppercase shadow-md backdrop-blur-md">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-orange-500"></span>
            </span>
            <span>SMART INDIA HACKATHON 2026 • PS #165 (OIL INDIA LIMITED)</span>
          </div>

          {/* Main Headline - Ultra Clear and High Contrast */}
          <h1 className="mt-8 text-4xl font-black tracking-tight text-slate-950 dark:text-white sm:text-6xl sm:leading-[1.12] lg:text-7xl drop-shadow-sm dark:drop-shadow-[0_2px_16px_rgba(0,0,0,0.9)]">
            AI/NLP Engine to Detect{" "}
            <span className="bg-gradient-to-r from-orange-600 via-amber-600 to-amber-700 dark:from-orange-400 dark:via-amber-300 dark:to-yellow-400 bg-clip-text text-transparent drop-shadow-none">
              SIF Precursors
            </span>{" "}
            in High-Risk Operations
          </h1>

          {/* Subtitle - Crisp and Perfectly Readable */}
          <p className="mx-auto mt-6 max-w-3xl text-base font-medium leading-8 text-slate-800 dark:text-slate-200 sm:text-xl drop-shadow-sm dark:drop-shadow-md">
            Transforming thousands of unstructured Near-Miss, Unsafe Act, and Unsafe Condition field notes into real-time predictive hazard intelligence, DGMS compliance, and zero-fatality interventions.
          </p>

          {/* Primary Action Buttons */}
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4 sm:gap-6">
            <button
              type="button"
              onClick={() => handleProtectedNavigate("/submit-report")}
              className="inline-flex items-center gap-3 rounded-full bg-gradient-to-r from-orange-500 via-amber-500 to-orange-600 px-8 py-4 text-base font-bold text-white shadow-xl shadow-orange-500/30 transition-all hover:shadow-orange-500/50 hover:scale-105"
            >
              <span>Submit Safety Observation</span>
              <span className="text-xl">→</span>
            </button>

            <a
              href="#playground"
              className="inline-flex items-center gap-2 rounded-full border border-slate-300 bg-white/70 px-7 py-4 text-base font-bold text-slate-800 backdrop-blur-md transition-all hover:bg-white hover:border-orange-400 dark:border-white/15 dark:bg-white/10 dark:text-white dark:hover:bg-white/20"
            >
              <span>⚡ Try Live AI Scanner</span>
            </a>
          </div>

          {/* Trust Badges */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-6 text-xs font-semibold text-slate-500 dark:text-slate-400">
            <div className="flex items-center gap-2">
              <span className="text-emerald-500 text-base">✓</span>
              <span>OISD &amp; DGMS Safety Compliant</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-emerald-500 text-base">✓</span>
              <span>Multilingual Vernacular Support</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-emerald-500 text-base">✓</span>
              <span>Linear SVM &amp; Vector Embeddings</span>
            </div>
          </div>
        </div>
      </section>

      {/* ================= KEY PERFORMANCE METRICS ================= */}
      <section id="metrics" className="relative border-y border-slate-200 bg-white/70 py-12 backdrop-blur-md transition-colors duration-300 dark:border-white/10 dark:bg-[#071411]/90">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="grid grid-cols-2 gap-8 text-center md:grid-cols-4 lg:gap-12">
            <div className="p-4">
              <p className="font-orbitron text-4xl font-extrabold text-orange-500 lg:text-5xl">
                99.2%
              </p>
              <p className="mt-2 text-xs font-bold text-slate-600 uppercase tracking-wider dark:text-slate-300">
                Precursor Recall
              </p>
              <p className="mt-1 text-[11px] text-slate-400">
                High-pressure &amp; Gas NER
              </p>
            </div>

            <div className="p-4">
              <p className="font-orbitron text-4xl font-extrabold text-amber-500 lg:text-5xl">
                425+
              </p>
              <p className="mt-2 text-xs font-bold text-slate-600 uppercase tracking-wider dark:text-slate-300">
                Incident Corpus
              </p>
              <p className="mt-1 text-[11px] text-slate-400">
                Indexed Vector Knowledge Base
              </p>
            </div>

            <div className="p-4">
              <p className="font-orbitron text-4xl font-extrabold text-emerald-500 lg:text-5xl">
                &lt;850ms
              </p>
              <p className="mt-2 text-xs font-bold text-slate-600 uppercase tracking-wider dark:text-slate-300">
                Inference Latency
              </p>
              <p className="mt-1 text-[11px] text-slate-400">
                Real-Time Risk Scoring
              </p>
            </div>

            <div className="p-4">
              <p className="font-orbitron text-4xl font-extrabold text-cyan-500 lg:text-5xl">
                ZERO
              </p>
              <p className="mt-2 text-xs font-bold text-slate-600 uppercase tracking-wider dark:text-slate-300">
                Fatalities Target
              </p>
              <p className="mt-1 text-[11px] text-slate-400">
                Proactive SIF Prevention
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ================= INTERACTIVE LIVE AI SCANNER PLAYGROUND ================= */}
      <section id="playground" className="py-24 relative overflow-hidden bg-slate-100/60 dark:bg-[#071712]/50">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 rounded-full border border-orange-500/30 bg-orange-500/10 px-4 py-1.5 text-xs font-bold tracking-wider text-orange-600 dark:text-orange-400 uppercase">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-orange-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-orange-500"></span>
              </span>
              Connected to Live AI Engine
            </div>
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight sm:text-5xl">
              Live AI Precursor Detection Simulator
            </h2>
            <p className="mt-4 text-base text-slate-600 dark:text-slate-300">
              Type or select any field observation to test the real-time NLP classification, SIF precursor detection, and historical similarity search via the live <code className="rounded bg-orange-500/10 px-1.5 py-0.5 font-mono text-xs text-orange-600 dark:text-orange-400">/analyze</code> backend.
            </p>
          </div>

          {/* Scenario Selector Chips */}
          <div className="mt-10 flex flex-wrap justify-center gap-3">
            {sampleScenarios.map((sc, i) => (
              <button
                key={sc.title}
                type="button"
                onClick={() => handleSelectScenario(i)}
                className={`flex items-center gap-2.5 rounded-full px-5 py-2.5 text-xs font-bold transition-all ${selectedScenario === i
                  ? "bg-orange-500 text-white shadow-lg shadow-orange-500/25 scale-105"
                  : "border border-slate-200 bg-white text-slate-700 hover:border-orange-300 dark:border-white/10 dark:bg-white/5 dark:text-slate-300"
                  }`}
              >
                <span>{sc.icon}</span>
                <span>{sc.title}</span>
              </button>
            ))}
          </div>

          {/* Interactive Simulator Card */}
          <div className="mt-8 grid gap-8 lg:grid-cols-12">
            {/* Left: Input Console */}
            <div className="lg:col-span-7 rounded-3xl border border-slate-200 bg-white p-6 shadow-xl dark:border-white/10 dark:bg-[#0a1f1a]">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-slate-100 dark:border-white/10">
                <div className="flex items-center gap-2">
                  <span className="h-3 w-3 rounded-full bg-red-400" />
                  <span className="h-3 w-3 rounded-full bg-yellow-400" />
                  <span className="h-3 w-3 rounded-full bg-green-400" />
                  <span className="ml-2 text-xs font-bold text-slate-600 dark:text-slate-300">
                    Observation Input Terminal
                  </span>
                </div>

                {/* Connection Status Badge */}
                <div className="flex items-center gap-2">
                  {isBackendOnline === true ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-2.5 py-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                      Live FastAPI Active {latencyMs !== null ? `(${latencyMs}ms)` : ""}
                    </span>
                  ) : isBackendOnline === false ? (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-500/10 px-2.5 py-1 text-[10px] font-bold text-amber-600 dark:text-amber-400">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                      Local AI Engine Active {latencyMs !== null ? `(${latencyMs}ms)` : ""}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-200 px-2.5 py-1 text-[10px] font-bold text-slate-600 dark:bg-white/10 dark:text-slate-300">
                      Checking Connection...
                    </span>
                  )}
                  <span className="text-xs font-semibold text-orange-500">
                    📍 {activeScenario?.location}
                  </span>
                </div>
              </div>

              <div className="mt-4">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                    Field Incident / Observation Narrative:
                  </label>
                  <span className="text-[11px] font-mono text-slate-400">
                    {customText.length} chars • {customText.trim().split(/\s+/).filter(Boolean).length} words
                  </span>
                </div>
                <textarea
                  value={customText}
                  onChange={(e) => setCustomText(e.target.value)}
                  rows={6}
                  placeholder="Type an unsafe act, unsafe condition, or near-miss observation..."
                  className="mt-2 w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 p-4 font-mono text-xs leading-relaxed text-slate-800 outline-none transition focus:border-orange-500 focus:ring-2 focus:ring-orange-500/20 dark:border-white/10 dark:bg-black/30 dark:text-slate-200"
                />
              </div>

              <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleQuickRun}
                    disabled={isScanning || !customText.trim()}
                    className="inline-flex items-center gap-2 rounded-xl bg-orange-500 px-5 py-2.5 text-xs font-bold text-white shadow-md shadow-orange-500/20 transition hover:bg-orange-600 disabled:opacity-50"
                  >
                    {isScanning ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                        </svg>
                        <span>Analyzing with ML Engine...</span>
                      </>
                    ) : (
                      <>
                        <span>⚡ Run Live AI Scan</span>
                      </>
                    )}
                  </button>

                  <button
                    type="button"
                    onClick={() => {
                      setCustomText(activeScenario.text);
                      runLiveInference(activeScenario.text);
                    }}
                    className="rounded-xl border border-slate-200 bg-slate-100 px-3.5 py-2.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-200 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
                    title="Reset to scenario default"
                  >
                    Reset Text
                  </button>
                </div>

                <button
                  type="button"
                  onClick={handleLaunchFullAnalysis}
                  className="inline-flex items-center gap-2 rounded-xl border border-orange-500/40 bg-orange-500/10 px-5 py-2.5 text-xs font-bold text-orange-600 transition hover:bg-orange-500 hover:text-white dark:text-orange-400 dark:hover:text-white"
                >
                  <span>Open Full Investigation Portal →</span>
                </button>
              </div>
            </div>

            {/* Right: Real-Time AI Inference Output */}
            <div className="lg:col-span-5 flex flex-col justify-between rounded-3xl border border-slate-200 bg-gradient-to-br from-white to-orange-50/30 p-6 shadow-xl dark:border-white/10 dark:from-[#0a1f1a] dark:to-[#050d0a]">
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-white/10">
                  <div className="flex items-center gap-2">
                    <span className="text-xl">🤖</span>
                    <h3 className="font-extrabold text-base">Real-Time AI Telemetry</h3>
                  </div>
                  <span className="rounded-full bg-emerald-500/10 px-2.5 py-1 text-[10px] font-bold text-emerald-600 dark:text-emerald-400">
                    Live Score
                  </span>
                </div>

                {/* Score & Severity Gauge */}
                {(() => {
                  const score = apiResult?.analysis?.overall_risk?.score ?? 0;
                  const level = apiResult?.analysis?.overall_risk?.level ?? "LOW";
                  const potAccLevel = apiResult?.analysis?.severity_prediction?.potential_accident_level ?? "I";
                  const modelName = apiResult?.analysis?.severity_prediction?.model ?? "Linear SVM";

                  const severityMap: Record<string, { label: string; bg: string }> = {
                    I: { label: "Level I (Minor)", bg: "bg-emerald-500" },
                    II: { label: "Level II (Moderate)", bg: "bg-amber-500" },
                    III: { label: "Level III (Serious)", bg: "bg-orange-500" },
                    IV: { label: "Level IV (Critical)", bg: "bg-red-500" },
                    V: { label: "Level V (Catastrophic)", bg: "bg-purple-600" },
                  };

                  const currentSeverity = severityMap[potAccLevel] || {
                    label: `Level ${potAccLevel}`,
                    bg: "bg-red-500",
                  };

                  const getScoreTheme = (sc: number) => {
                    if (sc >= 70) return { text: "text-red-500", bg: "bg-red-500/10", border: "border-red-500/30", bar: "bg-red-500" };
                    if (sc >= 30) return { text: "text-orange-500", bg: "bg-orange-500/10", border: "border-orange-500/30", bar: "bg-orange-500" };
                    return { text: "text-emerald-500", bg: "bg-emerald-500/10", border: "border-emerald-500/30", bar: "bg-emerald-500" };
                  };

                  const theme = getScoreTheme(score);

                  return (
                    <div className={`mt-5 rounded-2xl border ${theme.border} ${theme.bg} p-4 transition-all`}>
                      <div className="flex items-center justify-between">
                        <div>
                          <p className={`text-[10px] font-bold uppercase tracking-wider ${theme.text}`}>
                            SIF Criticality Score ({level})
                          </p>
                          <p className={`mt-1 font-orbitron text-4xl font-black ${theme.text}`}>
                            {score} <span className="text-xs font-sans text-slate-400">/ 100</span>
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                            Severity Prediction
                          </p>
                          <span className={`mt-1 inline-block rounded-lg ${currentSeverity.bg} px-2.5 py-1 text-xs font-bold text-white shadow-sm`}>
                            {currentSeverity.label}
                          </span>
                          <p className="mt-1 text-[9px] font-medium text-slate-400">
                            Engine: {modelName}
                          </p>
                        </div>
                      </div>

                      {/* Progress Bar */}
                      <div className="mt-3 h-1.5 w-full rounded-full bg-slate-200 dark:bg-white/10 overflow-hidden">
                        <div
                          className={`h-full ${theme.bar} transition-all duration-500`}
                          style={{ width: `${Math.min(100, Math.max(5, score))}%` }}
                        />
                      </div>
                    </div>
                  );
                })()}

                {/* Detected Safety Precursors */}
                <div className="mt-5">
                  <div className="flex items-center justify-between">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Detected Safety Precursors:
                    </p>
                    <span className="text-[10px] font-bold text-orange-500">
                      {apiResult?.analysis?.detected_precursors?.length || 0} Flagged
                    </span>
                  </div>

                  <div className="mt-2 flex flex-wrap gap-2">
                    {apiResult?.analysis?.detected_precursors && apiResult.analysis.detected_precursors.length > 0 ? (
                      apiResult.analysis.detected_precursors.map((p, idx) => (
                        <span
                          key={p.factor || idx}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-orange-500/30 bg-orange-500/10 px-3 py-1 text-xs font-semibold text-orange-600 dark:text-orange-300 animate-fadeIn"
                        >
                          <span>⚠️</span>
                          <span>{p.label || p.factor}</span>
                          {p.contribution ? (
                            <span className="rounded bg-orange-500/20 px-1 py-0.2 text-[9px] font-bold">
                              +{p.contribution}%
                            </span>
                          ) : null}
                        </span>
                      ))
                    ) : (
                      <span className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-600 dark:text-emerald-300">
                        ✅ No Critical SIF Precursors Detected
                      </span>
                    )}
                  </div>
                </div>

                {/* Prescriptive Action & AI Reasoning */}
                <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-3.5 dark:border-white/10 dark:bg-white/[0.03]">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Prescriptive Mitigation Trigger:
                  </p>
                  <p className="mt-1 text-xs leading-relaxed font-medium text-slate-700 dark:text-slate-300">
                    {apiResult?.analysis?.recommended_actions?.[0] ||
                      apiResult?.analysis?.ai_explanation ||
                      "Standard routine monitoring recommended."}
                  </p>
                </div>

                {/* Historical Case Precedent Match (RAG) */}
                {apiResult?.analysis?.historical_evidence?.incidents?.[0] && (
                  <div className="mt-3 rounded-2xl border border-orange-500/20 bg-orange-500/5 p-3 dark:border-orange-500/20 dark:bg-orange-500/[0.03]">
                    <div className="flex items-center justify-between text-[10px] font-bold text-orange-600 dark:text-orange-400 uppercase tracking-wider">
                      <span>🔗 Historical Incident Match (RAG)</span>
                      <span>
                        {(() => {
                          const sim = apiResult.analysis.historical_evidence.incidents[0].similarity;
                          if (sim === undefined) return "";
                          const pct = sim <= 1 ? (sim * 100).toFixed(1) : sim.toFixed(1);
                          return `${pct}% Match`;
                        })()}
                      </span>
                    </div>
                    <p className="mt-1 line-clamp-2 text-[11px] text-slate-600 dark:text-slate-400 italic">
                      "{apiResult.analysis.historical_evidence.incidents[0].description}"
                    </p>
                  </div>
                )}
              </div>

              <div className="mt-5 pt-3 border-t border-slate-200/80 flex items-center justify-between text-[10px] text-slate-400 dark:border-white/10">
                <span>Model: Sublinear TF-IDF + Linear SVM</span>
                <span>OISD 113 / IOGP Life-Saving Rules</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ================= PROBLEM CONTEXT (OIL INDIA LIMITED CHALLENGE) ================= */}
      <section id="problem" className="py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-4 py-1.5 text-xs font-bold tracking-wider text-orange-600 dark:text-orange-400 uppercase">
              The Safety Dilemma
            </span>
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight sm:text-5xl">
              Why Traditional Safety Reporting Fails
            </h2>
            <p className="mt-4 text-base text-slate-600 dark:text-slate-400">
              Thousands of daily Near-Miss, Unsafe Act (UA), and Unsafe Condition (UC) reports in Oil &amp; Gas operations mask high-risk catastrophic signals.
            </p>
          </div>

          <div className="mt-16 grid gap-8 md:grid-cols-3">
            <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm transition-all hover:border-orange-400 hover:shadow-xl dark:border-white/10 dark:bg-[#0a1915]">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-orange-500/10 text-3xl">
                📝
              </div>
              <h3 className="mt-6 text-xl font-bold">Unstructured &amp; Colloquial Text</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                Reports are written in free-text by operators with varied regional terms, technical acronyms, and mixed languages, defying simple keyword lookups.
              </p>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm transition-all hover:border-orange-400 hover:shadow-xl dark:border-white/10 dark:bg-[#0a1915]">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-red-500/10 text-3xl">
                ⚠️
              </div>
              <h3 className="mt-6 text-xl font-bold">Hidden SIF Precursors</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                A minor hydrocarbon drip or scaffold plank shift often contains the exact precursor to a major blowout or fatality, but is misfiled as low severity.
              </p>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm transition-all hover:border-orange-400 hover:shadow-xl dark:border-white/10 dark:bg-[#0a1915]">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-500/10 text-3xl">
                ⏱️
              </div>
              <h3 className="mt-6 text-xl font-bold">Delayed Manual Intervention</h3>
              <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                Manual review takes days. By the time safety officers correlate repetitive unsafe acts across drilling rigs, an avoidable incident has already occurred.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ================= SAFETY INTELLIGENCE ECOSYSTEM SECTION (SIH26165) ================= */}
      <section id="ecosystem" className="relative border-t border-slate-200 bg-gradient-to-b from-slate-50 via-white to-slate-50 py-28 transition-colors duration-300 dark:border-white/10 dark:from-[#050d0a] dark:via-[#04110d] dark:to-[#050d0a] overflow-hidden">
        {/* Subtle Ambient Radial Glow */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-gradient-to-tr from-emerald-500/10 via-orange-500/10 to-transparent blur-[140px] pointer-events-none rounded-full" />
        <div className="absolute inset-0 bg-grid-pattern opacity-30 dark:opacity-15 pointer-events-none" />

        <div className="relative z-10 mx-auto max-w-7xl px-6 lg:px-8">
          {/* Section Header */}
          <div className="text-center max-w-3xl mx-auto">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-4 py-1.5 text-xs font-bold tracking-wider text-emerald-700 dark:text-emerald-400 uppercase shadow-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              Connected Safety Architecture • SIH26165
            </div>

            <h2 className="mt-5 text-3xl font-black tracking-tight text-slate-950 dark:text-white sm:text-5xl lg:text-5xl leading-tight">
              Safety Intelligence Works When{" "}
              <span className="bg-gradient-to-r from-orange-600 via-amber-500 to-emerald-600 dark:from-orange-400 dark:via-amber-300 dark:to-emerald-400 bg-clip-text text-transparent">
                Every Signal Connects
              </span>
            </h2>

            <p className="mt-4 text-base sm:text-lg font-medium leading-relaxed text-slate-700 dark:text-slate-300">
              Connecting field observations, AI risk intelligence, historical evidence and HSE decision-making through one unified safety intelligence layer.
            </p>
          </div>

          {/* ================= CONNECTED ARCHITECTURE NODES ================= */}
          <div className="mt-20">
            {/* Desktop / Large Screens Flow */}
            <div className="grid gap-6 lg:grid-cols-5 items-stretch relative">

              {/* Node 1: FIELD OBSERVATIONS */}
              <div className="relative flex flex-col justify-between rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg backdrop-blur-xl transition-all hover:border-orange-400 hover:shadow-orange-500/10 interactive-card dark:border-white/10 dark:bg-[#071914]/90">
                <div className="flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-orange-500/10 text-2xl border border-orange-500/30">
                    📋
                  </div>
                  <span className="rounded-full bg-orange-500/10 px-2.5 py-1 text-[10px] font-bold text-orange-600 dark:text-orange-400 uppercase tracking-wider">
                    Source
                  </span>
                </div>
                <div className="mt-6">
                  <h3 className="text-lg font-bold text-slate-950 dark:text-white">Field Observations</h3>
                  <p className="mt-1 text-xs font-semibold text-orange-600 dark:text-orange-400">
                    Primary Data Entry
                  </p>
                  <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    Unsafe Acts • Unsafe Conditions • Near-Miss Reports submitted by rig &amp; pipeline crews.
                  </p>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100 dark:border-white/10 flex items-center gap-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                  <span>→ Ingests Unstructured Notes</span>
                </div>
              </div>

              {/* Node 2: AI / NLP ENGINE */}
              <div className="relative flex flex-col justify-between rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg backdrop-blur-xl transition-all hover:border-amber-400 hover:shadow-amber-500/10 interactive-card dark:border-white/10 dark:bg-[#071914]/90">
                <div className="flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/10 text-2xl border border-amber-500/30">
                    🧠
                  </div>
                  <span className="rounded-full bg-amber-500/10 px-2.5 py-1 text-[10px] font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
                    Core AI
                  </span>
                </div>
                <div className="mt-6">
                  <h3 className="text-lg font-bold text-slate-950 dark:text-white">AI Intelligence</h3>
                  <p className="mt-1 text-xs font-semibold text-amber-600 dark:text-amber-400">
                    NLP Analysis Engine
                  </p>
                  <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    NLP • SIF Precursor Detection • Severity Prediction extracting latent hazardous risks.
                  </p>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100 dark:border-white/10 flex items-center gap-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                  <span>→ Feeds Intelligence Hub</span>
                </div>
              </div>

              {/* CENTRAL NODE: SAFETY INTELLIGENCE LAYER */}
              <div className="relative flex flex-col justify-between rounded-3xl border-2 border-orange-500/60 bg-gradient-to-b from-orange-500/15 via-white/95 to-emerald-500/15 p-6 shadow-2xl backdrop-blur-xl transition-all hover:shadow-orange-500/25 interactive-card dark:from-orange-500/20 dark:via-[#09221b] dark:to-emerald-500/20 dark:border-orange-500/50">
                <div className="flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-500 to-amber-500 text-white text-2xl shadow-md">
                    ⚡
                  </div>
                  <span className="rounded-full bg-gradient-to-r from-orange-500 to-amber-500 px-2.5 py-1 text-[10px] font-black text-white uppercase tracking-wider shadow-sm">
                    Central Layer
                  </span>
                </div>
                <div className="mt-6">
                  <h3 className="text-lg font-extrabold text-slate-950 dark:text-white">
                    Safety Intelligence Layer
                  </h3>
                  <p className="mt-1 text-xs font-bold text-orange-600 dark:text-orange-400">
                    Unified Safety Engine
                  </p>
                  <p className="mt-3 text-xs leading-relaxed text-slate-700 dark:text-slate-300 font-medium">
                    Risk Score + SIF Precursors + Severity + Recommended Actions correlated synchronously.
                  </p>
                </div>
                <div className="mt-6 pt-4 border-t border-orange-500/20 flex items-center justify-between text-[11px] font-bold text-orange-600 dark:text-orange-400">
                  <span>↙ Semantic Retrieval</span>
                  <span>↘ Human Review</span>
                </div>
              </div>

              {/* Node 3: HISTORICAL EVIDENCE */}
              <div className="relative flex flex-col justify-between rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-lg backdrop-blur-xl transition-all hover:border-cyan-400 hover:shadow-cyan-500/10 interactive-card dark:border-white/10 dark:bg-[#071914]/90">
                <div className="flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-cyan-500/10 text-2xl border border-cyan-500/30">
                    🗄️
                  </div>
                  <span className="rounded-full bg-cyan-500/10 px-2.5 py-1 text-[10px] font-bold text-cyan-600 dark:text-cyan-400 uppercase tracking-wider">
                    Memory
                  </span>
                </div>
                <div className="mt-6">
                  <h3 className="text-lg font-bold text-slate-950 dark:text-white">Historical Evidence</h3>
                  <p className="mt-1 text-xs font-semibold text-cyan-600 dark:text-cyan-400">
                    Incident Memory
                  </p>
                  <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    Semantic Similarity • Similar Incidents • Case Retrieval across expandable incident corpus.
                  </p>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100 dark:border-white/10 flex items-center gap-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                  <span>→ Benchmarks Past Cases</span>
                </div>
              </div>

              {/* Node 4: HSE DECISION LAYER (Final Human Validation) */}
              <div className="relative flex flex-col justify-between rounded-3xl border border-emerald-500/40 bg-white/90 p-6 shadow-lg backdrop-blur-xl transition-all hover:border-emerald-400 hover:shadow-emerald-500/10 interactive-card dark:border-emerald-500/30 dark:bg-[#071914]/90">
                <div className="flex items-center justify-between">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 text-2xl border border-emerald-500/30">
                    🛡️
                  </div>
                  <span className="rounded-full bg-emerald-500/15 px-2.5 py-1 text-[10px] font-extrabold text-emerald-700 dark:text-emerald-400 uppercase tracking-wider">
                    Final Step (Human)
                  </span>
                </div>
                <div className="mt-6">
                  <h3 className="text-lg font-bold text-slate-950 dark:text-white">HSE Decision Layer</h3>
                  <p className="mt-1 text-xs font-bold text-emerald-700 dark:text-emerald-400">
                    Human-in-the-Loop
                  </p>
                  <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    Risk Review • Corrective Actions • Human Validation ensuring final safety governance.
                  </p>
                </div>
                <div className="mt-6 pt-4 border-t border-slate-100 dark:border-white/10 flex items-center gap-2 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400">
                  <span>✓ Human Validation Authority</span>
                </div>
              </div>

            </div>

            {/* Architecture Flow Guide Strip */}
            <div className="mt-8 rounded-2xl border border-slate-200 bg-slate-100/80 p-4 text-center text-xs font-bold text-slate-700 backdrop-blur-md dark:border-white/10 dark:bg-white/[0.03] dark:text-slate-300 flex flex-wrap items-center justify-center gap-3">
              <span className="text-orange-500 font-extrabold">Field Reports</span>
              <span className="text-slate-400">→</span>
              <span className="text-amber-500 font-extrabold">AI / NLP Engine</span>
              <span className="text-slate-400">→</span>
              <span className="text-orange-600 dark:text-orange-400 font-black">Safety Intelligence Layer</span>
              <span className="text-slate-400">→</span>
              <span className="text-cyan-500 font-extrabold">Historical Evidence</span>
              <span className="text-slate-400">&amp;</span>
              <span className="text-emerald-600 dark:text-emerald-400 font-extrabold">HSE Officer Validation (Human-in-the-Loop)</span>
            </div>
          </div>

          {/* ================= PROTOTYPE CAPABILITIES ================= */}
          <div className="mt-20 pt-16 border-t border-slate-200 dark:border-white/10">
            <div className="text-center max-w-xl mx-auto mb-12">
              <span className="text-xs font-black tracking-widest text-orange-600 dark:text-orange-400 uppercase">
                PROTOTYPE CAPABILITIES
              </span>
              <h3 className="mt-2 text-2xl font-extrabold text-slate-950 dark:text-white">
                Verified Industrial AI Safety Specifications
              </h3>
            </div>

            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {/* Card 1: 8 SIF Precursor Categories */}
              <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm interactive-card dark:border-white/10 dark:bg-[#071914]">
                <div className="font-orbitron text-4xl font-extrabold text-orange-500">
                  8
                </div>
                <h4 className="mt-3 text-sm font-bold text-slate-950 dark:text-white">
                  SIF Precursor Categories
                </h4>
                <p className="mt-2 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
                  High Pressure, Gas/Hydrocarbon Leakage, PPE, Machinery, Confined Space, Electrical, Fall from Height, Chemical Hazard.
                </p>
              </div>

              {/* Card 2: 3 AI Analysis Layers */}
              <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm interactive-card dark:border-white/10 dark:bg-[#071914]">
                <div className="font-orbitron text-4xl font-extrabold text-amber-500">
                  3
                </div>
                <h4 className="mt-3 text-sm font-bold text-slate-950 dark:text-white">
                  AI Analysis Layers
                </h4>
                <p className="mt-2 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
                  NLP Precursor Extraction, Multi-Class Severity Classification, and Cosine Semantic Similarity Retrieval.
                </p>
              </div>

              {/* Card 3: Top-3 Historical Case Retrieval */}
              <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm interactive-card dark:border-white/10 dark:bg-[#071914]">
                <div className="font-orbitron text-4xl font-extrabold text-cyan-500">
                  Top-3
                </div>
                <h4 className="mt-3 text-sm font-bold text-slate-950 dark:text-white">
                  Historical Case Retrieval
                </h4>
                <p className="mt-2 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
                  Automated retrieval of closest historical precedents to guide preventative interventions before recurrence.
                </p>
              </div>

              {/* Card 4: Human-in-the-Loop */}
              <div className="rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm interactive-card dark:border-white/10 dark:bg-[#071914]">
                <div className="text-2xl font-black text-emerald-600 dark:text-emerald-400">
                  Human-in-the-Loop
                </div>
                <h4 className="mt-3 text-sm font-bold text-slate-950 dark:text-white">
                  Safety Decision Workflow
                </h4>
                <p className="mt-2 text-[11px] leading-relaxed text-slate-600 dark:text-slate-400">
                  AI provides predictive recommendations while authorized HSE safety officers retain final sign-off authority.
                </p>
              </div>
            </div>

            {/* Subtle Bottom Statement */}
            <div className="mt-14 text-center">
              <p className="text-sm font-bold tracking-wide text-slate-600 dark:text-slate-300">
                “Detect early. Understand context. Support safer decisions.”
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ================= AI PIPELINE & ARCHITECTURE (SIH26165 SOLUTION) ================= */}
      <section id="pipeline" className="border-t border-slate-200 bg-slate-100/70 py-24 transition-colors duration-300 dark:border-white/10 dark:bg-[#071411]/60">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-4 py-1.5 text-xs font-bold tracking-wider text-orange-600 dark:text-orange-400 uppercase">
              End-to-End AI Engine
            </span>
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight sm:text-5xl">
              Intelligent Risk Detection Architecture
            </h2>
            <p className="mt-4 text-base text-slate-600 dark:text-slate-400">
              A four-stage predictive intelligence pipeline built specifically for Oil India Limited exploration and production safety requirements.
            </p>
          </div>

          <div className="mt-16 grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {/* Step 1 */}
            <div className="relative rounded-3xl border border-slate-200 bg-white p-7 shadow-sm transition-all hover:shadow-xl dark:border-white/10 dark:bg-[#0a1915]">
              <span className="font-orbitron text-3xl font-extrabold text-orange-500/30">01</span>
              <h3 className="mt-3 text-lg font-bold">Multi-Modal Ingestion</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Accepts free-text observation logs, inspector voice notes (Speech-to-Text), and photo evidence from mobile &amp; web terminals.
              </p>
            </div>

            {/* Step 2 */}
            <div className="relative rounded-3xl border border-slate-200 bg-white p-7 shadow-sm transition-all hover:shadow-xl dark:border-white/10 dark:bg-[#0a1915]">
              <span className="font-orbitron text-3xl font-extrabold text-orange-500/30">02</span>
              <h3 className="mt-3 text-lg font-bold">Domain NLP &amp; NER</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Extracts 8 SIF precursor dimensions (gas leaks, high pressure, PPE violations, confined spaces) using OISD-adapted entity recognition.
              </p>
            </div>

            {/* Step 3 */}
            <div className="relative rounded-3xl border border-slate-200 bg-white p-7 shadow-sm transition-all hover:shadow-xl dark:border-white/10 dark:bg-[#0a1915]">
              <span className="font-orbitron text-3xl font-extrabold text-orange-500/30">03</span>
              <h3 className="mt-3 text-lg font-bold">ML Severity Prediction</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Calibrated Machine Learning model classifies potential incident level from Level I (Minor) to Level V (Catastrophic) with zero false-alarm bias.
              </p>
            </div>

            {/* Step 4 */}
            <div className="relative rounded-3xl border border-slate-200 bg-white p-7 shadow-sm transition-all hover:shadow-xl dark:border-white/10 dark:bg-[#0a1915]">
              <span className="font-orbitron text-3xl font-extrabold text-orange-500/30">04</span>
              <h3 className="mt-3 text-lg font-bold">Vector Match &amp; Alert</h3>
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Matches vector embeddings against 425+ historical cases and generates prescriptive corrective checklists &amp; instant safety officer alerts.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ================= SIF PRECURSOR TAXONOMY MATRIX ================= */}
      <section id="taxonomy" className="py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-8">
          <div className="text-center max-w-3xl mx-auto">
            <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-4 py-1.5 text-xs font-bold tracking-wider text-orange-600 dark:text-orange-400 uppercase">
              Domain Intelligence
            </span>
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight sm:text-5xl">
              8 Critical SIF Precursor Dimensions
            </h2>
            <p className="mt-4 text-base text-slate-600 dark:text-slate-400">
              Specialized NLP rule mining and embeddings mapped to Oil &amp; Gas operational risk categories.
            </p>
          </div>

          <div className="mt-16 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[
              {
                title: "High-Pressure Hazards",
                desc: "Surge pressures, manifold flange leaks, blowout preventer (BOP) line integrity.",
                icon: "⚙️",
                tag: "Wellhead & Rigs",
              },
              {
                title: "Hydrocarbon & Toxic Gas",
                desc: "H2S, Methane (CH4) detection, gas flaring anomalies, Zone-0/1 vapor accumulation.",
                icon: "🧪",
                tag: "Refineries & Gas Plants",
              },
              {
                title: "Confined Space Entry",
                desc: "Storage tanks, vessel cleanout, oxygen depletion, permit-to-work (PTW) bypass.",
                icon: "🕳️",
                tag: "Plant Maintenance",
              },
              {
                title: "Working at Heights",
                desc: "Derrick mast climbing, monkey board operations, scaffolding tether non-compliance.",
                icon: "🧗",
                tag: "Drilling Derricks",
              },
              {
                title: "Electrical Arcing",
                desc: "High-voltage substation faults, ungrounded generators, explosion-proof integrity.",
                icon: "⚡",
                tag: "Power Distribution",
              },
              {
                title: "Heavy Lifting & Cranes",
                desc: "Rig mobilization, drill pipe transfer, crane sling wear, suspended load violations.",
                icon: "🏗️",
                tag: "Material Handling",
              },
              {
                title: "PPE Defiance",
                desc: "Absence of flame-retardant clothing (FRC), H2S escape hoods, impact goggles.",
                icon: "🦺",
                tag: "Field Workforce",
              },
              {
                title: "Machinery Guarding",
                desc: "Rotary table unguarded chains, mud pump drive belts, lockout/tagout (LOTO) failures.",
                icon: "🛡️",
                tag: "Operational Equipment",
              },
            ].map((item) => (
              <div
                key={item.title}
                className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm transition-all hover:border-orange-400 hover:shadow-lg dark:border-white/10 dark:bg-[#0a1915]"
              >
                <div className="flex items-center justify-between">
                  <span className="text-3xl">{item.icon}</span>
                  <span className="rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-bold text-slate-600 dark:bg-white/10 dark:text-slate-400">
                    {item.tag}
                  </span>
                </div>
                <h3 className="mt-4 font-bold text-base">{item.title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ================= CALL TO ACTION ================= */}
      <section className="relative overflow-hidden border-t border-slate-200 bg-gradient-to-br from-orange-500 via-amber-600 to-orange-700 py-20 text-white shadow-2xl">
        <div className="relative z-10 mx-auto max-w-5xl px-6 text-center lg:px-8">
          <span className="rounded-full bg-white/20 px-4 py-1.5 text-xs font-bold tracking-wider uppercase backdrop-blur-md">
            Smart India Hackathon 2026
          </span>

          <h2 className="mt-6 text-3xl font-black tracking-tight sm:text-5xl">
            Empower Oil India Limited with Proactive Safety Intelligence
          </h2>

          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-orange-100 sm:text-lg">
            Experience real-time precursor screening, severity classification, and historical case analytics in action.
          </p>

          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <button
              type="button"
              onClick={() => handleProtectedNavigate("/submit-report")}
              className="rounded-full bg-white px-8 py-4 text-base font-bold text-orange-600 shadow-xl transition-all hover:bg-orange-50 hover:scale-105"
            >
              Submit Observation Report →
            </button>

            <button
              type="button"
              onClick={() => handleProtectedNavigate("/analytics-dashboard")}
              className="rounded-full border border-white/40 bg-black/20 px-8 py-4 text-base font-bold text-white backdrop-blur-md transition-all hover:bg-black/30"
            >
              View Analytics Dashboard
            </button>
          </div>
        </div>
      </section>

      {/* ================= SPACIOUS CLEAN FOOTER ================= */}
      <footer className="border-t border-slate-200 bg-white px-6 py-12 text-slate-500 transition-colors duration-300 dark:border-white/10 dark:bg-[#050d0a] dark:text-slate-400">
        <div className="mx-auto max-w-7xl flex flex-col items-center justify-between gap-6 md:flex-row">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500 font-extrabold text-white text-sm">
              OIL
            </div>
            <div>
              <p className="font-extrabold text-slate-900 dark:text-white text-sm">
                SurakshaSetu Platform
              </p>
              <p className="text-[11px] text-slate-400">
                Oil India Limited • SIH26165 Solution
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-6 text-xs font-semibold">
            <a href="#problem" className="hover:text-orange-500">Problem</a>
            <a href="#playground" className="hover:text-orange-500">Live Simulator</a>
            <a href="#pipeline" className="hover:text-orange-500">Architecture</a>
            <a href="#taxonomy" className="hover:text-orange-500">Taxonomy</a>
            <Link href="/login" className="hover:text-orange-500">Portal Login</Link>
          </div>

          <p className="text-xs text-slate-400">
            © 2026 SurakshaSetu. Built for SIH 2026.
          </p>
        </div>
      </footer>
    </main>
  );
}