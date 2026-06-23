import json
import os
import psutil
from syslens.optimizer.profiles import set_active_power_scheme

# App data directory for syslens history
HISTORY_FILE = r"C:\Users\sahan\.gemini\antigravity\syslens_history.json"

def _load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []

def _save_history(history):
    try:
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass

def log_action(action):
    """Logs an action to the persistent JSON history file."""
    history = _load_history()
    history.append(action)
    _save_history(history)

def rollback_last():
    """
    Rolls back the last applied optimization:
    - Restores previous power scheme.
    - Restores background process priorities.
    """
    history = _load_history()
    if not history:
        return {"status": "no_actions_to_rollback"}

    last = history.pop()
    _save_history(history)

    reverted = []

    # 1. Revert power scheme
    prev_power = last.get("previous_power_scheme")
    if prev_power:
        success = set_active_power_scheme(prev_power)
        if success:
            reverted.append(f"Power scheme restored to GUID: {prev_power}")

    # 2. Revert process priorities
    results = last.get("results", [])
    for step in results:
        # Step could be a list of auto-fixes or cleanup details
        if isinstance(step, list):
            for item in step:
                if isinstance(item, dict) and item.get("type") == "CPU_OPTIMIZATION":
                    details = item.get("details", [])
                    if isinstance(details, list):
                        for proc in details:
                            pid = proc.get("pid")
                            prev_priority = proc.get("prev_priority")
                            if pid and prev_priority is not None:
                                try:
                                    p = psutil.Process(pid)
                                    p.nice(prev_priority)
                                    reverted.append(f"Restored process priority for {p.name()} (PID {pid}) to {prev_priority}")
                                except Exception:
                                    pass

    return {
        "status": "rollback_executed",
        "reverted_action": last,
        "details": reverted
    }
