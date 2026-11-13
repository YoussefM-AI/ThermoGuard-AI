"""
CabinetSense AI - Backend Business & ML Integration Services
Handles telemetry validation, hardware connection tracking, AI model interfacing,
feature buffer management, and intelligent alert triggering.
"""

import os
import sys
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, Optional, List
import numpy as np

# Ensure root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import (
    insert_reading,
    insert_alert,
    insert_system_event,
    get_latest_reading,
    get_readings
)

# Reference Thresholds for Industrial Cabinet (Physical Baseline & Sensor limits)
SENSOR_LIMITS = {
    "temp_min": -10.0,
    "temp_max": 90.0,
    "hum_min": 0.0,
    "hum_max": 100.0
}

CABINET_THRESHOLDS = {
    "temp_warning": 38.0,
    "temp_critical": 52.0,
    "hum_warning": 70.0,
    "hum_critical": 85.0
}

class TelemetryBuffer:
    """
    Maintains a thread-safe rolling window of recent readings
    to compute rolling averages and differential features for the ML model.
    """
    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self._buffer: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, reading: Dict[str, Any]):
        with self._lock:
            self._buffer.append(reading)
            if len(self._buffer) > self.max_size:
                self._buffer.pop(0)

    def get_features(self, current_temp: float, current_hum: float) -> Tuple[np.ndarray, Dict[str, float]]:
        with self._lock:
            if not self._buffer:
                # Cold start: deltas are 0, rolling equals current
                delta_temp = 0.0
                delta_hum = 0.0
                rolling_temp = current_temp
                rolling_hum = current_hum
            else:
                last_reading = self._buffer[-1]
                delta_temp = current_temp - last_reading["temperature"]
                delta_hum = current_hum - last_reading["humidity"]
                
                recent_temps = [r["temperature"] for r in self._buffer] + [current_temp]
                recent_hums = [r["humidity"] for r in self._buffer] + [current_hum]
                
                rolling_temp = float(np.mean(recent_temps))
                rolling_hum = float(np.mean(recent_hums))

        features_dict = {
            "temperature": current_temp,
            "humidity": current_hum,
            "delta_temperature": delta_temp,
            "delta_humidity": delta_hum,
            "rolling_temp_avg": rolling_temp,
            "rolling_hum_avg": rolling_hum
        }
        
        feature_vector = np.array([[
            current_temp,
            current_hum,
            delta_temp,
            delta_hum,
            rolling_temp,
            rolling_hum
        ]])

        return feature_vector, features_dict

telemetry_buffer = TelemetryBuffer(max_size=15)

class HardwareTracker:
    """
    Tracks the active connection status of the ESP32 hardware and simulator.
    """
    def __init__(self):
        self._last_hardware_time: Optional[datetime] = None
        self._last_hardware_ip: Optional[str] = None
        self._lock = threading.Lock()

    def record_hardware_ping(self, client_ip: str):
        with self._lock:
            self._last_hardware_time = datetime.now(timezone.utc)
            self._last_hardware_ip = client_ip

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            if self._last_hardware_time is None:
                return {
                    "connected": False,
                    "status": "DISCONNECTED",
                    "last_seen_seconds": None,
                    "client_ip": None
                }
            
            elapsed = (datetime.now(timezone.utc) - self._last_hardware_time).total_seconds()
            is_connected = elapsed <= 15.0 # Consider disconnected if no ping in 15 seconds
            
            return {
                "connected": is_connected,
                "status": "ONLINE" if is_connected else "TIMEOUT",
                "last_seen_seconds": round(elapsed, 1),
                "client_ip": self._last_hardware_ip
            }

hardware_tracker = HardwareTracker()

# Alert debouncer to avoid flooding logs with the exact same alert within 30 seconds
class AlertDebouncer:
    def __init__(self, cooldown_seconds: float = 30.0):
        self.cooldown = cooldown_seconds
        self._last_alerts: Dict[str, datetime] = {}
        self._lock = threading.Lock()

    def should_trigger(self, key: str) -> bool:
        with self._lock:
            now = datetime.now(timezone.utc)
            last = self._last_alerts.get(key)
            if last and (now - last).total_seconds() < self.cooldown:
                return False
            self._last_alerts[key] = now
            return True

alert_debouncer = AlertDebouncer(cooldown_seconds=30.0)

# -------------------------------------------------------------
# SERVICE FUNCTIONS
# -------------------------------------------------------------

def validate_telemetry_payload(data: Any) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validates incoming JSON payload structure and sensor value physics.
    """
    if not isinstance(data, dict):
        return False, "Payload must be a JSON object", None

    if "temperature" not in data or "humidity" not in data:
        return False, "Missing 'temperature' or 'humidity' field", None

    try:
        temp = float(data["temperature"])
        hum = float(data["humidity"])
    except (ValueError, TypeError):
        return False, "Temperature and humidity must be numeric values", None

    if np.isnan(temp) or np.isinf(temp) or np.isnan(hum) or np.isinf(hum):
        return False, "Telemetry values cannot be NaN or Infinite", None

    if temp < SENSOR_LIMITS["temp_min"] or temp > SENSOR_LIMITS["temp_max"]:
        return False, f"Temperature {temp}°C out of realistic physical range ({SENSOR_LIMITS['temp_min']} to {SENSOR_LIMITS['temp_max']}°C)", None

    if hum < SENSOR_LIMITS["hum_min"] or hum > SENSOR_LIMITS["hum_max"]:
        return False, f"Humidity {hum}% out of realistic physical range (0 to 100%)", None

    source = str(data.get("source", "SIMULATION")).strip().upper()
    if source not in ("HARDWARE", "SIMULATION"):
        source = "SIMULATION"

    return True, None, {
        "temperature": round(temp, 2),
        "humidity": round(hum, 2),
        "source": source
    }

def process_telemetry_reading(
    valid_data: Dict[str, Any],
    client_ip: str = "127.0.0.1",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Processes a valid sensor reading:
    1. Updates connection tracker if hardware.
    2. Runs AI / anomaly prediction.
    3. Saves record into SQLite.
    4. Evaluates and triggers alerts if abnormal.
    """
    temp = valid_data["temperature"]
    hum = valid_data["humidity"]
    source = valid_data["source"]

    if source == "HARDWARE":
        hardware_tracker.record_hardware_ping(client_ip)

    # ML Anomaly Evaluation
    from ai.predict import predict_anomaly
    
    # Extract feature vector using rolling buffer
    feature_vec, feat_meta = telemetry_buffer.get_features(temp, hum)
    ai_result = predict_anomaly(feature_vec, feat_meta)
    
    is_anomaly = ai_result["is_anomaly"]
    anomaly_score = ai_result["anomaly_score"]
    explanation = ai_result.get("explanation", "Normal conditions")

    # Persist in SQLite
    inserted = insert_reading(
        temperature=temp,
        humidity=hum,
        source=source,
        is_anomaly=is_anomaly,
        anomaly_score=anomaly_score,
        db_path=db_path
    )

    if inserted.get("duplicate"):
        return {"status": "ignored", "reason": inserted["message"]}

    # Update buffer with inserted record
    telemetry_buffer.add({"temperature": temp, "humidity": hum, "is_anomaly": is_anomaly})

    # Alert Trigger Evaluation
    alert_info = evaluate_and_create_alerts(temp, hum, is_anomaly, anomaly_score, explanation, db_path=db_path)

    return {
        "reading": inserted,
        "ai": {
            "is_anomaly": bool(is_anomaly),
            "anomaly_score": anomaly_score,
            "explanation": explanation,
            "model_status": ai_result.get("model_status", "operational")
        },
        "alert": alert_info
    }

def evaluate_and_create_alerts(
    temp: float,
    hum: float,
    is_anomaly: int,
    anomaly_score: float,
    explanation: str,
    db_path: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Evaluates telemetry against safety thresholds and ML anomalies.
    Dispatches alerts with proper severity levels.
    """
    severity = None
    message = None
    debounce_key = None

    if temp >= CABINET_THRESHOLDS["temp_critical"]:
        severity = "CRITICAL"
        message = f"CRITICAL THERMAL LEVEL: Cabinet temperature reached {temp}°C (Critical Limit: {CABINET_THRESHOLDS['temp_critical']}°C). High risk of equipment failure."
        debounce_key = "crit_temp"
    elif hum >= CABINET_THRESHOLDS["hum_critical"]:
        severity = "CRITICAL"
        message = f"CRITICAL MOISTURE LEVEL: Cabinet humidity reached {hum}% (Critical Limit: {CABINET_THRESHOLDS['hum_critical']}%). Condensation hazard."
        debounce_key = "crit_hum"
    elif temp >= CABINET_THRESHOLDS["temp_warning"]:
        severity = "WARNING"
        message = f"Thermal Warning: Cabinet temperature at {temp}°C (Warning threshold: {CABINET_THRESHOLDS['temp_warning']}°C)."
        debounce_key = "warn_temp"
    elif hum >= CABINET_THRESHOLDS["hum_warning"]:
        severity = "WARNING"
        message = f"Humidity Warning: Cabinet relative humidity elevated at {hum}% (Threshold: {CABINET_THRESHOLDS['hum_warning']}%)."
        debounce_key = "warn_hum"
    elif is_anomaly == 1:
        severity = "WARNING"
        message = f"AI Environmental Anomaly Detected: {explanation} (Score: {round(anomaly_score, 4)})."
        debounce_key = "ai_anomaly"

    if severity and debounce_key:
        if alert_debouncer.should_trigger(debounce_key):
            alert_record = insert_alert(
                severity=severity,
                message=message,
                temperature=temp,
                humidity=hum,
                anomaly_score=anomaly_score,
                db_path=db_path
            )
            return alert_record

    return None
