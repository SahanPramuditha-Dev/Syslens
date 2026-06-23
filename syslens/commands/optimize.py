"""
``syslens optimize`` — Profile-based smart optimizer: cleanup + auto-fix + rollback.
"""
from syslens.commands._shared import (
    ARROW_ICON,
    BULLET,
    CHECK_ICON,
    CLEAN_ICON,
    DIAL_ICON,
    GEAR_ICON,
    LIGHTNING_ICON,
    LINE_CHAR,
    console,
)


def run(profile: str = "safe", dry_run: bool = False) -> None:
    """Run the SysLens Smart Auto-Optimizer for the given profile."""
    from syslens.optimizer.engine import optimize

    console.print()
    title_suffix = " - DRY RUN" if dry_run else ""
    console.rule(
        f"[bold cyan]{LIGHTNING_ICON}SYSLENS SMART OPTIMIZER v1.6 (Profile: {profile.upper()}{title_suffix})[/bold cyan]",
        characters=LINE_CHAR,
    )
    console.print()

    res        = optimize(mode=profile, dry_run=dry_run)
    results    = res.get("results", [])
    cleanup_data = results[0] if len(results) > 0 else []
    autofix_data = results[1] if len(results) > 1 else []
    profile_data = results[2] if len(results) > 2 else {}

    action_verb = "Would clear" if dry_run else "Cleared"

    # 1. Cleanup summary
    console.print(f"  [bold green]{CLEAN_ICON}CLEANUP EXECUTED[/bold green]")
    temp_removed = 0
    rb_success   = False
    dev_cleaned  = 0
    for r in cleanup_data:
        if r.get("task") == "TEMP_CLEAN":
            temp_removed = r.get("files_removed", 0)
        elif r.get("task") == "RECYCLE_BIN":
            if r.get("status") in ("completed", "dry_run"):
                rb_success = True
        elif r.get("task") == "DEV_CACHE_CLEAN":
            dev_cleaned = r.get("folders_cleaned", 0)
            
    console.print(f"  [green]{CHECK_ICON}[/green] Temp files: {action_verb.lower()} {temp_removed} files")
    if rb_success:
        rb_verb = "Would empty" if dry_run else "Emptied"
        console.print(f"  [green]{CHECK_ICON}[/green] Recycle bin: {rb_verb.lower()} successfully")
    else:
        console.print(f"  [yellow]{BULLET}[/yellow] Recycle bin skipped or empty")
    console.print(f"  [green]{CHECK_ICON}[/green] Developer caches: {action_verb.lower()} {dev_cleaned} folders (node_modules, pycache, pytest)")
    console.print()

    # 2. Auto-fix summary
    console.print(f"  [bold yellow]{GEAR_ICON}AUTO-FIX SUMMARY[/bold yellow]")
    if autofix_data:
        for fix in autofix_data:
            fix_status = "would trigger" if dry_run else "triggered"
            console.print(f"  [green]{BULLET}[/green] {fix.get('fix', '')} ({fix_status})")
    else:
        console.print(f"  [green]{BULLET}[/green] System resources stable, no resource spikes detected")
    console.print()

    # 3. Profile details
    profile_verb = "Would apply" if dry_run else "Applied"
    console.print(f"  [bold blue]{DIAL_ICON}PROFILE: {profile.upper()} MODE ({profile_verb})[/bold blue]")
    for k, v in profile_data.items():
        k_display  = k.replace("_", " ").capitalize()
        val_display = (
            "[green]Enabled[/green]"  if v is True  else
            "[red]Disabled[/red]"     if v is False else
            f"[cyan]{v}[/cyan]"
        )
        console.print(f"  [blue]{BULLET}[/blue] {k_display}: {val_display}")
    console.print()

    # 4. Rollback notice
    if dry_run:
        console.print(f"  [bold magenta]{ARROW_ICON}ROLLBACK: NOT APPLICABLE[/bold magenta]")
        console.print("  Dry run audits are not stored in optimization history")
    else:
        console.print(f"  [bold magenta]{ARROW_ICON}ROLLBACK: AVAILABLE[/bold magenta]")
        console.print("  Last action stored safely in system history")
    console.print()
    
    if dry_run:
        from syslens.commands._shared import supports_unicode
        warn_symbol = "⚠" if supports_unicode() else "WARNING:"
        console.print(f"[yellow]{warn_symbol} DRY RUN MODE - No system configurations or files were actually modified.[/yellow]")
        console.print()
        
    console.rule(f"[bold cyan]{LINE_CHAR * 30}[/bold cyan]", characters=LINE_CHAR)
    console.print()
