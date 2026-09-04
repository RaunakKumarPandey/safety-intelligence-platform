"""
Historical Incident TF-IDF Similarity Retrieval Engine for SIH26165
-------------------------------------------------------------------
Implements normalized, mathematically bounded text similarity retrieval for
historical safety reports using term frequency-inverse document frequency (TF-IDF)
and cosine similarity with configurable relevance thresholding.

Guarantees:
- Strict cosine bounds: 0.0 <= similarity <= 1.0 (Never exceeds 100%)
- Deterministic ranking with stable secondary index ordering
- Configurable minimum similarity threshold (suppresses irrelevant matches below cutoff)
- Standardized output schema with complete historical context
- Strictly TF-IDF + Cosine Similarity (no neural embeddings / vector databases)
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    from services.data_pipeline import SafetyDataPipeline, SafetyTextNormalizer
except ImportError:
    from backend.services.data_pipeline import SafetyDataPipeline, SafetyTextNormalizer


DEFAULT_MIN_SIMILARITY_THRESHOLD = 0.10  # 10% minimum cosine similarity cutoff
DEFAULT_TOP_N = 3
RETRIEVAL_METHOD_LABEL = "TF-IDF + Cosine Similarity (Sublinear TF, n-gram 1-2)"


class SimilarityEngine:
    """TF-IDF and Cosine Similarity retrieval engine for historical safety incidents."""

    def __init__(
        self,
        data_path: Optional[Path] = None,
        min_threshold: float = DEFAULT_MIN_SIMILARITY_THRESHOLD
    ):
        self.min_threshold = float(min_threshold)
        self.normalizer = SafetyTextNormalizer()

        if data_path is None:
            data_path = BASE_DIR / "data" / "accidents.csv"

        self.df = pd.read_csv(data_path)

        # Normalize descriptions for robust domain retrieval
        raw_descriptions = self.df["Description"].fillna("").astype(str)
        self.cleaned_descriptions = [
            self.normalizer.clean(desc) for desc in raw_descriptions
        ]

        # Fit Sublinear TF-IDF Vectorizer with Unigrams and Bigrams
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
            max_features=20000
        )

        self.tfidf_matrix = self.vectorizer.fit_transform(self.cleaned_descriptions)

        print(
            f"Similarity Engine ready with {len(self.df)} historical reports "
            f"(Threshold: {self.min_threshold:.0%}, Method: {RETRIEVAL_METHOD_LABEL})"
        )

    def find_similar(
        self,
        report_text: str,
        top_n: int = DEFAULT_TOP_N,
        min_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves top similar historical incidents strictly exceeding the similarity threshold.

        Steps:
        1. Clean and normalize the query narrative.
        2. Compute TF-IDF representation of the query.
        3. Compute exact Cosine Similarity against all historical records.
        4. Deterministically sort matches in descending order.
        5. Filter out all results below the configured similarity threshold.
        6. Return at most top_n records.

        Args:
            report_text: Field observation narrative to query
            top_n: Maximum number of incidents to return
            min_threshold: Custom minimum similarity threshold (defaults to self.min_threshold)

        Returns:
            List of normalized incident dictionaries:
            {
                "incident_id": int,
                "source_id": str,
                "reference_id": str,
                "description": str,
                "historical_description": str,
                "similarity": float (0.0 to 1.0),
                "similarity_score": float (0.0 to 1.0),
                "similarity_percentage": float (0.0 to 100.0),
                "potential_accident_level": str,
                "potential_incident_level": str,
                "critical_risk": str,
                "industry_sector": str,
                "worker_type": str,
                "retrieval_method": str
            }
        """
        if not report_text or not report_text.strip():
            return []

        threshold = self.min_threshold if min_threshold is None else float(min_threshold)
        cleaned_query = self.normalizer.clean(report_text)

        if not cleaned_query.strip():
            return []

        # Vectorize query
        query_vector = self.vectorizer.transform([cleaned_query])

        # Compute cosine similarity
        raw_scores = cosine_similarity(query_vector, self.tfidf_matrix).flatten()

        # Deterministic sorting: sort by score descending, then by original index ascending for ties
        ranked_indices = sorted(
            range(len(raw_scores)),
            key=lambda idx: (round(float(raw_scores[idx]), 6), -idx),
            reverse=True
        )

        results: List[Dict[str, Any]] = []

        for idx in ranked_indices:
            raw_sim = float(raw_scores[idx])

            # Mathematical clamping to guarantee 0.0 <= sim <= 1.0
            clamped_sim = max(0.0, min(1.0, raw_sim))

            # Stop and filter out once score falls below minimum threshold
            if clamped_sim < threshold:
                break

            row = self.df.iloc[idx]

            incident_id = int(row.get("Unnamed: 0", idx))
            description = str(row.get("Description", "")).strip()
            level = str(row.get("Potential Accident Level", row.get("potential_incident_level", "Unknown"))).strip()
            critical_risk = str(row.get("Critical Risk", "Not Specified")).strip()
            industry_sector = str(row.get("Industry Sector", "Mining")).strip()
            worker_type = str(row.get("Employee or Third Party", "Third Party")).strip()

            source_id = f"INC-{incident_id:04d}" if isinstance(incident_id, int) else f"INC-{incident_id}"

            results.append({
                "incident_id": incident_id,
                "source_id": source_id,
                "reference_id": source_id,
                "description": description,
                "historical_description": description,
                "similarity": round(clamped_sim, 4),
                "similarity_score": round(clamped_sim, 4),
                "similarity_percentage": round(clamped_sim * 100.0, 2),
                "potential_accident_level": level,
                "potential_incident_level": level,
                "critical_risk": critical_risk,
                "industry_sector": industry_sector,
                "worker_type": worker_type,
                "retrieval_method": RETRIEVAL_METHOD_LABEL
            })

            if len(results) >= top_n:
                break

        return results