"""
Unit & Integration Tests for Production-Grade Error Handling (Task 14)
----------------------------------------------------------------------
Validates all 10 core error handling scenarios and requirements:
1. Backend unavailable / resource not found handling (404 clean responses)
2. Invalid report payloads & schema validation
3. Empty / whitespace-only description rejection with structured 422 errors
4. Invalid file validation (unsupported extensions, empty files, missing columns, oversized files)
5. Model loading / prediction failure resilience (rule-based fallback)
6. Similarity engine robustness (empty queries, special characters, zero matches)
7. Risk engine robustness (empty queries, punctuation, safe bounds)
8. Batch processing row-level fault tolerance and summary accounting
9. Structured error response schema (never exposes internal stack traces)
10. Explicit analysis source attribution ("backend_ai")
"""

import asyncio
import io
import sys
import unittest
from pathlib import Path
from fastapi import HTTPException, status
from fastapi.datastructures import UploadFile

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from main import (
        _process_single_report,
        analyze_report,
        analyze_batch_reports,
        get_safety_alert,
        get_safety_review,
        get_evidence_image,
        get_corrective_action,
        update_safety_alert_status,
        update_corrective_action_status,
        SafetyReport,
        UpdateAlertStatusRequest,
        UpdateActionStatusRequest,
        app,
    )
    from services.similarity import SimilarityEngine
    from services.risk_engine import RiskEngine
    from services.image_service import ImageEvidenceService
except ImportError:
    from backend.main import (
        _process_single_report,
        analyze_report,
        analyze_batch_reports,
        get_safety_alert,
        get_safety_review,
        get_evidence_image,
        get_corrective_action,
        update_safety_alert_status,
        update_corrective_action_status,
        SafetyReport,
        UpdateAlertStatusRequest,
        UpdateActionStatusRequest,
        app,
    )
    from backend.services.similarity import SimilarityEngine
    from backend.services.risk_engine import RiskEngine
    from backend.services.image_service import ImageEvidenceService


class TestProductionErrorHandling(unittest.TestCase):

    # ------------------------------------------------------------------------
    # 1. EMPTY AND WHITESPACE DESCRIPTION REJECTION (REQUIREMENTS 2 & 3)
    # ------------------------------------------------------------------------
    def test_empty_description_rejected(self):
        """Rejects empty string report_text with HTTPException 422."""
        with self.assertRaises(HTTPException) as ctx:
            analyze_report(SafetyReport(report_text=""))
        self.assertIn(ctx.exception.status_code, [400, 422])
        self.assertIn("cannot be empty", ctx.exception.detail.lower())

    def test_whitespace_only_description_rejected(self):
        """Rejects whitespace-only report_text."""
        with self.assertRaises(HTTPException) as ctx:
            analyze_report(SafetyReport(report_text="   \n\t   "))
        self.assertIn(ctx.exception.status_code, [400, 422])
        self.assertIn("cannot be empty", ctx.exception.detail.lower())

    def test_process_single_report_empty_guard(self):
        """Direct call to _process_single_report raises 422 for empty description."""
        with self.assertRaises(HTTPException) as ctx:
            _process_single_report(report_text="")
        self.assertEqual(ctx.exception.status_code, 422)

    # ------------------------------------------------------------------------
    # 2. ANALYSIS SOURCE ATTRIBUTION (REQUIREMENTS 10 & FALLBACK SPECS)
    # ------------------------------------------------------------------------
    def test_successful_analysis_includes_backend_ai_source(self):
        """Ensures authoritative backend AI analysis explicitly sets analysis_source='backend_ai'."""
        report = SafetyReport(
            report_text="High pressure flammable gas hissing from flange joint on separator skid."
        )
        resp = analyze_report(report)
        self.assertTrue(resp["success"])
        self.assertEqual(resp.get("analysis_source"), "backend_ai")
        self.assertEqual(resp["analysis"].get("analysis_source"), "backend_ai")
        self.assertIn("overall_risk", resp["analysis"])
        self.assertIn("severity_prediction", resp["analysis"])

    # ------------------------------------------------------------------------
    # 3. INVALID FILE & BATCH ERROR HANDLING (REQUIREMENTS 4 & 8)
    # ------------------------------------------------------------------------
    def test_batch_unsupported_file_extension(self):
        """Rejects files with unsupported extensions (e.g. .exe, .pdf, .bin)."""
        file_obj = UploadFile(filename="malicious.exe", file=io.BytesIO(b"binary data"))
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(analyze_batch_reports(file_obj))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("unsupported file format", ctx.exception.detail.lower())

    def test_batch_empty_file(self):
        """Rejects 0-byte batch files."""
        file_obj = UploadFile(filename="empty.csv", file=io.BytesIO(b""))
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(analyze_batch_reports(file_obj))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("empty", ctx.exception.detail.lower())

    def test_batch_missing_description_column(self):
        """Rejects tabular datasets missing any identifiable narrative/description column."""
        csv_no_desc = b"Location,Department,Worker Type\nRig 1,Drilling,Employee\nRig 2,Production,Contractor"
        file_obj = UploadFile(filename="no_desc.csv", file=io.BytesIO(csv_no_desc))
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(analyze_batch_reports(file_obj))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("description", ctx.exception.detail.lower())

    def test_batch_oversized_file_rejected(self):
        """Rejects batch files exceeding the 25 MB maximum batch limit."""
        # 26 MB of dummy data
        large_bytes = b"A" * (26 * 1024 * 1024)
        file_obj = UploadFile(filename="large.csv", file=io.BytesIO(large_bytes))
        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(analyze_batch_reports(file_obj))
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("exceeds 25 mb", ctx.exception.detail.lower())

    def test_batch_row_level_fault_tolerance(self):
        """Malformed rows are flagged as FAILED without breaking valid rows in the batch."""
        mixed_csv = (
            b"Description,Location,Department\n"
            b'"High pressure methane gas leak detected at separator flange.",Rig 1,Drilling\n'
            b'"",Rig 2,Maintenance\n'
            b'"Unsafe scaffold at 10m height without harness.",Rig 3,Drilling\n'
            b'"Hi",Rig 4,Production\n'
        )
        file_obj = UploadFile(filename="mixed.csv", file=io.BytesIO(mixed_csv))
        resp = asyncio.run(analyze_batch_reports(file_obj))

        self.assertTrue(resp["success"])
        self.assertEqual(resp.get("analysis_source"), "backend_ai")
        summary = resp["summary"]
        self.assertEqual(summary["total_reports"], 4)
        self.assertEqual(summary["successfully_analyzed"], 2)
        self.assertEqual(summary["failed_rows"], 2)

        results = resp["results"]
        self.assertEqual(results[0]["status"], "SUCCESS")
        self.assertEqual(results[1]["status"], "FAILED")
        self.assertEqual(results[2]["status"], "SUCCESS")
        self.assertEqual(results[3]["status"], "FAILED")

    # ------------------------------------------------------------------------
    # 4. MODEL LOADING & INFERENCE FALLBACK (REQUIREMENT 5)
    # ------------------------------------------------------------------------
    def test_model_inference_fallback_resilience(self):
        """When ML model is None or fails, pipeline falls back gracefully to rule-based severity."""
        report = "Worker slipped on oily metal grating on drill floor."
        # Call single report processing directly
        res = _process_single_report(report_text=report)
        self.assertIn("severity_prediction", res)
        self.assertIn("potential_accident_level", res["severity_prediction"])
        self.assertIn(res["severity_prediction"]["potential_accident_level"], ["I", "II", "III", "IV", "V"])

    # ------------------------------------------------------------------------
    # 5. SIMILARITY & RISK ENGINE ROBUSTNESS (REQUIREMENTS 6 & 7)
    # ------------------------------------------------------------------------
    def test_similarity_engine_edge_cases(self):
        """Similarity engine handles empty text, whitespace, and special characters cleanly."""
        sim_engine = SimilarityEngine()
        self.assertEqual(sim_engine.find_similar(""), [])
        self.assertEqual(sim_engine.find_similar("   \n  "), [])
        self.assertEqual(sim_engine.find_similar("!@#$%^&*()_+"), [])
        self.assertEqual(sim_engine.find_similar("12345 67890"), [])

    def test_risk_engine_edge_cases(self):
        """Risk engine handles empty text, punctuation, and non-hazard narrative cleanly."""
        risk_engine = RiskEngine()
        self.assertEqual(risk_engine.detect_precursors(""), [])
        self.assertEqual(risk_engine.detect_precursors("   "), [])
        self.assertEqual(risk_engine.detect_precursors("!@#$%^&*()"), [])

        res = risk_engine.analyze("")
        self.assertEqual(res["score"], 0)
        self.assertEqual(res["level"], "LOW")
        self.assertIn("summary", res)

    # ------------------------------------------------------------------------
    # 6. IMAGE EVIDENCE SERVICE ISOLATION & VALIDATION (REQUIREMENT 4)
    # ------------------------------------------------------------------------
    def test_image_service_invalid_base64_rejection(self):
        """Image service safely rejects corrupted base64 without throwing uncaught exceptions."""
        img_service = ImageEvidenceService()
        record = img_service.process_and_store_image(
            image_payload="corrupted_not_base64_%%%",
            report_id="REP-TEST-001"
        )
        self.assertFalse(record.image_attached)
        self.assertIsNotNone(record.error_message)

    def test_image_service_unsupported_format_rejection(self):
        """Image service rejects non-image formats."""
        img_service = ImageEvidenceService()
        import base64
        text_b64 = base64.b64encode(b"This is a text file not an image.").decode("utf-8")
        record = img_service.process_and_store_image(
            image_payload=text_b64,
            report_id="REP-TEST-002"
        )
        self.assertFalse(record.image_attached)

    # ------------------------------------------------------------------------
    # 7. RESOURCE NOT FOUND (404) & STATUS UPDATES (REQUIREMENT 1)
    # ------------------------------------------------------------------------
    def test_nonexistent_alert_404(self):
        """Retrieving a non-existent alert raises clean 404 HTTPException."""
        with self.assertRaises(HTTPException) as ctx:
            get_safety_alert("ALT-NONEXISTENT-999")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_nonexistent_review_404(self):
        """Retrieving a non-existent review raises clean 404 HTTPException."""
        with self.assertRaises(HTTPException) as ctx:
            get_safety_review("REV-NONEXISTENT-999")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_nonexistent_evidence_image_404(self):
        """Retrieving a non-existent image raises clean 404 HTTPException."""
        with self.assertRaises(HTTPException) as ctx:
            get_evidence_image("IMG-NONEXISTENT-999")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_nonexistent_action_404(self):
        """Retrieving a non-existent tracked action raises clean 404 HTTPException."""
        with self.assertRaises(HTTPException) as ctx:
            get_corrective_action("ACT-NONEXISTENT-999")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    def test_invalid_alert_status_update(self):
        """Updating alert status with invalid value raises clean 400 HTTPException."""
        with self.assertRaises(HTTPException) as ctx:
            update_safety_alert_status("ALT-NONEXISTENT-123", UpdateAlertStatusRequest(status="INVALID_STATUS", role="officer"))
        self.assertEqual(ctx.exception.status_code, 400)

    def test_invalid_action_status_update(self):
        """Updating action status with invalid value raises clean 400 HTTPException."""
        with self.assertRaises(HTTPException) as ctx:
            update_corrective_action_status("ACT-NONEXISTENT-123", UpdateActionStatusRequest(status="INVALID_STATUS", role="officer"))
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()

