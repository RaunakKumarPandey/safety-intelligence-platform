"""
Comprehensive Unit Tests for Oil & Gas SIF Precursor Taxonomy & Risk Engine (Task 8)
------------------------------------------------------------------------------------
Validates:
1. Complete 11-Category Taxonomy Detection:
   - SIF-001: High Pressure Exposure
   - SIF-002: Hydrocarbon & Gas Leakage
   - SIF-003: Fire / Gas Hazard
   - SIF-004: Toxic Gas (H2S) & Chemical Hazard
   - SIF-005: Working at Height & Fall Hazard
   - SIF-006: Machinery & Rotating Equipment
   - SIF-007: Confined Space Exposure
   - SIF-008: Electrical Hazard
   - SIF-009: PPE Violation
   - SIF-010: Dropped Objects & Lifting Hazard
   - SIF-011: Maintenance Activity
2. Contextual Negation Handling:
   - Direct negation prefix: "no gas leakage detected"
   - Suffix negation: "H2S was not observed"
   - Safe / mitigated state: "wearing proper full PPE", "cable isolated via LOTO"
   - Contrast: "no gas leakage detected" vs "gas leakage detected from flange"
3. Multi-Hazard Compound Synergy Escalation.
4. Explainable Scoring Attribution & Formula Breakdown.
"""

import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from services.risk_engine import RiskEngine, SIF_TAXONOMY
except ImportError:
    from backend.services.risk_engine import RiskEngine, SIF_TAXONOMY


class TestOilAndGasSIFTaxonomy(unittest.TestCase):

    def setUp(self):
        self.engine = RiskEngine()

    # ------------------------------------------------------------------------
    # 1. INDIVIDUAL PRECURSOR TAXONOMY DETECTION (ALL 11 CATEGORIES)
    # ------------------------------------------------------------------------
    def test_detect_sif_001_high_pressure(self):
        """Validates detection of SIF-001 High Pressure Exposure."""
        report = "During wellhead hydrotest, high pressure line experienced 3000 psi surge."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("high_pressure", factors)
        p = next(p for p in precursors if p["factor"] == "high_pressure")
        self.assertEqual(p["precursor_id"], "SIF-001")
        self.assertEqual(p["contribution"], 25)

    def test_detect_sif_002_hydrocarbon_leakage(self):
        """Validates detection of SIF-002 Hydrocarbon & Gas Leakage."""
        report = "Condensate leak observed dripping from separator discharge flange with hissing sound."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("leakage", factors)
        p = next(p for p in precursors if p["factor"] == "leakage")
        self.assertEqual(p["precursor_id"], "SIF-002")
        self.assertEqual(p["contribution"], 20)

    def test_detect_sif_003_fire_gas_hazard(self):
        """Validates detection of SIF-003 Fire / Gas Hazard."""
        report = "Sparks from grinding wheel entered flammable gas zone near crude storage tank."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("fire_gas", factors)
        p = next(p for p in precursors if p["factor"] == "fire_gas")
        self.assertEqual(p["precursor_id"], "SIF-003")
        self.assertEqual(p["contribution"], 25)

    def test_detect_sif_004_toxic_chemical_h2s(self):
        """Validates detection of SIF-004 Toxic Gas (H2S) & Chemical Hazard."""
        report = "Sour gas release triggered 15 ppm H2S alarm near drilling mud degassing unit."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("toxic_chemical", factors)
        p = next(p for p in precursors if p["factor"] == "toxic_chemical")
        self.assertEqual(p["precursor_id"], "SIF-004")
        self.assertEqual(p["contribution"], 25)

    def test_detect_sif_005_fall_hazard(self):
        """Validates detection of SIF-005 Working at Height & Fall Hazard."""
        report = "Derrickman was observed working at 18 meters height on monkey board without harness tie-off."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("fall_hazard", factors)
        p = next(p for p in precursors if p["factor"] == "fall_hazard")
        self.assertEqual(p["precursor_id"], "SIF-005")
        self.assertEqual(p["contribution"], 20)

    def test_detect_sif_006_machinery_rotating_equipment(self):
        """Validates detection of SIF-006 Machinery & Rotating Equipment."""
        report = "Mud pump chain drive mesh guard was removed while rotary table was running."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("machinery", factors)
        p = next(p for p in precursors if p["factor"] == "machinery")
        self.assertEqual(p["precursor_id"], "SIF-006")
        self.assertEqual(p["contribution"], 20)

    def test_detect_sif_007_confined_space(self):
        """Validates detection of SIF-007 Confined Space Exposure."""
        report = "Technician entered inside separator vessel mud pit without confined space permit."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("confined_space", factors)
        p = next(p for p in precursors if p["factor"] == "confined_space")
        self.assertEqual(p["precursor_id"], "SIF-007")
        self.assertEqual(p["contribution"], 20)

    def test_detect_sif_008_electrical_hazard(self):
        """Validates detection of SIF-008 Electrical Hazard."""
        report = "Frayed 440V electrical trailing cable was exposed in puddle of drilling water near MCC panel."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("electrical", factors)
        p = next(p for p in precursors if p["factor"] == "electrical")
        self.assertEqual(p["precursor_id"], "SIF-008")
        self.assertEqual(p["contribution"], 20)

    def test_detect_sif_009_ppe_violation(self):
        """Validates detection of SIF-009 PPE Violation."""
        report = "Contractor floorhand observed working on drill floor without safety helmet and no hearing protection."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("ppe", factors)
        p = next(p for p in precursors if p["factor"] == "ppe")
        self.assertEqual(p["precursor_id"], "SIF-009")
        self.assertEqual(p["contribution"], 15)

    def test_detect_sif_010_dropped_objects(self):
        """Validates detection of SIF-010 Dropped Objects & Lifting Hazard."""
        report = "Un-tethered heavy wrench fell from height of derrick mast to the active deck below."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("dropped_objects", factors)
        p = next(p for p in precursors if p["factor"] == "dropped_objects")
        self.assertEqual(p["precursor_id"], "SIF-010")
        self.assertEqual(p["contribution"], 20)

    def test_detect_sif_011_maintenance_activity(self):
        """Validates detection of SIF-011 Maintenance Activity."""
        report = "Crew was conducting non-routine maintenance and line breaking on crude oil manifold."
        precursors = self.engine.detect_precursors(report)
        factors = [p["factor"] for p in precursors]
        self.assertIn("maintenance", factors)
        p = next(p for p in precursors if p["factor"] == "maintenance")
        self.assertEqual(p["precursor_id"], "SIF-011")
        self.assertEqual(p["contribution"], 10)

    # ------------------------------------------------------------------------
    # 2. CONTEXTUAL NEGATION & MITIGATION HANDLING
    # ------------------------------------------------------------------------
    def test_negation_contrast_gas_leak(self):
        """Validates that 'no gas leakage detected' is NOT treated the same as 'gas leakage detected'."""
        negated_report = "Area survey completed and no gas leakage detected during routine round."
        active_report = "Gas leakage detected from high pressure flange during routine round."

        neg_precursors = self.engine.detect_precursors(negated_report)
        act_precursors = self.engine.detect_precursors(active_report)

        # Negated report must NOT detect leakage
        self.assertEqual(len(neg_precursors), 0, "'no gas leakage detected' must not trigger leakage hazard.")
        self.assertEqual(self.engine.analyze(negated_report)["score"], 0)

        # Active report MUST detect leakage
        self.assertTrue(any(p["factor"] == "leakage" for p in act_precursors))
        self.assertGreaterEqual(self.engine.analyze(active_report)["score"], 20)

    def test_mitigated_states_suppressed(self):
        """Validates that properly mitigated/isolated equipment does not trigger false hazards."""
        mitigated_reports = [
            "All workers verified wearing proper full mandatory PPE on rig floor.",
            "Prior to maintenance, the 440V electrical panel was safely isolated and de-energized via LOTO.",
            "Atmospheric testing completed with 0% LEL and zero H2S observed."
        ]

        for rep in mitigated_reports:
            res = self.engine.analyze(rep)
            self.assertEqual(res["score"], 0, f"Mitigated report '{rep}' should yield 0 score.")
            self.assertEqual(len(res["precursors"]), 0)

    # ------------------------------------------------------------------------
    # 3. COMPOUND HAZARD SYNERGY ESCALATION
    # ------------------------------------------------------------------------
    def test_compound_hazard_high_pressure_and_leak(self):
        """Validates that High Pressure + Gas Leakage triggers compound synergy boost."""
        report = "High pressure pipeline rupture released volatile hydrocarbon gas leak into compressor room."
        res = self.engine.analyze(report)

        self.assertGreater(res["compound_risk_boost"], 0)
        self.assertIn("Compound Synergy", res["formula_explanation"])
        self.assertGreaterEqual(res["score"], 55)
        self.assertIn(res["level"], ["HIGH", "CRITICAL"])

    def test_compound_hazard_confined_space_and_toxic_gas(self):
        """Validates that Confined Space + Toxic Gas triggers asphyxiation compound synergy."""
        report = "Worker entered confined space separator vessel while 20 ppm H2S toxic gas was detected."
        res = self.engine.analyze(report)

        self.assertGreater(res["compound_risk_boost"], 0)
        self.assertGreaterEqual(res["score"], 55)
        self.assertIn(res["level"], ["HIGH", "CRITICAL"])

    # ------------------------------------------------------------------------
    # 4. EXPLAINABLE ATTRIBUTION & FORMULA VERIFICATION
    # ------------------------------------------------------------------------
    def test_explainable_scoring_attribution(self):
        """Validates that scoring formula and components list provide complete transparent attribution."""
        report = "Technician working at 12m height on elevated scaffold platform near rotating mud pump chain drive."
        res = self.engine.analyze(report)

        # Height (20) + Machinery (20) = 40 (MEDIUM)
        self.assertEqual(res["score"], 40)
        self.assertEqual(res["level"], "MEDIUM")
        self.assertEqual(res["base_precursor_score"], 40)
        self.assertIn("Base Precursors (40) = 40/100", res["formula_explanation"])

        # Check structured components
        self.assertEqual(len(res["components"]), 2)
        comp_factors = [c["factor"] for c in res["components"]]
        self.assertIn("fall_hazard", comp_factors)
        self.assertIn("machinery", comp_factors)


if __name__ == "__main__":
    unittest.main()