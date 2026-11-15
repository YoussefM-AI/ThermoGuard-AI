"""
ThermoGuard AI - Database Management Layer
Provides thread-safe SQLite operations, schema auto-initialization, and indexing.
"""

import os
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Any

# Retain existing data if present, otherwise default to thermoguard.db
_LEGACY_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cabinetsense.db")
_NEW_DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "thermoguard.db")
DEFAULT_DB_PATH = _LEGACY_DB if os.path.exists(_LEGACY_DB) else _NEW_DB


def _create_tables(cur: sqlite3.Cursor):
    """Creates tables and indexes if they do not exist."""
    # 1. Readings Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS readings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        temperature REAL NOT NULL,
        humidity REAL NOT NULL,
        source TEXT NOT NULL CHECK(source IN ('HARDWARE', 'SIMULATION')),
        is_anomaly INTEGER DEFAULT 0,
        anomaly_score REAL DEFAULT 0.0
    );
    """)

    # 2. Alerts Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        severity TEXT NOT NULL CHECK(severity IN ('CRITICAL', 'WARNING', 'INFO')),
        message TEXT NOT NULL,
        temperature REAL,
        humidity REAL,
        anomaly_score REAL,
        status TEXT NOT NULL DEFAULT 'UNRESOLVED' CHECK(status IN ('UNRESOLVED', 'ACKNOWLEDGED', 'RESOLVED'))
    );
    """)

    # 3. System Events Table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS system_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        event_type TEXT NOT NULL,
        description TEXT NOT NULL,
        source TEXT NOT NULL
    );
    """)

    # Indexes for fast historical queries & dashboards
    cur.execute("CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON readings(timestamp DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_readings_source ON readings(source);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_readings_anomaly ON readings(is_anomaly);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp DESC);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events(timestamp DESC);")


def ensure_schema(conn: sqlite3.Connection):
    """Verifies that all required tables and indexes exist; auto-creates missing ones."""
    try:
        cur = conn.cursor()
        _create_tables(cur)
        conn.commit()
    except sqlite3.OperationalError:
        # If another worker or thread already committed schema, continue safely
        pass


def seed_initial_readings_if_empty(conn: sqlite3.Connection):
    """Populates baseline nominal readings if the database is brand new and empty."""
    from datetime import timedelta

    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM readings")
        count = cur.fetchone()[0]
        if count == 0:
            now = datetime.now(UTC)
            base_t = 24.6
            base_h = 45.2
            for i in range(15):
                dt = now - timedelta(seconds=(14 - i) * 3)
                t = round(base_t + (0.25 * (i % 3)) - 0.15, 2)
                h = round(base_h + (0.4 * (i % 2)) - 0.2, 2)
                cur.execute(
                    """
                    INSERT INTO readings (timestamp, temperature, humidity, source, is_anomaly, anomaly_score)
                    VALUES (?, ?, ?, 'SIMULATION', 0, 0.065)
                """,
                    (dt.isoformat(), t, h),
                )
            conn.commit()
    except sqlite3.OperationalError:
        pass


def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    """
    Creates a thread-safe connection to SQLite with dictionary cursor, 30s busy timeout, and WAL mode.
    Guarantees schema exists automatically without locking contention.
    """
    path = db_path or os.getenv("THERMOGUARD_DB", os.getenv("CABINETSENSE_DB", DEFAULT_DB_PATH))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA busy_timeout = 30000;")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
    except sqlite3.OperationalError:
        pass

    ensure_schema(conn)

    return conn


def init_db(db_path: str | None = None, seed: bool = False):
    """
    Initializes database tables, performance indexes, and seeds baseline readings safely.
    """
    conn = get_db_connection(db_path)
    try:
        ensure_schema(conn)
        if seed:
            seed_initial_readings_if_empty(conn)
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()


# -------------------------------------------------------------
# READINGS OPERATIONS
# -------------------------------------------------------------


def is_duplicate_reading(
    conn: sqlite3.Connection, temperature: float, humidity: float, source: str, window_seconds: float = 0.5
) -> bool:
    """
    Prevents duplicate submissions if client sends repeated identical packets within <0.5s.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT timestamp, temperature, humidity FROM readings
        WHERE source = ?
        ORDER BY id DESC LIMIT 1
    """,
        (source,),
    )
    row = cur.fetchone()
    if not row:
        return False

    try:
        last_dt = datetime.fromisoformat(row["timestamp"])
        now_dt = datetime.now(UTC)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=UTC)
        diff = abs((now_dt - last_dt).total_seconds())
        if diff < window_seconds and abs(row["temperature"] - temperature) < 0.001 and abs(row["humidity"] - humidity) < 0.001:
            return True
    except (ValueError, TypeError, KeyError):
        return False
    return False


def insert_reading(
    temperature: float,
    humidity: float,
    source: str = "SIMULATION",
    is_anomaly: int = 0,
    anomaly_score: float = 0.0,
    timestamp: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Inserts a validated telemetry reading into SQLite.
    """
    if timestamp is None:
        timestamp = datetime.now(UTC).isoformat()

    conn = get_db_connection(db_path)

    # Check duplicate
    if is_duplicate_reading(conn, temperature, humidity, source):
        conn.close()
        return {"duplicate": True, "message": "Ignored duplicate payload within deduplication window"}

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO readings (timestamp, temperature, humidity, source, is_anomaly, anomaly_score)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (timestamp, float(temperature), float(humidity), source.upper(), int(is_anomaly), float(anomaly_score)),
    )
    reading_id = cur.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": reading_id,
        "timestamp": timestamp,
        "temperature": round(float(temperature), 2),
        "humidity": round(float(humidity), 2),
        "source": source.upper(),
        "is_anomaly": int(is_anomaly),
        "anomaly_score": round(float(anomaly_score), 4),
    }


def get_latest_reading(source: str | None = None, db_path: str | None = None) -> dict[str, Any] | None:
    """
    Retrieves the most recent single reading.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    if source:
        cur.execute("SELECT * FROM readings WHERE source = ? ORDER BY id DESC LIMIT 1", (source.upper(),))
    else:
        cur.execute("SELECT * FROM readings ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_readings(
    limit: int = 100,
    offset: int = 0,
    source: str | None = None,
    anomalies_only: bool = False,
    order: str = "DESC",
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    """
    Retrieves historical readings with flexible filtering.
    When order='ASC', returns the latest N readings in chronological order for time-series charts.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    where_parts = []
    params = []

    if source:
        where_parts.append("source = ?")
        params.append(source.upper())

    if anomalies_only:
        where_parts.append("is_anomaly = 1")

    where_sql = (" AND " + " AND ".join(where_parts)) if where_parts else ""
    lim = max(1, min(limit, 2000))
    off = max(0, offset)

    if order.upper() == "ASC":
        query = f"""
            SELECT * FROM (
                SELECT * FROM readings WHERE 1=1{where_sql}
                ORDER BY id DESC LIMIT ? OFFSET ?
            ) ORDER BY id ASC
        """
    else:
        query = f"SELECT * FROM readings WHERE 1=1{where_sql} ORDER BY id DESC LIMIT ? OFFSET ?"

    params.extend([lim, off])
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# -------------------------------------------------------------
# ALERTS OPERATIONS
# -------------------------------------------------------------


def insert_alert(
    severity: str,
    message: str,
    temperature: float | None = None,
    humidity: float | None = None,
    anomaly_score: float | None = None,
    status: str = "UNRESOLVED",
    timestamp: str | None = None,
    db_path: str | None = None,
) -> dict[str, Any]:
    """
    Creates an alert record and writes a corresponding system event.
    """
    if timestamp is None:
        timestamp = datetime.now(UTC).isoformat()

    severity = severity.upper()
    if severity not in ("CRITICAL", "WARNING", "INFO"):
        severity = "WARNING"

    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO alerts (timestamp, severity, message, temperature, humidity, anomaly_score, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        (timestamp, severity, message, temperature, humidity, anomaly_score, status),
    )
    alert_id = cur.lastrowid

    # Mirror event
    cur.execute(
        """
        INSERT INTO system_events (timestamp, event_type, description, source)
        VALUES (?, ?, ?, ?)
    """,
        (timestamp, f"ALERT_{severity}", message, "ALERT_ENGINE"),
    )

    conn.commit()
    conn.close()

    return {
        "id": alert_id,
        "timestamp": timestamp,
        "severity": severity,
        "message": message,
        "temperature": temperature,
        "humidity": humidity,
        "anomaly_score": anomaly_score,
        "status": status,
    }


def get_alerts(
    limit: int = 50, severity: str | None = None, status: str | None = None, db_path: str | None = None
) -> list[dict[str, Any]]:
    """
    Retrieves alerts with filtering options.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    query = "SELECT * FROM alerts WHERE 1=1"
    params = []

    if severity:
        query += " AND severity = ?"
        params.append(severity.upper())
    if status:
        query += " AND status = ?"
        params.append(status.upper())

    query += " ORDER BY id DESC LIMIT ?"
    params.append(max(1, min(limit, 500)))

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def acknowledge_alert(alert_id: int, db_path: str | None = None) -> bool:
    """
    Acknowledge an alert by ID.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE alerts SET status = 'ACKNOWLEDGED' WHERE id = ?", (alert_id,))
    updated = cur.rowcount > 0
    if updated:
        ts = datetime.now(UTC).isoformat()
        cur.execute(
            """
            INSERT INTO system_events (timestamp, event_type, description, source)
            VALUES (?, 'ALERT_ACKNOWLEDGED', ?, 'USER')
        """,
            (ts, f"Alert #{alert_id} acknowledged"),
        )
    conn.commit()
    conn.close()
    return updated


def acknowledge_all_alerts(db_path: str | None = None) -> int:
    """
    Acknowledge all UNRESOLVED alerts in the database.
    Returns the count of alerts updated.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("UPDATE alerts SET status = 'ACKNOWLEDGED' WHERE status = 'UNRESOLVED'")
    count = cur.rowcount
    if count > 0:
        ts = datetime.now(UTC).isoformat()
        cur.execute(
            """
            INSERT INTO system_events (timestamp, event_type, description, source)
            VALUES (?, 'ALERTS_BULK_ACKNOWLEDGED', ?, 'USER')
        """,
            (ts, f"Bulk acknowledged {count} unresolved alerts"),
        )
    conn.commit()
    conn.close()
    return count


# -------------------------------------------------------------
# SYSTEM EVENTS & ANALYTICS
# -------------------------------------------------------------


def insert_system_event(event_type: str, description: str, source: str = "SYSTEM", db_path: str | None = None):
    """
    Records an operational system event.
    """
    ts = datetime.now(UTC).isoformat()
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO system_events (timestamp, event_type, description, source)
        VALUES (?, ?, ?, ?)
    """,
        (ts, event_type, description, source),
    )
    conn.commit()
    conn.close()


def get_system_events(limit: int = 50, db_path: str | None = None) -> list[dict[str, Any]]:
    """
    Retrieves recent system events.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM system_events ORDER BY id DESC LIMIT ?", (max(1, min(limit, 200)),))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_analytics_summary(hours: float | None = None, db_path: str | None = None) -> dict[str, Any]:
    """
    Calculates summary telemetry statistics, anomaly counts, and alert distribution.
    When hours is provided (e.g. 24), aggregates are scoped to the rolling time window.
    Never fabricates metrics: returns zeros if no data exists.
    """
    conn = get_db_connection(db_path)
    cur = conn.cursor()

    time_filter_readings = ""
    time_filter_alerts = ""
    params_readings: list[Any] = []
    params_alerts: list[Any] = []

    if hours is not None and hours > 0:
        cutoff = (datetime.now(UTC) - timedelta(hours=hours)).isoformat()
        time_filter_readings = " WHERE timestamp >= ?"
        time_filter_alerts = " WHERE timestamp >= ?"
        params_readings = [cutoff]
        params_alerts = [cutoff]

    # Total counts
    cur.execute(
        f"SELECT COUNT(*), COUNT(CASE WHEN is_anomaly = 1 THEN 1 END) FROM readings{time_filter_readings}",
        params_readings,
    )
    total_readings, total_anomalies = cur.fetchone()

    # Aggregates
    cur.execute(
        f"""
        SELECT
            MIN(temperature), MAX(temperature), AVG(temperature),
            MIN(humidity), MAX(humidity), AVG(humidity)
        FROM readings{time_filter_readings}
    """,
        params_readings,
    )
    t_min, t_max, t_avg, h_min, h_max, h_avg = cur.fetchone()

    # Source breakdown
    cur.execute(
        f"SELECT source, COUNT(*) FROM readings{time_filter_readings} GROUP BY source",
        params_readings,
    )
    sources = dict(cur.fetchall())

    # Alerts breakdown
    cur.execute(
        f"""
        SELECT
            COUNT(*),
            COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END),
            COUNT(CASE WHEN severity = 'WARNING' THEN 1 END),
            COUNT(CASE WHEN status = 'UNRESOLVED' THEN 1 END)
        FROM alerts{time_filter_alerts}
    """,
        params_alerts,
    )
    total_alerts, critical_alerts, warning_alerts, unresolved_alerts = cur.fetchone()

    conn.close()

    return {
        "window_hours": hours,
        "readings_count": total_readings or 0,
        "anomalies_count": total_anomalies or 0,
        "anomaly_rate_pct": round((total_anomalies / total_readings * 100), 2) if total_readings else 0.0,
        "temperature": {
            "min": round(t_min, 2) if t_min is not None else None,
            "max": round(t_max, 2) if t_max is not None else None,
            "avg": round(t_avg, 2) if t_avg is not None else None,
        },
        "humidity": {
            "min": round(h_min, 2) if h_min is not None else None,
            "max": round(h_max, 2) if h_max is not None else None,
            "avg": round(h_avg, 2) if h_avg is not None else None,
        },
        "sources": {"hardware": sources.get("HARDWARE", 0), "simulation": sources.get("SIMULATION", 0)},
        "alerts": {
            "total": total_alerts or 0,
            "critical": critical_alerts or 0,
            "warning": warning_alerts or 0,
            "unresolved": unresolved_alerts or 0,
        },
    }


def get_24h_summary(db_path: str | None = None) -> dict[str, Any]:
    """Retrieves analytics summary specifically over the last 24 hours."""
    return get_analytics_summary(hours=24.0, db_path=db_path)
