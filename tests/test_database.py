"""
ThermoGuard AI - Database Unit Test Suite
Validates schema creation, CRUD operations, indexing, and deduplication logic.
"""

import os
import sys
import tempfile
import unittest

# Ensure project root is available in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import (
    acknowledge_alert,
    get_alerts,
    get_analytics_summary,
    get_24h_summary,
    get_latest_reading,
    get_readings,
    init_db,
    insert_alert,
    insert_reading,
)


class TestThermoGuardDatabase(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary database for each test
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

    def tearDown(self):
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_insert_and_retrieve_reading(self):
        result = insert_reading(
            temperature=25.4, humidity=46.2, source="HARDWARE", is_anomaly=0, anomaly_score=0.12, db_path=self.temp_db_path
        )
        self.assertIn("id", result)
        self.assertEqual(result["temperature"], 25.4)
        self.assertEqual(result["humidity"], 46.2)
        self.assertEqual(result["source"], "HARDWARE")

        # Retrieve latest
        latest = get_latest_reading(db_path=self.temp_db_path)
        self.assertIsNotNone(latest)
        self.assertEqual(latest["id"], result["id"])
        self.assertEqual(latest["temperature"], 25.4)

    def test_deduplication(self):
        # First insert
        r1 = insert_reading(24.0, 45.0, "SIMULATION", db_path=self.temp_db_path)
        self.assertIn("id", r1)

        # Immediate identical insert within deduplication window
        r2 = insert_reading(24.0, 45.0, "SIMULATION", db_path=self.temp_db_path)
        self.assertTrue(r2.get("duplicate"))

        # Verify only 1 reading exists
        readings = get_readings(db_path=self.temp_db_path)
        self.assertEqual(len(readings), 1)

    def test_alerts_lifecycle(self):
        alert = insert_alert(
            severity="CRITICAL",
            message="Cabinet temperature 58C exceeded threshold",
            temperature=58.0,
            humidity=42.0,
            anomaly_score=-0.45,
            db_path=self.temp_db_path,
        )
        self.assertIn("id", alert)
        self.assertEqual(alert["severity"], "CRITICAL")
        self.assertEqual(alert["status"], "UNRESOLVED")

        # Query alert
        alerts = get_alerts(status="UNRESOLVED", db_path=self.temp_db_path)
        self.assertEqual(len(alerts), 1)

        # Acknowledge alert
        success = acknowledge_alert(alert["id"], db_path=self.temp_db_path)
        self.assertTrue(success)

        # Confirm status updated
        unresolved = get_alerts(status="UNRESOLVED", db_path=self.temp_db_path)
        self.assertEqual(len(unresolved), 0)
        ack = get_alerts(status="ACKNOWLEDGED", db_path=self.temp_db_path)
        self.assertEqual(len(ack), 1)

    def test_analytics_calculation(self):
        # Insert 3 readings: 2 normal, 1 anomaly
        insert_reading(20.0, 40.0, "SIMULATION", is_anomaly=0, db_path=self.temp_db_path)
        insert_reading(30.0, 50.0, "HARDWARE", is_anomaly=0, db_path=self.temp_db_path)
        insert_reading(40.0, 60.0, "SIMULATION", is_anomaly=1, db_path=self.temp_db_path)

        summary = get_analytics_summary(db_path=self.temp_db_path)
        self.assertEqual(summary["readings_count"], 3)
        self.assertEqual(summary["anomalies_count"], 1)
        self.assertAlmostEqual(summary["temperature"]["min"], 20.0)
        self.assertAlmostEqual(summary["temperature"]["max"], 40.0)
        self.assertAlmostEqual(summary["temperature"]["avg"], 30.0)
        self.assertEqual(summary["sources"]["hardware"], 1)
        self.assertEqual(summary["sources"]["simulation"], 2)

        # Verify 24-hour window summary
        summary_24h = get_24h_summary(db_path=self.temp_db_path)
        self.assertEqual(summary_24h["readings_count"], 3)
        self.assertEqual(summary_24h["anomalies_count"], 1)
        self.assertEqual(summary_24h["window_hours"], 24.0)


if __name__ == "__main__":
    unittest.main()
