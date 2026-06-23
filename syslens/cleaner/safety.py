import os
from pathlib import Path

def safety_check(action: str) -> bool:
    """
    Check if a cleanup action or target path is safe to modify/delete.
    Returns False if the action resolves to critical system paths, registry, drivers, or root directories.
    """
    # 1. Simple substring safety check
    risky_substrings = ["registry"]
    for sub in risky_substrings:
        if sub in action.lower():
            return False

    # 2. Check path safety using resolved paths (prevents directory traversal exploits)
    try:
        path = Path(action).resolve()
        parts = [p.lower() for p in path.parts]
        
        # Block critical folders anywhere in path
        critical_dirs = {"system32", "drivers", "syswow64", "winsxs", "systemvolumeinformation"}
        for d in critical_dirs:
            if d in parts:
                return False

        # Windows root path protection
        if os.name == 'nt':
            win_dir = Path(os.environ.get("SystemRoot", "C:\\Windows")).resolve()
            if path == win_dir or path in win_dir.parents:
                return False
            
            # Allow Temp directory specifically, but block other subfolders inside C:\Windows
            win_temp = win_dir / "Temp"
            if win_dir in path.parents and win_temp not in path.parents and path != win_temp:
                return False

        # Root folder safety check (prevent deleting root drives like C:\ or /)
        if path == path.parent:
            return False

    except Exception:
        # Fallback to standard substring checks if resolution errors out
        fallback_risks = ["system32", "drivers", "syswow64"]
        for r in fallback_risks:
            if r in action.lower():
                return False

    return True
