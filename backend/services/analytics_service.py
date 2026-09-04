"""
Safety Analytics and Model Evaluation Service for SIH26165
----------------------------------------------------------
Computes:
1. Operational Safety Analytics:
   - Overall corpus distributions (Severity Level I-V, Precursors, Risk Tiers)
   - Location-wise safety analytics (reports, high-risk, critical-risk, severity distribution, top recurring SIF precursors)
   - Department/Industry Sector analytics (reports, high/critical risk, top recurring hazards)
   - Temporal risk trend analytics over time (monthly reports, high-risk counts, avg risk score)
2. ML Evaluation & SIF Recall Validation Metrics (derived from zero-leakage test holdouts)
3. Confusion Matrix and per-class False Positive / False Negative counts

Separates Operational Dashboard telemetry from ML Model Performance analytics.
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
import numpy as np
import pandas as pd
import json

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from services.data_pipeline import SafetyDataPipeline
    from services.risk_engine import RiskEngine, SIF_TAXONOMY
    from evaluate_model import run_full_evaluation
except ImportError:
    from backend.services.data_pipeline import SafetyDataPipeline
    from backend.services.risk_engine import RiskEngine, SIF_TAXONOMY
    from backend.evaluate_model import run_full_evaluation


class SafetyAnalyticsService:
    """Service providing operational safety analytics and verified ML performance metrics."""

    def __init__(self):
        self.pipeline = SafetyDataPipeline()
        self.risk_engine = RiskEngine()
        self._cached_eval_metrics: Optional[Dict[str, Any]] = None
        self._cached_operational_data: Optional[Dict[str, Any]] = None

    def _compute_full_operational_dataset(self) -> Dict[str, Any]:
        """Processes historical reports once and calculates comprehensive location, department, and temporal metrics."""
        try:
            df = self.pipeline.process_all(deduplicate=False)
        except Exception:
            df = pd.DataFrame()

        total_reports = len(df)
        if total_reports == 0:
            return {
                "available": False,
                "message": "Operational dataset not available",
                "total_reports_analyzed": 0,
                "location_analytics": [],
                "department_analytics": [],
                "time_trend_analytics": []
            }

        # Global aggregators
        sev_counts: Dict[str, int] = {"I": 0, "II": 0, "III": 0, "IV": 0, "V": 0}
        global_precursor_counts: Dict[str, int] = {p.name: 0 for p in SIF_TAXONOMY.values()}
        risk_level_dist: Dict[str, int] = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        sector_counts: Dict[str, int] = defaultdict(int)

        # Location-wise accumulator
        loc_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_reports": 0,
            "high_risk_reports": 0,
            "critical_risk_reports": 0,
            "severity_dist": {"I": 0, "II": 0, "III": 0, "IV": 0, "V": 0},
            "precursor_counts": defaultdict(int),
            "total_score": 0
        })

        # Department-wise accumulator
        dept_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_reports": 0,
            "high_risk_reports": 0,
            "critical_risk_reports": 0,
            "severity_dist": {"I": 0, "II": 0, "III": 0, "IV": 0, "V": 0},
            "precursor_counts": defaultdict(int),
            "total_score": 0
        })

        # Temporal accumulator (by YYYY-MM)
        time_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_reports": 0,
            "high_risk_count": 0,
            "critical_risk_count": 0,
            "scores": [],
            "precursor_counts": defaultdict(int)
        })

        # Process each report in the dataset
        for _, row in df.iterrows():
            desc = str(row.get("cleaned_text", "")).strip()
            loc = str(row.get("location", "Unknown")).strip() or "Unknown"
            dept = str(row.get("industry_sector", "General Industrial")).strip() or "General Industrial"
            sev = str(row.get("severity_level", "I")).strip().upper()
            date_val = str(row.get("date_logged", "")).strip()

            if sev in sev_counts:
                sev_counts[sev] += 1
            else:
                sev_counts["I"] += 1
                sev = "I"

            sector_counts[dept] += 1

            # Run risk engine on report text
            res = self.risk_engine.analyze(desc)
            score = res["score"]
            detected_precs = [p["label"] for p in res["precursors"]]

            # Global stats
            if score >= 75:
                risk_level_dist["CRITICAL"] += 1
            elif score >= 50:
                risk_level_dist["HIGH"] += 1
            elif score >= 20:
                risk_level_dist["MEDIUM"] += 1
            else:
                risk_level_dist["LOW"] += 1

            for p_label in detected_precs:
                if p_label in global_precursor_counts:
                    global_precursor_counts[p_label] += 1

            # Location accumulation
            loc_entry = loc_data[loc]
            loc_entry["total_reports"] += 1
            loc_entry["total_score"] += score
            loc_entry["severity_dist"][sev] += 1
            if score >= 50:
                loc_entry["high_risk_reports"] += 1
            if score >= 75:
                loc_entry["critical_risk_reports"] += 1
            for p_label in detected_precs:
                loc_entry["precursor_counts"][p_label] += 1

            # Department accumulation
            dept_entry = dept_data[dept]
            dept_entry["total_reports"] += 1
            dept_entry["total_score"] += score
            dept_entry["severity_dist"][sev] += 1
            if score >= 50:
                dept_entry["high_risk_reports"] += 1
            if score >= 75:
                dept_entry["critical_risk_reports"] += 1
            for p_label in detected_precs:
                dept_entry["precursor_counts"][p_label] += 1

            # Time accumulation
            period = None
            if date_val and date_val != "Unknown" and date_val != "nan":
                try:
                    # Match YYYY-MM
                    m = re.search(r"(\d{4}[-/]\d{2})", date_val)
                    if m:
                        period = m.group(1).replace("/", "-")
                except Exception:
                    period = None

            if period:
                t_entry = time_data[period]
                t_entry["total_reports"] += 1
                t_entry["scores"].append(score)
                if score >= 50:
                    t_entry["high_risk_count"] += 1
                if score >= 75:
                    t_entry["critical_risk_count"] += 1
                for p_label in detected_precs:
                    t_entry["precursor_counts"][p_label] += 1

        # Format Location Analytics
        formatted_locations: List[Dict[str, Any]] = []
        for loc_name, data in loc_data.items():
            tot = data["total_reports"]
            hi = data["high_risk_reports"]
            crit = data["critical_risk_reports"]
            avg_sc = round(data["total_score"] / tot, 1) if tot > 0 else 0.0
            
            # Sort top recurring precursors
            sorted_precursors = sorted(
                data["precursor_counts"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            top_precs = [
                {"precursor": p_name, "count": count}
                for p_name, count in sorted_precursors[:4] if count > 0
            ]

            formatted_locations.append({
                "location": loc_name,
                "total_reports": tot,
                "high_risk_reports": hi,
                "critical_risk_reports": crit,
                "high_risk_percentage": round((hi / tot) * 100, 1) if tot > 0 else 0.0,
                "critical_risk_percentage": round((crit / tot) * 100, 1) if tot > 0 else 0.0,
                "average_risk_score": avg_sc,
                "severity_distribution": data["severity_dist"],
                "top_recurring_precursors": top_precs
            })

        # Sort locations by total reports descending
        formatted_locations.sort(key=lambda x: x["total_reports"], reverse=True)

        # Format Department/Sector Analytics
        formatted_departments: List[Dict[str, Any]] = []
        for dept_name, data in dept_data.items():
            tot = data["total_reports"]
            hi = data["high_risk_reports"]
            crit = data["critical_risk_reports"]
            avg_sc = round(data["total_score"] / tot, 1) if tot > 0 else 0.0

            sorted_precursors = sorted(
                data["precursor_counts"].items(),
                key=lambda x: x[1],
                reverse=True
            )
            top_precs = [
                {"precursor": p_name, "count": count}
                for p_name, count in sorted_precursors[:4] if count > 0
            ]

            formatted_departments.append({
                "department": dept_name,
                "industry_sector": dept_name,
                "total_reports": tot,
                "high_risk_reports": hi,
                "critical_risk_reports": crit,
                "high_risk_percentage": round((hi / tot) * 100, 1) if tot > 0 else 0.0,
                "critical_risk_percentage": round((crit / tot) * 100, 1) if tot > 0 else 0.0,
                "average_risk_score": avg_sc,
                "severity_distribution": data["severity_dist"],
                "top_recurring_precursors": top_precs
            })

        formatted_departments.sort(key=lambda x: x["total_reports"], reverse=True)

        # Format Time Trend Analytics
        formatted_trends: List[Dict[str, Any]] = []
        for period in sorted(time_data.keys()):
            t_data = time_data[period]
            tot = t_data["total_reports"]
            scores = t_data["scores"]
            avg_score = round(float(np.mean(scores)), 1) if scores else 0.0
            
            top_precursor = "None"
            if t_data["precursor_counts"]:
                top_precursor = max(t_data["precursor_counts"].items(), key=lambda x: x[1])[0]

            formatted_trends.append({
                "period": period,
                "total_reports": tot,
                "high_risk_count": t_data["high_risk_count"],
                "critical_risk_count": t_data["critical_risk_count"],
                "average_risk_score": avg_score,
                "top_precursor": top_precursor
            })

        deduped_df = self.pipeline.deduplicate_reports(df) if hasattr(self.pipeline, "deduplicate_reports") else df.drop_duplicates(subset=["cleaned_text"])

        return {
            "available": True,
            "total_reports_analyzed": total_reports,
            "unique_usable_records": len(deduped_df),
            "severity_distribution": sev_counts,
            "precursor_detection_distribution": global_precursor_counts,
            "risk_level_distribution": risk_level_dist,
            "industry_sector_distribution": dict(sector_counts),
            "retrieval_corpus_size": total_reports,
            "taxonomy_precursor_categories": len(SIF_TAXONOMY),
            "location_analytics": formatted_locations,
            "department_analytics": formatted_departments,
            "time_trend_analytics": formatted_trends
        }

    def get_operational_analytics(self) -> Dict[str, Any]:
        """Returns operational safety statistics including location, department, and temporal breakdowns."""
        if not self._cached_operational_data:
            self._cached_operational_data = self._compute_full_operational_dataset()
        return self._cached_operational_data

    def get_location_analytics(self) -> List[Dict[str, Any]]:
        """Returns location-wise safety analytics."""
        data = self.get_operational_analytics()
        return data.get("location_analytics", [])

    def get_department_analytics(self) -> List[Dict[str, Any]]:
        """Returns department/industry sector safety analytics."""
        data = self.get_operational_analytics()
        return data.get("department_analytics", [])

    def get_time_trend_analytics(self) -> List[Dict[str, Any]]:
        """Returns risk trend over time."""
        data = self.get_operational_analytics()
        return data.get("time_trend_analytics", [])

    def get_model_performance_analytics(self) -> Dict[str, Any]:
        """Returns verified, zero-leakage ML model evaluation and per-class recall metrics."""
        try:
            metrics_file = BASE_DIR / "data" / "evaluation_metrics.json"
            file_mtime = metrics_file.stat().st_mtime if metrics_file.exists() else 0

            if not hasattr(self, "_eval_metrics_mtime") or self._eval_metrics_mtime != file_mtime or self._cached_eval_metrics is None:
                if metrics_file.exists():
                    try:
                        with open(metrics_file, "r", encoding="utf-8") as f:
                            self._cached_eval_metrics = json.load(f)
                            self._eval_metrics_mtime = file_mtime
                    except Exception:
                        self._cached_eval_metrics = run_full_evaluation()
                else:
                    self._cached_eval_metrics = run_full_evaluation()

            eval_block = self._cached_eval_metrics.get("evaluation", {})
            raw_test = self._cached_eval_metrics.get("deployed_model_test_metrics", {})
            cm = self._cached_eval_metrics.get("confusion_matrix") or raw_test.get("confusion_matrix", [])
            labels = ["I", "II", "III", "IV", "V"]

            # Calculate False Positives (FP) and False Negatives (FN) per class
            cm_arr = np.array(cm)
            fp_fn_per_class = {}
            for i, cls in enumerate(labels):
                tp = int(cm_arr[i, i])
                fn = int(np.sum(cm_arr[i, :]) - tp)
                fp = int(np.sum(cm_arr[:, i]) - tp)
                tn = int(np.sum(cm_arr) - tp - fn - fp)
                support = int(np.sum(cm_arr[i, :]))
                recall = round(float(tp / support), 4) if support > 0 else 0.0
                precision = round(float(tp / (tp + fp)), 4) if (tp + fp) > 0 else 0.0
                f1 = round(float(2 * precision * recall / (precision + recall)), 4) if (precision + recall) > 0 else 0.0

                label_full_name = {
                    "I": "Level I (Minor)",
                    "II": "Level II (Moderate)",
                    "III": "Level III (Serious)",
                    "IV": "Level IV (Critical)",
                    "V": "Level V (Catastrophic)"
                }.get(cls, f"Level {cls}")

                fp_fn_per_class[cls] = {
                    "class_label": cls,
                    "name": label_full_name,
                    "true_positives": tp,
                    "false_positives": fp,
                    "false_negatives": fn,
                    "true_negatives": tn,
                    "recall": recall,
                    "precision": precision,
                    "f1_score": f1,
                    "support": support,
                    "is_safety_critical": cls in ["IV", "V"]
                }

            acc = eval_block.get("accuracy", raw_test.get("accuracy", 0.0))
            macro_p = eval_block.get("macro_precision", raw_test.get("macro_precision", 0.0))
            macro_r = eval_block.get("macro_recall", raw_test.get("macro_recall", 0.0))
            macro_f1 = eval_block.get("macro_f1", raw_test.get("macro_f1", 0.0))
            weighted_f1 = eval_block.get("weighted_f1", raw_test.get("weighted_f1", 0.0))
            holdout_size = eval_block.get("holdout_size", raw_test.get("sample_count", 62))

            return {
                "available": True,
                "model_name": self._cached_eval_metrics.get("model_name", "Calibrated Linear SVM (Platt, Balanced)"),
                "model_version": self._cached_eval_metrics.get("model_version", "v2.0.0-honest-evaluation"),
                "test_split_size": holdout_size,
                "overall_accuracy": acc,
                "macro_precision": macro_p,
                "macro_recall": macro_r,
                "macro_f1": macro_f1,
                "weighted_f1": weighted_f1,
                "per_class_metrics": fp_fn_per_class,
                "confusion_matrix": {
                    "labels": labels,
                    "matrix": cm
                },
                "benchmark_comparison": self._cached_eval_metrics.get("benchmark_comparison", {}),
                "evaluation_note": "Evaluated strictly on disjoint 15% holdout test partition (zero data leakage)."
            }
        except Exception as e:
            print(f"Warning: Failed to compute model performance analytics: {e}")
            return {
                "available": False,
                "message": "Evaluation data not available",
                "error": str(e)
            }

