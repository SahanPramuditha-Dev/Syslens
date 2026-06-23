import os
import shutil
from pathlib import Path
from syslens.cleaner.safety import safety_check

def clean_browser_cache(dry_run=False):
    """
    Cleans Google Chrome and Microsoft Edge cache folders if they exist.
    Only executes if the paths pass the safety checks.
    Supports dry_run to only audit sizes without unlinking.
    """
    # Locate LOCALAPPDATA or use home dir AppData/Local as fallback
    local_appdata = os.environ.get("LOCALAPPDATA")
    if local_appdata:
        base_path = Path(local_appdata)
    else:
        base_path = Path.home() / "AppData" / "Local"

    paths = [
        base_path / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
        base_path / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache"
    ]

    removed = 0
    bytes_freed = 0

    for path in paths:
        if path.exists():
            if not safety_check(str(path)):
                continue

            # Calculate size
            folder_size = 0
            try:
                for root, dirs, files in os.walk(path):
                    for f in files:
                        try:
                            folder_size += os.path.getsize(os.path.join(root, f))
                        except Exception:
                            pass
            except Exception:
                pass

            if dry_run:
                removed += 1
                bytes_freed += folder_size
                continue

            try:
                # If directory, clear it or delete it.
                # shutil.rmtree will try to delete the entire directory.
                shutil.rmtree(path)
                removed += 1
                bytes_freed += folder_size
            except Exception:
                # Try to clean files inside it if folder rmtree fails due to locked files
                try:
                    for item in path.iterdir():
                        try:
                            item_size = 0
                            if item.is_file():
                                try:
                                    item_size = item.stat().st_size
                                    item.unlink()
                                except Exception:
                                    pass
                            elif item.is_dir():
                                try:
                                    for subroot, subdirs, subfiles in os.walk(item):
                                        for subf in subfiles:
                                            try:
                                                item_size += os.path.getsize(os.path.join(subroot, subf))
                                            except Exception:
                                                pass
                                    shutil.rmtree(item)
                                except Exception:
                                    pass
                            bytes_freed += item_size
                        except Exception:
                            pass
                    removed += 1
                except Exception:
                    pass

    return {
        "task": "BROWSER_CACHE",
        "status": "dry_run" if dry_run else "completed",
        "folders_cleaned": removed,
        "bytes_freed": bytes_freed
    }
