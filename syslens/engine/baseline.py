import json
import os
import math
import threading
from typing import Dict, Any, List

class BehaviorBaseline:
    """Maintains a baseline model representing 'normal' system telemetry patterns."""

    def __init__(self, filepath: str = None):
        self._lock = threading.RLock()
        
        if filepath is None:
            home = os.path.expanduser("~")
            self.dirpath = os.path.join(home, ".syslens")
            self.filepath = os.path.join(self.dirpath, "baseline.json")
        else:
            self.filepath = filepath
            self.dirpath = os.path.dirname(filepath)

        self.max_history = 120  # Store last 120 samples (~2 mins if 1s intervals)
        self.history: List[Dict[str, float]] = []
        self.stats: Dict[str, Dict[str, float]] = {
            "cpu": {"mean": 20.0, "std": 10.0},
            "memory": {"mean": 50.0, "std": 15.0},
            "disk_read_rate": {"mean": 50000.0, "std": 100000.0},  # Bytes/sec
            "disk_write_rate": {"mean": 50000.0, "std": 100000.0}
        }
        self.last_disk_read = 0.0
        self.last_disk_write = 0.0
        self.last_timestamp = 0.0

        self.load()

    def load(self) -> None:
        """Load baseline stats and history from disk if they exist."""
        with self._lock:
            if os.path.exists(self.filepath):
                try:
                    with open(self.filepath, "r") as f:
                        data = json.load(f)
                        self.stats = data.get("stats", self.stats)
                        self.history = data.get("history", [])
                except Exception:
                    # Fallback to defaults on corrupt load
                    pass

    def save(self) -> None:
        """Persist current baseline stats and history to disk."""
        with self._lock:
            try:
                if self.dirpath and not os.path.exists(self.dirpath):
                    os.makedirs(self.dirpath, exist_ok=True)
                with open(self.filepath, "w") as f:
                    json.dump({
                        "stats": self.stats,
                        "history": self.history
                    }, f, indent=4)
            except Exception:
                pass

    def update(self, current_metrics: Dict[str, Any]) -> None:
        """Incorporate current metrics to refine the system baseline model."""
        with self._lock:
            timestamp = current_metrics.get("timestamp", 0.0)
            cpu_usage = current_metrics.get("cpu", {}).get("usage_percent", 0.0)
            mem_usage = current_metrics.get("memory", {}).get("usage_percent", 0.0)
            
            disk = current_metrics.get("disk", {})
            curr_read = disk.get("read_bytes", 0.0)
            curr_write = disk.get("write_bytes", 0.0)

            # Calculate read/write rate in bytes per second
            read_rate = 0.0
            write_rate = 0.0
            if self.last_timestamp > 0.0 and timestamp > self.last_timestamp:
                dt = timestamp - self.last_timestamp
                if curr_read >= self.last_disk_read:
                    read_rate = (curr_read - self.last_disk_read) / dt
                if curr_write >= self.last_disk_write:
                    write_rate = (curr_write - self.last_disk_write) / dt

            self.last_timestamp = timestamp
            self.last_disk_read = curr_read
            self.last_disk_write = curr_write

            # Record metric point
            point = {
                "cpu": cpu_usage,
                "memory": mem_usage,
                "disk_read_rate": read_rate,
                "disk_write_rate": write_rate
            }
            self.history.append(point)

            # Truncate to maximum history window
            if len(self.history) > self.max_history:
                self.history.pop(0)

            # Recalculate stats if we have sufficient samples (e.g. >= 10 points)
            if len(self.history) >= 10:
                for key in self.stats.keys():
                    values = [p[key] for p in self.history]
                    mean = sum(values) / len(values)
                    # Compute standard deviation
                    variance = sum((v - mean) ** 2 for v in values) / len(values)
                    std = math.sqrt(variance)
                    # Avoid zero standard deviation
                    std = max(std, 1.0 if "rate" not in key else 1000.0)
                    
                    self.stats[key] = {
                        "mean": round(mean, 2),
                        "std": round(std, 2)
                    }

            self.save()

    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Get baseline statistics."""
        with self._lock:
            return self.stats
