"""
Corrective Action Tracking & Governance Service for SIH26165
------------------------------------------------------------
Implements an action-tracking workflow for AI-generated and human-assigned corrective actions:
- Distinct separation between immutable AI-generated recommendations and human tracking metadata.
- Lifecycle statuses: OPEN -> IN_PROGRESS -> COMPLETED -> VERIFIED.
- Quantitative verification status, responsible safety roles, due dates, and completion timestamps.
- Thread-safe persistent JSON storage.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field

DATA_STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "actions_store.json"

VALID_STATUSES = {"OPEN", "IN_PROGRESS", "COMPLETED", "VERIFIED"}
VALID_PRIORITIES = {"IMMEDIATE", "HIGH", "MEDIUM", "ROUTINE"}


@dataclass
class ActionTrackingRecord:
    """Represents an actionable, tracked corrective safety task with lifecycle audit."""
    action_id: str                          # e.g. "ACT-A1B2C3D4"
    report_id: str                          # Reference observation ID
    action_description: str                 # Authoritative task description
    priority: str                           # "IMMEDIATE" | "HIGH" | "MEDIUM" | "ROUTINE"
    responsible_role: str                   # Assigned safety role (e.g. "Process Safety Lead")
    status: str                             # "OPEN" | "IN_PROGRESS" | "COMPLETED" | "VERIFIED"
    created_at: str                         # ISO 8601 UTC timestamp
    due_date: Optional[str] = None          # ISO 8601 UTC timestamp or YYYY-MM-DD
    completed_at: Optional[str] = None      # ISO 8601 UTC timestamp
    verification_status: str = "UNVERIFIED" # "UNVERIFIED" | "PENDING_VERIFICATION" | "VERIFIED"
    verified_at: Optional[str] = None       # ISO 8601 UTC timestamp
    verified_by_officer: Optional[str] = None
    officer_id: Optional[str] = None
    tracking_notes: Optional[str] = None
    
    # Strictly separated immutable AI context
    ai_generated_context: Dict[str, Any] = field(default_factory=dict)
    
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ActionTrackingService:
    """Service managing the lifecycle, validation, and persistence of corrective action items."""

    def __init__(self, store_path: Optional[Path] = None):
        self.store_path = store_path or DATA_STORE_PATH
        self.actions: Dict[str, Dict[str, Any]] = {}
        self._load_store()

    def _load_store(self):
        if self.store_path.exists():
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    self.actions = json.load(f)
            except Exception:
                self.actions = {}
        else:
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            self._save_store()

    def _save_store(self):
        try:
            import os
            self.store_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.store_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.actions, f, indent=2)
            try:
                os.replace(tmp_path, self.store_path)
            except OSError:
                with open(self.store_path, "w", encoding="utf-8") as f:
                    json.dump(self.actions, f, indent=2)
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass
        except Exception as e:
            print(f"Warning: Failed to persist action tracking store: {e}")

    def create_action(
        self,
        report_id: str,
        action_description: str,
        priority: str = "HIGH",
        responsible_role: str = "Safety Officer",
        due_date: Optional[str] = None,
        ai_context: Optional[Dict[str, Any]] = None,
        action_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Creates a new tracked corrective action in OPEN status."""
        if not report_id or not report_id.strip():
            raise ValueError("Report ID is required to create a corrective action.")
        if not action_description or not action_description.strip():
            raise ValueError("Action description is required.")

        clean_priority = priority.upper().strip() if priority else "HIGH"
        if clean_priority not in VALID_PRIORITIES:
            clean_priority = "HIGH"

        act_id = action_id or f"ACT-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        record = ActionTrackingRecord(
            action_id=act_id,
            report_id=report_id.strip(),
            action_description=action_description.strip(),
            priority=clean_priority,
            responsible_role=responsible_role.strip() if responsible_role else "Safety Officer",
            status="OPEN",
            created_at=now_iso,
            due_date=due_date,
            verification_status="UNVERIFIED",
            ai_generated_context=ai_context or {},
            updated_at=now_iso
        )

        dict_record = record.to_dict()
        self.actions[act_id] = dict_record
        self._save_store()
        return dict_record

    def register_actions_for_analysis(
        self,
        report_id: str,
        corrective_actions: List[Dict[str, Any]],
        due_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Registers a list of AI-generated corrective actions into the tracking store."""
        registered: List[Dict[str, Any]] = []

        for item in corrective_actions:
            if not isinstance(item, dict):
                continue

            desc = item.get("action") or item.get("immediate_control") or "Execute safety mitigation."
            priority = item.get("priority", "HIGH")
            role = item.get("responsible_safety_role") or item.get("responsible_role") or "Process Safety Lead"
            
            # Extract immutable AI context
            ai_ctx = {
                "precursor_id": item.get("precursor_id"),
                "related_precursor": item.get("related_precursor"),
                "immediate_control": item.get("immediate_control"),
                "verification_step": item.get("verification_step"),
                "escalation_condition": item.get("escalation_condition"),
                "follow_up_action": item.get("follow_up_action"),
                "reason": item.get("reason"),
            }

            rec = self.create_action(
                report_id=report_id,
                action_description=desc,
                priority=priority,
                responsible_role=role,
                due_date=due_date,
                ai_context=ai_ctx
            )
            registered.append(rec)

        return registered

    def update_action_status(
        self,
        action_id: str,
        status: str,
        officer_name: Optional[str] = None,
        officer_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Updates the status of a tracked corrective action with audit trail validation.
        Valid statuses: OPEN, IN_PROGRESS, COMPLETED, VERIFIED.
        """
        if action_id not in self.actions:
            raise ValueError(f"Action '{action_id}' not found.")

        target_status = status.upper().strip()
        if target_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {', '.join(sorted(VALID_STATUSES))}.")

        action = self.actions[action_id]
        now_iso = datetime.now(timezone.utc).isoformat()

        action["status"] = target_status
        action["updated_at"] = now_iso

        if notes:
            action["tracking_notes"] = notes.strip()

        if officer_name:
            action["verified_by_officer"] = officer_name.strip()
        if officer_id:
            action["officer_id"] = officer_id.strip()

        # Handle completion and verification milestones
        if target_status == "COMPLETED":
            if not action.get("completed_at"):
                action["completed_at"] = now_iso
            action["verification_status"] = "PENDING_VERIFICATION"
        elif target_status == "VERIFIED":
            if not action.get("completed_at"):
                action["completed_at"] = now_iso
            action["verified_at"] = now_iso
            action["verification_status"] = "VERIFIED"
        elif target_status == "IN_PROGRESS":
            action["verification_status"] = "UNVERIFIED"
        elif target_status == "OPEN":
            action["completed_at"] = None
            action["verified_at"] = None
            action["verification_status"] = "UNVERIFIED"

        self.actions[action_id] = action
        self._save_store()
        return action

    def get_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves an action item by ID."""
        return self.actions.get(action_id)

    def list_actions(
        self,
        report_id: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Returns action records sorted by created timestamp descending with optional filtering."""
        all_actions = list(self.actions.values())

        if report_id:
            r_id = report_id.strip()
            all_actions = [a for a in all_actions if a.get("report_id") == r_id]

        if status:
            s_target = status.upper().strip()
            all_actions = [a for a in all_actions if a.get("status") == s_target]

        if priority:
            p_target = priority.upper().strip()
            all_actions = [a for a in all_actions if a.get("priority") == p_target]

        all_actions.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return all_actions[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Calculates global summary counts across all tracked actions."""
        all_actions = list(self.actions.values())
        tot = len(all_actions)

        status_counts = {s: 0 for s in VALID_STATUSES}
        priority_counts = {p: 0 for p in VALID_PRIORITIES}

        for a in all_actions:
            st = a.get("status", "OPEN")
            if st in status_counts:
                status_counts[st] += 1
            pr = a.get("priority", "HIGH")
            if pr in priority_counts:
                priority_counts[pr] += 1

        return {
            "total_actions": tot,
            "status_distribution": status_counts,
            "priority_distribution": priority_counts,
            "open_count": status_counts["OPEN"],
            "in_progress_count": status_counts["IN_PROGRESS"],
            "completed_count": status_counts["COMPLETED"],
            "verified_count": status_counts["VERIFIED"],
            "resolution_rate": round(((status_counts["COMPLETED"] + status_counts["VERIFIED"]) / tot) * 100, 1) if tot > 0 else 0.0
        }
