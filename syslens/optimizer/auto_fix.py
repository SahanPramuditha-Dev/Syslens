import psutil
import os
import ctypes
from ctypes import wintypes

# Win32 privilege constants
TOKEN_ADJUST_PRIVILEGES = 0x0020
TOKEN_QUERY = 0x0008
SE_PRIVILEGE_ENABLED = 0x00000002

class LUID(ctypes.Structure):
    _fields_ = [
        ("LowPart", wintypes.DWORD),
        ("HighPart", wintypes.LONG)
    ]

class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Luid", LUID),
        ("Attributes", wintypes.DWORD)
    ]

class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [
        ("PrivilegeCount", wintypes.DWORD),
        ("Privileges", LUID_AND_ATTRIBUTES * 1)
    ]

def enable_privilege(privilege_name: str) -> bool:
    """Helper function to enable a Windows process token privilege."""
    if os.name != 'nt':
        return False
    try:
        hToken = wintypes.HANDLE()
        if not ctypes.windll.advapi32.OpenProcessToken(
            ctypes.windll.kernel32.GetCurrentProcess(),
            TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY,
            ctypes.byref(hToken)
        ):
            return False

        luid = LUID()
        if not ctypes.windll.advapi32.LookupPrivilegeValueW(
            None,
            privilege_name,
            ctypes.byref(luid)
        ):
            ctypes.windll.kernel32.CloseHandle(hToken)
            return False

        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED

        if not ctypes.windll.advapi32.AdjustTokenPrivileges(
            hToken,
            False,
            ctypes.byref(tp),
            0,
            None,
            None
        ):
            ctypes.windll.kernel32.CloseHandle(hToken)
            return False

        err = ctypes.windll.kernel32.GetLastError()
        ctypes.windll.kernel32.CloseHandle(hToken)
        return err == 0
    except Exception:
        return False

def apply_safe_fixes(cpu_override=None, mem_override=None, dry_run=False):
    """
    Analyzes current system resources and applies safe auto-fixes:
    - If CPU > 85%, reduces background process priority.
    - If Memory > 80%, flushes standby page lists (Windows native NtSetSystemInformation).
    Accepts overrides and dry_run flag.
    """
    fixes = []

    cpu = cpu_override if cpu_override is not None else psutil.cpu_percent(interval=0.1)
    mem = mem_override if mem_override is not None else psutil.virtual_memory().percent

    current_pid = os.getpid()

    if cpu > 85:
        # Find background CPU hogs to reduce priority
        hogs = []
        try:
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    # Ignore system processes and current syslens process
                    if p.info['pid'] in (0, 4, current_pid):
                        continue
                    name = (p.info['name'] or "").lower()
                    if any(sys_name in name for sys_name in ["system", "idle", "svchost", "explorer", "registry"]):
                        continue
                    
                    cpu_p = p.info['cpu_percent'] or 0.0
                    if cpu_p > 15.0:
                        hogs.append(p)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass

        # Apply priority reduction to up to 3 hogs
        applied_hogs = []
        for hog in hogs[:3]:
            try:
                # Save previous priority for rollback
                if os.name == 'nt':
                    prev_priority = hog.nice()
                    if not dry_run:
                        # BELOW_NORMAL_PRIORITY_CLASS = 0x4000
                        hog.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                    applied_hogs.append({
                        "pid": hog.pid,
                        "name": hog.name(),
                        "prev_priority": prev_priority,
                        "new_priority": psutil.BELOW_NORMAL_PRIORITY_CLASS
                    })
                else:
                    prev_nice = hog.nice()
                    if not dry_run:
                        hog.nice(10) # lower priority on Unix
                    applied_hogs.append({
                        "pid": hog.pid,
                        "name": hog.name(),
                        "prev_priority": prev_nice,
                        "new_priority": 10
                    })
            except Exception:
                pass

        fixes.append({
            "fix": "Reduce background process priority",
            "type": "CPU_OPTIMIZATION",
            "status": "dry_run" if dry_run else "recommended_applied",
            "details": applied_hogs
        })

    if mem > 80:
        status_text = "simulation_skipped"
        details_text = "Standby list flush simulation"
        
        if os.name == 'nt':
            if dry_run:
                status_text = "dry_run"
                details_text = "Would flush Windows standby page list via NtSetSystemInformation (requires admin)"
            else:
                try:
                    # Attempt to enable the required privilege
                    enable_privilege("SeProfileSingleProcessPrivilege")
                    
                    SystemMemoryListInformation = 80
                    MemoryPurgeStandbyList = 4
                    
                    command = ctypes.c_int(MemoryPurgeStandbyList)
                    res = ctypes.windll.ntdll.NtSetSystemInformation(
                        SystemMemoryListInformation,
                        ctypes.byref(command),
                        ctypes.sizeof(command)
                    )
                    
                    if res == 0:
                        status_text = "recommended_applied"
                        details_text = "Flushed OS standby page list via NtSetSystemInformation"
                    elif res == 0xC0000022:  # STATUS_ACCESS_DENIED
                        status_text = "failed_privilege"
                        details_text = "Failed to flush standby list: Access Denied. Administrator privileges required."
                    else:
                        status_text = "failed_code"
                        details_text = f"Failed to flush standby list: NTSTATUS code {hex(res & 0xffffffff)}"
                except Exception as e:
                    status_text = "error"
                    details_text = f"Flushing standby list raised error: {e}"
        else:
            status_text = "skipped_non_windows"
            details_text = "Standby list flushing is only supported on Windows"

        fixes.append({
            "fix": "Clear memory cache (safe flush)",
            "type": "MEMORY_OPTIMIZATION",
            "status": status_text,
            "details": details_text
        })

    return fixes
