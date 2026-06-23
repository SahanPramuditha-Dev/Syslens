import os
import sys
import asyncio
import json
import logging
import subprocess
from contextlib import asynccontextmanager
from typing import Dict, Any

import uvicorn
import webbrowser
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan handler — opens dashboard in default browser on startup."""
    try:
        logger.info("Auto-opening dashboard web UI in browser...")
        webbrowser.open("http://127.0.0.1:8000")
    except Exception as e:
        logger.error(f"Failed to auto-open web browser: {e}")
    yield  # Application runs here


app = FastAPI(
    title="SysLens API",
    description="Backend telemetry and anomaly diagnostic service.",
    version="1.0.0",
    lifespan=lifespan,
)

# Core subsystems
anomaly_interface = AnomalyInterface()
health_engine = SystemHealthEngine()
plugin_manager = PluginManager()

PLAYBOOK_COMMANDS = {
    "sfc_scannow": {
        "name": "SFC Integrity Check",
        "cmd": ["sfc", "/scannow"],
        "desc": "Scans and repairs corrupted Windows system files.",
        "caution": "Takes 5-15 minutes. Do not close or shut down during execution.",
        "type": "cli",
        "category": "repair",
        "requires_admin": True
    },
    "dism_restore": {
        "name": "DISM Restore Health",
        "cmd": ["DISM", "/Online", "/Cleanup-Image", "/RestoreHealth"],
        "desc": "Repairs Windows system image using Windows Update.",
        "caution": "Takes 10-15 minutes. Requires active internet connection.",
        "type": "cli",
        "category": "repair",
        "requires_admin": True
    },
    "dism_scan": {
        "name": "DISM Scan Health",
        "cmd": ["DISM", "/Online", "/Cleanup-Image", "/ScanHealth"],
        "desc": "Scans system image cache for corruption flags.",
        "caution": "Takes 2-5 minutes. Safe diagnostic check.",
        "type": "cli",
        "category": "repair",
        "requires_admin": True
    },
    "battery_report": {
        "name": "Generate Battery Report",
        "cmd": ["powercfg", "/batteryreport"],
        "desc": "Generates a detailed battery lifecycle and health report.",
        "caution": "Saves report as HTML in the current SysLens directory.",
        "type": "cli",
        "category": "power",
        "requires_admin": False
    },
    "energy_audit": {
        "name": "Energy Efficiency Audit",
        "cmd": ["powercfg", "/energy"],
        "desc": "Runs a 60-second audit of power consumption and efficiency.",
        "caution": "Takes 60 seconds. Leave system idle during audit.",
        "type": "cli",
        "category": "power",
        "requires_admin": True
    },
    "system_info": {
        "name": "System Info Summary",
        "cmd": ["systeminfo"],
        "desc": "Collects detailed hardware and OS configuration summary.",
        "caution": "Takes 10-15 seconds to inventory patches and drivers.",
        "type": "cli",
        "category": "power",
        "requires_admin": False
    },
    "ssd_trim": {
        "name": "SSD TRIM Optimization",
        "cmd": ["defrag", "C:", "/O"],
        "desc": "Trims and optimizes local SSD/HDD storage drives.",
        "caution": "Takes 5-10 seconds. Safe performance uplift.",
        "type": "cli",
        "category": "power",
        "requires_admin": True
    },
    "flush_dns": {
        "name": "Flush DNS Resolver Cache",
        "cmd": ["ipconfig", "/flushdns"],
        "desc": "Clears local DNS resolver cache to resolve connectivity issues.",
        "caution": "Instant action. Clears all cached domain-to-IP resolutions.",
        "type": "cli",
        "category": "network",
        "requires_admin": False
    },
    "ping_test": {
        "name": "Ping Test (google.com)",
        "cmd": ["ping", "google.com"],
        "desc": "Pings google.com to verify external network latency.",
        "caution": "Takes 4 seconds. Standard ICMP test.",
        "type": "cli",
        "category": "network",
        "requires_admin": False
    },
    "winsock_reset": {
        "name": "Netsh Winsock Reset",
        "cmd": ["netsh", "winsock", "reset"],
        "desc": "Resets the socket catalog layer to repair TCP/IP stack corruption.",
        "caution": "Requires administrative privileges. **Requires a system reboot after completion.**",
        "type": "cli",
        "category": "network",
        "requires_admin": True
    },
    "open_resmon": {
        "name": "Launch Resource Monitor",
        "cmd": ["resmon"],
        "desc": "Opens the legacy Windows Resource Monitor for deep CPU/disk metrics.",
        "caution": "Launches interactive GUI panel on host system desktop.",
        "type": "gui",
        "category": "power",
        "requires_admin": False
    },
    "open_perfmon": {
        "name": "Launch Performance Monitor",
        "cmd": ["perfmon"],
        "desc": "Opens legacy Windows Performance MMC console.",
        "caution": "Launches interactive GUI panel on host system desktop.",
        "type": "gui",
        "category": "power",
        "requires_admin": False
    },
    "open_eventvwr": {
        "name": "Launch Event Viewer",
        "cmd": ["eventvwr"],
        "desc": "Opens legacy Windows Event Log Viewer.",
        "caution": "Launches interactive GUI panel on host system desktop.",
        "type": "gui",
        "category": "repair",
        "requires_admin": False
    }
}

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

@app.get("/api/suggestions")
def get_suggestions() -> Dict[str, Any]:
    """Retrieve system optimization suggestions categorized by risk levels."""
    from syslens.engine.suggester import generate_suggestions
    try:
        metrics = get_metrics()
        sugs = generate_suggestions(metrics)
        return {
            "suggestions": sugs
        }
    except Exception as e:
        logger.error(f"Error gathering suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clean")
def post_clean(mode: str = "safe") -> Dict[str, Any]:
    """Execute cleanup actions depending on mode (safe or full)."""
    from syslens.cleaner.engine import run_cleanup
    try:
        if mode not in ["safe", "full"]:
            raise HTTPException(status_code=400, detail="Invalid mode. Must be 'safe' or 'full'.")
        results = run_cleanup(mode=mode)
        return {"status": "success", "results": results}
    except Exception as e:
        logger.error(f"Error running cleanup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/optimize")
def post_optimize(profile: str = "safe") -> Dict[str, Any]:
    """Execute optimization engine actions for a profile (safe, gaming, dev, battery)."""
    from syslens.optimizer.engine import optimize
    try:
        if profile not in ["safe", "gaming", "dev", "battery"]:
            raise HTTPException(status_code=400, detail="Invalid profile. Must be 'safe', 'gaming', 'dev', or 'battery'.")
        results = optimize(mode=profile)
        return results
    except Exception as e:
        logger.error(f"Error running optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/rollback")
def post_rollback() -> Dict[str, Any]:
    """Rollback the last optimization action."""
    from syslens.optimizer.rollback import rollback_last
    try:
        results = rollback_last()
        return results
    except Exception as e:
        logger.error(f"Error running rollback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/schedule")
def post_schedule(interval: int = 3600) -> Dict[str, Any]:
    """Schedule background cleanups at the specified interval in seconds."""
    from syslens.optimizer.scheduler import schedule_cleanup
    try:
        results = schedule_cleanup(interval=interval)
        return results
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/processes/kill")
def post_kill_process(pid: int) -> Dict[str, Any]:
    """Terminate a process by PID with safety guards."""
    import psutil
    
    # 1. Safety Guards
    if pid <= 4:
        raise HTTPException(
            status_code=400, 
            detail="Termination denied: Critical system process (PID <= 4)."
        )
        
    if pid == os.getpid():
        raise HTTPException(
            status_code=400, 
            detail="Termination denied: Cannot terminate the SysLens process itself."
        )
        
    try:
        proc = psutil.Process(pid)
        name = proc.name().lower()
        
        # Blacklist critical process names
        critical_names = [
            "system", "system idle process", "svchost.exe", "lsass.exe", 
            "services.exe", "wininit.exe", "csrss.exe", "smss.exe",
            "explorer.exe", "winlogon.exe"
        ]
        if name in critical_names:
            raise HTTPException(
                status_code=400,
                detail=f"Termination denied: '{proc.name()}' is a protected system process."
            )
            
        # Terminate the process
        proc.kill()
        return {
            "status": "success",
            "pid": pid,
            "name": name,
            "message": f"Process (PID {pid}) terminated successfully."
        }
    except HTTPException:
        raise
    except psutil.NoSuchProcess:
        raise HTTPException(status_code=404, detail=f"Process with PID {pid} not found.")
    except psutil.AccessDenied:
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied: Insufficient privileges to terminate PID {pid}."
        )
    except Exception as e:
        logger.error(f"Error killing process {pid}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/elevate")
def post_elevate_server() -> Dict[str, Any]:
    """Relaunch the SysLens server process as Administrator."""
    from syslens.utils.admin import is_admin
    import os
    import sys
    import ctypes
    
    if is_admin():
        return {"status": "success", "message": "Already running as Administrator."}
        
    if os.name == "nt":
        try:
            # Resolve binary and args safely
            argv = list(sys.argv)
            if not argv:
                argv = ["syslens", "serve"]
                
            first_arg = argv[0].lower()
            if first_arg.endswith(".exe") or (not first_arg.endswith(".py") and os.path.exists(argv[0])):
                executable = argv[0]
                arguments = " ".join(argv[1:])
            else:
                executable = sys.executable
                arguments = " ".join(argv)
                
            # Launch new elevated process asynchronously (verb runas triggers UAC)
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                executable,
                arguments,
                None,
                1
            )
            
            # Terminate current non-elevated process shortly after response returns
            import threading
            import time
            
            def exit_soon():
                time.sleep(0.5)
                os._exit(0)
                
            threading.Thread(target=exit_soon, daemon=True).start()
            
            return {
                "status": "success",
                "message": "UAC elevation requested. Relaunching server as Administrator..."
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to elevate process: {str(e)}")
    else:
        raise HTTPException(
            status_code=400,
            detail="Self-elevation is only supported on Windows in this version."
        )


@app.get("/api/playbook/commands")
def get_playbook_commands() -> Dict[str, Any]:
    """Retrieve list of playbook commands and their descriptions."""
    from syslens.utils.admin import is_admin
    return {
        "is_admin": is_admin(),
        "commands": [
            {
                "id": k, 
                "name": v["name"], 
                "desc": v["desc"], 
                "caution": v["caution"], 
                "type": v["type"],
                "category": v["category"],
                "cmd_string": " ".join(v["cmd"]),
                "requires_admin": v.get("requires_admin", False)
            }
            for k, v in PLAYBOOK_COMMANDS.items()
        ]
    }


@app.post("/api/playbook/run/{command_id}")
async def post_run_playbook_command(command_id: str):
    """Run a playbook command, streaming output if CLI or returning immediately if GUI."""
    if command_id not in PLAYBOOK_COMMANDS:
        raise HTTPException(status_code=404, detail="Command not found.")
        
    cmd_info = PLAYBOOK_COMMANDS[command_id]
    
    if cmd_info["type"] == "gui":
        try:
            # Spawn GUI tool as background process
            subprocess.Popen(cmd_info["cmd"], shell=True)
            return {
                "status": "success",
                "message": f"Successfully launched {cmd_info['name']} on host desktop."
            }
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to launch GUI tool: {str(e)}"
            )
            
    # For CLI tools, stream output
    async def output_generator():
        from syslens.utils.admin import is_admin
        
        try:
            cmd_str = " ".join(cmd_info["cmd"])
            requires_admin = cmd_info.get("requires_admin", False)
            accumulator = []
            
            if requires_admin and not is_admin():
                # Server is not elevated but command requires administrator privileges.
                # Relaunch using PowerShell Start-Process with -Verb RunAs (on Windows).
                import os
                if os.name == "nt":
                    yield "[SysLens Elevation Manager]\n"
                    yield "⚠️ SysLens is running in standard user mode, but this command requires Administrator privileges.\n"
                    yield "Attempting to launch elevated command via UAC prompt...\n"
                    yield "👉 Please approve the User Account Control (UAC) prompt on the host machine.\n"
                    yield "Note: The output will stream directly in this window after approval.\n\n"
                    
                    import tempfile
                    import uuid
                    temp_dir = tempfile.gettempdir()
                    log_id = uuid.uuid4().hex[:8]
                    output_file = os.path.join(temp_dir, f"syslens_playbook_{command_id}_{log_id}.log")
                    if os.path.exists(output_file):
                        try:
                            os.remove(output_file)
                        except Exception:
                            pass

                    escaped_cmd = cmd_str.replace('"', '\\"')
                    elevation_cmd = f"powershell.exe -NoProfile -Command \"$ErrorActionPreference = 'Stop'; Start-Process cmd.exe -ArgumentList '/V:ON', '/c', '{escaped_cmd} > \\\"{output_file}\\\" 2>&1 & echo __SYSLENS_ELEVATED_DONE__ !errorlevel! >> \\\"{output_file}\\\"' -Verb RunAs -Wait\""
                    
                    proc = await asyncio.create_subprocess_shell(
                        elevation_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.STDOUT
                    )
                    
                    yielded_len = 0
                    done = False
                    exit_code = 0
                    start_time = asyncio.get_event_loop().time()
                    last_activity_time = start_time
                    
                    # Tail log file until the completion marker is written
                    # Timeout after 30 minutes (1800s)
                    while not done and (asyncio.get_event_loop().time() - start_time < 1800):
                        try:
                            # Actively poll and reap the subprocess
                            await asyncio.wait_for(proc.wait(), timeout=0.0001)
                        except asyncio.TimeoutError:
                            pass
                            
                        await asyncio.sleep(0.5)
                        
                        has_new_data = False
                        if os.path.exists(output_file):
                            try:
                                with open(output_file, "r", encoding="utf-8", errors="replace") as f:
                                    content = f.read()
                                if len(content) > yielded_len:
                                    new_content = content[yielded_len:]
                                    if "__SYSLENS_ELEVATED_DONE__" in content:
                                        marker_idx = content.find("__SYSLENS_ELEVATED_DONE__")
                                        clean_new = content[yielded_len:marker_idx]
                                        if clean_new:
                                            accumulator.append(clean_new)
                                            yield clean_new
                                        
                                        marker_line = content[marker_idx:]
                                        parts = marker_line.strip().split()
                                        if len(parts) >= 2:
                                            try:
                                                exit_code = int(parts[1])
                                            except ValueError:
                                                exit_code = 0
                                        yielded_len = len(content)  # Prevent duplication in final check
                                        done = True
                                    else:
                                        accumulator.append(new_content)
                                        yield new_content
                                        yielded_len = len(content)
                                    has_new_data = True
                                    last_activity_time = asyncio.get_event_loop().time()
                            except Exception:
                                pass
                                
                        # Send keep-alive heartbeat if idle for 15 seconds to prevent browser/TCP timeouts
                        if not has_new_data and (asyncio.get_event_loop().time() - last_activity_time > 15.0):
                            yield "\0"
                            last_activity_time = asyncio.get_event_loop().time()
                            
                        # Check process status
                        if proc.returncode is not None:
                            if proc.returncode != 0:
                                # PowerShell process failed (e.g. UAC cancelled/denied)
                                exit_code = proc.returncode
                                break
                            elif not os.path.exists(output_file):
                                # PowerShell process completed but no log file was created (mock/dry run)
                                break
                            elif (asyncio.get_event_loop().time() - start_time) > 5.0:
                                # PowerShell process completed after running for more than 5 seconds.
                                # It must have waited for the elevated command to finish.
                                break
                                
                    await proc.wait()
                    # Final check for any remaining lines if we broke out of loop early
                    if os.path.exists(output_file):
                        try:
                            with open(output_file, "r", encoding="utf-8", errors="replace") as f:
                                content = f.read()
                            if len(content) > yielded_len:
                                new_content = content[yielded_len:]
                                if "__SYSLENS_ELEVATED_DONE__" in new_content:
                                    marker_idx = new_content.find("__SYSLENS_ELEVATED_DONE__")
                                    clean_new = new_content[:marker_idx]
                                    if clean_new:
                                        accumulator.append(clean_new)
                                        yield clean_new
                                else:
                                    accumulator.append(new_content)
                                    yield new_content
                        except Exception:
                            pass
                            
                    # Clean up temp file
                    try:
                        if os.path.exists(output_file):
                            os.remove(output_file)
                    except Exception:
                        pass

                    full_output = "".join(accumulator)
                    
                    from syslens.dashboard.playbook_guide import get_playbook_suggestion
                    suggestion = get_playbook_suggestion(command_id, full_output, exit_code)
                    
                    yield f"\n\n==================================================\n"
                    yield f"[SysLens Intelligent Guidance]\n"
                    yield f"{suggestion}\n"
                    yield f"==================================================\n"
                else:
                    yield f"\n[Error: This command requires root privileges. Please restart SysLens as root.]\n"
            else:
                proc = await asyncio.create_subprocess_shell(
                    cmd_str,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT
                )
                
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    try:
                        chunk = line.decode("utf-8")
                    except UnicodeDecodeError:
                        chunk = line.decode("cp1252", errors="replace")
                    accumulator.append(chunk)
                    yield chunk
                        
                await proc.wait()
                yield f"\n[Process completed with exit code {proc.returncode}]\n"
                
                full_output = "".join(accumulator)
                from syslens.dashboard.playbook_guide import get_playbook_suggestion
                suggestion = get_playbook_suggestion(command_id, full_output, proc.returncode)
                
                yield f"\n\n==================================================\n"
                yield f"[SysLens Intelligent Guidance]\n"
                yield f"{suggestion}\n"
                yield f"==================================================\n"
        except Exception as err:
            yield f"\n[Execution error: {str(err)}]\n"
            
    from fastapi.responses import StreamingResponse
    return StreamingResponse(output_generator(), media_type="text/plain")


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


@app.get("/SysLens.png")
@app.get("/syslens.png")
def read_logo():
    logo_path = os.path.join(WEB_DIR, "SysLens.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path, media_type="image/png")
    root_logo = os.path.join(ROOT_DIR, "SysLens.png")
    if os.path.exists(root_logo):
        return FileResponse(root_logo, media_type="image/png")
    raise HTTPException(status_code=404, detail="SysLens.png logo not found")

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
