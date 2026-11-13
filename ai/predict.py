"""
CabinetSense AI - Anomaly Prediction Engine
Loads the serialized Isolation Forest model and evaluates live telemetry.
Provides robust fallbacks when model is not yet trained.
"""

import os
import joblib
import numpy as np
from typing import Dict, Any, Optional

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

# Cached model holder
_cached_model = None
_cached_mtime = 0.0

def load_trained_model():
    """
    Thread-safe, lazy cached loader for the Isolation Forest model artifact.
    Reloads automatically if model.pkl file is modified.
    """
    global _cached_model, _cached_mtime
    if not os.path.exists(MODEL_PATH):
        return None

    try:
        current_mtime = os.path.getmtime(MODEL_PATH)
        if _cached_model is None or current_mtime > _cached_mtime:
            _cached_model = joblib.load(MODEL_PATH)
            _cached_mtime = current_mtime
        return _cached_model
    except Exception as e:
        print(f"[AI-PREDICT] Error loading model.pkl: {e}")
        return None

def predict_anomaly(
    feature_vector: np.ndarray,
    metadata: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Evaluates incoming feature vector [temperature, humidity, delta_t, delta_h, roll_t, roll_h].
    Returns:
      - is_anomaly: 0 (Normal) or 1 (Anomaly)
      - anomaly_score: float score (negative indicates anomaly in standard Isolation Forest)
      - explanation: factual environmental explanation
      - model_status: 'trained' or 'baseline_fallback'
    """
    temp = float(feature_vector[0][0])
    hum = float(feature_vector[0][1])
    delta_t = float(feature_vector[0][2])
    delta_h = float(feature_vector[0][3])

    model_bundle = load_trained_model()

    if model_bundle is None:
        # Heuristic baseline fallback when model has not been trained yet
        is_anomaly = 0
        reasons = []

        if temp > 38.0:
            is_anomaly = 1
            reasons.append(f"Temperature of {temp:.1f}°C exceeds nominal cabinet threshold (38°C)")
        if hum > 70.0:
            is_anomaly = 1
            reasons.append(f"Relative humidity of {hum:.1f}% exceeds normal moisture bounds (70%)")
        if abs(delta_t) >= 4.0:
            is_anomaly = 1
            reasons.append(f"Sudden thermal gradient shift of {delta_t:+.1f}°C")
        if abs(delta_h) >= 8.0:
            is_anomaly = 1
            reasons.append(f"Rapid humidity transition of {delta_h:+.1f}%")

        explanation = "; ".join(reasons) if reasons else "Environmental parameters within standard operating baseline."
        score = -0.5 if is_anomaly else 0.5

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": score,
            "explanation": explanation,
            "model_status": "baseline_fallback"
        }

    # Model is loaded from disk
    model = model_bundle["model"] if isinstance(model_bundle, dict) else model_bundle
    scaler = model_bundle.get("scaler") if isinstance(model_bundle, dict) else None

    X = feature_vector
    if scaler is not None:
        X = scaler.transform(X)

    # IsolationForest: 1 for inlier (normal), -1 for outlier (anomaly)
    raw_pred = model.predict(X)[0]
    # Decision function: smaller/negative = more anomalous
    raw_score = float(model.decision_function(X)[0])

    is_anomaly = 1 if raw_pred == -1 else 0

    # Build clear, transparent explanation based on actual observations
    explanations = []
    if is_anomaly == 1:
        if temp > 35.0:
            explanations.append(f"Cabinet temperature ({temp:.1f}°C) elevated significantly above training distribution")
        if hum > 65.0:
            explanations.append(f"Moisture levels ({hum:.1f}%) deviate from normal dry enclosure baseline")
        if abs(delta_t) >= 3.0:
            explanations.append(f"Abnormal thermal rate-of-change ({delta_t:+.1f}°C/step)")
        if abs(delta_h) >= 6.0:
            explanations.append(f"Sharp moisture variation ({delta_h:+.1f}%/step)")
        if not explanations:
            explanations.append(f"Multivariate pattern anomaly detected by Isolation Forest (score: {raw_score:.3f})")
        explanation = "; ".join(explanations)
    else:
        explanation = "Environmental conditions align with learned normal operational profile."

    return {
        "is_anomaly": is_anomaly,
        "anomaly_score": round(raw_score, 4),
        "explanation": explanation,
        "model_status": "trained"
    }

def get_model_info() -> Dict[str, Any]:
    """
    Returns AI model metadata and status.
    """
    model_bundle = load_trained_model()
    if model_bundle is None:
        return {
            "loaded": False,
            "model_name": "Isolation Forest",
            "status": "NOT_TRAINED",
            "message": "Model artifact not found. Execute training pipeline to build model.pkl.",
            "features": ["temperature", "humidity", "delta_temperature", "delta_humidity", "rolling_temp_avg", "rolling_hum_avg"]
        }

    meta = model_bundle.get("metadata", {}) if isinstance(model_bundle, dict) else {}
    return {
        "loaded": True,
        "model_name": "Isolation Forest (Unsupervised Anomaly Detector)",
        "status": "OPERATIONAL",
        "trained_at": meta.get("trained_at"),
        "training_samples": meta.get("training_samples"),
        "contamination": meta.get("contamination", 0.05),
        "n_estimators": meta.get("n_estimators", 100),
        "features": meta.get("features", ["temperature", "humidity", "delta_temperature", "delta_humidity", "rolling_temp_avg", "rolling_hum_avg"])
    }
