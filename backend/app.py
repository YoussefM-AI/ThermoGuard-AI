"""
ThermoGuard AI - Main Flask Application Server
Initializes SQLite database, registers REST blueprints, CORS middleware,
and hosts the premium frontend static dashboard.
"""

import os
import sys

# Ensure project root is available in path
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from flask import Flask, jsonify, send_from_directory  # noqa: E402

try:
    from flask_cors import CORS  # noqa: E402
except ImportError:
    CORS = None

from backend.database import DEFAULT_DB_PATH, init_db, insert_system_event  # noqa: E402
from backend.routes import api_bp  # noqa: E402

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend"))


def create_app(test_config=None) -> Flask:
    """
    Application factory for ThermoGuard AI.
    """
    app = Flask(__name__, static_folder=FRONTEND_DIR)

    # Enable CORS for all routes (enables ESP32 and remote browser dashboards)
    if CORS is not None:
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    else:

        @app.after_request
        def add_cors_headers(response):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

    # Database initialization
    if test_config and "DATABASE" in test_config:
        db_path = test_config["DATABASE"]
    else:
        db_path = os.getenv("THERMOGUARD_DB", os.getenv("CABINETSENSE_DB", DEFAULT_DB_PATH))

    os.environ["THERMOGUARD_DB"] = db_path
    os.environ["CABINETSENSE_DB"] = db_path
    app.config["DATABASE"] = db_path

    should_seed = test_config is None or not test_config.get("TESTING")
    init_db(db_path=db_path, seed=should_seed)

    # Register API blueprint
    app.register_blueprint(api_bp)

    # Static frontend serving
    @app.route("/", methods=["GET"])
    def serve_index():
        if os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
            return send_from_directory(FRONTEND_DIR, "index.html")
        return jsonify(
            {
                "service": "ThermoGuard AI Backend",
                "status": "online",
                "message": "Frontend index.html not yet generated. Visit /api/health for API status.",
            }
        ), 200

    @app.route("/<path:path>", methods=["GET"])
    def serve_static(path):
        target = os.path.join(FRONTEND_DIR, path)
        if os.path.exists(target):
            return send_from_directory(FRONTEND_DIR, path)
        return jsonify({"error": f"File '{path}' not found"}), 404

    # Log backend initialization event
    insert_system_event(
        event_type="SYSTEM_BOOT", description="ThermoGuard AI Backend service started", source="SYSTEM", db_path=db_path
    )

    return app


# WSGI application entrypoint for cloud hosting (e.g. gunicorn backend.app:app)
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    print(f"ThermoGuard AI Server running at http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
