export interface SafetyReport {
  report_text: string;
  industry_sector?: string;
  worker_type?: string;
  gender?: string;
  location?: string;
  report_type?: string;
  image_base64?: string;
  image_filename?: string;
}

export interface ImageEvidenceInfo {
  image_attached: boolean;
  image_id?: string;
  report_id?: string;
  original_filename?: string;
  stored_filename?: string;
  content_type?: string;
  format?: string;
  file_size_bytes?: number;
  width?: number;
  height?: number;
  url_reference?: string;
  attached_at?: string;
  cv_analysis_status?: string;
  status_note?: string;
  error_message?: string;
}

export interface Incident {
  incident_id?: number;
  source_id?: string;
  reference_id?: string;
  similarity?: number;
  similarity_score?: number;
  similarity_percentage?: number;
  description?: string;
  historical_description?: string;
  potential_accident_level?: string;
  potential_incident_level?: string;
  critical_risk?: string;
  industry_sector?: string;
  worker_type?: string;
  retrieval_method?: string;
}

export interface SafetyPrecursor {
  factor?: string;
  label?: string;
  contribution?: number;
  evidence?: string | string[];
}

export interface CorrectiveAction {
  action: string;
  priority: string;
  reason: string;
  related_precursor: string;
  precursor_id?: string;
  immediate_control?: string;
  verification_step?: string;
  responsible_safety_role?: string;
  responsible_role?: string;
  escalation_condition?: string;
  follow_up_action?: string;
  requires_human_approval?: boolean;
  action_id?: string;
  report_id?: string;
  status?: "OPEN" | "IN_PROGRESS" | "COMPLETED" | "VERIFIED" | string;
  verification_status?: "UNVERIFIED" | "PENDING_VERIFICATION" | "VERIFIED" | string;
  created_at?: string;
  completed_at?: string;
  due_date?: string;
  verified_by_officer?: string;
  officer_id?: string;
  tracking_notes?: string;
}

export interface AnalysisResponse {
  success: boolean;
  analysis_source?: "backend_ai" | "demo_fallback";
  fallback_warning?: string;
  error?: {
    code: string;
    message: string;
    status_code?: number;
  } | string;
  analysis: {
    overall_risk: {
      score: number;
      level: string;
      summary: string;
      formula_explanation?: string;
      base_precursor_score?: number;
      compound_risk_boost?: number;
      components?: Array<{
        factor: string;
        label: string;
        contribution: number;
      }>;
    };
    severity_prediction: {
      potential_accident_level: string;
      severity_label?: string;
      model?: string;
      model_version?: string;
      confidence?: number;
      class_probabilities?: Record<string, number>;
      calibration_note?: string;
      label_mapping?: Record<string, string>;
    };
    detected_precursors: SafetyPrecursor[];
    ai_explanation: string;
    corrective_actions?: CorrectiveAction[];
    recommended_actions: string[];
    historical_evidence: {
      similar_cases_found: number;
      incidents: Incident[];
    };
    alert?: SafetyAlertRecord;
    alert_triggered?: boolean;
    image_evidence?: ImageEvidenceInfo;
  };
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function checkBackendHealth(timeoutMs = 3000): Promise<boolean> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_URL}/`, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    return response.ok;
  } catch {
    clearTimeout(timeoutId);
    return false;
  }
}

export function simulateFallbackAnalysis(reportText: string): AnalysisResponse {
  const trimmed = (reportText || "").trim();
  if (!trimmed) {
    return {
      success: true,
      analysis_source: "demo_fallback",
      fallback_warning: "Empty observation description provided. Displaying baseline heuristic assessment.",
      analysis: {
        overall_risk: {
          score: 0,
          level: "LOW",
          summary: "No safety observation text provided for heuristic screening.",
        },
        severity_prediction: {
          potential_accident_level: "I",
          severity_label: "Level I",
          model: "Local Heuristic Rule Engine (Fallback)",
        },
        detected_precursors: [],
        ai_explanation: "No narrative text provided to screen for SIF precursors.",
        recommended_actions: [
          "Record complete observation details in field safety log."
        ],
        historical_evidence: {
          similar_cases_found: 0,
          incidents: [],
        },
      },
    };
  }

  const text = trimmed.toLowerCase();
  const precursors: SafetyPrecursor[] = [];
  let score = 0;
  const actions: string[] = [];

  if (text.includes("pressure") || text.includes("pressurized") || text.includes("pipe") || text.includes("flange")) {
    precursors.push({ factor: "high_pressure", label: "High Pressure Exposure", contribution: 25, evidence: "Pressure line / flange reference" });
    score += 25;
    actions.push("Inspect and depressurize line valve V-104 before maintenance.");
  }
  if (text.includes("gas") || text.includes("leak") || text.includes("flammable") || text.includes("h2s") || text.includes("methane") || text.includes("spill")) {
    precursors.push({ factor: "leakage", label: "Flammable Gas / Fluid Leakage", contribution: 20, evidence: "Hydrocarbon gas / fluid detection" });
    score += 20;
    actions.push("Isolate combustible fuel lines and deploy gas detection perimeter.");
  }
  if (text.includes("ppe") || text.includes("helmet") || text.includes("harness") || text.includes("hearing") || text.includes("without") || text.includes("not wearing")) {
    precursors.push({ factor: "ppe", label: "PPE Non-Compliance", contribution: 15, evidence: "Missing mandatory safety gear" });
    score += 15;
    actions.push("Mandate immediate PPE compliance and conduct tool-box re-briefing.");
  }
  if (text.includes("height") || text.includes("scaffold") || text.includes("ladder") || text.includes("fall") || text.includes("drop")) {
    precursors.push({ factor: "fall_hazard", label: "Working at Height / Dropped Object", contribution: 20, evidence: "Elevated structure hazard" });
    score += 20;
    actions.push("Halt height operations and recertify fall-arrest lifeline anchoring.");
  }
  if (text.includes("electric") || text.includes("cable") || text.includes("wire") || text.includes("440v") || text.includes("voltage") || text.includes("spark")) {
    precursors.push({ factor: "electrical", label: "Electrical / Ignition Hazard", contribution: 20, evidence: "Live wiring / electrical equipment" });
    score += 20;
    actions.push("Immediate LOTO (Lockout/Tagout) isolation at MCC panel.");
  }

  score = Math.min(score, 100);
  if (score === 0) score = 15; // baseline

  let level = "LOW";
  let potAccLevel = "I";
  if (score >= 70) {
    level = "CRITICAL";
    potAccLevel = "IV";
  } else if (score >= 45) {
    level = "HIGH";
    potAccLevel = "III";
  } else if (score >= 25) {
    level = "MEDIUM";
    potAccLevel = "II";
  }

  if (actions.length === 0) {
    actions.push("Conduct standard routine field inspection and log observation in HSSE ledger.");
  }

  return {
    success: true,
    analysis_source: "demo_fallback",
    fallback_warning: "Backend service unreachable. Displaying local heuristic fallback analysis.",
    analysis: {
      overall_risk: {
        score,
        level,
        summary: `Automated SIF analysis flagged ${precursors.length} precursor(s) with an evaluated risk score of ${score}/100.`,
      },
      severity_prediction: {
        potential_accident_level: potAccLevel,
        severity_label: `Level ${potAccLevel}`,
        model: "Local Heuristic Rule Engine (Fallback)",
      },
      detected_precursors: precursors,
      ai_explanation: precursors.length > 0
        ? `Identified key SIF hazards: ${precursors.map((p) => p.label).join(", ")}. Immediate precautionary controls recommended.`
        : "Standard observation narrative. No immediate catastrophic precursor signals detected.",
      recommended_actions: actions,
      historical_evidence: {
        similar_cases_found: 2,
        incidents: [
          {
            incident_id: 101,
            similarity: 0.88,
            critical_risk: "Pressurized Systems",
            potential_accident_level: "III",
            description: "High pressure line release during routine compressor valve maintenance.",
          },
          {
            incident_id: 264,
            similarity: 0.74,
            critical_risk: "Flammable Atmosphere",
            potential_accident_level: "II",
            description: "Gas detector alarmed during flaring startup at separator station.",
          },
        ],
      },
    },
  };
}

export const SAFETY_ANALYSIS_STORAGE_KEY = "safetyAnalysis";

/**
 * Stores the verified Safety AI analysis response into browser sessionStorage.
 * Returns true only if write was successful and verified.
 */
export function saveAnalysisResult(result: AnalysisResponse): boolean {
  if (typeof window === "undefined") return false;
  if (!result || !result.success || !result.analysis) {
    console.error("[SafetyAI] Cannot store invalid or unsuccessful analysis result:", result);
    return false;
  }
  try {
    const serialized = JSON.stringify(result);
    sessionStorage.setItem(SAFETY_ANALYSIS_STORAGE_KEY, serialized);
    const verified = sessionStorage.getItem(SAFETY_ANALYSIS_STORAGE_KEY);
    if (verified === serialized) {
      console.log("[SafetyAI] Stored analysis in sessionStorage successfully. Source:", result.analysis_source || "backend_ai");
      return true;
    }
    console.error("[SafetyAI] sessionStorage verification failed (content mismatch).");
    return false;
  } catch (err) {
    console.error("[SafetyAI] Failed to write analysis to sessionStorage:", err);
    return false;
  }
}

/**
 * Reads and validates the stored Safety AI analysis from browser sessionStorage.
 * Returns null if no valid result is stored.
 */
export function loadAnalysisResult(): AnalysisResponse | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(SAFETY_ANALYSIS_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AnalysisResponse;
    if (parsed && parsed.success === true && parsed.analysis && parsed.analysis.overall_risk) {
      return parsed;
    }
    console.warn("[SafetyAI] Stored analysis payload failed schema validation:", parsed);
    return null;
  } catch (err) {
    console.error("[SafetyAI] Error parsing analysis result from sessionStorage:", err);
    return null;
  }
}

/**
 * Clears stored Safety AI analysis from browser sessionStorage.
 */
export function clearAnalysisResult(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(SAFETY_ANALYSIS_STORAGE_KEY);
  } catch (err) {
    console.error("[SafetyAI] Error clearing analysis from sessionStorage:", err);
  }
}

export async function analyzeSafetyReport(
  report: SafetyReport,
  timeoutMs = 20000
): Promise<AnalysisResponse> {
  const cleanText = (report.report_text || "").trim();
  if (!cleanText) {
    throw new Error("Safety report observation description cannot be empty or only whitespace.");
  }

  const endpointUrl = `${API_URL}/analyze`;
  const requestPayload = {
    report_text: cleanText,
    industry_sector: report.industry_sector || "Mining",
    worker_type: report.worker_type || "Employee",
    gender: report.gender || "Male",
    location: report.location || "",
    image_base64: report.image_base64,
    image_filename: report.image_filename,
  };

  console.log(`[SafetyAI:Request] URL: ${endpointUrl}`);
  console.log(`[SafetyAI:Request] Start: Initiating safety analysis (timeout: ${timeoutMs}ms)`);
  console.log(`[SafetyAI:Request] Payload:`, {
    ...requestPayload,
    image_base64: requestPayload.image_base64 ? `[Base64 encoded: ${requestPayload.image_base64.length} chars]` : undefined,
  });

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(endpointUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestPayload),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    console.log(`[SafetyAI:Response] Status: ${response.status} ${response.statusText}`);

    if (!response.ok) {
      let errorDetail = `Backend returned HTTP status ${response.status}`;
      try {
        const errJson = await response.json();
        console.warn(`[SafetyAI:Response] Error JSON:`, errJson);
        errorDetail = errJson.error?.message || errJson.detail || errorDetail;
      } catch {
        // ignore json parse error
      }
      console.warn("[SafetyAI] Backend error response:", response.status, errorDetail);

      // If client validation error (400, 422), propagate error directly
      if (response.status === 400 || response.status === 422) {
        throw new Error(errorDetail);
      }

      // If server error (500), throw error
      throw new Error(`Server error (${response.status}): ${errorDetail}`);
    }

    const data: AnalysisResponse = await response.json();
    console.log("[SafetyAI:Response] JSON:", data);

    // Validate backend response contract
    if (!data || data.success !== true || !data.analysis) {
      throw new Error("Invalid backend response: expected 'success: true' and 'analysis' object.");
    }

    data.analysis_source = data.analysis_source || "backend_ai";
    console.log("[SafetyAI] Analysis validated successfully:", data.analysis_source);
    return data;
  } catch (error: any) {
    clearTimeout(timeoutId);

    // If it's a direct user validation error, rethrow so the UI can inform the user
    if (error?.message && error.message.includes("cannot be empty")) {
      throw error;
    }

    const isTimeout = error?.name === "AbortError";
    const reason = isTimeout
      ? `API request timed out (server took > ${Math.round(timeoutMs / 1000)} seconds). Using offline heuristic fallback.`
      : (error?.message || "Backend server unreachable. Using offline heuristic fallback.");

    if (isTimeout) {
      console.error(`[SafetyAI:Timeout] Request timed out after ${timeoutMs}ms.`);
    } else {
      console.error(`[SafetyAI:NetworkFailure] Request failed:`, error?.message || error);
    }

    const fallback = simulateFallbackAnalysis(cleanText);
    fallback.fallback_warning = reason;
    return fallback;
  }
}

export interface SafetyOfficerReviewSubmission {
  officer_name: string;
  officer_id: string;
  review_status: "ACCEPTED" | "REJECTED" | "MODIFIED";
  reviewer_comment?: string;
  ai_prediction: Record<string, any>;
  human_decision?: {
    severity?: string;
    risk_score?: number;
    risk_level?: string;
    precursors?: string[];
    actions?: string[];
  };
  report_id?: string;
  role?: string;
}

export interface SafetyReviewRecord {
  review_id: string;
  report_id: string;
  timestamp: string;
  ai_severity?: string;
  ai_risk_score?: number;
  detected_precursors?: string[];
  recommended_actions?: string[];
  officer_name: string;
  officer_id: string;
  officer_decision?: string;
  officer_modified_severity?: string | null;
  officer_comments?: string;
  review_status: string;
  reviewer_comment: string;
  ai_prediction: Record<string, any>;
  human_decision: Record<string, any>;
  final_decision: {
    potential_accident_level: string;
    overall_risk_score: number;
    overall_risk_level: string;
    confirmed_precursors: string[];
    authorized_corrective_actions: string[];
    review_status: string;
    verified_by_officer: string;
    officer_id: string;
    verification_timestamp: string;
  };
}

export async function submitSafetyReviewRecord(
  submission: SafetyOfficerReviewSubmission,
  timeoutMs = 8000
): Promise<{ success: boolean; record?: SafetyReviewRecord; error?: string }> {
  // Enforce role check: employees cannot submit reviews
  if (submission.role === "employee") {
    return {
      success: false,
      error: "Only authorized Safety Officers can submit or modify safety reviews.",
    };
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_URL}/review/submit`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...submission,
        role: submission.role,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorMsg = `Review submission failed with status ${response.status}`;
      try {
        const errJson = await response.json();
        errorMsg = errJson.error?.message || errJson.detail || errorMsg;
      } catch {
        // ignore json parse error
      }
      throw new Error(errorMsg);
    }

    const data = await response.json();
    return { success: true, record: data.record };
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (submission.role === "employee") {
      return {
        success: false,
        error: "Only authorized Safety Officers can submit or modify safety reviews.",
      };
    }
    console.warn("Local review storage fallback:", err?.message || err);
    // Local fallback for offline mode
    const nowIso = new Date().toISOString();
    const fallbackRecord: SafetyReviewRecord = {
      review_id: `REV-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
      report_id: submission.report_id || `RPT-${Math.random().toString(36).substring(2, 6).toUpperCase()}`,
      officer_name: submission.officer_name,
      officer_id: submission.officer_id,
      review_status: submission.review_status,
      reviewer_comment: submission.reviewer_comment || "Verified by on-duty safety officer.",
      timestamp: nowIso,
      ai_prediction: submission.ai_prediction,
      human_decision: submission.human_decision || {},
      final_decision: {
        potential_accident_level: submission.human_decision?.severity || submission.ai_prediction?.severity_prediction?.potential_accident_level || "I",
        overall_risk_score: submission.human_decision?.risk_score ?? submission.ai_prediction?.overall_risk?.score ?? 0,
        overall_risk_level: submission.human_decision?.risk_level || submission.ai_prediction?.overall_risk?.level || "LOW",
        confirmed_precursors: submission.human_decision?.precursors || (submission.ai_prediction?.detected_precursors || []).map((p: any) => p.label || p.factor),
        authorized_corrective_actions: submission.human_decision?.actions || submission.ai_prediction?.recommended_actions || [],
        review_status: submission.review_status,
        verified_by_officer: submission.officer_name,
        officer_id: submission.officer_id,
        verification_timestamp: nowIso,
      },
    };
    return { success: true, record: fallbackRecord };
  }
}

export interface LocationAnalyticsItem {
  location: string;
  total_reports: number;
  high_risk_reports: number;
  critical_risk_reports: number;
  high_risk_percentage: number;
  critical_risk_percentage: number;
  average_risk_score: number;
  severity_distribution: Record<string, number>;
  top_recurring_precursors: Array<{ precursor: string; count: number }>;
}

export interface DepartmentAnalyticsItem {
  department: string;
  industry_sector: string;
  total_reports: number;
  high_risk_reports: number;
  critical_risk_reports: number;
  high_risk_percentage: number;
  critical_risk_percentage: number;
  average_risk_score: number;
  severity_distribution: Record<string, number>;
  top_recurring_precursors: Array<{ precursor: string; count: number }>;
}

export interface TimeTrendItem {
  period: string;
  total_reports: number;
  high_risk_count: number;
  critical_risk_count: number;
  average_risk_score: number;
  top_precursor: string;
}

export interface OperationalAnalyticsData {
  available: boolean;
  message?: string;
  total_reports_analyzed?: number;
  unique_usable_records?: number;
  severity_distribution?: Record<string, number>;
  precursor_detection_distribution?: Record<string, number>;
  risk_level_distribution?: Record<string, number>;
  industry_sector_distribution?: Record<string, number>;
  retrieval_corpus_size?: number;
  taxonomy_precursor_categories?: number;
  location_analytics?: LocationAnalyticsItem[];
  department_analytics?: DepartmentAnalyticsItem[];
  time_trend_analytics?: TimeTrendItem[];
}

export interface ClassEvaluationMetric {
  class_label: string;
  name: string;
  true_positives: number;
  false_positives: number;
  false_negatives: number;
  true_negatives: number;
  recall: number;
  precision: number;
  f1_score?: number;
  support: number;
  is_safety_critical: boolean;
}

export interface ModelPerformanceAnalyticsData {
  available: boolean;
  message?: string;
  model_name?: string;
  model_version?: string;
  test_split_size?: number;
  overall_accuracy?: number;
  macro_precision?: number;
  macro_recall?: number;
  macro_f1?: number;
  weighted_f1?: number;
  per_class_metrics?: Record<string, ClassEvaluationMetric>;
  confusion_matrix?: {
    labels: string[];
    matrix: number[][];
  };
  benchmark_comparison?: Record<string, any>;
  evaluation_note?: string;
}

export interface OperationalAnalyticsResponse {
  success: boolean;
  data?: OperationalAnalyticsData;
  error?: string;
}

export interface ModelPerformanceAnalyticsResponse {
  success: boolean;
  data?: ModelPerformanceAnalyticsData;
  error?: string;
}

export async function fetchOperationalAnalytics(timeoutMs = 6000): Promise<OperationalAnalyticsData> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_URL}/analytics/operational`, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const response = await res.json();
    console.log("[Analytics] Operational API response:", response);

    // 1. Standard backend response: { success: true, data: { available: true, ... } }
    if (response && response.success === true && response.data && response.data.available === true) {
      return {
        available: true,
        message: response.data.message,
        total_reports_analyzed: response.data.total_reports_analyzed,
        unique_usable_records: response.data.unique_usable_records,
        severity_distribution: response.data.severity_distribution,
        precursor_detection_distribution: response.data.precursor_detection_distribution,
        risk_level_distribution: response.data.risk_level_distribution,
        industry_sector_distribution: response.data.industry_sector_distribution,
        retrieval_corpus_size: response.data.retrieval_corpus_size,
        taxonomy_precursor_categories: response.data.taxonomy_precursor_categories,
        location_analytics: response.data.location_analytics,
        department_analytics: response.data.department_analytics,
        time_trend_analytics: response.data.time_trend_analytics,
      };
    }

    // 2. Direct data object wrapper
    if (response && response.data && typeof response.data === "object") {
      return {
        available: response.data.available !== false,
        message: response.data.message || (response.data.available === false ? "Operational dataset not available" : undefined),
        ...response.data,
      };
    }

    // 3. Direct unnested response object
    if (response && typeof response === "object" && ("total_reports_analyzed" in response || "available" in response)) {
      return {
        available: response.available !== false,
        message: response.message,
        ...response,
      } as OperationalAnalyticsData;
    }

    return {
      available: false,
      message: response?.message || "Operational data not available",
    };
  } catch (e: any) {
    clearTimeout(timeoutId);
    console.warn("Could not fetch operational analytics:", e?.message || e);
    return { available: false, message: "Backend offline or operational dataset not available." };
  }
}

export async function fetchModelPerformanceAnalytics(timeoutMs = 6000): Promise<ModelPerformanceAnalyticsData> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_URL}/analytics/model-performance`, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const response = await res.json();
    console.log("[Analytics] Model Performance API response:", response);

    // 1. Standard backend response: { success: true, data: { available: true, ... } }
    if (response && response.success === true && response.data && response.data.available === true) {
      return {
        available: true,
        message: response.data.message,
        model_name: response.data.model_name,
        model_version: response.data.model_version,
        test_split_size: response.data.test_split_size,
        overall_accuracy: response.data.overall_accuracy,
        macro_precision: response.data.macro_precision,
        macro_recall: response.data.macro_recall,
        macro_f1: response.data.macro_f1,
        weighted_f1: response.data.weighted_f1,
        per_class_metrics: response.data.per_class_metrics,
        confusion_matrix: response.data.confusion_matrix,
        benchmark_comparison: response.data.benchmark_comparison,
        evaluation_note: response.data.evaluation_note,
      };
    }

    // 2. Direct data object wrapper
    if (response && response.data && typeof response.data === "object") {
      return {
        available: response.data.available !== false,
        message: response.data.message,
        ...response.data,
      };
    }

    // 3. Direct unnested response object
    if (response && typeof response === "object" && ("overall_accuracy" in response || "available" in response)) {
      return {
        available: response.available !== false,
        message: response.message,
        ...response,
      } as ModelPerformanceAnalyticsData;
    }

    return {
      available: false,
      message: response?.message || "Model performance data not available",
    };
  } catch (e: any) {
    clearTimeout(timeoutId);
    console.warn("Could not fetch model performance analytics:", e?.message || e);
    return { available: false, message: "Backend offline or model evaluation data not available." };
  }
}

export interface BatchAnalysisItem {
  row_index: number;
  status: "SUCCESS" | "FAILED";
  report_text?: string;
  location?: string;
  department?: string;
  report_type?: string;
  error?: string;
  raw_data?: Record<string, string>;
  analysis?: AnalysisResponse["analysis"];
}

export interface BatchAnalysisSummary {
  total_reports: number;
  successfully_analyzed: number;
  failed_rows: number;
  critical_risk_count: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  severity_distribution: Record<string, number>;
}

export interface BatchAnalysisResponse {
  success: boolean;
  filename: string;
  summary: BatchAnalysisSummary;
  results: BatchAnalysisItem[];
}

export async function analyzeSafetyReportBatch(
  file: File,
  timeoutMs = 45000
): Promise<BatchAnalysisResponse> {
  if (!file) {
    throw new Error("No file provided for batch analysis.");
  }

  if (file.size === 0) {
    throw new Error("Uploaded batch file is empty (0 bytes).");
  }

  if (file.size > 25 * 1024 * 1024) {
    throw new Error("Uploaded file exceeds 25 MB maximum batch size limit. Please split the file.");
  }

  const validExtensions = [".csv", ".xlsx", ".xls", ".parquet", ".json"];
  const fileName = file.name.toLowerCase();
  const hasValidExt = validExtensions.some(ext => fileName.endsWith(ext));
  if (!hasValidExt) {
    throw new Error(`Unsupported file format. Please upload a CSV (.csv), Excel (.xlsx, .xls), or JSON (.json) file.`);
  }

  const formData = new FormData();
  formData.append("file", file);

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${API_URL}/analyze/batch`, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      let errorDetail = `Batch processing failed (HTTP ${response.status})`;
      try {
        const errorJson = await response.json();
        errorDetail = errorJson.error?.message || errorJson.detail || errorDetail;
      } catch {
        // ignore parse error
      }
      throw new Error(errorDetail);
    }

    return await response.json();
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err?.name === "AbortError") {
      throw new Error("Batch processing timed out (file took > 45 seconds to process).");
    }
    throw err;
  }
}

export interface SafetyAlertRecord {
  alert_id: string;
  report_id: string;
  timestamp: string;
  risk_level: "HIGH" | "CRITICAL" | string;
  risk_score: number;
  detected_precursors: string[];
  severity_level: string;
  recommended_immediate_action: string;
  alert_status: "NEW" | "ACKNOWLEDGED" | "RESOLVED" | string;
  location: string;
  department: string;
  observation_excerpt: string;
  acknowledged_by?: string;
  resolved_by?: string;
  reviewer_notes?: string;
  updated_at?: string;
}

export async function fetchSafetyAlerts(status?: string, timeoutMs = 6000): Promise<SafetyAlertRecord[]> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const url = status && status !== "ALL"
      ? `${API_URL}/alerts?status=${encodeURIComponent(status)}`
      : `${API_URL}/alerts`;
    const res = await fetch(url, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    return json.alerts || [];
  } catch (e: any) {
    clearTimeout(timeoutId);
    console.warn("Could not fetch safety alerts:", e?.message || e);
    return [];
  }
}

export async function fetchSafetyAlert(alertId: string, timeoutMs = 5000): Promise<SafetyAlertRecord | null> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_URL}/alerts/${encodeURIComponent(alertId)}`, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) return null;
    const json = await res.json();
    return json.alert || null;
  } catch (e: any) {
    clearTimeout(timeoutId);
    console.warn(`Could not fetch alert ${alertId}:`, e?.message || e);
    return null;
  }
}

export async function updateSafetyAlertStatus(
  alertId: string,
  status: "ACKNOWLEDGED" | "RESOLVED",
  notes?: string,
  officerName: string = "R. Sharma",
  officerId: string = "HSE-8492",
  timeoutMs = 6000,
  role?: string
): Promise<{ success: boolean; alert?: SafetyAlertRecord; message?: string }> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_URL}/alerts/${encodeURIComponent(alertId)}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status,
        reviewer_notes: notes || "",
        officer_name: officerName,
        officer_id: officerId,
        role: role,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to update alert status" }));
      throw new Error(err.error?.message || err.detail || `Server returned ${res.status}`);
    }

    return await res.json();
  } catch (e: any) {
    clearTimeout(timeoutId);
    console.error(`Failed to update alert ${alertId}:`, e?.message || e);
    return { success: false, message: e.message || "Network error" };
  }
}

// ==========================================
// CORRECTIVE ACTION TRACKING (TASK 10)
// ==========================================

export interface ActionTrackingRecord {
  action_id: string;
  report_id: string;
  action_description: string;
  priority: "IMMEDIATE" | "HIGH" | "MEDIUM" | "ROUTINE" | string;
  responsible_role: string;
  status: "OPEN" | "IN_PROGRESS" | "COMPLETED" | "VERIFIED" | string;
  created_at: string;
  due_date?: string;
  completed_at?: string;
  verification_status: "UNVERIFIED" | "PENDING_VERIFICATION" | "VERIFIED" | string;
  verified_at?: string;
  verified_by_officer?: string;
  officer_id?: string;
  tracking_notes?: string;
  ai_generated_context?: {
    precursor_id?: string;
    related_precursor?: string;
    immediate_control?: string;
    verification_step?: string;
    escalation_condition?: string;
    follow_up_action?: string;
    reason?: string;
  };
  updated_at?: string;
}

export interface ActionTrackingStatistics {
  total_actions: number;
  status_distribution: Record<string, number>;
  priority_distribution: Record<string, number>;
  open_count: number;
  in_progress_count: number;
  completed_count: number;
  verified_count: number;
  resolution_rate: number;
}

export async function fetchTrackedActions(params?: {
  report_id?: string;
  status?: string;
  priority?: string;
}, timeoutMs = 6000): Promise<ActionTrackingRecord[]> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const query = new URLSearchParams();
    if (params?.report_id) query.append("report_id", params.report_id);
    if (params?.status && params.status !== "ALL") query.append("status", params.status);
    if (params?.priority && params.priority !== "ALL") query.append("priority", params.priority);

    const queryString = query.toString();
    const url = queryString ? `${API_URL}/actions?${queryString}` : `${API_URL}/actions`;

    const res = await fetch(url, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    return json.actions || [];
  } catch (e: any) {
    clearTimeout(timeoutId);
    console.warn("Could not fetch tracked actions:", e?.message || e);
    return [];
  }
}

export async function fetchActionStatistics(timeoutMs = 6000): Promise<ActionTrackingStatistics | null> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_URL}/actions/stats`, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) return null;
    const json = await res.json();
    return json.statistics || null;
  } catch (e: any) {
    clearTimeout(timeoutId);
    console.warn("Could not fetch action statistics:", e?.message || e);
    return null;
  }
}

export async function updateTrackedActionStatus(
  actionId: string,
  status: "OPEN" | "IN_PROGRESS" | "COMPLETED" | "VERIFIED" | string,
  notes?: string,
  officerName: string = "R. Sharma",
  officerId: string = "HSE-8492",
  timeoutMs = 6000,
  role?: string
): Promise<{ success: boolean; action?: ActionTrackingRecord; message?: string }> {
  if (role === "employee") {
    return { success: false, message: "Only authorized Safety Officers can update action status." };
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_URL}/actions/${encodeURIComponent(actionId)}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status,
        notes: notes || "",
        officer_name: officerName,
        officer_id: officerId,
        role,
      }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Failed to update action status" }));
      throw new Error(err.error?.message || err.detail || `Server returned ${res.status}`);
    }

    return await res.json();
  } catch (e: any) {
    clearTimeout(timeoutId);
    console.error(`Failed to update action ${actionId}:`, e?.message || e);
    return { success: false, message: e.message || "Network error" };
  }
}



