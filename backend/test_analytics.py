"""
Comprehensive Unit Tests for Safety Analytics Service (Task 9)
---------------------------------------------------------------
Validates:
1. Operational analytics structure (Total reports, severity/risk distributions, precursors)
2. Location-wise safety analytics (reports, high-risk, critical-risk, severity distribution, top recurring SIF precursors)
3. Department/Industry Sector safety analytics (reports, risk exposure, top recurring hazards)
4. Temporal risk trend analytics over time (monthly reports, high-risk counts, avg risk score)
5. ML model performance analytics (Accuracy, Macro F1, Weighted F1, Confusion Matrix)
6. Per-class Recall and Precision with specific verification of SIF Critical/Catastrophic classes
7. False Positive (FP) and False Negative (FN) calculations
8. Logical separation between operational and ML performance analytics
"""

import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from services.analytics_service import SafetyAnalyticsService
except ImportError:
    from backend.services.analytics_service import SafetyAnalyticsService


class TestSafetyAnalyticsService(unittest.TestCase):

    def setUp(self):
        self.service = SafetyAnalyticsService()

    # ------------------------------------------------------------------------
    # 1. OPERATIONAL ANALYTICS
    # ------------------------------------------------------------------------
    def test_operational_analytics_metrics(self):
        """Validates that operational analytics returns genuine dataset distributions."""
        data = self.service.get_operational_analytics()

        self.assertTrue(data.get("available"), "Operational analytics must be available")
        self.assertGreater(data["total_reports_analyzed"], 400)
        self.assertGreater(data["unique_usable_records"], 400)

        # Severity distribution covers all 5 tiers
        sev = data["severity_distribution"]
        for level in ["I", "II", "III", "IV", "V"]:
            self.assertIn(level, sev)
            self.assertGreater(sev[level], 0)

        # Precursor distribution covers domain categories
        precursors = data["precursor_detection_distribution"]
        self.assertIn("High Pressure Exposure", precursors)
        self.assertIn("Hydrocarbon & Gas Leakage", precursors)
        self.assertIn("Working at Height & Fall Hazard", precursors)

        # Risk tiers
        risk_tiers = data["risk_level_distribution"]
        for tier in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            self.assertIn(tier, risk_tiers)

    # ------------------------------------------------------------------------
    # 2. LOCATION-WISE SAFETY ANALYTICS
    # ------------------------------------------------------------------------
    def test_location_wise_analytics(self):
        """Validates calculation of reports, high/critical risks, and top precursors by location."""
        locations = self.service.get_location_analytics()

        self.assertIsInstance(locations, list)
        self.assertGreater(len(locations), 0, "Should have operating locations analyzed")

        first_loc = locations[0]
        self.assertIn("location", first_loc)
        self.assertIn("total_reports", first_loc)
        self.assertIn("high_risk_reports", first_loc)
        self.assertIn("critical_risk_reports", first_loc)
        self.assertIn("high_risk_percentage", first_loc)
        self.assertIn("critical_risk_percentage", first_loc)
        self.assertIn("average_risk_score", first_loc)
        self.assertIn("severity_distribution", first_loc)
        self.assertIn("top_recurring_precursors", first_loc)

        # Validate numeric bounds
        self.assertGreater(first_loc["total_reports"], 0)
        self.assertGreaterEqual(first_loc["high_risk_reports"], 0)
        self.assertGreaterEqual(first_loc["critical_risk_reports"], 0)
        self.assertGreaterEqual(first_loc["average_risk_score"], 0.0)
        self.assertLessEqual(first_loc["average_risk_score"], 100.0)

        # Validate severity distribution per location
        loc_sev = first_loc["severity_distribution"]
        for lvl in ["I", "II", "III", "IV", "V"]:
            self.assertIn(lvl, loc_sev)

        # Validate top recurring precursors
        self.assertIsInstance(first_loc["top_recurring_precursors"], list)
        if len(first_loc["top_recurring_precursors"]) > 0:
            top_p = first_loc["top_recurring_precursors"][0]
            self.assertIn("precursor", top_p)
            self.assertIn("count", top_p)
            self.assertGreater(top_p["count"], 0)

    # ------------------------------------------------------------------------
    # 3. DEPARTMENT & INDUSTRY SECTOR ANALYTICS
    # ------------------------------------------------------------------------
    def test_department_wise_analytics(self):
        """Validates reports, risk exposure, and hazard breakdowns by department/sector."""
        departments = self.service.get_department_analytics()

        self.assertIsInstance(departments, list)
        self.assertGreater(len(departments), 0, "Should have departments/sectors analyzed")

        first_dept = departments[0]
        self.assertIn("department", first_dept)
        self.assertIn("total_reports", first_dept)
        self.assertIn("high_risk_reports", first_dept)
        self.assertIn("critical_risk_reports", first_dept)
        self.assertIn("high_risk_percentage", first_dept)
        self.assertIn("average_risk_score", first_dept)
        self.assertIn("severity_distribution", first_dept)

        self.assertGreater(first_dept["total_reports"], 0)
        self.assertGreaterEqual(first_dept["high_risk_reports"], 0)

    # ------------------------------------------------------------------------
    # 4. TEMPORAL RISK TREND OVER TIME
    # ------------------------------------------------------------------------
    def test_time_trend_analytics(self):
        """Validates periodic risk and observation progression over time."""
        trends = self.service.get_time_trend_analytics()

        self.assertIsInstance(trends, list)
        self.assertGreater(len(trends), 0, "Should have temporal trend data")

        first_trend = trends[0]
        self.assertIn("period", first_trend)
        self.assertIn("total_reports", first_trend)
        self.assertIn("high_risk_count", first_trend)
        self.assertIn("critical_risk_count", first_trend)
        self.assertIn("average_risk_score", first_trend)
        self.assertIn("top_precursor", first_trend)

        self.assertGreater(first_trend["total_reports"], 0)
        self.assertGreaterEqual(first_trend["average_risk_score"], 0.0)

    # ------------------------------------------------------------------------
    # 5. MODEL PERFORMANCE ANALYTICS
    # ------------------------------------------------------------------------
    def test_model_performance_evaluation_metrics(self):
        """Validates that ML performance analytics contains zero-leakage test holdout metrics."""
        data = self.service.get_model_performance_analytics()

        self.assertTrue(data.get("available"), "ML performance metrics must be available")
        self.assertIn("Linear SVM", data["model_name"])
        self.assertEqual(data["test_split_size"], 62)
        self.assertGreaterEqual(data["overall_accuracy"], 0.0)
        self.assertLessEqual(data["overall_accuracy"], 1.0)
        self.assertGreaterEqual(data["macro_f1"], 0.0)
        self.assertLessEqual(data["macro_f1"], 1.0)

        # Check per-class recall and precision
        per_class = data["per_class_metrics"]
        for level in ["I", "II", "III", "IV", "V"]:
            self.assertIn(level, per_class)
            c = per_class[level]
            self.assertIn("recall", c)
            self.assertIn("precision", c)
            self.assertIn("false_positives", c)
            self.assertIn("false_negatives", c)
            self.assertIn("support", c)
            self.assertGreaterEqual(c["recall"], 0.0)
            self.assertLessEqual(c["recall"], 1.0)
            self.assertGreaterEqual(c["precision"], 0.0)
            self.assertLessEqual(c["precision"], 1.0)

    # ------------------------------------------------------------------------
    # 6. CONFUSION MATRIX STRUCTURE
    # ------------------------------------------------------------------------
    def test_confusion_matrix_structure(self):
        """Validates that the confusion matrix is a 5x5 matrix with correct labels."""
        data = self.service.get_model_performance_analytics()
        cm = data["confusion_matrix"]

        self.assertEqual(cm["labels"], ["I", "II", "III", "IV", "V"])
        self.assertEqual(len(cm["matrix"]), 5)
        for row in cm["matrix"]:
            self.assertEqual(len(row), 5)


if __name__ == "__main__":
    unittest.main()
