import os
import shutil
import time
from pathlib import Path
from syslens.cleaner.safety import safety_check

def clean_dev_caches(dry_run=False, age_days=7):
    """
    Scans the current directory recursively for stale development caches:
    - node_modules
    - .pytest_cache
    - __pycache__
    Deletes them if they are unmodified for over age_days.
    Filters out critical folders like .git.
    """
    cwd = os.getcwd()
    freed_bytes = 0
    folders_removed = 0
    details = []

    target_names = {"node_modules", ".pytest_cache", "__pycache__"}
    now = time.time()
    max_age_sec = age_days * 86400

    # Walk the directory structure
    for root, dirs, files in os.walk(cwd, topdown=True):
        # Exclude .git directories immediately
        if ".git" in dirs:
            dirs.remove(".git")

        i = len(dirs) - 1
        while i >= 0:
            d = dirs[i]
            if d in target_names:
                dir_path = Path(root) / d
                
                # Double-check path safety
                if not safety_check(str(dir_path)):
                    i -= 1
                    continue
                
                try:
                    # Determine latest modified time across all contents
                    mtime = dir_path.stat().st_mtime
                    for item in dir_path.glob("**/*"):
                        try:
                            mtime = max(mtime, item.stat().st_mtime)
                        except Exception:
                            pass
                    
                    age = now - mtime
                    if age > max_age_sec:
                        # Calculate folder size
                        size = 0
                        for item in dir_path.glob("**/*"):
                            if item.is_file():
                                try:
                                    size += item.stat().st_size
                                except Exception:
                                    pass
                        
                        freed_bytes += size
                        folders_removed += 1
                        details.append({
                            "path": str(dir_path),
                            "size": size,
                            "type": d
                        })
                        
                        if not dry_run:
                            shutil.rmtree(dir_path)
                            
                        # Prune directory from future walk
                        dirs.pop(i)
                except Exception:
                    pass
            i -= 1

    return {
        "task": "DEV_CACHE_CLEAN",
        "status": "dry_run" if dry_run else "completed",
        "folders_cleaned": folders_removed,
        "bytes_freed": freed_bytes,
        "details": details
    }
