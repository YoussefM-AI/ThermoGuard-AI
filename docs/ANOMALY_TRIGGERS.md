# ThermoGuard AI — Anomaly & Alert Trigger Specification

This document details the exact environmental conditions, numerical steps, and thresholds that trigger AI anomalies and automated email alerts in ThermoGuard AI.

---

## 1. Dual-Layer Protection Architecture

ThermoGuard AI employs a **defense-in-depth monitoring strategy**:

```
[ ESP32 + DHT Sensor ] ── (every 2.0s) ──> [ POST /api/readings ]
                                                    │
                ┌───────────────────────────────────┴───────────────────────────────────┐
                ▼                                                                       ▼
   [ Layer 1: Predictive AI Model ]                                       [ Layer 2: Safety Interlocks ]
   • Isolation Forest (Unsupervised)                                       • Fixed Thermal & Moisture Limits
   • Rates-of-change (ΔT, ΔH per 2s)                                       • Warning: 38°C / 70% RH
   • Rolling averages (5–15 steps)                                         • Critical: 52°C / 85% RH
   • Detects creep & early faults BEFORE breach                            • Hardware damage prevention
                │                                                                       │
                └───────────────────────────────────┬───────────────────────────────────┘
                                                    ▼
                                   [ Resend Email & SCADA Alarms ]
```

- **Layer 1 (AI Predictive Early Warning):** Flags anomalies while temperatures are still within nominal bounds by analyzing dynamics, sudden spikes, or multivariate outliers.
- **Layer 2 (Deterministic Thresholds):** Hard safety limits that guarantee alarms even if an abnormal condition was reached extremely slowly.

---

## 2. Trigger Hierarchy & Matrix

| Level | Severity | Trigger Condition | Notification | Purpose |
| :--- | :---: | :--- | :---: | :--- |
| **0. Normal Baseline** | `NORMAL` | • $16.0^\circ\text{C} \le \text{Temp} \le 32.0^\circ\text{C}$<br>• $30.0\% \le \text{Hum} \le 65.0\%$<br>• $|\Delta T| < 1.5^\circ\text{C}/\text{step}$ | None (Inlier) | Standard room / cabinet environment. |
| **1. AI Moisture Ingress** | `WARNING` | • $\Delta H \ge +6.0\%$ to $+10.0\%$ in 2s, OR<br>• $\text{Hum} > 68.0\%$ | **Email (Amber ⚠️)** | Early warning: enclosure seal breach, water ingress, or condensation danger. |
| **2. AI Thermal Surge** | `WARNING` | • $\Delta T \ge +3.0^\circ\text{C}/\text{step}$ in 2s, OR<br>• Elevated pattern + negative score | **Email (Amber ⚠️)** | Early warning: rapid heating, loose contact, ventilation fan failure. |
| **3. Thermal Warning** | `WARNING` | • $\text{Temp} \ge 38.0^\circ\text{C}$ | **Email (Amber ⚠️)** | Cabinet temperature uncomfortably high for sensitive industrial electronics. |
| **4. Moisture Warning** | `WARNING` | • $\text{Hum} \ge 70.0\%$ | **Email (Amber ⚠️)** | Sustained high humidity inside enclosure. |
| **5. Critical Thermal** | `CRITICAL` | • $\text{Temp} \ge 52.0^\circ\text{C}$ | **Email (Red 🔴)** | Imminent risk of semiconductor / PLC thermal shutdown or fire hazard. |
| **6. Critical Moisture** | `CRITICAL` | • $\text{Hum} \ge 85.0\%$ | **Email (Red 🔴)** | Direct condensation and short-circuit hazard on active PCB traces. |

---

## 3. Step-by-Step Trigger Details

### Step 0: Nominal Operating Profile (No Anomaly)
- **Temperature:** $16.0^\circ\text{C}$ to $32.0^\circ\text{C}$
- **Humidity:** $30.0\%$ to $65.0\%$ relative humidity
- **Dynamics:** Temperature changes by less than $1.0^\circ\text{C}$ per 2-second cycle.
- **AI Output:** `is_anomaly: 0`, `anomaly_score: > 0.0` (Inlier).
- **Action:** Telemetry logged to SQLite, chart updated in real-time, green status on dashboard.

---

### Step 1: Predictive AI Thermal Spike (Early Fault)
- **Trigger Scenario:** A heating element turns on, a cooling fan halts, or an electrical contact loosens.
- **Trigger Parameters:**
  - **Rate of change ($\Delta T$):** An increase of **$\ge +3.0^\circ\text{C}$ within a single 2-second cycle** (e.g., jumping from $23.0^\circ\text{C} \to 26.5^\circ\text{C}$).
  - **Dynamic Score:** Isolation Forest decision score drops to **negative** (outlier subspace).
- **Result:**
  - Dashboard: Amber warning banner + dot on chart.
  - Email: Dispatched immediately via Resend:
    - Subject: `⚠️ ThermoGuard AI — WARNING Alert: AI Environmental Anomaly Detected...`
    - Body: Includes exact rate-of-change (`+3.5°C/step`) and AI Outlier Score.

---

### Step 2: Predictive AI Moisture Ingress (Seal Breach)
- **Trigger Scenario:** Gasket seal failure on the industrial enclosure or sudden humidity spike from the external environment.
- **Trigger Parameters:**
  - **Rate of change ($\Delta H$):** An increase of **$\ge +6.0\%$ to $+10.0\%$ within a single 2-second cycle** (e.g., jumping from $45\% \to 55\%$).
  - **Moisture Elevation:** Enclosure humidity sustained above **$68\%$**.
- **Result:**
  - Dashboard: Amber warning banner + moisture anomaly dot.
  - Email: Dispatched immediately via Resend with explanation: `"Moisture levels deviate from normal dry enclosure baseline"`.

---

### Step 3: High Temperature Warning Threshold
- **Trigger Parameter:** Temperature reaches or exceeds **$38.0^\circ\text{C}$** ($100.4^\circ\text{F}$).
- **Result:**
  - Severity: `WARNING`
  - Email: Dispatched with message `"Thermal Warning: Cabinet temperature at XX.X°C (Warning threshold: 38.0°C)"`.

---

### Step 4: High Humidity Warning Threshold
- **Trigger Parameter:** Relative humidity reaches or exceeds **$70.0\%$**.
- **Result:**
  - Severity: `WARNING`
  - Email: Dispatched with message `"Humidity Warning: Cabinet relative humidity elevated at XX.X% (Threshold: 70.0%)"`.

---

### Step 5: Critical Thermal Limit (Imminent Equipment Failure)
- **Trigger Parameter:** Temperature reaches or exceeds **$52.0^\circ\text{C}$** ($125.6^\circ\text{F}$).
- **Result:**
  - Severity: `CRITICAL`
  - Email: Dispatched with high-priority red styling:
    - Subject: `🔴 ThermoGuard AI — CRITICAL Alert: CRITICAL THERMAL LEVEL...`
    - Body: `"CRITICAL THERMAL LEVEL: Cabinet temperature reached XX.X°C. High risk of equipment failure."`

---

### Step 6: Critical Moisture Limit (Condensation Hazard)
- **Trigger Parameter:** Relative humidity reaches or exceeds **$85.0\%$**.
- **Result:**
  - Severity: `CRITICAL`
  - Email: Dispatched with high-priority red styling:
    - Subject: `🔴 ThermoGuard AI — CRITICAL Alert: CRITICAL MOISTURE LEVEL...`
    - Body: `"CRITICAL MOISTURE LEVEL: Cabinet humidity reached XX.X%. Condensation hazard."`

---

## 4. How to Test Each Trigger with Your Hardware

You can safely test every stage using your physical ESP32 and DHT sensor:

### Test 1: Trigger the AI Moisture Anomaly (Quickest Test)
1. Blow a long, warm breath directly onto the DHT sensor grid from 2–3 cm away.
2. **What happens:** The humidity will spike rapidly by $+15\%$ to $+30\%$ in a few seconds (e.g., from $50\% \to 75\%$).
3. **Trigger:** The $\Delta H$ rate of change triggers the **AI Moisture Anomaly** (`WARNING`).
4. **Verification:** Check your email inbox for the `⚠️ Early Warning: AI Anomaly Detected` alert.

### Test 2: Trigger the AI Thermal Anomaly
1. Firmly pinch the DHT sensor casing between your thumb and forefinger (body warmth transfers into the sensor).
2. Or hold a warm mug or gentle warm air near the sensor.
3. **What happens:** Temperature jumps by $+2^\circ\text{C}$ to $+4^\circ\text{C}$ in a couple of readings.
4. **Trigger:** The sudden thermal gradient triggers the **AI Thermal Surge** (`WARNING`).

### Test 3: Trigger the Critical Thermal Limit
1. Use warm air (e.g., hair dryer on low setting from 30 cm away) to bring the reading above $52^\circ\text{C}$.
2. **Trigger:** Hard **Critical Safety Limit** triggers.
3. **Verification:** Red critical email alert is delivered.

---

## 5. Anti-Flooding (Debounce) Protection

To prevent thousands of duplicate emails when an abnormal condition persists over time:
- **Alert Debouncer:** Alerts of the same category (`ai_anomaly`, `warn_temp`, `crit_temp`, etc.) are debounced for **30 seconds**.
- Once an alert is sent, the system will not send another email for the exact same event key until 30 seconds have elapsed, or until a new/higher severity event occurs.
