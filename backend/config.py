"""
ThermoGuard AI - Centralized Configuration
All configurable thresholds, paths, and settings in one place.
Loads from environment variables with sensible defaults.
"""

import os

# --- Database ---
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.getenv("THERMOGUARD_DB", os.path.join(DATA_DIR, "thermoguard.db"))

# --- AI Model ---
AI_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ai")
_AI_MODEL = os.path.join(AI_DIR, "model.pkl")
_DATA_MODEL = os.path.join(DATA_DIR, "model.pkl")
MODEL_PATH = os.getenv("THERMOGUARD_MODEL_PATH", _AI_MODEL if os.path.exists(_AI_MODEL) else _DATA_MODEL)

# --- Safety Thresholds (configurable via environment variables) ---
TEMP_WARNING_C  = float(os.getenv("TEMP_WARNING",  "38.0"))   # °C
TEMP_CRITICAL_C = float(os.getenv("TEMP_CRITICAL", "52.0"))   # °C
HUM_WARNING_PCT = float(os.getenv("HUM_WARNING",   "70.0"))   # %
HUM_CRITICAL_PCT= float(os.getenv("HUM_CRITICAL",  "85.0"))   # %

# --- Sensor Physical Limits ---
TEMP_MIN_C = float(os.getenv("TEMP_MIN", "-10.0"))
TEMP_MAX_C = float(os.getenv("TEMP_MAX", "90.0"))
HUM_MIN_PCT= float(os.getenv("HUM_MIN",  "0.0"))
HUM_MAX_PCT= float(os.getenv("HUM_MAX",  "100.0"))

# --- Hardware Connection ---
HW_TIMEOUT_SECONDS = float(os.getenv("HW_TIMEOUT", "15.0"))   # seconds before marking ESP32 offline
ALERT_COOLDOWN_SECONDS = float(os.getenv("ALERT_COOLDOWN", "30.0"))

# --- Flask ---
FLASK_HOST = os.getenv("HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "false").lower() == "true"
