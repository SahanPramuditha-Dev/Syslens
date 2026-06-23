import sys
import time
import json
import argparse
from typing import Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.columns import Columns
from rich.text import Text

from syslens.core.anomaly import AnomalyInterface
from syslens.core.health import SystemHealthEngine
from syslens.plugins.manager import PluginManager
from syslens.utils.format import format_bytes, format_time_duration, get_severity_color, get_progress_bar, supports_unicode

console = Console()

# Cross-platform safe symbols
EM_DASH = "—" if supports_unicode() else "-"
CHECK_MARK = "✓" if supports_unicode() else "[OK]"
BULLET = "•" if supports_unicode() else "*"

class SysLensCLI:
    """Developer Command-Line Interface for interacting with SysLens system metrics."""

    def __init__(self):
        self.anomaly_interface = AnomalyInterface()
        self.health_engine = SystemHealthEngine()
        self.plugin_manager = PluginManager()

    def run_scan(self, output_json: bool = False) -> None:
        """Execute a full scan of system state and print formatted results."""
        metrics = self.anomaly_interface.scan_system()
        
        # Execute plugins
        plugin_data = self.plugin_manager.execute_all(metrics)
        metrics["plugins_data"] = plugin_data

        # Health Evaluation
        score, status = self.health_engine.calculate_score(metrics)
        # Modify health score through plugins
        score = self.plugin_manager.modify_health_score(score, metrics)
        
        # Recalculate status with final score
        if score >= 80.0:
            status = "HEALTHY"
        elif score >= 50.0:
            status = "DEGRADED"
        else:
            status = "CRITICAL"

        metrics["health"] = {"score": score, "status": status}

        if output_json:
            console.print(json.dumps(metrics, indent=2))
            return

        # Upgraded Enterprise-Grade CLI Scan Layout (Side-by-Side Double Column Layout)
        from syslens.utils.format import get_sparkline, get_severity_color, supports_unicode
        
        unicode_active = supports_unicode()
        
        # Cross-platform safe header titles
        env_icon = "🖥️  " if unicode_active else ""
        stats_icon = "⚙️  " if unicode_active else ""
        plug_icon = "🔌  " if unicode_active else ""
        health_icon = "🧠  " if unicode_active else ""
        proc_icon = "🔥  " if unicode_active else ""
        anom_icon = "⚠  " if unicode_active else ""
        
        # Outer grid table layout
        grid = Table.grid(expand=True, padding=2)
        grid.add_column(ratio=1) # Left pane
        grid.add_column(ratio=1) # Right pane
        
        # --- LEFT COLUMN CONTENT ---
        left_table = Table.grid(expand=True, padding=1)
        
        # 1. Environment Metadata Card
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
        
        # 2. Telemetry Statistics Card
        cpu = metrics.get("cpu", {})
        mem = metrics.get("memory", {})
        disk = metrics.get("disk", {})
        
        res_table = Table(show_header=True, header_style="bold magenta", box=None, expand=True)
        res_table.add_column("Resource")
        res_table.add_column("Utilization Meter")
        res_table.add_column("Details")
        
        cpu_usage = cpu.get("usage_percent", 0.0)
        res_table.add_row(
            "CPU",
            get_progress_bar(cpu_usage, width=18),
            f"{cpu.get('logical_cores')} Cores @ {cpu.get('frequency_mhz_current', 0.0):.0f}MHz"
        )
        mem_usage = mem.get("usage_percent", 0.0)
        res_table.add_row(
            "Memory",
            get_progress_bar(mem_usage, width=18),
            f"{format_bytes(mem.get('used_bytes', 0))} / {format_bytes(mem.get('total_bytes', 0))}"
        )
        for part in disk.get("partitions", []):
            part_usage = part.get("usage_percent", 0.0)
            res_table.add_row(
                f"Disk ({part.get('mountpoint')})",
                get_progress_bar(part_usage, width=18),
                f"{format_bytes(part.get('used_bytes', 0))} / {format_bytes(part.get('total_bytes', 0))}"
            )
        left_table.add_row(Panel(res_table, title=f"{stats_icon}TELEMETRY STATISTICS", border_style="magenta"))
        
        # 3. Plugin Data Card
        plug_text = Text()
        if plugin_data:
            for p_name, p_val in plugin_data.items():
                if p_val.get("available", False):
                    details = []
                    for k, v in p_val.items():
                        if k in ["available", "simulated"]:
                            continue
                        details.append(f"{k}: {v}")
                    val_str = ", ".join(details)
                    sim_tag = " (simulated)" if p_val.get("simulated") else ""
                    plug_text.append(f"  {BULLET} {p_name.replace('_', ' ').title()} : ", style="bold green")
                    plug_text.append(f"{val_str}{sim_tag}\n")
                else:
                    plug_text.append(f"  {BULLET} {p_name.replace('_', ' ').title()} : ")
                    plug_text.append("Not Active", style="grey50")
                    plug_text.append("\n")
        else:
            plug_text.append("  No plugin feeds registered.")
        left_table.add_row(Panel(plug_text, title=f"{plug_icon}PLUGIN DATA FEEDS", border_style="green"))
        
        # --- RIGHT COLUMN CONTENT ---
        right_table = Table.grid(expand=True, padding=1)
        
        # 1. Health KPI Card
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
        
        # 2. Process Hogs Card
        proc_table = Table(show_header=True, header_style="bold yellow", box=None, expand=True)
        proc_table.add_column("PID", style="cyan")
        proc_table.add_column("Name")
        proc_table.add_column("CPU %", justify="right")
        proc_table.add_column("Memory %", justify="right")
        proc_table.add_column("Status")
        
        for proc in metrics.get("processes", []):
            proc_table.add_row(
                str(proc["pid"]),
                proc["name"][:14],
                f"{proc['cpu_percent']}%",
                f"{proc['memory_percent']}%",
                proc["status"]
            )
        right_table.add_row(Panel(proc_table, title=f"{proc_icon}TOP PROCESS HOGS", border_style="yellow"))
        
        # 3. Anomalies Card
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
            anom_text.append(f"  {CHECK_MARK} No telemetry anomalies or behavioral deviations detected.")
        right_table.add_row(Panel(anom_text, title=f"{anom_icon}ACTIVE ANOMALIES", border_style="red" if anomalies else "green"))
        
        grid.add_row(left_table, right_table)
        
        # Print main rule header
        console.print()
        console.rule(f"[bold cyan]SYSLENS {EM_DASH} ENTERPRISE TELEMETRY SCAN[/bold cyan]")
        console.print()
        console.print(grid)
        console.print()

    def run_health(self) -> None:
        """Run system diagnostics and display troubleshoot reports."""
        metrics = self.anomaly_interface.scan_system()
        plugin_data = self.plugin_manager.execute_all(metrics)
        metrics["plugins_data"] = plugin_data

        score, status = self.health_engine.calculate_score(metrics)
        score = self.plugin_manager.modify_health_score(score, metrics)
        
        if score >= 80.0:
            status = "HEALTHY"
        elif score >= 50.0:
            status = "DEGRADED"
        else:
            status = "CRITICAL"

        metrics["health"] = {"score": score, "status": status}

        unicode_active = supports_unicode()
        border_char = "━" if unicode_active else "="
        border_line = border_char * 30
        
        brain_icon = "🧠 " if unicode_active else ""
        gear_icon = "⚙ " if unicode_active else ""
        warn_icon = "⚠ " if unicode_active else ""
        tip_icon = "💡 " if unicode_active else ""
        bullet = "•" if unicode_active else "*"
        arrow = "→" if unicode_active else "->"

        def get_status_circle(val_status: str) -> str:
            if not unicode_active:
                return f"[{val_status}]"
            if val_status == "HEALTHY":
                return "🟢"
            elif val_status == "DEGRADED":
                return "🟡"
            else:
                return "🔴"

        def get_metric_level(percent: float) -> tuple:
            if percent >= 80.0:
                return ("🔴", "High") if unicode_active else ("", "High")
            elif percent >= 60.0:
                return ("🟡", "Moderate") if unicode_active else ("", "Moderate")
            else:
                return ("🟢", "Normal") if unicode_active else ("", "Normal")

        # Get system metrics values
        cpu_usage = metrics.get("cpu", {}).get("usage_percent", 0.0)
        mem_usage = metrics.get("memory", {}).get("usage_percent", 0.0)
        disk_partitions = metrics.get("disk", {}).get("partitions", [])
        disk_usage = max([p.get("usage_percent", 0.0) for p in disk_partitions]) if disk_partitions else 0.0

        cpu_circle, cpu_level = get_metric_level(cpu_usage)
        mem_circle, mem_level = get_metric_level(mem_usage)
        disk_circle, disk_level = get_metric_level(disk_usage)

        # Print header
        console.print(border_line)
        console.print(f"{brain_icon}SYSLENS SYSTEM HEALTH REPORT")
        console.print(border_line)
        console.print()
        
        # Overall status
        console.print(f"{get_status_circle(status)} OVERALL STATUS: {score:.0f} / 100 ({status})")
        console.print()

        # System Metrics
        console.print(f"{gear_icon}SYSTEM METRICS")
        console.print(f"CPU Usage      : {cpu_usage:.0f}%  {cpu_circle} {cpu_level}".strip())
        console.print(f"Memory Usage   : {mem_usage:.0f}%  {mem_circle} {mem_level}".strip())
        console.print(f"Disk Usage     : {disk_usage:.0f}%  {disk_circle} {disk_level}".strip())
        console.print()

        # Anomalies
        console.print(f"{warn_icon}ANOMALIES DETECTED")
        anomalies = metrics.get("anomalies", [])
        if anomalies:
            for anom in anomalies:
                metric_name = anom.get("metric", "UNKNOWN").upper()
                deviation = ""
                
                # Try to calculate deviation percentage from baseline
                curr_val = anom.get("current_value")
                base_mean = anom.get("baseline_mean")
                if isinstance(curr_val, (int, float)) and isinstance(base_mean, (int, float)) and base_mean > 0:
                    dev_pct = ((curr_val - base_mean) / base_mean) * 100
                    deviation = f"{dev_pct:.0f}% deviation from baseline"
                elif isinstance(curr_val, dict) and isinstance(base_mean, dict):
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

        # Recommendations
        console.print(f"{tip_icon}RECOMMENDATION")
        diagnoses = self.health_engine.diagnose_issues(metrics)
        recs = []
        for diag in diagnoses:
            recs.extend(diag.get("recommendations", []))
        
        # Unique list of recommendations
        unique_recs = []
        for r in recs:
            if r not in unique_recs:
                unique_recs.append(r)

        if unique_recs:
            for rec in unique_recs:
                console.print(f"{bullet} {rec}")
        else:
            console.print(f"{bullet} System parameters are stable. No actions required.")
            
        console.print(border_line)

    def run_live(self) -> None:
        """Start a real-time terminal dashboard streaming telemetry updates with split-pane layout."""
        from syslens.core.system import get_system_info
        from syslens.core.health import calculate_health
        from syslens.engine.detector import AnomalyDetector
        from syslens.utils.format import (
            get_sparkline,
            get_severity_color,
            supports_unicode
        )
        
        console.clear()
        detector = AnomalyDetector()
        
        cpu_history = []
        mem_history = []
        alerted_keys = set()
        flash_state = False
        footer_msg = "Q: quit | R: refresh | E: export html | D: start dashboard API"
        
        try:
            # Refresh telemetry at 0.5Hz, but check keyboard hit at 20Hz (50ms interval) for rapid hotkey response
            tick_counter = 0
            metrics = None
            data = None
            score = 100.0
            status = "HEALTHY"
            anomalies = []
            diagnoses = []
            
            with Live(console=console, screen=True, auto_refresh=True) as live:
                while True:
                    # Update telemetry if it's the first tick or 2 seconds have passed (40 ticks at 50ms)
                    if tick_counter == 0 or tick_counter >= 40:
                        tick_counter = 0
                        metrics = self.anomaly_interface.scan_system()
                        plugin_data = self.plugin_manager.execute_all(metrics)
                        metrics["plugins_data"] = plugin_data

                        score, status = self.health_engine.calculate_score(metrics)
                        score = self.plugin_manager.modify_health_score(score, metrics)
                        
                        if score >= 80.0:
                            status = "HEALTHY"
                        elif score >= 50.0:
                            status = "DEGRADED"
                        else:
                            status = "CRITICAL"

                        metrics["health"] = {"score": score, "status": status}
                        
                        data = get_system_info()
                        anomalies = detector.analyze(metrics)
                        
                        cpu_usage = data.get("cpu_usage", 0.0)
                        mem_usage = data.get("memory_usage", 0.0)
                        cpu_history.append(cpu_usage)
                        mem_history.append(mem_usage)
                        cpu_history = cpu_history[-20:]
                        mem_history = mem_history[-20:]
                        
                        # Diagnose recommendations
                        diagnoses = self.health_engine.diagnose_issues(metrics)
                        
                        # Alarm sound beeps on HIGH anomalies
                        high_anoms = [a for a in anomalies if a.get("severity") == "HIGH"]
                        if high_anoms:
                            for a in high_anoms:
                                a_key = f"{a.get('metric')}_{a.get('timestamp')}"
                                if a_key not in alerted_keys:
                                    alerted_keys.add(a_key)
                                    try:
                                        import winsound
                                        winsound.Beep(1200, 250)
                                    except Exception:
                                        pass
                                        
                        # Toggle flash state if high anomalies exist
                        if high_anoms:
                            flash_state = not flash_state

                    # Construct layout
                    layout = Layout()
                    layout.split_column(
                        Layout(name="header", size=3),
                        Layout(name="body", ratio=1),
                        Layout(name="footer", size=3)
                    )
                    layout["body"].split_row(
                        Layout(name="left", ratio=1),
                        Layout(name="right", ratio=1)
                    )
                    
                    # 1. Header
                    has_critical = anomalies and any(a.get("severity") == "HIGH" for a in anomalies)
                    border_color = "red" if (has_critical and flash_state) else "cyan"
                    header_title = "🚨 SYSTEM CRITICAL OBSERVATION 🚨" if (has_critical and flash_state) else "🧠 SYSLENS • SYSTEM INTELLIGENCE STREAM"
                    
                    layout["header"].update(Panel(
                        f"[bold {border_color}]{header_title}[/bold {border_color}] | Host: {metrics.get('os', {}).get('hostname', 'localhost') if metrics else 'local'}",
                        border_style=border_color
                    ))

                    # 2. Left Pane (Status, Telemetry + Sparkline, Plugins)
                    left_text = Text()
                    
                    # Status text
                    status_color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
                    left_text.append("📊 SYSTEM HEALTH STATUS:\n", style="bold white")
                    left_text.append(f"  Score  : {score:.1f}/100\n")
                    left_text.append("  Status : ")
                    left_text.append(status, style=f"bold {status_color}")
                    left_text.append("\n\n")
                    
                    # Telemetry table with sparkline
                    left_text.append("⚙ RESOURCE METRICS:\n", style="bold magenta")
                    cpu_spark = get_sparkline(cpu_history, max_width=18)
                    mem_spark = get_sparkline(mem_history, max_width=18)
                    left_text.append(f"  CPU Usage   : {cpu_usage if data else 0.0:.1f}% ")
                    left_text.append(cpu_spark, style="cyan")
                    left_text.append("\n")
                    left_text.append(f"  Memory Usage: {mem_usage if data else 0.0:.1f}% ")
                    left_text.append(mem_spark, style="purple")
                    left_text.append("\n")
                    disk_usage = data.get("disk_usage", 0.0) if data else 0.0
                    left_text.append(f"  Disk Usage  : {disk_usage:.1f}%\n\n")
                    
                    # Plugins
                    left_text.append("🔌 LOADED PLUGINS:\n", style="bold green")
                    if metrics and metrics.get("plugins_data"):
                        for name, val in metrics.get("plugins_data").items():
                            if val.get("available", False):
                                if name == "battery_health":
                                    left_text.append(f"  • Battery : {val.get('percent')}% {'(Charging)' if val.get('power_plugged') else '(Discharging)'}\n")
                                elif name == "gpu_analyzer":
                                    left_text.append(f"  • GPU Load: {val.get('utilization_gpu_percent')}% ({val.get('temperature_c')}°C)\n")
                                else:
                                    left_text.append(f"  • {name} : OK\n")
                    else:
                        left_text.append("  No plugin feeds registered.\n")
                        
                    layout["left"].update(Panel(left_text, title="Observability Engine", border_style="cyan"))

                    # 3. Right Pane (Processes, Anomalies, Recommendations)
                    right_text = Text()
                    
                    # Active process hogs
                    right_text.append("🔥 TOP PROCESS HOGS:\n", style="bold yellow")
                    if metrics and metrics.get("processes"):
                        for p in metrics["processes"][:4]:
                            right_text.append(f"  {p['pid']:<6} {p['name'][:14]:<14} CPU: {p['cpu_percent']}% | Mem: {p['memory_percent']}%\n")
                    else:
                        right_text.append("  Gathering process list...\n")
                    right_text.append("\n")
                    
                    # Anomalies list
                    right_text.append("⚠ ACTIVE BEHAVIOR ANOMALIES:\n", style="bold red")
                    if anomalies:
                        for a in anomalies[:3]:
                            sev = a.get("severity", "LOW")
                            sev_color = get_severity_color(sev)
                            right_text.append("  • ")
                            right_text.append(f"[{sev}]", style=f"bold {sev_color}")
                            right_text.append(f" {a.get('description')[:38]}...\n")
                    else:
                        right_text.append("  • No active anomalies detected.\n")
                    right_text.append("\n")

                    # Recommendations
                    right_text.append("💡 SUGGESTED REMEDIATION:\n", style="bold cyan")
                    if diagnoses:
                        recs = []
                        for d in diagnoses:
                            recs.extend(d.get("recommendations", []))
                        unique_recs = list(set(recs))[:2]
                        for r in unique_recs:
                            right_text.append(f"  • {r[:42]}\n")
                    else:
                        right_text.append("  • System parameters stable.\n")

                    layout["right"].update(Panel(right_text, title="Diagnostics & Alerts", border_style="yellow"))

                    # 4. Footer
                    layout["footer"].update(Panel(
                        f"[bold white]{footer_msg}[/bold white]\n[grey37]SysLens v1.3 • Refreshing dynamically (Press Q to quit)[/]",
                        border_style="grey50"
                    ))

                    live.update(layout)

                    # 5. Non-blocking keyboard hit check (runs for 50ms)
                    import msvcrt
                    key_pressed = False
                    if msvcrt.kbhit():
                        char = msvcrt.getch().lower()
                        if char == b'q':
                            raise KeyboardInterrupt
                        elif char == b'r':
                            tick_counter = 0  # Force instant reload on next loop iteration
                            footer_msg = "[yellow]Refreshing telemetry now...[/]"
                            key_pressed = True
                        elif char == b'e':
                            try:
                                from syslens.utils.format import export_html_report
                                export_html_report(metrics, "syslens_report.html")
                                footer_msg = "[green]✓ Telemetry report exported to syslens_report.html![/green]"
                            except Exception as err:
                                footer_msg = f"[red]✗ Export failed: {err}[/red]"
                            key_pressed = True
                        elif char == b'd':
                            try:
                                import subprocess
                                subprocess.Popen(["syslensd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                footer_msg = "[green]✓ FastAPI Server starting on http://127.0.0.1:8000[/green]"
                            except Exception:
                                try:
                                    subprocess.Popen(["python", "-m", "syslens.cli", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    footer_msg = "[green]✓ FastAPI Server starting on http://127.0.0.1:8000[/green]"
                                except Exception as err:
                                    footer_msg = f"[red]✗ Launch failed: {err}[/red]"
                            key_pressed = True
                            
                    if key_pressed:
                        # Restart loop immediately to update visualization
                        continue
                        
                    tick_counter += 1
                    time.sleep(0.05)
                    
        except KeyboardInterrupt:
            console.clear()
            console.print("[green]Live stream terminated.[/green]")

def main() -> None:
    parser = argparse.ArgumentParser(description="SysLens v1.0 Developer Observability CLI Tool")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    subparsers.add_parser("scan", help="Retrieve full system snap and verify status").add_argument(
        "--json", action="store_true", help="Format the scan output as raw JSON string"
    )
    subparsers.add_parser("health", help="Execute diagnostics & health checklist")
    subparsers.add_parser("live", help="Display live updating telemetry console")
    subparsers.add_parser("serve", help="Launch FastAPI System Dashboard server")
    subparsers.add_parser("export", help="Export current telemetry snapshot to HTML report").add_argument(
        "--output", default="syslens_report.html", help="HTML report output destination path"
    )

    args = parser.parse_args()
    
    cli = SysLensCLI()

    if args.command == "scan":
        cli.run_scan(output_json=args.json)
    elif args.command == "health":
        cli.run_health()
    elif args.command == "live":
        cli.run_live()
    elif args.command == "export":
        metrics = cli.anomaly_interface.scan_system()
        plugin_data = cli.plugin_manager.execute_all(metrics)
        metrics["plugins_data"] = plugin_data

        score, status = cli.health_engine.calculate_score(metrics)
        score = cli.plugin_manager.modify_health_score(score, metrics)
        
        if score >= 80.0:
            status = "HEALTHY"
        elif score >= 50.0:
            status = "DEGRADED"
        else:
            status = "CRITICAL"

        metrics["health"] = {"score": score, "status": status}

        from syslens.utils.format import export_html_report
        export_html_report(metrics, args.output)
        console.print(f"[green]{CHECK_MARK} Exported SysLens HTML Report to: [bold]{args.output}[/bold][/green]")
    elif args.command == "serve":
        # Launch Dashboard Server
        try:
            from syslens.dashboard.app import serve
            serve()
        except ImportError:
            console.print("[red]Could not launch FastAPI dashboard. Ensure dependencies are installed.[/red]")
    else:
        # Default behavior: run scan
        cli.run_scan()

if __name__ == "__main__":
    main()
