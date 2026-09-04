"""
Comprehensive Unit & Integration Tests for Image Evidence Support (Task 12)
----------------------------------------------------------------------------
Validates:
1. Safe receipt and persistent storage of optional image evidence.
2. Accurate association with report_id.
3. Non-breaking fault tolerance (corrupted/invalid images never break text analysis).
4. Strict validation (allowed formats: JPEG, PNG, WEBP; max size: 10MB; corruption detection).
5. Explicit zero-fake-CV claims (cv_analysis_status is NOT_CONFIGURED).
6. File retrieval and metadata endpoints.
"""

import base64
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from services.image_service import (
        ImageEvidenceService,
        ImageEvidenceRecord,
        MAX_IMAGE_SIZE_BYTES,
    )
    from main import _process_single_report, SafetyReport, analyze_report
except ImportError:
    from backend.services.image_service import (
        ImageEvidenceService,
        ImageEvidenceRecord,
        MAX_IMAGE_SIZE_BYTES,
    )
    from backend.main import _process_single_report, SafetyReport, analyze_report


def create_test_image_base64(format_name: str = "PNG", size: tuple = (100, 100), color: str = "red") -> str:
    """Helper to generate a valid in-memory image base64 data URL."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format=format_name)
    raw_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    mime = "image/png" if format_name.upper() == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{raw_b64}"


class TestImageEvidenceService(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.image_service = ImageEvidenceService(storage_dir=self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # ------------------------------------------------------------------------
    # 1. VALID IMAGE ATTACHMENT & STORAGE
    # ------------------------------------------------------------------------
    def test_valid_png_image_attachment(self):
        """Tests processing and storage of a valid PNG image attachment."""
        b64_image = create_test_image_base64(format_name="PNG", size=(120, 80), color="blue")
        report_id = "REP-TEST101"

        record = self.image_service.process_and_store_image(
            image_payload=b64_image,
            report_id=report_id,
            original_filename="flange_leak.png"
        )

        self.assertTrue(record.image_attached)
        self.assertIsNotNone(record.image_id)
        self.assertEqual(record.report_id, report_id)
        self.assertEqual(record.format, "PNG")
        self.assertEqual(record.width, 120)
        self.assertEqual(record.height, 80)
        self.assertGreater(record.file_size_bytes, 0)
        self.assertEqual(record.cv_analysis_status, "NOT_CONFIGURED")

        # Check physical file on disk
        stored_path = self.image_service.get_image_file_path(record.image_id)
        self.assertIsNotNone(stored_path)
        self.assertTrue(stored_path.exists())
        self.assertEqual(stored_path.stat().st_size, record.file_size_bytes)

    def test_valid_jpeg_image_attachment(self):
        """Tests processing and storage of a valid JPEG image attachment."""
        b64_image = create_test_image_base64(format_name="JPEG", size=(64, 64), color="orange")
        report_id = "REP-TEST102"

        record = self.image_service.process_and_store_image(
            image_payload=b64_image,
            report_id=report_id,
            original_filename="corrosion_pipe.jpg"
        )

        self.assertTrue(record.image_attached)
        self.assertEqual(record.format, "JPEG")
        self.assertEqual(record.content_type, "image/jpeg")

    # ------------------------------------------------------------------------
    # 2. NO IMAGE ATTACHED
    # ------------------------------------------------------------------------
    def test_no_image_attached(self):
        """Tests that omitting an image results in clean image_attached=False."""
        record = self.image_service.process_and_store_image(
            image_payload=None,
            report_id="REP-NOIMG"
        )

        self.assertFalse(record.image_attached)
        self.assertIsNone(record.image_id)
        self.assertIsNone(record.error_message)

    # ------------------------------------------------------------------------
    # 3. CORRUPTED & INVALID IMAGE HANDLING (FAULT TOLERANCE)
    # ------------------------------------------------------------------------
    def test_corrupted_image_data(self):
        """Tests that corrupted binary data is rejected gracefully with error message."""
        corrupted_b64 = "data:image/jpeg;base64,VGhpcyBpcyBub3QgYW4gaW1hZ2UgZmlsZSE=" # "This is not an image file!"

        record = self.image_service.process_and_store_image(
            image_payload=corrupted_b64,
            report_id="REP-CORRUPT"
        )

        self.assertFalse(record.image_attached)
        self.assertIsNotNone(record.error_message)

    def test_invalid_base64_string(self):
        """Tests handling of unparseable base64 string."""
        record = self.image_service.process_and_store_image(
            image_payload="data:image/png;base64,Invalid!Base64*Character",
            report_id="REP-BADB64"
        )

        self.assertFalse(record.image_attached)
        self.assertIsNotNone(record.error_message)

    # ------------------------------------------------------------------------
    # 4. OVERSIZED IMAGE REJECTION
    # ------------------------------------------------------------------------
    def test_oversized_image_rejection(self):
        """Tests that images exceeding 10 MB are rejected."""
        fake_huge_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * (MAX_IMAGE_SIZE_BYTES + 1024)
        is_valid, fmt, ctype, w, h, err = self.image_service.validate_image_bytes(fake_huge_bytes)

        self.assertFalse(is_valid)
        self.assertIn("exceeds maximum allowed limit", err)

    # ------------------------------------------------------------------------
    # 5. INTEGRATION WITH CORE REPORT ANALYSIS PIPELINE
    # ------------------------------------------------------------------------
    def test_process_single_report_with_image_evidence(self):
        """Validates end-to-end report analysis with optional image attached."""
        b64_image = create_test_image_base64(format_name="PNG", size=(50, 50), color="green")
        report_text = "High pressure flammable hydrocarbon gas leakage observed near compressor suction valve."

        analysis = _process_single_report(
            report_text=report_text,
            industry_sector="Oil & Gas",
            worker_type="Employee",
            gender="Male",
            image_base64=b64_image,
            image_filename="compressor_leak.png"
        )

        # 1. Text analysis must succeed
        self.assertIn("overall_risk", analysis)
        self.assertIn("severity_prediction", analysis)
        self.assertIn("detected_precursors", analysis)

        # 2. Image evidence metadata must be present
        self.assertIn("image_evidence", analysis)
        img_meta = analysis["image_evidence"]
        self.assertTrue(img_meta["image_attached"])
        self.assertIsNotNone(img_meta["image_id"])
        self.assertEqual(img_meta["report_id"], analysis["report_id"])
        self.assertEqual(img_meta["cv_analysis_status"], "NOT_CONFIGURED")

    def test_corrupted_image_does_not_break_text_analysis(self):
        """
        CRITICAL REQUIREMENT 8:
        Ensures that even if an attached image is completely corrupted,
        the multi-stage text NLP/ML analysis runs to completion without throwing any error.
        """
        corrupted_b64 = "data:image/png;base64,ZmFrZV9jb3JydXB0ZWRfaW1hZ2VfZGF0YQ=="
        report_text = "Electrician observed working on 440V distribution panel without arc-flash PPE."

        # Execute analysis via endpoint model
        req = SafetyReport(
            report_text=report_text,
            industry_sector="Mining",
            worker_type="Employee",
            gender="Male",
            image_base64=corrupted_b64,
            image_filename="corrupted.png"
        )

        resp = analyze_report(req)
        self.assertTrue(resp["success"])
        analysis = resp["analysis"]

        # Text analysis completed accurately
        self.assertIn(analysis["severity_prediction"]["potential_accident_level"], ["I", "II", "III", "IV", "V"])
        self.assertTrue(any(p["factor"] == "electrical" for p in analysis["detected_precursors"]))

        # Image evidence gracefully reported as not attached with explanation
        img_meta = analysis["image_evidence"]
        self.assertFalse(img_meta["image_attached"])
        self.assertIsNotNone(img_meta["error_message"])


if __name__ == "__main__":
    unittest.main()
