"""
CabinetSense AI - Main Flask Application Server
Initializes SQLite database, registers REST blueprints, CORS middleware,
and hosts the premium frontend static dashboard.
"""

import os
import sys
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS

# Ensure project root is available in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.database import init_db, insert_system_event
from backend.routes import api_bp

FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend"))

def create_app(test_config=None) -> Flask:
    """
    Application factory for CabinetSense AI.
    """
    app = Flask(__name__, static_folder=FRONTEND_DIR)
    
    # Enable CORS for all routes (enables ESP32 and remote browser dashboards)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Database initialization
    if test_config and "DATABASE" in test_config:
        db_path = test_config["DATABASE"]
        os.environ["CABINETSENSE_DB"] = db_path
    else:
        db_path = os.getenv("CABINETSENSE_DB", DEFAULT_DB_PATH)
        
    init_db(db_path=db_path)

    # Register API blueprint
    app.register_blueprint(api_bp)

    # Static frontend serving
    @app.route("/", methods=["GET"])
    def serve_index():
        if os.path.exists(os.path.join(FRONTEND_DIR, "index.html")):
            return send_from_directory(FRONTEND_DIR, "index.html")
        return jsonify({
            "service": "CabinetSense AI Backend",
            "status": "online",
            "message": "Frontend index.html not yet generated. Visit /api/health for API status."
        }), 200

    @app.route("/<path:path>", methods=["GET"])
    def serve_static(path):
        target = os.path.join(FRONTEND_DIR, path)
        if os.path.exists(target):
            return send_from_directory(FRONTEND_DIR, path)
        return jsonify({"error": f"File '{path}' not found"}), 404

    # Log backend initialization event
    insert_system_event(
        event_type="SYSTEM_BOOT",
        description="CabinetSense AI Backend service started",
        source="SYSTEM",
        db_path=db_path
    )

    return app

if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    print(f"CabinetSense AI Server running at http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
