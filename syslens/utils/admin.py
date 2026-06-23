import ctypes
import os

def is_admin() -> bool:
    """Check if the current process has administrative/root privileges."""
    try:
        if os.name == "nt":
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.getuid() == 0
    except Exception:
        return False
