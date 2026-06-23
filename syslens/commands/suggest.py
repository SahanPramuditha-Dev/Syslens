"""
``syslens suggest`` — System optimization report with risk-rated actions.
"""
from syslens.commands._shared import (
    BULLET,
    ERROR_ICON,
    LINE_CHAR,
    OK_ICON,
    WARN_ICON,
    console,
    supports_unicode,
)


def run(anomaly_interface) -> None:
    """Evaluate system state and print a ranked optimization suggestions report."""
    from syslens.engine.suggester import generate_suggestions

    metrics     = anomaly_interface.scan_system()
    suggestions = generate_suggestions(metrics)

    console.print()
    console.rule("[bold yellow]💡 SYSTEM OPTIMIZATION REPORT[/bold yellow]", characters="━")
    console.print()

    if not suggestions:
        console.print("[bold green]✓ System is fully optimized. No bottlenecks or cleanup recommendations detected![/bold green]")
        console.print()
        console.print("  [grey50]Tip: Run 'syslens live' to watch performance telemetry in real-time.[/grey50]")
        console.print()
        return

    _U = supports_unicode()
    icons = {
        "STORAGE": "🗂️ STORAGE ISSUE DETECTED" if _U else "STORAGE ISSUE DETECTED",
        "CPU":     "⚙️ CPU ISSUE DETECTED"     if _U else "CPU ISSUE DETECTED",
        "MEMORY":  "🧠 MEMORY ISSUE DETECTED"  if _U else "MEMORY ISSUE DETECTED",
        "NETWORK": "🌐 NETWORK ISSUE DETECTED" if _U else "NETWORK ISSUE DETECTED",
        "BATTERY": "🔋 BATTERY ISSUE DETECTED" if _U else "BATTERY ISSUE DETECTED",
        "CLEANUP": "🧹 SYSTEM CLEANUP RECOMMENDED" if _U else "SYSTEM CLEANUP RECOMMENDED",
    }
    risk_colors = {
        "SAFE":      f"[green]{OK_ICON}SAFE[/green]"          if _U else "[green]SAFE[/green]",
        "MEDIUM":    f"[yellow]{WARN_ICON}MEDIUM[/yellow]"    if _U else "[yellow]MEDIUM[/yellow]",
        "HIGH RISK": f"[red]{ERROR_ICON}HIGH RISK[/red]"      if _U else "[red]HIGH RISK[/red]",
    }

    for i, sug in enumerate(suggestions):
        cat_header = icons.get(sug["category"], f"⚠️ {sug['category']} ISSUE DETECTED" if _U else f"{sug['category']} ISSUE DETECTED")
        console.print(f"[bold yellow]{cat_header}[/bold yellow]")
        console.print(f"[white]{sug['issue']}[/white]\n")
        console.print("[bold cyan]Actions:[/bold cyan]")
        for act in sug["actions"]:
            risk_str = risk_colors.get(act["risk"], f"[{act['risk']}]")
            console.print(f" • {act['name']:<50} {risk_str}")
        if i < len(suggestions) - 1:
            console.print()
            console.print("[grey37]" + "─" * 40 + "[/]")
            console.print()

    console.print()
    console.rule(f"[bold yellow]{LINE_CHAR * 30}[/bold yellow]", characters=" ")
    console.print()
    console.print("  [bold]Recommendation:[/bold] Run [bold white]syslens optimize[/bold white] to execute all [green]SAFE[/green] cleanup tasks automatically.")
    console.print()
