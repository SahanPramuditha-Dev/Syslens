"""
``syslens health`` — System health report with diagnostics and recommendations.
"""
from syslens.commands._shared import (
    BULLET,
    console,
    gather_metrics,
    get_progress_bar,
    get_severity_color,
    supports_unicode,
)


def run(anomaly_interface, plugin_manager, health_engine) -> None:
    """Run system diagnostics and display a human-readable health report."""
    metrics = gather_metrics(anomaly_interface, plugin_manager, health_engine)
    score  = metrics["health"]["score"]
    status = metrics["health"]["status"]

    unicode_active = supports_unicode()
    border_char = "━" if unicode_active else "="
    border_line = border_char * 30

    brain_icon = "🧠 " if unicode_active else ""
    gear_icon  = "⚙ "  if unicode_active else ""
    warn_icon  = "⚠ "  if unicode_active else ""
    tip_icon   = "💡 " if unicode_active else ""
    bullet     = "•"   if unicode_active else "*"
    arrow      = "→"   if unicode_active else "->"

    def get_status_circle(val_status: str) -> str:
        if not unicode_active:
            return f"[{val_status}]"
        return {"HEALTHY": "🟢", "DEGRADED": "🟡"}.get(val_status, "🔴")

    def get_metric_level(percent: float) -> tuple:
        if percent >= 80.0:
            return ("🔴", "High")   if unicode_active else ("", "High")
        elif percent >= 60.0:
            return ("🟡", "Moderate") if unicode_active else ("", "Moderate")
        return ("🟢", "Normal") if unicode_active else ("", "Normal")

    cpu_usage  = metrics.get("cpu",    {}).get("usage_percent",  0.0)
    mem_usage  = metrics.get("memory", {}).get("usage_percent",  0.0)
    partitions = metrics.get("disk",   {}).get("partitions",     [])
    disk_usage = max((p.get("usage_percent", 0.0) for p in partitions), default=0.0)

    cpu_circle,  cpu_level  = get_metric_level(cpu_usage)
    mem_circle,  mem_level  = get_metric_level(mem_usage)
    disk_circle, disk_level = get_metric_level(disk_usage)

    console.print(border_line)
    console.print(f"{brain_icon}SYSLENS SYSTEM HEALTH REPORT")
    console.print(border_line)
    console.print()

    console.print(f"{get_status_circle(status)} OVERALL STATUS: {score:.0f} / 100 ({status})")
    console.print()

    console.print(f"{gear_icon}SYSTEM METRICS")
    console.print(f"CPU Usage      : {cpu_usage:.0f}%  {cpu_circle} {cpu_level}".strip())
    console.print(f"Memory Usage   : {mem_usage:.0f}%  {mem_circle} {mem_level}".strip())
    console.print(f"Disk Usage     : {disk_usage:.0f}%  {disk_circle} {disk_level}".strip())
    console.print()

    console.print(f"{warn_icon}ANOMALIES DETECTED")
    anomalies = metrics.get("anomalies", [])
    if anomalies:
        for anom in anomalies:
            metric_name = anom.get("metric", "UNKNOWN").upper()
            curr_val   = anom.get("current_value")
            base_mean  = anom.get("baseline_mean")
            if isinstance(curr_val, (int, float)) and isinstance(base_mean, (int, float)) and base_mean > 0:
                dev_pct   = ((curr_val - base_mean) / base_mean) * 100
                deviation = f"{dev_pct:.0f}% deviation from baseline"
            elif isinstance(curr_val, dict):
                deviation = "multiple metric deviation"
            else:
                deviation = f"deviation index z: {anom.get('deviation_z')}"

            likely_cause = "background process overload"
            if "mem" in metric_name.lower():
                likely_cause = "heavy process memory consumption"
            elif "disk" in metric_name.lower():
                likely_cause = "heavy active disk I/O operations"
            elif "correlated" in metric_name.lower():
                likely_cause = "correlated hardware bottlenecks"

            console.print(f"{bullet} {metric_name}")
            console.print(f"  {arrow} {deviation}")
            console.print(f"  {arrow} Likely cause: {likely_cause}")
    else:
        console.print(f"{bullet} None detected")
    console.print()

    console.print(f"{tip_icon}RECOMMENDATIONS")
    diagnoses = health_engine.diagnose_issues(metrics)
    recs: list = []
    for diag in diagnoses:
        recs.extend(diag.get("recommendations", []))
    unique_recs = list(dict.fromkeys(recs))   # deduplicate while preserving order
    if unique_recs:
        for rec in unique_recs:
            console.print(f"  {bullet} {rec}")
    else:
        console.print(f"  {bullet} System operating within expected parameters.")
    console.print()
