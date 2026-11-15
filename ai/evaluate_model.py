"""
ThermoGuard AI - AI Model Evaluation Engine
Evaluates the trained Isolation Forest against labeled synthetic test datasets.
Outputs confusion matrix, precision, recall, F1-score, and critical industrial limitations.
"""

import os
import sys

# Ensure project root is available
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import joblib  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import (  # noqa: E402
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from ai.generate_dataset import generate_cabinet_dataset  # noqa: E402
from ai.predict import MODEL_PATH  # noqa: E402
from ai.preprocessing import extract_feature_matrix  # noqa: E402


def evaluate_model(test_dataset_path: str | None = None) -> dict:
    print("=" * 65)
    print("  ThermoGuard AI - Anomaly Detection Model Evaluation")
    print("=" * 65)

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Trained model not found at {MODEL_PATH}. Run train_model.py first.")

    model_bundle = joblib.load(MODEL_PATH)
    clf = model_bundle["model"] if isinstance(model_bundle, dict) else model_bundle

    # 1. Load or Generate Independent Test Set
    if test_dataset_path and os.path.exists(test_dataset_path):
        print(f"Loading test set from: {test_dataset_path}")
        test_df = pd.read_csv(test_dataset_path)
    else:
        print("Generating independent synthetic evaluation test set (4,000 samples, 8% anomaly ratio, seed=99)...")
        test_df = generate_cabinet_dataset(n_samples=4000, anomaly_ratio=0.08, random_seed=99)

    y_true = test_df["is_anomaly"].to_numpy(dtype=int)

    # 2. Extract Features
    X_test, _features = extract_feature_matrix(test_df)

    # 3. Predict Outliers
    # IsolationForest: 1 for normal (inlier), -1 for anomaly (outlier)
    raw_preds = clf.predict(X_test)
    y_pred = np.where(raw_preds == -1, 1, 0)  # Map to binary 0/1

    # 4. Metrics
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred)

    print("\n[CONFUSION MATRIX]")
    print("                  Predicted Normal (0)   Predicted Anomaly (1)")
    print(f"  Actual Normal (0)      {cm[0, 0]:<15}         {cm[0, 1]:<15}")
    print(f"  Actual Anomaly (1)     {cm[1, 0]:<15}         {cm[1, 1]:<15}")

    print("\n[PERFORMANCE METRICS]")
    print(f"  Accuracy  : {acc * 100:.2f}%")
    print(f"  Precision : {prec * 100:.2f}% (Out of flagged anomalies, how many were true anomalies)")
    print(f"  Recall    : {rec * 100:.2f}% (Out of true anomalies, how many were captured)")
    print(f"  F1-Score  : {f1 * 100:.2f}% (Harmonic mean of precision and recall)")

    print("\n[DETAILED CLASSIFICATION REPORT]")
    print(classification_report(y_true, y_pred, target_names=["Normal (0)", "Anomaly (1)"]))

    print("-" * 65)
    print("ACADEMIC & INDUSTRIAL NOTES ON SYNTHETIC EVALUATION:")
    print("1. Synthetic test evaluation provides structural algorithmic verification.")
    print("2. It validates that the unsupervised Isolation Forest partitions high-heat,")
    print("   high-moisture, and sudden delta variations into low-density outlier subspaces.")
    print("3. In a real factory cabinet, environmental noise includes variable seasonal weather,")
    print("   door opening maintenance, and differing transformer electrical loads.")
    print("4. This model detects environmental anomalies; it does NOT diagnose internal")
    print("   electrical component faults or substitute for certified safety interlocks.")
    print("=" * 65)

    return {
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "confusion_matrix": cm.tolist(),
    }


if __name__ == "__main__":
    evaluate_model()
