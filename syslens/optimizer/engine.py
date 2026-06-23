import time
from syslens.cleaner.engine import run_cleanup
from syslens.optimizer.auto_fix import apply_safe_fixes
from syslens.optimizer.profiles import get_profile, get_active_power_scheme, set_active_power_scheme
from syslens.optimizer.rollback import log_action

def optimize(mode="safe", cpu_override=None, mem_override=None, dry_run=False):
    """
    Runs full system optimization pipeline:
    1. Executes safe cleanups.
    2. Applies safe CPU/Memory auto-fixes.
    3. Tunes profiles (e.g. power plans).
    4. Logs action parameters to history for rollback (skipped on dry run).
    """
    results = []

    # Capture current Windows power scheme before modifying
    prev_power = get_active_power_scheme()

    # Step 1: Run cleanup
    results.append(run_cleanup(mode="safe", dry_run=dry_run))

    # Step 2: Apply safe system auto-fixes
    results.append(apply_safe_fixes(cpu_override=cpu_override, mem_override=mem_override, dry_run=dry_run))

    # Step 3: Apply profile tuning
    profile = get_profile(mode)
    results.append(profile)

    # Set power plan based on profile (skip on dry run)
    power_mode = profile.get("power_mode")
    if power_mode and not dry_run:
        if power_mode == "high_performance":
            set_active_power_scheme("SCHEME_MIN")
        elif power_mode == "power_saver":
            set_active_power_scheme("SCHEME_MAX")
        elif power_mode == "balanced":
            set_active_power_scheme("SCHEME_BALANCED")

    # Record action for rollback capability (skip on dry run)
    if not dry_run:
        action_log = {
            "timestamp": time.time(),
            "mode": mode,
            "previous_power_scheme": prev_power,
            "results": results
        }
        log_action(action_log)

    return {
        "status": "dry_run" if dry_run else "completed",
        "mode": mode,
        "results": results
    }
