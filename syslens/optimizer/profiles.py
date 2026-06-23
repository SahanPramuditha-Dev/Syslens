import os
import subprocess
import re

def get_profile(mode):
    """
    Returns profile parameters based on selected optimization profile.
    Profiles: gaming, dev, battery, safe
    """
    profiles = {
        "gaming": {
            "cpu_boost": True,
            "background_apps_limit": True,
            "power_mode": "high_performance"
        },
        "dev": {
            "cpu_boost": False,
            "background_apps_limit": False,
            "logging_mode": "verbose"
        },
        "battery": {
            "cpu_boost": False,
            "power_mode": "power_saver",
            "screen_optimization": True
        },
        "safe": {
            "cpu_boost": False,
            "safe_mode": True
        }
    }

    return profiles.get(mode, profiles["safe"])

def get_active_power_scheme():
    """Queries Windows powercfg to retrieve the active power scheme GUID."""
    if os.name != 'nt':
        return None
    try:
        res = subprocess.run(["powercfg", "/getactivescheme"], capture_output=True, text=True, check=True)
        match = re.search(r"GUID:\s+([a-fA-F0-9\-]+)", res.stdout)
        if match:
            return match.group(1)
    except Exception:
        pass
    return None

def set_active_power_scheme(scheme):
    """Sets active power scheme on Windows (SCHEME_MIN, SCHEME_MAX, SCHEME_BALANCED, or GUID)."""
    if os.name != 'nt':
        return False
    try:
        subprocess.run(["powercfg", "/setactive", scheme], check=True, capture_output=True)
        return True
    except Exception:
        return False
