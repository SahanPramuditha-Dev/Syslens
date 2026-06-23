"""
``syslens scan`` — Enterprise telemetry snapshot with dual-column Rich layout.
"""
import json

from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from syslens.commands._shared import (
    BULLET,
    EM_DASH,
    console,
    format_bytes,
    format_time_duration,
    gather_metrics,
    get_progress_bar,
    get_severity_color,
    get_sparkline,
    supports_unicode,
)


def run(anomaly_interface, plugin_manager, health_engine, output_json: bool = False) -> None:
    """Execute a full system scan and print formatted results (or raw JSON)."""
    metrics = gather_metrics(anomaly_interface, plugin_manager, health_engine)
    plugin_data = metrics.get("plugins_data", {})
    score = metrics["health"]["score"]
    status = metrics["health"]["status"]

    if output_json:
        console.print(json.dumps(metrics, indent=2))
        return

    unicode_active = supports_unicode()

    # Panel icons
    env_icon    = "🖥️  " if unicode_active else ""
    stats_icon  = "⚙️  " if unicode_active else ""
    plug_icon   = "🔌  " if unicode_active else ""
    health_icon = "🧠  " if unicode_active else ""
    proc_icon   = "🔥  " if unicode_active else ""
    anom_icon   = "⚠  "  if unicode_active else ""

    # Outer two-column grid
    grid = Table.grid(expand=True, padding=2)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)

    # ── LEFT COLUMN ──────────────────────────────────────────────────────────
    left_table = Table.grid(expand=True, padding=1)

    # 1. Environment Metadata
    os_data = metrics.get("os", {})
    os_text = Text()
    os_text.append(f"  {BULLET} OS Platform : ", style="bold")
    os_text.append(f"{os_data.get('os_name')} {os_data.get('os_release')} ({os_data.get('architecture')})\n")
    os_text.append(f"  {BULLET} Hostname    : ", style="bold")
    os_text.append(f"{os_data.get('hostname')}\n")
    os_text.append(f"  {BULLET} Local IP    : ", style="bold")
    os_text.append(f"{os_data.get('local_ip')}\n")
    os_text.append(f"  {BULLET} Uptime      : ", style="bold")
    os_text.append(f"{format_time_duration(os_data.get('uptime_seconds', 0))}\n")
    left_table.add_row(Panel(os_text, title=f"{env_icon}ENVIRONMENT METADATA", border_style="grey50"))

    # 2. Telemetry Statistics
    cpu  = metrics.get("cpu",    {})
    mem  = metrics.get("memory", {})
    disk = metrics.get("disk",   {})

    res_table = Table(show_header=True, header_style="bold magenta", box=None, expand=True)
    res_table.add_column("Resource")
    res_table.add_column("Utilization Meter")
    res_table.add_column("Details")

    cpu_usage = cpu.get("usage_percent", 0.0)
    res_table.add_row(
        "CPU",
        get_progress_bar(cpu_usage, width=18),
        f"{cpu.get('logical_cores')} Cores @ {cpu.get('frequency_mhz_current', 0.0):.0f}MHz",
    )
    mem_usage = mem.get("usage_percent", 0.0)
    res_table.add_row(
        "Memory",
        get_progress_bar(mem_usage, width=18),
        f"{format_bytes(mem.get('used_bytes', 0))} / {format_bytes(mem.get('total_bytes', 0))}",
    )
    for part in disk.get("partitions", []):
        part_usage = part.get("usage_percent", 0.0)
        res_table.add_row(
            f"Disk ({part.get('mountpoint')})",
            get_progress_bar(part_usage, width=18),
            f"{format_bytes(part.get('used_bytes', 0))} / {format_bytes(part.get('total_bytes', 0))}",
        )
    left_table.add_row(Panel(res_table, title=f"{stats_icon}TELEMETRY STATISTICS", border_style="magenta"))

    # 3. Plugin Data Feeds
    plug_text = Text()
    if plugin_data:
        for p_name, p_val in plugin_data.items():
            if p_val.get("available", False):
                details = [f"{k}: {v}" for k, v in p_val.items() if k not in ("available", "simulated")]
                sim_tag = " (simulated)" if p_val.get("simulated") else ""
                plug_text.append(f"  {BULLET} {p_name.replace('_', ' ').title()} : ", style="bold green")
                plug_text.append(f"{', '.join(details)}{sim_tag}\n")
            else:
                plug_text.append(f"  {BULLET} {p_name.replace('_', ' ').title()} : ")
                plug_text.append("Not Active", style="grey50")
                plug_text.append("\n")
    else:
        plug_text.append("  No plugin feeds registered.")
    left_table.add_row(Panel(plug_text, title=f"{plug_icon}PLUGIN DATA FEEDS", border_style="green"))

    # ── RIGHT COLUMN ─────────────────────────────────────────────────────────
    right_table = Table.grid(expand=True, padding=1)

    # 1. Health KPI
    health_color = get_severity_color(status)
    health_box = Text()
    health_box.append("\n  Overall Rating : ", style="bold")
    health_box.append(f"{status}\n", style=f"bold {health_color}")
    health_box.append("  Health Score   : ", style="bold")
    health_box.append(f"{score:.1f} / 100\n", style=f"bold {health_color}")
    health_bar = get_progress_bar(score, width=22)
    health_box.append("  Status Gauge   : ")
    health_box.append(Text.from_markup(health_bar))
    health_box.append("\n")
    right_table.add_row(Panel(health_box, title=f"{health_icon}SYSTEM HEALTH KPI", border_style=health_color))

    # 2. Process Hogs
    proc_table = Table(show_header=True, header_style="bold yellow", box=None, expand=True)
    proc_table.add_column("PID",      style="cyan")
    proc_table.add_column("Name")
    proc_table.add_column("CPU %",    justify="right")
    proc_table.add_column("Memory %", justify="right")
    proc_table.add_column("Status")
    for proc in metrics.get("processes", []):
        proc_table.add_row(
            str(proc["pid"]),
            proc["name"][:14],
            f"{proc['cpu_percent']}%",
            f"{proc['memory_percent']}%",
            proc["status"],
        )
    right_table.add_row(Panel(proc_table, title=f"{proc_icon}TOP PROCESS HOGS", border_style="yellow"))

    # 3. Anomalies
    anom_text = Text()
    anomalies = metrics.get("anomalies", [])
    if anomalies:
        for anom in anomalies:
            sev = anom.get("severity", "LOW")
            sev_color = get_severity_color(sev)
            anom_text.append(f"  {BULLET} ")
            anom_text.append(f"[{sev}]", style=f"bold {sev_color}")
            anom_text.append(f" {anom.get('description')}\n")
    else:
        anom_text.append(f"  ✓ No telemetry anomalies or behavioral deviations detected.")
    right_table.add_row(
        Panel(anom_text, title=f"{anom_icon}ACTIVE ANOMALIES",
              border_style="red" if anomalies else "green")
    )

    grid.add_row(left_table, right_table)

    console.print()
    console.rule(f"[bold cyan]SYSLENS {EM_DASH} ENTERPRISE TELEMETRY SCAN[/bold cyan]")
    console.print()
    console.print(grid)
    console.print()
