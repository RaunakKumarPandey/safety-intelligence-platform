"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import ThemeToggle from "../components/ThemeToggle";
import {
  AnalysisResponse,
  Incident,
  SafetyPrecursor,
  CorrectiveAction,
  SafetyReviewRecord,
  submitSafetyReviewRecord,
  updateTrackedActionStatus,
  ActionTrackingRecord,
  analyzeSafetyReport,
  saveAnalysisResult,
  loadAnalysisResult
} from "@/lib/api";
import { isUserAuthenticated, getStoredUser, UserSession } from "@/lib/auth";

const SAMPLE_ANALYSIS_SCENARIOS = [
  {
    title: "Gas Flange Leak",
    department: "Drilling Operations",
    text: "High-pressure natural gas hissing from separator flange gasket during startup. LEL detector triggered at 40% with gas plume drifting toward compressor station.",
  },
  {
    title: "Work at Height",
    department: "Maintenance",
    text: "Contractor technician was observed working at 18 meters height without full-body harness tethered to safety lifeline. Scaffold plank was unfastened and shifted 4 inches.",
  },
  {
    title: "440V Live Wire",
    department: "Logistics & Maintenance",
    text: "Frayed 440V electrical power cable found lying in pool of spilled drilling fluid and crude residue near high-vibration pump skid in Zone-1 classification area.",
  },
  {
    title: "Routine Safe Inspection",
    department: "Production",
    text: "Routine safety inspection completed at workshop bay. All tools stowed on shadow board, floor dry and clean, full PPE worn.",
  },
];

export default function AnalysisPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<UserSession | null>(null);
  const [showOfficerModal, setShowOfficerModal] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);

  // Human Safety Review State
  const [reviewMode, setReviewMode] = useState<"ACCEPTED" | "MODIFIED" | "REJECTED">("ACCEPTED");
  const [officerName, setOfficerName] = useState("R. Sharma");
  const [officerId, setOfficerId] = useState("HSE-8492");
  const [reviewerComment, setReviewerComment] = useState("");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("I");
  const [overrideScore, setOverrideScore] = useState<number>(0);
  const [customActionText, setCustomActionText] = useState("");
  const [activeActionsList, setActiveActionsList] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [reviewRecord, setReviewRecord] = useState<SafetyReviewRecord | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  // Action Tracking State (Task 10)
  const [actionStatuses, setActionStatuses] = useState<Record<string, { status: string; verification_status: string; updated_by?: string; isUpdating?: boolean }>>({});
  const [actionNotes, setActionNotes] = useState<Record<string, string>>({});

  const applyAnalysisResult = (parsedResult: AnalysisResponse) => {
    setResult(parsedResult);
    const potLevel = parsedResult.analysis?.severity_prediction?.potential_accident_level || "I";
    const score = parsedResult.analysis?.overall_risk?.score || 0;
    const actions = parsedResult.analysis?.recommended_actions || [];
    setSelectedSeverity(potLevel);
    setOverrideScore(score);
    setActiveActionsList([...actions]);
  };

  const loadScenarioAnalysis = async (scenarioIndex: number) => {
    try {
      setIsLoadingAnalysis(true);
      const scenario = SAMPLE_ANALYSIS_SCENARIOS[scenarioIndex];
      console.log(`[SafetyAI] Loading benchmark scenario: ${scenario.title}`);
      const res = await analyzeSafetyReport({
        report_text: scenario.text,
        industry_sector: scenario.department,
        worker_type: "Employee",
        gender: "Male",
      }, 20000);
      saveAnalysisResult(res);
      applyAnalysisResult(res);
    } catch (e) {
      console.warn("[SafetyAI] Could not analyze sample scenario:", e);
    } finally {
      setIsLoadingAnalysis(false);
    }
  };

  useEffect(() => {
    if (!isUserAuthenticated()) {
      router.push("/login?redirect=/analysis");
      return;
    }

    const session = getStoredUser();
    setCurrentUser(session);
    if (session?.role === "officer") {
      setOfficerName(session.name || "Safety Officer");
      const idSuffix = session.email ? session.email.split("@")[0].toUpperCase() : "8492";
      setOfficerId(`HSE-${idSuffix}`);
    }

    const initAnalysis = () => {
      try {
        console.log("[SafetyAI] Loading analysis from session storage...");
        const stored = loadAnalysisResult();
        if (stored) {
          console.log("[SafetyAI] Verified analysis loaded from session. Source:", stored.analysis_source);
          applyAnalysisResult(stored);
        } else {
          console.log("[SafetyAI] No active analysis in session storage.");
          setResult(null);
        }
      } catch (error) {
        console.error("[SafetyAI] Failed to load analysis result:", error);
        setResult(null);
      }
    };

    initAnalysis();
  }, [router]);

  const analysis = result?.analysis;
  const riskScore = analysis?.overall_risk?.score ?? 0;
  const riskLevel = analysis?.overall_risk?.level ?? "LOW";
  const summary = analysis?.overall_risk?.summary ?? "No safety summary available.";

  const rawSeverity = analysis?.severity_prediction?.potential_accident_level ?? "I";

  const severityMap: Record<string, string> = {
    I: "Minor (Level I)",
    II: "Moderate (Level II)",
    III: "Serious (Level III)",
    IV: "Critical (Level IV)",
    V: "Catastrophic (Level V)",
  };

  const severity = severityMap[rawSeverity] ?? rawSeverity;
  const precursors: SafetyPrecursor[] = analysis?.detected_precursors ?? [];
  const correctiveActions: CorrectiveAction[] = analysis?.corrective_actions ?? [];
  const recommendedActions: string[] = analysis?.recommended_actions ?? [];
  const similarCases: Incident[] = analysis?.historical_evidence?.incidents ?? [];

  const formatSimilarity = (sim?: number) => {
    if (sim === undefined || sim === null) return "N/A";
    const value = sim <= 1.0 && sim > 0 ? sim * 100 : sim;
    return `${Number(value).toFixed(1)}%`;
  };

  const isOfficer = currentUser?.role === "officer";

  const handleActionStatusChange = async (actionId: string, newStatus: string) => {
    const session = getStoredUser();
    if (!session || session.role !== "officer") {
      setShowOfficerModal(true);
      return;
    }

    setActionStatuses(prev => ({
      ...prev,
      [actionId]: {
        status: newStatus,
        verification_status: newStatus === "VERIFIED" ? "VERIFIED" : (newStatus === "COMPLETED" ? "PENDING_VERIFICATION" : "UNVERIFIED"),
        isUpdating: true
      }
    }));

    const note = actionNotes[actionId] || "Updated via Analysis Workbench";
    const res = await updateTrackedActionStatus(actionId, newStatus, note, officerName, officerId, 6000, session.role);
    if (res.success && res.action) {
      setActionStatuses(prev => ({
        ...prev,
        [actionId]: {
          status: res.action!.status,
          verification_status: res.action!.verification_status,
          updated_by: res.action!.verified_by_officer || officerName,
          isUpdating: false
        }
      }));
    } else {
      setActionStatuses(prev => ({
        ...prev,
        [actionId]: { ...prev[actionId], isUpdating: false }
      }));
    }
  };

  const getRiskColor = (score: number) => {
    if (score >= 70) {
      return {
        text: "text-red-500",
        bg: "bg-red-500/10",
        border: "border-red-500/30",
        badge: "bg-red-500 text-white",
        bar: "bg-red-500"
      };
    }
    if (score >= 30) {
      return {
        text: "text-orange-500",
        bg: "bg-orange-500/10",
        border: "border-orange-500/30",
        badge: "bg-orange-500 text-white",
        bar: "bg-orange-500"
      };
    }
    return {
      text: "text-emerald-500",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/30",
      badge: "bg-emerald-500 text-white",
      bar: "bg-emerald-500"
    };
  };

  const riskColor = getRiskColor(riskScore);

  const handleSelectReviewMode = (mode: "ACCEPTED" | "MODIFIED" | "REJECTED") => {
    const session = getStoredUser();
    if (!session || session.role !== "officer") {
      setShowOfficerModal(true);
      return;
    }
    setReviewMode(mode);
  };

  const handleAddCustomAction = () => {
    const session = getStoredUser();
    if (!session || session.role !== "officer") {
      setShowOfficerModal(true);
      return;
    }
    if (!customActionText.trim()) return;
    setActiveActionsList((prev) => [...prev, customActionText.trim()]);
    setCustomActionText("");
  };

  const handleRemoveAction = (index: number) => {
    const session = getStoredUser();
    if (!session || session.role !== "officer") {
      setShowOfficerModal(true);
      return;
    }
    setActiveActionsList((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmitReview = async () => {
    const session = getStoredUser();
    if (!session || session.role !== "officer") {
      setShowOfficerModal(true);
      return;
    }

    if (!result) return;
    setReviewError(null);

    if (!officerName.trim()) {
      setReviewError("Reviewing Safety Officer Name is required.");
      return;
    }
    if (!officerId.trim()) {
      setReviewError("Safety Officer ID / Badge Number is required.");
      return;
    }
    if (reviewMode !== "ACCEPTED" && (!reviewerComment || reviewerComment.trim().length < 3)) {
      setReviewError("Officer justification remarks are strictly required when modifying or rejecting AI findings.");
      return;
    }

    setIsSubmitting(true);

    const humanDecision = {
      severity: selectedSeverity,
      risk_score: Number(overrideScore),
      risk_level: Number(overrideScore) >= 75 ? "CRITICAL" : Number(overrideScore) >= 50 ? "HIGH" : Number(overrideScore) >= 20 ? "MEDIUM" : "LOW",
      precursors: precursors.map((p) => p.label || p.factor || "Hazard"),
      actions: activeActionsList,
    };

    const res = await submitSafetyReviewRecord({
      officer_name: officerName.trim(),
      officer_id: officerId.trim(),
      review_status: reviewMode,
      reviewer_comment: reviewerComment.trim() || (reviewMode === "ACCEPTED" ? "AI preliminary classification verified and accepted." : "Safety officer adjustments recorded."),
      ai_prediction: result.analysis,
      human_decision: reviewMode === "ACCEPTED" ? undefined : humanDecision,
      role: session.role,
    });

    setIsSubmitting(false);
    if (res.success && res.record) {
      setReviewRecord(res.record);
    } else if (res.error) {
      setReviewError(res.error);
    }
  };

  // Pipeline stages definition
  const pipelineStages = [
    { num: "01", name: "INPUT", icon: "📝", desc: "Observation Ingestion" },
    { num: "02", name: "NLP UNDERSTANDING", icon: "🧠", desc: "Entity & Negation Mining" },
    { num: "03", name: "PRECURSOR DETECTION", icon: "⚡", desc: "SIF Taxonomy Tagging" },
    { num: "04", name: "SEVERITY PREDICTION", icon: "🎯", desc: "Linear SVM Classification" },
    { num: "05", name: "RISK ASSESSMENT", icon: "📐", desc: "Explainable SIF Scoring" },
    { num: "06", name: "HISTORICAL EVIDENCE", icon: "🗄️", desc: "Vector Case Retrieval" },
    { num: "07", name: "RECOMMENDED ACTION", icon: "🛡️", desc: "Prescriptive Controls" },
    { num: "08", name: "HUMAN REVIEW", icon: "👮", desc: "Safety Officer Sign-off" },
  ];

  return (
    <main className="min-h-screen bg-slate-50 text-slate-900 transition-colors duration-300 dark:bg-[#050d0a] dark:text-slate-100">
      {/* HEADER */}
      <header className="sticky top-0 z-30 border-b border-slate-200/80 bg-white/80 backdrop-blur-xl dark:border-white/10 dark:bg-[#050d0a]/80">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-500 text-lg font-bold text-white shadow-md shadow-orange-500/20">
              <span className="font-orbitron text-xs">OIL</span>
            </div>

            <div>
              <h1 className="text-base font-extrabold text-slate-950 dark:text-white">
                Safety<span className="text-orange-500">AI</span>
              </h1>
              <p className="text-[9px] font-bold tracking-[0.18em] text-slate-400 dark:text-slate-400 uppercase">
                Oil India Limited • SIF Intelligence Pipeline
              </p>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <ThemeToggle />

            <Link
              href="/analytics-dashboard"
              className="rounded-full border border-slate-200 bg-white/50 px-4 py-2 text-xs font-bold text-orange-600 transition hover:bg-slate-100 dark:border-white/10 dark:bg-white/5 dark:text-orange-400 dark:hover:bg-white/10"
            >
              📊 Safety Analytics
            </Link>

            <Link
              href="/submit-report"
              className="rounded-full bg-orange-500 px-4 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-orange-600"
            >
              + Submit New Report
            </Link>
          </div>
        </div>
      </header>

      {/* CONTENT */}
      <section className="mx-auto max-w-7xl px-6 py-10">
        {/* Top Header Badge */}
        <div className="mb-6 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-3.5 py-1 text-[10px] font-bold tracking-wider text-orange-600 dark:text-orange-400 uppercase">
                SIH26165 AI/NLP Pipeline
              </span>
              <span className="rounded-full bg-blue-500/10 px-3 py-0.5 text-[10px] font-bold text-blue-600 dark:text-blue-400 border border-blue-500/20">
                End-to-End Decision Support Journey
              </span>
            </div>
            <h1 className="mt-3 text-3xl font-black md:text-4xl">
              SIF Precursor Screening &amp; Safety Review
            </h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              Traceable 8-stage pipeline from raw field report ingestion to authoritative HSE officer sign-off.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
              OISD Standard 113 / 114
            </span>
          </div>
        </div>

        {/* DEMO / OFFLINE FALLBACK WARNING BANNER */}
        {result?.analysis_source === "demo_fallback" && (
          <div className="mb-6 flex items-center justify-between gap-4 rounded-3xl border border-amber-500/30 bg-amber-500/10 p-5 dark:border-amber-500/20 dark:bg-amber-500/[0.05]">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-amber-500 text-lg text-white shadow-md shadow-amber-500/30">
                ⚡
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-extrabold text-sm text-amber-800 dark:text-amber-400">
                    Offline Heuristic Fallback Analysis
                  </span>
                  <span className="rounded-full bg-amber-600 px-2 py-0.5 text-[9px] font-black text-white uppercase font-mono">
                    DEMO_FALLBACK
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-slate-700 dark:text-slate-300">
                  {result.fallback_warning || "Backend server was unreachable at submission time. Displaying local heuristic estimate."} Connect to the FastAPI backend for authoritative Linear SVM and TF-IDF similarity analysis.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* RISK-TRIGGERED ALERT BANNER */}
        {(analysis?.alert || riskScore >= 50) && (
          <div className="mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-3xl border border-red-500/30 bg-red-500/10 p-5 dark:border-red-500/20 dark:bg-red-500/[0.05]">
            <div className="flex items-start sm:items-center gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-red-500 text-lg text-white shadow-md shadow-red-500/30 animate-pulse">
                🚨
              </span>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-extrabold text-sm text-red-700 dark:text-red-400">
                    Automated Risk Alert Generated
                  </span>
                  <span className="rounded-full bg-red-600 px-2 py-0.5 text-[9px] font-black text-white uppercase">
                    {analysis?.alert?.alert_id || "ALT-ACTIVE"}
                  </span>
                  <span className="rounded-full bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300 px-2 py-0.5 text-[9px] font-bold">
                    STATUS: {analysis?.alert?.alert_status || "NEW"}
                  </span>
                </div>
                <p className="mt-0.5 text-xs text-slate-700 dark:text-slate-300">
                  This observation reached <strong>{riskLevel} Risk ({riskScore}/100)</strong> and has been queued for immediate safety officer triage.
                </p>
              </div>
            </div>

            <Link
              href="/analytics-dashboard"
              className="rounded-xl bg-red-600 px-4 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-red-700 shrink-0"
            >
              View Alerts Queue →
            </Link>
          </div>
        )}

        {/* Quick Scenario Preset Chips */}
        <div className="mb-6 flex flex-wrap items-center gap-2">
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 mr-1">
            ⚡ Quick Benchmark Scenarios:
          </span>
          {SAMPLE_ANALYSIS_SCENARIOS.map((sc, idx) => (
            <button
              key={sc.title}
              onClick={() => loadScenarioAnalysis(idx)}
              disabled={isLoadingAnalysis}
              className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-orange-500 hover:text-orange-600 disabled:opacity-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:border-orange-500 dark:hover:text-orange-400"
            >
              {sc.title}
            </button>
          ))}
          {isLoadingAnalysis && (
            <span className="flex items-center gap-1.5 text-xs font-bold text-orange-500 ml-2">
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-orange-500 border-t-transparent" />
              Running Inference...
            </span>
          )}
        </div>

        {/* 8-STAGE VISUAL PIPELINE PROGRESS STRIP */}
        <div className="mb-10 overflow-x-auto rounded-3xl border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-[#071914]">
          <div className="flex items-center justify-between min-w-[760px] gap-2">
            {pipelineStages.map((st, idx) => (
              <div key={st.num} className="flex items-center gap-2 flex-1">
                <div className="flex flex-col items-center text-center p-2 rounded-2xl bg-slate-50 dark:bg-white/[0.02] border border-slate-100 dark:border-white/5 w-full">
                  <span className="text-base">{st.icon}</span>
                  <span className="mt-1 font-orbitron text-[9px] font-black text-orange-500">
                    {st.num}
                  </span>
                  <span className="text-[10px] font-extrabold text-slate-800 dark:text-slate-200 uppercase tracking-tight">
                    {st.name}
                  </span>
                </div>
                {idx < pipelineStages.length - 1 && (
                  <span className="text-slate-300 dark:text-slate-600 text-xs font-bold shrink-0">
                    →
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>

        {isLoadingAnalysis && !result ? (
          <div className="rounded-3xl border border-slate-200 bg-white p-16 text-center shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
            <div className="flex flex-col items-center justify-center">
              <span className="h-10 w-10 animate-spin rounded-full border-4 border-orange-500 border-t-transparent mb-4" />
              <h2 className="text-xl font-bold">Loading SIF Precursor Screening...</h2>
              <p className="mt-2 text-xs text-slate-500">
                Running real-time NLP precursor extraction and calibrated ML inference...
              </p>
            </div>
          </div>
        ) : !result ? (
          <div className="rounded-3xl border border-slate-200 bg-white p-16 text-center shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
            <div className="text-5xl">📋</div>
            <h2 className="mt-5 text-2xl font-bold">No Active Analysis Loaded</h2>
            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-md mx-auto">
              Select a benchmark oilfield scenario or submit a field safety report to run real-time SIF precursor detection.
            </p>
            <div className="mt-6 flex flex-wrap justify-center gap-3">
              {SAMPLE_ANALYSIS_SCENARIOS.map((sc, idx) => (
                <button
                  key={sc.title}
                  onClick={() => loadScenarioAnalysis(idx)}
                  className="rounded-full bg-slate-100 px-4 py-2 text-xs font-bold text-slate-800 transition hover:bg-orange-500 hover:text-white dark:bg-white/10 dark:text-slate-200 dark:hover:bg-orange-500"
                >
                  Load {sc.title} →
                </button>
              ))}
            </div>
            <div className="mt-6">
              <Link
                href="/submit-report"
                className="inline-block rounded-full bg-gradient-to-r from-orange-500 to-amber-500 px-8 py-3.5 font-bold text-white shadow-lg shadow-orange-500/25 transition hover:scale-105"
              >
                Go to Submission Portal →
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-10">

            {/* ============================================================ */}
            {/* STAGE 1 & 2: INPUT & NLP UNDERSTANDING                       */}
            {/* ============================================================ */}
            <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-white/10">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/10 font-orbitron text-xs font-black text-orange-600 dark:text-orange-400 border border-orange-500/20">
                    01-02
                  </div>
                  <div>
                    <h2 className="text-lg font-black text-slate-900 dark:text-white">
                      Stage 1 &amp; 2: Report Input &amp; NLP Understanding
                    </h2>
                    <p className="text-xs text-slate-500">
                      Normalizes field acronyms (BOP, LEL, SCBA, PTW), evaluates contextual negations, and structures observation parameters.
                    </p>
                  </div>
                </div>
                <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                  ✓ NLP Preprocessed
                </span>
              </div>

              <div className="mt-6 grid gap-6 md:grid-cols-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/5 dark:bg-white/[0.02]">
                  <p className="text-[10px] font-bold uppercase text-slate-400">Contextual Ingestion</p>
                  <p className="mt-1 text-xs font-bold text-slate-800 dark:text-slate-200">
                    Free-Text Narrative Cleaned
                  </p>
                  <p className="mt-2 text-[11px] text-slate-500">
                    Whitespace stripped, domain contractions expanded, numerical pressures &amp; LEL values preserved.
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/5 dark:bg-white/[0.02]">
                  <p className="text-[10px] font-bold uppercase text-slate-400">Negation Filtering Engine</p>
                  <p className="mt-1 text-xs font-bold text-emerald-600 dark:text-emerald-400">
                    Active Context Window
                  </p>
                  <p className="mt-2 text-[11px] text-slate-500">
                    Phrases such as &quot;no leak observed&quot; or &quot;isolated valve&quot; are prevented from triggering false positives.
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/5 dark:bg-white/[0.02]">
                  <p className="text-[10px] font-bold uppercase text-slate-400">Domain Mapping Standard</p>
                  <p className="mt-1 text-xs font-bold text-orange-600 dark:text-orange-400">
                    OISD 113 / IOGP Life-Saving
                  </p>
                  <p className="mt-2 text-[11px] text-slate-500">
                    Mapped to upstream exploration and production safety categories.
                  </p>
                </div>
              </div>

              {/* Optional Field Image Evidence Association */}
              {analysis?.image_evidence?.image_attached && (
                <div className="mt-6 rounded-2xl border border-blue-500/20 bg-blue-50/50 p-5 dark:border-blue-500/10 dark:bg-blue-950/10">
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-500 text-base text-white shadow-sm">
                        📷
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-blue-900 dark:text-blue-300">
                            Attached Field Evidence
                          </span>
                          <span className="rounded-full bg-blue-600 px-2 py-0.5 text-[9px] font-black text-white uppercase font-mono">
                            {analysis.image_evidence.image_id}
                          </span>
                          <span className="rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 px-2 py-0.5 text-[9px] font-bold">
                            {analysis.image_evidence.format} ({Math.round((analysis.image_evidence.file_size_bytes || 0) / 1024)} KB)
                          </span>
                        </div>
                        <p className="mt-0.5 text-xs text-slate-600 dark:text-slate-400">
                          {analysis.image_evidence.original_filename} • {analysis.image_evidence.status_note}
                        </p>
                      </div>
                    </div>

                    <span className="rounded-xl border border-blue-200 bg-white px-3 py-1.5 text-xs font-semibold text-blue-700 dark:border-white/10 dark:bg-white/5 dark:text-blue-300 self-start sm:self-auto">
                      Associated with Report
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* ============================================================ */}
            {/* STAGE 3 & 4: SIF PRECURSOR DETECTION & SEVERITY PREDICTION   */}
            {/* ============================================================ */}
            <div className="grid gap-8 lg:grid-cols-2">
              {/* STAGE 3: SIF PRECURSOR DETECTION */}
              <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-white/10">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/10 font-orbitron text-xs font-black text-orange-600 dark:text-orange-400 border border-orange-500/20">
                      03
                    </div>
                    <div>
                      <h2 className="text-base font-black text-slate-900 dark:text-white">
                        Stage 3: SIF Precursor Detection
                      </h2>
                      <p className="text-[11px] text-slate-500">11-Category Domain SIF Taxonomy</p>
                    </div>
                  </div>
                  <span className="rounded-full bg-orange-500/10 px-3 py-1 text-xs font-bold text-orange-600 dark:text-orange-400">
                    {precursors.length} Active
                  </span>
                </div>

                {precursors.length > 0 ? (
                  <div className="mt-6 space-y-4">
                    {precursors.map((item, index) => (
                      <div
                        key={index}
                        className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/5 dark:bg-white/[0.02]"
                      >
                        <div className="flex items-center justify-between">
                          <p className="font-bold text-xs text-slate-900 dark:text-white">
                            ⚠️ {item.label || item.factor}
                          </p>
                          {item.contribution !== undefined && (
                            <span className="rounded-full bg-orange-500/10 px-2.5 py-0.5 text-xs font-bold text-orange-600 dark:text-orange-400">
                              +{item.contribution} Pts
                            </span>
                          )}
                        </div>

                        {item.evidence && (
                          <p className="mt-2 text-[11px] text-slate-600 dark:text-slate-400">
                            <span className="font-semibold text-slate-700 dark:text-slate-300">
                              Extracted Evidence:{" "}
                            </span>
                            {Array.isArray(item.evidence)
                              ? item.evidence.join(", ")
                              : String(item.evidence)}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-6 rounded-2xl border border-dashed border-slate-200 p-8 text-center text-xs text-slate-500 dark:border-white/10">
                    ✅ No critical SIF precursors detected. Routine baseline observation.
                  </div>
                )}
              </div>

              {/* STAGE 4: SEVERITY PREDICTION */}
              <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-white/10">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/10 font-orbitron text-xs font-black text-orange-600 dark:text-orange-400 border border-orange-500/20">
                      04
                    </div>
                    <div>
                      <h2 className="text-base font-black text-slate-900 dark:text-white">
                        Stage 4: ML Severity Prediction
                      </h2>
                      <p className="text-[11px] text-slate-500">Linear SVM Hyperplane Multi-Class</p>
                    </div>
                  </div>
                  <span className="rounded-full bg-blue-500/10 px-3 py-1 text-xs font-bold text-blue-600 dark:text-blue-400">
                    {analysis?.severity_prediction?.model_version || "v1.2.0-calibrated"}
                  </span>
                </div>

                <div className="mt-6">
                  <div className="flex items-baseline justify-between">
                    <div>
                      <p className="text-xs font-bold uppercase text-slate-400">Potential Accident Level</p>
                      <p className="mt-1 font-orbitron text-5xl font-black text-orange-500">
                        {rawSeverity}
                      </p>
                    </div>
                    <span className="rounded-2xl bg-orange-500/10 px-4 py-2 font-bold text-xs text-orange-600 dark:text-orange-400 border border-orange-500/20">
                      {severity}
                    </span>
                  </div>

                  <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/5 dark:bg-white/[0.02] space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Classifier Architecture:</span>
                      <span className="font-semibold text-slate-700 dark:text-slate-300">
                        {analysis?.severity_prediction?.model || "Linear SVM (TF-IDF)"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Decision Margin Confidence:</span>
                      <span className="font-semibold text-emerald-600 dark:text-emerald-400">
                        {analysis?.severity_prediction?.confidence
                          ? `${(analysis.severity_prediction.confidence * 100).toFixed(1)}%`
                          : "Calibrated"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Calibration State:</span>
                      <span className="font-semibold text-slate-700 dark:text-slate-300">
                        {analysis?.severity_prediction?.calibration_note || "Zero False-Alarm Cap"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* ============================================================ */}
            {/* STAGE 5: RISK ASSESSMENT (EXPLAINABLE SIF RISK SCORE)        */}
            {/* ============================================================ */}
            <div className={`rounded-3xl border p-8 shadow-sm ${riskColor.border} ${riskColor.bg}`}>
              <div className="flex items-center justify-between border-b border-slate-200 pb-4 dark:border-white/10">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/10 font-orbitron text-xs font-black text-orange-600 dark:text-orange-400 border border-orange-500/20">
                    05
                  </div>
                  <div>
                    <h2 className="text-lg font-black text-slate-900 dark:text-white">
                      Stage 5: Transparent SIF Risk Score
                    </h2>
                    <p className="text-xs text-slate-500">
                      Transparent mathematical attribution without magic numbers (Score range: 0 to 100).
                    </p>
                  </div>
                </div>
                <span className={`rounded-full px-3.5 py-1 text-xs font-black uppercase ${riskColor.badge}`}>
                  {riskLevel} RISK TIER
                </span>
              </div>

              <div className="mt-6 grid gap-6 md:grid-cols-3 items-center">
                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-slate-400">Overall SIF Risk Score</p>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className={`font-orbitron text-6xl font-black ${riskColor.text}`}>
                      {riskScore}
                    </span>
                    <span className="text-xs font-bold text-slate-400">/ 100</span>
                  </div>
                  <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-white/10">
                    <div
                      className={`h-full ${riskColor.bar} transition-all duration-700`}
                      style={{ width: `${Math.min(riskScore, 100)}%` }}
                    />
                  </div>
                </div>

                <div className="md:col-span-2 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#0a1915] space-y-2 text-xs">
                  <p className="font-bold text-slate-800 dark:text-slate-200">
                    Executive Summary &amp; Rationale:
                  </p>
                  <p className="leading-relaxed text-slate-600 dark:text-slate-400 font-medium">
                    {summary}
                  </p>
                  {analysis?.overall_risk?.formula_explanation && (
                    <p className="mt-2 font-mono text-[11px] text-orange-600 dark:text-orange-400">
                      📐 Calculation: {analysis.overall_risk.formula_explanation}
                    </p>
                  )}
                </div>
              </div>
            </div>

            {/* ============================================================ */}
            {/* STAGE 6: HISTORICAL EVIDENCE (VECTOR PRECEDENTS)             */}
            {/* ============================================================ */}
            <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-white/10">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/10 font-orbitron text-xs font-black text-orange-600 dark:text-orange-400 border border-orange-500/20">
                    06
                  </div>
                  <div>
                    <h2 className="text-lg font-black text-slate-900 dark:text-white">
                      Stage 6: Historical Precedent Retrieval
                    </h2>
                    <p className="text-xs text-slate-500">
                      Sublinear TF-IDF + Cosine Similarity search over 425 historical incident cases.
                    </p>
                  </div>
                </div>
                <span className="rounded-full bg-cyan-500/10 px-3 py-1 text-xs font-bold text-cyan-600 dark:text-cyan-400">
                  {similarCases.length} Cases Retrieved
                </span>
              </div>

              {similarCases.length > 0 ? (
                <div className="mt-6 space-y-4">
                  {similarCases.map((incident, index) => {
                    const incSeverity =
                      incident.potential_accident_level ??
                      incident.potential_incident_level;

                    return (
                      <div
                        key={incident.incident_id ?? index}
                        className="rounded-2xl border border-slate-200 p-5 transition hover:border-orange-400 hover:shadow-md dark:border-white/10 dark:hover:border-orange-500/40"
                      >
                        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="rounded-lg bg-orange-500/10 px-2.5 py-1 text-xs font-bold text-orange-600 dark:text-orange-400">
                                Incident #{incident.incident_id ?? index + 1}
                              </span>

                              {incSeverity && (
                                <span className="rounded-lg bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700 dark:bg-white/10 dark:text-slate-300">
                                  Severity: {incSeverity}
                                </span>
                              )}

                              {incident.critical_risk && (
                                <span className="rounded-lg bg-red-500/10 px-2.5 py-1 text-xs font-bold text-red-500">
                                  Critical: {incident.critical_risk}
                                </span>
                              )}
                            </div>

                            <p className="mt-3 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                              {incident.description || "No description recorded."}
                            </p>
                          </div>

                          <div className="shrink-0 rounded-2xl bg-slate-100 px-5 py-3 text-center dark:bg-white/5">
                            <p className="text-[10px] font-bold text-slate-400 uppercase">
                              Cosine Match
                            </p>
                            <p className="mt-0.5 font-orbitron text-xl font-black text-orange-500">
                              {formatSimilarity(incident.similarity)}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="mt-6 rounded-2xl border border-dashed border-slate-200 p-8 text-center text-xs text-slate-500 dark:border-white/10">
                  No historical precedents met the 10% similarity threshold.
                </div>
              )}
            </div>

            {/* ============================================================ */}
            {/* STAGE 7: RECOMMENDED ACTION (EVIDENCE-BASED MITIGATIONS)     */}
            {/* ============================================================ */}
            <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
              <div className="flex items-center justify-between border-b border-slate-100 pb-4 dark:border-white/10">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/10 font-orbitron text-xs font-black text-orange-600 dark:text-orange-400 border border-orange-500/20">
                    07
                  </div>
                  <div>
                    <h2 className="text-lg font-black text-slate-900 dark:text-white">
                      Stage 7: Evidence-Based Corrective Mitigations
                    </h2>
                    <p className="text-xs text-slate-500">
                      Hierarchy of Controls directly tied to detected precursor triggers and field roles.
                    </p>
                  </div>
                </div>
                <span className="rounded-full bg-orange-500/10 px-3 py-1 text-xs font-bold text-orange-600 dark:text-orange-400">
                  {correctiveActions.length || recommendedActions.length} Prescribed Actions
                </span>
              </div>

              {correctiveActions.length > 0 ? (
                <div className="mt-6 space-y-4">
                  {correctiveActions.map((ca, idx) => {
                    const currentActId = ca.action_id || `ACT-${idx + 1}`;
                    const currentStatus = actionStatuses[currentActId]?.status || ca.status || "OPEN";
                    const isVer = actionStatuses[currentActId]?.verification_status === "VERIFIED" || ca.verification_status === "VERIFIED";
                    const isUpdating = actionStatuses[currentActId]?.isUpdating;

                    return (
                      <div
                        key={idx}
                        className="rounded-2xl border border-slate-200 bg-slate-50 p-5 dark:border-white/5 dark:bg-white/[0.02] space-y-3"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200/60 pb-3 dark:border-white/5">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[11px] font-bold text-slate-500 dark:text-slate-400">
                              {currentActId}
                            </span>
                            <span
                              className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                                ca.priority === "IMMEDIATE"
                                  ? "bg-red-500/10 text-red-600 border border-red-500/20"
                                  : ca.priority === "HIGH"
                                  ? "bg-orange-500/10 text-orange-600 border border-orange-500/20"
                                  : "bg-blue-500/10 text-blue-600 border border-blue-500/20"
                              }`}
                            >
                              {ca.priority} PRIORITY
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            {/* Action Lifecycle Badge */}
                            <span
                              className={`rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-wider ${
                                currentStatus === "VERIFIED"
                                  ? "bg-emerald-500/15 text-emerald-600 border border-emerald-500/30 dark:text-emerald-400"
                                  : currentStatus === "COMPLETED"
                                  ? "bg-indigo-500/15 text-indigo-600 border border-indigo-500/30 dark:text-indigo-400"
                                  : currentStatus === "IN_PROGRESS"
                                  ? "bg-amber-500/15 text-amber-600 border border-amber-500/30 dark:text-amber-400"
                                  : "bg-slate-200 text-slate-700 dark:bg-white/10 dark:text-slate-300"
                              }`}
                            >
                              {currentStatus === "VERIFIED" ? "✓ VERIFIED" : currentStatus}
                            </span>

                            <span className="text-[11px] font-semibold text-orange-600 dark:text-orange-400">
                              Role: {ca.responsible_safety_role || ca.responsible_role || "Process Safety Lead"}
                            </span>
                          </div>
                        </div>

                        <p className="text-xs font-bold text-slate-900 dark:text-white leading-relaxed">
                          {ca.action}
                        </p>

                        <div className="grid gap-2 sm:grid-cols-2 text-[11px] text-slate-600 dark:text-slate-400">
                          <p>
                            <span className="font-semibold text-slate-700 dark:text-slate-300">Physical Verification:</span>{" "}
                            {ca.verification_step}
                          </p>
                          <p>
                            <span className="font-semibold text-slate-700 dark:text-slate-300">Hazard Traceability:</span>{" "}
                            {ca.reason}
                          </p>
                        </div>

                        {/* Safety Officer Action Tracking Workflow Controls */}
                        <div className="mt-2 flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-200/60 dark:border-white/5">
                          <div className="flex items-center gap-2">
                            <span className="text-[11px] font-bold text-slate-500 dark:text-slate-400">
                              Update Tracking Status:
                            </span>
                            <div className="flex gap-1.5">
                              {(["OPEN", "IN_PROGRESS", "COMPLETED", "VERIFIED"] as const).map((st) => (
                                <button
                                  key={st}
                                  type="button"
                                  disabled={isUpdating || currentStatus === st}
                                  onClick={() => handleActionStatusChange(currentActId, st)}
                                  className={`rounded-lg px-2.5 py-1 text-[10px] font-bold transition ${
                                    currentStatus === st
                                      ? "bg-orange-500 text-white shadow-sm"
                                      : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-100 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
                                  }`}
                                >
                                  {st === "IN_PROGRESS" ? "In Progress" : st.charAt(0) + st.slice(1).toLowerCase()}
                                </button>
                              ))}
                            </div>
                          </div>

                          {actionStatuses[currentActId]?.updated_by && (
                            <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">
                              Updated by {actionStatuses[currentActId].updated_by}
                            </span>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : recommendedActions.length > 0 ? (
                <div className="mt-6 space-y-3">
                  {recommendedActions.map((action, idx) => (
                    <div
                      key={idx}
                      className="flex gap-3.5 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/5 dark:bg-white/[0.02]"
                    >
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-orange-500 text-xs font-bold text-white">
                        {idx + 1}
                      </span>
                      <p className="text-xs leading-relaxed text-slate-700 dark:text-slate-300 font-medium">
                        {action}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="mt-6 rounded-2xl border border-dashed border-slate-200 p-8 text-center text-xs text-slate-500 dark:border-white/10">
                  Standard operating procedures and field vigilance apply.
                </div>
              )}
            </div>

            {/* ============================================================ */}
            {/* STAGE 8: HUMAN SAFETY REVIEW (SAFETY OFFICER AUTHORITY)      */}
            {/* ============================================================ */}
            <div className="rounded-3xl border-2 border-orange-500/40 bg-white p-8 shadow-lg dark:border-orange-500/30 dark:bg-[#0a1915]">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-slate-200 pb-5 dark:border-white/10">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-500/20 font-orbitron text-xs font-black text-orange-600 dark:text-orange-400 border border-orange-500/30">
                    08
                  </div>
                  <div>
                    <h2 className="text-xl font-black text-slate-950 dark:text-white">
                      Stage 8: Human-in-the-Loop Safety Officer Review
                    </h2>
                    <p className="text-xs text-slate-500">
                      Authoritative human safety governance &amp; Permit-to-Work gatekeeper per OISD standard.
                    </p>
                  </div>
                </div>

                {reviewRecord ? (
                  <div className="flex items-center gap-2 rounded-full bg-emerald-500/10 px-4 py-1.5 text-xs font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    <span>🛡️ Verified #{reviewRecord.review_id}</span>
                  </div>
                ) : !isOfficer ? (
                  <div className="flex items-center gap-2 rounded-full bg-slate-100 dark:bg-white/5 px-4 py-1.5 text-xs font-bold text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-white/10">
                    <span>👁️ Field Employee View-Only</span>
                  </div>
                ) : null}
              </div>

              {/* ACTION MODE SELECTOR */}
              <div className="mt-6">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Select Safety Officer Action
                </p>
                <div className="mt-3 grid gap-3 sm:grid-cols-3">
                  <button
                    onClick={() => handleSelectReviewMode("ACCEPTED")}
                    className={`flex items-center justify-center gap-2 rounded-2xl border p-4 text-xs font-bold transition ${
                      reviewMode === "ACCEPTED"
                        ? "border-emerald-500 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shadow-sm"
                        : "border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 dark:border-white/10 dark:bg-white/5 dark:text-slate-400"
                    }`}
                  >
                    <span>✅</span> Accept AI Classification
                  </button>

                  <button
                    onClick={() => handleSelectReviewMode("MODIFIED")}
                    className={`flex items-center justify-center gap-2 rounded-2xl border p-4 text-xs font-bold transition ${
                      reviewMode === "MODIFIED"
                        ? "border-orange-500 bg-orange-500/10 text-orange-600 dark:text-orange-400 shadow-sm"
                        : "border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 dark:border-white/10 dark:bg-white/5 dark:text-slate-400"
                    }`}
                  >
                    <span>✏️</span> Modify Precursors &amp; Severity
                  </button>

                  <button
                    onClick={() => handleSelectReviewMode("REJECTED")}
                    className={`flex items-center justify-center gap-2 rounded-2xl border p-4 text-xs font-bold transition ${
                      reviewMode === "REJECTED"
                        ? "border-red-500 bg-red-500/10 text-red-600 dark:text-red-400 shadow-sm"
                        : "border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300 dark:border-white/10 dark:bg-white/5 dark:text-slate-400"
                    }`}
                  >
                    <span>❌</span> Reject AI Hazard Assessment
                  </button>
                </div>
              </div>

              {/* MODIFICATION CONTROLS (IF MODIFIED OR REJECTED) */}
              {reviewMode !== "ACCEPTED" && (
                <div className="mt-6 rounded-2xl border border-dashed border-orange-500/30 bg-orange-500/[0.02] p-6 space-y-5">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400">
                    Officer Calibration &amp; Override Inputs
                  </h3>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div>
                      <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                        Authoritative Potential Severity Level:
                      </label>
                      <select
                        value={selectedSeverity}
                        disabled={!isOfficer}
                        onChange={(e) => setSelectedSeverity(e.target.value)}
                        className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs font-bold text-slate-800 dark:border-white/10 dark:bg-[#050d0a] dark:text-white disabled:opacity-60 disabled:cursor-not-allowed"
                      >
                        <option value="I">Level I — Minor Hazard</option>
                        <option value="II">Level II — Moderate Hazard</option>
                        <option value="III">Level III — Serious Hazard</option>
                        <option value="IV">Level IV — Critical SIF Potential</option>
                        <option value="V">Level V — Catastrophic SIF Hazard</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                        Calibrated Risk Score (0 - 100):
                      </label>
                      <input
                        type="number"
                        min="0"
                        max="100"
                        value={overrideScore}
                        disabled={!isOfficer}
                        onChange={(e) => setOverrideScore(Math.max(0, Math.min(100, Number(e.target.value))))}
                        className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs font-bold text-slate-800 dark:border-white/10 dark:bg-[#050d0a] dark:text-white disabled:opacity-60 disabled:cursor-not-allowed"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                      Authorized Field Actions ({activeActionsList.length} items):
                    </label>
                    <div className="mt-2 space-y-2">
                      {activeActionsList.map((act, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-3 text-xs dark:border-white/10 dark:bg-[#050d0a]"
                        >
                          <span className="text-slate-800 dark:text-slate-200 font-medium">{act}</span>
                          {isOfficer && (
                            <button
                              onClick={() => handleRemoveAction(idx)}
                              className="text-red-500 hover:text-red-700 text-xs font-bold"
                            >
                              Remove
                            </button>
                          )}
                        </div>
                      ))}
                    </div>

                    {isOfficer && (
                      <div className="mt-3 flex gap-2">
                        <input
                          type="text"
                          placeholder="Add custom officer safety directive..."
                          value={customActionText}
                          onChange={(e) => setCustomActionText(e.target.value)}
                          className="flex-1 rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-800 dark:border-white/10 dark:bg-[#050d0a] dark:text-white"
                        />
                        <button
                          onClick={handleAddCustomAction}
                          className="rounded-xl bg-orange-500 px-4 py-2.5 text-xs font-bold text-white hover:bg-orange-600"
                        >
                          + Add Action
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* REVIEWER CREDENTIALS & REMARKS */}
              <div className="mt-6 grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                    Reviewing Officer Name:
                  </label>
                  <input
                    type="text"
                    value={officerName}
                    disabled={!isOfficer}
                    onChange={(e) => setOfficerName(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-800 dark:border-white/10 dark:bg-[#050d0a] dark:text-white disabled:opacity-60 disabled:cursor-not-allowed"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 dark:text-slate-300">
                    Safety Officer ID / Badge:
                  </label>
                  <input
                    type="text"
                    value={officerId}
                    disabled={!isOfficer}
                    onChange={(e) => setOfficerId(e.target.value)}
                    className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white p-2.5 text-xs text-slate-800 dark:border-white/10 dark:bg-[#050d0a] dark:text-white disabled:opacity-60 disabled:cursor-not-allowed"
                  />
                </div>
              </div>

              <div className="mt-4">
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300 flex items-center justify-between">
                  <span>Officer Remarks &amp; Justification Note:</span>
                  {reviewMode !== "ACCEPTED" && (
                    <span className="text-[10px] font-bold text-orange-600 dark:text-orange-400 uppercase">
                      * Required for {reviewMode}
                    </span>
                  )}
                </label>
                <textarea
                  rows={2}
                  disabled={!isOfficer}
                  placeholder={
                    !isOfficer
                      ? "Safety Officer review notes will appear here once submitted."
                      : reviewMode === "ACCEPTED"
                      ? "Optional confirmation remarks or field inspection notes..."
                      : "Provide mandatory operational justification for adjusting/rejecting the AI determination..."
                  }
                  value={reviewerComment}
                  onChange={(e) => {
                    setReviewerComment(e.target.value);
                    if (reviewError) setReviewError(null);
                  }}
                  className="mt-1.5 w-full rounded-xl border border-slate-200 bg-white p-3 text-xs text-slate-800 dark:border-white/10 dark:bg-[#050d0a] dark:text-white disabled:opacity-60 disabled:cursor-not-allowed"
                />
              </div>

              {/* VALIDATION ERROR BANNER */}
              {reviewError && (
                <div className="mt-4 rounded-2xl border border-red-500/30 bg-red-500/10 p-3.5 text-xs font-bold text-red-600 dark:text-red-400 flex items-center gap-2">
                  <span>⚠️</span>
                  <span>{reviewError}</span>
                </div>
              )}

              {/* SUBMIT BUTTON */}
              <div className="mt-6 flex items-center justify-between pt-4 border-t border-slate-200 dark:border-white/10">
                <p className="text-[11px] text-slate-500">
                  * Authoritative determination is saved to the compliance audit store.
                </p>

                <button
                  onClick={handleSubmitReview}
                  disabled={isSubmitting}
                  className="rounded-full bg-gradient-to-r from-orange-500 to-amber-500 px-8 py-3 text-xs font-extrabold text-white shadow-md shadow-orange-500/25 transition hover:scale-105 disabled:opacity-50"
                >
                  {isSubmitting ? "Archiving Review..." : "Confirm & Save Officer Determination →"}
                </button>
              </div>

              {/* ARCHIVED AUDIT CARD */}
              {reviewRecord && (
                <div className="mt-6 rounded-2xl border border-emerald-500/30 bg-emerald-500/[0.04] p-5">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-xs text-emerald-600 dark:text-emerald-400">
                      ✅ Final Authoritative Operational Record Archived
                    </span>
                    <span className="font-mono text-[10px] text-slate-400">
                      {reviewRecord.timestamp}
                    </span>
                  </div>

                  <div className="mt-3 grid gap-3 sm:grid-cols-3 text-xs">
                    <div>
                      <span className="text-slate-400">Final Severity:</span>{" "}
                      <span className="font-bold text-orange-500">
                        {reviewRecord.final_decision.potential_accident_level}
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400">Final Risk Score:</span>{" "}
                      <span className="font-bold text-orange-500">
                        {reviewRecord.final_decision.overall_risk_score} (
                        {reviewRecord.final_decision.overall_risk_level})
                      </span>
                    </div>
                    <div>
                      <span className="text-slate-400">Reviewed By:</span>{" "}
                      <span className="font-bold text-slate-800 dark:text-slate-200">
                        {reviewRecord.officer_name} ({reviewRecord.officer_id})
                      </span>
                    </div>
                  </div>

                  <p className="mt-2 text-xs text-slate-600 dark:text-slate-400 italic">
                    &quot;{reviewRecord.reviewer_comment}&quot;
                  </p>
                </div>
              )}
            </div>

          </div>
        )}
      </section>

      {/* SAFETY OFFICER ACCESS REQUIRED MODAL */}
      {showOfficerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
          <div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-orange-500/30 bg-white p-6 shadow-2xl dark:bg-[#0a1915] dark:border-orange-500/30">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-orange-500/10 border border-orange-500/30 text-2xl text-orange-500">
                🛡️
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                  Safety Officer Access Required
                </h3>
                <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                  Only authorized Safety Officers can submit or modify safety reviews. Please login as a Safety Officer to continue.
                </p>
                {currentUser && (
                  <div className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-600 dark:bg-white/5 dark:text-slate-400">
                    <span>Logged in as:</span>
                    <span className="font-semibold text-slate-800 dark:text-slate-200 capitalize">
                      {currentUser.role} ({currentUser.email})
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-6 flex items-center justify-end gap-3 border-t border-slate-200/80 pt-4 dark:border-white/10">
              <button
                type="button"
                onClick={() => setShowOfficerModal(false)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 dark:border-white/10 dark:text-slate-400 dark:hover:bg-white/5"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowOfficerModal(false);
                  router.push("/login?redirect=/analysis");
                }}
                className="rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 px-5 py-2 text-xs font-bold text-white shadow-md shadow-orange-500/20 transition hover:scale-105"
              >
                Login as Safety Officer →
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
