"""
ThermoGuard AI - Frontend Integration & Static Asset Test Suite
Validates that HTML5, CSS3, and JavaScript assets exist, contain the streamlined SPA views,
and are served correctly by the Flask web application.
"""

import os
import sys
import tempfile
import unittest

# Ensure project root is available in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app import create_app


class TestThermoGuardFrontend(unittest.TestCase):
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

    def test_serve_index_html(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        resp.close()
        self.assertIn("ThermoGuard", html)
        self.assertIn("Operational Dashboard", html)

        views = [
            "view-dashboard",
            "view-history",
            "view-alerts",
            "view-settings",
        ]
        for v in views:
            self.assertIn(f'id="{v}"', html, f"Missing view section: {v}")

    def test_serve_css_and_js(self):
        resp_css = self.client.get("/style.css")
        self.assertEqual(resp_css.status_code, 200)
        self.assertIn(b"--bg-base", resp_css.data)
        resp_css.close()

        resp_js = self.client.get("/script.js")
        self.assertEqual(resp_js.status_code, 200)
        self.assertIn(b"ThermoGuardApp", resp_js.data)
        self.assertIn(b"CabinetSenseApp", resp_js.data)
        resp_js.close()

    def test_hardware_node_rendered_in_html(self):
        resp = self.client.get("/")
        html = resp.data.decode("utf-8")
        resp.close()
        self.assertIn("ESP32", html)
        self.assertIn("/api/readings", html)


if __name__ == "__main__":
    unittest.main()
