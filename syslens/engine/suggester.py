import os
import math
import random
import time
import tempfile
import ctypes
from typing import List, Dict, Any
import psutil

from syslens.utils.format import format_bytes

def get_temp_files_size() -> int:
    """Calculate total size of files in the OS temp directory."""
    total_size = 0
    temp_dir = tempfile.gettempdir()
    try:
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                fp = os.path.join(root, f)
                if not os.path.islink(fp):
                    try:
                        total_size += os.path.getsize(fp)
                    except Exception:
                        pass
    except Exception:
        pass
    return total_size

def generate_suggestions(metrics: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Evaluate current system metrics to generate suggestions categorized by risk level."""
    suggestions = []

    # 1. STORAGE CHECK
    disk_pct = 0.0
    if metrics:
        disk_partitions = metrics.get("disk", {}).get("partitions", [])
        if disk_partitions:
            disk_pct = max(p.get("usage_percent", 0.0) for p in disk_partitions)
        else:
            disk_pct = metrics.get("disk_usage", 0.0)

    if disk_pct == 0.0:
        try:
            disk = psutil.disk_usage('/')
            disk_pct = disk.percent
        except Exception:
            disk_pct = 0.0

    if disk_pct > 80.0:
        suggestions.append({
            "category": "STORAGE",
            "issue": f"Low disk space ({disk_pct:.1f}% used)",
            "actions": [
                {"name": "Empty Recycle Bin", "risk": "SAFE"},
                {"name": "Delete temporary files", "risk": "SAFE"},
                {"name": "Uninstall unused applications", "risk": "MEDIUM"},
                {"name": "Move large files to external/cloud storage", "risk": "SAFE"}
            ]
        })

    # 2. CPU CHECK
    if metrics:
        cpu = metrics.get("cpu", {}).get("usage_percent", 0.0)
    else:
        cpu = psutil.cpu_percent(interval=0.1)

    if cpu > 75.0:
        suggestions.append({
            "category": "CPU",
            "issue": f"High CPU utilization ({cpu:.1f}%)",
            "actions": [
                {"name": "Close background applications", "risk": "SAFE"},
                {"name": "Check for runaway processes (Hogs)", "risk": "SAFE"},
                {"name": "Disable startup applications", "risk": "MEDIUM"}
            ]
        })

    # 3. MEMORY CHECK
    mem = 0.0
    if metrics:
        mem = metrics.get("memory", {}).get("usage_percent", 0.0)
        if mem == 0.0:
            mem = metrics.get("memory_usage", 0.0)

    if mem == 0.0:
        try:
            mem = psutil.virtual_memory().percent
        except Exception:
            mem = 0.0

    if mem > 80.0:
        suggestions.append({
            "category": "MEMORY",
            "issue": f"High memory usage ({mem:.1f}%)",
            "actions": [
                {"name": "Restart heavy applications (Browser, IDE)", "risk": "SAFE"},
                {"name": "Close unused browser tabs", "risk": "SAFE"},
                {"name": "Clear system page cache", "risk": "MEDIUM"}
            ]
        })

    # 4. NETWORK CHECK
    conns = 0
    if metrics:
        conns = metrics.get("plugins_data", {}).get("network_telemetry", {}).get("active_connections", 0)
    else:
        try:
            conns = len(psutil.net_connections(kind='inet'))
        except Exception:
            conns = 0

    if conns > 350:
        suggestions.append({
            "category": "NETWORK",
            "issue": f"High network socket count ({conns} active)",
            "actions": [
                {"name": "Check background downloads/updates", "risk": "SAFE"},
                {"name": "Switch DNS to Cloudflare (1.1.1.1) / Google (8.8.8.8)", "risk": "MEDIUM"},
                {"name": "Inspect for running peer-to-peer applications", "risk": "SAFE"}
            ]
        })

    # 5. BATTERY CHECK
    try:
        battery = psutil.sensors_battery()
    except Exception:
        battery = None

    if battery and not battery.power_plugged and battery.percent < 30.0:
        suggestions.append({
            "category": "BATTERY",
            "issue": f"Battery level is low ({battery.percent}%) & discharging",
            "actions": [
                {"name": "Enable OS Power Saver mode", "risk": "SAFE"},
                {"name": "Reduce screen brightness", "risk": "SAFE"},
                {"name": "Close high CPU background processes", "risk": "SAFE"}
            ]
        })

    # 6. SYSTEM CLEANUP CHECK
    temp_size = get_temp_files_size()
    if temp_size > 50 * 1024 * 1024:  # > 50 MB
        suggestions.append({
            "category": "CLEANUP",
            "issue": f"Accumulated temp files found ({format_bytes(temp_size)})",
            "actions": [
                {"name": "Run Safe Autocleaner", "risk": "SAFE"},
                {"name": "Clear browser cache files", "risk": "SAFE"},
                {"name": "Empty System Recycle Bin", "risk": "SAFE"},
                {"name": "Clean Windows Driver Registry leftovers", "risk": "HIGH RISK"}
            ]
        })

    return suggestions

def execute_safe_cleanups() -> Dict[str, Any]:
    """Execute SAFE category cleanups automatically and return report of bytes freed."""
    bytes_freed = 0
    files_deleted = 0
    recycle_bin_status = "SKIPPED_ON_NON_WINDOWS"

    # 1. Clean Temp Files
    temp_dir = tempfile.gettempdir()
    try:
        for root, dirs, files in os.walk(temp_dir):
            for f in files:
                fp = os.path.join(root, f)
                try:
                    size = os.path.getsize(fp)
                    os.remove(fp)
                    bytes_freed += size
                    files_deleted += 1
                except Exception:
                    pass
    except Exception:
        pass

    # 2. Empty Windows Recycle Bin
    if os.name == 'nt':
        try:
            # SHEmptyRecycleBinW flags: NOCONFIRMATION=1, NOPROGRESSUI=2, NOSOUND=4 (Sum: 7)
            res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
            recycle_bin_status = "SUCCESS" if res == 0 else "SKIPPED_OR_EMPTY"
        except Exception as e:
            recycle_bin_status = f"ERROR: {e}"

    # 3. Clean Browser Cache default directories (Google Chrome / Microsoft Edge)
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        paths = [
            os.path.join(local_app_data, "Google", "Chrome", "User Data", "Default", "Cache"),
            os.path.join(local_app_data, "Microsoft", "Edge", "User Data", "Default", "Cache")
        ]
        for p in paths:
            if os.path.exists(p):
                try:
                    for root, dirs, files in os.walk(p):
                        for f in files:
                            fp = os.path.join(root, f)
                            try:
                                size = os.path.getsize(fp)
                                os.remove(fp)
                                bytes_freed += size
                                files_deleted += 1
                            except Exception:
                                pass
                except Exception:
                    pass

    return {
        "success": True,
        "bytes_freed": bytes_freed,
        "formatted_freed": format_bytes(bytes_freed),
        "files_deleted": files_deleted,
        "recycle_bin": recycle_bin_status
    }
