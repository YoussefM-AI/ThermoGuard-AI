# CabinetSense AI
## Smart Industrial Electrical Cabinet Monitoring & AI-Based Anomaly Detection

[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/framework-Flask%203.1-black.svg)](https://flask.palletsprojects.com/)
[![Database](https://img.shields.io/badge/database-SQLite3%20WAL-lightgrey.svg)](https://www.sqlite.org/)
[![Machine Learning](https://img.shields.io/badge/AI-Isolation%20Forest-green.svg)](https://scikit-learn.org/)
[![Frontend](https://img.shields.io/badge/UI-SCADA%20Cyber-cyan.svg)](#)
[![Tests](https://img.shields.io/badge/tests-28%20passing-brightgreen.svg)](#)

---

## 1. Project Overview & Problem Statement

Industrial electrical cabinets house critical switchgear, motor drives, transformers, and electronic control systems. Adverse microclimatic conditions inside these enclosures—such as excessive thermal accumulation, ventilation fan blockage, dust accumulation, or moisture ingress from compromised seals—accelerate component degradation and increase the risk of premature failure.

**CabinetSense AI** is a complete, real-world IoT and unsupervised machine learning prototype designed to monitor temperature and relative humidity inside electrical cabinets. The platform:
1. Ingests high-frequency environmental telemetry from physical **ESP32** hardware or a **Python Simulation Laboratory**.
2. Evaluates incoming observations in real-time using an unsupervised **Isolation Forest** machine learning model.
3. Automatically dispatches tiered SCADA alarms (**WARNING** and **CRITICAL**) based on physical safety bounds and multivariate anomaly scores.
4. Visualizes telemetry and diagnostic assessments on a dark-themed, glassmorphic **Industry 4.0 Command Center**.

> [!IMPORTANT]
> **Academic & Industrial Scope:** CabinetSense AI monitors and detects *environmental anomalies* (thermal spikes, humidity surges, unusual rate-of-change). It does **not** diagnose internal electrical faults (e.g. arc flash, short circuit) nor replace certified industrial safety relays.

---

## 2. System Architecture

```text
       +-----------------------+              +---------------------------+
       |   ESP32 Microcontroller|              |   Python Simulation Lab   |
       |  DHT11 Sensor (GPIO 4)|              |  5 Industrial Scenarios   |
       +-----------+-----------+              +-------------+-------------+
                   |                                        |
       Wi-Fi / HTTP POST                                 HTTP POST
                   |                                        |
                   +-------------------+--------------------+
                                       |
                                       v
                    +------------------------------------+
                    |        Python Flask REST API       |
                    |     (backend/app.py - Port 5000)   |
                    +------------------+-----------------+
                                       |
                +----------------------+----------------------+
                |                                             |
                v                                             v
  +---------------------------+                 +---------------------------+
  |    SQLite Relational DB   |                 |     AI / ML Pipeline      |
  |  - readings (WAL mode)    |                 |  - Feature Engineering    |
  |  - alerts                 |                 |  - Isolation Forest Model |
  |  - system_events          |                 |  - Decision Score Meter   |
  +---------------------------+                 +---------------------------+
                ^                                             |
                |                                             |
                +----------------------+----------------------+
                                       |
                                       v
                    +------------------------------------+
                    |     Premium SCADA Web Dashboard    |
                    |   (Chart.js, HTML5, CSS3, Lucide)  |
                    |   - Overview & Live SCADA Charts   |
                    |   - AI Intelligence Center         |
                    |   - Anomaly Registry & Alarm Desk  |
                    |   - Simulation Orchestrator        |
                    +------------------------------------+
```

---

## 3. Technology Stack

- **Microcontroller Firmware:** ESP32 (C++/Arduino Core), `WiFi.h`, `HTTPClient.h`, `DHT.h`.
- **Backend Application:** Python 3, Flask 3.1, Flask-CORS, Gunicorn-compatible.
- **Database Engine:** SQLite3 in Write-Ahead Logging (`WAL`) mode with indexing.
- **Machine Learning Engine:** Scikit-Learn (Isolation Forest), Pandas, NumPy, Joblib.
- **Frontend Presentation:** HTML5, CSS3 (Modern SCADA Dark Palette), JavaScript (ES6+), Chart.js 4.4, Lucide Icons.

---

## 4. Hardware Wiring & ESP32 Configuration

### 4.1 Component Bill of Materials (BOM)
- 1x ESP32 Development Board (ESP32-WROOM-32).
- 1x DHT11 Temperature & Relative Humidity Sensor.
- 1x Breadboard & 3x Jumper Wires.
- 1x USB Micro-B or Type-C Data Cable.

### 4.2 Pinout Connection Table

| DHT11 Pin | Description | ESP32 Pin Connection |
| :--- | :--- | :--- |
| **VCC (+)** | Power Supply | **3V3** (3.3V Output) |
| **DATA (OUT)**| Single-Bus Serial Data | **GPIO 4** |
| **GND (-)** | Ground Reference | **GND** |

*Note: If using a 4-pin bare DHT11 sensor instead of a 3-pin module, place a 10kΩ pull-up resistor between VCC (3.3V) and DATA (GPIO 4).*

### 4.3 Flashing the ESP32 Firmware
1. Open [`esp32/cabinet_sensor.ino`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/esp32/cabinet_sensor.ino) in the Arduino IDE.
2. Select Board: **ESP32 Dev Module**.
3. Install required libraries via Library Manager:
   - `DHT sensor library` by Adafruit
   - `Adafruit Unified Sensor`
4. Update configuration credentials:
   ```cpp
   const char* WIFI_SSID     = "YOUR_WIFI_NETWORK";
   const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
   const char* SERVER_IP     = "192.168.1.X"; // Local IP of your PC running Flask
   const int   SERVER_PORT   = 5000;
   ```
5. Click **Upload** and open Serial Monitor at **115200 baud**.

---

## 5. Machine Learning Pipeline & Feature Engineering

### 5.1 Why Isolation Forest?
Traditional threshold alarms fire only when a variable crosses an absolute boundary (e.g. $T > 52^\circ\text{C}$). However, early environmental anomalies manifest as **unusual multidimensional trajectories** (e.g., rapid thermal rate of change $\frac{dT}{dt}$ during low ambient hours or sudden moisture shifts without ambient temperature changes).

Isolation Forest isolates outliers by randomly partitioning feature dimensions into recursive orthogonal hyperplanes. Anomalies require significantly fewer partitions (shorter path lengths) to isolate than nominal cluster points.

### 5.2 Feature Space (6 Dimensions)
1. `temperature`: Instantaneous calibrated temperature ($^\circ\text{C}$).
2. `humidity`: Instantaneous calibrated relative humidity ($\%$).
3. `delta_temperature`: Instantaneous 1st-order gradient $\Delta T = T_t - T_{t-1}$.
4. `delta_humidity`: Instantaneous moisture gradient $\Delta H = H_t - H_{t-1}$.
5. `rolling_temp_avg`: 5-point moving thermal baseline average.
6. `rolling_hum_avg`: 5-point moving moisture baseline average.

### 5.3 Model Performance on Synthetic Evaluation Testbed
Executed against an independent 4,000-sample test set (8% anomaly ratio):
- **Accuracy:** 95.05%
- **Anomaly Recall:** 100.00% (Captured all 388 true environmental anomaly signatures)
- **Precision:** 66.21%
- **F1-Score:** 79.67%
- **Serialized Artifact:** [`ai/model.pkl`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/ai/model.pkl)

---

## 6. Simulation Laboratory (Mode A)

The project includes an integrated simulator supporting 5 realistic industrial electrical cabinet scenarios:

1. **Normal Conditions:** Stable nominal climate ($\approx 24.5^\circ\text{C}$, $\approx 45\%$ RH) with harmonic diurnal temperature cycles and natural Gaussian noise.
2. **Gradual Temperature Increase:** Progressive heat accumulation simulating clogged cabinet filters or cooling fan degradation (climbs to $55^\circ\text{C}+$).
3. **Abnormal Humidity:** Rapid moisture surge simulating door gasket seal degradation or ambient water leaks (surges to $85\%+$).
4. **Combined Anomaly:** Simultaneous thermal escalation and extreme humidity swings.
5. **Sensor / Network Drop:** Simulates loose sensor cables or Wi-Fi packet drops to test timeout alert recovery.

---

## 7. Quickstart Installation & Running

### 7.1 Clone and Environment Setup
```bash
# Navigate to project directory
cd CabinetSense-AI

# Verify Python environment
python tests/test_environment.py
```

### 7.2 Training the AI Model
```bash
# Generate synthetic dataset (12,000 records)
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

### 7.4 Running the Simulation
- **Via Web Dashboard:** Navigate to the **Simulation Lab** tab, select a scenario, adjust the interval slider, and click **Start Simulation**.
- **Via CLI:**
  ```bash
  python simulation/simulator.py --scenario gradual_temp --interval 1.5 --steps 50
  ```

---

## 8. REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Health check & SQLite database connection status |
| `GET` | `/api/status` | Consolidated state: hardware status, active mode, AI, KPIs |
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

CabinetSense AI includes 28 automated unit, integration, and end-to-end tests:

```bash
python -m unittest discover tests
```

**Test Breakdown:**
- [`tests/test_environment.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_environment.py): Library imports, Scikit-learn instantiation, SQLite memory engine.
- [`tests/test_simulation.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_simulation.py): All 5 simulation scenarios, bounding, packet drop flags, and simulator thread lifecycle.
- [`tests/test_database.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_database.py): Schema initialization, reading insertion, deduplication window, alert lifecycle, and analytics calculations.
- [`tests/test_api.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_api.py): REST endpoint contracts, payload validation, status codes, simulation triggers, CSV export.
- [`tests/test_ai.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_ai.py): Model serialization, feature engineering, normal prediction, anomaly sensitivity, missing data imputation.
- [`tests/test_frontend.py`](file:///c:/Users/HP/.gemini/antigravity/scratch/CabinetSense-AI/tests/test_frontend.py): Web server asset delivery, 8 SPA view containers, CSS/JS bundling.

---

## 10. University Jury Demonstration Script

1. **Architecture Walkthrough:** Show the ESP32 circuit breadboard and explain the hardware-software decoupled REST interface.
2. **Dashboard Tour:** Open `http://127.0.0.1:5000` to present the SCADA Cyber UI, highlighting the collapsible sidebar, live clock, and KPI cards.
3. **Normal Simulation:** In the Simulation Lab, start Scenario 1 (*Normal Conditions*). Observe stable temperatures ($\approx 24.5^\circ\text{C}$), positive AI decision score ($+0.065$, Inlier), and nominal green badges.
4. **Thermal Overload Anomaly:** Switch to Scenario 2 (*Gradual Temp Rise*). Watch the real-time Chart.js graph climb past $38^\circ\text{C}$ (Warning) and $52^\circ\text{C}$ (Critical). Note the AI decision score plunging below $0.0$, immediate alarm creation in the Alerts Center, and live toast notification.
5. **Alert Acknowledgment:** Go to the Alerts Center, click **Acknowledge**, and demonstrate state transition to `ACKNOWLEDGED` with an audit event recorded.
6. **AI Intelligence Center:** Show the live Isolation Forest decision score meter, active 6-dimensional feature vector, and discuss academic synthetic evaluation metrics.
7. **CSV Export:** Click **Export Telemetry CSV** on the Analytics page to download the logged dataset for lab verification.
