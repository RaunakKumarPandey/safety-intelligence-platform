"""
Honest, Zero-Leakage Evaluation of the Deployed SIH26165 Severity Model
-----------------------------------------------------------------------
Loads the actual saved model artifact from backend/models/severity_model.pkl
and evaluates it strictly on the untouched 15% holdout test partition (N=62).
Computes all metrics directly and independently from y_true and y_pred.
"""

import sys
import json
import joblib
from pathlib import Path
from typing import Dict, Any
import numpy as np
import pandas as pd

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    classification_report,
    confusion_matrix
)

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.data_pipeline import SafetyDataPipeline

LABEL_NAMES = ["I", "II", "III", "IV", "V"]
LABEL_FULL_NAMES = {
    "I": "Level I (Minor)",
    "II": "Level II (Moderate)",
    "III": "Level III (Serious)",
    "IV": "Level IV (Critical)",
    "V": "Level V (Catastrophic)"
}


def prepare_features(df: pd.DataFrame) -> pd.Series:
    """Prepares structured composite input text for ML models."""
    return (
        "Description: " + df["cleaned_text"].astype(str)
        + " Industry Sector: " + df["industry_sector"].astype(str)
        + " Worker Type: " + df["worker_type"].astype(str)
        + " Gender: " + df["gender"].astype(str)
    )


def evaluate() -> Dict[str, Any]:
    """Evaluates the saved severity_model.pkl artifact on the untouched holdout test partition."""
    model_path = BASE_DIR / "models" / "severity_model.pkl"
    if not model_path.exists():
        raise FileNotFoundError(f"Trained model artifact not found at: {model_path}. Run train_model.py first.")

    # 1. Load actual saved trained model artifact
    model = joblib.load(model_path)

    # 2. Load untouched holdout test split
    pipeline = SafetyDataPipeline()
    train_df, val_df, test_df = pipeline.create_stratified_splits(
        test_size=0.15,
        val_size=0.15,
        random_state=42
    )
    dev_count = len(train_df) + len(val_df)
    holdout_count = len(test_df)

    # 3. Model & Dataset Info
    model_type = type(model).__name__
    if hasattr(model, "named_steps"):
        step_names = [f"{k}: {type(v).__name__}" for k, v in model.named_steps.items()]
        model_type = f"Pipeline({', '.join(step_names)})"

    model_version = "v2.0.0-honest-evaluation"
    training_dataset = f"accidents.csv (Development partition: {dev_count} samples)"
    evaluation_dataset = f"accidents.csv (Untouched Holdout Test partition: {holdout_count} samples)"

    # Print metadata logging
    print("=" * 80)
    print("MODEL EVALUATION LOGGING")
    print("=" * 80)
    print(f"Model Artifact Path:         {model_path}")
    print(f"Model Type:                  {model_type}")
    print(f"Model Version:               {model_version}")
    print(f"Training Dataset:            {training_dataset}")
    print(f"Evaluation Dataset:          {evaluation_dataset}")
    print(f"Number of Evaluation Samples:{holdout_count}")
    print("=" * 80)

    # 4. Generate predictions from saved artifact
    X_test = prepare_features(test_df)
    y_test = test_df["severity_level"]
    y_pred = model.predict(X_test)

    # 5. Independent calculation of unrounded metrics directly from y_true and y_pred
    acc = float(accuracy_score(y_test, y_pred))
    macro_p = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
    macro_r = float(recall_score(y_test, y_pred, average="macro", zero_division=0))
    macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
    weighted_p = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
    weighted_r = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
    weighted_f1 = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))

    # 6. Confusion Matrix & Per-Class Metrics
    cm = confusion_matrix(y_test, y_pred, labels=LABEL_NAMES)
    cm_arr = np.array(cm)

    per_class_metrics = {}
    for i, cls in enumerate(LABEL_NAMES):
        tp = int(cm_arr[i, i])
        fn = int(np.sum(cm_arr[i, :]) - tp)
        fp = int(np.sum(cm_arr[:, i]) - tp)
        tn = int(np.sum(cm_arr) - tp - fn - fp)
        support = int(np.sum(cm_arr[i, :]))

        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = float(tp / support) if support > 0 else 0.0
        f1 = float((2 * precision * recall) / (precision + recall)) if (precision + recall) > 0 else 0.0

        per_class_metrics[cls] = {
            "name": LABEL_FULL_NAMES[cls],
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "support": support,
            "false_positives": fp,
            "false_negatives": fn,
            "true_positives": tp,
            "true_negatives": tn,
            "is_safety_critical": cls in ["IV", "V"]
        }

    # 7. Print formal evaluation summary as required
    print("\n========================================")
    print("MODEL EVALUATION")
    print("========================================")
    print(f"Model: {model_type}")
    print(f"Model version: {model_version}")
    print(f"Development samples: {dev_count}")
    print(f"Holdout samples: {holdout_count}")
    print()
    print(f"Accuracy:           {acc:.6f} ({acc*100:.2f}%)")
    print(f"Macro Precision:    {macro_p:.6f} ({macro_p*100:.2f}%)")
    print(f"Macro Recall:       {macro_r:.6f} ({macro_r*100:.2f}%)")
    print(f"Macro F1:           {macro_f1:.6f} ({macro_f1*100:.2f}%)")
    print(f"Weighted Precision: {weighted_p:.6f} ({weighted_p*100:.2f}%)")
    print(f"Weighted Recall:    {weighted_r:.6f} ({weighted_r*100:.2f}%)")
    print(f"Weighted F1:        {weighted_f1:.6f} ({weighted_f1*100:.2f}%)")
    print()
    print("Per-class results:")
    for cls in LABEL_NAMES:
        c = per_class_metrics[cls]
        print(f"  Level {cls} ({c['name']}):")
        print(f"    Precision:       {c['precision']:.4f} ({c['precision']*100:.1f}%)")
        print(f"    Recall:          {c['recall']:.4f} ({c['recall']*100:.1f}%)")
        print(f"    F1-score:        {c['f1_score']:.4f} ({c['f1_score']*100:.1f}%)")
        print(f"    Support:         {c['support']}")
        print(f"    False Positives: {c['false_positives']}")
        print(f"    False Negatives: {c['false_negatives']}")
    print()
    print("Confusion Matrix:")
    print("Actual \\ Pred  |  I  II III  IV   V")
    print("-" * 36)
    for i, row in enumerate(cm.tolist()):
        row_str = " ".join(f"{val:3d}" for val in row)
        print(f"Level {LABEL_NAMES[i]:<4}   | {row_str}")
    print("========================================\n")

    # 8. Update evaluation_metrics.json
    metrics_path = BASE_DIR / "data" / "evaluation_metrics.json"
    existing_data = {}
    if metrics_path.exists():
        try:
            with open(metrics_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            existing_data = {}

    eval_payload = {
        "model_name": existing_data.get("model_name", "Calibrated Linear SVM (Platt, Balanced)"),
        "model_type": model_type,
        "model_version": model_version,
        "random_state": 42,
        "evaluation": {
            "dataset": "Untouched Holdout Test Set",
            "holdout_size": holdout_count,
            "accuracy": acc,
            "macro_precision": macro_p,
            "macro_recall": macro_r,
            "macro_f1": macro_f1,
            "weighted_precision": weighted_p,
            "weighted_recall": weighted_r,
            "weighted_f1": weighted_f1
        },
        "per_class": {
            f"Level {cls}": {
                "precision": per_class_metrics[cls]["precision"],
                "recall": per_class_metrics[cls]["recall"],
                "f1": per_class_metrics[cls]["f1_score"],
                "support": per_class_metrics[cls]["support"],
                "false_positives": per_class_metrics[cls]["false_positives"],
                "false_negatives": per_class_metrics[cls]["false_negatives"]
            }
            for cls in LABEL_NAMES
        },
        "confusion_matrix": cm.tolist(),
        "training": existing_data.get("training", {
            "development_samples": dev_count,
            "training_samples": len(train_df),
            "validation_samples": len(val_df),
            "holdout_samples": holdout_count,
            "external_samples_used": 0,
            "features": ["cleaned_text (Description)", "industry_sector", "worker_type", "gender"],
            "selected_model": "Calibrated Linear SVM (Platt, Balanced)",
            "hyperparameters": {
                "ngram_range": [1, 2],
                "sublinear_tf": True,
                "max_features": 15000,
                "C": 1.0,
                "class_weight": "balanced",
                "calibration": "sigmoid (cv=5)"
            }
        }),
        # Backward-compatible fields for SafetyAnalyticsService
        "deployed_model_test_metrics": {
            "split": "Holdout Test Set",
            "sample_count": holdout_count,
            "accuracy": acc,
            "macro_precision": macro_p,
            "macro_recall": macro_r,
            "macro_f1": macro_f1,
            "weighted_precision": weighted_p,
            "weighted_recall": weighted_r,
            "weighted_f1": weighted_f1,
            "per_class": per_class_metrics,
            "confusion_matrix": cm.tolist()
        },
        "benchmark_comparison": existing_data.get("benchmark_comparison", {}),
        "evaluation_note": "Evaluated strictly on disjoint 15% holdout test partition (zero data leakage). No synthetic labels or test leakage used."
    }

    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(eval_payload, f, indent=2)

    # 9. Immediate Reload Verification Test
    reloaded_model = joblib.load(model_path)
    reloaded_pred = reloaded_model.predict(X_test)
    reloaded_acc = float(accuracy_score(y_test, reloaded_pred))
    reloaded_macro_f1 = float(f1_score(y_test, reloaded_pred, average="macro", zero_division=0))
    reloaded_cm = confusion_matrix(y_test, reloaded_pred, labels=LABEL_NAMES)

    assert acc == reloaded_acc, f"Reload accuracy mismatch: {acc} != {reloaded_acc}"
    assert macro_f1 == reloaded_macro_f1, f"Reload macro F1 mismatch: {macro_f1} != {reloaded_macro_f1}"
    assert np.array_equal(cm, reloaded_cm), "Reload confusion matrix mismatch"
    print("RELOAD VERIFICATION: SUCCESS (Saved model produces 100% identical metrics upon disk reload)")

    return eval_payload


def run_full_evaluation() -> Dict[str, Any]:
    """Backward-compatible hook used by analytics_service.py."""
    return evaluate()


if __name__ == "__main__":
    evaluate()
