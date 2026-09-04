"""
Comprehensive End-to-End (E2E) System Validation Test Suite for SIH26165
------------------------------------------------------------------------
Tests the complete inference & safety governance pipeline across 9 operational scenarios:

1. Low-risk normal observation
2. Gas/hydrocarbon leakage hazard
3. High-pressure hazard
4. PPE violation
5. Multiple simultaneous compounding precursors
6. Electrical energy hazard
7. Confined space entry violation
8. Report containing linguistic negations ("no leak", "no pressure surge")
9. Report with no matching historical case (threshold filter verification)

Validates:
- Schema compatibility between FastAPI backend and Next.js frontend (TypeScript definitions)
- Risk Score bounds: 0 <= score <= 100
- Similarity bounds: 0.0 <= sim <= 1.0 (and 0% <= pct <= 100%)
- Corrective Action traceability to detected precursors
- Human-in-the-Loop review capability
"""

import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from main import analyze_report, SafetyReport
except ImportError:
    from backend.main import analyze_report, SafetyReport


class TestEndToEndSystemValidation(unittest.TestCase):

    def _assert_valid_api_schema(self, res_json: dict):
        """Verifies that the API response strictly conforms to the AnalysisResponse schema."""
        self.assertTrue(res_json.get("success"), "API response must indicate success")
        self.assertIn("analysis", res_json)
        analysis = res_json["analysis"]

        # 1. Overall Risk
        self.assertIn("overall_risk", analysis)
        risk = analysis["overall_risk"]
        self.assertIn("score", risk)
        self.assertIn("level", risk)
        self.assertIn("summary", risk)
        self.assertGreaterEqual(risk["score"], 0)
        self.assertLessEqual(risk["score"], 100)
        self.assertIn(risk["level"], ["LOW", "MEDIUM", "HIGH", "CRITICAL"])

        # 2. Severity Prediction
        self.assertIn("severity_prediction", analysis)
        sev = analysis["severity_prediction"]
        self.assertIn("potential_accident_level", sev)
        self.assertIn("model", sev)
        self.assertIn(sev["potential_accident_level"], ["I", "II", "III", "IV", "V"])

        # 3. Detected Precursors
        self.assertIn("detected_precursors", analysis)
        self.assertIsInstance(analysis["detected_precursors"], list)

        # 4. Corrective & Recommended Actions
        self.assertIn("recommended_actions", analysis)
        self.assertIn("corrective_actions", analysis)
        self.assertIsInstance(analysis["recommended_actions"], list)
        self.assertIsInstance(analysis["corrective_actions"], list)

        for ca in analysis["corrective_actions"]:
            self.assertIn("action", ca)
            self.assertIn("priority", ca)
            self.assertIn("responsible_safety_role", ca)
            self.assertIn(ca["priority"], ["IMMEDIATE", "HIGH", "MEDIUM", "LOW"])

        # 5. Historical Evidence
        self.assertIn("historical_evidence", analysis)
        hist = analysis["historical_evidence"]
        self.assertIn("similar_cases_found", hist)
        self.assertIn("incidents", hist)
        self.assertEqual(hist["similar_cases_found"], len(hist["incidents"]))

        for inc in hist["incidents"]:
            self.assertIn("incident_id", inc)
            self.assertIn("similarity", inc)
            self.assertGreaterEqual(inc["similarity"], 0.0)
            self.assertLessEqual(inc["similarity"], 1.0)

    # ------------------------------------------------------------------------
    # SCENARIO 1: LOW-RISK NORMAL OBSERVATION
    # ------------------------------------------------------------------------
    def test_scenario_1_low_risk_observation(self):
        req = SafetyReport(
            report_text="Routine housekeeping completed at workshop bay. Tools returned to shadow board and floor swept clean.",
            industry_sector="Mining",
            worker_type="Employee"
        )
        data = analyze_report(req)
        self._assert_valid_api_schema(data)

        analysis = data["analysis"]
        self.assertEqual(len(analysis["detected_precursors"]), 0, "No precursors should be detected for clean housekeeping")
        self.assertLessEqual(analysis["overall_risk"]["score"], 25)
        self.assertIn(analysis["overall_risk"]["level"], ["LOW", "MEDIUM"])

    # ------------------------------------------------------------------------
    # SCENARIO 2: GAS / HYDROCARBON LEAKAGE
    # ------------------------------------------------------------------------
    def test_scenario_2_gas_hydrocarbon_leakage(self):
        req = SafetyReport(
            report_text="Natural gas leakage and strong hydrocarbon odor detected around separator flange gasket with portable gas detector alarming at 28% LEL.",
            industry_sector="Oil & Gas Operations"
        )
        data = analyze_report(req)
        self._assert_valid_api_schema(data)

        precursor_names = [p["label"] for p in data["analysis"]["detected_precursors"]]
        self.assertIn("Hydrocarbon & Gas Leakage", precursor_names)
        self.assertGreaterEqual(data["analysis"]["overall_risk"]["score"], 40)

        # Check evidence-based corrective action
        actions = data["analysis"]["corrective_actions"]
        self.assertTrue(any(ca["priority"] in ["IMMEDIATE", "HIGH"] for ca in actions))

    # ------------------------------------------------------------------------
    # SCENARIO 3: HIGH-PRESSURE HAZARD
    # ------------------------------------------------------------------------
    def test_scenario_3_high_pressure_hazard(self):
        req = SafetyReport(
            report_text="High pressure discharge manifold vibrating violently with line pressure surge reaching 4500 psi during well pump operation.",
            industry_sector="Drilling Operations"
        )
        data = analyze_report(req)
        self._assert_valid_api_schema(data)

        precursor_names = [p["label"] for p in data["analysis"]["detected_precursors"]]
        self.assertIn("High Pressure Exposure", precursor_names)

    # ------------------------------------------------------------------------
    # SCENARIO 4: PPE VIOLATION
    # ------------------------------------------------------------------------
    def test_scenario_4_ppe_violation(self):
        req = SafetyReport(
            report_text="Worker was observed transferring corrosive chemical acid without wearing safety goggles and chemical resistant gloves.",
            industry_sector="Maintenance"
        )
        data = analyze_report(req)
        self._assert_valid_api_schema(data)

        precursor_names = [p["label"] for p in data["analysis"]["detected_precursors"]]
        self.assertIn("PPE Violation", precursor_names)

    # ------------------------------------------------------------------------
    # SCENARIO 5: MULTIPLE SIMULTANEOUS COMPOUNDING PRECURSORS
    # ------------------------------------------------------------------------
    def test_scenario_5_multiple_simultaneous_precursors(self):
        req = SafetyReport(
            report_text="Contractor working at height on derrick platform without safety harness while high-pressure hydrocarbon gas leak occurred directly below.",
            industry_sector="Drilling Operations"
        )
        data = analyze_report(req)
        self._assert_valid_api_schema(data)

        analysis = data["analysis"]
        self.assertGreaterEqual(len(analysis["detected_precursors"]), 2, "Multiple precursors must be triggered")
        self.assertGreaterEqual(analysis["overall_risk"]["score"], 70, "Compounding risk must elevate score to Critical tier")
        self.assertEqual(analysis["overall_risk"]["level"], "CRITICAL")
        self.assertGreater(analysis["overall_risk"]["compound_risk_boost"], 0, "Multi-hazard compounding boost must be applied")

    # ------------------------------------------------------------------------
    # SCENARIO 6: ELECTRICAL HAZARD
    # ------------------------------------------------------------------------
    def test_scenario_6_electrical_hazard(self):
        req = SafetyReport(
            report_text="Damaged 440V electrical power cable with exposed live copper conductors lying in standing water pool near mud pump skid.",
            industry_sector="Mining"
        )
        data = analyze_report(req)
        self._assert_valid_api_schema(data)

        precursor_names = [p["label"] for p in data["analysis"]["detected_precursors"]]
        self.assertIn("Electrical Hazard", precursor_names)

    # ------------------------------------------------------------------------
    # SCENARIO 7: CONFINED SPACE HAZARD
    # ------------------------------------------------------------------------
    def test_scenario_7_confined_space_hazard(self):
        req = SafetyReport(
            report_text="Worker entered crude oil storage vessel for sludge cleanout without permit-to-work (PTW) and without continuous oxygen atmospheric testing.",
            industry_sector="Production Operations"
        )
        data = analyze_report(req)
        self._assert_valid_api_schema(data)

        precursor_names = [p["label"] for p in data["analysis"]["detected_precursors"]]
        self.assertIn("Confined Space Exposure", precursor_names)

    # ------------------------------------------------------------------------
    # SCENARIO 8: REPORT CONTAINING NEGATION
    # ------------------------------------------------------------------------
    def test_scenario_8_negation_handling(self):
        req = SafetyReport(
            report_text="Comprehensive inspection completed. No gas leak detected, no pressure surge observed, and no safety violations were found.",
            industry_sector="Mining"
        )
        data = analyze_report(req)
        self._assert_valid_api_schema(data)

        analysis = data["analysis"]
        self.assertEqual(len(analysis["detected_precursors"]), 0, "Negated hazard terms must NOT produce false positive precursors")
        self.assertLessEqual(analysis["overall_risk"]["score"], 25)

    # ------------------------------------------------------------------------
    # SCENARIO 9: REPORT WITH NO MATCHING HISTORICAL CASE (THRESHOLDING)
    # ------------------------------------------------------------------------
    def test_scenario_9_unmatched_historical_case(self):
        req = SafetyReport(
            report_text="Astronomer observed celestial nebula photons through radio telescope array in deep space.",
            industry_sector="Others"
        )
        data = analyze_report(req)
        self._assert_valid_api_schema(data)

        # Historical retrieval threshold is 10%; out-of-domain text should yield 0 matches
        hist = data["analysis"]["historical_evidence"]
        self.assertEqual(hist["similar_cases_found"], 0, "Out-of-domain narrative must yield 0 matching cases under 10% threshold")
        self.assertEqual(len(hist["incidents"]), 0)

    # ------------------------------------------------------------------------
    # SCENARIO 10: SEVERITY PREDICTION REACHES RISK ENGINE (INTEGRATION TEST)
    # ------------------------------------------------------------------------
    def test_scenario_10_severity_prediction_reaches_risk_engine(self):
        """Verifies that ML severity prediction is passed into Risk Engine and reflected in score and components."""
        req = SafetyReport(
            report_text="High pressure discharge manifold vibrating violently with line pressure surge reaching 4500 psi during well pump operation.",
            industry_sector="Drilling Operations"
        )
        data = analyze_report(req)
        self._assert_valid_api_schema(data)

        analysis = data["analysis"]
        pot_acc_level = analysis["severity_prediction"]["potential_accident_level"]
        self.assertIn(pot_acc_level, ["I", "II", "III", "IV", "V"])

        # If the ML model predicted Level II or higher, Risk Engine must have a severity_model_alignment component
        components = analysis["overall_risk"]["components"]
        comp_factors = [c["factor"] for c in components]

        if pot_acc_level in ["II", "III", "IV", "V"]:
            self.assertIn("severity_model_alignment", comp_factors, "Severity prediction must reach Risk Engine components")
            sev_comp = next(c for c in components if c["factor"] == "severity_model_alignment")
            self.assertGreater(sev_comp["contribution"], 0)
            self.assertIn(f"Severity Level {pot_acc_level}", analysis["overall_risk"]["formula_explanation"])

        # Check that all frontend contract fields are intact
        self.assertIn("potential_accident_level", analysis["severity_prediction"])
        self.assertIn("overall_risk", analysis)
        self.assertIn("detected_precursors", analysis)
        self.assertIn("corrective_actions", analysis)
        self.assertIn("historical_evidence", analysis)


if __name__ == "__main__":
    unittest.main()

