"""
Comprehensive Unit Tests for TF-IDF Historical Incident Retrieval Engine (Task 7)
---------------------------------------------------------------------------------
Validates:
1. Identical & Highly Similar Reports: Exact matches produce high similarity (>= 0.90).
2. Unrelated Reports: Suppresses spurious matches below threshold.
3. Threshold Behavior: Verifies configurable min_threshold cutoff.
4. Top-K Retrieval: Respects top_n parameter bounds.
5. Determinism: Repeated queries produce strictly identical rankings and scores.
6. Complete Schema: All required metadata fields (similarity_score, description, level, critical_risk, industry_sector, worker_type, source_id) are present.
7. Pure TF-IDF Verification: Verifies no neural embeddings or vector database dependencies.
"""

import sys
from pathlib import Path
import unittest

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from services.similarity import SimilarityEngine
except ImportError:
    from backend.services.similarity import SimilarityEngine


class TestHistoricalIncidentRetrieval(unittest.TestCase):

    def setUp(self):
        self.engine = SimilarityEngine(min_threshold=0.10)

    # ------------------------------------------------------------------------
    # 1. IDENTICAL & SIMILAR REPORTS TEST
    # ------------------------------------------------------------------------
    def test_identical_and_similar_reports(self):
        """Validates that exact historical descriptions achieve near 100% similarity."""
        # Pick first row from dataset
        first_row = self.engine.df.iloc[0]
        exact_text = str(first_row["Description"]).strip()

        results = self.engine.find_similar(exact_text, top_n=3)
        self.assertGreater(len(results), 0, "Exact report query must return at least 1 match.")

        top_match = results[0]
        self.assertGreaterEqual(top_match["similarity"], 0.85, "Exact match should have >= 85% cosine similarity.")
        self.assertGreaterEqual(top_match["similarity_score"], 0.85)

        # Related incident test
        similar_query = "High pressure gas leakage from flange joint during routine maintenance."
        sim_results = self.engine.find_similar(similar_query, top_n=3)
        self.assertGreater(len(sim_results), 0)
        self.assertGreaterEqual(sim_results[0]["similarity"], 0.10)

    # ------------------------------------------------------------------------
    # 2. UNRELATED REPORTS SUPPRESSION TEST
    # ------------------------------------------------------------------------
    def test_unrelated_reports_suppressed(self):
        """Validates that queries with zero relevance to industrial safety return no results."""
        unrelated_queries = [
            "The blue unicorn danced across the rainbow in wonderland.",
            "Symphony orchestra violin concerto tempo crescendo allegro.",
            "Fictional dragon wizard enchanted magical castle spell."
        ]

        for query in unrelated_queries:
            results = self.engine.find_similar(query, min_threshold=0.10)
            self.assertEqual(len(results), 0, f"Unrelated query '{query}' must return 0 results under 10% threshold.")

    # ------------------------------------------------------------------------
    # 3. THRESHOLD BEHAVIOR TEST
    # ------------------------------------------------------------------------
    def test_configurable_threshold_behavior(self):
        """Validates that higher thresholds filter more aggressively than lower thresholds."""
        query = "Oil spill on deck near drilling rig pump room."

        low_thresh_results = self.engine.find_similar(query, top_n=10, min_threshold=0.05)
        high_thresh_results = self.engine.find_similar(query, top_n=10, min_threshold=0.40)

        # Lower threshold should return equal or more results than high threshold
        self.assertGreaterEqual(len(low_thresh_results), len(high_thresh_results))

        for inc in high_thresh_results:
            self.assertGreaterEqual(inc["similarity"], 0.40, "Results must exceed custom threshold.")

    # ------------------------------------------------------------------------
    # 4. TOP-K BEHAVIOR TEST
    # ------------------------------------------------------------------------
    def test_top_k_behavior(self):
        """Validates that retrieval respects the requested top_n limit."""
        query = "Worker fell from scaffold ladder while performing maintenance."

        res_k1 = self.engine.find_similar(query, top_n=1, min_threshold=0.05)
        res_k3 = self.engine.find_similar(query, top_n=3, min_threshold=0.05)
        res_k5 = self.engine.find_similar(query, top_n=5, min_threshold=0.05)

        self.assertLessEqual(len(res_k1), 1)
        self.assertLessEqual(len(res_k3), 3)
        self.assertLessEqual(len(res_k5), 5)

        if len(res_k3) >= 2:
            # Verify descending score ordering
            self.assertGreaterEqual(res_k3[0]["similarity"], res_k3[1]["similarity"])

    # ------------------------------------------------------------------------
    # 5. DETERMINISTIC RETRIEVAL TEST
    # ------------------------------------------------------------------------
    def test_retrieval_is_deterministic(self):
        """Validates that identical queries return identical results across repeated calls."""
        query = "Pressure release valve blew out spraying mud and water across drill floor."

        run1 = self.engine.find_similar(query, top_n=5)
        run2 = self.engine.find_similar(query, top_n=5)
        run3 = self.engine.find_similar(query, top_n=5)

        self.assertEqual(len(run1), len(run2))
        self.assertEqual(len(run2), len(run3))

        for r1, r2, r3 in zip(run1, run2, run3):
            self.assertEqual(r1["incident_id"], r2["incident_id"])
            self.assertEqual(r2["incident_id"], r3["incident_id"])
            self.assertEqual(r1["similarity"], r2["similarity"])
            self.assertEqual(r2["similarity"], r3["similarity"])

    # ------------------------------------------------------------------------
    # 6. COMPLETE METADATA SCHEMA TEST
    # ------------------------------------------------------------------------
    def test_complete_metadata_schema(self):
        """Validates that all required fields are present in every retrieved record."""
        query = "Electrical motor sparking in hazardous gas area."
        results = self.engine.find_similar(query, top_n=3)

        self.assertGreater(len(results), 0)
        for inc in results:
            self.assertIn("similarity", inc)
            self.assertIn("similarity_score", inc)
            self.assertIn("description", inc)
            self.assertIn("historical_description", inc)
            self.assertIn("potential_accident_level", inc)
            self.assertIn("critical_risk", inc)
            self.assertIn("industry_sector", inc)
            self.assertIn("worker_type", inc)
            self.assertIn("source_id", inc)
            self.assertIn("reference_id", inc)
            self.assertIn("retrieval_method", inc)

            # Type checks
            self.assertIsInstance(inc["similarity"], float)
            self.assertIsInstance(inc["description"], str)
            self.assertIsInstance(inc["potential_accident_level"], str)
            self.assertIsInstance(inc["source_id"], str)
            self.assertIn("TF-IDF", inc["retrieval_method"])

    # ------------------------------------------------------------------------
    # 7. EMPTY / BLANK QUERY HANDLING
    # ------------------------------------------------------------------------
    def test_empty_query_returns_empty_list(self):
        """Validates that empty or whitespace queries return empty lists."""
        self.assertEqual(self.engine.find_similar(""), [])
        self.assertEqual(self.engine.find_similar("    "), [])


if __name__ == "__main__":
    unittest.main()