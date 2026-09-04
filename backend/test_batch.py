"""
Unit Tests for Batch Upload and Analysis Endpoint (Task 4)
-----------------------------------------------------------
Validates:
1. CSV tabular upload and automated multi-report AI processing.
2. Excel (.xlsx) upload and automated multi-report AI processing.
3. Fault-tolerant row-level validation (invalid rows produce structured error objects without failing valid rows).
4. Summary metrics aggregation (total_reports, successfully_analyzed, failed_rows, critical_risk_count, severity_distribution).
5. Unsupported file extensions rejection (HTTP 400).
"""

import sys
from pathlib import Path
import unittest
import asyncio
import io
import pandas as pd
from starlette.datastructures import UploadFile
from starlette.exceptions import HTTPException

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from main import analyze_batch_reports, _process_single_report
except ImportError:
    from backend.main import analyze_batch_reports, _process_single_report


class TestBatchSafetyReportAnalysis(unittest.TestCase):

    def test_csv_batch_upload_successful(self):
        """Validates that a multi-row CSV is parsed and analyzed through the complete AI pipeline."""
        df = pd.DataFrame([
            {
                "Description": "High-pressure hydrocarbon gas leak detected near separator outlet valve during pump startup. LEL detector alarmed at 45%.",
                "Location": "Compressor Bay #3",
                "Department": "Drilling Operations",
                "Worker Type": "Employee",
                "Gender": "Male"
            },
            {
                "Description": "Contractor technician observed working on scaffold at 16m elevation without safety harness connected to lifeline.",
                "Location": "Separator Column #2",
                "Department": "Maintenance",
                "Worker Type": "Contractor / Third Party",
                "Gender": "Male"
            },
            {
                "Description": "Routine daily safety inspection completed at tool warehouse. All housekeeping standards verified and PPE compliant.",
                "Location": "Warehouse Bay A",
                "Department": "Production",
                "Worker Type": "Employee",
                "Gender": "Male"
            }
        ])

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        upload_file = UploadFile(
            filename="safety_batch.csv",
            file=io.BytesIO(csv_bytes)
        )

        data = asyncio.run(analyze_batch_reports(file=upload_file))
        self.assertTrue(data["success"])
        self.assertEqual(data["filename"], "safety_batch.csv")

        summary = data["summary"]
        self.assertEqual(summary["total_reports"], 3)
        self.assertEqual(summary["successfully_analyzed"], 3)
        self.assertEqual(summary["failed_rows"], 0)
        self.assertGreaterEqual(summary["critical_risk_count"] + summary["high_risk_count"], 1)

        results = data["results"]
        self.assertEqual(len(results), 3)

        # Check Row 1 (Gas Leak)
        row1 = results[0]
        self.assertEqual(row1["row_index"], 1)
        self.assertEqual(row1["status"], "SUCCESS")
        self.assertIn("analysis", row1)
        self.assertIn("overall_risk", row1["analysis"])
        self.assertIn("severity_prediction", row1["analysis"])
        self.assertIn("detected_precursors", row1["analysis"])
        self.assertGreaterEqual(row1["analysis"]["overall_risk"]["score"], 50)

        # Check Row 3 (Safe Observation)
        row3 = results[2]
        self.assertEqual(row3["row_index"], 3)
        self.assertEqual(row3["status"], "SUCCESS")
        self.assertEqual(row3["analysis"]["severity_prediction"]["potential_accident_level"], "I")

    def test_xlsx_batch_upload_successful(self):
        """Validates that an Excel (.xlsx) file is parsed and analyzed correctly."""
        df = pd.DataFrame([
            {
                "Description": "Damaged 440V electrical power line with frayed insulation submerged in standing water near rig mud tanks.",
                "Location": "Drill Rig #4 Mud Tank",
                "Industry Sector": "Mining",
                "Worker Type": "Employee",
                "Gender": "Male"
            },
            {
                "Description": "Worker entered confined mud pit without gas testing or atmospheric clearance permit.",
                "Location": "Mud Pit Cluster #2",
                "Industry Sector": "Mining",
                "Worker Type": "Employee",
                "Gender": "Male"
            }
        ])

        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_buffer.seek(0)

        upload_file = UploadFile(
            filename="rig_incidents.xlsx",
            file=excel_buffer
        )

        data = asyncio.run(analyze_batch_reports(file=upload_file))
        self.assertTrue(data["success"])
        self.assertEqual(data["summary"]["total_reports"], 2)
        self.assertEqual(data["summary"]["successfully_analyzed"], 2)
        self.assertEqual(len(data["results"]), 2)

    def test_mixed_batch_with_invalid_rows_fault_tolerance(self):
        """Validates that corrupt or empty rows produce row-level errors without failing valid rows."""
        df = pd.DataFrame([
            {
                "Description": "Valid observation: High pressure flange leak with hydrocarbon mist spraying.",
                "Location": "Bay 1",
                "Department": "Production"
            },
            {
                "Description": "",  # Empty row -> should fail at row level
                "Location": "Bay 2",
                "Department": "Production"
            },
            {
                "Description": "Valid observation: Scaffold plank slipped when worker climbed ladder.",
                "Location": "Bay 3",
                "Department": "Maintenance"
            }
        ])

        csv_bytes = df.to_csv(index=False).encode("utf-8")
        upload_file = UploadFile(
            filename="mixed_batch.csv",
            file=io.BytesIO(csv_bytes)
        )

        data = asyncio.run(analyze_batch_reports(file=upload_file))
        self.assertTrue(data["success"])
        self.assertEqual(data["summary"]["total_reports"], 3)
        self.assertEqual(data["summary"]["successfully_analyzed"], 2)
        self.assertEqual(data["summary"]["failed_rows"], 1)

        results = data["results"]
        self.assertEqual(results[0]["status"], "SUCCESS")
        self.assertEqual(results[1]["status"], "FAILED")
        self.assertIn("error", results[1])
        self.assertEqual(results[2]["status"], "SUCCESS")

    def test_unsupported_file_format_rejected(self):
        """Validates that unsupported formats (e.g. .pdf or .txt) raise HTTPException 400."""
        upload_file = UploadFile(
            filename="report_document.pdf",
            file=io.BytesIO(b"PDF header content")
        )

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(analyze_batch_reports(file=upload_file))
        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
