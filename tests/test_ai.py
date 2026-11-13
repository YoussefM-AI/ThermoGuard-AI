"""
CabinetSense AI - AI Unit and Integration Test Suite
Validates model artifact loading, feature engineering, normal prediction,
anomaly sensitivity, and safe handling of missing/corrupted data.
"""

import os
import unittest
import numpy as np
import pandas as pd

from ai.predict import predict_anomaly, load_trained_model, get_model_info, MODEL_PATH
from ai.preprocessing import compute_engineered_features, extract_feature_matrix, FEATURE_NAMES
from ai.train_model import train_isolation_forest

class TestCabinetSenseAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Ensure model is trained and available
        if not os.path.exists(MODEL_PATH):
            train_isolation_forest(n_estimators=50)

    def test_model_loading_and_metadata(self):
        bundle = load_trained_model()
        self.assertIsNotNone(bundle)
        info = get_model_info()
        self.assertTrue(info["loaded"])
        self.assertEqual(info["status"], "OPERATIONAL")
        self.assertIn("Isolation Forest", info["model_name"])
        self.assertEqual(len(info["features"]), 6)

    def test_feature_engineering_pipeline(self):
        sample_df = pd.DataFrame({
            "temperature": [24.0, 24.2, 24.5, 25.0, 26.0],
            "humidity": [45.0, 44.8, 45.2, 45.0, 44.5]
        })
        feat_df = compute_engineered_features(sample_df, window_size=3)
        for col in FEATURE_NAMES:
            self.assertIn(col, feat_df.columns)
        
        # Verify delta calculation
        self.assertAlmostEqual(feat_df["delta_temperature"].iloc[1], 0.2)
        # Verify rolling avg
        self.assertAlmostEqual(feat_df["rolling_temp_avg"].iloc[0], 24.0)

        # Test matrix extraction
        X, names = extract_feature_matrix(sample_df)
        self.assertEqual(X.shape, (5, 6))
        self.assertEqual(names, FEATURE_NAMES)

    def test_missing_and_corrupt_data_handling(self):
        corrupt_df = pd.DataFrame({
            "temperature": [24.0, None, np.nan, 25.0],
            "humidity": [45.0, np.nan, 46.0, None]
        })
        clean_df = compute_engineered_features(corrupt_df)
        self.assertEqual(clean_df.isna().sum().sum(), 0)

    def test_normal_condition_prediction(self):
        # Nominal cabinet: 24.5C, 45%, zero delta, 24.5C rolling, 45% rolling
        vec = np.array([[24.5, 45.0, 0.0, 0.0, 24.5, 45.0]])
        result = predict_anomaly(vec)
        self.assertEqual(result["is_anomaly"], 0)
        self.assertGreater(result["anomaly_score"], 0.0) # Inlier score > 0
        self.assertIn("operational profile", result["explanation"].lower())

    def test_severe_thermal_anomaly_prediction(self):
        # Critical heat: 58.5C, 30% hum, +6.0C jump, -5% jump, 52C rolling, 33% rolling
        vec = np.array([[58.5, 30.0, 6.0, -5.0, 52.0, 33.0]])
        result = predict_anomaly(vec)
        self.assertEqual(result["is_anomaly"], 1)
        self.assertLess(result["anomaly_score"], 0.0) # Outlier score < 0
        self.assertIn("elevated", result["explanation"].lower())

    def test_severe_humidity_anomaly_prediction(self):
        # Enclosure seal breach: 25.0C, 92.0% hum, 0C jump, +15% jump, 25C rolling, 85% rolling
        vec = np.array([[25.0, 92.0, 0.0, 15.0, 25.0, 85.0]])
        result = predict_anomaly(vec)
        self.assertEqual(result["is_anomaly"], 1)
        self.assertLess(result["anomaly_score"], 0.0)
        self.assertIn("moisture", result["explanation"].lower())

if __name__ == "__main__":
    unittest.main()
