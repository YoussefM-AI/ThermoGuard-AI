# ThermoGuard AI
## Smart Industrial Environmental Monitoring & AI-Based Anomaly Detection

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask%203.1-black.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/database-SQLite3%20WAL-lightgrey.svg)](https://www.sqlite.org/)
[![Machine Learning](https://img.shields.io/badge/AI-Isolation%20Forest-green.svg)](https://scikit-learn.org/)
[![Frontend](https://img.shields.io/badge/UI-Modern%20SCADA%20Dark-cyan.svg)](#)
[![Cloud Ready](https://img.shields.io/badge/Cloud-Docker%20%7C%20Render%20%7C%20Procfile-purple.svg)](#)

---

## 1. Project Overview & Problem Statement

Industrial electrical cabinets house critical switchgear, motor drives, transformers, and electronic control systems. Adverse microclimatic conditions inside these enclosures—such as excessive thermal accumulation, ventilation fan blockage, dust accumulation, or moisture ingress from compromised seals—accelerate component degradation and cause critical hardware downtime.

**ThermoGuard AI** is a complete, real-world Hybrid IoT and unsupervised machine learning platform designed to monitor temperature and relative humidity inside electrical enclosures:
1. **Telemetry Ingestion:** Receives environmental telemetry from physical **ESP32** nodes, online **Wokwi** simulations, or an in-process **Simulation Engine**.
2. **AI Anomaly Detection:** Evaluates incoming observations in real time using an unsupervised **Isolation Forest** model with engineered rolling & differential features.
3. **Smart Tiered Alarms:** Dispatches tiered alarms (**WARNING** and **CRITICAL**) based on physical safety bounds and multivariate anomaly scores.
4. **Streamlined Web Dashboard:** Clean, modern, dark navy/black UI with 4 focused views: **Dashboard**, **History**, **Alerts**, and **Settings**.
5. **Hybrid IoT + Cloud Architecture:** Designed to run locally on your LAN during prototyping or deployed to the cloud (Docker / Render / Railway) so your personal computer can stay powered off.

> [!IMPORTANT]
> **Industrial Scope:** ThermoGuard AI monitors and detects *environmental anomalies* (thermal spikes, humidity surges, unusual rate-of-change). It does **not** diagnose internal electrical faults (e.g., arc flash, short circuit) nor replace certified industrial safety disconnect relays.

---

## 2. System Architecture

```text
       +-----------------------+              +---------------------------+
       |   ESP32 Physical Node |              |    Wokwi Cloud Simulation |
       |  DHT11 Sensor (GPIO 4)|              |    DHT22 Sensor (GPIO 4)  |
       +-----------+-----------+              +-------------+-------------+
                   |                                        |
       Wi-Fi / HTTP POST                               HTTP POST (Gateway / Tunnel)
                   |                                        |
                   +-------------------+--------------------+
                                       |
                                       v
                    +------------------------------------+
                    |       ThermoGuard AI Engine        |
                    |     (backend/app.py - Port 5000)   |
                    +------------------+-----------------+
                                       |
                +----------------------+----------------------+
                |                                             |
                v                                             v
  +---------------------------+                 +---------------------------+
  |    SQLite Relational DB   |                 |     AI / ML Pipeline      |
  |  - readings (WAL mode)    |                 |  - Feature Engineering    |
  |  - alerts (unresolved/ack)|                 |  - Isolation Forest Model |
  |  - system_events          |                 |  - Anomaly Score Meter    |
  +---------------------------+                 +---------------------------+
                ^                                             |
                |                                             |
                +----------------------+----------------------+
                                       |
                                       v
                    +------------------------------------+
                    |     Streamlined SCADA Dashboard    |
                    |     (Chart.js, HTML5, CSS3, JS)    |
                    |   - Dashboard (Status, KPIs, Chart)|
                    |   - History (Logs & CSV Export)    |
                    |   - Alerts (SCADA Alarm Desk)      |
                    |   - Settings (Wokwi & Pinout Info) |
                    +------------------------------------+
```

---

## 3. Technology Stack

- **Microcontroller Firmware:** ESP32 (C++/Arduino Core), `WiFi.h`, `HTTPClient.h`, `WiFiClientSecure.h`, `DHT.h`.
- **Backend Service:** Python 3, Flask 3.1, Flask-CORS, Gunicorn WSGI.
- **Database Engine:** SQLite3 with Write-Ahead Logging (`WAL`) mode and automatic schema migrations.
- **Machine Learning Engine:** Scikit-Learn (Isolation Forest), Pandas, NumPy, Joblib.
- **Frontend Dashboard:** HTML5, CSS3 (Modern SCADA Dark Navy `#080C14` / `#111A2E`), JavaScript (ES6+), Chart.js 4.4, Lucide Icons.
- **Cloud Packaging:** Docker container (`Dockerfile`), `Procfile`, and `render.yaml` blueprint.

---

## 4. Hardware Wiring & Wokwi Simulation Invariants

> [!IMPORTANT]
> **Strict Sensor Pinout & Distinction:**
> - **Physical ESP32 Node:** Uses **DHT11** connected to **GPIO 4** (configured in [`esp32/cabinet_sensor.ino`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/esp32/cabinet_sensor.ino)).
> - **Virtual Wokwi Node:** Uses **DHT22** connected to **GPIO 4** (configured in [`wokwi/sketch.ino`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/wokwi/sketch.ino) and [`wokwi/diagram.json`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/wokwi/diagram.json)).

### 4.1 Physical Hardware Pinout Table

| DHT11 Pin | Description | ESP32 Pin Connection | Voltage |
| :--- | :--- | :--- | :--- |
| **VCC (+)** | Power Supply | **3V3** (3.3V Output) | 3.3V DC |
| **DATA (OUT)**| Single-Bus Serial Data | **GPIO 4** | 3.3V Logic |
| **GND (-)** | Ground Reference | **GND** | 0V |

*Note: If using a bare 4-pin DHT11 without a built-in module PCB, place a 10kΩ pull-up resistor between VCC (3.3V) and DATA (GPIO 4).*

### 4.2 Connecting Wokwi Simulation to the Dashboard

When running the virtual simulation on [Wokwi](https://wokwi.com/):
1. Copy [`wokwi/sketch.ino`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/wokwi/sketch.ino) and [`wokwi/diagram.json`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/wokwi/diagram.json) into Wokwi.
2. In `sketch.ino`, configure the target endpoint:
   - **Local Gateway Mode (with Wokwi IoT Gateway running):**
     ```cpp
     const char* DASHBOARD_URL = "http://10.0.2.2:5000/api/readings";
     ```
   - **Cloud or Tunnel Mode (Render, Railway, Cloudflared, Ngrok):**
     ```cpp
     const char* DASHBOARD_URL = "https://your-public-url.com/api/readings";
     ```
3. Start the simulation. Click the DHT22 component on the schematic to slide temperature & humidity and observe the live response on your ThermoGuard AI dashboard.

---

## 5. Machine Learning Pipeline & Feature Engineering

### 5.1 Why Isolation Forest?
Traditional threshold alarms fire only when an absolute ceiling is breached (e.g. $T > 52^\circ\text{C}$). However, early equipment failure or filter blockage manifests as **unusual dynamic trajectories** (e.g. sharp thermal rise during cold ambient periods or anomalous humidity rates of change).

Isolation Forest isolates unusual multidimensional points using recursive random decision cuts. Outliers require significantly fewer splits to separate from nominal operational clusters.

### 5.2 Feature Space (6 Dimensions)
1. `temperature`: Instantaneous calibrated temperature ($^\circ\text{C}$).
2. `humidity`: Instantaneous calibrated relative humidity ($\%$).
3. `delta_temperature`: Instantaneous 1st-order gradient $\Delta T = T_t - T_{t-1}$.
4. `delta_humidity`: Instantaneous moisture gradient $\Delta H = H_t - H_{t-1}$.
5. `rolling_temp_avg`: 5-point moving thermal baseline average.
6. `rolling_hum_avg`: 5-point moving moisture baseline average.

---

## 6. Dashboard Interface (4 Simple Views)

ThermoGuard AI features a streamlined, dark navy/black UI designed for industrial reliability:

1. **Dashboard:**
   - Real-time System ONLINE/OFFLINE status beacon with live heartbeat.
   - 4 KPI metric cards: System Connectivity, Current Temperature, Current Humidity, AI Anomaly Assessment.
   - Combined historical telemetry chart with industrial threshold guide lines (38°C warning, 52°C critical).
   - Recent Alerts list with 1-click Acknowledge button.
   - Quick Wokwi & simulation controls.
2. **History:**
   - Full telemetry log with pagination and source filter (Hardware vs Simulation vs Anomalies).
   - 1-click **Export CSV** button calling `/api/export/csv`.
3. **Alerts:**
   - SCADA Alarm Desk with severity filters (All, Unresolved, Critical, Warning).
   - Instant alarm acknowledgment with recorded resolution audits.
4. **Settings:**
   - Wokwi simulation guide with 1-click endpoint URL copy.
   - Physical hardware pinout and wiring reference.
   - Hybrid Cloud architecture status.
   - Isolation Forest hyper-parameter diagnostics.

---

## 7. Quickstart Installation & Local Execution

### 7.1 Clone and Environment Setup
```bash
# Navigate to project directory
cd CabinetSense-AI

# Verify Python environment
python tests/test_environment.py
```

### 7.2 Training the AI Model
```bash
# Generate synthetic dataset
python ai/generate_dataset.py

# Train and serialize the Isolation Forest model
python ai/train_model.py

# Run evaluation suite
python ai/evaluate_model.py
```

### 7.3 Starting the Backend & Dashboard
```bash
python backend/app.py
```
Open your browser and navigate to:
**`http://127.0.0.1:5000`**

---

## 8. REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check & SQLite database connectivity |
| `GET` | `/api/status` | System state: hardware status, active mode, AI, KPIs |
| `POST`| `/api/readings` | Ingests sensor reading (`{"temperature": X, "humidity": Y, "source": "..."}`) |
| `GET` | `/api/readings` | Retrieves historical readings (supports `limit`, `offset`, `source`, `anomalies_only`) |
| `GET` | `/api/readings/latest` | Retrieves the most recent single sensor observation |
| `GET` | `/api/alerts` | Lists SCADA alarms (supports `severity` and `status` filters) |
| `POST`| `/api/alerts/<id>/acknowledge` | Acknowledges an active unresolved alert |
| `POST`| `/api/simulation/start` | Starts background telemetry simulation |
| `POST`| `/api/simulation/stop` | Stops background telemetry simulation |
| `GET` | `/api/simulation/status` | Retrieves current simulator engine status |
| `GET` | `/api/analytics` | Statistical distributions (min/max/avg, anomaly frequency) |
| `GET` | `/api/ai/status` | ML model architecture, features, and training metadata |
| `POST`| `/api/ai/train` | Triggers on-demand Isolation Forest retraining |
| `GET` | `/api/export/csv` | Streams full telemetry history as downloadable CSV |

---

## 9. Automated Test Suite

ThermoGuard AI includes an automated unit and integration test suite:

```bash
python -m unittest discover tests
```

- [`tests/test_environment.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_environment.py): Library imports, Scikit-learn instantiation, SQLite engine.
- [`tests/test_simulation.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_simulation.py): All 5 simulation scenarios, bounding, packet drop flags, thread lifecycle.
- [`tests/test_database.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_database.py): Schema initialization, reading insertion, deduplication window, alert lifecycle.
- [`tests/test_api.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_api.py): REST endpoint contracts, payload validation, status codes, simulation triggers, CSV export.
- [`tests/test_ai.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_ai.py): Model serialization, feature engineering, normal prediction, anomaly sensitivity.
- [`tests/test_frontend.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_frontend.py): Web server asset delivery, 4 streamlined SPA views, CSS/JS bundling.
