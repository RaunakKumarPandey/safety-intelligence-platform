"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import {
  analyzeSafetyReport,
  analyzeSafetyReportBatch,
  saveAnalysisResult,
  SAFETY_ANALYSIS_STORAGE_KEY,
  AnalysisResponse,
  BatchAnalysisResponse,
  BatchAnalysisItem,
} from "@/lib/api";
import { isUserAuthenticated } from "@/lib/auth";
import ThemeToggle from "../components/ThemeToggle";

const quickScenarios = [
  {
    label: "🔥 Gas Flaring Surge",
    type: "Near Miss",
    department: "Drilling Operations",
    location: "Compressor Bay #3, Duliajan Rig",
    desc: "During routine compressor startup at bay 3, severe vibration was observed followed by high-pressure natural gas hissing from flange gasket. Hydrocarbon gas detector alarmed at 35% LEL. Operator evacuated perimeter immediately without hearing protection.",
  },
  {
    label: "🏗️ Scaffold Fall Hazard",
    type: "Unsafe Act",
    department: "Maintenance",
    location: "Production Separator Column 2",
    desc: "Contractor technician was observed working at 18 meters height without full-body harness tethered to safety lifeline. Scaffold plank was unfastened and shifted 4 inches when heavy wrench dropped, narrowly missing ground crew.",
  },
  {
    label: "⚡ Wellhead Cable Hazard",
    type: "Unsafe Condition",
    department: "Maintenance",
    location: "Wellhead Cluster W-14",
    desc: "Frayed 440V electrical power cable found lying in pool of spilled drilling fluid and crude residue near high-vibration pump skid. Potential ignition hazard in Zone-1 classification area.",
  },
];

export default function SubmitReportPage() {
  const router = useRouter();

  // Mode: single report vs batch upload
  const [activeMode, setActiveMode] = useState<"single" | "batch">("single");

  // Single Report State
  const [reportType, setReportType] = useState("Unsafe Condition");
  const [location, setLocation] = useState("");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionError, setSubmissionError] = useState<string | null>(null);

  const [department, setDepartment] = useState("Drilling Operations");
  const [departmentOpen, setDepartmentOpen] = useState(false);

  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [imageName, setImageName] = useState("");
  const [rawImageFile, setRawImageFile] = useState<File | null>(null);

  // Voice-to-Text State
  const [isRecording, setIsRecording] = useState(false);
  const [voiceSupported, setVoiceSupported] = useState(true);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [recognitionInstance, setRecognitionInstance] = useState<any>(null);

  // Batch Upload State
  const [batchFile, setBatchFile] = useState<File | null>(null);
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);
  const [batchResponse, setBatchResponse] = useState<BatchAnalysisResponse | null>(null);
  const [batchError, setBatchError] = useState<string | null>(null);
  const [expandedRow, setExpandedRow] = useState<number | null>(null);

  const departments = [
    "Production",
    "Maintenance",
    "Logistics",
    "Safety & HSE",
    "Quality Control",
    "Drilling Operations",
  ];

  // Check browser speech recognition capability
  useEffect(() => {
    if (typeof window !== "undefined") {
      const SpeechRec =
        (window as any).SpeechRecognition ||
        (window as any).webkitSpeechRecognition;
      if (!SpeechRec) {
        setVoiceSupported(false);
      }
    }
  }, []);

  // Auth protection & Auto-fill from sessionStorage if directed from landing page
  useEffect(() => {
    if (!isUserAuthenticated()) {
      router.push("/login?redirect=/submit-report");
      return;
    }

    try {
      const prefill = sessionStorage.getItem("prefilledReport");
      if (prefill) {
        const parsed = JSON.parse(prefill);
        if (parsed.description) setDescription(parsed.description);
        if (parsed.location) setLocation(parsed.location);
        if (parsed.department) setDepartment(parsed.department);
        if (parsed.reportType) setReportType(parsed.reportType);
        sessionStorage.removeItem("prefilledReport");
      }
    } catch {
      // ignore
    }
  }, [router]);

  // Revoke object URL on unmount to prevent memory leaks
  useEffect(() => {
    return () => {
      if (selectedImage && selectedImage.startsWith("blob:")) {
        URL.revokeObjectURL(selectedImage);
      }
    };
  }, [selectedImage]);

  const toggleVoiceRecording = () => {
    if (isRecording && recognitionInstance) {
      try {
        recognitionInstance.stop();
      } catch {
        // ignore
      }
      setIsRecording(false);
      return;
    }

    setVoiceError(null);
    if (typeof window === "undefined") return;

    const SpeechRec =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;

    if (!SpeechRec) {
      setVoiceSupported(false);
      setVoiceError("Voice recognition is not supported in this browser.");
      return;
    }

    try {
      const recognition = new SpeechRec();
      recognition.lang = "en-US";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => {
        setIsRecording(true);
        setVoiceError(null);
      };

      recognition.onresult = (event: any) => {
        const transcript = event.results?.[0]?.[0]?.transcript;
        if (transcript) {
          setDescription((prev) =>
            prev && prev.trim().length > 0
              ? `${prev.trim()} ${transcript.trim()}`
              : transcript.trim()
          );
        }
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition error:", event.error);
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          setVoiceError("Microphone permission denied. Please allow microphone access.");
        } else if (event.error === "no-speech") {
          setVoiceError("No speech detected. Please speak clearly into the microphone.");
        } else {
          setVoiceError(`Voice input: ${event.error}`);
        }
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      setRecognitionInstance(recognition);
      recognition.start();
    } catch (err: any) {
      console.error("Failed to start speech recognition:", err);
      setVoiceError("Could not initialize microphone input.");
      setIsRecording(false);
    }
  };

  const handleApplyPreset = (item: (typeof quickScenarios)[0]) => {
    setReportType(item.type);
    setDepartment(item.department);
    setLocation(item.location);
    setDescription(item.desc);
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (selectedImage && selectedImage.startsWith("blob:")) {
        URL.revokeObjectURL(selectedImage);
      }
      setImageName(file.name);
      setRawImageFile(file);
      setSelectedImage(URL.createObjectURL(file));
    }
  };

  const handleRemoveImage = () => {
    if (selectedImage && selectedImage.startsWith("blob:")) {
      URL.revokeObjectURL(selectedImage);
    }
    setSelectedImage(null);
    setImageName("");
    setRawImageFile(null);
  };

  const handleSubmit = async (e: FormEvent) => {
    // 1. preventDefault
    e.preventDefault();
    setSubmissionError(null);

    // 2. validate description
    const cleanDesc = description.trim();
    if (!cleanDesc || cleanDesc.length < 4) {
      setSubmissionError("Please enter a meaningful safety observation narrative (minimum 4 characters) before submitting.");
      return;
    }

    try {
      // 3. setIsSubmitting(true)
      setIsSubmitting(true);
      console.log("[SafetyAI] Initiating report submission...");

      // 4. prepare optional image
      let imageBase64: string | undefined = undefined;
      if (rawImageFile) {
        try {
          imageBase64 = await new Promise<string>((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result as string);
            reader.onerror = reject;
            reader.readAsDataURL(rawImageFile);
          });
        } catch (imgErr) {
          console.warn("[SafetyAI] Could not encode image to base64:", imgErr);
        }
      }

      // 5. call analyzeSafetyReport()
      const result = await analyzeSafetyReport({
        report_text: cleanDesc,
        industry_sector: department || "Mining",
        worker_type: "Employee",
        gender: "Male",
        location: location || "",
        report_type: reportType,
        image_base64: imageBase64,
        image_filename: imageName || undefined,
      }, 20000);

      // 6. validate returned result
      if (!result || !result.success || !result.analysis || !result.analysis.overall_risk) {
        throw new Error("Invalid response received from Safety AI analysis engine.");
      }

      // 7. save using saveAnalysisResult(result)
      const savedSuccessfully = saveAnalysisResult(result);
      if (!savedSuccessfully) {
        throw new Error("Safety analysis result could not be stored in browser session storage.");
      }

      // 8. verify sessionStorage contains "safetyAnalysis"
      const storedCheck = sessionStorage.getItem(SAFETY_ANALYSIS_STORAGE_KEY);
      if (!storedCheck) {
        throw new Error("Verification failed: safetyAnalysis key missing from sessionStorage.");
      }

      // 9. ONLY THEN router.push("/analysis")
      console.log("[SafetyAI] Verified storage. Navigating to /analysis...");
      router.push("/analysis");
    } catch (error: any) {
      console.error("[SafetyAI] Submission failed:", error);
      setSubmissionError(
        error?.message || "Failed to analyze report. Please ensure the safety analysis service is reachable."
      );
    } finally {
      // 10. finally setIsSubmitting(false)
      setIsSubmitting(false);
    }
  };

  const handleBatchFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setBatchFile(file);
      setBatchError(null);
      setBatchResponse(null);
    }
  };

  const handleRunBatchAnalysis = async () => {
    if (!batchFile) {
      setBatchError("Please select a batch CSV or Excel file to process.");
      return;
    }

    if (batchFile.size === 0) {
      setBatchError("The selected file is empty (0 bytes). Please select a valid dataset.");
      return;
    }

    if (batchFile.size > 25 * 1024 * 1024) {
      setBatchError("The selected file exceeds the 25 MB maximum batch size limit.");
      return;
    }

    try {
      setIsBatchProcessing(true);
      setBatchError(null);
      const res = await analyzeSafetyReportBatch(batchFile);
      setBatchResponse(res);
    } catch (err: any) {
      console.error("Batch processing failed:", err);
      setBatchError(err.message || "Failed to process batch file.");
    } finally {
      setIsBatchProcessing(false);
    }
  };

  const handleLoadSampleBatch = () => {
    const sampleCsvContent = `Description,Location,Department,Worker Type,Gender
"High-pressure natural gas hissing from separator flange gasket during startup. LEL detector triggered at 40%.","Compressor Bay #3, Duliajan Rig","Drilling Operations","Employee","Male"
"Technician observed at 15m elevation without safety harness lifeline connection while erecting scaffold.","Separator Column #2","Maintenance","Contractor / Third Party","Male"
"Exposed 440V electrical power cable lying in puddle of spilled drilling fluid near mud pump skid.","Wellhead Cluster W-14","Maintenance","Employee","Male"
"Routine safety inspection completed at workshop bay. All tools stowed on shadow board and PPE worn.","Workshop Bay A","Production","Employee","Male"
"Severe hydraulic oil line rupture spraying hot fluid near diesel generator exhaust manifold.","Power Plant Station 1","Drilling Operations","Employee","Male"`;

    const blob = new Blob([sampleCsvContent], { type: "text/csv;charset=utf-8;" });
    const file = new File([blob], "oilfield_sample_batch.csv", { type: "text/csv" });
    setBatchFile(file);
    setBatchError(null);
    setBatchResponse(null);
  };

  const handleInspectBatchItem = (item: BatchAnalysisItem) => {
    if (item.analysis) {
      const fullAnalysis: AnalysisResponse = {
        success: true,
        analysis_source: "backend_ai",
        analysis: item.analysis,
      };
      saveAnalysisResult(fullAnalysis);
      router.push("/analysis");
    }
  };

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
                Oil India Limited • Report Submission
              </p>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            <ThemeToggle />

            <Link
              href="/"
              className="rounded-full border border-slate-200 bg-white/50 px-4 py-2 text-xs font-bold transition hover:bg-slate-100 dark:border-white/10 dark:bg-white/5 dark:hover:bg-white/10"
            >
              ← Public Home
            </Link>
          </div>
        </div>
      </header>

      {/* CONTENT */}
      <section className="mx-auto max-w-7xl px-6 py-10">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6 mb-8">
          <div>
            <span className="rounded-full border border-orange-500/30 bg-orange-500/10 px-3.5 py-1 text-[10px] font-bold tracking-wider text-orange-600 dark:text-orange-400 uppercase">
              HSE Field Intake Portal
            </span>
            <h2 className="mt-3 text-3xl font-black md:text-4xl">
              Safety Observation &amp; Intake
            </h2>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
              Submit individual field observations or upload multi-record CSV/Excel logs for automated SIF precursor screening.
            </p>
          </div>

          {/* MODE SELECTOR TABS */}
          <div className="flex rounded-2xl border border-slate-200 bg-slate-100 p-1.5 dark:border-white/10 dark:bg-white/5 shrink-0">
            <button
              type="button"
              onClick={() => setActiveMode("single")}
              className={`rounded-xl px-5 py-2.5 text-xs font-bold transition ${
                activeMode === "single"
                  ? "bg-white text-orange-600 shadow-sm dark:bg-[#0a1915] dark:text-orange-400"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              }`}
            >
              📝 Single Report Form
            </button>
            <button
              type="button"
              onClick={() => setActiveMode("batch")}
              className={`rounded-xl px-5 py-2.5 text-xs font-bold transition ${
                activeMode === "batch"
                  ? "bg-white text-orange-600 shadow-sm dark:bg-[#0a1915] dark:text-orange-400"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
              }`}
            >
              📂 Batch Upload (CSV / XLSX)
            </button>
          </div>
        </div>

        {/* ==================================================================== */}
        {/* MODE 1: SINGLE REPORT FORM                                            */}
        {/* ==================================================================== */}
        {activeMode === "single" && (
          <div>
            {/* QUICK TEST CHIPS */}
            <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm dark:border-white/10 dark:bg-[#0a1f1a]">
              <p className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                Quick Oilfield Sample Fillers:
              </p>
              <div className="mt-3 flex flex-wrap gap-2.5">
                {quickScenarios.map((qs) => (
                  <button
                    key={qs.label}
                    type="button"
                    onClick={() => handleApplyPreset(qs)}
                    className="rounded-xl border border-orange-500/20 bg-orange-500/5 px-3.5 py-2 text-xs font-bold text-orange-600 transition hover:bg-orange-500/20 dark:text-orange-400"
                  >
                    {qs.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
              {/* FORM */}
              <form
                onSubmit={handleSubmit}
                className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 dark:border-white/10 dark:bg-[#0a1915]"
              >
                {/* TYPE */}
                <div>
                  <label className="text-sm font-bold text-slate-900 dark:text-white">
                    Observation Category
                  </label>

                  <div className="mt-3 grid gap-3 sm:grid-cols-3">
                    {[
                      {
                        type: "Unsafe Condition",
                        icon: "🔧",
                        desc: "Equipment, gas leak, pressure surge",
                      },
                      {
                        type: "Unsafe Act",
                        icon: "⚠️",
                        desc: "No harness, PPE defiance, shortcut",
                      },
                      {
                        type: "Near Miss",
                        icon: "🚨",
                        desc: "Close call that could cause SIF",
                      },
                    ].map((item) => (
                      <button
                        key={item.type}
                        type="button"
                        onClick={() => setReportType(item.type)}
                        className={`rounded-2xl border p-4 text-left transition-all ${
                          reportType === item.type
                            ? "border-orange-500 bg-orange-50/80 dark:bg-orange-500/10 shadow-md ring-1 ring-orange-500"
                            : "border-slate-200 hover:border-orange-300 dark:border-white/10"
                        }`}
                      >
                        <p className="font-bold text-slate-900 dark:text-white">
                          {item.icon} {item.type}
                        </p>
                        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                          {item.desc}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* LOCATION */}
                <div className="mt-6">
                  <label className="mb-2 block text-sm font-semibold">
                    Facility / Rig Location
                  </label>
                  <input
                    required
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. Duliajan Drill Rig #4, Compressor Station Bay 2"
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5"
                  />
                </div>

                {/* DEPARTMENT */}
                <div className="mt-6">
                  <label className="mb-2 block text-sm font-semibold">
                    Department / Operation Area
                  </label>
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setDepartmentOpen(!departmentOpen)}
                      className="flex w-full items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-left outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5"
                    >
                      <span
                        className={
                          department
                            ? "text-slate-900 dark:text-white font-medium"
                            : "text-slate-400"
                        }
                      >
                        {department || "Select department"}
                      </span>
                      <span className="text-xs text-slate-400">▼</span>
                    </button>

                    {departmentOpen && (
                      <div className="absolute z-20 mt-2 w-full rounded-2xl border border-slate-200 bg-white p-2 shadow-xl dark:border-white/10 dark:bg-[#0c201b]">
                        {departments.map((dept) => (
                          <button
                            key={dept}
                            type="button"
                            onClick={() => {
                              setDepartment(dept);
                              setDepartmentOpen(false);
                            }}
                            className="w-full rounded-xl px-4 py-2.5 text-left text-sm transition hover:bg-orange-50 hover:text-orange-600 dark:hover:bg-white/5 dark:hover:text-white"
                          >
                            {dept}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* DESCRIPTION */}
                <div className="mt-6">
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-sm font-semibold">
                      Observation Narrative / Free-Text Notes
                    </label>

                    {/* Microphone Interaction Button */}
                    {voiceSupported ? (
                      <button
                        type="button"
                        onClick={toggleVoiceRecording}
                        className={`flex items-center gap-1.5 rounded-xl px-3 py-1 text-xs font-bold transition shadow-sm ${
                          isRecording
                            ? "bg-red-500 text-white animate-pulse shadow-red-500/30"
                            : "border border-orange-500/30 bg-orange-500/10 text-orange-600 hover:bg-orange-500/20 dark:text-orange-400"
                        }`}
                        title={isRecording ? "Click to stop recording" : "Click to speak observation"}
                      >
                        <span>{isRecording ? "🔴" : "🎙️"}</span>
                        <span>{isRecording ? "Listening... (Stop)" : "Voice-to-Text"}</span>
                      </button>
                    ) : (
                      <span className="text-[11px] font-medium text-slate-400" title="Web Speech API not supported on this browser">
                        🎙️ Voice input unavailable
                      </span>
                    )}
                  </div>

                  {voiceError && (
                    <div className="mb-2 flex items-center justify-between rounded-xl border border-red-500/20 bg-red-500/5 px-3 py-1.5 text-xs text-red-600 dark:text-red-400">
                      <span>⚠️ {voiceError}</span>
                      <button
                        type="button"
                        onClick={() => setVoiceError(null)}
                        className="ml-2 font-bold hover:underline"
                      >
                        ✕
                      </button>
                    </div>
                  )}

                  <textarea
                    required
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={5}
                    placeholder="Describe the incident, observed hazard, pressure readings, or PPE violations in detail... (Type or use Voice-to-Text)"
                    className="w-full resize-none rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 outline-none transition focus:border-orange-500 dark:border-white/10 dark:bg-white/5"
                  />
                </div>

                {/* PHOTO UPLOAD */}
                <div className="mt-6">
                  <div className="mb-2 flex items-center justify-between">
                    <label className="text-sm font-semibold">
                      Evidence Photo <span className="text-slate-400">(Optional)</span>
                    </label>

                    {selectedImage && (
                      <button
                        type="button"
                        onClick={handleRemoveImage}
                        className="text-xs font-medium text-red-500 hover:text-red-600"
                      >
                        Remove Photo
                      </button>
                    )}
                  </div>

                  {!selectedImage ? (
                    <label className="group flex min-h-28 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 p-6 text-center transition hover:border-orange-400 hover:bg-orange-50/40 dark:border-white/10 dark:bg-white/[0.02] dark:hover:border-orange-500/40">
                      <span className="text-3xl transition-transform group-hover:scale-110">
                        📷
                      </span>
                      <p className="mt-2 text-sm font-semibold">
                        Attach observation photo / inspection snapshot
                      </p>
                      <p className="text-xs text-slate-400">
                        Supports JPG, PNG (Max 10MB)
                      </p>
                      <input
                        type="file"
                        accept="image/*"
                        className="hidden"
                        onChange={handleImageChange}
                      />
                    </label>
                  ) : (
                    <div className="relative overflow-hidden rounded-2xl border border-slate-200 dark:border-white/10">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={selectedImage}
                        alt="Uploaded preview"
                        className="h-48 w-full object-cover"
                      />
                      <div className="absolute inset-x-0 bottom-0 flex items-center justify-between bg-black/70 px-4 py-2 text-xs text-white">
                        <span className="truncate">{imageName}</span>
                        <span className="rounded bg-green-500/30 px-2 py-0.5 text-green-300 font-semibold">
                          Attached
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* SUBMISSION ERROR BANNER */}
                {submissionError && (
                  <div className="mt-6 flex items-start justify-between gap-3 rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-xs text-red-700 dark:border-red-500/20 dark:bg-red-500/[0.08] dark:text-red-300">
                    <div className="flex items-start gap-2.5">
                      <span className="text-base leading-none">⚠️</span>
                      <div>
                        <p className="font-bold text-red-800 dark:text-red-300">Submission Notice</p>
                        <p className="mt-0.5">{submissionError}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setSubmissionError(null)}
                      className="text-red-500 hover:text-red-700 dark:hover:text-red-200 font-bold"
                      aria-label="Dismiss error"
                    >
                      ✕
                    </button>
                  </div>
                )}

                {/* SUBMIT BUTTON */}
                <button
                  type="submit"
                  disabled={!description || isSubmitting}
                  className="mt-8 flex w-full items-center justify-center gap-3 rounded-2xl bg-gradient-to-r from-orange-500 to-amber-500 py-4 font-bold text-white shadow-lg shadow-orange-500/25 transition-all hover:shadow-orange-500/40 hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
                      Running AI Precursor Extraction &amp; Risk Scoring...
                    </>
                  ) : (
                    <>Run AI Risk &amp; SIF Analysis →</>
                  )}
                </button>
              </form>

              {/* RIGHT SIDE PANEL */}
              <aside className="space-y-5">
                <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                  <h3 className="font-extrabold text-base">OIL AI Screening Flow</h3>
                  <div className="mt-4 space-y-4 text-xs text-slate-600 dark:text-slate-400">
                    <div className="flex gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-orange-500/10 font-bold text-orange-600 dark:text-orange-400">
                        1
                      </span>
                      <p>
                        NLP extracts safety precursors (gas leaks, high pressure, PPE violations).
                      </p>
                    </div>
                    <div className="flex gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-orange-500/10 font-bold text-orange-600 dark:text-orange-400">
                        2
                      </span>
                      <p>
                        Machine Learning model predicts the potential incident severity.
                      </p>
                    </div>
                    <div className="flex gap-3">
                      <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-orange-500/10 font-bold text-orange-600 dark:text-orange-400">
                        3
                      </span>
                      <p>
                        Matches against 425+ historical cases to suggest actionable mitigations.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                  <h3 className="font-extrabold text-xs uppercase tracking-wider text-slate-400">
                    Regulatory Standards
                  </h3>
                  <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                    Calibrated under OISD Standard 113 / 114 and Directorate General of Mines Safety (DGMS) guidelines for hydrocarbon exploration.
                  </p>
                </div>
              </aside>
            </div>
          </div>
        )}

        {/* ==================================================================== */}
        {/* MODE 2: BATCH UPLOAD (CSV / XLSX)                                     */}
        {/* ==================================================================== */}
        {activeMode === "batch" && (
          <div className="space-y-8">
            {/* UPLOAD CARD */}
            <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8 dark:border-white/10 dark:bg-[#0a1915]">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                  <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                    Bulk Safety Report Processing
                  </h3>
                  <p className="mt-1 text-xs text-slate-600 dark:text-slate-400">
                    Upload an Excel (.xlsx, .xls) or CSV (.csv) file containing multiple safety observation records.
                  </p>
                </div>

                <button
                  type="button"
                  onClick={handleLoadSampleBatch}
                  className="inline-flex items-center gap-2 rounded-xl border border-orange-500/30 bg-orange-500/10 px-4 py-2 text-xs font-bold text-orange-600 transition hover:bg-orange-500/20 dark:text-orange-400"
                >
                  ⚡ Load 5-Report Oilfield Sample
                </button>
              </div>

              {/* DROPZONE */}
              <div className="mt-6">
                <label className="group flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 p-6 text-center transition hover:border-orange-500 hover:bg-orange-50/30 dark:border-white/15 dark:bg-white/[0.02] dark:hover:border-orange-500/50">
                  <span className="text-4xl transition-transform group-hover:scale-110">
                    📁
                  </span>
                  <p className="mt-3 text-sm font-bold text-slate-900 dark:text-white">
                    {batchFile ? batchFile.name : "Select or Drop CSV / Excel Spreadsheet"}
                  </p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Supports columns: <code className="text-orange-500 font-mono">Description</code>, <code className="text-orange-500 font-mono">Location</code>, <code className="text-orange-500 font-mono">Department</code>, <code className="text-orange-500 font-mono">Worker Type</code>, <code className="text-orange-500 font-mono">Gender</code>
                  </p>
                  <input
                    type="file"
                    accept=".csv, .xlsx, .xls"
                    className="hidden"
                    onChange={handleBatchFileChange}
                  />
                </label>
              </div>

              {/* FILE PREVIEW & SUBMIT */}
              {batchFile && (
                <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-white/10 dark:bg-white/5">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-orange-500/10 text-orange-600 dark:text-orange-400 font-bold text-base">
                      📄
                    </span>
                    <div>
                      <p className="text-sm font-bold text-slate-900 dark:text-white truncate max-w-xs sm:max-w-md">
                        {batchFile.name}
                      </p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Size: {(batchFile.size / 1024).toFixed(1)} KB • Format: {batchFile.name.split(".").pop()?.toUpperCase()}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 w-full sm:w-auto">
                    <button
                      type="button"
                      onClick={() => {
                        setBatchFile(null);
                        setBatchResponse(null);
                        setBatchError(null);
                      }}
                      className="rounded-xl border border-slate-200 px-4 py-2.5 text-xs font-bold text-slate-600 transition hover:bg-slate-200 dark:border-white/10 dark:text-slate-400 dark:hover:bg-white/10"
                    >
                      Clear
                    </button>
                    <button
                      type="button"
                      disabled={isBatchProcessing}
                      onClick={handleRunBatchAnalysis}
                      className="flex-1 sm:flex-initial flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-orange-500 to-amber-500 px-6 py-2.5 text-xs font-bold text-white shadow-md shadow-orange-500/20 transition hover:shadow-orange-500/30 disabled:opacity-50"
                    >
                      {isBatchProcessing ? (
                        <>
                          <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                          Processing Batch...
                        </>
                      ) : (
                        <>⚡ Process Batch AI Pipeline</>
                      )}
                    </button>
                  </div>
                </div>
              )}

              {/* ERROR ALERT */}
              {batchError && (
                <div className="mt-4 rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-xs font-semibold text-red-600 dark:text-red-400">
                  ⚠️ Error processing batch: {batchError}
                </div>
              )}
            </div>

            {/* BATCH RESULTS DASHBOARD */}
            {batchResponse && (
              <div className="space-y-6">
                {/* SUMMARY METRICS CARDS */}
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Total Reports
                    </p>
                    <p className="mt-2 text-3xl font-black text-slate-900 dark:text-white">
                      {batchResponse.summary.total_reports}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                      Processed in file
                    </p>
                  </div>

                  <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5 shadow-sm dark:border-emerald-500/10 dark:bg-emerald-500/[0.03]">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                      Successfully Analyzed
                    </p>
                    <p className="mt-2 text-3xl font-black text-emerald-600 dark:text-emerald-400">
                      {batchResponse.summary.successfully_analyzed}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                      Valid safety logs
                    </p>
                  </div>

                  <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-5 shadow-sm dark:border-red-500/10 dark:bg-red-500/[0.03]">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-red-600 dark:text-red-400">
                      Critical SIF Cases
                    </p>
                    <p className="mt-2 text-3xl font-black text-red-600 dark:text-red-400">
                      {batchResponse.summary.critical_risk_count}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                      Score &ge; 75 / Immediate Action
                    </p>
                  </div>

                  <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5 shadow-sm dark:border-amber-500/10 dark:bg-amber-500/[0.03]">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                      High Risk Cases
                    </p>
                    <p className="mt-2 text-3xl font-black text-amber-600 dark:text-amber-400">
                      {batchResponse.summary.high_risk_count}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                      Score 50-74 / Priority
                    </p>
                  </div>

                  <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-white/10 dark:bg-[#0a1915]">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                      Validation Errors
                    </p>
                    <p className="mt-2 text-3xl font-black text-slate-900 dark:text-white">
                      {batchResponse.summary.failed_rows}
                    </p>
                    <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                      Missing/empty descriptions
                    </p>
                  </div>
                </div>

                {/* DETAILED RESULTS TABLE / CARDS */}
                <div className="rounded-3xl border border-slate-200 bg-white shadow-sm overflow-hidden dark:border-white/10 dark:bg-[#0a1915]">
                  <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-white/10">
                    <div>
                      <h4 className="font-extrabold text-sm text-slate-900 dark:text-white">
                        Batch Triage Breakdown ({batchResponse.results.length} Rows)
                      </h4>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        Click any row to view expanded corrective actions and similarity evidence.
                      </p>
                    </div>

                    <button
                      type="button"
                      onClick={() => {
                        const jsonStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(batchResponse, null, 2));
                        const downloadAnchor = document.createElement("a");
                        downloadAnchor.setAttribute("href", jsonStr);
                        downloadAnchor.setAttribute("download", `batch_analysis_${Date.now()}.json`);
                        document.body.appendChild(downloadAnchor);
                        downloadAnchor.click();
                        downloadAnchor.remove();
                      }}
                      className="rounded-xl border border-slate-200 bg-white/50 px-3.5 py-1.5 text-xs font-bold text-slate-700 transition hover:bg-slate-100 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
                    >
                      💾 Export JSON Results
                    </button>
                  </div>

                  <div className="divide-y divide-slate-100 dark:divide-white/5">
                    {batchResponse.results.map((item) => {
                      const isExpanded = expandedRow === item.row_index;
                      const riskLevel = item.analysis?.overall_risk?.level || "UNKNOWN";
                      const riskScore = item.analysis?.overall_risk?.score || 0;
                      const severity = item.analysis?.severity_prediction?.potential_accident_level || "I";
                      const precursors = item.analysis?.detected_precursors || [];

                      return (
                        <div
                          key={item.row_index}
                          className={`p-6 transition ${
                            item.status === "FAILED"
                              ? "bg-red-50/30 dark:bg-red-950/10"
                              : isExpanded
                              ? "bg-slate-50 dark:bg-white/[0.02]"
                              : "hover:bg-slate-50/60 dark:hover:bg-white/[0.01]"
                          }`}
                        >
                          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                            <div className="flex items-start gap-4 flex-1">
                              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-200 text-xs font-black text-slate-700 dark:bg-white/10 dark:text-slate-300">
                                #{item.row_index}
                              </span>

                              <div className="flex-1 min-w-0">
                                <div className="flex flex-wrap items-center gap-2 mb-1">
                                  {item.status === "FAILED" ? (
                                    <span className="rounded-full bg-red-500/10 px-2.5 py-0.5 text-[10px] font-extrabold text-red-600 dark:text-red-400">
                                      FAILED ROW
                                    </span>
                                  ) : (
                                    <>
                                      <span
                                        className={`rounded-full px-2.5 py-0.5 text-[10px] font-extrabold ${
                                          riskLevel === "CRITICAL"
                                            ? "bg-red-500/10 text-red-600 dark:text-red-400"
                                            : riskLevel === "HIGH"
                                            ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                            : riskLevel === "MEDIUM"
                                            ? "bg-yellow-500/10 text-yellow-600 dark:text-yellow-400"
                                            : "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                        }`}
                                      >
                                        RISK: {riskLevel} ({riskScore}/100)
                                      </span>

                                      <span className="rounded-full bg-slate-200 px-2.5 py-0.5 text-[10px] font-extrabold text-slate-700 dark:bg-white/10 dark:text-slate-300">
                                        SEVERITY: LEVEL {severity}
                                      </span>

                                      {item.department && (
                                        <span className="rounded-full border border-slate-200 px-2 py-0.5 text-[10px] font-bold text-slate-500 dark:border-white/10 dark:text-slate-400">
                                          {item.department}
                                        </span>
                                      )}
                                    </>
                                  )}
                                </div>

                                <p className="text-xs text-slate-700 dark:text-slate-300 line-clamp-2">
                                  {item.report_text || item.error}
                                </p>

                                {precursors.length > 0 && (
                                  <div className="mt-2 flex flex-wrap gap-1.5">
                                    {precursors.map((p, pIdx) => (
                                      <span
                                        key={pIdx}
                                        className="rounded-md bg-orange-500/10 px-2 py-0.5 text-[10px] font-bold text-orange-600 dark:text-orange-400"
                                      >
                                        ⚠️ {p.label || p.factor} (+{p.contribution})
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>

                            <div className="flex items-center gap-2 self-end md:self-center shrink-0">
                              {item.status === "SUCCESS" && (
                                <>
                                  <button
                                    type="button"
                                    onClick={() =>
                                      setExpandedRow(isExpanded ? null : item.row_index)
                                    }
                                    className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-xs font-bold text-slate-700 transition hover:bg-slate-100 dark:border-white/10 dark:bg-white/5 dark:text-slate-300 dark:hover:bg-white/10"
                                  >
                                    {isExpanded ? "Hide Details ▲" : "View Details ▼"}
                                  </button>

                                  <button
                                    type="button"
                                    onClick={() => handleInspectBatchItem(item)}
                                    className="rounded-xl bg-orange-500/10 px-3 py-1.5 text-xs font-bold text-orange-600 transition hover:bg-orange-500/20 dark:text-orange-400"
                                  >
                                    Inspect in Single View →
                                  </button>
                                </>
                              )}
                            </div>
                          </div>

                          {/* EXPANDED DETAILS */}
                          {isExpanded && item.analysis && (
                            <div className="mt-5 pt-5 border-t border-slate-200 dark:border-white/10 grid gap-4 md:grid-cols-2">
                              <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/[0.02]">
                                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                                  AI Safety Explanation &amp; Alignment
                                </p>
                                <p className="mt-2 text-xs leading-relaxed text-slate-700 dark:text-slate-300">
                                  {item.analysis.ai_explanation}
                                </p>
                                {item.analysis.overall_risk.formula_explanation && (
                                  <p className="mt-2 text-[10px] text-slate-500 dark:text-slate-400 font-mono">
                                    Formula: {item.analysis.overall_risk.formula_explanation}
                                  </p>
                                )}
                              </div>

                              <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-white/10 dark:bg-white/[0.02]">
                                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                                  Recommended Corrective Actions
                                </p>
                                <ul className="mt-2 space-y-1.5 text-xs text-slate-700 dark:text-slate-300">
                                  {item.analysis.recommended_actions.map((act, actIdx) => (
                                    <li key={actIdx} className="flex items-start gap-2">
                                      <span className="text-orange-500">✓</span>
                                      <span>{act}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </section>
    </main>
  );
}
