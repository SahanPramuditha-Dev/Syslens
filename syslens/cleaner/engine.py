from syslens.cleaner.temp_cleaner import clean_temp_files
from syslens.cleaner.recycle_bin import empty_recycle_bin
from syslens.cleaner.browser_cleaner import clean_browser_cache
from syslens.cleaner.disk_optimizer import analyze_disk
from syslens.cleaner.dev_cache import clean_dev_caches

def run_cleanup(mode="safe", dry_run=False):
    """
    Executes cleanup tasks depending on the mode.
    Modes:
    - safe: temp cleaner + recycle bin + dev cache cleaner + disk analysis
    - full: temp cleaner + recycle bin + dev cache cleaner + browser cache cleaner + disk analysis
    """
    results = []

    # SAFE ACTIONS: Temp cleaner is always run
    results.append(clean_temp_files(dry_run=dry_run))

    # RECYCLE BIN: Emptied on all modes (safe but trackable)
    results.append(empty_recycle_bin(dry_run=dry_run))

    # DEV CACHES: Always run (safe check targets unmodified stale cache files)
    results.append(clean_dev_caches(dry_run=dry_run, age_days=7))

    # BROWSER CACHE: Run only in 'full' mode to avoid clearing user browsing caches on 'safe'
    if mode == "full":
        results.append(clean_browser_cache(dry_run=dry_run))

    # DISK ANALYSIS: Run on all modes (non-destructive check)
    results.append(analyze_disk())

    return results
