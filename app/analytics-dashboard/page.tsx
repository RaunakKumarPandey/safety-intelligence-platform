"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import ThemeToggle from "../components/ThemeToggle";
import {
  fetchOperationalAnalytics,
  fetchModelPerformanceAnalytics,
  fetchSafetyAlerts,
  updateSafetyAlertStatus,
  fetchTrackedActions,
  updateTrackedActionStatus,
  fetchActionStatistics,
  OperationalAnalyticsData,
  ModelPerformanceAnalyticsData,
  SafetyAlertRecord,
  ActionTrackingRecord,
  ActionTrackingStatistics
} from "@/lib/api";
import { getStoredUser, UserSession, isSafetyOfficer } from "@/lib/auth";
import { useRouter, useSearchParams } from "next/navigation";

function AnalyticsDashboardContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const viewParam = searchParams.get("view");
  const [currentUser, setCurrentUser] = useState<UserSession | null>(null);
  const [showAccessModal, setShowAccessModal] = useState(false);
  const [activeTab, setActiveTab] = useState<"operational" | "model_performance" | "alerts" | "actions">("operational");
  const [operationalData, setOperationalData] = useState<OperationalAnalyticsData | null>(null);
  const [modelData, setModelData] = useState<ModelPerformanceAnalyticsData | null>(null);
  const [alerts, setAlerts] = useState<SafetyAlertRecord[]>([]);
  const [alertFilter, setAlertFilter] = useState<string>("ALL");
  const [alertSearchQuery, setAlertSearchQuery] = useState<string>("");
  const [isUpdatingAlert, setIsUpdatingAlert] = useState<string | null>(null);
  const [officerNotes, setOfficerNotes] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);

  // Corrective Action Tracking State (Task 10)
  const [actions, setActions] = useState<ActionTrackingRecord[]>([]);
  const [actionFilter, setActionFilter] = useState<string>("ALL");
  const [actionSearchQuery, setActionSearchQuery] = useState<string>("");
  const [actionStats, setActionStats] = useState<ActionTrackingStatistics | null>(null);
  const [isUpdatingAction, setIsUpdatingAction] = useState<string | null>(null);
  const [actionOfficerNotes, setActionOfficerNotes] = useState<Record<string, string>>({});

  const loadData = async (user?: UserSession | null) => {
    setIsLoading(true);
    try {
      const activeUser = user !== undefined ? user : getStoredUser();
      const isOfficer = isSafetyOfficer(activeUser);

      const promises: [
        Promise<OperationalAnalyticsData | null>,
        Promise<ModelPerformanceAnalyticsData | null>,
        Promise<SafetyAlertRecord[]>,
        Promise<ActionTrackingRecord[]>,
        Promise<ActionTrackingStatistics | null>
      ] = [
        fetchOperationalAnalytics(),
        isOfficer ? fetchModelPerformanceAnalytics() : Promise.resolve(null),
        fetchSafetyAlerts(),
        fetchTrackedActions(),
        fetchActionStatistics()
      ];

      const [op, mod, altList, actList, stats] = await Promise.all(promises);
      setOperationalData(op);
      setModelData(mod);
      setAlerts(altList);
      setActions(actList);
      setActionStats(stats);
    } catch (err) {
      console.error("[Analytics] Error in loadData:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const user = getStoredUser();
    setCurrentUser(user);
    if (viewParam === "model-validation") {
      setActiveTab("model_performance");
    }
    loadData(user);

    // Auto-poll for live employee submissions every 15 seconds
    const intervalId = setInterval(() => {
      loadData(user);
    }, 15000);

    return () => clearInterval(intervalId);
  }, [viewParam]);

  const handleActionStatusChange = async (actionId: string, newStatus: string) => {
    const session = getStoredUser();
    if (!session || session.role !== "officer") {
      setShowAccessModal(true);
      return;
    }

    try {
      setIsUpdatingAction(actionId);
      const note = actionOfficerNotes[actionId] || "";
      const officerName = session.name || "Safety Officer";
      const officerId = session.email ? `HSE-${session.email.split("@")[0].toUpperCase()}` : "HSE-8492";
      const res = await updateTrackedActionStatus(actionId, newStatus, note, officerName, officerId, 6000, session.role);
      if (res.success && res.action) {
        setActions((prev) =>
          prev.map((a) => (a.action_id === actionId ? res.action! : a))
        );
        const newStats = await fetchActionStatistics();
        if (newStats) setActionStats(newStats);
      }
    } catch (e) {
      console.error("Failed to update action status:", e);
    } finally {
      setIsUpdatingAction(null);
    }
  };

  const handleStatusChange = async (alertId: string, newStatus: "ACKNOWLEDGED" | "RESOLVED") => {
    const session = getStoredUser();
    if (!session || session.role !== "officer") {
      setShowAccessModal(true);
      return;
    }

    try {
      setIsUpdatingAlert(alertId);
      const note = officerNotes[alertId] || "";
      const officerName = session.name || "Safety Officer";
      const officerId = session.email ? `HSE-${session.email.split("@")[0].toUpperCase()}` : "HSE-8492";
      const res = await updateSafetyAlertStatus(alertId, newStatus, note, officerName, officerId, 6000, session.role);
      if (res.success && res.alert) {
        setAlerts((prev) =>
          prev.map((a) => (a.alert_id === alertId ? res.alert! : a))
        );
      }
    } catch (e) {
      console.error("Failed to update alert:", e);
    } finally {
      setIsUpdatingAlert(null);
    }
  };

  const filteredAlerts = alerts.filter((a) => {
    const matchesStatus = alertFilter === "ALL" || a.alert_status === alertFilter;
    if (!matchesStatus) return false;
    if (!alertSearchQuery.trim()) return true;
    const q = alertSearchQuery.toLowerCase().trim();
    return (
      a.alert_id.toLowerCase().includes(q) ||
      (a.location && a.location.toLowerCase().includes(q)) ||
      (a.department && a.department.toLowerCase().includes(q)) ||
      (a.observation_excerpt && a.observation_excerpt.toLowerCase().includes(q)) ||
      (a.risk_level && a.risk_level.toLowerCase().includes(q)) ||
      (a.recommended_immediate_action && a.recommended_immediate_action.toLowerCase().includes(q)) ||
      (a.detected_precursors && a.detected_precursors.some((p) => p.toLowerCase().includes(q)))
    );
  });

  const newAlertsCount = alerts.filter((a) => a.alert_status === "NEW").length;
  const acknowledgedCount = alerts.filter((a) => a.alert_status === "ACKNOWLEDGED").length;
  const resolvedCount = alerts.filter((a) => a.alert_status === "RESOLVED").length;

  const openActionsCount = actions.filter((a) => a.status === "OPEN" || a.status === "IN_PROGRESS").length;
  const filteredActions = actions.filter((a) => {
    const matchesStatus = actionFilter === "ALL" || a.status === actionFilter;
    if (!matchesStatus) return false;
    if (!actionSearchQuery.trim()) return true;
    const q = actionSearchQuery.toLowerCase().trim();
    return (
      a.action_id.toLowerCase().includes(q) ||
      (a.report_id && a.report_id.toLowerCase().includes(q)) ||
      (a.action_description && a.action_description.toLowerCase().includes(q)) ||
      (a.responsible_role && a.responsible_role.toLowerCase().includes(q)) ||
      (a.tracking_notes && a.tracking_notes.toLowerCase().includes(q)) ||
      (a.priority && a.priority.toLowerCase().includes(q)) ||
      (a.ai_generated_context?.related_precursor && a.ai_generated_context.related_precursor.toLowerCase().includes(q)) ||
      (a.ai_generated_context?.immediate_control && a.ai_generated_context.immediate_control.toLowerCase().includes(q))
    );
  });

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
                Oil India Limited • Analytics &amp; Safety Governance
              </p>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/"
              className="rounded-full border border-slate-200 bg-white/50 px-4 py-2 text-xs font-bold transition hover:bg-slate-100 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
            >
              ← Back to Portal
            </Link>
          </div>
        </div>
      </header>

      {/* BODY */}
      <section className="mx-auto max-w-7xl px-6 py-10">
        {/* Title */}
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-3.5 py-1 text-[10px] font-bold tracking-wider text-orange-600 dark:text-orange-400 uppercase">
                Analytics &amp; Safety Governance
              </span>
              <span className="rounded-full bg-emerald-500/10 px-3 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                Zero-Leakage Verified
              </span>
            </div>
            <h1 className="mt-3 text-3xl font-black md:text-4xl">
              Safety Intelligence &amp; Operational Analytics
            </h1>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              Operational field distributions, automated SIF risk alerts, and corrective action workflows.
            </p>
          </div>

          {/* TAB SWITCHER */}
          <div className="flex flex-wrap rounded-2xl border border-slate-200 bg-slate-100/80 p-1.5 dark:border-white/10 dark:bg-white/5">
            <button
              onClick={() => setActiveTab("operational")}
              className={`rounded-xl px-4 py-2 text-xs font-bold transition ${
                activeTab === "operational"
                  ? "bg-white text-orange-600 shadow-sm dark:bg-[#0a1915] dark:text-orange-400"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              }`}
            >
              📊 Operational Analytics
            </button>
            {isSafetyOfficer(currentUser) && (
              <button
                onClick={() => setActiveTab("model_performance")}
                className={`rounded-xl px-4 py-2 text-xs font-bold transition ${
                  activeTab === "model_performance"
                    ? "bg-white text-orange-600 shadow-sm dark:bg-[#0a1915] dark:text-orange-400"
                    : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
                }`}
              >
                🎯 ML Model Validation
              </button>
            )}
            <button
              onClick={() => setActiveTab("alerts")}
              className={`rounded-xl px-4 py-2 text-xs font-bold transition flex items-center gap-1.5 ${
                activeTab === "alerts"
                  ? "bg-white text-orange-600 shadow-sm dark:bg-[#0a1915] dark:text-orange-400"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              }`}
            >
              <span>🚨 SIF Risk Alerts</span>
              {newAlertsCount > 0 && (
                <span className="rounded-full bg-red-500 px-1.5 py-0.2 text-[9px] font-black text-white">
                  {newAlertsCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab("actions")}
              className={`rounded-xl px-4 py-2 text-xs font-bold transition flex items-center gap-1.5 ${
                activeTab === "actions"
                  ? "bg-white text-orange-600 shadow-sm dark:bg-[#0a1915] dark:text-orange-400"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              }`}
            >
              <span>📋 Action Tracker</span>
              {openActionsCount > 0 && (
                <span className="rounded-full bg-amber-500 px-1.5 py-0.2 text-[9px] font-black text-white">
                  {openActionsCount}
                </span>
              )}
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="mt-12 rounded-3xl border border-slate-200 bg-white p-16 text-center shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
            <div className="animate-spin text-4xl">⏳</div>
            <p className="mt-4 text-sm font-bold text-slate-500 dark:text-slate-400">
              Loading verified analytics telemetry...
            </p>
          </div>
        ) : activeTab === "operational" ? (
          /* ================= TAB 1: OPERATIONAL ANALYTICS ================= */
          <div className="mt-8 space-y-8">
            {!operationalData?.available ? (
              <div className="rounded-3xl border border-dashed border-slate-200 bg-white p-16 text-center dark:border-white/10 dark:bg-[#0a1915]">
                <p className="text-base font-bold text-slate-400">
                  {operationalData?.message || "Evaluation data not available"}
                </p>
              </div>
            ) : (
              <>
                {/* Metric Summary Cards */}
                <div className="grid gap-6 md:grid-cols-4">
                  <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Total Reports Analyzed
                    </p>
                    <p className="mt-3 font-orbitron text-4xl font-black text-orange-500">
                      {operationalData.total_reports_analyzed}
                    </p>
                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                      {operationalData.unique_usable_records} unique deduplicated records
                    </p>
                  </div>

                  <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      SIF Precursor Classes
                    </p>
                    <p className="mt-3 font-orbitron text-4xl font-black text-amber-500">
                      {operationalData.taxonomy_precursor_categories}
                    </p>
                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                      OISD-113 &amp; DGMS aligned taxonomies
                    </p>
                  </div>

                  <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Critical Risk Ratio
                    </p>
                    <p className="mt-3 font-orbitron text-4xl font-black text-red-500">
                      {operationalData.risk_level_distribution
                        ? Math.round(
                            (operationalData.risk_level_distribution.CRITICAL /
                              (operationalData.total_reports_analyzed || 1)) *
                              100
                          )
                        : 0}
                      %
                    </p>
                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                      {operationalData.risk_level_distribution?.CRITICAL || 0} critical risk observations
                    </p>
                  </div>

                  <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                    <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      Precedent Retrieval Base
                    </p>
                    <p className="mt-3 font-orbitron text-4xl font-black text-emerald-500">
                      {operationalData.retrieval_corpus_size}
                    </p>
                    <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                      Verified historical case database
                    </p>
                  </div>
                </div>

                {/* Distributions */}
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Severity Distribution */}
                  <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                    <h2 className="text-base font-bold text-slate-950 dark:text-white">
                      Severity Distribution (Level I to V)
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      Historical breakdown of incident severity ratings in the knowledge corpus.
                    </p>

                    <div className="mt-6 space-y-3">
                      {operationalData.severity_distribution &&
                        Object.entries(operationalData.severity_distribution).map(([level, count]) => {
                          const total = operationalData.total_reports_analyzed || 1;
                          const pct = Math.round((count / total) * 100);
                          return (
                            <div key={level}>
                              <div className="flex justify-between text-xs font-bold mb-1">
                                <span>Level {level}</span>
                                <span className="text-slate-500">{count} ({pct}%)</span>
                              </div>
                              <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-white/5">
                                <div
                                  className={`h-full rounded-full ${
                                    level === "V"
                                      ? "bg-red-500"
                                      : level === "IV"
                                      ? "bg-orange-500"
                                      : level === "III"
                                      ? "bg-amber-500"
                                      : level === "II"
                                      ? "bg-yellow-500"
                                      : "bg-emerald-500"
                                  }`}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                    </div>
                  </div>

                  {/* Precursor Breakdown */}
                  <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                    <h2 className="text-base font-bold text-slate-950 dark:text-white">
                      Identified SIF Precursor Frequency
                    </h2>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                      Frequency of detected precursor risk factors across historical observations.
                    </p>

                    <div className="mt-6 space-y-3">
                      {operationalData.precursor_detection_distribution &&
                        Object.entries(operationalData.precursor_detection_distribution).map(
                          ([name, count]) => {
                            const maxVal = Math.max(
                              ...Object.values(operationalData.precursor_detection_distribution || {}),
                              1
                            );
                            const pct = Math.round((count / maxVal) * 100);
                            return (
                              <div key={name}>
                                <div className="flex justify-between text-xs font-bold mb-1">
                                  <span>{name}</span>
                                  <span className="text-slate-500">{count} occurrences</span>
                                </div>
                                <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-white/5">
                                  <div
                                    className="h-full rounded-full bg-gradient-to-r from-orange-500 to-amber-500"
                                    style={{ width: `${pct}%` }}
                                  />
                                </div>
                              </div>
                            );
                          }
                        )}
                    </div>
                  </div>
                </div>

                {/* ================= LOCATION-WISE SAFETY ANALYTICS ================= */}
                <div className="rounded-3xl border border-slate-200 bg-white p-6 md:p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                    <div>
                      <h2 className="text-lg font-black text-slate-900 dark:text-white flex items-center gap-2">
                        <span>📍 Location-Wise Safety Analytics &amp; SIF Hotspots</span>
                      </h2>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Reports by location, high/critical risk rates, severity distributions, and top recurring SIF precursors.
                      </p>
                    </div>
                    <span className="rounded-full bg-orange-500/10 px-3 py-1 text-xs font-bold text-orange-600 dark:text-orange-400 border border-orange-500/20 self-start sm:self-auto">
                      {operationalData.location_analytics?.length || 0} Operating Locations
                    </span>
                  </div>

                  {(!operationalData.location_analytics || operationalData.location_analytics.length === 0) ? (
                    <div className="mt-6 rounded-2xl border border-dashed border-slate-200 p-8 text-center dark:border-white/10">
                      <p className="text-xs font-bold text-slate-400">
                        Insufficient location metadata to calculate location distributions.
                      </p>
                    </div>
                  ) : (
                    <div className="mt-6 overflow-x-auto">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="border-b border-slate-200 text-slate-400 dark:border-white/10">
                            <th className="pb-3 font-bold">Location</th>
                            <th className="pb-3 font-bold">Total Reports</th>
                            <th className="pb-3 font-bold">High / Critical Risk</th>
                            <th className="pb-3 font-bold">Severity Distribution (I - V)</th>
                            <th className="pb-3 font-bold">Top Recurring SIF Precursors</th>
                            <th className="pb-3 font-bold">Avg Risk Score</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                          {operationalData.location_analytics.map((loc) => {
                            const totalCorpus = operationalData.total_reports_analyzed || 1;
                            const locPct = Math.round((loc.total_reports / totalCorpus) * 100);
                            return (
                              <tr key={loc.location} className="hover:bg-slate-50/50 dark:hover:bg-white/[0.02]">
                                <td className="py-4 font-bold text-slate-900 dark:text-white">
                                  <div className="flex items-center gap-2">
                                    <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-orange-500/10 text-[10px] font-bold text-orange-600 dark:text-orange-400">
                                      🏢
                                    </span>
                                    <span>{loc.location}</span>
                                  </div>
                                </td>
                                <td className="py-4 font-mono">
                                  <span className="font-bold text-slate-800 dark:text-slate-200">
                                    {loc.total_reports}
                                  </span>
                                  <span className="text-[10px] text-slate-400 ml-1">
                                    ({locPct}%)
                                  </span>
                                </td>
                                <td className="py-4">
                                  <div className="flex items-center gap-2">
                                    <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                      loc.critical_risk_reports > 0
                                        ? "bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20"
                                        : loc.high_risk_reports > 0
                                        ? "bg-orange-500/10 text-orange-600 dark:text-orange-400 border border-orange-500/20"
                                        : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20"
                                    }`}>
                                      {loc.high_risk_reports} High ({loc.high_risk_percentage}%)
                                    </span>
                                    {loc.critical_risk_reports > 0 && (
                                      <span className="rounded-full bg-red-500/20 px-1.5 py-0.5 text-[9px] font-extrabold text-red-600 dark:text-red-300">
                                        {loc.critical_risk_reports} Crit
                                      </span>
                                    )}
                                  </div>
                                </td>
                                <td className="py-4 min-w-[140px]">
                                  <div className="flex items-center gap-1 text-[10px] font-mono mb-1 text-slate-400">
                                    <span>I:{loc.severity_distribution?.I || 0}</span>
                                    <span>II:{loc.severity_distribution?.II || 0}</span>
                                    <span>III:{loc.severity_distribution?.III || 0}</span>
                                    <span className="text-orange-500 font-bold">IV:{loc.severity_distribution?.IV || 0}</span>
                                    <span className="text-red-500 font-bold">V:{loc.severity_distribution?.V || 0}</span>
                                  </div>
                                  <div className="flex h-1.5 w-full overflow-hidden rounded-full bg-slate-100 dark:bg-white/5">
                                    <div style={{ width: `${((loc.severity_distribution?.I || 0) / loc.total_reports) * 100}%` }} className="bg-emerald-500" />
                                    <div style={{ width: `${((loc.severity_distribution?.II || 0) / loc.total_reports) * 100}%` }} className="bg-yellow-500" />
                                    <div style={{ width: `${((loc.severity_distribution?.III || 0) / loc.total_reports) * 100}%` }} className="bg-amber-500" />
                                    <div style={{ width: `${((loc.severity_distribution?.IV || 0) / loc.total_reports) * 100}%` }} className="bg-orange-500" />
                                    <div style={{ width: `${((loc.severity_distribution?.V || 0) / loc.total_reports) * 100}%` }} className="bg-red-500" />
                                  </div>
                                </td>
                                <td className="py-4">
                                  <div className="flex flex-wrap gap-1">
                                    {loc.top_recurring_precursors && loc.top_recurring_precursors.length > 0 ? (
                                      loc.top_recurring_precursors.map((p, idx) => (
                                        <span
                                          key={idx}
                                          className="rounded-lg bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-700 dark:bg-white/5 dark:text-slate-300 border border-slate-200 dark:border-white/10"
                                        >
                                          {p.precursor} <strong className="text-orange-500">({p.count})</strong>
                                        </span>
                                      ))
                                    ) : (
                                      <span className="text-slate-400 text-[10px]">No specific SIF precursor detected</span>
                                    )}
                                  </div>
                                </td>
                                <td className="py-4">
                                  <span className={`font-orbitron font-bold text-xs ${
                                    loc.average_risk_score >= 50
                                      ? "text-red-500"
                                      : loc.average_risk_score >= 30
                                      ? "text-orange-500"
                                      : "text-emerald-500"
                                  }`}>
                                    {loc.average_risk_score} / 100
                                  </span>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* ================= DEPARTMENT & TIME TREND ANALYTICS ================= */}
                <div className="grid gap-6 md:grid-cols-2">
                  {/* Department / Sector Breakdown */}
                  <div className="rounded-3xl border border-slate-200 bg-white p-6 md:p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-base font-bold text-slate-950 dark:text-white">
                          🏭 Department &amp; Industry Sector Breakdown
                        </h2>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          Reports and high-risk precursor exposure by operating department.
                        </p>
                      </div>
                      <span className="rounded-full bg-amber-500/10 px-2.5 py-0.5 text-[10px] font-bold text-amber-600 dark:text-amber-400 border border-amber-500/20">
                        {operationalData.department_analytics?.length || 0} Sectors
                      </span>
                    </div>

                    {(!operationalData.department_analytics || operationalData.department_analytics.length === 0) ? (
                      <div className="mt-6 rounded-2xl border border-dashed border-slate-200 p-8 text-center dark:border-white/10">
                        <p className="text-xs font-bold text-slate-400">
                          Insufficient department metadata available.
                        </p>
                      </div>
                    ) : (
                      <div className="mt-6 space-y-4">
                        {operationalData.department_analytics.map((dept) => {
                          const totalCorpus = operationalData.total_reports_analyzed || 1;
                          const pct = Math.round((dept.total_reports / totalCorpus) * 100);
                          return (
                            <div key={dept.department} className="rounded-2xl border border-slate-100 bg-slate-50/50 p-4 dark:border-white/5 dark:bg-white/[0.02]">
                              <div className="flex items-center justify-between text-xs font-bold mb-1.5">
                                <span className="text-slate-900 dark:text-white flex items-center gap-1.5">
                                  <span>🏭</span>
                                  <span>{dept.department}</span>
                                </span>
                                <span className="font-mono text-slate-600 dark:text-slate-300">
                                  {dept.total_reports} reports ({pct}%)
                                </span>
                              </div>

                              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-white/10 mb-2.5">
                                <div
                                  className="h-full rounded-full bg-gradient-to-r from-amber-500 to-orange-500"
                                  style={{ width: `${pct}%` }}
                                />
                              </div>

                              <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-200/50 dark:border-white/5 text-[10px]">
                                <div className="flex items-center gap-1.5">
                                  <span className="text-slate-400 font-medium">Risk Exposure:</span>
                                  <span className={`font-bold ${dept.high_risk_reports > 0 ? "text-orange-500" : "text-emerald-500"}`}>
                                    {dept.high_risk_reports} High ({dept.high_risk_percentage}%)
                                  </span>
                                  {dept.critical_risk_reports > 0 && (
                                    <span className="text-red-500 font-extrabold">
                                      • {dept.critical_risk_reports} Critical
                                    </span>
                                  )}
                                </div>
                                <div className="text-slate-400">
                                  Avg Score: <strong className="text-slate-700 dark:text-slate-300">{dept.average_risk_score}</strong>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Temporal Risk Trend Over Time */}
                  <div className="rounded-3xl border border-slate-200 bg-white p-6 md:p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-base font-bold text-slate-950 dark:text-white">
                          📈 Historical Risk Trend Over Time
                        </h2>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                          Monthly incident volume, high-risk frequency, and average risk progression.
                        </p>
                      </div>
                      <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                        {operationalData.time_trend_analytics?.length || 0} Periods
                      </span>
                    </div>

                    {(!operationalData.time_trend_analytics || operationalData.time_trend_analytics.length === 0) ? (
                      <div className="mt-6 rounded-2xl border border-dashed border-slate-200 p-8 text-center dark:border-white/10">
                        <p className="text-xs font-bold text-slate-400">
                          Timestamp metadata is insufficient or unavailable to plot temporal trends.
                        </p>
                      </div>
                    ) : (
                      <div className="mt-6 space-y-3.5">
                        {operationalData.time_trend_analytics.map((t) => {
                          const maxReports = Math.max(
                            ...operationalData.time_trend_analytics!.map((item) => item.total_reports),
                            1
                          );
                          const barPct = Math.round((t.total_reports / maxReports) * 100);
                          const highRiskPct = t.total_reports > 0 ? Math.round((t.high_risk_count / t.total_reports) * 100) : 0;

                          return (
                            <div key={t.period} className="rounded-2xl border border-slate-100 bg-slate-50/40 p-3.5 dark:border-white/5 dark:bg-white/[0.02]">
                              <div className="flex items-center justify-between text-xs font-bold mb-1">
                                <span className="font-mono text-slate-900 dark:text-white flex items-center gap-1.5">
                                  <span>📅</span>
                                  <span>{t.period}</span>
                                </span>
                                <div className="flex items-center gap-2 font-mono text-[11px]">
                                  <span className="text-slate-600 dark:text-slate-300">{t.total_reports} reports</span>
                                  <span className="text-orange-500 font-bold">({t.high_risk_count} High)</span>
                                </div>
                              </div>

                              <div className="relative h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-white/10 mb-2">
                                <div
                                  className="h-full rounded-full bg-slate-400 dark:bg-slate-600"
                                  style={{ width: `${barPct}%` }}
                                />
                                {t.high_risk_count > 0 && (
                                  <div
                                    className="absolute top-0 left-0 h-full rounded-full bg-gradient-to-r from-orange-500 to-red-500"
                                    style={{ width: `${(barPct * highRiskPct) / 100}%` }}
                                  />
                                )}
                              </div>

                              <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
                                <span>Top Precursor: <strong className="text-slate-700 dark:text-slate-300">{t.top_precursor}</strong></span>
                                <span>Avg Risk: <strong className="text-orange-500 font-orbitron">{t.average_risk_score}</strong></span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        ) : activeTab === "model_performance" ? (
          /* ================= TAB 2: MODEL PERFORMANCE (SAFETY OFFICER ONLY) ================= */
          !isSafetyOfficer(currentUser) ? (
            <div className="mt-8 rounded-3xl border border-slate-200 bg-white p-12 text-center shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-orange-500/10 border border-orange-500/30 text-3xl text-orange-500">
                🛡️
              </div>
              <h2 className="mt-4 text-xl font-bold text-slate-900 dark:text-white">
                Internal Model Governance
              </h2>
              <p className="mx-auto mt-2 max-w-md text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                Model performance metrics are available only to authorized safety personnel.
              </p>
              <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab("operational");
                    router.push("/analytics-dashboard");
                  }}
                  className="rounded-xl border border-slate-200 bg-slate-100 px-4 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-200 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
                >
                  ← Return to Operational Analytics
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowAccessModal(true);
                  }}
                  className="rounded-xl bg-orange-500 px-4 py-2 text-xs font-bold text-white shadow-md shadow-orange-500/20 transition hover:bg-orange-600"
                >
                  Login as Safety Officer →
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-8 space-y-8">
              {!modelData?.available ? (
                <div className="rounded-3xl border border-dashed border-slate-200 bg-white p-16 text-center dark:border-white/10 dark:bg-[#0a1915]">
                  <p className="text-base font-bold text-slate-400">
                    {modelData?.message || "Model evaluation data not available"}
                  </p>
                </div>
              ) : (
                <>
                  {/* Metric Summary Cards */}
                  <div className="grid gap-6 md:grid-cols-4">
                    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                      <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Overall Accuracy
                      </p>
                      <p className="mt-3 font-orbitron text-4xl font-black text-orange-500">
                        {typeof modelData.overall_accuracy === "number"
                          ? `${(modelData.overall_accuracy * 100).toFixed(1)}%`
                          : "N/A"}
                      </p>
                      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        Holdout test partition (N={modelData.test_split_size || 62})
                      </p>
                    </div>

                    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                      <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Macro F1-Score
                      </p>
                      <p className="mt-3 font-orbitron text-4xl font-black text-amber-500">
                        {typeof modelData.macro_f1 === "number"
                          ? `${(modelData.macro_f1 * 100).toFixed(1)}%`
                          : "N/A"}
                      </p>
                      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        Unweighted balanced class average
                      </p>
                    </div>

                    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                      <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Weighted F1-Score
                      </p>
                      <p className="mt-3 font-orbitron text-4xl font-black text-emerald-500">
                        {typeof modelData.weighted_f1 === "number"
                          ? `${(modelData.weighted_f1 * 100).toFixed(1)}%`
                          : "N/A"}
                      </p>
                      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                        Support-weighted class metric
                      </p>
                    </div>

                    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                      <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Deployed Architecture
                      </p>
                      <p className="mt-3 text-base font-bold text-slate-900 dark:text-white">
                        {modelData.model_name || "Linear SVM (Platt Calibrated)"}
                      </p>
                      <p className="mt-2 text-xs text-emerald-600 dark:text-emerald-400 font-mono">
                        {modelData.model_version || "v2.0.0-honest-evaluation"}
                      </p>
                    </div>
                  </div>

                  {/* Per-Class Table */}
                  {modelData.per_class_metrics && (
                    <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                        <div>
                          <h2 className="text-lg font-black text-slate-900 dark:text-white">
                            🎯 Per-Class Severity Precision, Recall &amp; Errors
                          </h2>
                          <p className="text-xs text-slate-500">
                            Holdout test evaluation metrics demonstrating multi-class performance on unseen data.
                          </p>
                        </div>
                        <span className="rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 self-start sm:self-auto">
                          Zero Test Leakage Verified
                        </span>
                      </div>

                      <div className="mt-6 overflow-x-auto">
                        <table className="w-full text-left text-xs">
                          <thead>
                            <tr className="border-b border-slate-200 text-slate-400 dark:border-white/10">
                              <th className="pb-3 font-bold">Severity Tier</th>
                              <th className="pb-3 font-bold">Precision</th>
                              <th className="pb-3 font-bold">Recall</th>
                              <th className="pb-3 font-bold">False Positives (FP)</th>
                              <th className="pb-3 font-bold">False Negatives (FN)</th>
                              <th className="pb-3 font-bold">Test Support</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                            {Object.entries(modelData.per_class_metrics).map(([cls, metrics]) => (
                              <tr key={cls} className="hover:bg-slate-50/50 dark:hover:bg-white/[0.02]">
                                <td className="py-3 font-bold">
                                  <span
                                    className={`inline-block w-2.5 h-2.5 rounded-full mr-2 ${
                                      cls === "V"
                                        ? "bg-red-500"
                                        : cls === "IV"
                                        ? "bg-orange-500"
                                        : cls === "III"
                                        ? "bg-amber-500"
                                        : cls === "II"
                                        ? "bg-yellow-500"
                                        : "bg-emerald-500"
                                    }`}
                                  />
                                  {metrics.name}
                                </td>
                                <td className="py-3 font-mono font-bold text-slate-700 dark:text-slate-300">
                                  {typeof metrics.precision === "number" ? `${(metrics.precision * 100).toFixed(1)}%` : "0.0%"}
                                </td>
                                <td className="py-3 font-mono font-bold text-slate-700 dark:text-slate-300">
                                  {typeof metrics.recall === "number" ? `${(metrics.recall * 100).toFixed(1)}%` : "0.0%"}
                                </td>
                                <td className="py-3 font-mono text-slate-500">
                                  {metrics.false_positives}
                                </td>
                                <td className="py-3 font-mono text-slate-500">
                                  {metrics.false_negatives}
                                </td>
                                <td className="py-3 font-mono text-slate-500">
                                  {metrics.support}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}

                  {/* 5x5 Confusion Matrix */}
                  {modelData.confusion_matrix && (
                    <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                      <h2 className="text-lg font-black text-slate-900 dark:text-white">
                        🧮 Multi-Class Confusion Matrix (5 × 5)
                      </h2>
                      <p className="mt-1 text-xs text-slate-500">
                        Rows represent Actual Historical Severity; Columns represent Model Predicted Severity.
                      </p>

                      <div className="mt-6 overflow-x-auto">
                        <table className="w-full text-center text-xs">
                          <thead>
                            <tr className="border-b border-slate-200 text-slate-400 dark:border-white/10">
                              <th className="py-2 text-left font-bold">Actual \ Predicted</th>
                              {modelData.confusion_matrix.labels.map((lbl) => (
                                <th key={lbl} className="py-2 font-bold font-orbitron">
                                  Level {lbl}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 dark:divide-white/5">
                            {modelData.confusion_matrix.matrix.map((row, rIdx) => (
                              <tr key={rIdx}>
                                <td className="py-3 text-left font-bold text-slate-700 dark:text-slate-300 font-orbitron">
                                  Level {modelData.confusion_matrix?.labels[rIdx]}
                                </td>
                                {row.map((val, cIdx) => (
                                  <td
                                    key={cIdx}
                                    className={`py-3 font-bold ${
                                      rIdx === cIdx
                                        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                        : val > 0
                                        ? "bg-orange-500/5 text-orange-600"
                                        : "text-slate-300 dark:text-slate-600"
                                    }`}
                                  >
                                    {val}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          )
        ) : activeTab === "alerts" ? (
          /* ================= TAB 3: SIF RISK ALERTS ================= */
          <div className="mt-8 space-y-8">
            {/* ALERT SUMMARY CARDS */}
            <div className="grid gap-6 md:grid-cols-4">
              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                <p className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  Total Risk Alerts
                </p>
                <p className="mt-3 font-orbitron text-4xl font-black text-orange-500">
                  {alerts.length}
                </p>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  Automated SIF threshold triggers
                </p>
              </div>

              <div className="rounded-3xl border border-red-500/20 bg-red-500/5 p-6 shadow-sm dark:border-red-500/10 dark:bg-red-500/[0.03]">
                <p className="text-xs font-bold uppercase tracking-wider text-red-600 dark:text-red-400">
                  Active (New) Alerts
                </p>
                <p className="mt-3 font-orbitron text-4xl font-black text-red-600 dark:text-red-400">
                  {newAlertsCount}
                </p>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  Pending immediate officer review
                </p>
              </div>

              <div className="rounded-3xl border border-amber-500/20 bg-amber-500/5 p-6 shadow-sm dark:border-amber-500/10 dark:bg-amber-500/[0.03]">
                <p className="text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                  Acknowledged
                </p>
                <p className="mt-3 font-orbitron text-4xl font-black text-amber-600 dark:text-amber-400">
                  {acknowledgedCount}
                </p>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  Response team dispatched / underway
                </p>
              </div>

              <div className="rounded-3xl border border-emerald-500/20 bg-emerald-500/5 p-6 shadow-sm dark:border-emerald-500/10 dark:bg-emerald-500/[0.03]">
                <p className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                  Resolved Alerts
                </p>
                <p className="mt-3 font-orbitron text-4xl font-black text-emerald-600 dark:text-emerald-400">
                  {resolvedCount}
                </p>
                <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                  Mitigations verified &amp; cleared
                </p>
              </div>
            </div>

            {/* ALERT LIST & TRIAGE */}
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 dark:border-white/10 dark:bg-[#0a1915]">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-200 pb-5 dark:border-white/10">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-black text-slate-900 dark:text-white">
                      🚨 Active SIF Risk Alerts Queue
                    </h2>
                    {alertSearchQuery.trim() && (
                      <span className="rounded-full bg-orange-100 text-orange-700 dark:bg-orange-950/40 dark:text-orange-400 px-2.5 py-0.5 text-[10px] font-bold">
                        {filteredAlerts.length} {filteredAlerts.length === 1 ? "match" : "matches"}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Risk-triggered alerts automatically raised for observations scoring HIGH (&ge;50) or CRITICAL (&ge;75).
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                  {/* Instant Search Bar */}
                  <div className="relative min-w-[260px]">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
                      🔍
                    </span>
                    <input
                      type="text"
                      placeholder="Search ID (e.g. ALT-2B6B), keyword, location..."
                      value={alertSearchQuery}
                      onChange={(e) => setAlertSearchQuery(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-9 pr-8 text-xs text-slate-900 placeholder-slate-400 transition focus:border-orange-500 focus:bg-white focus:outline-none dark:border-white/10 dark:bg-white/5 dark:text-white dark:placeholder-slate-500 dark:focus:border-orange-500"
                    />
                    {alertSearchQuery && (
                      <button
                        type="button"
                        onClick={() => setAlertSearchQuery("")}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        title="Clear search"
                      >
                        ✕
                      </button>
                    )}
                  </div>

                  {/* Filter Chips */}
                  <div className="flex rounded-xl border border-slate-200 bg-slate-100 p-1 dark:border-white/10 dark:bg-white/5 shrink-0">
                    {["ALL", "NEW", "ACKNOWLEDGED", "RESOLVED"].map((st) => (
                      <button
                        key={st}
                        type="button"
                        onClick={() => setAlertFilter(st)}
                        className={`rounded-lg px-3 py-1.5 text-[11px] font-bold transition ${
                          alertFilter === st
                            ? "bg-white text-orange-600 shadow-sm dark:bg-[#0a1915] dark:text-orange-400"
                            : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
                        }`}
                      >
                        {st}
                      </button>
                    ))}
                  </div>

                  {/* Manual Refresh Button */}
                  <button
                    type="button"
                    onClick={() => loadData(currentUser)}
                    disabled={isLoading}
                    className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 shadow-sm transition hover:border-orange-500 hover:text-orange-600 disabled:opacity-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 shrink-0"
                    title="Refresh alerts from cloud database"
                  >
                    <span className={`text-xs ${isLoading ? "animate-spin inline-block" : ""}`}>🔄</span>
                    Refresh
                  </button>
                </div>
              </div>

              {filteredAlerts.length === 0 ? (
                <div className="py-16 text-center">
                  <p className="text-3xl">🔍</p>
                  <p className="mt-2 text-sm font-bold text-slate-700 dark:text-slate-300">
                    {alertSearchQuery
                      ? `No alerts found matching "${alertSearchQuery}"`
                      : `No alerts found for filter '${alertFilter}'.`}
                  </p>
                  <p className="mt-1 text-xs text-slate-400">
                    {alertSearchQuery
                      ? "Try searching for another keyword, location, or clear the search filter."
                      : "High or Critical safety reports submitted will automatically register here."}
                  </p>
                  {alertSearchQuery && (
                    <button
                      type="button"
                      onClick={() => setAlertSearchQuery("")}
                      className="mt-4 rounded-xl bg-orange-500 px-4 py-2 text-xs font-bold text-white transition hover:bg-orange-600 shadow-sm"
                    >
                      Clear Search Filter
                    </button>
                  )}
                </div>
              ) : (
                <div className="mt-6 divide-y divide-slate-100 dark:divide-white/5">
                  {filteredAlerts.map((alt) => (
                    <div key={alt.alert_id} className="py-6 first:pt-0 last:pb-0">
                      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                        <div className="space-y-2 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-mono text-xs font-black text-slate-900 dark:text-white">
                              {alt.alert_id}
                            </span>

                            <span
                              className={`rounded-full px-2.5 py-0.5 text-[10px] font-extrabold ${
                                alt.risk_level === "CRITICAL"
                                  ? "bg-red-500/10 text-red-600 dark:text-red-400"
                                  : "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                              }`}
                            >
                              RISK: {alt.risk_level} ({alt.risk_score}/100)
                            </span>

                            <span className="rounded-full bg-slate-200 px-2.5 py-0.5 text-[10px] font-extrabold text-slate-700 dark:bg-white/10 dark:text-slate-300">
                              SEVERITY: LEVEL {alt.severity_level}
                            </span>

                            <span
                              className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                                alt.alert_status === "NEW"
                                  ? "bg-red-500 text-white animate-pulse"
                                  : alt.alert_status === "ACKNOWLEDGED"
                                  ? "bg-amber-500 text-white"
                                  : "bg-emerald-500 text-white"
                              }`}
                            >
                              STATUS: {alt.alert_status}
                            </span>
                          </div>

                          <p className="text-xs text-slate-700 dark:text-slate-300">
                            {alt.observation_excerpt}
                          </p>

                          <div className="flex flex-wrap gap-2 text-[11px] text-slate-500 dark:text-slate-400">
                            <span>📍 Location: <strong>{alt.location}</strong></span>
                            <span>•</span>
                            <span>🏢 Dept: <strong>{alt.department}</strong></span>
                            <span>•</span>
                            <span>⏰ {new Date(alt.timestamp).toLocaleString()}</span>
                          </div>

                          {alt.detected_precursors && alt.detected_precursors.length > 0 && (
                            <div className="flex flex-wrap gap-1.5 pt-1">
                              {alt.detected_precursors.map((prec, pIdx) => (
                                <span
                                  key={pIdx}
                                  className="rounded-md bg-orange-500/10 px-2 py-0.5 text-[10px] font-bold text-orange-600 dark:text-orange-400"
                                >
                                  ⚠️ {prec}
                                </span>
                              ))}
                            </div>
                          )}

                          <div className="mt-2 rounded-2xl bg-orange-50/60 p-3 dark:bg-orange-500/[0.04] border border-orange-500/20 text-xs">
                            <p className="font-bold text-orange-700 dark:text-orange-300">
                              ⚡ Recommended Immediate Control:
                            </p>
                            <p className="mt-0.5 text-slate-700 dark:text-slate-300">
                              {alt.recommended_immediate_action}
                            </p>
                          </div>

                          {alt.reviewer_notes && (
                            <div className="rounded-xl bg-slate-100 p-2.5 dark:bg-white/5 text-[11px] text-slate-600 dark:text-slate-400">
                              💬 Officer Notes: {alt.reviewer_notes} (by {alt.acknowledged_by || alt.resolved_by})
                            </div>
                          )}
                        </div>

                        {/* Officer Actions */}
                        <div className="flex flex-col gap-2 min-w-[220px] shrink-0">
                          <input
                            type="text"
                            placeholder="Add officer resolution notes..."
                            value={officerNotes[alt.alert_id] || ""}
                            onChange={(e) =>
                              setOfficerNotes({
                                ...officerNotes,
                                [alt.alert_id]: e.target.value,
                              })
                            }
                            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs outline-none focus:border-orange-500 dark:border-white/10 dark:bg-white/5"
                          />

                          <div className="flex gap-2">
                            {alt.alert_status === "NEW" && (
                              <button
                                type="button"
                                disabled={isUpdatingAlert === alt.alert_id}
                                onClick={() => handleStatusChange(alt.alert_id, "ACKNOWLEDGED")}
                                className="flex-1 rounded-xl bg-amber-500 px-3 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-amber-600 disabled:opacity-50"
                              >
                                {isUpdatingAlert === alt.alert_id ? "Saving..." : "✓ Acknowledge"}
                              </button>
                            )}

                            {alt.alert_status !== "RESOLVED" && (
                              <button
                                type="button"
                                disabled={isUpdatingAlert === alt.alert_id}
                                onClick={() => handleStatusChange(alt.alert_id, "RESOLVED")}
                                className="flex-1 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50"
                              >
                                {isUpdatingAlert === alt.alert_id ? "Saving..." : "✓ Resolve Alert"}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* ================= TAB 4: CORRECTIVE ACTION TRACKER ================= */
          <div className="mt-8 space-y-8">
            {/* KPI Summary Cards */}
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                <p className="text-xs font-bold text-slate-500 uppercase tracking-wider">Total Actions</p>
                <p className="mt-2 font-orbitron text-4xl font-black text-slate-900 dark:text-white">
                  {actions.length}
                </p>
                <p className="mt-1 text-[11px] text-slate-400">All Tracked Mitigations</p>
              </div>

              <div className="rounded-3xl border border-blue-500/20 bg-blue-50/50 p-6 shadow-sm dark:border-blue-500/20 dark:bg-blue-950/10">
                <p className="text-xs font-bold text-blue-600 dark:text-blue-400 uppercase tracking-wider">Open</p>
                <p className="mt-2 font-orbitron text-4xl font-black text-blue-600 dark:text-blue-400">
                  {actions.filter(a => a.status === "OPEN").length}
                </p>
                <p className="mt-1 text-[11px] text-blue-500/80">Pending Field Assignment</p>
              </div>

              <div className="rounded-3xl border border-amber-500/20 bg-amber-50/50 p-6 shadow-sm dark:border-amber-500/20 dark:bg-amber-950/10">
                <p className="text-xs font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider">In Progress</p>
                <p className="mt-2 font-orbitron text-4xl font-black text-amber-600 dark:text-amber-400">
                  {actions.filter(a => a.status === "IN_PROGRESS").length}
                </p>
                <p className="mt-1 text-[11px] text-amber-500/80">Under Active Execution</p>
              </div>

              <div className="rounded-3xl border border-emerald-500/20 bg-emerald-50/50 p-6 shadow-sm dark:border-emerald-500/20 dark:bg-emerald-950/10">
                <p className="text-xs font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider">Verified</p>
                <p className="mt-2 font-orbitron text-4xl font-black text-emerald-600 dark:text-emerald-400">
                  {actions.filter(a => a.status === "VERIFIED").length}
                </p>
                <p className="mt-1 text-[11px] text-emerald-500/80">Closed &amp; Physically Checked</p>
              </div>

              <div className="rounded-3xl border border-orange-500/20 bg-orange-50/50 p-6 shadow-sm dark:border-orange-500/20 dark:bg-orange-950/10">
                <p className="text-xs font-bold text-orange-600 dark:text-orange-400 uppercase tracking-wider">Resolution Rate</p>
                <p className="mt-2 font-orbitron text-4xl font-black text-orange-600 dark:text-orange-400">
                  {actions.length > 0
                    ? `${Math.round(((actions.filter(a => a.status === "COMPLETED" || a.status === "VERIFIED").length) / actions.length) * 100)}%`
                    : "0%"}
                </p>
                <p className="mt-1 text-[11px] text-orange-500/80">Mitigation Closeout</p>
              </div>
            </div>

            {/* Main Action Queue Container */}
            <div className="rounded-3xl border border-slate-200 bg-white p-8 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-100 pb-5 dark:border-white/10">
                <div>
                  <div className="flex items-center gap-2">
                    <h2 className="text-lg font-black text-slate-900 dark:text-white">
                      Field Corrective Action Queue
                    </h2>
                    {actionSearchQuery.trim() && (
                      <span className="rounded-full bg-orange-100 text-orange-700 dark:bg-orange-950/40 dark:text-orange-400 px-2.5 py-0.5 text-[10px] font-bold">
                        {filteredActions.length} {filteredActions.length === 1 ? "match" : "matches"}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    Track mitigation lifecycles from AI derivation to physical Safety Officer verification.
                  </p>
                </div>

                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                  {/* Instant Search Bar */}
                  <div className="relative min-w-[240px]">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-400">
                      🔍
                    </span>
                    <input
                      type="text"
                      placeholder="Search action ID, title, keyword..."
                      value={actionSearchQuery}
                      onChange={(e) => setActionSearchQuery(e.target.value)}
                      className="w-full rounded-xl border border-slate-200 bg-slate-50 py-2 pl-9 pr-8 text-xs text-slate-900 placeholder-slate-400 transition focus:border-orange-500 focus:bg-white focus:outline-none dark:border-white/10 dark:bg-white/5 dark:text-white dark:placeholder-slate-500 dark:focus:border-orange-500"
                    />
                    {actionSearchQuery && (
                      <button
                        type="button"
                        onClick={() => setActionSearchQuery("")}
                        className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
                        title="Clear search"
                      >
                        ✕
                      </button>
                    )}
                  </div>

                  {/* Status Filter Pills */}
                  <div className="flex flex-wrap gap-1.5 rounded-2xl border border-slate-200 bg-slate-50 p-1.5 dark:border-white/5 dark:bg-white/5 shrink-0">
                    {(["ALL", "OPEN", "IN_PROGRESS", "COMPLETED", "VERIFIED"] as const).map((filter) => (
                      <button
                        key={filter}
                        type="button"
                        onClick={() => setActionFilter(filter)}
                        className={`rounded-xl px-3 py-1.5 text-xs font-bold transition ${
                          actionFilter === filter
                            ? "bg-white text-orange-600 shadow-sm dark:bg-[#0a1915] dark:text-orange-400"
                            : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
                        }`}
                      >
                        {filter === "ALL" ? "All Actions" : filter === "IN_PROGRESS" ? "In Progress" : filter.charAt(0) + filter.slice(1).toLowerCase()}
                      </button>
                    ))}
                  </div>

                  {/* Manual Refresh Button */}
                  <button
                    type="button"
                    onClick={() => loadData(currentUser)}
                    disabled={isLoading}
                    className="flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700 shadow-sm transition hover:border-orange-500 hover:text-orange-600 disabled:opacity-50 dark:border-white/10 dark:bg-white/5 dark:text-slate-200 shrink-0"
                    title="Refresh actions from cloud database"
                  >
                    <span className={`text-xs ${isLoading ? "animate-spin inline-block" : ""}`}>🔄</span>
                    Refresh
                  </button>
                </div>
              </div>

              {filteredActions.length === 0 ? (
                <div className="mt-8 rounded-2xl border border-dashed border-slate-200 p-12 text-center text-xs text-slate-500 dark:border-white/10">
                  <div className="text-3xl">🔍</div>
                  <p className="mt-2 font-bold text-slate-700 dark:text-slate-300">
                    {actionSearchQuery
                      ? `No actions found matching "${actionSearchQuery}"`
                      : `No actions found matching "${actionFilter}".`}
                  </p>
                  <p className="mt-1 text-slate-400">
                    {actionSearchQuery
                      ? "Try searching for another keyword or clear the search filter."
                      : "When safety reports are analyzed or initiated, their corrective tasks will be tracked here."}
                  </p>
                  {actionSearchQuery && (
                    <button
                      type="button"
                      onClick={() => setActionSearchQuery("")}
                      className="mt-4 rounded-xl bg-orange-500 px-4 py-2 text-xs font-bold text-white transition hover:bg-orange-600 shadow-sm"
                    >
                      Clear Search Filter
                    </button>
                  )}
                </div>
              ) : (
                <div className="mt-6 space-y-4">
                  {filteredActions.map((act) => (
                    <div
                      key={act.action_id}
                      className="rounded-2xl border border-slate-200 bg-slate-50/50 p-6 transition hover:shadow-md dark:border-white/5 dark:bg-white/[0.02]"
                    >
                      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        <div className="space-y-3 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-mono text-xs font-bold text-slate-500 dark:text-slate-400">
                              {act.action_id}
                            </span>
                            <span className="font-mono text-xs text-slate-400">
                              • Ref: {act.report_id}
                            </span>
                            <span
                              className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold ${
                                act.priority === "IMMEDIATE"
                                  ? "bg-red-500/10 text-red-600 border border-red-500/20"
                                  : act.priority === "HIGH"
                                  ? "bg-orange-500/10 text-orange-600 border border-orange-500/20"
                                  : "bg-blue-500/10 text-blue-600 border border-blue-500/20"
                              }`}
                            >
                              {act.priority} PRIORITY
                            </span>
                            <span
                              className={`rounded-full px-3 py-0.5 text-[10px] font-black uppercase ${
                                act.status === "VERIFIED"
                                  ? "bg-emerald-500/15 text-emerald-600 border border-emerald-500/30 dark:text-emerald-400"
                                  : act.status === "COMPLETED"
                                  ? "bg-indigo-500/15 text-indigo-600 border border-indigo-500/30 dark:text-indigo-400"
                                  : act.status === "IN_PROGRESS"
                                  ? "bg-amber-500/15 text-amber-600 border border-amber-500/30 dark:text-amber-400"
                                  : "bg-slate-200 text-slate-700 dark:bg-white/10 dark:text-slate-300"
                              }`}
                            >
                              {act.status === "VERIFIED" ? "✓ VERIFIED" : act.status}
                            </span>
                            <span className="text-[11px] font-semibold text-orange-600 dark:text-orange-400">
                              Assigned: {act.responsible_role}
                            </span>
                          </div>

                          <p className="text-sm font-bold text-slate-900 dark:text-white leading-relaxed">
                            {act.action_description}
                          </p>

                          {act.ai_generated_context?.verification_step && (
                            <div className="rounded-xl bg-orange-50/60 p-3 dark:bg-orange-500/[0.04] border border-orange-500/20 text-xs">
                              <p className="font-bold text-orange-700 dark:text-orange-300">
                                🔍 Verification Protocol:
                              </p>
                              <p className="mt-0.5 text-slate-700 dark:text-slate-300">
                                {act.ai_generated_context.verification_step}
                              </p>
                            </div>
                          )}

                          <div className="flex flex-wrap gap-4 text-[11px] text-slate-400">
                            <span>📅 Created: {act.created_at ? new Date(act.created_at).toLocaleDateString() : "Recent"}</span>
                            {act.completed_at && <span>🏁 Completed: {new Date(act.completed_at).toLocaleDateString()}</span>}
                            {act.verified_at && <span className="text-emerald-600 dark:text-emerald-400">✓ Verified: {new Date(act.verified_at).toLocaleDateString()} ({act.verified_by_officer})</span>}
                          </div>

                          {act.tracking_notes && (
                            <div className="rounded-xl bg-slate-100 p-2.5 dark:bg-white/5 text-[11px] text-slate-600 dark:text-slate-400">
                              💬 Officer Notes: {act.tracking_notes}
                            </div>
                          )}
                        </div>

                        {/* Officer Workflow Update Actions */}
                        <div className="flex flex-col gap-2 min-w-[220px] shrink-0">
                          <input
                            type="text"
                            placeholder="Add verification notes..."
                            value={actionOfficerNotes[act.action_id] || ""}
                            onChange={(e) =>
                              setActionOfficerNotes({
                                ...actionOfficerNotes,
                                [act.action_id]: e.target.value,
                              })
                            }
                            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs outline-none focus:border-orange-500 dark:border-white/10 dark:bg-white/5"
                          />

                          <div className="flex flex-col gap-1.5">
                            <div className="flex gap-2">
                              {act.status === "OPEN" && (
                                <button
                                  type="button"
                                  disabled={isUpdatingAction === act.action_id}
                                  onClick={() => handleActionStatusChange(act.action_id, "IN_PROGRESS")}
                                  className="flex-1 rounded-xl bg-amber-500 px-3 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-amber-600 disabled:opacity-50"
                                >
                                  {isUpdatingAction === act.action_id ? "Saving..." : "Start Action"}
                                </button>
                              )}

                              {act.status === "IN_PROGRESS" && (
                                <button
                                  type="button"
                                  disabled={isUpdatingAction === act.action_id}
                                  onClick={() => handleActionStatusChange(act.action_id, "COMPLETED")}
                                  className="flex-1 rounded-xl bg-indigo-600 px-3 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
                                >
                                  {isUpdatingAction === act.action_id ? "Saving..." : "Mark Completed"}
                                </button>
                              )}
                            </div>

                            {act.status !== "VERIFIED" && (
                              <button
                                type="button"
                                disabled={isUpdatingAction === act.action_id}
                                onClick={() => handleActionStatusChange(act.action_id, "VERIFIED")}
                                className="w-full rounded-xl bg-emerald-600 px-3 py-2 text-xs font-bold text-white shadow-sm transition hover:bg-emerald-700 disabled:opacity-50"
                              >
                                {isUpdatingAction === act.action_id ? "Saving..." : "✓ Authorize & Verify"}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </section>

      {/* SAFETY OFFICER ACCESS REQUIRED MODAL */}
      {showAccessModal && (
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
                onClick={() => setShowAccessModal(false)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-xs font-semibold text-slate-600 transition hover:bg-slate-100 dark:border-white/10 dark:text-slate-400 dark:hover:bg-white/5"
              >
                Close
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowAccessModal(false);
                  router.push("/login?redirect=/analytics-dashboard?view=model-validation");
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

export default function AnalyticsDashboardPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-slate-50 text-slate-900 transition-colors duration-300 dark:bg-[#050d0a] dark:text-slate-100">
          <div className="mx-auto max-w-7xl px-6 py-20 text-center">
            <div className="animate-spin text-4xl">⏳</div>
            <p className="mt-4 text-sm font-bold text-slate-500 dark:text-slate-400">
              Loading Safety Analytics...
            </p>
          </div>
        </main>
      }
    >
      <AnalyticsDashboardContent />
    </Suspense>
  );
}
