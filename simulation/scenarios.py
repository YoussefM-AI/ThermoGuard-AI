"""
ThermoGuard AI - Simulation Scenarios Engine
Defines 5 realistic environmental simulation scenarios for industrial electrical cabinets.
"""

import math
import random
from datetime import UTC, datetime


class BaseScenario:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.step_count = 0
        self.base_temp = 24.5
        self.base_hum = 45.0

    def reset(self):
        self.step_count = 0

    def next_reading(self) -> dict:
        raise NotImplementedError


class NormalScenario(BaseScenario):
    """
    Scenario 1: Normal Conditions
    Steady state: Temperature ~24.5°C (±1.5°C), Humidity ~45% (±3%),
    with subtle diurnal sine variations and natural Gaussian noise.
    """

    def __init__(self):
        super().__init__("Normal Conditions", "Standard cabinet operation with nominal climate control.")

    def next_reading(self) -> dict:
        self.step_count += 1
        # Subtle harmonic diurnal cycle
        diurnal = 0.8 * math.sin(self.step_count / 15.0)
        temp = self.base_temp + diurnal + random.gauss(0, 0.25)
        hum = self.base_hum - (0.5 * diurnal) + random.gauss(0, 0.45)

        # Physical bounding
        temp = max(18.0, min(32.0, temp))
        hum = max(30.0, min(60.0, hum))

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "temperature": round(temp, 2),
            "humidity": round(hum, 2),
            "source": "SIMULATION",
            "scenario": self.name,
            "simulated_drop": False,
        }


class GradualTempIncreaseScenario(BaseScenario):
    """
    Scenario 2: Gradual Temperature Increase
    Simulates equipment overload, ventilation dust blockage, or cooling fan degradation.
    Temperature creeps up progressively by 0.3°C - 0.7°C per step up to 55°C+.
    """

    def __init__(self):
        super().__init__("Gradual Temperature Increase", "Thermal accumulation from cabinet fan failure or high electrical load.")

    def next_reading(self) -> dict:
        self.step_count += 1
        # First 5 steps are normal, then heat accumulates
        if self.step_count <= 5:
            temp_offset = random.gauss(0, 0.2)
        else:
            temp_offset = (self.step_count - 5) * 0.55 + random.gauss(0, 0.3)

        temp = self.base_temp + temp_offset
        # As temperature rises, relative humidity tends to drop slightly
        hum = self.base_hum - (temp_offset * 0.35) + random.gauss(0, 0.5)

        temp = min(68.0, max(20.0, temp))
        hum = max(15.0, min(70.0, hum))

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "temperature": round(temp, 2),
            "humidity": round(hum, 2),
            "source": "SIMULATION",
            "scenario": self.name,
            "simulated_drop": False,
        }


class AbnormalHumidityScenario(BaseScenario):
    """
    Scenario 3: Abnormal Humidity
    Simulates cabinet enclosure seal degradation, water infiltration, or high ambient humidity.
    Humidity surges from 45% up to 80% - 92%.
    """

    def __init__(self):
        super().__init__(
            "Abnormal Humidity", "Moisture ingress or exterior seal breach exposing electronics to condensation risks."
        )

    def next_reading(self) -> dict:
        self.step_count += 1
        if self.step_count <= 5:
            hum_offset = random.gauss(0, 0.4)
        else:
            hum_offset = (self.step_count - 5) * 2.2 + random.gauss(0, 0.6)

        hum = self.base_hum + hum_offset
        temp = self.base_temp + random.gauss(0, 0.3)

        temp = max(18.0, min(35.0, temp))
        hum = min(95.0, max(30.0, hum))

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "temperature": round(temp, 2),
            "humidity": round(hum, 2),
            "source": "SIMULATION",
            "scenario": self.name,
            "simulated_drop": False,
        }


class CombinedAnomalyScenario(BaseScenario):
    """
    Scenario 4: Combined Anomaly
    Simulates severe combined environmental distress: both extreme heat and sharp humidity swings.
    """

    def __init__(self):
        super().__init__("Combined Anomaly", "Simultaneous extreme thermal elevation and humidity volatility.")

    def next_reading(self) -> dict:
        self.step_count += 1
        if self.step_count <= 4:
            temp = self.base_temp + random.gauss(0, 0.3)
            hum = self.base_hum + random.gauss(0, 0.5)
        else:
            drift = self.step_count - 4
            temp = self.base_temp + (drift * 0.8) + random.gauss(0, 0.4)
            hum = self.base_hum + (drift * 1.5) + random.gauss(0, 0.7)

        temp = min(72.0, max(20.0, temp))
        hum = min(96.0, max(20.0, hum))

        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "temperature": round(temp, 2),
            "humidity": round(hum, 2),
            "source": "SIMULATION",
            "scenario": self.name,
            "simulated_drop": False,
        }


class NetworkInterruptionScenario(BaseScenario):
    """
    Scenario 5: Sensor or Network Interruption
    Simulates transient hardware loss, disconnected Wi-Fi, or cable fault.
    After 4 normal readings, it withholds transmissions for 5 steps, then resumes.
    """

    def __init__(self):
        super().__init__("Sensor / Network Interruption", "Intermittent communication loss or sensor disconnect.")

    def next_reading(self) -> dict:
        self.step_count += 1
        # Steps 5 to 9 simulate packet drops
        if 5 <= self.step_count <= 9:
            return {
                "timestamp": datetime.now(UTC).isoformat(),
                "temperature": None,
                "humidity": None,
                "source": "SIMULATION",
                "scenario": self.name,
                "simulated_drop": True,
            }

        temp = self.base_temp + random.gauss(0, 0.3)
        hum = self.base_hum + random.gauss(0, 0.5)
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "temperature": round(temp, 2),
            "humidity": round(hum, 2),
            "source": "SIMULATION",
            "scenario": self.name,
            "simulated_drop": False,
        }


SCENARIOS = {
    "normal": NormalScenario,
    "gradual_temp": GradualTempIncreaseScenario,
    "abnormal_hum": AbnormalHumidityScenario,
    "combined": CombinedAnomalyScenario,
    "network_drop": NetworkInterruptionScenario,
}


def get_scenario(key: str) -> BaseScenario:
    scenario_class = SCENARIOS.get(key, NormalScenario)
    return scenario_class()
