"""
``syslens clean`` — Auto-cleaner: temp files, recycle bin, browser cache, disk analysis.
"""
from syslens.commands._shared import (
    CLEAN_ICON,
    DISK_ICON,
    ERROR_ICON,
    LINE_CHAR,
    OK_ICON,
    WARN_ICON,
    console,
)


def run(mode: str = "safe", dry_run: bool = False) -> None:
    """Run the SysLens Auto Cleaner Engine in the given mode (safe | full)."""
    from syslens.cleaner.engine import run_cleanup
    from syslens.utils.format import format_bytes

    console.print()
    title_suffix = " (DRY RUN)" if dry_run else ""
    console.rule(f"[bold green]{CLEAN_ICON}SYSLENS AUTO CLEANER REPORT{title_suffix}[/bold green]", characters=LINE_CHAR)
    console.print()

    results = run_cleanup(mode=mode, dry_run=dry_run)

    temp_files_removed = 0
    temp_bytes_freed   = 0
    recycle_bin_note   = "Skipped (Non-Windows)"
    recycle_bin_status = "Skipped"
    browser_cleaned    = 0
    browser_bytes      = 0
    dev_cache_cleaned  = 0
    dev_cache_bytes    = 0
    disk_used_pct      = 0
    disk_rec           = "Run cleanup if usage > 85%"

    for r in results:
        task = r.get("task")
        if task == "TEMP_CLEAN":
            temp_files_removed = r.get("files_removed", 0)
            temp_bytes_freed   = r.get("bytes_freed", 0)
        elif task == "RECYCLE_BIN":
            recycle_bin_status = r.get("status")
            recycle_bin_note   = r.get("note") or r.get("error", "Unknown error")
        elif task == "BROWSER_CACHE":
            browser_cleaned = r.get("folders_cleaned", 0)
            browser_bytes   = r.get("bytes_freed", 0)
        elif task == "DEV_CACHE_CLEAN":
            dev_cache_cleaned = r.get("folders_cleaned", 0)
            dev_cache_bytes   = r.get("bytes_freed", 0)
        elif task == "DISK_ANALYSIS":
            disk_used_pct = r.get("used_percent", 0)
            disk_rec      = r.get("recommendation", "")

    action_verb = "Would remove" if dry_run else "Removed"

    console.print(f"  [bold green]{OK_ICON}TEMP FILES CLEANED[/bold green]")
    console.print(f"  Files: {action_verb} {temp_files_removed} ({format_bytes(temp_bytes_freed)})")
    console.print()

    # Recycle Bin
    if recycle_bin_status == "dry_run":
        console.print(f"  [bold yellow]{WARN_ICON}RECYCLE BIN[/bold yellow]")
        console.print(f"  Status: {recycle_bin_note}")
    elif recycle_bin_status == "completed":
        console.print(f"  [bold green]{OK_ICON}RECYCLE BIN CLEARED[/bold green]")
        console.print("  Status: Completed successfully")
    elif recycle_bin_status == "failed":
        console.print(f"  [bold red]{ERROR_ICON}RECYCLE BIN CLEARED[/bold red]")
        console.print(f"  Status: Failed ({recycle_bin_note})")
    else:
        console.print(f"  [bold yellow]{WARN_ICON}RECYCLE BIN CLEARED[/bold yellow]")
        console.print(f"  Status: {recycle_bin_note}")
    console.print()

    # Developer Caches
    console.print(f"  [bold green]{OK_ICON}DEVELOPER CACHES CLEANED[/bold green]")
    console.print(f"  Folders: {action_verb} {dev_cache_cleaned} (node_modules, .pytest_cache, __pycache__)")
    console.print(f"  Bytes: {action_verb.lower()} {format_bytes(dev_cache_bytes)}")
    console.print()

    if mode == "full":
        console.print(f"  [bold yellow]{WARN_ICON}BROWSER CACHE[/bold yellow]")
        console.print(f"  Folders: {action_verb} {browser_cleaned} (Chrome, Edge)")
        console.print(f"  Bytes: {action_verb.lower()} {format_bytes(browser_bytes)}")
        console.print()

    disk_color = "green" if disk_used_pct <= 70 else "yellow" if disk_used_pct <= 85 else "red"
    console.print(f"  [bold blue]{DISK_ICON}DISK STATUS[/bold blue]")
    console.print(f"  Used: [{disk_color}]{disk_used_pct}%[/{disk_color}]")
    console.print(f"  Recommendation: {disk_rec}")
    console.print()

    if dry_run:
        from syslens.commands._shared import supports_unicode
        warn_symbol = "⚠" if supports_unicode() else "WARNING:"
        console.print(f"[yellow]{warn_symbol} DRY RUN MODE - No files were actually deleted.[/yellow]")
        console.print()

    console.rule(f"[bold green]{LINE_CHAR * 30}[/bold green]", characters=LINE_CHAR)
    console.print()
