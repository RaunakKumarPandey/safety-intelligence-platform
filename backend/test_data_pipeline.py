"""
Comprehensive Unit Tests for Safety Data Pipeline (Task 11)
-----------------------------------------------------------
Validates:
1. Separation of safety incident datasets from operational governance JSON stores
   (reviews_store.json, test_reviews_store.json, alerts_store.json, actions_store.json).
2. Automated multi-format discovery (CSV, XLSX, Parquet, and validated JSON).
3. Schema and attribute normalization:
   - description (Unicode cleaning, whitespace normalization)
   - location (Standardized or fallback to 'Unknown')
   - industry sector (Mapping via SECTOR_MAP)
   - worker type (Mapping via WORKER_MAP)
   - potential accident level & actual accident level (Roman numerals I to V)
   - critical risk (Mapping via CRITICAL_RISK_MAP)
4. Content-based deduplication with preservation of highest severity on collision.
5. Ingestion validation reporting:
   - total rows, valid rows, invalid rows, duplicates, missing descriptions.
6. Zero-leakage stratified splits creation (Train, Val, Test).
"""

import sys
import tempfile
import json
import shutil
import unittest
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from services.data_pipeline import (
        SafetyDataPipeline,
        SafetyTextNormalizer,
        UnifiedSafetyReport,
        IngestionValidationReport,
        SEVERITY_MAP,
        CRITICAL_RISK_MAP,
        SECTOR_MAP,
        WORKER_MAP,
    )
except ImportError:
    from backend.services.data_pipeline import (
        SafetyDataPipeline,
        SafetyTextNormalizer,
        UnifiedSafetyReport,
        IngestionValidationReport,
        SEVERITY_MAP,
        CRITICAL_RISK_MAP,
        SECTOR_MAP,
        WORKER_MAP,
    )


class TestSafetyDataPipeline(unittest.TestCase):

    def setUp(self):
        # Create an isolated temporary test directory
        self.test_dir = Path(tempfile.mkdtemp())
        self.pipeline = SafetyDataPipeline(data_dir=self.test_dir)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # ------------------------------------------------------------------------
    # 1. EXCLUSION OF OPERATIONAL GOVERNANCE STORES
    # ------------------------------------------------------------------------
    def test_exclude_operational_json_stores(self):
        """Validates that reviews_store.json, alerts_store.json, etc. are NOT treated as incident datasets."""
        # 1. Create dummy operational store files
        reviews_store = self.test_dir / "reviews_store.json"
        with open(reviews_store, "w") as f:
            json.dump({"REV-001": {"review_status": "ACCEPTED", "officer_name": "R. Sharma"}}, f)

        test_reviews_store = self.test_dir / "test_reviews_store.json"
        with open(test_reviews_store, "w") as f:
            json.dump({"REV-999": {"review_status": "REJECTED"}}, f)

        alerts_store = self.test_dir / "alerts_store.json"
        with open(alerts_store, "w") as f:
            json.dump({"ALT-100": {"alert_status": "NEW", "risk_level": "CRITICAL"}}, f)

        actions_store = self.test_dir / "actions_store.json"
        with open(actions_store, "w") as f:
            json.dump({"ACT-500": {"status": "OPEN", "priority": "HIGH"}}, f)

        # 2. Create a genuine safety dataset
        valid_csv = self.test_dir / "accidents.csv"
        df_valid = pd.DataFrame([
            {
                "Description": "High pressure gas leak observed at separator flange.",
                "Potential Accident Level": "IV",
                "Accident Level": "I",
                "Critical Risk": "Pressurized Systems",
                "Industry Sector": "Mining",
                "Employee or Third Party": "Employee",
                "Local": "Local_01",
                "Countries": "Country_01"
            }
        ])
        df_valid.to_csv(valid_csv, index=False)

        # 3. Discover datasets
        discovered = self.pipeline.discover_datasets()

        # The pipeline must only discover the valid CSV and exclude all store JSONs
        discovered_names = [p.name for p in discovered]
        self.assertIn("accidents.csv", discovered_names)
        self.assertNotIn("reviews_store.json", discovered_names)
        self.assertNotIn("test_reviews_store.json", discovered_names)
        self.assertNotIn("alerts_store.json", discovered_names)
        self.assertNotIn("actions_store.json", discovered_names)

    # ------------------------------------------------------------------------
    # 2. MULTI-FORMAT DATASET DISCOVERY & PARSING
    # ------------------------------------------------------------------------
    def test_discover_and_load_valid_json_dataset(self):
        """Ensures valid JSON safety datasets are discovered and parsed."""
        valid_json = self.test_dir / "safety_observations.json"
        json_content = [
            {
                "Description": "Worker observed without safety harness while repairing mast.",
                "Potential Accident Level": "III",
                "Critical Risk": "Fall Prevention",
                "Industry Sector": "Oil & Gas",
                "Employee or Third Party": "Third Party",
                "Local": "Drilling Rig 04"
            }
        ]
        with open(valid_json, "w") as f:
            json.dump(json_content, f)

        discovered = self.pipeline.discover_datasets()
        self.assertIn(valid_json, discovered)

        df = self.pipeline.load_raw_dataset(valid_json)
        self.assertEqual(len(df), 1)
        self.assertIn("Description", df.columns)

    def test_discover_and_load_xlsx_dataset(self):
        """Ensures Excel (.xlsx) safety datasets are discovered and parsed."""
        valid_xlsx = self.test_dir / "safety_log.xlsx"
        df_excel = pd.DataFrame([
            {
                "Description": "Hydraulic oil spill near pump motor skid. Slip hazard.",
                "Potential Accident Level": "II",
                "Critical Risk": "Chemical Substances",
                "Industry Sector": "Metals",
                "Employee or Third Party": "Employee",
                "Local": "Plant A"
            }
        ])
        df_excel.to_excel(valid_xlsx, index=False)

        discovered = self.pipeline.discover_datasets()
        self.assertIn(valid_xlsx, discovered)

        df = self.pipeline.load_raw_dataset(valid_xlsx)
        self.assertEqual(len(df), 1)

    # ------------------------------------------------------------------------
    # 3. SCHEMA AND ATTRIBUTE NORMALIZATION
    # ------------------------------------------------------------------------
    def test_normalization_rules(self):
        """Tests normalization of descriptions, locations, sectors, worker types, severities, and risks."""
        sample_row = pd.Series({
            "Description": "  High   pressure line burst   with Latin-1 artifact  ",
            "Potential Accident Level": "Level IV",
            "Accident Level": "Minor",
            "Critical Risk": "pressurized systems",
            "Industry Sector": "mining",
            "Employee or Third Party": "third party",
            "Local": "  Local_05  ",
            "Countries": " Country_01 ",
            "Data": "2016-05-12 00:00:00",
            "Genre": "male"
        })

        report = self.pipeline.normalize_record(sample_row, source_name="test.csv", index_num=0)
        self.assertIsNotNone(report)

        # 1. Text normalization
        self.assertEqual(report.cleaned_text, "High pressure line burst with Latin-1 artifact")
        # 2. Severity normalization
        self.assertEqual(report.severity_level, "IV")
        self.assertEqual(report.severity_rank, 4)
        self.assertEqual(report.actual_accident_level, "I")
        # 3. Critical risk normalization
        self.assertEqual(report.critical_risk, "Pressurized Systems & Lines")
        # 4. Sector & Worker normalization
        self.assertEqual(report.industry_sector, "Mining & Extraction")
        self.assertEqual(report.worker_type, "Contractor / Third Party")
        # 5. Metadata normalization
        self.assertEqual(report.location, "Local_05")
        self.assertEqual(report.country, "Country_01")
        self.assertEqual(report.gender, "Male")

    # ------------------------------------------------------------------------
    # 4. DEDUPLICATION & HIGHEST SEVERITY PRESERVATION
    # ------------------------------------------------------------------------
    def test_deduplication_preserves_highest_severity(self):
        """
        Validates that when duplicate descriptions have conflicting potential accident levels,
        the record with the HIGHER consequence potential is deterministically preserved.
        """
        csv_file = self.test_dir / "duplicate_test.csv"
        # Two identical reports with different severities: Level II vs Level IV
        duplicate_data = pd.DataFrame([
            {
                "Description": "Cracked crane wire rope identified during pre-shift lifting inspection.",
                "Potential Accident Level": "II",  # Rank 2 (Lower)
                "Critical Risk": "Suspended Loads",
                "Industry Sector": "Mining",
                "Local": "Local_01"
            },
            {
                "Description": "Cracked crane wire rope identified during pre-shift lifting inspection.",
                "Potential Accident Level": "IV",  # Rank 4 (Higher)
                "Critical Risk": "Suspended Loads",
                "Industry Sector": "Mining",
                "Local": "Local_01"
            }
        ])
        duplicate_data.to_csv(csv_file, index=False)

        df_processed = self.pipeline.process_all(deduplicate=True)

        # Should be deduplicated to exactly 1 record
        self.assertEqual(len(df_processed), 1)
        preserved_record = df_processed.iloc[0]

        # The preserved record MUST have severity Level IV (rank 4)
        self.assertEqual(preserved_record["severity_level"], "IV")
        self.assertEqual(preserved_record["severity_rank"], 4)

    # ------------------------------------------------------------------------
    # 5. INGESTION VALIDATION REPORT
    # ------------------------------------------------------------------------
    def test_validation_report_metrics(self):
        """Validates that get_validation_report accurately tracks rows, valid, invalid, and duplicates."""
        csv_file = self.test_dir / "validation_test.csv"
        test_data = pd.DataFrame([
            {"Description": "Valid observation 1 with gas hazard.", "Potential Accident Level": "IV"},
            {"Description": "Valid observation 2 with electrical fault.", "Potential Accident Level": "III"},
            {"Description": "Valid observation 1 with gas hazard.", "Potential Accident Level": "IV"}, # Duplicate
            {"Description": "", "Potential Accident Level": "I"},                                       # Missing description
            {"Description": "nan", "Potential Accident Level": "I"},                                    # Uninformative
        ])
        test_data.to_csv(csv_file, index=False)

        self.pipeline.process_all(deduplicate=True)
        report = self.pipeline.get_validation_report()

        self.assertEqual(report["total_rows"], 5)
        self.assertEqual(report["valid_rows"], 2)            # 2 unique valid rows
        self.assertEqual(report["duplicates"], 1)            # 1 duplicate removed
        self.assertGreaterEqual(report["missing_descriptions"], 2) # Empty or nan descriptions
        self.assertIn("validation_test.csv", report["files_scanned"])

    # ------------------------------------------------------------------------
    # 6. INTEGRATION WITH REAL WORKSPACE DATASET
    # ------------------------------------------------------------------------
    def test_real_dataset_ingestion_and_stratification(self):
        """Validates ingestion, deduplication, and zero-leakage stratification on workspace accidents.csv."""
        real_pipeline = SafetyDataPipeline()
        df = real_pipeline.process_all(deduplicate=True)

        self.assertGreater(len(df), 400)
        self.assertTrue((df["severity_rank"] >= 1).all() and (df["severity_rank"] <= 5).all())

        # Verify zero-leakage stratification partitions
        train_df, val_df, test_df = real_pipeline.create_stratified_splits(test_size=0.15, val_size=0.15)
        self.assertEqual(len(train_df) + len(val_df) + len(test_df), len(df))

        # Check disjoint text index sets
        train_texts = set(train_df["cleaned_text"])
        val_texts = set(val_df["cleaned_text"])
        test_texts = set(test_df["cleaned_text"])

        self.assertEqual(len(train_texts.intersection(test_texts)), 0, "Zero test leakage constraint violated")
        self.assertEqual(len(train_texts.intersection(val_texts)), 0, "Zero validation leakage constraint violated")
        self.assertEqual(len(val_texts.intersection(test_texts)), 0, "Zero val/test leakage constraint violated")


if __name__ == "__main__":
    unittest.main()
