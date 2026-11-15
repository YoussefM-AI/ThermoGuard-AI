"""
ThermoGuard AI - Sensor Simulator Runner
Sends realistic simulated telemetry to the ThermoGuard Flask REST API.
Can be run via CLI or driven asynchronously from the backend API.
"""

import argparse
import os
import sys
import threading
import time

# Add project root to sys.path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import requests  # noqa: E402
from simulation.scenarios import SCENARIOS, get_scenario  # noqa: E402


class ThermoGuardSimulator:
    def __init__(self, server_url: str = "http://127.0.0.1:5000", interval: float = 2.0, scenario_key: str = "normal"):
        self.server_url = server_url.rstrip("/")
        self.interval = max(0.2, interval)
        self.scenario_key = scenario_key
        self.scenario = get_scenario(scenario_key)
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self.last_sent = None
        self.sent_count = 0
        self.error_count = 0
        self.status_message = "Idle"

    def set_scenario(self, scenario_key: str):
        with self._lock:
            if scenario_key in SCENARIOS:
                self.scenario_key = scenario_key
                self.scenario = get_scenario(scenario_key)
                self.status_message = f"Scenario set to {self.scenario.name}"
                return True
            return False

    def set_interval(self, interval: float):
        with self._lock:
            self.interval = max(0.2, float(interval))
            self.status_message = f"Interval set to {self.interval}s"

    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> dict:
        with self._lock:
            return {
                "running": self._running,
                "scenario_key": self.scenario_key,
                "scenario_name": self.scenario.name,
                "interval": self.interval,
                "sent_count": self.sent_count,
                "error_count": self.error_count,
                "last_sent": self.last_sent,
                "status_message": self.status_message,
            }

    def start(self):
        with self._lock:
            if self._running:
                return False
            self._running = True
            self.status_message = f"Running scenario: {self.scenario.name}"
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            return True

    def stop(self):
        with self._lock:
            if not self._running:
                return False
            self._running = False
            self.status_message = "Stopped"
            return True

    def _run_loop(self):
        endpoint = f"{self.server_url}/api/readings"
        while self._running:
            start_time = time.time()
            reading = self.scenario.next_reading()

            if reading.get("simulated_drop"):
                self.status_message = "Simulated network/sensor packet drop (no transmission sent)"
                self.last_sent = {"timestamp": reading["timestamp"], "temperature": None, "humidity": None, "status": "DROPPED"}
            else:
                payload = {"temperature": reading["temperature"], "humidity": reading["humidity"], "source": "SIMULATION"}

                delivered = False
                # 1. In-process direct processing (zero network latency, bypasses loopback port/firewall issues)
                try:
                    from backend.services import process_telemetry_reading

                    result = process_telemetry_reading(payload, client_ip="127.0.0.1")
                    if result.get("status") != "ignored":
                        self.sent_count += 1
                        self.last_sent = {
                            "timestamp": reading["timestamp"],
                            "temperature": reading["temperature"],
                            "humidity": reading["humidity"],
                            "status": "DELIVERED",
                            "http_code": 201,
                            "response": result,
                        }
                        self.status_message = f"Delivered reading: {reading['temperature']}°C, {reading['humidity']}%"
                        delivered = True
                    else:
                        # Ignored duplicate within debounce window
                        delivered = True
                except (ImportError, RuntimeError, KeyError, ValueError, TypeError):
                    delivered = False

                # 2. HTTP POST fallback for standalone CLI execution or remote instances
                if not delivered:
                    try:
                        resp = requests.post(endpoint, json=payload, timeout=2.5)
                        if resp.status_code in (200, 201):
                            self.sent_count += 1
                            self.last_sent = {
                                "timestamp": reading["timestamp"],
                                "temperature": reading["temperature"],
                                "humidity": reading["humidity"],
                                "status": "DELIVERED",
                                "http_code": resp.status_code,
                                "response": resp.json(),
                            }
                            self.status_message = f"Delivered reading: {reading['temperature']}°C, {reading['humidity']}%"
                        else:
                            self.error_count += 1
                            self.status_message = f"Server returned status {resp.status_code}"
                    except requests.exceptions.RequestException as e:
                        self.error_count += 1
                        self.status_message = f"Connection error: {e.__class__.__name__}"
                        self.last_sent = {
                            "timestamp": reading["timestamp"],
                            "temperature": reading["temperature"],
                            "humidity": reading["humidity"],
                            "status": "FAILED_CONNECTION",
                        }

            # Sleep remaining time
            elapsed = time.time() - start_time
            sleep_duration = max(0.05, self.interval - elapsed)
            time.sleep(sleep_duration)


# Backward compatibility alias
CabinetSimulator = ThermoGuardSimulator

# Global singleton simulator for backend-driven operation
simulator_instance = ThermoGuardSimulator()


def main():
    parser = argparse.ArgumentParser(description="ThermoGuard AI Sensor Simulator")
    parser.add_argument("--scenario", choices=list(SCENARIOS.keys()), default="normal", help="Simulation scenario")
    parser.add_argument("--interval", type=float, default=2.0, help="Transmission cadence in seconds")
    parser.add_argument("--server", default="http://127.0.0.1:5000", help="Flask backend URL")
    parser.add_argument("--steps", type=int, default=10, help="Number of steps (0 for infinite)")
    args = parser.parse_args()

    print(f"Starting ThermoGuard AI Simulator -> {args.server}")
    print(f"Scenario: {args.scenario} | Interval: {args.interval}s | Steps: {args.steps}")

    scenario = get_scenario(args.scenario)
    step = 0
    while args.steps == 0 or step < args.steps:
        step += 1
        data = scenario.next_reading()
        if data.get("simulated_drop"):
            print(f"[{step}] [DROPPED] Simulated network packet drop.")
        else:
            payload = {"temperature": data["temperature"], "humidity": data["humidity"], "source": "SIMULATION"}
            try:
                resp = requests.post(f"{args.server.rstrip('/')}/api/readings", json=payload, timeout=2.0)
                print(
                    f"[{step}] [HTTP {resp.status_code}] Sent: {payload['temperature']}°C, {payload['humidity']}% -> Server: {resp.text}"
                )
            except requests.exceptions.RequestException as e:
                print(
                    f"[{step}] [LOCAL-MODE] Generated: {payload['temperature']}°C, {payload['humidity']}% (Server unreachable: {e.__class__.__name__})"
                )
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
