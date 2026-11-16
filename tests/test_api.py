"""
ThermoGuard AI - REST API Endpoint Test Suite
Tests all endpoints using Flask's test client on an isolated database.
"""

import os
import sys
import tempfile
import unittest

# Ensure project root is available in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import create_app


class TestThermoGuardAPI(unittest.TestCase):
    def setUp(self):
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        self.app = create_app(test_config={"TESTING": True, "DATABASE": self.temp_db_path})
        self.client = self.app.test_client()

    def tearDown(self):
        os.close(self.temp_db_fd)
        try:
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    def test_health_endpoint(self):
        resp = self.client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["database"], "connected")

    def test_post_reading_valid(self):
        payload = {"temperature": 25.5, "humidity": 45.2, "source": "HARDWARE"}
        resp = self.client.post("/api/readings", json=payload)
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["data"]["reading"]["temperature"], 25.5)
        self.assertEqual(data["data"]["reading"]["source"], "HARDWARE")

    def test_post_reading_invalid(self):
        # Missing fields
        resp = self.client.post("/api/readings", json={"temperature": 25.0})
        self.assertEqual(resp.status_code, 400)

        # Out-of-bounds temperature
        resp = self.client.post("/api/readings", json={"temperature": 999.0, "humidity": 50.0})
        self.assertEqual(resp.status_code, 400)

        # Non-numeric
        resp = self.client.post("/api/readings", json={"temperature": "hot", "humidity": 50.0})
        self.assertEqual(resp.status_code, 400)

    def test_get_readings_and_latest(self):
        self.client.post("/api/readings", json={"temperature": 24.1, "humidity": 44.0, "source": "SIMULATION"})
        self.client.post("/api/readings", json={"temperature": 26.2, "humidity": 46.5, "source": "HARDWARE"})

        # Get list
        resp = self.client.get("/api/readings")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreaterEqual(data["count"], 2)

        # Get latest
        resp_latest = self.client.get("/api/readings/latest")
        self.assertEqual(resp_latest.status_code, 200)
        latest_data = resp_latest.get_json()
        self.assertIsNotNone(latest_data["reading"])
        self.assertEqual(latest_data["reading"]["temperature"], 26.2)

    def test_system_status(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("monitoring_mode", data)
        self.assertIn("hardware", data)
        self.assertIn("ai", data)

    def test_alerts_and_acknowledgement(self):
        # Trigger an alert by sending high critical temperature
        resp = self.client.post("/api/readings", json={"temperature": 60.0, "humidity": 40.0, "source": "HARDWARE"})
        self.assertEqual(resp.status_code, 201)

        # Fetch alerts
        resp_alerts = self.client.get("/api/alerts")
        self.assertEqual(resp_alerts.status_code, 200)
        alerts_data = resp_alerts.get_json()
        self.assertGreaterEqual(len(alerts_data["alerts"]), 1)
        alert_id = alerts_data["alerts"][0]["id"]

        # Acknowledge alert
        resp_ack = self.client.post(f"/api/alerts/{alert_id}/acknowledge")
        self.assertEqual(resp_ack.status_code, 200)

        # Test bulk acknowledge-all endpoint
        resp_bulk = self.client.post("/api/alerts/acknowledge-all")
        self.assertEqual(resp_bulk.status_code, 200)
        self.assertIn("count", resp_bulk.get_json())

    def test_analytics_and_export(self):
        # Insert a reading
        self.client.post("/api/readings", json={"temperature": 25.0, "humidity": 45.0, "source": "HARDWARE"})

        # Analytics
        resp = self.client.get("/api/analytics")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("analytics", data)
        self.assertGreaterEqual(data["analytics"]["readings_count"], 1)

        # CSV Export
        resp_csv = self.client.get("/api/export/csv")
        self.assertEqual(resp_csv.status_code, 200)
        self.assertEqual(resp_csv.mimetype, "text/csv")
        self.assertIn(b"Temperature", resp_csv.data)


if __name__ == "__main__":
    unittest.main()
