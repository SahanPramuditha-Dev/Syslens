"""
``syslens live`` — Real-time split-pane terminal dashboard streaming telemetry.
"""
import subprocess
import time

from rich.layout import Layout
from rich.live import Live
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table

from syslens.commands._shared import (
    console,
    format_bytes,
    format_time_duration,
    get_progress_bar,
    get_severity_color,
    get_sparkline,
    supports_unicode,
)


def run(anomaly_interface, plugin_manager, health_engine) -> None:
    """Start the real-time terminal dashboard with split-pane Rich layout."""
    from syslens.core.system import get_system_info
    from syslens.engine.detector import AnomalyDetector

    console.clear()
    detector = AnomalyDetector()

    cpu_history: list  = []
    mem_history: list  = []
    alerted_keys: set  = set()
    flash_state        = False
    footer_msg         = "Q: quit | R: refresh | E: export html | D: start dashboard API"

    try:
        tick_counter = 0
        metrics = None
        data    = None
        score   = 100.0
        status  = "HEALTHY"
        anomalies: list  = []
        net_data: dict   = {}
        disk_h: dict     = {}
        cpu_usage = 0.0
        mem_usage = 0.0

        with Live(console=console, screen=True, auto_refresh=True) as live:
            while True:
                if tick_counter == 0 or tick_counter >= 20:
                    tick_counter = 0
                    metrics = anomaly_interface.scan_system()
                    plugin_data = plugin_manager.execute_all(metrics)
                    metrics["plugins_data"] = plugin_data

                    score, _ = health_engine.calculate_score(metrics)
                    score = plugin_manager.modify_health_score(score, metrics)
                    status = "HEALTHY" if score >= 80 else "DEGRADED" if score >= 50 else "CRITICAL"
                    metrics["health"] = {"score": score, "status": status}

                    data      = get_system_info()
                    anomalies = detector.analyze(metrics)

                    cpu_usage = data.get("cpu_usage", 0.0)
                    mem_usage = data.get("memory_usage", 0.0)
                    cpu_history = (cpu_history + [cpu_usage])[-20:]
                    mem_history = (mem_history + [mem_usage])[-20:]

                    diagnoses = health_engine.diagnose_issues(metrics)
                    net_data  = metrics.get("plugins_data", {}).get("network_telemetry", {})
                    disk_h    = metrics.get("plugins_data", {}).get("disk_health", {})

                    high_anoms = [a for a in anomalies if a.get("severity") == "HIGH"]
                    for a in high_anoms:
                        a_key = f"{a.get('metric')}_{a.get('timestamp')}"
                        if a_key not in alerted_keys:
                            alerted_keys.add(a_key)
                            try:
                                import winsound
                                winsound.Beep(1200, 250)
                            except Exception:
                                pass
                    if high_anoms:
                        flash_state = not flash_state

                # ── Layout skeleton ───────────────────────────────────────────
                layout = Layout()
                layout.split_column(
                    Layout(name="header",  size=4),
                    Layout(name="body",    ratio=1),
                    Layout(name="footer",  size=3),
                )
                layout["body"].split_row(Layout(name="left", ratio=1), Layout(name="right", ratio=1))
                layout["left"].split_column(
                    Layout(name="health",    size=7),
                    Layout(name="telemetry", ratio=1),
                    Layout(name="plugins",   size=11),
                )
                layout["right"].split_column(
                    Layout(name="watchdog",      ratio=1),
                    Layout(name="alerts",        size=8),
                    Layout(name="troubleshooter",size=9),
                )

                # ── 1. Header ─────────────────────────────────────────────────
                has_critical = anomalies and any(a.get("severity") == "HIGH" for a in anomalies)
                status_theme = "red" if score < 50 else "yellow" if score < 80 else "green"
                border_color = "red" if (has_critical and flash_state) else ("cyan" if status_theme == "green" else status_theme)
                header_title = (
                    "🚨 SYSTEM CRITICAL OBSERVATION 🚨" if (has_critical and flash_state)
                    else "🧠 SYSLENS • COGNITIVE TELEMETRY & DIAGNOSTICS CENTER"
                )
                hostname  = metrics.get("os", {}).get("hostname",    "localhost") if metrics else "local"
                os_desc   = f"{metrics.get('os', {}).get('os_name', 'OS')} {metrics.get('os', {}).get('os_release', '')}" if metrics else "Local System"
                uptime_str = format_time_duration(metrics.get("os", {}).get("uptime_seconds", 0)) if metrics else "0s"
                local_ip   = metrics.get("os", {}).get("local_ip",   "127.0.0.1") if metrics else "127.0.0.1"

                hdr = Table.grid(expand=True)
                hdr.add_column(ratio=2, justify="left")
                hdr.add_column(ratio=3, justify="right")
                hdr.add_row(
                    f"[bold {border_color}]{header_title}[/bold {border_color}]",
                    f"[grey50]Host:[/grey50] [bold white]{hostname}[/bold white] | [grey50]OS:[/grey50] {os_desc} | [grey50]IP:[/grey50] {local_ip}",
                )
                layout["header"].update(Panel(hdr, border_style=border_color))

                # ── 2. Health KPI ─────────────────────────────────────────────
                s_color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
                health_desc = (
                    "System performance is optimal. Background workloads are stable."
                    if s_color == "green" else
                    "Degraded performance. Review anomalies and process hogs."
                    if s_color == "yellow" else
                    "Critical bottleneck! Severe CPU/Memory spikes detected. Action required."
                )
                health_gauge = get_progress_bar(score, width=28)
                ht = Table.grid(expand=True)
                ht.add_column(width=16)
                ht.add_column(ratio=1)
                ht.add_row("[bold white]System Rating[/bold white] :", f"[bold {s_color}]{status.upper()}[/bold {s_color}]")
                ht.add_row("[bold white]Health Index[/bold white]  :", f"{score:.1f}/100 [grey37]({health_gauge})[/]")
                ht.add_row("[bold white]Diagnostics[/bold white]   :", f"[italic grey70]{health_desc}[/italic grey70]")
                ht.add_row("[bold white]System Uptime[/bold white] :", uptime_str)
                layout["health"].update(Panel(ht, title="🧠 COGNITIVE HEALTH STATUS", border_style=s_color))

                # ── 3. Resource Telemetry ─────────────────────────────────────
                cpu_spark = get_sparkline(cpu_history, max_width=18)
                mem_spark = get_sparkline(mem_history, max_width=18)
                cpu_gauge = get_progress_bar(cpu_usage, width=18)
                mem_gauge = get_progress_bar(mem_usage, width=18)

                disk_partitions = metrics.get("disk", {}).get("partitions", []) if metrics else []
                max_d_usage = disk_partitions[0].get("usage_percent", 0.0) if disk_partitions else 0.0
                disk_gauge  = get_progress_bar(max_d_usage, width=18)

                read_rate = write_rate = 0.0
                if metrics and len(anomaly_interface.baseline.history) >= 1:
                    last_pt    = anomaly_interface.baseline.history[-1]
                    read_rate  = last_pt.get("disk_read_rate",  0.0) / 1024 / 1024
                    write_rate = last_pt.get("disk_write_rate", 0.0) / 1024 / 1024

                cores_usage = metrics.get("cpu", {}).get("cores_usage_percent", []) if metrics else []
                cores_str   = ""
                if cores_usage:
                    blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
                    cores_str = " | Cores: " + "".join(
                        blocks[max(0, min(len(blocks) - 1, int((v / 100.0) * (len(blocks) - 1))))]
                        for v in cores_usage[:8]
                    )
                    if len(cores_usage) > 8:
                        cores_str += f"+{len(cores_usage) - 8}"

                freq_curr = metrics.get("cpu", {}).get("frequency_mhz_current", 0.0) if metrics else 0.0
                freq_max  = metrics.get("cpu", {}).get("frequency_mhz_max",     0.0) if metrics else 0.0
                freq_text = f" ({freq_curr:.0f}/{freq_max:.0f}MHz)" if freq_max > 0 else ""

                tt = Table(show_header=True, header_style="bold cyan", box=None, expand=True)
                tt.add_column("Subsystem", width=10)
                tt.add_column("Utilization Gauge", width=32)
                tt.add_column("Activity Sparkline / Info", ratio=1)
                tt.add_row("CPU",     cpu_gauge,  f"[cyan]{cpu_spark}[/cyan]{freq_text}{cores_str}")
                tt.add_row("Memory",  mem_gauge,  f"[purple]{mem_spark}[/purple] Swap: {metrics.get('memory', {}).get('swap_usage_percent', 0.0):.1f}%" if metrics else "0.0%")
                tt.add_row("Storage", disk_gauge, f"Read: {read_rate:.2f} MB/s | Write: {write_rate:.2f} MB/s")
                layout["telemetry"].update(Panel(tt, title="⚙️ HARDWARE METRICS & RESOURCE ENGINE", border_style="cyan"))

                # ── 4. Plugins ────────────────────────────────────────────────
                gpu_data = metrics.get("plugins_data", {}).get("gpu_analyzer",     {}) if metrics else {}
                bat_data = metrics.get("plugins_data", {}).get("battery_health",   {}) if metrics else {}

                pt = Table(show_header=True, header_style="bold green", box=None, expand=True)
                pt.add_column("Plugin Module", width=18)
                pt.add_column("Telemetry Observations", ratio=1)
                pt.add_column("Status", width=10, justify="right")

                if gpu_data and gpu_data.get("available"):
                    gl   = gpu_data.get("utilization_gpu_percent", 0.0)
                    gt   = gpu_data.get("temperature_c", 0.0)
                    gc   = "red" if gt > 80 else "yellow" if gt > 65 else "green"
                    pt.add_row("GPU Analyzer", f"Load: {gl}% | Temp: {gt}°C | VRAM: {gpu_data.get('utilization_memory_percent')}%", f"[{gc}]ACTIVE[/]")
                else:
                    pt.add_row("GPU Analyzer", "[grey50]No compatible GPU detected.[/grey50]", "[grey50]OFFLINE[/]")

                if bat_data and bat_data.get("available"):
                    bp   = bat_data.get("percent", 100)
                    plug = bat_data.get("power_plugged", True)
                    bc   = "green" if plug or bp > 25 else "yellow" if bp > 15 else "red"
                    bst  = "Charging ⚡" if plug else "Discharging 🔋"
                    pt.add_row("Battery Health", f"Level: {bp}% | Mode: {bst}", f"[{bc}]ONLINE[/]")
                else:
                    pt.add_row("Battery Health", "[grey50]No system battery detected.[/grey50]", "[grey50]OFFLINE[/]")

                if net_data and net_data.get("available"):
                    down  = net_data.get("bytes_recv_sec", 0.0)
                    up    = net_data.get("bytes_sent_sec", 0.0)
                    conns = net_data.get("active_connections", 0)
                    nc    = "red" if conns > 500 else "green"
                    pt.add_row("Network Telemetry", f"Down: {format_bytes(down)}/s | Up: {format_bytes(up)}/s | Conns: {conns}", f"[{nc}]ONLINE[/]")
                else:
                    pt.add_row("Network Telemetry", "[grey50]Interface query failed.[/grey50]", "[grey50]OFFLINE[/]")

                if disk_h and disk_h.get("available"):
                    smart = disk_h.get("smart_status", "PASSED")
                    temp  = disk_h.get("disk_temp_c", 32.0)
                    life  = disk_h.get("wear_level_percent", 100.0)
                    dc    = "red" if smart != "PASSED" or temp > 55 else "green"
                    pt.add_row("Disk Diagnostics", f"SMART: {smart} | Temp: {temp}°C | SSD Life: {life}%", f"[{dc}]{'WARNING' if smart != 'PASSED' else 'HEALTHY'}[/]")
                else:
                    pt.add_row("Disk Diagnostics", "[grey50]Drive diagnostics unavailable.[/grey50]", "[grey50]OFFLINE[/]")

                layout["plugins"].update(Panel(pt, title="🔌 EXPANDED PLUGIN TELEMETRY", border_style="green"))

                # ── 5. Process Watchdog ───────────────────────────────────────
                wt = Table(show_header=True, header_style="bold yellow", box=None, expand=True)
                wt.add_column("PID",   width=7,  style="cyan")
                wt.add_column("Process Name", width=18, style="bold")
                wt.add_column("CPU %", width=8,  justify="right")
                wt.add_column("Memory %", width=10, justify="right")
                wt.add_column("Watchdog Alert Label", ratio=1, justify="right")
                procs = metrics.get("processes", []) if metrics else []
                if procs:
                    for p in procs[:5]:
                        cv = p.get("cpu_percent", 0.0)
                        mv = p.get("memory_percent", 0.0)
                        hog = cv > 20.0 or mv > 10.0
                        pc  = "red" if cv > 50.0 or mv > 25.0 else "yellow" if hog else "white"
                        lbl = "[bold red]Resource Hog ⚠️[/bold red]" if cv > 40.0 else "[yellow]High Load ⚠[/yellow]" if hog else "[grey37]Normal[/]"
                        wt.add_row(str(p["pid"]), f"[{pc}]{p['name'][:18]}[/]", f"[{pc}]{cv:.1f}%[/]", f"[{pc}]{mv:.1f}%[/]", lbl)
                else:
                    wt.add_row("[grey50]--[/]", "[grey50]Gathering processes...[/]", "[grey50]0.0%[/]", "[grey50]0.0%[/]", "[grey50]--[/]")
                layout["watchdog"].update(Panel(wt, title="🔥 BACKGROUND PROCESS WATCHDOG", border_style="yellow"))

                # ── 6. Alerts ─────────────────────────────────────────────────
                at = Table(show_header=True, header_style="bold red", box=None, expand=True)
                at.add_column("Severity", width=10)
                at.add_column("Subsystem", width=12, style="bold")
                at.add_column("Telemetry Deviation Details", ratio=1)
                has_high = has_medium = False
                if anomalies:
                    for a in anomalies[:3]:
                        sev = a.get("severity", "LOW")
                        has_high   = has_high   or sev == "HIGH"
                        has_medium = has_medium or sev == "MEDIUM"
                        sc = get_severity_color(sev)
                        mn = a.get("metric", "unknown").replace("_", " ").upper()
                        at.add_row(f"[bold {sc}]{sev}[/bold {sc}]", mn, a.get("description", "Telemetry deviation detected."))
                else:
                    at.add_row("[bold green]HEALTHY[/bold green]", "SYSTEM", "All hardware components and baseline thresholds are stable.")
                layout["alerts"].update(Panel(at,
                    title="⚠️ REAL-TIME BEHAVIOR ALERTS & ANOMALIES (Z-SCORE)",
                    border_style="red" if has_high else "yellow" if has_medium else "green"))

                # ── 7. Troubleshooter ─────────────────────────────────────────
                trt = Table(show_header=False, box=None, expand=True)
                trt.add_column("Indicator", width=3, justify="center")
                trt.add_column("Diagnostics", ratio=1)
                cpu_hogs = [p for p in procs if p.get("cpu_percent", 0.0)    > 25.0]
                mem_hogs = [p for p in procs if p.get("memory_percent", 0.0) > 12.0]
                slow = False

                if cpu_usage > 70.0:
                    slow = True
                    trt.add_row("[bold red]➜[/bold red]", "[bold red]CPU Spike Detected[/bold red]: Fans spinning up.")
                    if cpu_hogs:
                        h = cpu_hogs[0]
                        trt.add_row("", f"[bold yellow]Remedy[/bold yellow]: Terminate {escape(h['name'])} (PID: {h['pid']}) → [bold white]taskkill /PID {h['pid']} /F[/bold white]")
                    else:
                        trt.add_row("", "[bold yellow]Remedy[/bold yellow]: Close heavy IDE processes.")

                if mem_usage > 80.0:
                    slow = True
                    trt.add_row("[bold red]➜[/bold red]", "[bold red]RAM Saturation Warning[/bold red]: Swap writing active.")
                    if mem_hogs:
                        h = mem_hogs[0]
                        trt.add_row("", f"[bold yellow]Remedy[/bold yellow]: Terminate RAM hog {escape(h['name'])} (PID: {h['pid']}).")
                    else:
                        trt.add_row("", "[bold yellow]Remedy[/bold yellow]: Close unused browser helpers or idle terminals.")

                net_conns = net_data.get("active_connections", 0)
                if net_conns > 400:
                    slow = True
                    trt.add_row("[bold yellow]➜[/bold yellow]", f"[bold yellow]High Connection Count ({net_conns})[/bold yellow]: Socket leak risk.")
                    trt.add_row("", "[bold yellow]Remedy[/bold yellow]: Identify network process using active sockets.")

                smart_s = disk_h.get("smart_status", "PASSED")
                if smart_s != "PASSED":
                    slow = True
                    trt.add_row("[bold red]➜[/bold red]", "[bold red]SMART HDD/SSD Warnings[/bold red]: Drive failure risks detected!")
                    trt.add_row("", "[bold yellow]Remedy[/bold yellow]: Run sector check or backup data immediately.")

                if not slow:
                    trt.add_row("[bold green]✓[/bold green]", "[bold green]Hardware parameters stable.[/bold green]")
                    trt.add_row("", "[bold cyan]Advice[/bold cyan]: Run [bold white]syslens scan[/bold white] for complete diagnostics snap.")
                    trt.add_row("", "[bold cyan]Advice[/bold cyan]: Use [bold white]syslens health[/bold white] for troubleshoot reports.")

                layout["troubleshooter"].update(Panel(trt, title="💡 DIAGNOSTICS & REMEDIATION SUGGESTIONS", border_style="cyan"))

                # ── 8. Footer ─────────────────────────────────────────────────
                layout["footer"].update(Panel(
                    f"[bold white]{footer_msg}[/bold white]\n[grey37]SysLens v1.3 • Refreshing dynamically (Press Q to quit)[/]",
                    border_style="grey50"
                ))

                live.update(layout)

                # ── Keyboard input ────────────────────────────────────────────
                key_pressed = False
                try:
                    import msvcrt
                    if msvcrt.kbhit():
                        char = msvcrt.getch().lower()
                        if char == b"q":
                            raise KeyboardInterrupt
                        elif char == b"r":
                            tick_counter = 0
                            footer_msg   = "[yellow]Refreshing telemetry now...[/]"
                            key_pressed  = True
                        elif char == b"e":
                            try:
                                from syslens.utils.format import export_html_report
                                export_html_report(metrics, "syslens_report.html")
                                footer_msg = "[green]✓ Telemetry report exported to syslens_report.html![/green]"
                            except Exception as err:
                                footer_msg = f"[red]✗ Export failed: {err}[/red]"
                            key_pressed = True
                        elif char == b"d":
                            try:
                                subprocess.Popen(["syslensd"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                footer_msg = "[green]✓ FastAPI Server starting on http://127.0.0.1:8000[/green]"
                            except Exception:
                                try:
                                    subprocess.Popen(["python", "-m", "syslens.cli", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                    footer_msg = "[green]✓ FastAPI Server starting on http://127.0.0.1:8000[/green]"
                                except Exception as err:
                                    footer_msg = f"[red]✗ Launch failed: {err}[/red]"
                            key_pressed = True
                except ImportError:
                    pass

                if key_pressed:
                    continue

                tick_counter += 1
                time.sleep(0.05)

    except KeyboardInterrupt:
        console.clear()
        console.print("[green]Live stream terminated.[/green]")
