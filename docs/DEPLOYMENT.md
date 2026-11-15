# ThermoGuard AI — Deployment Guide

## 1. Local Development

### Prerequisites

- Python 3.11+
- pip

### Setup

```bash
# 1. Clone / navigate to project
cd ThermoGuard-AI

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate    # Linux/macOS

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the backend
python backend/app.py
```

Backend will start at: `http://localhost:5000`  
Dashboard will be at: `http://localhost:5000`

### Verify Backend is Working

```bash
curl http://localhost:5000/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "service": "ThermoGuard AI Industrial Engine"
}
```

---

## 2. Connecting ESP32 (Physical Hardware)

### Configuration

Open `esp32/cabinet_sensor.ino` and set:

```cpp
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* LOCAL_SERVER_IP = "192.168.X.X";  // Your PC's LAN IP
const bool  USE_CLOUD_ENDPOINT = false;        // Local mode
```

**To find your PC's LAN IP:**
- Windows: `ipconfig` → look for IPv4 Address under your Wi-Fi adapter

### Flash

1. Open Arduino IDE
2. Install ESP32 board package
3. Install DHT sensor library (DHTesp or Adafruit DHT)
4. Select: ESP32 Dev Module, correct COM port
5. Upload `esp32/cabinet_sensor.ino`
6. Open Serial Monitor at 115200 baud

---

## 3. Testing via Python Simulator

You can generate realistic telemetry and test all 5 failure modes without physical hardware:

### Via Dashboard UI:
1. Open `http://localhost:5000` in your browser.
2. Under **Simulation Control**, select any scenario (e.g., Thermal Spike, Humidity Leak).
3. Click **Start Simulation**.

### Via CLI:
```bash
# Run 10 steps of normal scenario
python simulation/simulator.py --scenario normal --interval 2.0

# Run gradual temperature increase
python simulation/simulator.py --scenario gradual_temp --steps 20
```

---

## 4. Cloud Deployment

> ⚠️ **Do not deploy without approval.** This section explains how to deploy when you are ready.

### Option A: Render.com (Recommended — Free Tier Available)

The project includes a `render.yaml` blueprint.

**Steps:**
1. Push the project to a GitHub repository
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your GitHub repo
4. Render reads `render.yaml` and creates the web service automatically
5. Add a **Persistent Disk** mounted at `/app/data` for the database
6. Set environment variables in Render dashboard:
   - `PORT=5000`
   - `THERMOGUARD_DB=/app/data/thermoguard.db`

**Update ESP32 firmware:**
```cpp
const bool  USE_CLOUD_ENDPOINT = true;
const char* CLOUD_SERVER_URL = "https://your-app.onrender.com/api/readings";
```

### Option B: Docker

```bash
# Build image
docker build -t thermoguard-ai .

# Run with persistent data volume
docker run -d \
  -p 5000:5000 \
  -v thermoguard_data:/app/data \
  -e THERMOGUARD_DB=/app/data/thermoguard.db \
  thermoguard-ai
```

### Option C: Railway / Fly.io

The `Procfile` and `requirements.txt` are compatible with both platforms.

```
# Procfile (already included)
web: gunicorn backend.app:app --workers 2 --bind 0.0.0.0:$PORT
```

---

## 5. Environment Variables Reference

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
# Edit .env with your values
```

| Variable | Default | Description |
|----------|---------|-------------|
| `THERMOGUARD_DB` | `data/thermoguard.db` | SQLite database path |
| `TEMP_WARNING` | `38.0` | Warning threshold (°C) |
| `TEMP_CRITICAL` | `52.0` | Critical threshold (°C) |
| `HUM_WARNING` | `70.0` | Humidity warning (%) |
| `HUM_CRITICAL` | `85.0` | Humidity critical (%) |
| `PORT` | `5000` | Flask server port |
| `FLASK_DEBUG` | `false` | Debug mode (set false in prod) |

---

## 6. Testing the System

### Quick API Test (local)

```bash
# Health check
curl http://localhost:5000/api/health

# Send a test reading (simulates ESP32)
curl -X POST http://localhost:5000/api/readings \
  -H "Content-Type: application/json" \
  -d '{"temperature": 27.5, "humidity": 52.3, "source": "HARDWARE"}'

# Get latest reading
curl http://localhost:5000/api/readings/latest

# Get system status
curl http://localhost:5000/api/status

# Get alerts
curl http://localhost:5000/api/alerts
```

### Send a Critical Temperature (triggers alert)

```bash
curl -X POST http://localhost:5000/api/readings \
  -H "Content-Type: application/json" \
  -d '{"temperature": 55.0, "humidity": 65.0, "source": "HARDWARE"}'
```

### Use Built-in Simulation

From the dashboard Settings page, or via API:

```bash
# Start normal simulation
curl -X POST http://localhost:5000/api/simulation/start \
  -H "Content-Type: application/json" \
  -d '{"scenario": "normal", "interval": 2.0}'

# Start thermal spike scenario
curl -X POST http://localhost:5000/api/simulation/start \
  -H "Content-Type: application/json" \
  -d '{"scenario": "gradual_temp", "interval": 2.0}'

# Stop simulation
curl -X POST http://localhost:5000/api/simulation/stop
```

---

## 7. Troubleshooting

### "no such table: alerts"
This error occurred in the old version. The new backend calls `init_db()` on startup, which runs `CREATE TABLE IF NOT EXISTS` for all tables before any request is served.

### Dashboard shows "System OFFLINE"
- Verify Flask backend is running: `curl http://localhost:5000/api/health`
- Check browser console for CORS or network errors
- Ensure you're accessing the dashboard through Flask (port 5000), not by opening index.html directly as a file

### ESP32 cannot connect
- Verify `WIFI_SSID` and `WIFI_PASSWORD` are correct
- Verify `LOCAL_SERVER_IP` matches your PC's actual LAN IP (`ipconfig`)
- Ensure PC firewall allows connections on port 5000
- Check Serial Monitor output for connection status

### AI model not loaded
The model loads automatically from `ai/model.pkl`. If missing, the system uses statistical heuristics automatically. To retrain:
```bash
python ai/train_model.py
```
