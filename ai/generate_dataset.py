"""
CabinetSense AI - Training & Evaluation Dataset Generator
Generates realistic industrial electrical cabinet environmental telemetry.
Includes normal operational cycles and realistic environmental anomalies.
"""

import os
import math
import random
import argparse
from datetime import datetime, timedelta, timezone
import pandas as pd
import numpy as np

def generate_cabinet_dataset(
    n_samples: int = 10000,
    interval_seconds: int = 10,
    anomaly_ratio: float = 0.06,
    random_seed: int = 42
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

    start_time = datetime.now(timezone.utc) - timedelta(seconds=n_samples * interval_seconds)
    timestamps = [start_time + timedelta(seconds=i * interval_seconds) for i in range(n_samples)]

    records = []
    
    # Base operational baseline
    base_temp = 24.5
    base_hum = 45.0
    
    # Anomaly injection schedule
    n_anomalies = int(n_samples * anomaly_ratio)
    anomaly_indices = set(np.random.choice(range(50, n_samples - 50), size=n_anomalies, replace=False))
    
    # We will cluster some anomalies into continuous incident episodes
    # Group random indices into small bursts of 10-25 samples
    burst_starts = sorted(list(anomaly_indices))[::15]
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
        # 24-hour diurnal ambient cycle
        hour = ts.hour + ts.minute / 60.0
        diurnal_temp = 2.0 * math.sin((hour - 8.0) * math.pi / 12.0)
        diurnal_hum = -1.5 * math.sin((hour - 8.0) * math.pi / 12.0)
        
        # Factory operating hours load (8:00 - 18:00 has slightly higher cabinet heat)
        work_load = 1.2 if (8 <= ts.hour <= 18) else 0.0
        
        # Micro-fluctuations
        temp_noise = np.random.normal(0, 0.25)
        hum_noise = np.random.normal(0, 0.45)
        
        temp = base_temp + diurnal_temp + work_load + temp_noise
        hum = base_hum + diurnal_hum - (work_load * 0.4) + hum_noise
        
        is_anomaly = 0
        scenario_label = "normal"
        
        if i in incident_indices:
            is_anomaly = 1
            a_type = incident_types[i]
            scenario_label = a_type
            
            if a_type == "thermal_spike":
                # Heat rises sharply into 45°C - 65°C range
                temp += np.random.uniform(15.0, 32.0)
                hum -= np.random.uniform(5.0, 15.0)
            elif a_type == "moisture_ingress":
                # Humidity surges to 75% - 92%
                hum += np.random.uniform(28.0, 48.0)
                temp += np.random.uniform(-1.0, 2.0)
            elif a_type == "combined_distress":
                # Both heat and humidity surge
                temp += np.random.uniform(18.0, 35.0)
                hum += np.random.uniform(25.0, 45.0)
        
        # Realistic sensor clipping
        temp = max(10.0, min(85.0, temp))
        hum = max(10.0, min(98.0, hum))
        
        records.append({
            "timestamp": ts.isoformat(),
            "temperature": round(float(temp), 2),
            "humidity": round(float(hum), 2),
            "source": "SIMULATION",
            "is_anomaly": is_anomaly,
            "scenario": scenario_label
        })

    df = pd.DataFrame(records)
    return df

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic CabinetSense dataset.")
    parser.add_argument("--samples", type=int, default=12000, help="Number of telemetry data points (default: 12000)")
    parser.add_argument("--interval", type=int, default=10, help="Seconds between readings (default: 10s)")
    parser.add_argument("--anomaly-ratio", type=float, default=0.06, help="Fraction of anomalous points (default: 0.06)")
    parser.add_argument("--output", type=str, default="data/cabinet_data.csv", help="Output CSV path")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    print(f"Generating {args.samples} cabinet telemetry records...")
    df = generate_cabinet_dataset(
        n_samples=args.samples,
        interval_seconds=args.interval,
        anomaly_ratio=args.anomaly_ratio
    )
    
    df.to_csv(args.output, index=False)
    print(f"Dataset successfully saved to: {args.output}")
    print("\nDataset Summary:")
    print(f"  Total records    : {len(df)}")
    print(f"  Normal records   : {(df['is_anomaly'] == 0).sum()} ({((df['is_anomaly'] == 0).mean()*100):.1f}%)")
    print(f"  Anomalous records: {(df['is_anomaly'] == 1).sum()} ({((df['is_anomaly'] == 1).mean()*100):.1f}%)")
    print("\nTemperature Statistics (°C):")
    print(df.groupby('is_anomaly')['temperature'].describe())
    print("\nHumidity Statistics (%):")
    print(df.groupby('is_anomaly')['humidity'].describe())

if __name__ == "__main__":
    main()
