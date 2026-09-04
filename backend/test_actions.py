"""
Comprehensive Unit Tests for Evidence-Based Corrective Action Generation
------------------------------------------------------------------------
Validates:
1. Structured action schema: { action, priority, reason, related_precursor }
2. Traceability: action reason directly links to detected hazard evidence
3. Hierarchy of controls & role assignment:
   - Gas Leakage -> Isolate source, verify 0% LEL, Area HSE Officer
   - High Pressure -> Stop operation, depressurize, Process Safety Lead
   - PPE Non-Compliance -> Stop unsafe activity, supervisor verification
4. Priority classification: IMMEDIATE, HIGH, MEDIUM
5. Multi-hazard compound emergency coordination actions
6. Human Safety Officer in the decision loop (requires_human_approval == True)
"""

import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from services.risk_engine import RiskEngine
except ImportError:
    from backend.services.risk_engine import RiskEngine


class TestEvidenceBasedCorrectiveActions(unittest.TestCase):

    def setUp(self):
        self.engine = RiskEngine()

    # ------------------------------------------------------------------------
    # 1. GAS / HYDROCARBON LEAKAGE ACTION
    # ------------------------------------------------------------------------
    def test_gas_leakage_corrective_action(self):
        """Tests that gas leak generates immediate isolation, LEL verification, and HSE role."""
        report = "During morning shift, gas leak detected on flange joint at compressor station."
        res = self.engine.analyze(report)

        actions = res.get("corrective_actions", [])
        self.assertGreater(len(actions), 0)

        leak_act = next((a for a in actions if a["related_precursor"] == "Hydrocarbon & Gas Leakage"), None)
        self.assertIsNotNone(leak_act, "Must generate action for Hydrocarbon & Gas Leakage")

        # Schema & Priority
        self.assertEqual(leak_act["priority"], "IMMEDIATE")
        self.assertIn("gas leak", leak_act["reason"].lower())

        # Action Steps
        self.assertIn("isolate", leak_act["immediate_control"].lower())
        self.assertIn("0% lel", leak_act["verification_step"].lower())
        self.assertIn("hse", leak_act["responsible_safety_role"].lower())
        self.assertTrue(leak_act["requires_human_approval"])

    # ------------------------------------------------------------------------
    # 2. HIGH PRESSURE EXPOSURE ACTION
    # ------------------------------------------------------------------------
    def test_high_pressure_corrective_action(self):
        """Tests that high pressure hazard generates depressurization and zero-energy verification."""
        report = "High pressure testing line vibrating excessively with 5000 psi pressure surge."
        res = self.engine.analyze(report)

        actions = res.get("corrective_actions", [])
        hp_act = next((a for a in actions if a["related_precursor"] == "High Pressure Exposure"), None)
        self.assertIsNotNone(hp_act, "Must generate action for High Pressure Exposure")

        self.assertEqual(hp_act["priority"], "IMMEDIATE")
        self.assertIn("depressurize", hp_act["immediate_control"].lower())
        self.assertIn("zero stored energy", hp_act["verification_step"].lower())
        self.assertIn("process safety", hp_act["responsible_safety_role"].lower())
        self.assertTrue(hp_act["requires_human_approval"])

    # ------------------------------------------------------------------------
    # 3. PPE NON-COMPLIANCE ACTION
    # ------------------------------------------------------------------------
    def test_ppe_non_compliance_corrective_action(self):
        """Tests that missing PPE generates Stop-Work, gear provision, and supervisor verification."""
        report = "Worker was not wearing hearing protection near compressor unit during operation."
        res = self.engine.analyze(report)

        actions = res.get("corrective_actions", [])
        ppe_act = next((a for a in actions if a["related_precursor"] == "PPE Violation"), None)
        self.assertIsNotNone(ppe_act, "Must generate action for PPE Violation")

        self.assertEqual(ppe_act["priority"], "MEDIUM")
        self.assertIn("stop unsafe work", ppe_act["immediate_control"].lower())
        self.assertIn("supervisor", ppe_act["verification_step"].lower())
        self.assertIn("supervisor", ppe_act["responsible_safety_role"].lower())
        self.assertTrue(ppe_act["requires_human_approval"])

    # ------------------------------------------------------------------------
    # 4. STRUCTURED SCHEMA VALIDATION
    # ------------------------------------------------------------------------
    def test_structured_action_schema(self):
        """Validates that every generated corrective action strictly conforms to the required fields."""
        report = "Uninsulated 440V electrical power cable submerged in pool of drilling fluid."
        res = self.engine.analyze(report)

        actions = res.get("corrective_actions", [])
        self.assertGreater(len(actions), 0)

        for act in actions:
            # Required top-level keys
            self.assertIn("action", act)
            self.assertIn("priority", act)
            self.assertIn("reason", act)
            self.assertIn("related_precursor", act)

            # Prescriptive metadata
            self.assertIn("immediate_control", act)
            self.assertIn("verification_step", act)
            self.assertIn("responsible_safety_role", act)
            self.assertIn("escalation_condition", act)
            self.assertIn("follow_up_action", act)
            self.assertIn("requires_human_approval", act)

            # Priority range
            self.assertIn(act["priority"], ["IMMEDIATE", "HIGH", "MEDIUM", "ROUTINE"])
            self.assertTrue(act["requires_human_approval"], "Safety officer must always be in loop")

    # ------------------------------------------------------------------------
    # 5. MULTI-HAZARD COMPOUND EMERGENCY ACTION
    # ------------------------------------------------------------------------
    def test_multi_hazard_compound_emergency_action(self):
        """Tests that compound multi-hazard generates an immediate emergency coordination action."""
        report = "High pressure pipeline vibrating with natural gas hissing and leaking from valve."
        res = self.engine.analyze(report)

        actions = res.get("corrective_actions", [])
        self.assertGreater(len(actions), 1)

        # First action should be the emergency coordination action
        first_act = actions[0]
        self.assertEqual(first_act["priority"], "IMMEDIATE")
        self.assertEqual(first_act["related_precursor"], "Multi-Hazard Compounding Interaction")
        self.assertIn("emergency coordination", first_act["action"].lower())


if __name__ == "__main__":
    unittest.main()
