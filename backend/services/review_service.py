"""
Human-in-the-Loop Safety Review Service for SIH26165
---------------------------------------------------
Maintains strict, audited separation between:
1. AI Model Predictions (Preliminary Decision Support Snapshot)
2. Safety Officer Modifications (Human Overrides & Justifications)
3. Final Authoritative Determination (Operational Ground Truth)

Provides validation to prevent incomplete submissions and full compliance audit trails.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

DATA_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "reviews_store.json"


@dataclass
class SafetyReviewRecord:
    """Complete audit record representing a human safety officer's authoritative review."""
    review_id: str
    report_id: str
    timestamp: str

    # Core required snapshot fields
    ai_severity: str
    ai_risk_score: int
    detected_precursors: List[str]
    recommended_actions: List[str]

    officer_name: str
    officer_id: str
    officer_decision: str                # "ACCEPTED" | "MODIFIED" | "REJECTED"
    officer_modified_severity: Optional[str]
    officer_comments: str

    # Structured Separation Layers
    ai_prediction: Dict[str, Any]
    human_decision: Dict[str, Any]
    final_decision: Dict[str, Any]

    # Legacy alias for backward compatibility
    review_status: str = ""
    reviewer_comment: str = ""

    def __post_init__(self):
        if not self.review_status:
            self.review_status = self.officer_decision
        if not self.reviewer_comment:
            self.reviewer_comment = self.officer_comments

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ReviewService:
    """Thread-safe review management service with JSON file persistence."""

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or DATA_STORE_PATH
        self.reviews: Dict[str, Dict[str, Any]] = {}
        self._load_store()

    def _load_store(self):
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    self.reviews = json.load(f)
            except Exception:
                self.reviews = {}
        else:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_store()

    def _save_store(self):
        try:
            import os
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.store_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.reviews, f, indent=2)
            try:
                os.replace(tmp_path, self.store_path)
            except OSError:
                with open(self.store_path, "w", encoding="utf-8") as f:
                    json.dump(self.reviews, f, indent=2)
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass
        except Exception as e:
            print(f"Warning: Failed to persist review store: {e}")

    def submit_review(
        self,
        officer_name: str,
        officer_id: str,
        review_status: str,
        reviewer_comment: str,
        ai_prediction: Dict[str, Any],
        human_decision: Optional[Dict[str, Any]] = None,
        report_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validates and archives a safety officer's authoritative review decision.
        Enforces validation rules:
        - officer_name and officer_id are required.
        - ai_prediction is required.
        - review_status must be ACCEPT / ACCEPTED, MODIFY / MODIFIED, or REJECT / REJECTED.
        - When MODIFY or REJECT is selected, a non-empty reviewer_comment is strictly required.
        """
        # 1. Validate Officer Credentials
        if not officer_name or not str(officer_name).strip():
            raise ValueError("Safety officer name is required to submit a review.")
        if not officer_id or not str(officer_id).strip():
            raise ValueError("Safety officer ID/badge number is required to submit a review.")

        # 2. Validate AI Prediction Presence
        if not ai_prediction or not isinstance(ai_prediction, dict):
            raise ValueError("Valid AI prediction payload is required for human-in-the-loop review.")

        # 3. Normalize Status
        raw_status = str(review_status).upper().strip()
        if raw_status in ["ACCEPT", "ACCEPTED"]:
            normalized_status = "ACCEPTED"
        elif raw_status in ["MODIFY", "MODIFIED"]:
            normalized_status = "MODIFIED"
        elif raw_status in ["REJECT", "REJECTED"]:
            normalized_status = "REJECTED"
        else:
            raise ValueError(f"Invalid review status '{review_status}'. Must be ACCEPTED, MODIFIED, or REJECTED.")

        # 4. Enforce Justification Requirement on Modification or Rejection
        clean_comment = str(reviewer_comment).strip() if reviewer_comment else ""
        if normalized_status in ["MODIFIED", "REJECTED"] and len(clean_comment) < 3:
            raise ValueError(
                f"Officer justification comment is required when {normalized_status} the AI prediction."
            )

        if not clean_comment and normalized_status == "ACCEPTED":
            clean_comment = "AI preliminary classification verified and accepted by Safety Officer."

        review_id = f"REV-{uuid.uuid4().hex[:8].upper()}"
        assigned_report_id = report_id or f"RPT-{uuid.uuid4().hex[:6].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()
        human_mod = human_decision or {}

        # 5. Extract AI Snapshot Elements
        ai_severity = str(
            ai_prediction.get("severity_prediction", {}).get("potential_accident_level")
            or ai_prediction.get("severity_level")
            or "I"
        )
        ai_risk_score = int(
            ai_prediction.get("overall_risk", {}).get("score")
            or ai_prediction.get("risk_score")
            or 0
        )
        ai_precursors = [
            p.get("label", p.get("factor", "Unknown"))
            if isinstance(p, dict) else str(p)
            for p in ai_prediction.get("detected_precursors", [])
        ]
        ai_actions = list(ai_prediction.get("recommended_actions", []))

        # 6. Compute Separate Final Authoritative Determination
        if normalized_status == "ACCEPTED":
            final_severity = ai_severity
            final_risk_score = ai_risk_score
            final_risk_level = ai_prediction.get("overall_risk", {}).get("level", "LOW")
            final_precursors = ai_precursors
            final_actions = ai_actions
            officer_mod_sev = None
        elif normalized_status == "REJECTED":
            final_severity = str(human_mod.get("severity", "I"))
            final_risk_score = int(human_mod.get("risk_score", 0))
            final_risk_level = str(human_mod.get("risk_level", "LOW"))
            final_precursors = list(human_mod.get("precursors", []))
            final_actions = list(human_mod.get("actions", ["Observation marked as false positive / non-hazardous by Safety Officer."]))
            officer_mod_sev = final_severity
        else:  # MODIFIED
            final_severity = str(human_mod.get("severity", ai_severity))
            final_risk_score = int(human_mod.get("risk_score", ai_risk_score))
            final_risk_level = str(human_mod.get("risk_level", ai_prediction.get("overall_risk", {}).get("level", "LOW")))
            final_precursors = list(human_mod.get("precursors", ai_precursors))
            final_actions = list(human_mod.get("actions", ai_actions))
            officer_mod_sev = final_severity

        final_decision = {
            "potential_accident_level": final_severity,
            "overall_risk_score": final_risk_score,
            "overall_risk_level": final_risk_level,
            "confirmed_precursors": final_precursors,
            "authorized_corrective_actions": final_actions,
            "review_status": normalized_status,
            "verified_by_officer": officer_name,
            "officer_id": officer_id,
            "verification_timestamp": now_iso
        }

        record = SafetyReviewRecord(
            review_id=review_id,
            report_id=assigned_report_id,
            timestamp=now_iso,
            ai_severity=ai_severity,
            ai_risk_score=ai_risk_score,
            detected_precursors=ai_precursors,
            recommended_actions=ai_actions,
            officer_name=officer_name,
            officer_id=officer_id,
            officer_decision=normalized_status,
            officer_modified_severity=officer_mod_sev,
            officer_comments=clean_comment,
            ai_prediction=ai_prediction,
            human_decision=human_mod,
            final_decision=final_decision,
            review_status=normalized_status,
            reviewer_comment=clean_comment
        )

        record_dict = record.to_dict()
        self.reviews[review_id] = record_dict
        self._save_store()

        return record_dict

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an archived review audit record by ID."""
        return self.reviews.get(review_id)

    def list_reviews(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Lists archived review audit records sorted descending by timestamp."""
        all_reviews = list(self.reviews.values())
        all_reviews.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
        return all_reviews[:limit]
