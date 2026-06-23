from typing import Union

def format_bytes(bytes_value: Union[int, float]) -> str:
    """Format bytes count into human-readable representation (e.g. KB, MB, GB, TB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"

def format_time_duration(seconds: Union[int, float]) -> str:
    """Format duration in seconds into readable hours/minutes/seconds string."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
        
    return " ".join(parts)

def get_severity_color(severity: str) -> str:
    """Map anomaly or health severity to standard console colors."""
    severity = severity.upper()
    if severity == "HIGH" or severity == "CRITICAL":
        return "red"
    elif severity == "MEDIUM" or severity == "DEGRADED":
        return "yellow"
    elif severity == "LOW" or severity == "HEALTHY":
        return "cyan"
    return "white"

import sys

def supports_unicode() -> bool:
    """Determine if current stdout stream supports full unicode rendering."""
    try:
        encoding = (sys.stdout.encoding or 'ascii').lower()
        return 'utf-8' in encoding or 'utf16' in encoding or 'utf32' in encoding or 'cp65001' in encoding
    except Exception:
        return False

def get_progress_bar(percent: float, width: int = 15) -> str:
    """Generate a visual character progress bar with color markup for CLI output."""
    filled = int((percent / 100) * width)
    filled = max(0, min(width, filled))
    empty = width - filled
    
    if supports_unicode():
        bar_char = "█"
        empty_char = "░"
    else:
        bar_char = "#"
        empty_char = "-"

    bar_chars = bar_char * filled
    empty_chars = empty_char * empty
    
    # Decide color based on percentage
    if percent >= 85:
        color = "red"
    elif percent >= 60:
        color = "yellow"
    else:
        color = "green"
        
    return f"[{color}]{bar_chars}[/][grey37]{empty_chars}[/] {percent:.1f}%"

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

def render_header():
    """Render premium system header."""
    console.print("\n")
    console.rule("[bold cyan]SYSLENS • SYSTEM INTELLIGENCE[/bold cyan]")

def render_status(score: float, status: str):
    """Render status panel."""
    color = "green"
    if score < 70:
        color = "yellow"
    if score < 50:
        color = "red"

    console.print(
        Panel.fit(
            f"[bold]{status.upper()}[/bold]\nScore: {score}/100",
            title="🧠 SYSTEM STATUS",
            border_style=color
        )
    )

def render_metrics(data: dict):
    """Render metrics table."""
    table = Table(
        title="⚙ Performance Metrics",
        box=box.SIMPLE_HEAVY
    )

    table.add_column("Metric", style="bold")
    table.add_column("Value")
    table.add_column("State")

    # Support multiple formats defensively
    cpu = data.get("cpu_usage")
    if cpu is None:
        cpu = data.get("cpu", {}).get("usage_percent", 0.0)

    mem = data.get("memory_usage")
    if mem is None:
        # Try virtual memory or percent key
        mem = data.get("memory", {}).get("usage_percent")
        if mem is None:
            mem = data.get("memory", {}).get("percent", 0.0)

    disk = data.get("disk_usage")
    if disk is None:
        parts = data.get("disk", {}).get("partitions", [])
        disk = parts[0].get("usage_percent", 0.0) if parts else 0.0

    table.add_row(
        "CPU Usage",
        f"{cpu:.1f}%" if isinstance(cpu, (int, float)) else f"{cpu}%",
        "🔴 HIGH" if cpu > 80 else "🟡 MODERATE" if cpu > 60 else "🟢 NORMAL"
    )

    table.add_row(
        "Memory Usage",
        f"{mem:.1f}%" if isinstance(mem, (int, float)) else f"{mem}%",
        "🔴 HIGH" if mem > 80 else "🟡 MODERATE" if mem > 60 else "🟢 NORMAL"
    )

    table.add_row(
        "Disk Usage",
        f"{disk:.1f}%" if isinstance(disk, (int, float)) else f"{disk}%",
        "🔴 HIGH" if disk > 80 else "🟡 MODERATE" if disk > 60 else "🟢 NORMAL"
    )

    console.print(table)

def render_anomalies(anomalies: list):
    """Render active anomalies panel."""
    if not anomalies:
        console.print(Panel("[green]No anomalies detected[/green]", title="⚠ Live Anomalies"))
        return

    text = ""
    for a in anomalies:
        a_type = a.get("type") or a.get("metric", "UNKNOWN").upper()
        a_msg = a.get("message") or a.get("description", "Deviation detected.")
        severity = a.get("severity", "LOW")
        
        drift = ""
        curr_val = a.get("current_value")
        base_mean = a.get("baseline_mean")
        if isinstance(curr_val, (int, float)) and isinstance(base_mean, (int, float)) and base_mean > 0:
            dev = ((curr_val - base_mean) / base_mean) * 100
            drift = f"+{dev:.0f}% from baseline"
        else:
            drift = f"index z: {a.get('deviation_z', 0)}"

        text += (
            f"• [bold]{a_type}[/bold]\n"
            f"  Severity : {severity}\n"
            f"  Drift    : {drift}\n"
            f"  Impact   : {a_msg}\n\n"
        )

    console.print(
        Panel(text.strip(), title="⚠ Live Anomalies", border_style="red")
    )

def render_recommendations(diagnoses: list = None):
    """Render recommendations panel."""
    if diagnoses:
        recs = []
        for diag in diagnoses:
            recs.extend(diag.get("recommendations", []))
        
        unique_recs = []
        for r in recs:
            if r not in unique_recs:
                unique_recs.append(r)
        
        text = "\n".join([f"• {r}" for r in unique_recs])
    else:
        text = (
            "• Close unnecessary background apps\n"
            "• Monitor thermal load\n"
            "• Update system drivers if instability persists"
        )
        
    console.print(
        Panel(
            text,
            title="💡 Recommendations",
            border_style="cyan"
        )
    )

def get_sparkline(history: list, max_width: int = 20) -> str:
    """Generate a clean ASCII/Unicode live sparkline chart."""
    if not history:
        return ""
    pts = history[-max_width:]
    if len(pts) < max_width:
        pts = [0.0] * (max_width - len(pts)) + pts
        
    if supports_unicode():
        blocks = [" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█"]
    else:
        blocks = [".", ".", "-", "-", "+", "+", "*", "*", "#"]
        
    line = ""
    for v in pts:
        # map 0-100 values to blocks list index
        idx = int((v / 100.0) * (len(blocks) - 1))
        idx = max(0, min(len(blocks) - 1, idx))
        line += blocks[idx]
    return line

def export_html_report(data: dict, filepath: str) -> None:
    """Compile and save a gorgeous offline-capable HTML dashboard telemetry report."""
    import time
    
    cpu = data.get("cpu_usage") or data.get("cpu", {}).get("usage_percent", 0.0)
    mem = data.get("memory_usage") or data.get("memory", {}).get("usage_percent", 0.0)
    score = data.get("health", {}).get("score", 100.0)
    status = data.get("health", {}).get("status", "HEALTHY")
    
    os_data = data.get("os", {})
    os_name = os_data.get("os_name", "Unknown OS")
    release = os_data.get("os_release", "N/A")
    architecture = os_data.get("architecture", "N/A")
    hostname = os_data.get("hostname", "Unknown")
    local_ip = os_data.get("local_ip", "127.0.0.1")
    uptime_seconds = os_data.get("uptime_seconds", 0.0)
    
    # Format anomalies list
    anomalies_html = ""
    anomalies = data.get("anomalies", [])
    if anomalies:
        for a in anomalies:
            severity = a.get("severity", "LOW").upper()
            badge_class = "badge-critical" if severity == "HIGH" else "badge-degraded" if severity == "MEDIUM" else "badge-healthy"
            anomalies_html += f"""
            <tr>
                <td><span class="badge {badge_class}">{severity}</span></td>
                <td style="font-weight: 600; color: #fff;">{a.get('metric', 'UNKNOWN').upper()}</td>
                <td>{a.get('description', '')}</td>
            </tr>
            """
    else:
        anomalies_html = "<tr><td colspan='3' style='text-align: center; color: #9ca3af;'>No telemetry anomalies or behavioral deviations detected.</td></tr>"

    # Format process list
    processes_html = ""
    for p in data.get("processes", []):
        processes_html += f"""
        <tr>
            <td style="color: #60a5fa; font-weight: 600;">{p.get('pid')}</td>
            <td style="color: #fff; font-weight: 500;">{p.get('name')}</td>
            <td><span class="badge badge-healthy">{p.get('cpu_percent')}%</span></td>
            <td><span class="badge" style="background: rgba(139, 92, 246, 0.15); color: #a78bfa;">{p.get('memory_percent')}%</span></td>
            <td style="color: #9ca3af;">{p.get('status')}</td>
        </tr>
        """
    if not processes_html:
        processes_html = "<tr><td colspan='5' style='text-align: center; color: #9ca3af;'>No process data available.</td></tr>"

    # Format Recommendations
    recs_html = ""
    # Retrieve dynamic suggestions
    from syslens.core.health import SystemHealthEngine
    engine = SystemHealthEngine()
    
    # Adapt partitions mapping for diagnosis
    disk_partitions = data.get("disk", {}).get("partitions", [])
    if not disk_partitions and "disk_usage" in data:
        disk_partitions = [{"mountpoint": "/", "usage_percent": data.get("disk_usage")}]
        
    mock_metrics = {
        "cpu": {"usage_percent": cpu},
        "memory": {"usage_percent": mem},
        "disk": {"partitions": disk_partitions},
        "anomalies": anomalies,
        "processes": data.get("processes", [])
    }
    diagnoses = engine.diagnose_issues(mock_metrics)
    recs = []
    for diag in diagnoses:
        recs.extend(diag.get("recommendations", []))
    
    # Unique recommendations
    unique_recs = []
    for r in recs:
        if r not in unique_recs:
            unique_recs.append(r)
            
    if unique_recs:
        for r in unique_recs:
            recs_html += f"<li>{r}</li>"
    else:
        recs_html = "<li>System parameters are stable. No diagnostics required.</li>"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SysLens Telemetry Diagnostics Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(17, 25, 40, 0.65);
            --card-border: rgba(255, 255, 255, 0.08);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
            --color-healthy: #10b981;
            --color-degraded: #f59e0b;
            --color-critical: #ef4444;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            background-image: radial-gradient(at 10% 20%, rgba(59, 130, 246, 0.1) 0px, transparent 50%),
                              radial-gradient(at 90% 80%, rgba(139, 92, 246, 0.08) 0px, transparent 50%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem;
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 1.5rem;
            border-bottom: 1px solid var(--card-border);
            margin-bottom: 2rem;
        }}
        h1, h2, h3 {{ font-family: 'Outfit', sans-serif; }}
        .header-title h1 {{ font-size: 1.75rem; font-weight: 700; color: #fff; }}
        .header-title p {{ font-size: 0.8rem; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 1px; margin-top: 0.25rem; }}
        .status-pill {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--card-border);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            color: var(--color-healthy);
        }}
        .status-pill.degraded {{ color: var(--color-degraded); }}
        .status-pill.critical {{ color: var(--color-critical); }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 1.5rem;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }}
        .col-4 {{ grid-column: span 4; }}
        .col-8 {{ grid-column: span 8; }}
        .col-12 {{ grid-column: span 12; }}
        .card-title {{ font-size: 1.1rem; font-weight: 600; color: #fff; margin-bottom: 1rem; border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 0.5rem; }}
        .metadata-row {{ display: flex; justify-content: space-between; margin-bottom: 0.75rem; font-size: 0.9rem; }}
        .metadata-row span:first-child {{ color: var(--text-secondary); }}
        .metadata-row span:last-child {{ color: #fff; font-weight: 500; }}
        .metric-progress {{ margin-bottom: 1rem; }}
        .progress-label {{ display: flex; justify-content: space-between; font-size: 0.85rem; margin-bottom: 0.4rem; }}
        .progress-outer {{ width: 100%; height: 8px; background: rgba(255, 255, 255, 0.05); border-radius: 4px; overflow: hidden; }}
        .progress-inner {{ height: 100%; background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%); border-radius: 4px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 0.85rem; }}
        th {{ color: var(--text-secondary); font-weight: 500; padding: 0.6rem; border-bottom: 1px solid var(--card-border); }}
        td {{ padding: 0.6rem; border-bottom: 1px solid rgba(255,255,255,0.02); color: var(--text-primary); }}
        .badge {{ padding: 0.15rem 0.4rem; border-radius: 4px; font-weight: 600; font-size: 0.75rem; text-transform: uppercase; }}
        .badge-healthy {{ background: rgba(16, 185, 129, 0.15); color: var(--color-healthy); }}
        .badge-degraded {{ background: rgba(245, 158, 11, 0.15); color: var(--color-degraded); }}
        .badge-critical {{ background: rgba(239, 68, 68, 0.15); color: var(--color-critical); }}
        .recs-list {{ padding-left: 1.25rem; font-size: 0.9rem; color: var(--text-secondary); }}
        .recs-list li {{ margin-bottom: 0.5rem; }}
    </style>
</head>
<body>
    <header>
        <div class="header-title">
            <h1>SysLens System Report</h1>
            <p>Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <div class="status-pill {'degraded' if status == 'DEGRADED' else 'critical' if status == 'CRITICAL' else ''}">
            OVERALL STATUS: {status} ({score:.0f}/100)
        </div>
    </header>
    <main class="grid">
        <div class="card col-4">
            <h2 class="card-title">Environment Metadata</h2>
            <div class="metadata-row"><span>Hostname</span><span>{hostname}</span></div>
            <div class="metadata-row"><span>Local IP</span><span>{local_ip}</span></div>
            <div class="metadata-row"><span>OS Platform</span><span>{os_name} {release}</span></div>
            <div class="metadata-row"><span>Architecture</span><span>{architecture}</span></div>
            <div class="metadata-row"><span>Uptime</span><span>{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m</span></div>
        </div>
        
        <div class="card col-4">
            <h2 class="card-title">Hardware Telemetry</h2>
            <div class="metric-progress">
                <div class="progress-label"><span>CPU Usage</span><span>{cpu:.1f}%</span></div>
                <div class="progress-outer"><div class="progress-inner" style="width: {cpu}%;"></div></div>
            </div>
            <div class="metric-progress">
                <div class="progress-label"><span>Memory Usage</span><span>{mem:.1f}%</span></div>
                <div class="progress-outer"><div class="progress-inner" style="width: {mem}%; background: linear-gradient(135deg, #a78bfa 0%, #8b5cf6 100%);"></div></div>
            </div>
        </div>
        
        <div class="card col-4">
            <h2 class="card-title">Diagnostic Recommendations</h2>
            <ul class="recs-list">
                {recs_html}
            </ul>
        </div>
        
        <div class="card col-4">
            <h2 class="card-title">Live Anomalies</h2>
            <table>
                <thead>
                    <tr><th>Severity</th><th>Metric</th><th>Description</th></tr>
                </thead>
                <tbody>
                    {anomalies_html}
                </tbody>
            </table>
        </div>
        
        <div class="card col-8">
            <h2 class="card-title">Active Processes</h2>
            <table>
                <thead>
                    <tr><th>PID</th><th>Name</th><th>CPU Usage</th><th>Memory Usage</th><th>Status</th></tr>
                </thead>
                <tbody>
                    {processes_html}
                </tbody>
            </table>
        </div>
    </main>
</body>
</html>"""
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
