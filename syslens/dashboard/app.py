import os
import sys
import asyncio
import json
import logging
from typing import Dict, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from syslens.core.anomaly import AnomalyInterface
from syslens.core.health import SystemHealthEngine
from syslens.plugins.manager import PluginManager
from syslens.dashboard.socket import manager

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("syslens.dashboard")

app = FastAPI(
    title="SysLens API",
    description="Backend telemetry and anomaly diagnostic service.",
    version="1.0.0"
)

# Core subsystems
anomaly_interface = AnomalyInterface()
health_engine = SystemHealthEngine()
plugin_manager = PluginManager()

# Resolve web directory path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WEB_DIR = os.path.join(ROOT_DIR, "web")

# If running as an installed package, search for web files in nested package location
if not os.path.exists(os.path.join(WEB_DIR, "index.html")):
    PACKAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    WEB_DIR = os.path.join(PACKAGE_DIR, "dashboard", "static", "web")

logger.info(f"Serving dashboard files from: {WEB_DIR}")

# API routes
@app.get("/api/metrics")
def get_metrics() -> Dict[str, Any]:
    """Retrieve full system metrics, baseline stats, and active anomalies."""
    try:
        metrics = anomaly_interface.scan_system()
        # Execute plugins
        plugins_data = plugin_manager.execute_all(metrics)
        metrics["plugins_data"] = plugins_data

        # Calculate health score
        score, status = health_engine.calculate_score(metrics)
        # Apply plugins
        score = plugin_manager.modify_health_score(score, metrics)
        
        # Recalculate status with final score
        if score >= 80.0:
            status = "Healthy"
        elif score >= 50.0:
            status = "Degraded"
        else:
            status = "Critical"

        metrics["health"] = {"score": score, "status": status}
        return metrics
    except Exception as e:
        logger.error(f"Error gathering metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
def get_health() -> Dict[str, Any]:
    """Retrieve current health score, classification, and diagnostics suggestions."""
    metrics = get_metrics()
    diagnoses = health_engine.diagnose_issues(metrics)
    return {
        "score": metrics["health"]["score"],
        "status": metrics["health"]["status"],
        "diagnoses": diagnoses
    }

@app.get("/api/plugins")
def get_plugins() -> Dict[str, Any]:
    """Retrieve all loaded/registered plugins."""
    return {
        "plugins": plugin_manager.get_registered_plugins()
    }

# WebSocket route
@app.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket stream supplying real-time telemetry updates."""
    await manager.connect(websocket)
    try:
        # Loop and broadcast metrics every 1 second
        while True:
            metrics = get_metrics()
            await websocket.send_text(json.dumps(metrics))
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# HTML static routing
@app.get("/")
def read_root():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h2>SysLens Dashboard Web Files Not Found. Check web UI build assets.</h2>")

@app.get("/app.js")
def read_js():
    js_path = os.path.join(WEB_DIR, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")

# Serve any other static file (CSS, images) in the WEB_DIR
if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

def serve() -> None:
    """Launch the dashboard server."""
    logger.info("Initializing SysLens FastAPI server...")
    uvicorn.run("syslens.dashboard.app:app", host="127.0.0.1", port=8000, reload=False)

def run() -> None:
    """Launch the dashboard server (SDK Integration)."""
    serve()

if __name__ == "__main__":
    serve()
