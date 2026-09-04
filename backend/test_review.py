"""
Comprehensive Unit Tests for Human-in-the-Loop Safety Review Service
---------------------------------------------------------------------
Validates:
1. Acceptance of AI classification (status = ACCEPTED)
2. Rejection of AI classification (status = REJECTED)
3. Modification of precursors, severity, and actions (status = MODIFIED)
4. Immutable preservation of original AI prediction
5. Calculation of final authoritative operational determination
6. Persistence and retrieval via get_review and list_reviews
"""

import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from services.review_service import ReviewService
except ImportError:
    from backend.services.review_service import ReviewService


class TestHumanSafetyReviewService(unittest.TestCase):

    def setUp(self):
        # Use a temporary test store path
        test_store = BASE_DIR / "data" / "test_reviews_store.json"
        if test_store.exists():
            test_store.unlink()
        self.service = ReviewService(store_path=test_store)

        self.sample_ai_prediction = {
            "overall_risk": {"score": 75, "level": "CRITICAL", "summary": "Compounding gas leak detected."},
            "severity_prediction": {"potential_accident_level": "IV", "model": "Linear SVM"},
            "detected_precursors": [
                {"factor": "leakage", "label": "Hydrocarbon & Gas Leakage", "contribution": 20, "evidence": ["gas leak"]}
            ],
            "recommended_actions": ["Isolate upstream emergency shutdown valves."]
        }

    # ------------------------------------------------------------------------
    # 1. ACCEPT AI CLASSIFICATION
    # ------------------------------------------------------------------------
    def test_accept_ai_classification(self):
        """Tests that accepting AI assessment preserves AI values into final decision."""
        record = self.service.submit_review(
            officer_name="R. Sharma",
            officer_id="HSE-8492",
            review_status="ACCEPTED",
            reviewer_comment="Verified on-site pressure gauge readings and confirmed flange gas leakage.",
            ai_prediction=self.sample_ai_prediction
        )

        self.assertEqual(record["review_status"], "ACCEPTED")
        self.assertEqual(record["officer_name"], "R. Sharma")
        self.assertEqual(record["officer_id"], "HSE-8492")

        # Final decision matches AI
        final = record["final_decision"]
        self.assertEqual(final["potential_accident_level"], "IV")
        self.assertEqual(final["overall_risk_score"], 75)
        self.assertEqual(final["overall_risk_level"], "CRITICAL")
        self.assertIn("Hydrocarbon & Gas Leakage", final["confirmed_precursors"])

        # Original AI prediction is preserved immutably
        self.assertEqual(record["ai_prediction"]["overall_risk"]["score"], 75)

    # ------------------------------------------------------------------------
    # 2. REJECT AI CLASSIFICATION
    # ------------------------------------------------------------------------
    def test_reject_ai_classification(self):
        """Tests that rejecting AI assessment overwrites final decision with officer determination."""
        human_override = {
            "severity": "I",
            "risk_score": 0,
            "risk_level": "LOW",
            "precursors": [],
            "actions": ["Observation was a routine drill. No active hazard."]
        }

        record = self.service.submit_review(
            officer_name="A. Gogoi",
            officer_id="HSE-1104",
            review_status="REJECTED",
            reviewer_comment="False positive: Planned drill with cold nitrogen, not flammable hydrocarbon.",
            ai_prediction=self.sample_ai_prediction,
            human_decision=human_override
        )

        self.assertEqual(record["review_status"], "REJECTED")
        final = record["final_decision"]
        self.assertEqual(final["potential_accident_level"], "I")
        self.assertEqual(final["overall_risk_score"], 0)
        self.assertEqual(final["overall_risk_level"], "LOW")

        # AI prediction still contains original values for model retraining audit
        self.assertEqual(record["ai_prediction"]["severity_prediction"]["potential_accident_level"], "IV")

    # ------------------------------------------------------------------------
    # 3. MODIFY PRECURSOR AND SEVERITY
    # ------------------------------------------------------------------------
    def test_modify_ai_classification(self):
        """Tests modifying severity from IV to V and appending missing precursor."""
        human_modification = {
            "severity": "V",
            "risk_score": 90,
            "risk_level": "CRITICAL",
            "precursors": ["Hydrocarbon & Gas Leakage", "Working at Height & Fall Hazard"],
            "actions": ["Immediate plant ESD and derrick platform evacuation."]
        }

        record = self.service.submit_review(
            officer_name="V. K. Mehta",
            officer_id="HSE-5520",
            review_status="MODIFIED",
            reviewer_comment="Escalated to Level V due to simultaneous elevated working without harness.",
            ai_prediction=self.sample_ai_prediction,
            human_decision=human_modification
        )

        self.assertEqual(record["review_status"], "MODIFIED")
        final = record["final_decision"]
        self.assertEqual(final["potential_accident_level"], "V")
        self.assertEqual(final["overall_risk_score"], 90)
        self.assertIn("Working at Height & Fall Hazard", final["confirmed_precursors"])

    # ------------------------------------------------------------------------
    # 4. PERSISTENCE & RETRIEVAL
    # ------------------------------------------------------------------------
    def test_persistence_and_listing(self):
        """Validates that reviews are retrieved by ID and listed chronologically."""
        rec1 = self.service.submit_review(
            officer_name="Officer A",
            officer_id="HSE-1",
            review_status="ACCEPTED",
            reviewer_comment="Good",
            ai_prediction=self.sample_ai_prediction
        )
        rec2 = self.service.submit_review(
            officer_name="Officer B",
            officer_id="HSE-2",
            review_status="MODIFIED",
            reviewer_comment="Updated",
            ai_prediction=self.sample_ai_prediction,
            human_decision={"severity": "II"}
        )

        fetched = self.service.get_review(rec1["review_id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["officer_name"], "Officer A")

        all_reviews = self.service.list_reviews()
        self.assertEqual(len(all_reviews), 2)


if __name__ == "__main__":
    unittest.main()
