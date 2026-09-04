import logging
import sys
import uuid
from pathlib import Path
import numpy as np

# Configure standard production-grade logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("sentinel.api")

# Add backend directory to sys.path to support execution from any directory
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import joblib
import io
import pandas as pd

try:
    from services.similarity import SimilarityEngine
    from services.risk_engine import RiskEngine
    from services.review_service import ReviewService
    from services.analytics_service import SafetyAnalyticsService
    from services.alert_service import AlertService
    from services.action_tracking_service import ActionTrackingService
    from services.image_service import ImageEvidenceService
except ImportError:
    from backend.services.similarity import SimilarityEngine
    from backend.services.risk_engine import RiskEngine
    from backend.services.review_service import ReviewService
    from backend.services.analytics_service import SafetyAnalyticsService
    from backend.services.alert_service import AlertService
    from backend.services.action_tracking_service import ActionTrackingService
    from backend.services.image_service import ImageEvidenceService


# =========================
# CREATE FASTAPI APP
# =========================

app = FastAPI(
    title="Sentinel AI Safety Intelligence API",
    description="AI-powered industrial safety report analysis",
    version="1.0.0"
)


# =========================
# GLOBAL EXCEPTION HANDLERS (PRODUCTION-GRADE ERROR HANDLING)
# =========================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handles deliberate HTTPExceptions with clean structured JSON (no stack trace leak)."""
    logger.warning("HTTP %d error on %s %s: %s", exc.status_code, request.method, request.url.path, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "status_code": exc.status_code
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handles request body/parameter validation errors gracefully."""
    logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    first_error = exc.errors()[0] if exc.errors() else {}
    field_name = ".".join(str(loc) for loc in first_error.get("loc", []))
    msg = first_error.get("msg", "Invalid request payload format.")
    clean_msg = f"Validation error on '{field_name}': {msg}" if field_name else msg

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": clean_msg,
                "status_code": 422
            }
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catches all unhandled exceptions, logs technical stack traces internally, and returns clean error."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, str(exc), exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred while processing the safety request. Technical details have been logged.",
                "status_code": 500
            }
        }
    )


# =========================
# CORS CONFIGURATION
# =========================

import os

cors_origins_env = os.getenv("CORS_ORIGINS", "").strip()
if cors_origins_env == "*":
    cors_allowed_origins = ["*"]
    cors_allow_credentials = False
elif cors_origins_env:
    cors_allowed_origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]
    cors_allow_credentials = True
else:
    cors_allowed_origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    cors_allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allowed_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# LOAD ML MODEL SAFELY & CONSISTENCY VERIFICATION
# =========================

logger.info("Loading ML severity model...")

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "severity_model.pkl"
METRICS_PATH = BASE_DIR / "data" / "evaluation_metrics.json"

severity_model = None
model_metadata = {
    "model_path": str(MODEL_PATH),
    "model_version": "v2.0.0-honest-evaluation",
    "model_type": "Pipeline(tfidf: TfidfVectorizer, classifier: CalibratedClassifierCV)",
    "holdout_size": 62,
    "metrics_version": "v2.0.0-honest-evaluation"
}

try:
    if MODEL_PATH.exists():
        severity_model = joblib.load(MODEL_PATH)
        if hasattr(severity_model, "named_steps"):
            step_names = [f"{k}: {type(v).__name__}" for k, v in severity_model.named_steps.items()]
            model_metadata["model_type"] = f"Pipeline({', '.join(step_names)})"
        
        if METRICS_PATH.exists():
            try:
                with open(METRICS_PATH, "r", encoding="utf-8") as mf:
                    m_data = json.load(mf)
                    model_metadata["model_version"] = m_data.get("model_version", model_metadata["model_version"])
                    model_metadata["holdout_size"] = m_data.get("evaluation", {}).get("holdout_size", 62)
                    model_metadata["metrics_version"] = m_data.get("model_version", model_metadata["metrics_version"])
            except Exception:
                pass

        logger.info(
            "ML severity model loaded successfully. [Path: %s | Type: %s | Version: %s | Holdout Size: %s | Metrics Version: %s]",
            model_metadata["model_path"],
            model_metadata["model_type"],
            model_metadata["model_version"],
            model_metadata["holdout_size"],
            model_metadata["metrics_version"]
        )
    else:
        logger.warning("ML severity model file not found at %s. Running with rule-based fallback.", MODEL_PATH)
except Exception as model_err:
    logger.error("Failed to deserialize ML severity model: %s. Rule-based severity fallback active.", str(model_err), exc_info=True)
    severity_model = None


# =========================
# LOAD AI ENGINES & SERVICES
# =========================

similarity_engine = SimilarityEngine()
risk_engine = RiskEngine()
review_service = ReviewService()
analytics_service = SafetyAnalyticsService()
alert_service = AlertService()
action_service = ActionTrackingService()
image_service = ImageEvidenceService()

logger.info("All AI engines, Review Service, Analytics Service, Alert Service, Action Tracking Service, and Image Service loaded successfully!")


# =========================
# CENTRALIZED ROLE AUTHORIZATION
# =========================

def verify_officer_role(role: Optional[str], action: str = "perform this safety operation"):
    """
    Centralized role authorization check for safety officer operations.
    Strictly validates role == 'officer'. Rejects any employee or unauthenticated access
    with HTTP 403 Forbidden.
    """
    if not role or role.strip().lower() != "officer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: Only authorized Safety Officers can {action}. Safety Officer access required."
        )


# =========================
# REQUEST MODELS
# =========================

class SafetyReport(BaseModel):
    report_text: str
    industry_sector: Optional[str] = "Mining"
    worker_type: Optional[str] = "Employee"
    gender: Optional[str] = "Male"
    location: Optional[str] = ""
    report_type: Optional[str] = None
    image_base64: Optional[str] = None
    image_filename: Optional[str] = None


class SafetyOfficerReviewRequest(BaseModel):
    officer_name: str
    officer_id: str
    review_status: str
    reviewer_comment: str
    ai_prediction: dict
    human_decision: dict = {}
    report_id: str = ""
    role: Optional[str] = None


class UpdateAlertStatusRequest(BaseModel):
    status: str
    officer_name: Optional[str] = None
    officer_id: Optional[str] = None
    reviewer_notes: Optional[str] = None
    role: Optional[str] = None


class UpdateActionStatusRequest(BaseModel):
    status: str
    officer_name: Optional[str] = None
    officer_id: Optional[str] = None
    notes: Optional[str] = None
    role: Optional[str] = None


class InitiateActionRequest(BaseModel):
    report_id: str
    action_description: str
    priority: str = "HIGH"
    responsible_role: str = "Safety Officer"
    due_date: Optional[str] = None
    ai_context: Optional[dict] = None
    role: Optional[str] = None


# =========================
# HOME ROUTE
# =========================

@app.get("/")
def home():
    return {
        "message": "Sentinel AI Safety Intelligence API is running",
        "status": "active"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "model_loaded": severity_model is not None
    }


# =========================
# CORE REPORT ANALYSIS PIPELINE
# =========================

def _process_single_report(
    report_text: str,
    industry_sector: str = "Mining",
    worker_type: str = "Employee",
    gender: str = "Male",
    location: str = "",
    image_base64: Optional[str] = None,
    image_filename: Optional[str] = None
) -> dict:
    """Executes the complete multi-stage AI safety analysis pipeline for an observation narrative."""
    # 0. Input Validation
    if not report_text or not report_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Observation narrative cannot be empty or only whitespace."
        )

    # 1. Precursor Detection
    try:
        precursors = risk_engine.detect_precursors(report_text)
    except Exception as pe:
        logger.error("Precursor detection engine encountered error: %s", str(pe), exc_info=True)
        precursors = []
    base_precursor_score = sum(p.get("contribution", 0) for p in precursors)

    # 2. ML Severity Prediction & Probability Calibration
    model_input = (
        "Description: " + report_text
        + " Industry Sector: " + (industry_sector or "Mining")
        + " Worker Type: " + (worker_type or "Employee")
        + " Gender: " + (gender or "Male")
    )

    if severity_model is not None:
        try:
            model_classes = list(
                severity_model.classes_
                if hasattr(severity_model, 'classes_')
                else severity_model.named_steps['classifier'].classes_
            )
            if hasattr(severity_model, 'predict_proba'):
                probs = severity_model.predict_proba([model_input])[0]
                confidence_method = 'Probability estimate'
            elif hasattr(severity_model, 'decision_function'):
                scores = np.asarray(severity_model.decision_function([model_input])[0], dtype=float)
                scores = scores - np.max(scores)
                exp_scores = np.exp(scores)
                probs = exp_scores / np.sum(exp_scores)
                confidence_method = 'Decision-score softmax (not calibrated probability)'
            else:
                raise RuntimeError('Severity model supports neither predict_proba nor decision_function')
            class_prob_map = {str(c): round(float(p), 3) for c, p in zip(model_classes, probs)}
            raw_confidence = round(float(np.max(probs)), 3)
            raw_predicted_level = str(model_classes[int(np.argmax(probs))])
        except Exception as pred_err:
            logger.warning("ML prediction failed (%s). Using fallback rule-based severity.", str(pred_err))
            raw_predicted_level = "II"
            class_prob_map = {}
            raw_confidence = 0.85
    else:
        raw_predicted_level = "II"
        class_prob_map = {}
        raw_confidence = 0.85

    # Safe observation calibration
    if base_precursor_score == 0 and len(precursors) == 0:
        predicted_level = "I"
        confidence = 0.95
        calibration_applied = "Rule Calibration (Safe Observation -> Level I)"
    elif base_precursor_score < 25:
        predicted_level = "I" if raw_predicted_level in ["I", "II"] else "II"
        confidence = max(raw_confidence, 0.80)
        calibration_applied = "Rule Calibration (Low Risk Cap -> Level I/II)"
    else:
        predicted_level = raw_predicted_level
        confidence = raw_confidence
        calibration_applied = "Platt Scaling (CalibratedClassifierCV)"

    severity_label_map = {
        "I": "Minor (Level I)",
        "II": "Moderate (Level II)",
        "III": "Serious (Level III)",
        "IV": "Critical (Level IV)",
        "V": "Catastrophic (Level V)"
    }

    # 3. Multi-Signal SIF Risk Scoring
    try:
        risk_analysis = risk_engine.analyze(
            report_text,
            predicted_severity=str(predicted_level)
        )
    except Exception as re_err:
        logger.error("Risk engine calculation error: %s", str(re_err), exc_info=True)
        risk_analysis = {
            "score": base_precursor_score,
            "level": "LOW" if base_precursor_score < 20 else ("MEDIUM" if base_precursor_score < 50 else "HIGH"),
            "summary": "Risk evaluated via base precursor estimation.",
            "formula_explanation": "Fallback calculation.",
            "base_precursor_score": base_precursor_score,
            "compound_risk_boost": 0,
            "components": []
        }

    # 4. Historical Precedent Retrieval
    try:
        similar_incidents = similarity_engine.find_similar(
            report_text,
            top_n=3
        )
    except Exception as sim_err:
        logger.error("Similarity retrieval error: %s", str(sim_err), exc_info=True)
        similar_incidents = []

    # 5. Precursor Explanation & Actions
    precursor_labels = [
        factor.get("label", factor.get("factor", "Unknown"))
        for factor in precursors
    ]

    if precursor_labels:
        factors_text = ", ".join(precursor_labels)
        explanation = (
            f"The AI identified {factors_text}. "
            f"These factors contribute to an overall "
            f"{risk_analysis.get('level', 'Unknown')} safety risk."
        )
    else:
        explanation = (
            "The AI did not detect any major predefined "
            "safety precursors in the submitted report."
        )

    recommended_actions = risk_analysis.get("recommended_actions", [])
    if not recommended_actions:
        for factor in precursors:
            factor_name = factor.get("factor", "")
            if factor_name == "high_pressure":
                recommended_actions.append("Inspect and secure high-pressure equipment before continuing operations.")
            elif factor_name == "leakage":
                recommended_actions.append("Identify and isolate the source of leakage immediately.")
            elif factor_name == "ppe":
                recommended_actions.append("Ensure all personnel use the required personal protective equipment.")
            elif factor_name == "maintenance":
                recommended_actions.append("Conduct a safety review before continuing maintenance activities.")
            elif factor_name == "fire_gas":
                recommended_actions.append("Inspect the area for gas accumulation and potential ignition sources.")
            elif factor_name == "electrical":
                recommended_actions.append("Isolate electrical energy sources and perform an electrical safety inspection.")
            elif factor_name == "confined_space":
                recommended_actions.append("Follow confined-space entry procedures and verify atmospheric safety.")

        if not recommended_actions:
            recommended_actions.append("Standard routine field inspection and operational monitoring recommended.")

    # 6. Corrective Action Tracking & Governance
    assigned_report_id = f"REP-{uuid.uuid4().hex[:8].upper()}"
    raw_corrective_actions = risk_analysis.get("corrective_actions", [])
    try:
        tracked_actions = action_service.register_actions_for_analysis(
            report_id=assigned_report_id,
            corrective_actions=raw_corrective_actions
        )
    except Exception as act_err:
        logger.warning("Action registration error: %s", str(act_err))
        tracked_actions = []

    enriched_corrective_actions = []
    for idx, ca in enumerate(raw_corrective_actions):
        ca_copy = dict(ca)
        if idx < len(tracked_actions):
            t_rec = tracked_actions[idx]
            ca_copy["action_id"] = t_rec.get("action_id")
            ca_copy["report_id"] = t_rec.get("report_id")
            ca_copy["status"] = t_rec.get("status", "OPEN")
            ca_copy["verification_status"] = t_rec.get("verification_status", "UNVERIFIED")
            ca_copy["created_at"] = t_rec.get("created_at")
            ca_copy["responsible_role"] = t_rec.get("responsible_role")
        enriched_corrective_actions.append(ca_copy)

    # 7. Optional Image Evidence Processing & Storage (Robust Isolation)
    image_record = image_service.process_and_store_image(
        image_payload=image_base64,
        report_id=assigned_report_id,
        original_filename=image_filename
    )

    # 8. Assembly of Full Analysis Payload
    analysis_payload = {
        "analysis_source": "backend_ai",
        "report_id": assigned_report_id,
        "overall_risk": {
            "score": risk_analysis.get("score", 0),
            "level": risk_analysis.get("level", "Unknown"),
            "summary": risk_analysis.get("summary", "No safety summary available."),
            "formula_explanation": risk_analysis.get("formula_explanation", ""),
            "base_precursor_score": risk_analysis.get("base_precursor_score", 0),
            "compound_risk_boost": risk_analysis.get("compound_risk_boost", 0),
            "components": risk_analysis.get("components", [])
        },
        "severity_prediction": {
            "potential_accident_level": str(predicted_level),
            "severity_label": severity_label_map.get(str(predicted_level), f"Level {predicted_level}"),
            "model": "Linear SVM (Platt Calibrated TF-IDF)" if severity_model is not None else "Rule-Based Heuristic",
            "model_version": "v2.0.0-calibrated-validation-selected",
            "confidence": confidence,
            "class_probabilities": class_prob_map,
            "calibration_note": calibration_applied,
            "label_mapping": severity_label_map
        },
        "detected_precursors": precursors,
        "ai_explanation": explanation,
        "corrective_actions": enriched_corrective_actions,
        "recommended_actions": recommended_actions,
        "historical_evidence": {
            "similar_cases_found": len(similar_incidents),
            "incidents": similar_incidents
        },
        "image_evidence": image_record.to_dict()
    }

    try:
        alert_record = alert_service.trigger_alert_if_needed(
            report_text=report_text,
            analysis_data=analysis_payload,
            location=location or "Field Site",
            department=industry_sector or "Mining",
            report_id=assigned_report_id
        )
    except Exception as alt_err:
        logger.error("Alert trigger evaluation error: %s", str(alt_err), exc_info=True)
        alert_record = None

    analysis_payload["alert"] = alert_record
    analysis_payload["alert_triggered"] = bool(alert_record is not None)

    return analysis_payload


# =========================
# ANALYZE SINGLE REPORT ROUTE
# =========================

@app.post("/analyze")
def analyze_report(report: SafetyReport):
    """Analyzes a single safety report with validation and structured response."""
    if not report.report_text or not report.report_text.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Safety report observation description cannot be empty or only whitespace."
        )

    analysis = _process_single_report(
        report_text=report.report_text,
        industry_sector=report.industry_sector or "Mining",
        worker_type=report.worker_type or "Employee",
        gender=report.gender or "Male",
        location=report.location or "",
        image_base64=report.image_base64,
        image_filename=report.image_filename
    )
    return {
        "success": True,
        "analysis_source": "backend_ai",
        "analysis": analysis
    }


# =========================
# BATCH ANALYZE REPORTS ROUTE (CSV / XLSX)
# =========================

@app.post("/analyze/batch")
async def analyze_batch_reports(file: UploadFile = File(...)):
    """Processes multiple safety observation reports uploaded in CSV or Excel (XLSX/XLS) format."""
    filename = file.filename or "uploaded_file"
    ext = Path(filename).suffix.lower()

    if ext not in [".csv", ".xlsx", ".xls", ".parquet", ".json"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Please upload a CSV (.csv), Excel (.xlsx, .xls), Parquet (.parquet), or JSON (.json) file."
        )

    try:
        contents = await file.read()
        if len(contents) > 25 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file exceeds 25 MB maximum batch size limit. Please split dataset into smaller files."
            )

        if len(contents) == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded file is empty (0 bytes)."
            )

        if ext == ".csv":
            try:
                df = pd.read_csv(io.BytesIO(contents), encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(contents), encoding="latin-1")
        elif ext in [".xlsx", ".xls"]:
            df = pd.read_excel(io.BytesIO(contents))
        elif ext == ".parquet":
            df = pd.read_parquet(io.BytesIO(contents))
        elif ext == ".json":
            df = pd.read_json(io.BytesIO(contents))
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to parse batch file '%s': %s", filename, str(e), exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to parse tabular file '{filename}': {str(e)}")

    if df.empty:
        return {
            "success": True,
            "analysis_source": "backend_ai",
            "filename": filename,
            "summary": {
                "total_reports": 0,
                "successfully_analyzed": 0,
                "failed_rows": 0,
                "high_risk_count": 0,
                "critical_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0,
                "severity_distribution": {"I": 0, "II": 0, "III": 0, "IV": 0, "V": 0}
            },
            "results": []
        }

    # Normalize column names for flexible lookup
    col_mapping = {}
    for col in df.columns:
        clean_col = str(col).strip().lower()
        col_mapping[clean_col] = col

    def find_col(candidates):
        for c in candidates:
            if c in col_mapping:
                return col_mapping[c]
        return None

    desc_col = find_col(["description", "narrative", "observation", "report_text", "text", "details", "incident_description"])
    if not desc_col:
        raise HTTPException(
            status_code=400,
            detail="No valid observation description column found in the uploaded file. Expected columns such as 'Description', 'description', 'report_text', 'narrative', 'observation', or 'text'."
        )

    sector_col = find_col(["industry_sector", "industry sector", "sector", "department", "dept", "operation_area"])
    worker_col = find_col(["worker_type", "worker type", "employee or third party", "employee_type", "role"])
    gender_col = find_col(["gender", "genre", "sex"])
    location_col = find_col(["location", "local", "facility", "site", "rig_location"])
    report_type_col = find_col(["report_type", "report type", "type", "category"])

    results = []
    success_count = 0
    failed_count = 0
    high_count = 0
    critical_count = 0
    medium_count = 0
    low_count = 0
    sev_dist = {"I": 0, "II": 0, "III": 0, "IV": 0, "V": 0}

    for idx, row in df.iterrows():
        row_num = int(idx) + 1
        raw_text = str(row[desc_col]).strip() if (desc_col and pd.notna(row[desc_col])) else ""

        if not raw_text or len(raw_text) < 4 or raw_text.lower() == "nan":
            failed_count += 1
            results.append({
                "row_index": row_num,
                "status": "FAILED",
                "error": "Empty or insufficient narrative text (< 4 characters).",
                "raw_data": {str(k): (str(v) if pd.notna(v) else "") for k, v in row.items()}
            })
            continue

        sector_val = str(row[sector_col]).strip() if (sector_col and pd.notna(row[sector_col])) else "Mining"
        worker_val = str(row[worker_col]).strip() if (worker_col and pd.notna(row[worker_col])) else "Employee"
        gender_val = str(row[gender_col]).strip() if (gender_col and pd.notna(row[gender_col])) else "Male"
        location_val = str(row[location_col]).strip() if (location_col and pd.notna(row[location_col])) else ""
        report_type_val = str(row[report_type_col]).strip() if (report_type_col and pd.notna(row[report_type_col])) else "Observation"

        try:
            analysis_data = _process_single_report(
                report_text=raw_text,
                industry_sector=sector_val,
                worker_type=worker_val,
                gender=gender_val,
                location=location_val
            )

            level = analysis_data["overall_risk"]["level"]
            pot_level = analysis_data["severity_prediction"]["potential_accident_level"]

            if level == "CRITICAL":
                critical_count += 1
            elif level == "HIGH":
                high_count += 1
            elif level == "MEDIUM":
                medium_count += 1
            else:
                low_count += 1

            if pot_level in sev_dist:
                sev_dist[pot_level] += 1

            success_count += 1
            results.append({
                "row_index": row_num,
                "status": "SUCCESS",
                "report_text": raw_text,
                "location": location_val,
                "department": sector_val,
                "report_type": report_type_val,
                "analysis": analysis_data
            })
        except Exception as row_err:
            logger.warning("Error processing batch row #%d: %s", row_num, str(row_err))
            failed_count += 1
            results.append({
                "row_index": row_num,
                "status": "FAILED",
                "error": f"Analysis execution error: {str(row_err)}",
                "raw_data": {str(k): (str(v) if pd.notna(v) else "") for k, v in row.items()}
            })

    summary = {
        "total_reports": len(df),
        "successfully_analyzed": success_count,
        "failed_rows": failed_count,
        "critical_risk_count": critical_count,
        "high_risk_count": high_count,
        "medium_risk_count": medium_count,
        "low_risk_count": low_count,
        "severity_distribution": sev_dist
    }

    return {
        "success": True,
        "analysis_source": "backend_ai",
        "filename": filename,
        "summary": summary,
        "results": results
    }


# =========================
# HUMAN-IN-THE-LOOP SAFETY REVIEW ROUTES
# =========================

@app.post("/review/submit")
def submit_safety_review(req: SafetyOfficerReviewRequest):
    """Saves a safety officer's authoritative review decision and audit trail with strict validation."""
    verify_officer_role(req.role, "submit or modify safety reviews")
    try:
        record = review_service.submit_review(
            officer_name=req.officer_name,
            officer_id=req.officer_id,
            review_status=req.review_status,
            reviewer_comment=req.reviewer_comment,
            ai_prediction=req.ai_prediction,
            human_decision=req.human_decision,
            report_id=req.report_id or None
        )
        return {
            "success": True,
            "message": f"Review record {record['review_id']} successfully archived.",
            "record": record
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.get("/reviews")
def list_safety_reviews(limit: int = 50):
    """Retrieves all archived safety review audit records."""
    reviews = review_service.list_reviews(limit=limit)
    return {
        "success": True,
        "total": len(reviews),
        "reviews": reviews
    }


@app.get("/review/{review_id}")
def get_safety_review(review_id: str):
    """Retrieves a specific safety review record by ID."""
    record = review_service.get_review(review_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Review record '{review_id}' not found.")
    return {
        "success": True,
        "record": record
    }


# =========================
# RISK-TRIGGERED SAFETY ALERTS ROUTES
# =========================

@app.get("/alerts")
def list_safety_alerts(status: Optional[str] = None, limit: int = 100):
    """Retrieves all risk-triggered safety alerts with optional status filtering (NEW, ACKNOWLEDGED, RESOLVED)."""
    all_matching = [
        a for a in alert_service.alerts.values()
        if not status or a.get("alert_status") == status.upper().strip()
    ]
    alerts = alert_service.list_alerts(status=status, limit=limit)
    return {
        "success": True,
        "total": len(all_matching),
        "total_store_count": len(alert_service.alerts),
        "alerts": alerts
    }


@app.get("/alerts/{alert_id}")
def get_safety_alert(alert_id: str):
    """Retrieves a specific safety alert record by ID."""
    alert = alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
    return {
        "success": True,
        "alert": alert
    }


@app.patch("/alerts/{alert_id}/status")
def update_safety_alert_status(alert_id: str, req: UpdateAlertStatusRequest):
    """Updates the triage status of an active safety alert (NEW, ACKNOWLEDGED, RESOLVED)."""
    verify_officer_role(req.role, "acknowledge or resolve safety alerts")
    try:
        updated = alert_service.update_alert_status(
            alert_id=alert_id,
            status=req.status,
            officer_name=req.officer_name,
            officer_id=req.officer_id,
            reviewer_notes=req.reviewer_notes
        )
        if not updated:
            raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")
        return {
            "success": True,
            "message": f"Alert {alert_id} status updated to {req.status.upper()}.",
            "alert": updated
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


# =========================
# SAFETY & MODEL ANALYTICS ROUTES
# =========================

@app.get("/analytics/operational")
def get_operational_analytics():
    """Returns operational safety statistics across the historical knowledge corpus."""
    data = analytics_service.get_operational_analytics()
    return {
        "success": True,
        "data": data
    }


@app.get("/analytics/locations")
def get_location_analytics():
    """Returns location-wise safety distributions, high/critical risk rates, and top recurring precursors."""
    locations = analytics_service.get_location_analytics()
    return {
        "success": True,
        "total_locations": len(locations),
        "locations": locations
    }


@app.get("/analytics/departments")
def get_department_analytics():
    """Returns department and industry sector safety distributions and top recurring precursors."""
    departments = analytics_service.get_department_analytics()
    return {
        "success": True,
        "total_departments": len(departments),
        "departments": departments
    }


@app.get("/analytics/trends")
def get_time_trend_analytics():
    """Returns historical risk and incident trends over time."""
    trends = analytics_service.get_time_trend_analytics()
    return {
        "success": True,
        "total_periods": len(trends),
        "trends": trends
    }


@app.get("/analytics/model-performance")
def get_model_performance_analytics():
    """Returns verified zero-leakage ML model evaluation and per-class recall metrics."""
    data = analytics_service.get_model_performance_analytics()
    return {
        "success": True,
        "data": data
    }


@app.get("/analytics")
def get_combined_analytics():
    """Returns logically separated operational and model performance analytics."""
    operational = analytics_service.get_operational_analytics()
    model_perf = analytics_service.get_model_performance_analytics()
    return {
        "success": True,
        "operational_analytics": operational,
        "model_performance_analytics": model_perf
    }


# =========================
# CORRECTIVE ACTION TRACKING ROUTES (TASK 10)
# =========================

@app.get("/actions")
def list_corrective_actions(
    report_id: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 100
):
    """Lists tracked corrective actions with optional filters for report ID, status, and priority."""
    all_matching = list(action_service.actions.values())
    if report_id:
        all_matching = [a for a in all_matching if a.get("report_id") == report_id.strip()]
    if status:
        all_matching = [a for a in all_matching if a.get("status") == status.upper().strip()]
    if priority:
        all_matching = [a for a in all_matching if a.get("priority") == priority.upper().strip()]

    actions = action_service.list_actions(
        report_id=report_id,
        status=status,
        priority=priority,
        limit=limit
    )
    return {
        "success": True,
        "total": len(all_matching),
        "total_store_count": len(action_service.actions),
        "actions": actions
    }


@app.get("/actions/stats")
def get_action_statistics():
    """Returns summary metrics and resolution counts for all tracked corrective actions."""
    stats = action_service.get_statistics()
    return {
        "success": True,
        "statistics": stats
    }


@app.get("/actions/{action_id}")
def get_corrective_action(action_id: str):
    """Retrieves a single tracked corrective action by its action ID."""
    action = action_service.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"Corrective action '{action_id}' not found.")
    return {
        "success": True,
        "action": action
    }


@app.patch("/actions/{action_id}/status")
def update_corrective_action_status(action_id: str, req: UpdateActionStatusRequest):
    """Updates the status of a tracked corrective action (OPEN, IN_PROGRESS, COMPLETED, VERIFIED)."""
    verify_officer_role(req.role, "update action status")
    try:
        updated = action_service.update_action_status(
            action_id=action_id,
            status=req.status,
            officer_name=req.officer_name,
            officer_id=req.officer_id,
            notes=req.notes
        )
        return {
            "success": True,
            "message": f"Action '{action_id}' status updated to {req.status.upper()}.",
            "action": updated
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@app.post("/actions/initiate")
def initiate_corrective_action(req: InitiateActionRequest):
    """Initiates a new tracked corrective action task."""
    verify_officer_role(req.role, "initiate corrective actions")
    try:
        record = action_service.create_action(
            report_id=req.report_id,
            action_description=req.action_description,
            priority=req.priority,
            responsible_role=req.responsible_role,
            due_date=req.due_date,
            ai_context=req.ai_context
        )
        return {
            "success": True,
            "message": f"Action '{record['action_id']}' initiated successfully.",
            "action": record
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


# =========================
# IMAGE EVIDENCE RETRIEVAL ROUTES
# =========================

@app.get("/evidence/{image_id}")
def get_evidence_image(image_id: str):
    """Serves a stored field evidence image file."""
    file_path = image_service.get_image_file_path(image_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Image evidence '{image_id}' not found.")
    return FileResponse(str(file_path))


@app.get("/evidence/{image_id}/meta")
def get_evidence_image_meta(image_id: str):
    """Retrieves metadata for a stored field evidence image."""
    meta = image_service.get_image_metadata(image_id)
    if not meta:
        file_path = image_service.get_image_file_path(image_id)
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Image evidence '{image_id}' not found.")
        return {
            "image_id": image_id,
            "file_size_bytes": file_path.stat().st_size,
            "filename": file_path.name,
            "url_reference": f"/evidence/{image_id}"
        }
    return meta


