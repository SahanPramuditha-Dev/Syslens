"""
Shared console instance, Unicode-safe symbols, and helpers used by all CLI commands.
Import from here rather than repeating the setup in every module.
"""
from rich.console import Console
from rich.text import Text

from syslens.utils.format import (
    format_bytes,
    format_time_duration,
    get_progress_bar,
    get_severity_color,
    get_sparkline,
    supports_unicode,
)

# Singleton console used by every command module
console = Console()

# ---------------------------------------------------------------------------
# Unicode / ASCII cross-platform safe symbols
# ---------------------------------------------------------------------------
_U = supports_unicode()

EM_DASH      = "—"  if _U else "-"
CHECK_MARK   = "✓"  if _U else "[OK]"
BULLET       = "•"  if _U else "*"
CHECK_ICON   = "✔"  if _U else "[OK]"
LINE_CHAR    = "━"  if _U else "-"

# Prefixed icons (include trailing space so callers don't need to)
CLEAN_ICON     = "🧹 " if _U else ""
OK_ICON        = "🟢 " if _U else "[OK] "
WARN_ICON      = "🟡 " if _U else "[WARN] "
ERROR_ICON     = "🔴 " if _U else "[ERROR] "
DISK_ICON      = "💾 " if _U else ""
LIGHTNING_ICON = "⚡ " if _U else ""
GEAR_ICON      = "⚙ "  if _U else ""
DIAL_ICON      = "🎛 " if _U else ""
CLOCK_ICON     = "⏱ " if _U else ""
ARROW_ICON     = "↩ " if _U else ""


def compute_health_status(score: float) -> str:
    """Map a numeric score to its text status label."""
    if score >= 80.0:
        return "HEALTHY"
    elif score >= 50.0:
        return "DEGRADED"
    return "CRITICAL"


def gather_metrics(anomaly_interface, plugin_manager, health_engine):
    """
    Collect a full system snapshot, run plugins, and compute the health score.

    Returns the enriched metrics dict (with 'health' key populated).
    """
    metrics = anomaly_interface.scan_system()
    plugin_data = plugin_manager.execute_all(metrics)
    metrics["plugins_data"] = plugin_data

    score, _ = health_engine.calculate_score(metrics)
    score = plugin_manager.modify_health_score(score, metrics)
    status = compute_health_status(score)
    metrics["health"] = {"score": score, "status": status}
    return metrics


__all__ = [
    "console",
    "format_bytes",
    "format_time_duration",
    "get_progress_bar",
    "get_severity_color",
    "get_sparkline",
    "supports_unicode",
    "EM_DASH", "CHECK_MARK", "BULLET", "CHECK_ICON", "LINE_CHAR",
    "CLEAN_ICON", "OK_ICON", "WARN_ICON", "ERROR_ICON", "DISK_ICON",
    "LIGHTNING_ICON", "GEAR_ICON", "DIAL_ICON", "CLOCK_ICON", "ARROW_ICON",
    "compute_health_status",
    "gather_metrics",
]
