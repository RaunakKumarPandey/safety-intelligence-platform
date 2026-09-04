"""
Test suite for SIH26165 Safety Data Pipeline
"""

import unittest
from pathlib import Path
import pandas as pd
import sys

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from services.data_pipeline import SafetyDataPipeline, SafetyTextNormalizer, SEVERITY_MAP
except ImportError:
    from backend.services.data_pipeline import SafetyDataPipeline, SafetyTextNormalizer, SEVERITY_MAP


class TestSafetyDataPipeline(unittest.TestCase):

    def setUp(self):
        self.pipeline = SafetyDataPipeline()

    def test_dataset_discovery(self):
        files = self.pipeline.discover_datasets()
        self.assertGreater(len(files), 0, "Should discover at least 1 dataset file (accidents.csv)")
        self.assertTrue(any(f.name == "accidents.csv" for f in files))

    def test_text_normalization(self):
        raw = "  During  routine   inspection\r\nat BAP-01...  LEL reached 25%   "
        cleaned = SafetyTextNormalizer.clean(raw, expand_acronyms=True)
        self.assertNotIn("\r\n", cleaned)
        self.assertNotIn("  ", cleaned)
        self.assertIn("lower explosive limit", cleaned)

    def test_raw_425_preservation(self):
        df_raw = self.pipeline.process_all(deduplicate=False)
        self.assertEqual(len(df_raw), 425, "Raw dataset without deduplication should preserve all 425 records")

    def test_deduplication(self):
        df_dedup = self.pipeline.process_all(deduplicate=True)
        self.assertEqual(len(df_dedup), 411, "Deduplication should result in exactly 411 unique records")
        self.assertEqual(df_dedup["cleaned_text"].duplicated().sum(), 0, "No duplicate texts should exist")

    def test_severity_standardization(self):
        df = self.pipeline.process_all(deduplicate=True)
        valid_levels = {"I", "II", "III", "IV", "V"}
        unique_levels = set(df["severity_level"].unique())
        self.assertTrue(unique_levels.issubset(valid_levels), f"All severity levels must be within {valid_levels}")

    def test_zero_leakage_stratification(self):
        train_df, val_df, test_df = self.pipeline.create_stratified_splits(test_size=0.15, val_size=0.15, random_state=42)

        # Check total rows
        total_split = len(train_df) + len(val_df) + len(test_df)
        self.assertEqual(total_split, 411, "Sum of splits should equal 411")

        # Check disjoint sets (zero data leakage)
        train_texts = set(train_df["cleaned_text"])
        val_texts = set(val_df["cleaned_text"])
        test_texts = set(test_df["cleaned_text"])

        self.assertEqual(len(train_texts.intersection(val_texts)), 0, "Train and Validation must have zero overlap")
        self.assertEqual(len(train_texts.intersection(test_texts)), 0, "Train and Test must have zero overlap")
        self.assertEqual(len(val_texts.intersection(test_texts)), 0, "Validation and Test must have zero overlap")

        # Check all 5 classes are represented in train
        self.assertEqual(len(train_df["severity_level"].unique()), 5, "Train set must have all 5 severity levels")


if __name__ == "__main__":
    unittest.main()
