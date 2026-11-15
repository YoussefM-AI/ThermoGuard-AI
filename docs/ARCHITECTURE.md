# ThermoGuard AI — System Architecture

## Overview

ThermoGuard AI is a lightweight industrial IoT system for monitoring temperature and humidity inside electrical cabinets. It combines a real-time sensor node (ESP32 + DHT), a Python Flask backend, an SQLite database, a simple AI anomaly detector, and a web dashboard.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     ESP32 DevKit V1                         │
│                                                             │
│  DHT11 (physical) │ DHT22 (Wokwi)                          │
│  GPIO 4 ──────────┘                                         │
│                                                             │
│  • Read temp + humidity every 3s                            │
│  • Validate (NaN, range check)                              │
│  • POST JSON → Flask /api/readings                          │
│  • Auto-reconnect Wi-Fi on drop                             │
└──────────────┬──────────────────────────────────────────────┘
               │ Wi-Fi / HTTP POST
               │ { "temperature": 25.4, "humidity": 48.1,
               │   "source": "HARDWARE" }
               ▼
┌─────────────────────────────────────────────────────────────┐
│               FLASK BACKEND  (backend/)                     │
│                                                             │
│  app.py         ── Application factory, CORS, static serve  │
│  routes.py      ── REST API Blueprint (/api/*)              │
│  services.py    ── Telemetry processing, alert engine       │
│  database.py    ── Thread-safe SQLite CRUD                  │
│  config.py      ── All thresholds and settings              │
└───────────┬────────────────────────────────────────────────-┘
            │
            ├──► ai/predict.py ─── Isolation Forest inference
            │                      (fallback: statistical heuristics)
            │
            ├──► data/thermoguard.db ─── SQLite persistence
            │
            └──► frontend/ ─────────── Static SPA dashboard
```

---

## Components

### 1. ESP32 Sensor Node

| Property     | Physical Hardware  | Wokwi Simulation   |
|-------------|--------------------|--------------------|
| Board       | ESP32 DevKit V1    | ESP32 DevKit V1    |
| Sensor      | DHT11              | DHT22              |
| GPIO Pin    | GPIO 4             | GPIO 4             |
| Interval    | 3 000 ms           | 3 000 ms           |
| Firmware    | esp32/cabinet_sensor.ino | wokwi/sketch.ino |
| Source tag  | HARDWARE           | HARDWARE           |

Both firmwares send the same JSON payload to `/api/readings`.

---

### 2. Flask Backend

**Entry point:** `backend/app.py` → `create_app()` factory.

**Key responsibilities:**
- Initialize SQLite schema on boot (auto-creates tables)
- Receive and validate sensor readings
- Run AI anomaly detection on every reading
- Generate alerts with 30s debounce cooldown
- Serve the frontend dashboard (static files)
- Track ESP32 connection status (online/offline within 15s window)

**API Endpoints:**

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/api/health` | Backend + DB connectivity |
| POST | `/api/readings` | Ingest sensor telemetry |
| GET | `/api/readings` | Historical readings (filterable) |
| GET | `/api/readings/latest` | Most recent reading |
| GET | `/api/alerts` | Alert list |
| POST | `/api/alerts/<id>/acknowledge` | Acknowledge an alert |
| GET | `/api/status` | Full system status |
| POST | `/api/simulation/start` | Start Python simulator |
| POST | `/api/simulation/stop` | Stop Python simulator |
| GET | `/api/analytics` | Statistical summary |
| GET | `/api/export/csv` | CSV data export |

---

### 3. Database (SQLite)

**Location:** `data/thermoguard.db`

**Schema:**

```sql
-- Sensor readings
CREATE TABLE readings (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT    NOT NULL,
    temperature  REAL    NOT NULL,
    humidity     REAL    NOT NULL,
    source       TEXT    NOT NULL CHECK(source IN ('HARDWARE','SIMULATION')),
    is_anomaly   INTEGER DEFAULT 0,
    anomaly_score REAL   DEFAULT 0.0
);

-- System alerts
CREATE TABLE alerts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT    NOT NULL,
    severity      TEXT    NOT NULL CHECK(severity IN ('CRITICAL','WARNING','INFO')),
    message       TEXT    NOT NULL,
    temperature   REAL,
    humidity      REAL,
    anomaly_score REAL,
    status        TEXT    NOT NULL DEFAULT 'UNRESOLVED'
                  CHECK(status IN ('UNRESOLVED','ACKNOWLEDGED','RESOLVED'))
);

-- Audit log
CREATE TABLE system_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    event_type  TEXT    NOT NULL,
    description TEXT    NOT NULL,
    source      TEXT    NOT NULL
);
```

Tables are created automatically on first boot via `CREATE TABLE IF NOT EXISTS`.

---

### 4. AI Anomaly Detection

**Algorithm:** Isolation Forest (scikit-learn) — unsupervised anomaly detection.

**Feature vector (6 features):**
1. `temperature` — raw °C reading
2. `humidity` — raw % reading
3. `delta_temperature` — change since last reading
4. `delta_humidity` — change since last reading
5. `rolling_temp_avg` — 15-sample rolling average temperature
6. `rolling_hum_avg` — 15-sample rolling average humidity

**Fallback heuristics** (used when model is not loaded):
- Temp > 38°C → anomaly
- Humidity > 70% → anomaly
- |ΔTemp| ≥ 4°C → anomaly (sudden spike)
- |ΔHum| ≥ 8% → anomaly (sudden change)

**Alert Classification:**

| Level | Condition |
|-------|-----------|
| CRITICAL | Temp ≥ 52°C OR Humidity ≥ 85% |
| WARNING | Temp ≥ 38°C OR Humidity ≥ 70% OR AI detects anomaly |
| NORMAL | All readings within limits, no anomaly |

> **Important:** AI detection complements physical safety thresholds — it does not replace independent electrical protection systems.

---

### 5. Dashboard (Frontend SPA)

**Location:** `frontend/`

**Technology:** Vanilla JS, Chart.js, Lucide icons. No build step required.

**4 views:**
1. **Dashboard** — System status hero, 4 KPI cards (System, Temp, Humidity, AI), historical chart, recent alerts, simulation controls
2. **History** — Full telemetry log with source/anomaly filtering + CSV export
3. **Alerts** — SCADA alarm desk with severity filters and acknowledge actions
4. **Settings** — Wokwi setup guide, hardware pinout, cloud architecture, AI diagnostics

**Polling:** Every 2 seconds for live updates.

---

## Data Flow

```
ESP32 DHT Read (every 3s)
  ↓
Validate reading (NaN, range)
  ↓
HTTP POST /api/readings { temperature, humidity, source }
  ↓
Flask: validate_telemetry_payload()
  ↓
Flask: get_features() — build 6-feature vector from rolling buffer
  ↓
Flask: predict_anomaly() — Isolation Forest inference (or heuristic fallback)
  ↓
Flask: insert_reading() — save to SQLite
  ↓
Flask: evaluate_and_create_alerts() — check thresholds + AI result
  ↓
If alert needed: insert_alert() + insert_system_event()
  ↓
JSON response → 201 Created
  ↓
Dashboard polls every 2s → GET /api/readings/latest + /api/alerts + /api/status
  ↓
Chart.js updates live
```

---

## Configuration

All settings in `backend/config.py`, overridable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `THERMOGUARD_DB` | `data/thermoguard.db` | SQLite database path |
| `TEMP_WARNING` | `38.0` | Warning threshold (°C) |
| `TEMP_CRITICAL` | `52.0` | Critical threshold (°C) |
| `HUM_WARNING` | `70.0` | Humidity warning (%) |
| `HUM_CRITICAL` | `85.0` | Humidity critical (%) |
| `PORT` | `5000` | Flask server port |
| `FLASK_DEBUG` | `false` | Debug mode |
