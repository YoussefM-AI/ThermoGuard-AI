"""
CabinetSense AI - Machine Learning Model Training Engine
Trains an unsupervised Isolation Forest on engineered industrial telemetry features.
Saves the serialized model artifact using Joblib.
"""

import os
import sys
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import joblib

# Ensure project root is available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ai.preprocessing import compute_engineered_features, extract_feature_matrix, FEATURE_NAMES
from ai.generate_dataset import generate_cabinet_dataset

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "cabinet_data.csv")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

def train_isolation_forest(
    dataset_path: str = DATA_PATH,
    n_estimators: int = 100,
    contamination: float = 0.05,
    random_state: int = 42
) -> dict:
    """
    Trains the Isolation Forest model on nominal operating conditions and saves the artifact.
    """
    print("=" * 60)
    print("  CabinetSense AI - Isolation Forest Model Training")
    print("=" * 60)

    # 1. Load or Generate Dataset
    if not os.path.exists(dataset_path):
        print(f"Dataset not found at {dataset_path}. Generating synthetic baseline dataset...")
        os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
        raw_df = generate_cabinet_dataset(n_samples=12000, anomaly_ratio=0.06)
        raw_df.to_csv(dataset_path, index=False)
    else:
        print(f"Loading telemetry dataset from: {dataset_path}")
        raw_df = pd.read_csv(dataset_path)

    print(f"Loaded {len(raw_df)} telemetry records.")

    # 2. Filter normal operating regime for unsupervised normal baseline learning
    # In real industrial settings, the model learns from historical verified normal operation
    if "is_anomaly" in raw_df.columns:
        normal_df = raw_df[raw_df["is_anomaly"] == 0].copy()
    else:
        normal_df = raw_df.copy()

    print(f"Training set size (nominal operational records): {len(normal_df)}")

    # 3. Feature Extraction
    print(f"Extracting features: {FEATURE_NAMES}")
    X_train, feature_cols = extract_feature_matrix(normal_df)

    # 4. Model Training
    print(f"Fitting IsolationForest(n_estimators={n_estimators}, contamination={contamination})...")
    clf = IsolationForest(
        n_estimators=n_estimators,
        max_samples="auto",
        contamination=contamination,
        random_state=random_state,
        n_jobs=-1
    )
    clf.fit(X_train)

    # Compute baseline score statistics on training set
    train_scores = clf.decision_function(X_train)
    min_score = float(np.min(train_scores))
    max_score = float(np.max(train_scores))
    mean_score = float(np.mean(train_scores))

    # 5. Serialization
    model_bundle = {
        "model": clf,
        "scaler": None, # Isolation Forest is tree-based and scale-invariant
        "features": feature_cols,
        "metadata": {
            "model_type": "IsolationForest",
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "training_samples": int(len(normal_df)),
            "n_estimators": n_estimators,
            "contamination": contamination,
            "score_stats": {
                "min": round(min_score, 4),
                "max": round(max_score, 4),
                "mean": round(mean_score, 4)
            }
        }
    }

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model_bundle, MODEL_PATH)
    print(f"Model artifact successfully saved to: {MODEL_PATH}")
    print(f"Training complete. Normal baseline decision score mean: {mean_score:.4f}")
    print("=" * 60)

    return model_bundle["metadata"]

if __name__ == "__main__":
    train_isolation_forest()
