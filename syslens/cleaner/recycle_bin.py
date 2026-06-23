import os
import ctypes

def empty_recycle_bin(dry_run=False):
    """
    Empties the system recycle bin. Uses native Windows API SHEmptyRecycleBinW on Windows.
    Uses silent flags (7 = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND).
    If dry_run is True, queries items and size instead of emptying.
    """
    if os.name != 'nt':
        return {
            "task": "RECYCLE_BIN",
            "status": "skipped" if not dry_run else "dry_run",
            "note": "Recycle Bin emptying is only supported on Windows"
        }

    if dry_run:
        try:
            class SHQUERYRBINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("i64Size", ctypes.c_int64),
                    ("i64NumItems", ctypes.c_int64)
                ]
            rb_info = SHQUERYRBINFO()
            rb_info.cbSize = ctypes.sizeof(SHQUERYRBINFO)
            res = ctypes.windll.shell32.SHQueryRecycleBinW(None, ctypes.byref(rb_info))
            if res == 0:
                size = rb_info.i64Size
                items = rb_info.i64NumItems
                from syslens.utils.format import format_bytes
                note = f"Would empty Recycle Bin ({items} items, {format_bytes(size)})"
            else:
                note = "Would empty Recycle Bin"
        except Exception:
            note = "Would empty Recycle Bin"
        return {
            "task": "RECYCLE_BIN",
            "status": "dry_run",
            "note": note
        }

    try:
        # SHERB_NOCONFIRMATION = 0x00000001
        # SHERB_NOPROGRESSUI   = 0x00000002
        # SHERB_NOSOUND        = 0x00000004
        # Total: 7 (silent run)
        res = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        if res == 0:
            return {
                "task": "RECYCLE_BIN",
                "status": "completed",
                "note": "Recycle Bin emptied successfully"
            }
        else:
            return {
                "task": "RECYCLE_BIN",
                "status": "completed",
                "note": f"Recycle Bin operation returned code {res}"
            }

    except Exception as e:
        return {
            "task": "RECYCLE_BIN",
            "status": "failed",
            "error": str(e)
        }
