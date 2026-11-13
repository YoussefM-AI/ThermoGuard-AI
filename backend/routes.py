"""
CabinetSense AI - REST API Routes Blueprint
Implements all required RESTful endpoints with validation, structured error responses,
simulation control, and CSV export.
"""

import os
import io
import csv
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, Response

from backend.database import (
    get_readings,
    get_latest_reading,
    get_alerts,
    acknowledge_alert,
    get_system_events,
    get_analytics_summary,
    get_db_connection
)
from backend.services import (
    validate_telemetry_payload,
    process_telemetry_reading,
    hardware_tracker
)
from simulation.simulator import simulator_instance
from ai.predict import get_model_info

api_bp = Blueprint("api", __name__, url_prefix="/api")

# -------------------------------------------------------------
# 1. HEALTH & SYSTEM STATUS
# -------------------------------------------------------------

@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health status and database connectivity check."""
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": db_status,
        "version": "1.0.0",
        "service": "CabinetSense AI Industrial Engine"
    }), 200

@api_bp.route("/status", methods=["GET"])
def system_status():
    """
    Consolidated system status: hardware connection, simulation engine,
    AI model readiness, and top-level KPIs.
    """
    hw_status = hardware_tracker.get_status()
    sim_status = simulator_instance.get_status()
    ai_status = get_model_info()
    latest = get_latest_reading()
    summary = get_analytics_summary()

    # Determine primary monitoring mode
    if hw_status["connected"]:
        active_mode = "HARDWARE"
    elif sim_status["running"]:
        active_mode = "SIMULATION"
    else:
        active_mode = "IDLE"

    return jsonify({
        "system_time": datetime.now(timezone.utc).isoformat(),
        "monitoring_mode": active_mode,
        "hardware": hw_status,
        "simulation": sim_status,
        "ai": ai_status,
        "latest_reading": latest,
        "summary": summary
    }), 200

# -------------------------------------------------------------
# 2. TELEMETRY READINGS
# -------------------------------------------------------------

@api_bp.route("/readings", methods=["POST"])
def post_reading():
    """
    Ingests sensor telemetry from ESP32 hardware or Python simulator.
    Validates payload, evaluates AI anomaly detection, triggers alerts, and stores in SQLite.
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    payload = request.get_json(silent=True)
    is_valid, error_msg, valid_data = validate_telemetry_payload(payload)
    if not is_valid:
        return jsonify({"error": "Validation failed", "details": error_msg}), 400

    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr or "127.0.0.1").split(",")[0].strip()

    try:
        result = process_telemetry_reading(valid_data, client_ip=client_ip)
        if result.get("status") == "ignored":
            return jsonify({"status": "ignored", "message": result.get("reason")}), 200
        return jsonify({"status": "success", "data": result}), 201
    except Exception as e:
        return jsonify({"error": "Internal processing error", "details": str(e)}), 500

@api_bp.route("/readings", methods=["GET"])
def get_readings_list():
    """
    Retrieves filtered list of sensor readings.
    Query params: limit (default: 50), offset (default: 0), source, anomalies_only (bool), order ('ASC'/'DESC')
    """
    try:
        limit = int(request.args.get("limit", 50))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        return jsonify({"error": "limit and offset must be integers"}), 400

    source = request.args.get("source")
    anomalies_only = request.args.get("anomalies_only", "false").lower() in ("true", "1")
    order = request.args.get("order", "DESC").upper()

    readings = get_readings(limit=limit, offset=offset, source=source, anomalies_only=anomalies_only, order=order)
    return jsonify({
        "status": "success",
        "count": len(readings),
        "limit": limit,
        "offset": offset,
        "readings": readings
    }), 200

@api_bp.route("/readings/latest", methods=["GET"])
def get_latest_reading_endpoint():
    """Retrieves the most recent single sensor observation."""
    source = request.args.get("source")
    latest = get_latest_reading(source=source)
    return jsonify({
        "status": "success",
        "reading": latest
    }), 200

# -------------------------------------------------------------
# 3. ALERTS & NOTIFICATIONS
# -------------------------------------------------------------

@api_bp.route("/alerts", methods=["GET"])
def get_alerts_endpoint():
    """Retrieves system and environmental alerts with optional filters."""
    try:
        limit = int(request.args.get("limit", 50))
    except ValueError:
        return jsonify({"error": "limit must be an integer"}), 400

    severity = request.args.get("severity")
    status = request.args.get("status")

    alerts = get_alerts(limit=limit, severity=severity, status=status)
    return jsonify({
        "status": "success",
        "count": len(alerts),
        "alerts": alerts
    }), 200

@api_bp.route("/alerts/<int:alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert_endpoint(alert_id: int):
    """Marks an unresolved alert as acknowledged by user."""
    updated = acknowledge_alert(alert_id)
    if not updated:
        return jsonify({"error": f"Alert #{alert_id} not found"}), 404
    return jsonify({
        "status": "success",
        "message": f"Alert #{alert_id} acknowledged successfully",
        "alert_id": alert_id
    }), 200

# -------------------------------------------------------------
# 4. SIMULATION CONTROL
# -------------------------------------------------------------

@api_bp.route("/simulation/start", methods=["POST"])
def start_simulation():
    """Starts simulated telemetry injection."""
    data = request.get_json(silent=True) or {}
    scenario_key = data.get("scenario", "normal")
    interval = float(data.get("interval", 2.0))

    if not simulator_instance.set_scenario(scenario_key):
        return jsonify({"error": f"Invalid scenario '{scenario_key}'"}), 400

    simulator_instance.set_interval(interval)
    started = simulator_instance.start()
    
    return jsonify({
        "status": "success",
        "started": started,
        "simulation": simulator_instance.get_status()
    }), 200

@api_bp.route("/simulation/stop", methods=["POST"])
def stop_simulation():
    """Stops simulated telemetry injection."""
    stopped = simulator_instance.stop()
    return jsonify({
        "status": "success",
        "stopped": stopped,
        "simulation": simulator_instance.get_status()
    }), 200

@api_bp.route("/simulation/status", methods=["GET"])
def get_simulation_status():
    """Returns current simulator engine state."""
    return jsonify({
        "status": "success",
        "simulation": simulator_instance.get_status()
    }), 200

# -------------------------------------------------------------
# 5. ANALYTICS & EVENTS
# -------------------------------------------------------------

@api_bp.route("/analytics", methods=["GET"])
def get_analytics():
    """Returns summary statistics and aggregation distributions."""
    summary = get_analytics_summary()
    return jsonify({
        "status": "success",
        "analytics": summary
    }), 200

@api_bp.route("/events", methods=["GET"])
def get_events():
    """Returns recent audit events."""
    limit = int(request.args.get("limit", 50))
    events = get_system_events(limit=limit)
    return jsonify({
        "status": "success",
        "count": len(events),
        "events": events
    }), 200

# -------------------------------------------------------------
# 6. AI INTELLIGENCE CENTER & TRAINING
# -------------------------------------------------------------

@api_bp.route("/ai/status", methods=["GET"])
def ai_status_endpoint():
    """Returns details on the Isolation Forest model artifact and training metrics."""
    return jsonify({
        "status": "success",
        "ai": get_model_info()
    }), 200

@api_bp.route("/ai/train", methods=["POST"])
def train_ai_endpoint():
    """Executes retraining of the Isolation Forest model from historical/dataset data."""
    from ai.train_model import train_isolation_forest
    try:
        metrics = train_isolation_forest()
        return jsonify({
            "status": "success",
            "message": "Isolation Forest model trained and serialized successfully",
            "metrics": metrics
        }), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Training failed: {str(e)}"
        }), 500

# -------------------------------------------------------------
# 7. CSV EXPORT
# -------------------------------------------------------------

@api_bp.route("/export/csv", methods=["GET"])
def export_csv():
    """Exports recorded cabinet telemetry to a CSV file."""
    limit = int(request.args.get("limit", 5000))
    readings = get_readings(limit=limit, order="ASC")
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Temperature (°C)", "Humidity (%)", "Source", "Is Anomaly", "Anomaly Score"])
    
    for r in readings:
        writer.writerow([
            r["id"],
            r["timestamp"],
            r["temperature"],
            r["humidity"],
            r["source"],
            r["is_anomaly"],
            r["anomaly_score"]
        ])
    
    output.seek(0)
    filename = f"cabinetsense_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
