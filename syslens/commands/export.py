"""
``syslens export`` — Export a telemetry snapshot to a glassmorphic HTML report.
"""
from syslens.commands._shared import CHECK_MARK, console, gather_metrics


def run(anomaly_interface, plugin_manager, health_engine, output: str = "syslens_report.html") -> None:
    """Collect metrics and export them to an HTML report file."""
    from syslens.utils.format import export_html_report

    metrics = gather_metrics(anomaly_interface, plugin_manager, health_engine)
    export_html_report(metrics, output)
    console.print(
        f"[green]{CHECK_MARK} Exported SysLens HTML Report to: [bold]{output}[/bold][/green]"
    )
