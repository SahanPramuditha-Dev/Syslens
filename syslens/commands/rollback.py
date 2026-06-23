"""
``syslens rollback`` — Rollback the last recorded optimization action.
"""
from syslens.commands._shared import ARROW_ICON, BULLET, CHECK_ICON, LINE_CHAR, console


def run() -> None:
    """Rollback the last optimization action stored in the history log."""
    from syslens.optimizer.rollback import rollback_last

    console.print()
    console.rule(f"[bold red]{ARROW_ICON}SYSLENS ROLLBACK UTILITY[/bold red]", characters=LINE_CHAR)
    console.print()

    res    = rollback_last()
    status = res.get("status")

    if status == "no_actions_to_rollback":
        console.print("  [yellow]⚠ No actions available in history to rollback.[/yellow]")
    else:
        reverted = res.get("details", [])
        console.print(f"  [bold green]{ARROW_ICON}ROLLBACK: EXECUTED[/bold green]")
        if reverted:
            for change in reverted:
                console.print(f"  [green]{CHECK_ICON}[/green] {change}")
        else:
            console.print(f"  [green]{CHECK_ICON}[/green] Last transaction reverted successfully")

        action_info = res.get("reverted_action", {})
        console.print(f"  [grey37]Mode rolled back: {action_info.get('mode')}[/grey37]")

    console.print()
    console.rule(f"[bold red]{LINE_CHAR * 30}[/bold red]", characters=LINE_CHAR)
    console.print()
