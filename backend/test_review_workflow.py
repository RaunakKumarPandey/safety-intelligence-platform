"""
Unit Tests for Human-in-the-Loop Safety Review Workflow (Task 6)
----------------------------------------------------------------
Validates:
1. ACCEPT outcome: AI predictions are endorsed as authoritative final determination.
2. MODIFY outcome: Officer modifies severity/score/precursors with mandatory justification.
3. REJECT outcome: Officer rejects AI hazard prediction with mandatory justification.
4. Strict separation of AI prediction snapshot, human modifications, and final decision.
5. Incomplete review validation (empty officer credentials, missing comments for MODIFY/REJECT).
6. API routes (POST /review/submit, GET /reviews, GET /review/{id}).
"""

import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from main import (
        submit_safety_review,
        list_safety_reviews,
        get_safety_review,
        SafetyOfficerReviewRequest,
        review_service
    )
    from fastapi import HTTPException
except ImportError:
    from backend.main import (
        submit_safety_review,
        list_safety_reviews,
        get_safety_review,
        SafetyOfficerReviewRequest,
        review_service
    )
    from fastapi import HTTPException


class TestHumanInTheLoopReviewWorkflow(unittest.TestCase):

    def setUp(self):
        self.review_service = review_service
        self.mock_ai_prediction = {
            "overall_risk": {
                "score": 65,
                "level": "HIGH",
                "summary": "High pressure gas leakage identified."
            },
            "severity_prediction": {
                "potential_accident_level": "IV",
                "severity_label": "Critical (Level IV)",
                "confidence": 0.88
            },
            "detected_precursors": [
                {"factor": "high_pressure", "label": "High Pressure Exposure", "contribution": 35},
                {"factor": "leakage", "label": "Gas Leakage", "contribution": 30}
            ],
            "recommended_actions": [
                "Inspect and secure high-pressure equipment.",
                "Identify and isolate the source of leakage immediately."
            ]
        }

    def test_accept_review_outcome(self):
        """Validates that ACCEPT outcome endorses AI classification as final determination."""
        req = SafetyOfficerReviewRequest(
            officer_name="R. Sharma",
            officer_id="HSE-8492",
            review_status="ACCEPTED",
            reviewer_comment="Physical inspection confirmed high-pressure gas seal degradation.",
            ai_prediction=self.mock_ai_prediction,
            report_id="RPT-TEST-001",
            role="officer"
        )

        res = submit_safety_review(req)
        self.assertTrue(res["success"])
        record = res["record"]

        # Core fields verification
        self.assertTrue(record["review_id"].startswith("REV-"))
        self.assertEqual(record["report_id"], "RPT-TEST-001")
        self.assertEqual(record["officer_decision"], "ACCEPTED")
        self.assertEqual(record["ai_severity"], "IV")
        self.assertEqual(record["ai_risk_score"], 65)
        self.assertIn("High Pressure Exposure", record["detected_precursors"])
        self.assertEqual(record["officer_name"], "R. Sharma")

        # Strict layer separation verification
        self.assertEqual(record["final_decision"]["potential_accident_level"], "IV")
        self.assertEqual(record["final_decision"]["overall_risk_score"], 65)
        self.assertEqual(record["final_decision"]["overall_risk_level"], "HIGH")
        self.assertEqual(record["ai_prediction"]["severity_prediction"]["potential_accident_level"], "IV")

    def test_modify_review_outcome(self):
        """Validates that MODIFY outcome records human overrides while keeping AI snapshot intact."""
        human_mod = {
            "severity": "III",
            "risk_score": 45,
            "risk_level": "MEDIUM",
            "precursors": ["High Pressure Exposure"],
            "actions": ["Depressurize line and install safety clamp."]
        }

        req = SafetyOfficerReviewRequest(
            officer_name="A. Das",
            officer_id="HSE-1104",
            review_status="MODIFY",
            reviewer_comment="Vessel was already depressurized; downgraded severity from IV to III.",
            ai_prediction=self.mock_ai_prediction,
            human_decision=human_mod,
            report_id="RPT-TEST-002",
            role="officer"
        )

        res = submit_safety_review(req)
        self.assertTrue(res["success"])
        record = res["record"]

        self.assertEqual(record["officer_decision"], "MODIFIED")
        self.assertEqual(record["officer_modified_severity"], "III")
        self.assertEqual(record["ai_severity"], "IV")  # AI snapshot preserved
        self.assertEqual(record["ai_risk_score"], 65)

        # Final decision reflects officer modification
        self.assertEqual(record["final_decision"]["potential_accident_level"], "III")
        self.assertEqual(record["final_decision"]["overall_risk_score"], 45)
        self.assertEqual(record["final_decision"]["overall_risk_level"], "MEDIUM")
        self.assertEqual(record["final_decision"]["confirmed_precursors"], ["High Pressure Exposure"])

    def test_reject_review_outcome(self):
        """Validates that REJECT outcome marks finding as overridden with justification."""
        human_mod = {
            "severity": "I",
            "risk_score": 5,
            "risk_level": "LOW",
            "precursors": [],
            "actions": ["False alarm; sensor calibration artifact."]
        }

        req = SafetyOfficerReviewRequest(
            officer_name="V. K. Mehta",
            officer_id="HSE-9931",
            review_status="REJECT",
            reviewer_comment="Routine steam exhaust mistaken for hazardous gas leak by optical sensor.",
            ai_prediction=self.mock_ai_prediction,
            human_decision=human_mod,
            report_id="RPT-TEST-003",
            role="officer"
        )

        res = submit_safety_review(req)
        self.assertTrue(res["success"])
        record = res["record"]

        self.assertEqual(record["officer_decision"], "REJECTED")
        self.assertEqual(record["final_decision"]["potential_accident_level"], "I")
        self.assertEqual(record["final_decision"]["overall_risk_score"], 5)
        self.assertEqual(record["final_decision"]["overall_risk_level"], "LOW")
        self.assertEqual(record["ai_severity"], "IV")  # AI original snapshot preserved

    def test_validation_rejects_empty_officer_name(self):
        """Validates that reviews with blank officer name are rejected."""
        req = SafetyOfficerReviewRequest(
            officer_name="   ",
            officer_id="HSE-8492",
            review_status="ACCEPTED",
            reviewer_comment="Verified.",
            ai_prediction=self.mock_ai_prediction,
            role="officer"
        )
        with self.assertRaises(HTTPException) as ctx:
            submit_safety_review(req)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("name is required", ctx.exception.detail)

    def test_validation_rejects_empty_officer_id(self):
        """Validates that reviews with blank officer ID are rejected."""
        req = SafetyOfficerReviewRequest(
            officer_name="R. Sharma",
            officer_id="",
            review_status="ACCEPTED",
            reviewer_comment="Verified.",
            ai_prediction=self.mock_ai_prediction,
            role="officer"
        )
        with self.assertRaises(HTTPException) as ctx:
            submit_safety_review(req)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("badge number is required", ctx.exception.detail)

    def test_validation_requires_comment_on_modify(self):
        """Validates that MODIFY review without comments is rejected."""
        req = SafetyOfficerReviewRequest(
            officer_name="R. Sharma",
            officer_id="HSE-8492",
            review_status="MODIFIED",
            reviewer_comment="  ",
            ai_prediction=self.mock_ai_prediction,
            human_decision={"severity": "II"},
            role="officer"
        )
        with self.assertRaises(HTTPException) as ctx:
            submit_safety_review(req)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("comment is required", ctx.exception.detail)

    def test_validation_requires_comment_on_reject(self):
        """Validates that REJECT review without comments is rejected."""
        req = SafetyOfficerReviewRequest(
            officer_name="R. Sharma",
            officer_id="HSE-8492",
            review_status="REJECTED",
            reviewer_comment="",
            ai_prediction=self.mock_ai_prediction,
            role="officer"
        )
        with self.assertRaises(HTTPException) as ctx:
            submit_safety_review(req)
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("comment is required", ctx.exception.detail)

    def test_list_and_get_reviews(self):
        """Validates listing and retrieving archived review audit records."""
        # Submit a record
        res = submit_safety_review(SafetyOfficerReviewRequest(
            officer_name="R. Sharma",
            officer_id="HSE-8492",
            review_status="ACCEPTED",
            reviewer_comment="Audit listing check.",
            ai_prediction=self.mock_ai_prediction,
            role="officer"
        ))
        review_id = res["record"]["review_id"]

        # List reviews
        list_res = list_safety_reviews(limit=20)
        self.assertTrue(list_res["success"])
        self.assertGreaterEqual(list_res["total"], 1)

        # Get review by ID
        get_res = get_safety_review(review_id)
        self.assertTrue(get_res["success"])
        self.assertEqual(get_res["record"]["review_id"], review_id)

    def test_employee_role_review_submission_blocked_with_403(self):
        """Validates that reviews submitted with employee role return HTTP 403 Forbidden."""
        req = SafetyOfficerReviewRequest(
            officer_name="Field Employee",
            officer_id="EMP-1001",
            review_status="ACCEPTED",
            reviewer_comment="Employee trying to submit review.",
            ai_prediction=self.mock_ai_prediction,
            role="employee"
        )
        with self.assertRaises(HTTPException) as ctx:
            submit_safety_review(req)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Only authorized Safety Officers", ctx.exception.detail)

    def test_officer_role_review_submission_allowed(self):
        """Validates that reviews submitted with officer role succeed."""
        req = SafetyOfficerReviewRequest(
            officer_name="R. Sharma",
            officer_id="HSE-8492",
            review_status="ACCEPTED",
            reviewer_comment="Officer review verified.",
            ai_prediction=self.mock_ai_prediction,
            role="officer"
        )
        res = submit_safety_review(req)
        self.assertTrue(res["success"])
        self.assertIn("record", res)


if __name__ == "__main__":
    unittest.main()
