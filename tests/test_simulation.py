"""
ThermoGuard AI - Simulation Test Suite
Tests all 5 simulation scenarios and simulator functionality.
"""

import os
import sys
import unittest

# Ensure project root is available in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulation.scenarios import (
    SCENARIOS,
    AbnormalHumidityScenario,
    CombinedAnomalyScenario,
    GradualTempIncreaseScenario,
    NetworkInterruptionScenario,
    NormalScenario,
)
from simulation.simulator import CabinetSimulator


class TestSimulationScenarios(unittest.TestCase):
    def test_scenario_catalog(self):
        self.assertIn("normal", SCENARIOS)
        self.assertIn("gradual_temp", SCENARIOS)
        self.assertIn("abnormal_hum", SCENARIOS)
        self.assertIn("combined", SCENARIOS)
        self.assertIn("network_drop", SCENARIOS)

    def test_normal_scenario(self):
        sc = NormalScenario()
        for _ in range(30):
            r = sc.next_reading()
            self.assertIn("temperature", r)
            self.assertIn("humidity", r)
            self.assertIn("timestamp", r)
            self.assertEqual(r["source"], "SIMULATION")
            self.assertFalse(r["simulated_drop"])
            # In normal conditions, temp stays within 20 - 30 deg C, hum 35 - 55%
            self.assertGreaterEqual(r["temperature"], 18.0)
            self.assertLessEqual(r["temperature"], 32.0)
            self.assertGreaterEqual(r["humidity"], 30.0)
            self.assertLessEqual(r["humidity"], 60.0)

    def test_gradual_temp_scenario(self):
        sc = GradualTempIncreaseScenario()
        first_readings = [sc.next_reading()["temperature"] for _ in range(5)]
        later_readings = [sc.next_reading()["temperature"] for _ in range(25)]
        # Initial readings are normal (~25C), later readings climb significantly
        self.assertLess(sum(first_readings) / len(first_readings), sum(later_readings) / len(later_readings))
        self.assertGreater(later_readings[-1], 30.0)

    def test_abnormal_humidity_scenario(self):
        sc = AbnormalHumidityScenario()
        first_hum = [sc.next_reading()["humidity"] for _ in range(5)]
        later_hum = [sc.next_reading()["humidity"] for _ in range(25)]
        self.assertLess(sum(first_hum) / len(first_hum), sum(later_hum) / len(later_hum))
        self.assertGreater(later_hum[-1], 65.0)

    def test_combined_anomaly_scenario(self):
        sc = CombinedAnomalyScenario()
        readings = [sc.next_reading() for _ in range(30)]
        final_temp = readings[-1]["temperature"]
        final_hum = readings[-1]["humidity"]
        self.assertGreater(final_temp, 35.0)
        self.assertGreater(final_hum, 65.0)

    def test_network_interruption_scenario(self):
        sc = NetworkInterruptionScenario()
        dropped_count = 0
        normal_count = 0
        for _ in range(15):
            r = sc.next_reading()
            if r["simulated_drop"]:
                dropped_count += 1
                self.assertIsNone(r["temperature"])
                self.assertIsNone(r["humidity"])
            else:
                normal_count += 1
                self.assertIsNotNone(r["temperature"])
                self.assertIsNotNone(r["humidity"])
        self.assertEqual(dropped_count, 5)  # Steps 5 to 9
        self.assertEqual(normal_count, 10)

    def test_simulator_controller(self):
        sim = CabinetSimulator(server_url="http://127.0.0.1:5000", interval=0.5, scenario_key="normal")
        status = sim.get_status()
        self.assertFalse(status["running"])
        self.assertEqual(status["scenario_key"], "normal")

        # Test scenario switching
        success = sim.set_scenario("gradual_temp")
        self.assertTrue(success)
        self.assertEqual(sim.scenario_key, "gradual_temp")

        # Test invalid scenario
        self.assertFalse(sim.set_scenario("non_existent"))


if __name__ == "__main__":
    unittest.main()
