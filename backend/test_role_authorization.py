"""
Unit Tests for Centralized Role Authorization in SIH26165 SafetyAI
-------------------------------------------------------------------
Validates strict enforcement of role authorization on officer-only operations:
- TEST 1: Employee attempt to submit/modify a review is rejected with HTTP 403 Forbidden.
- TEST 2: Employee direct attempts on officer-only endpoints (/alerts status, /actions status, /actions initiate) receive 403 Forbidden.
- TEST 3: Safety Officer submitting review with ACCEPT, MODIFY, and REJECT succeeds with full audit record.
- TEST 4: Employee read-only access to reviews, alerts, actions, and analysis is permitted (HTTP 200).
- TEST 5: Safety Officer updating action lifecycle (IN_PROGRESS -> COMPLETED -> VERIFIED) succeeds.
"""

import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from main import (
        analyze_report,
        submit_safety_review,
        list_safety_reviews,
        get_safety_review,
        list_safety_alerts,
        get_safety_alert,
        update_safety_alert_status,
        list_corrective_actions,
        get_corrective_action,
        update_corrective_action_status,
        initiate_corrective_action,
        SafetyReport,
        SafetyOfficerReviewRequest,
        UpdateAlertStatusRequest,
        UpdateActionStatusRequest,
        InitiateActionRequest,
        alert_service,
        action_service,
        review_service
    )
    from fastapi import HTTPException
except ImportError:
    from backend.main import (
        analyze_report,
        submit_safety_review,
        list_safety_reviews,
        get_safety_review,
        list_safety_alerts,
        get_safety_alert,
        update_safety_alert_status,
        list_corrective_actions,
        get_corrective_action,
        update_corrective_action_status,
        initiate_corrective_action,
        SafetyReport,
        SafetyOfficerReviewRequest,
        UpdateAlertStatusRequest,
        UpdateActionStatusRequest,
        InitiateActionRequest,
        alert_service,
        action_service,
        review_service
    )
    from fastapi import HTTPException


class TestRoleAuthorization(unittest.TestCase):

    def setUp(self):
        self.mock_ai_prediction = {
            "overall_risk": {
                "score": 60,
                "level": "HIGH",
                "summary": "Gas accumulation detected near manifold."
            },
            "severity_prediction": {
                "potential_accident_level": "IV",
                "severity_label": "Critical (Level IV)",
                "confidence": 0.85
            },
            "detected_precursors": [
                {"factor": "leakage", "label": "Gas Leakage", "contribution": 35}
            ],
            "recommended_actions": [
                "Isolate fuel gas header and purge lines immediately."
            ]
        }

    # =========================================================================
    # TEST 1: Employee cannot submit/modify safety review -> HTTP 403 Forbidden
    # =========================================================================
    def test_employee_review_submission_blocked_with_403(self):
        """Validates that employee role is strictly denied review submission with HTTP 403."""
        employee_req = SafetyOfficerReviewRequest(
            officer_name="Ramesh Kumar (Employee)",
            officer_id="EMP-4421",
            review_status="ACCEPTED",
            reviewer_comment="Employee trying to sign off review.",
            ai_prediction=self.mock_ai_prediction,
            report_id="REP-TEST-EMP1",
            role="employee"
        )

        with self.assertRaises(HTTPException) as ctx:
            submit_safety_review(employee_req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Safety Officer access required", ctx.exception.detail)

    def test_unauthenticated_or_empty_role_review_submission_blocked_with_403(self):
        """Validates that missing or non-officer role is also rejected with HTTP 403."""
        guest_req = SafetyOfficerReviewRequest(
            officer_name="Unknown User",
            officer_id="GUEST-001",
            review_status="ACCEPTED",
            reviewer_comment="Guest attempting to sign off review.",
            ai_prediction=self.mock_ai_prediction,
            report_id="REP-TEST-GUEST",
            role=""
        )

        with self.assertRaises(HTTPException) as ctx:
            submit_safety_review(guest_req)

        self.assertEqual(ctx.exception.status_code, 403)

    # =========================================================================
    # TEST 2: Employee direct attempts on officer-only endpoints receive 403
    # =========================================================================
    def test_employee_alert_status_update_blocked_with_403(self):
        """Validates that employee cannot acknowledge or resolve safety alerts."""
        # Create a test alert
        alert = alert_service.trigger_alert_if_needed(
            report_text="Hydrocarbon vapor cloud observed near separator unit.",
            analysis_data={
                "overall_risk": {"score": 70, "level": "HIGH"},
                "detected_precursors": [{"label": "Gas Leakage", "factor": "gas_leak"}],
                "severity_prediction": {"potential_accident_level": "IV"},
                "recommended_actions": ["Emergency isolation"]
            }
        )
        self.assertIsNotNone(alert)
        alert_id = alert["alert_id"]

        # Employee attempt to update alert status
        emp_req = UpdateAlertStatusRequest(
            status="RESOLVED",
            officer_name="Field Employee",
            officer_id="EMP-9001",
            reviewer_notes="Employee attempting resolution.",
            role="employee"
        )

        with self.assertRaises(HTTPException) as ctx:
            update_safety_alert_status(alert_id, emp_req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Safety Officer access required", ctx.exception.detail)

    def test_employee_action_status_update_blocked_with_403(self):
        """Validates that employee cannot modify corrective action status."""
        action = action_service.create_action(
            report_id="REP-AUTH-TEST",
            action_description="Replace degraded flange bolts on manifold."
        )
        action_id = action["action_id"]

        emp_req = UpdateActionStatusRequest(
            status="VERIFIED",
            officer_name="Field Employee",
            officer_id="EMP-9001",
            notes="Employee attempting verification.",
            role="employee"
        )

        with self.assertRaises(HTTPException) as ctx:
            update_corrective_action_status(action_id, emp_req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Safety Officer access required", ctx.exception.detail)

    def test_employee_action_initiation_blocked_with_403(self):
        """Validates that employee cannot initiate new corrective action tasks."""
        emp_req = InitiateActionRequest(
            report_id="REP-AUTH-TEST",
            action_description="Unauthorized action task",
            role="employee"
        )

        with self.assertRaises(HTTPException) as ctx:
            initiate_corrective_action(emp_req)

        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Safety Officer access required", ctx.exception.detail)

    # =========================================================================
    # TEST 2B: Missing/Omitted role on officer endpoints receives 403 (No default officer)
    # =========================================================================
    def test_omitted_role_review_submission_blocked_with_403(self):
        """Validates that omitting role parameter on review submit is rejected with HTTP 403."""
        # role not passed, defaults to None
        no_role_req = SafetyOfficerReviewRequest(
            officer_name="Anonymous Reviewer",
            officer_id="ANON-001",
            review_status="ACCEPTED",
            reviewer_comment="Attempting submission without role.",
            ai_prediction=self.mock_ai_prediction,
            report_id="REP-TEST-NOROLE"
        )
        self.assertIsNone(no_role_req.role)
        with self.assertRaises(HTTPException) as ctx:
            submit_safety_review(no_role_req)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_omitted_role_alert_status_update_blocked_with_403(self):
        """Validates that omitting role on alert status update is rejected with HTTP 403."""
        alert = alert_service.trigger_alert_if_needed(
            report_text="Hydrocarbon vapor cloud observed near separator unit.",
            analysis_data={
                "overall_risk": {"score": 70, "level": "HIGH"},
                "detected_precursors": [{"label": "Gas Leakage", "factor": "gas_leak"}],
                "severity_prediction": {"potential_accident_level": "IV"},
                "recommended_actions": ["Emergency isolation"]
            }
        )
        self.assertIsNotNone(alert)
        no_role_req = UpdateAlertStatusRequest(status="RESOLVED")
        self.assertIsNone(no_role_req.role)
        with self.assertRaises(HTTPException) as ctx:
            update_safety_alert_status(alert["alert_id"], no_role_req)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_omitted_role_action_status_update_blocked_with_403(self):
        """Validates that omitting role on action status update is rejected with HTTP 403."""
        action = action_service.create_action(
            report_id="REP-AUTH-TEST-2",
            action_description="Check emergency shutdown valves."
        )
        no_role_req = UpdateActionStatusRequest(status="COMPLETED")
        self.assertIsNone(no_role_req.role)
        with self.assertRaises(HTTPException) as ctx:
            update_corrective_action_status(action["action_id"], no_role_req)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_omitted_role_action_initiation_blocked_with_403(self):
        """Validates that omitting role on action initiate is rejected with HTTP 403."""
        no_role_req = InitiateActionRequest(
            report_id="REP-AUTH-TEST-3",
            action_description="Initiate unauthenticated inspection."
        )
        self.assertIsNone(no_role_req.role)
        with self.assertRaises(HTTPException) as ctx:
            initiate_corrective_action(no_role_req)
        self.assertEqual(ctx.exception.status_code, 403)

    # =========================================================================
    # TEST 3: Safety Officer review submit (Accept, Modify, Reject) -> All Valid
    # =========================================================================
    def test_officer_review_accept_succeeds(self):
        """Validates that Safety Officer can verify and ACCEPT AI classification."""
        officer_req = SafetyOfficerReviewRequest(
            officer_name="R. Sharma",
            officer_id="HSE-8492",
            review_status="ACCEPTED",
            reviewer_comment="Physical inspection confirmed gas seal degradation. Accepted.",
            ai_prediction=self.mock_ai_prediction,
            report_id="REP-OFFICER-001",
            role="officer"
        )

        res = submit_safety_review(officer_req)
        self.assertTrue(res["success"])
        self.assertEqual(res["record"]["officer_decision"], "ACCEPTED")
        self.assertEqual(res["record"]["final_decision"]["potential_accident_level"], "IV")

    def test_officer_review_modify_succeeds(self):
        """Validates that Safety Officer can MODIFY severity with human justification."""
        officer_req = SafetyOfficerReviewRequest(
            officer_name="R. Sharma",
            officer_id="HSE-8492",
            review_status="MODIFIED",
            reviewer_comment="Secondary valve was engaged, reducing potential severity to Level II.",
            ai_prediction=self.mock_ai_prediction,
            human_decision={
                "severity": "II",
                "risk_score": 30,
                "risk_level": "LOW",
                "precursors": ["Gas Leakage"],
                "actions": ["Re-torque secondary seal"]
            },
            report_id="REP-OFFICER-002",
            role="officer"
        )

        res = submit_safety_review(officer_req)
        self.assertTrue(res["success"])
        self.assertEqual(res["record"]["officer_decision"], "MODIFIED")
        self.assertEqual(res["record"]["final_decision"]["potential_accident_level"], "II")
        self.assertEqual(res["record"]["final_decision"]["overall_risk_score"], 30)

    def test_officer_review_reject_succeeds(self):
        """Validates that Safety Officer can REJECT false hazard classification."""
        officer_req = SafetyOfficerReviewRequest(
            officer_name="R. Sharma",
            officer_id="HSE-8492",
            review_status="REJECTED",
            reviewer_comment="Venting was scheduled routine maintenance, not an uncontrolled leak.",
            ai_prediction=self.mock_ai_prediction,
            human_decision={
                "precursors": [],
                "actions": ["Log scheduled maintenance"]
            },
            report_id="REP-OFFICER-003",
            role="officer"
        )

        res = submit_safety_review(officer_req)
        self.assertTrue(res["success"])
        self.assertEqual(res["record"]["officer_decision"], "REJECTED")

    # =========================================================================
    # TEST 4: Employee read-only endpoints and report submission allowed (HTTP 200)
    # =========================================================================
    def test_employee_can_submit_report_and_view_analysis(self):
        """Validates that an employee can submit safety reports and view AI analysis."""
        report = SafetyReport(
            report_text="Routine check: observed oil seepage around compressor seal at Bay 2.",
            industry_sector="Oil & Gas",
            worker_type="Employee",
            gender="Male",
            location="Bay 2 Compressor"
        )
        res = analyze_report(report)
        self.assertTrue(res["success"])
        self.assertIn("analysis", res)
        self.assertIn("overall_risk", res["analysis"])

    def test_employee_can_view_reviews_alerts_and_actions(self):
        """Validates that read-only access to reviews, alerts, and actions is permitted."""
        reviews_res = list_safety_reviews(limit=10)
        self.assertTrue(reviews_res["success"])
        self.assertIsInstance(reviews_res["reviews"], list)

        alerts_res = list_safety_alerts(limit=10)
        self.assertTrue(alerts_res["success"])
        self.assertIsInstance(alerts_res["alerts"], list)

        actions_res = list_corrective_actions(limit=10)
        self.assertTrue(actions_res["success"])
        self.assertIsInstance(actions_res["actions"], list)

    # =========================================================================
    # TEST 5: Safety Officer action tracking lifecycle allowed
    # =========================================================================
    def test_safety_officer_action_tracking_lifecycle(self):
        """Validates that Safety Officer can transition action through full lifecycle."""
        # 1. Initiate action
        init_req = InitiateActionRequest(
            report_id="REP-LIFECYCLE-001",
            action_description="Perform ultrasonic thickness gauging on high-pressure line.",
            priority="HIGH",
            responsible_role="NDT Inspector",
            role="officer"
        )
        init_res = initiate_corrective_action(init_req)
        self.assertTrue(init_res["success"])
        act_id = init_res["action"]["action_id"]

        # 2. Officer sets to IN_PROGRESS
        s1 = update_corrective_action_status(
            act_id,
            UpdateActionStatusRequest(
                status="IN_PROGRESS",
                officer_name="R. Sharma",
                officer_id="HSE-8492",
                notes="NDT inspection team dispatched.",
                role="officer"
            )
        )
        self.assertTrue(s1["success"])
        self.assertEqual(s1["action"]["status"], "IN_PROGRESS")

        # 3. Officer sets to COMPLETED
        s2 = update_corrective_action_status(
            act_id,
            UpdateActionStatusRequest(
                status="COMPLETED",
                officer_name="R. Sharma",
                officer_id="HSE-8492",
                notes="Ultrasonic gauging completed. Wall thickness within safe margin.",
                role="officer"
            )
        )
        self.assertTrue(s2["success"])
        self.assertEqual(s2["action"]["status"], "COMPLETED")

        # 4. Officer verifies and closes action
        s3 = update_corrective_action_status(
            act_id,
            UpdateActionStatusRequest(
                status="VERIFIED",
                officer_name="R. Sharma",
                officer_id="HSE-8492",
                notes="Authorized and closed by HSE Lead.",
                role="officer"
            )
        )
        self.assertTrue(s3["success"])
        self.assertEqual(s3["action"]["status"], "VERIFIED")
        self.assertEqual(s3["action"]["verification_status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
