"""
``syslens schedule`` — Background cleanup scheduler at configurable intervals.
"""
from syslens.commands._shared import CLOCK_ICON, LINE_CHAR, console


def run(interval: int = 3600) -> None:
    """Schedule background cleanup at *interval* seconds and report status."""
    from syslens.optimizer.scheduler import schedule_cleanup

    console.print()
    console.rule(f"[bold yellow]{CLOCK_ICON}SYSLENS CLEANUP SCHEDULER[/bold yellow]", characters=LINE_CHAR)
    console.print()

    schedule_cleanup(interval=interval)

    console.print(f"  [bold green]{CLOCK_ICON}SCHEDULER: ACTIVE[/bold green]")
    console.print(f"  Cleanup routine scheduled every [cyan]{interval}[/cyan] seconds.")
    console.print("  Running in background daemon thread.")
    console.print()
    console.rule(f"[bold yellow]{LINE_CHAR * 30}[/bold yellow]", characters=LINE_CHAR)
    console.print()
