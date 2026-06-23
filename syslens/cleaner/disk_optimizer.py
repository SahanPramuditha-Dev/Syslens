import psutil

def analyze_disk():
    """
    Perform a non-destructive analysis of disk space.
    Provides optimization recommendations based on disk utilization levels.
    """
    try:
        usage = psutil.disk_usage('/')
        total_gb = usage.total // (1024**3)
        used_percent = usage.percent
    except Exception:
        # Fallback values
        total_gb = 512
        used_percent = 50.0

    recommendation = "Consider uninstalling unused apps" if used_percent > 85 else "Run cleanup if usage > 85%"

    return {
        "task": "DISK_ANALYSIS",
        "total_gb": total_gb,
        "used_percent": used_percent,
        "recommendation": recommendation
    }
