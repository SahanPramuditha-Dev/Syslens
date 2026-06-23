import os
import tempfile
from syslens.cleaner.safety import safety_check

def clean_temp_files(dry_run=False):
    """
    Cleans all temporary files in the OS temp directory,
    skipping locked files or files that fail safety checks.
    Supports dry_run to only count files instead of deleting them.
    """
    temp_dir = tempfile.gettempdir()
    deleted = 0

    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            path = os.path.join(root, file)
            if not safety_check(path):
                continue
            try:
                if not dry_run:
                    os.remove(path)
                deleted += 1
            except Exception:
                pass

    return {
        "task": "TEMP_CLEAN",
        "status": "dry_run" if dry_run else "completed",
        "files_removed": deleted
    }
