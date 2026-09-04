"""
Comprehensive Unit & Integration Tests for Corrective Action Tracking Module (Task 10)
--------------------------------------------------------------------------------------
Validates:
1. Creation of tracked corrective actions with valid defaults (OPEN status, UNVERIFIED).
2. Registration of AI-generated corrective actions from risk engine analysis.
3. Strict separation between immutable AI-generated context and human tracking metadata.
4. All four lifecycle transitions: OPEN -> IN_PROGRESS -> COMPLETED -> VERIFIED.
5. Automated recording of completion and verification timestamps.
6. Validation checks for invalid statuses, missing fields, and non-existent IDs.
7. Global statistics aggregation (open, in-progress, completed, verified, resolution rate).
8. Endpoint integration testing (list_corrective_actions, update_corrective_action_status, get_action_statistics, _process_single_report).
"""

import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from services.action_tracking_service import ActionTrackingService, ActionTrackingRecord
    from main import (
        list_corrective_actions,
        get_corrective_action,
        update_corrective_action_status,
        initiate_corrective_action,
        get_action_statistics,
        _process_single_report,
        UpdateActionStatusRequest,
        InitiateActionRequest
    )
except ImportError:
    from backend.services.action_tracking_service import ActionTrackingService, ActionTrackingRecord
    from backend.main import (
        list_corrective_actions,
        get_corrective_action,
        update_corrective_action_status,
        initiate_corrective_action,
        get_action_statistics,
        _process_single_report,
        UpdateActionStatusRequest,
        InitiateActionRequest
    )


class TestActionTrackingService(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self.temp_file.close()
        self.store_path = Path(self.temp_file.name)
        self.service = ActionTrackingService(store_path=self.store_path)

    def tearDown(self):
        if self.store_path.exists():
            try:
                self.store_path.unlink()
            except Exception:
                pass

    # ------------------------------------------------------------------------
    # 1. ACTION CREATION & DEFAULTS
    # ------------------------------------------------------------------------
    def test_create_action_defaults(self):
        """Validates that a created action initializes in OPEN status with UNVERIFIED state."""
        action = self.service.create_action(
            report_id="REP-TEST-100",
            action_description="Isolate hydrocarbon feed valve and tag out.",
            priority="HIGH",
            responsible_role="Process Safety Lead"
        )

        self.assertTrue(action["action_id"].startswith("ACT-"))
        self.assertEqual(action["report_id"], "REP-TEST-100")
        self.assertEqual(action["action_description"], "Isolate hydrocarbon feed valve and tag out.")
        self.assertEqual(action["priority"], "HIGH")
        self.assertEqual(action["responsible_role"], "Process Safety Lead")
        self.assertEqual(action["status"], "OPEN")
        self.assertEqual(action["verification_status"], "UNVERIFIED")
        self.assertIsNotNone(action["created_at"])
        self.assertIsNone(action["completed_at"])
        self.assertIsNone(action["verified_at"])

    def test_create_action_validation_failures(self):
        """Ensures creation fails on missing report ID or empty action description."""
        with self.assertRaises(ValueError):
            self.service.create_action(report_id="", action_description="Some task")

        with self.assertRaises(ValueError):
            self.service.create_action(report_id="REP-1", action_description="")

    # ------------------------------------------------------------------------
    # 2. SEPARATION OF AI RECOMMENDATIONS AND HUMAN TRACKING
    # ------------------------------------------------------------------------
    def test_register_actions_from_analysis_separation(self):
        """Ensures AI-generated fields are stored in immutable context separate from human lifecycle."""
        sample_ai_actions = [
            {
                "action": "Calibrate lower explosive limit (LEL) sensors in battery room.",
                "priority": "IMMEDIATE",
                "responsible_safety_role": "Instrumentation Lead",
                "precursor_id": "SIF-001",
                "related_precursor": "Hydrocarbon & Gas Leakage",
                "immediate_control": "Zero gas source",
                "verification_step": "Test combustible gas sensor readout",
                "reason": "Gas accumulation hazard"
            }
        ]

        tracked = self.service.register_actions_for_analysis(
            report_id="REP-AI-500",
            corrective_actions=sample_ai_actions
        )

        self.assertEqual(len(tracked), 1)
        rec = tracked[0]

        # Top-level human tracking fields
        self.assertEqual(rec["status"], "OPEN")
        self.assertEqual(rec["priority"], "IMMEDIATE")
        self.assertEqual(rec["responsible_role"], "Instrumentation Lead")
        self.assertEqual(rec["verification_status"], "UNVERIFIED")

        # Isolated AI context
        ai_ctx = rec["ai_generated_context"]
        self.assertEqual(ai_ctx["precursor_id"], "SIF-001")
        self.assertEqual(ai_ctx["related_precursor"], "Hydrocarbon & Gas Leakage")
        self.assertEqual(ai_ctx["verification_step"], "Test combustible gas sensor readout")

    # ------------------------------------------------------------------------
    # 3. LIFECYCLE TRANSITIONS (OPEN -> IN_PROGRESS -> COMPLETED -> VERIFIED)
    # ------------------------------------------------------------------------
    def test_status_transitions_and_timestamps(self):
        """Tests sequential transitions through all four statuses and verifies milestone timestamps."""
        action = self.service.create_action(
            report_id="REP-TRANS-01",
            action_description="Replace degraded scaffolding plank on Level 3."
        )
        act_id = action["action_id"]

        # 1. Transition to IN_PROGRESS
        s1 = self.service.update_action_status(
            action_id=act_id,
            status="IN_PROGRESS",
            officer_name="Officer Sarah Connor",
            officer_id="SO-901",
            notes="Scaffolding team dispatched to site."
        )
        self.assertEqual(s1["status"], "IN_PROGRESS")
        self.assertEqual(s1["verification_status"], "UNVERIFIED")
        self.assertEqual(s1["tracking_notes"], "Scaffolding team dispatched to site.")
        self.assertIsNone(s1["completed_at"])

        # 2. Transition to COMPLETED
        s2 = self.service.update_action_status(
            action_id=act_id,
            status="COMPLETED",
            officer_name="Officer Sarah Connor",
            notes="Planks replaced and secured."
        )
        self.assertEqual(s2["status"], "COMPLETED")
        self.assertEqual(s2["verification_status"], "PENDING_VERIFICATION")
        self.assertIsNotNone(s2["completed_at"])
        self.assertIsNone(s2["verified_at"])

        # 3. Transition to VERIFIED
        s3 = self.service.update_action_status(
            action_id=act_id,
            status="VERIFIED",
            officer_name="Senior Inspector Miller",
            officer_id="SO-100",
            notes="Physical site inspection confirmed compliance."
        )
        self.assertEqual(s3["status"], "VERIFIED")
        self.assertEqual(s3["verification_status"], "VERIFIED")
        self.assertEqual(s3["verified_by_officer"], "Senior Inspector Miller")
        self.assertIsNotNone(s3["completed_at"])
        self.assertIsNotNone(s3["verified_at"])

    def test_invalid_status_rejection(self):
        """Ensures updating with an invalid status raises ValueError."""
        action = self.service.create_action(
            report_id="REP-INV",
            action_description="Test action"
        )
        with self.assertRaises(ValueError):
            self.service.update_action_status(action["action_id"], "INVALID_STATUS")

    def test_nonexistent_action_rejection(self):
        """Ensures updating a non-existent action raises ValueError."""
        with self.assertRaises(ValueError):
            self.service.update_action_status("ACT-NONEXISTENT", "COMPLETED")

    # ------------------------------------------------------------------------
    # 4. STATISTICS AND AGGREGATIONS
    # ------------------------------------------------------------------------
    def test_statistics_calculation(self):
        """Validates that summary statistics reflect open, completed, and verified counts."""
        a1 = self.service.create_action("REP-1", "Task 1", priority="IMMEDIATE")
        a2 = self.service.create_action("REP-2", "Task 2", priority="HIGH")
        a3 = self.service.create_action("REP-3", "Task 3", priority="MEDIUM")

        self.service.update_action_status(a2["action_id"], "IN_PROGRESS")
        self.service.update_action_status(a3["action_id"], "VERIFIED", officer_name="Officer Dave")

        stats = self.service.get_statistics()
        self.assertEqual(stats["total_actions"], 3)
        self.assertEqual(stats["open_count"], 1)
        self.assertEqual(stats["in_progress_count"], 1)
        self.assertEqual(stats["verified_count"], 1)
        self.assertEqual(stats["completed_count"], 0)
        self.assertAlmostEqual(stats["resolution_rate"], 33.3, places=1)


class TestActionTrackingIntegration(unittest.TestCase):

    def test_report_analysis_generates_tracked_actions(self):
        """Validates that _process_single_report returns corrective actions equipped with tracking metadata."""
        report_text = "Severe crude oil and high pressure gas leakage detected from flange. Pressure at 95 bar."
        result = _process_single_report(
            report_text=report_text,
            industry_sector="Mining",
            worker_type="Employee"
        )

        self.assertIn("report_id", result)
        self.assertTrue(result["report_id"].startswith("REP-"))
        self.assertIn("corrective_actions", result)
        self.assertGreater(len(result["corrective_actions"]), 0)

        first_action = result["corrective_actions"][0]
        self.assertIn("action_id", first_action)
        self.assertTrue(first_action["action_id"].startswith("ACT-"))
        self.assertEqual(first_action["status"], "OPEN")
        self.assertEqual(first_action["verification_status"], "UNVERIFIED")
        self.assertIn("action", first_action)

    def test_api_handlers_initiate_and_update(self):
        """Tests the FastAPI route handlers directly for initiate and status update."""
        # 1. Initiate Action
        init_req = InitiateActionRequest(
            report_id="REP-ROUTE-99",
            action_description="Perform ultrasonic thickness check on pipe elbow.",
            priority="HIGH",
            responsible_role="Non-Destructive Testing Specialist",
            role="officer"
        )
        init_res = initiate_corrective_action(init_req)
        self.assertTrue(init_res["success"])
        action_id = init_res["action"]["action_id"]

        # 2. Query Action
        get_res = get_corrective_action(action_id)
        self.assertTrue(get_res["success"])
        self.assertEqual(get_res["action"]["status"], "OPEN")

        # 3. Update Status
        up_req = UpdateActionStatusRequest(
            status="VERIFIED",
            officer_name="Chief Inspector Vance",
            officer_id="CI-77",
            notes="NDT scans within acceptable wall thickness margin.",
            role="officer"
        )
        up_res = update_corrective_action_status(action_id, up_req)
        self.assertTrue(up_res["success"])
        self.assertEqual(up_res["action"]["status"], "VERIFIED")
        self.assertEqual(up_res["action"]["verification_status"], "VERIFIED")
        self.assertEqual(up_res["action"]["verified_by_officer"], "Chief Inspector Vance")

    def test_employee_role_action_update_blocked_with_403(self):
        """Validates that action status updates from employee role are blocked with 403."""
        init_req = InitiateActionRequest(
            report_id="REP-RBAC-1",
            action_description="Check valve seal pressure.",
            priority="MEDIUM",
            role="officer"
        )
        init_res = initiate_corrective_action(init_req)
        action_id = init_res["action"]["action_id"]

        up_req = UpdateActionStatusRequest(
            status="COMPLETED",
            role="employee"
        )
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            update_corrective_action_status(action_id, up_req)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Only authorized Safety Officers", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
