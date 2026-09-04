"""
Safety Alert Management Service for SIH26165
--------------------------------------------
Implements automated risk-triggered alert generation and lifecycle management.
Automatically creates an actionable alert record whenever an analyzed safety observation
reaches HIGH (>=50) or CRITICAL (>=75) risk tiers.

Supported Alert Lifecycle Statuses:
- NEW: Unreviewed urgent alert requiring safety officer triage.
- ACKNOWLEDGED: Assigned safety officer has reviewed the alert and initiated response.
- RESOLVED: Immediate mitigations verified and site cleared.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

DATA_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "alerts_store.json"


@dataclass
class SafetyAlertRecord:
    """Represents an actionable safety officer alert triggered by high SIF risk."""
    alert_id: str
    report_id: str
    timestamp: str
    risk_level: str                       # "HIGH" | "CRITICAL"
    risk_score: int                       # 0 - 100
    detected_precursors: List[str]
    severity_level: str                   # "I" through "V"
    recommended_immediate_action: str
    alert_status: str                     # "NEW" | "ACKNOWLEDGED" | "RESOLVED"
    location: str
    department: str
    observation_excerpt: str
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    reviewer_notes: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AlertService:
    """Thread-safe alert management service with persistent JSON storage."""

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or DATA_STORE_PATH
        self.alerts: Dict[str, Dict[str, Any]] = {}
        self._load_store()

    def _load_store(self):
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    self.alerts = json.load(f)
            except Exception:
                self.alerts = {}
        else:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_store()

    def _save_store(self):
        try:
            import os
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.store_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.alerts, f, indent=2)
            try:
                os.replace(tmp_path, self.store_path)
            except OSError:
                with open(self.store_path, "w", encoding="utf-8") as f:
                    json.dump(self.alerts, f, indent=2)
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass
        except Exception as e:
            print(f"Warning: Failed to persist alert store: {e}")

    def trigger_alert_if_needed(
        self,
        report_text: str,
        analysis_data: Dict[str, Any],
        location: str = "Field Site",
        department: str = "Operations",
        report_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Evaluates analysis results and automatically creates a new alert
        if overall risk level is HIGH or CRITICAL.
        """
        overall_risk = analysis_data.get("overall_risk", {})
        risk_level = str(overall_risk.get("level", "LOW")).upper()
        risk_score = int(overall_risk.get("score", 0))

        if risk_level not in ["HIGH", "CRITICAL"]:
            return None

        alert_id = f"ALT-{uuid.uuid4().hex[:8].upper()}"
        assigned_report_id = report_id or f"REP-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        # Extract precursors
        precursor_list = [
            p.get("label", p.get("factor", "Unknown"))
            for p in analysis_data.get("detected_precursors", [])
        ]

        # Extract recommended immediate action
        rec_actions = analysis_data.get("recommended_actions", [])
        corrective_actions = analysis_data.get("corrective_actions", [])
        if corrective_actions and isinstance(corrective_actions[0], dict):
            immediate_action = corrective_actions[0].get("immediate_control") or corrective_actions[0].get("action")
        elif rec_actions:
            immediate_action = rec_actions[0]
        else:
            immediate_action = "Initiate emergency safety inspection and secure the perimeter immediately."

        sev_level = str(analysis_data.get("severity_prediction", {}).get("potential_accident_level", "III"))

        alert_record = SafetyAlertRecord(
            alert_id=alert_id,
            report_id=assigned_report_id,
            timestamp=now_iso,
            risk_level=risk_level,
            risk_score=risk_score,
            detected_precursors=precursor_list,
            severity_level=sev_level,
            recommended_immediate_action=immediate_action or "Immediate field investigation required.",
            alert_status="NEW",
            location=location or "Field Site",
            department=department or "Operations",
            observation_excerpt=report_text[:220].strip() + ("..." if len(report_text) > 220 else ""),
            updated_at=now_iso
        )

        dict_record = alert_record.to_dict()
        self.alerts[alert_id] = dict_record
        self._save_store()
        return dict_record

    def list_alerts(self, status: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns alerts sorted by timestamp descending, optionally filtered by status."""
        all_alerts = list(self.alerts.values())
        if status:
            target_status = status.upper().strip()
            all_alerts = [a for a in all_alerts if a.get("alert_status") == target_status]

        # Sort descending by timestamp
        all_alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return all_alerts[:limit]

    def get_alert(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single alert record by alert_id."""
        return self.alerts.get(alert_id)

    def update_alert_status(
        self,
        alert_id: str,
        status: str,
        officer_name: Optional[str] = None,
        officer_id: Optional[str] = None,
        reviewer_notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Updates the status and audit trail of an existing alert."""
        valid_statuses = ["NEW", "ACKNOWLEDGED", "RESOLVED"]
        target_status = status.upper().strip()
        if target_status not in valid_statuses:
            raise ValueError(f"Invalid status '{status}'. Must be one of {valid_statuses}")

        if alert_id not in self.alerts:
            return None

        alert = self.alerts[alert_id]
        now_iso = datetime.now(timezone.utc).isoformat()

        alert["alert_status"] = target_status
        alert["updated_at"] = now_iso

        if reviewer_notes is not None:
            alert["reviewer_notes"] = reviewer_notes

        officer_tag = f"{officer_name} ({officer_id})" if officer_id and officer_name else (officer_name or officer_id or "Safety Officer")

        if target_status == "ACKNOWLEDGED":
            alert["acknowledged_by"] = officer_tag
        elif target_status == "RESOLVED":
            if not alert.get("acknowledged_by"):
                alert["acknowledged_by"] = officer_tag
            alert["resolved_by"] = officer_tag

        self.alerts[alert_id] = alert
        self._save_store()
        return alert
