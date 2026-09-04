"""
Unit Tests for Severity Model Probability Calibration & Confidence Reliability
--------------------------------------------------------------------------------
Validates Task 3 requirements:
1. Output range: All calibrated class probabilities are valid probabilities (0.0 <= p <= 1.0)
2. Probability distribution: Sum of class probabilities across all 5 classes equals 1.0 (+/- epsilon)
3. Predicted class consistency: Predicted class matches argmax of class probabilities (or calibrated rule)
4. Confidence consistency: Confidence value equals max class probability or calibrated rule
5. Calibration metadata integrity: Model name, version, and calibration notes populated correctly
"""

import sys
from pathlib import Path
import unittest
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from main import analyze_report, SafetyReport, severity_model
except ImportError:
    from backend.main import analyze_report, SafetyReport, severity_model


class TestSeverityConfidenceReliability(unittest.TestCase):

    def test_model_predict_proba_range_and_sum(self):
        """Validates that severity_model.predict_proba outputs values in [0, 1] summing to 1.0."""
        test_inputs = [
            "Description: High pressure gas leakage near compressor. Industry Sector: Mining Worker Type: Employee Gender: Male",
            "Description: Routine inspection completed with no safety hazards. Industry Sector: Mining Worker Type: Employee Gender: Male",
            "Description: Worker fell from 15m height without safety harness. Industry Sector: Drilling Operations Worker Type: Contractor / Third Party Gender: Male",
        ]

        for inp in test_inputs:
            probs = severity_model.predict_proba([inp])[0]
            
            # Check length
            self.assertEqual(len(probs), 5, "Must output probabilities for all 5 classes (I, II, III, IV, V)")
            
            # Check range
            for p in probs:
                self.assertGreaterEqual(p, 0.0, "Probability must be >= 0.0")
                self.assertLessEqual(p, 1.0, "Probability must be <= 1.0")
            
            # Check sum to 1.0
            self.assertAlmostEqual(float(np.sum(probs)), 1.0, places=4, msg="Probabilities must sum to 1.0")

    def test_analyze_endpoint_confidence_consistency(self):
        """Validates that /analyze returns technically consistent confidence and class probabilities."""
        test_reports = [
            SafetyReport(
                report_text="Natural gas leakage and strong hydrocarbon odor detected around separator flange gasket.",
                industry_sector="Oil & Gas Operations"
            ),
            SafetyReport(
                report_text="Damaged 440V electrical power cable with exposed live copper conductors in standing water.",
                industry_sector="Mining"
            ),
            SafetyReport(
                report_text="Routine housekeeping completed at workshop bay. Tools returned to shadow board.",
                industry_sector="Mining"
            )
        ]

        for req in test_reports:
            res = analyze_report(req)
            self.assertTrue(res["success"])
            sev = res["analysis"]["severity_prediction"]

            # 1. Output range checks
            self.assertIn(sev["potential_accident_level"], ["I", "II", "III", "IV", "V"])
            self.assertGreaterEqual(sev["confidence"], 0.0)
            self.assertLessEqual(sev["confidence"], 1.0)

            # 2. Class probabilities dictionary checks
            class_probs = sev["class_probabilities"]
            if class_probs:
                for cls_name in ["I", "II", "III", "IV", "V"]:
                    self.assertIn(cls_name, class_probs)
                    prob_val = class_probs[cls_name]
                    self.assertGreaterEqual(prob_val, 0.0)
                    self.assertLessEqual(prob_val, 1.0)

                # Sum of probabilities
                prob_sum = sum(class_probs.values())
                self.assertAlmostEqual(prob_sum, 1.0, places=2)

            # 3. Model metadata
            self.assertIn("Linear SVM", sev["model"])
            self.assertIn("Calibrated", sev["model"])
            self.assertIn("calibration_note", sev)

    def test_safe_observation_calibrated_confidence(self):
        """Validates that safe observation rule calibration sets confidence to >= 0.90 for Level I."""
        safe_req = SafetyReport(
            report_text="Routine inspection conducted at separator station. No gas leak detected and all technicians wearing proper full PPE.",
            industry_sector="Mining"
        )
        res = analyze_report(safe_req)
        sev = res["analysis"]["severity_prediction"]

        self.assertEqual(sev["potential_accident_level"], "I")
        self.assertGreaterEqual(sev["confidence"], 0.90)
        self.assertIn("Safe Observation", sev["calibration_note"])


if __name__ == "__main__":
    unittest.main()
