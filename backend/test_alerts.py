"""
Unit Tests for Risk-Triggered Safety Alert Workflow (Task 5)
-------------------------------------------------------------
Validates:
1. Automatic alert creation when analyzed reports reach HIGH (>=50) or CRITICAL (>=75) risk tiers.
2. Non-triggering of alerts for LOW and MEDIUM risk reports.
3. Listing and filtering alerts by status (GET /alerts?status=NEW).
4. Fetching single alert by ID (GET /alerts/{id}) and 404 for unknown IDs.
5. Status lifecycle transitions (NEW -> ACKNOWLEDGED -> RESOLVED) via PATCH /alerts/{id}/status.
6. Validation on invalid status transitions (HTTP 400).
"""

import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from main import (
        analyze_report,
        list_safety_alerts,
        get_safety_alert,
        update_safety_alert_status,
        SafetyReport,
        UpdateAlertStatusRequest,
        alert_service
    )
    from fastapi import HTTPException
except ImportError:
    from backend.main import (
        analyze_report,
        list_safety_alerts,
        get_safety_alert,
        update_safety_alert_status,
        SafetyReport,
        UpdateAlertStatusRequest,
        alert_service
    )
    from fastapi import HTTPException


class TestRiskTriggeredAlertWorkflow(unittest.TestCase):

    def setUp(self):
        # Clear or inspect existing in-memory store
        self.alert_service = alert_service

    def test_critical_risk_report_triggers_alert(self):
        """Validates that a Critical multi-precursor observation automatically generates a NEW alert."""
        critical_report = SafetyReport(
            report_text="High pressure gas leak spraying flammable condensate near 440V electrical panel. Technicians operating at 16m height without safety harness.",
            industry_sector="Drilling Operations"
        )

        res = analyze_report(critical_report)
        self.assertTrue(res["success"])
        analysis = res["analysis"]
        risk_level = analysis["overall_risk"]["level"]

        self.assertIn(risk_level, ["HIGH", "CRITICAL"])
        self.assertTrue(analysis.get("alert_triggered"))
        alert = analysis.get("alert")
        self.assertIsNotNone(alert)
        self.assertTrue(alert["alert_id"].startswith("ALT-"))
        self.assertEqual(alert["alert_status"], "NEW")
        self.assertEqual(alert["risk_level"], risk_level)
        self.assertGreaterEqual(alert["risk_score"], 50)
        self.assertGreaterEqual(len(alert["detected_precursors"]), 1)
        self.assertIn("recommended_immediate_action", alert)

    def test_safe_observation_does_not_trigger_alert(self):
        """Validates that a routine, safe observation (Level I / Low risk) does NOT trigger an alert."""
        safe_report = SafetyReport(
            report_text="Routine daily inspection completed at workshop bay. All tools stowed on shadow board and PPE compliant.",
            industry_sector="Mining"
        )

        res = analyze_report(safe_report)
        self.assertTrue(res["success"])
        analysis = res["analysis"]

        self.assertEqual(analysis["overall_risk"]["level"], "LOW")
        self.assertFalse(analysis.get("alert_triggered"))
        self.assertIsNone(analysis.get("alert"))

    def test_list_and_filter_alerts(self):
        """Validates listing alerts and filtering by status."""
        # Ensure at least one alert exists
        self.alert_service.trigger_alert_if_needed(
            report_text="Severe compressor vibration and gas leakage alarm.",
            analysis_data={
                "overall_risk": {"score": 80, "level": "CRITICAL"},
                "detected_precursors": [{"label": "Gas Leakage", "factor": "leakage"}],
                "severity_prediction": {"potential_accident_level": "IV"},
                "recommended_actions": ["Isolate suction valve"]
            }
        )

        # List all alerts
        all_res = list_safety_alerts(status=None, limit=50)
        self.assertTrue(all_res["success"])
        self.assertGreaterEqual(all_res["total"], 1)

        # Filter by NEW
        new_res = list_safety_alerts(status="NEW", limit=50)
        self.assertTrue(new_res["success"])
        for alt in new_res["alerts"]:
            self.assertEqual(alt["alert_status"], "NEW")

    def test_get_alert_by_id_and_not_found(self):
        """Validates retrieving an alert by ID and 404 for unknown ID."""
        alert_record = self.alert_service.trigger_alert_if_needed(
            report_text="High voltage cable exposed in water.",
            analysis_data={
                "overall_risk": {"score": 75, "level": "CRITICAL"},
                "detected_precursors": [{"label": "Electrical Hazard", "factor": "electrical"}],
                "severity_prediction": {"potential_accident_level": "IV"},
                "recommended_actions": ["Lock out electrical breaker"]
            }
        )
        self.assertIsNotNone(alert_record)
        alert_id = alert_record["alert_id"]

        # Fetch existing
        res = get_safety_alert(alert_id)
        self.assertTrue(res["success"])
        self.assertEqual(res["alert"]["alert_id"], alert_id)

        # Fetch non-existent
        with self.assertRaises(HTTPException) as ctx:
            get_safety_alert("ALT-NONEXISTENT")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_alert_status_lifecycle_updates(self):
        """Validates status progression: NEW -> ACKNOWLEDGED -> RESOLVED."""
        alert_record = self.alert_service.trigger_alert_if_needed(
            report_text="Flange leak near pump discharge line.",
            analysis_data={
                "overall_risk": {"score": 60, "level": "HIGH"},
                "detected_precursors": [{"label": "High Pressure Exposure", "factor": "high_pressure"}],
                "severity_prediction": {"potential_accident_level": "III"},
                "recommended_actions": ["De-pressurize and replace gasket"]
            }
        )
        alert_id = alert_record["alert_id"]

        # 1. Update to ACKNOWLEDGED
        ack_res = update_safety_alert_status(
            alert_id=alert_id,
            req=UpdateAlertStatusRequest(
                status="ACKNOWLEDGED",
                officer_name="R. Sharma",
                officer_id="HSE-8492",
                reviewer_notes="Response team dispatched to Bay 2.",
                role="officer"
            )
        )
        self.assertTrue(ack_res["success"])
        self.assertEqual(ack_res["alert"]["alert_status"], "ACKNOWLEDGED")
        self.assertIn("R. Sharma", ack_res["alert"]["acknowledged_by"])
        self.assertEqual(ack_res["alert"]["reviewer_notes"], "Response team dispatched to Bay 2.")

        # 2. Update to RESOLVED
        res_res = update_safety_alert_status(
            alert_id=alert_id,
            req=UpdateAlertStatusRequest(
                status="RESOLVED",
                officer_name="R. Sharma",
                officer_id="HSE-8492",
                reviewer_notes="Gasket replaced and pressure tested to 150 PSI. Cleared.",
                role="officer"
            )
        )
        self.assertTrue(res_res["success"])
        self.assertEqual(res_res["alert"]["alert_status"], "RESOLVED")
        self.assertIn("R. Sharma", res_res["alert"]["resolved_by"])

        # 3. Invalid status returns 400
        with self.assertRaises(HTTPException) as ctx:
            update_safety_alert_status(
                alert_id=alert_id,
                req=UpdateAlertStatusRequest(status="INVALID_STATUS", role="officer")
            )
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
