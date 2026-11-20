"""
ThermoGuard AI - Training & Evaluation Dataset Generator
Generates realistic industrial electrical cabinet environmental telemetry.
Includes normal operational cycles and realistic environmental anomalies.
"""

import argparse
import math
import os
import random
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd


def generate_cabinet_dataset(
    n_samples: int = 10000, interval_seconds: int = 10, anomaly_ratio: float = 0.06, random_seed: int = 42
) -> pd.DataFrame:
    """
    Synthesizes continuous time-series data modeling an electrical cabinet.
    - Normal state: ~24.5°C base, ~45% base humidity, daily thermal cycle (HVAC on/off, ambient),
      minor load variations during industrial operating hours.
    - Anomaly states (controlled ~6%):
      1. Thermal creep (overheated transformer / loose contact / fan breakdown)
      2. Moisture ingress (cabinet gasket seal breach / ambient water leak)
      3. Extreme combined distress (cooling failure under high load)
    """
    np.random.seed(random_seed)
    random.seed(random_seed)

    start_time = datetime.now(UTC) - timedelta(seconds=n_samples * interval_seconds)
    timestamps = [start_time + timedelta(seconds=i * interval_seconds) for i in range(n_samples)]

    records = []

    # Base operational baseline (Industrial ambient & enclosure profile)
    # Calibrated for realistic ambient conditions: 16°C - 32°C temp, 30% - 66% humidity
    center_temp = 23.5
    center_hum = 48.0

    # Anomaly injection schedule
    n_anomalies = int(n_samples * anomaly_ratio)
    anomaly_indices = set(np.random.choice(range(50, n_samples - 50), size=n_anomalies, replace=False))

    # Cluster anomalies into continuous incident episodes (bursts of 8-25 samples)
    burst_starts = sorted(anomaly_indices)[::15]
    incident_indices = set()
    incident_types = {}

    for b_start in burst_starts:
        burst_len = random.randint(8, 25)
        a_type = random.choice(["thermal_spike", "moisture_ingress", "combined_distress"])
        for idx in range(b_start, min(n_samples, b_start + burst_len)):
            incident_indices.add(idx)
            incident_types[idx] = a_type

    # Generation loop
    for i, ts in enumerate(timestamps):
        # Multi-day ambient weather / seasonal drift (smooth long-period wave)
        drift_phase = i * 2.0 * math.pi / max(1, n_samples * 0.3)
        ambient_temp_drift = 4.5 * math.sin(drift_phase)
        ambient_hum_drift = 12.0 * math.cos(drift_phase)

        # 24-hour diurnal ambient cycle
        hour = ts.hour + ts.minute / 60.0
        diurnal_temp = 2.5 * math.sin((hour - 8.0) * math.pi / 12.0)
        diurnal_hum = -2.5 * math.sin((hour - 8.0) * math.pi / 12.0)

        # Factory operating hours load (8:00 - 18:00 has slightly higher cabinet heat)
        work_load = 1.5 if (8 <= ts.hour <= 18) else 0.0

        # Micro-fluctuations
        temp_noise = np.random.normal(0, 0.25)
        hum_noise = np.random.normal(0, 0.45)

        temp = center_temp + ambient_temp_drift + diurnal_temp + work_load + temp_noise
        hum = center_hum + ambient_hum_drift + diurnal_hum - (work_load * 0.3) + hum_noise

        is_anomaly = 0
        scenario_label = "normal"

        if i in incident_indices:
            is_anomaly = 1
            a_type = incident_types[i]
            scenario_label = a_type

            if a_type == "thermal_spike":
                # Critical heat surge into 42°C - 68°C range
                temp = max(temp + np.random.uniform(16.0, 32.0), np.random.uniform(43.0, 65.0))
                hum = max(15.0, hum - np.random.uniform(5.0, 15.0))
            elif a_type == "moisture_ingress":
                # Humidity surges to 76% - 95%
                hum = max(hum + np.random.uniform(25.0, 45.0), np.random.uniform(76.0, 95.0))
                temp += np.random.uniform(-1.0, 2.0)
            elif a_type == "combined_distress":
                # Both heat and moisture surge into critical danger
                temp = max(temp + np.random.uniform(18.0, 35.0), np.random.uniform(44.0, 68.0))
                hum = max(hum + np.random.uniform(25.0, 45.0), np.random.uniform(78.0, 96.0))

        # Realistic sensor clipping
        temp = max(5.0, min(85.0, temp))
        hum = max(10.0, min(98.0, hum))

        records.append(
            {
                "timestamp": ts.isoformat(),
                "temperature": round(float(temp), 2),
                "humidity": round(float(hum), 2),
                "source": "HARDWARE",
                "is_anomaly": is_anomaly,
                "scenario": scenario_label,
            }
        )

    df = pd.DataFrame(records)
    return df


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic ThermoGuard AI dataset.")
    parser.add_argument("--samples", type=int, default=12000, help="Number of telemetry data points (default: 12000)")
    parser.add_argument("--interval", type=int, default=10, help="Seconds between readings (default: 10s)")
    parser.add_argument("--anomaly-ratio", type=float, default=0.06, help="Fraction of anomalous points (default: 0.06)")
    parser.add_argument("--output", type=str, default="data/cabinet_data.csv", help="Output CSV path")
    args = parser.parse_args()

    out_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(out_dir, exist_ok=True)

    print(f"Generating {args.samples} cabinet telemetry records...")
    df = generate_cabinet_dataset(n_samples=args.samples, interval_seconds=args.interval, anomaly_ratio=args.anomaly_ratio)

    df.to_csv(args.output, index=False)
    print(f"Dataset successfully saved to: {args.output}")
    print("\nDataset Summary:")
    print(f"  Total records    : {len(df)}")
    print(f"  Normal records   : {(df['is_anomaly'] == 0).sum()} ({((df['is_anomaly'] == 0).mean() * 100):.1f}%)")
    print(f"  Anomalous records: {(df['is_anomaly'] == 1).sum()} ({((df['is_anomaly'] == 1).mean() * 100):.1f}%)")
    print("\nTemperature Statistics (°C):")
    print(df.groupby("is_anomaly")["temperature"].describe())
    print("\nHumidity Statistics (%):")
    print(df.groupby("is_anomaly")["humidity"].describe())


if __name__ == "__main__":
    main()
