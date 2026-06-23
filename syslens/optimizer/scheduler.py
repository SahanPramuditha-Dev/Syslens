import time
from threading import Thread
from syslens.cleaner.engine import run_cleanup

# Global reference to running scheduler thread and control flag
_scheduler_thread = None
_scheduler_running = False

def schedule_cleanup(interval=3600):
    """
    Schedules clean_temp_files and empty_recycle_bin in a daemon thread.
    Cancels any existing scheduler thread before starting.
    """
    global _scheduler_thread, _scheduler_running

    # Stop existing running scheduler
    if _scheduler_running:
        _scheduler_running = False
        time.sleep(0.1) # brief pause to let thread exit

    _scheduler_running = True

    def loop():
        global _scheduler_running
        while _scheduler_running:
            try:
                run_cleanup(mode="safe")
            except Exception:
                pass
            
            # Sleep in small increments to allow responsive stopping
            slept = 0
            while slept < interval and _scheduler_running:
                time.sleep(1)
                slept += 1

    _scheduler_thread = Thread(target=loop, daemon=True)
    _scheduler_thread.start()

    return {
        "status": "scheduler_started",
        "interval_seconds": interval
    }

def stop_scheduler():
    """Stops the active scheduler thread."""
    global _scheduler_running
    if _scheduler_running:
        _scheduler_running = False
        return {"status": "scheduler_stopped"}
    return {"status": "scheduler_not_running"}
