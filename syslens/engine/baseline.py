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
        self.history: List[Dict[str, Any]] = []
        self.stats: Dict[str, Dict[str, float]] = {
            "cpu": {"mean": 20.0, "std": 10.0},
            "memory": {"mean": 50.0, "std": 15.0},
            "disk_read_rate": {"mean": 50000.0, "std": 100000.0},  # Bytes/sec
            "disk_write_rate": {"mean": 50000.0, "std": 100000.0},
            "active_connections": {"mean": 25.0, "std": 10.0},
            "gpu_utilization": {"mean": 10.0, "std": 10.0},
            "swap_usage_percent": {"mean": 10.0, "std": 10.0}
        }
        self.diurnal_stats: Dict[str, Dict[str, Dict[str, float]]] = {}
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
                        self.diurnal_stats = data.get("diurnal_stats", {})
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
                        "history": self.history,
                        "diurnal_stats": self.diurnal_stats
                    }, f, indent=4)
            except Exception:
                pass

    def update(self, current_metrics: Dict[str, Any]) -> None:
        """Incorporate current metrics to refine the system baseline model."""
        with self._lock:
            timestamp = current_metrics.get("timestamp", 0.0) or time.time()
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

            # Local hour
            import time as pytime
            local_hour = pytime.localtime(timestamp).tm_hour

            # Broader metrics
            net_conn = current_metrics.get("plugins_data", {}).get("network_telemetry", {}).get("active_connections", 0.0)
            gpu_data = current_metrics.get("plugins_data", {}).get("gpu_analyzer", {})
            gpu_util = gpu_data.get("utilization_gpu_percent", 0.0) if gpu_data and gpu_data.get("available") else 0.0
            swap_pct = current_metrics.get("memory", {}).get("swap_usage_percent", 0.0)

            # Record metric point
            point = {
                "hour": local_hour,
                "cpu": cpu_usage,
                "memory": mem_usage,
                "disk_read_rate": read_rate,
                "disk_write_rate": write_rate,
                "active_connections": float(net_conn),
                "gpu_utilization": float(gpu_util),
                "swap_usage_percent": float(swap_pct)
            }
            self.history.append(point)

            # Truncate to maximum history window
            if len(self.history) > self.max_history:
                self.history.pop(0)

            # Recalculate stats if we have sufficient samples (e.g. >= 10 points)
            if len(self.history) >= 10:
                # 1. Recalculate global stats
                for key in self.stats.keys():
                    values = [p[key] for p in self.history if key in p]
                    if not values:
                        continue
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

                # 2. Recalculate diurnal stats
                self.diurnal_stats = {}
                points_by_hour = {}
                for p in self.history:
                    h = p.get("hour")
                    if h is not None:
                        points_by_hour.setdefault(str(h), []).append(p)

                for h_str, h_points in points_by_hour.items():
                    if len(h_points) >= 10:
                        self.diurnal_stats[h_str] = {}
                        for key in self.stats.keys():
                            values = [p[key] for p in h_points if key in p]
                            if not values:
                                continue
                            mean = sum(values) / len(values)
                            variance = sum((v - mean) ** 2 for v in values) / len(values)
                            std = math.sqrt(variance)
                            std = max(std, 1.0 if "rate" not in key else 1000.0)
                            self.diurnal_stats[h_str][key] = {
                                "mean": round(mean, 2),
                                "std": round(std, 2)
                            }

            self.save()

    def get_stats(self, hour: int = None) -> Dict[str, Dict[str, float]]:
        """Get baseline statistics. Falls back to global stats if insufficient diurnal data."""
        with self._lock:
            if hour is None:
                import time as pytime
                hour = pytime.localtime().tm_hour
            
            hour_str = str(hour)
            if hasattr(self, "diurnal_stats") and hour_str in self.diurnal_stats:
                # Merge diurnal stats with global stats for any keys missing in diurnal
                res = self.stats.copy()
                res.update(self.diurnal_stats[hour_str])
                return res
            return self.stats
