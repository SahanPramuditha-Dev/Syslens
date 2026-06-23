import time
from typing import Dict, Any, List
from syslens.engine.baseline import BehaviorBaseline

class AnomalyDetector:
    """Evaluates real-time telemetry against the learned baseline to identify behavior deviations."""

    def __init__(self, baseline: BehaviorBaseline = None):
        self.baseline = baseline or BehaviorBaseline()

    def analyze(self, current_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compare current telemetry against the baseline to return detected anomalies."""
        anomalies = []
        stats = self.baseline.get_stats()

        cpu_usage = current_metrics.get("cpu", {}).get("usage_percent", 0.0)
        mem_usage = current_metrics.get("memory", {}).get("usage_percent", 0.0)
        
        # CPU Anomaly
        cpu_baseline = stats.get("cpu", {"mean": 20.0, "std": 10.0})
        cpu_mean = cpu_baseline["mean"]
        cpu_std = cpu_baseline["std"]
        
        # Calculate deviation (z-score)
        cpu_z = (cpu_usage - cpu_mean) / cpu_std if cpu_std > 0 else 0
        if cpu_z > 2.0 or cpu_usage > 85.0:
            severity = "LOW"
            if cpu_z > 3.5 or cpu_usage > 90.0:
                severity = "HIGH"
            elif cpu_z > 2.5 or cpu_usage > 75.0:
                severity = "MEDIUM"

            anomalies.append({
                "metric": "cpu_usage",
                "current_value": cpu_usage,
                "baseline_mean": cpu_mean,
                "deviation_z": round(cpu_z, 2),
                "severity": severity,
                "timestamp": time.time(),
                "description": f"CPU usage ({cpu_usage}%) deviates from baseline mean ({cpu_mean}%)."
            })

        # Memory Anomaly
        mem_baseline = stats.get("memory", {"mean": 50.0, "std": 15.0})
        mem_mean = mem_baseline["mean"]
        mem_std = mem_baseline["std"]
        mem_z = (mem_usage - mem_mean) / mem_std if mem_std > 0 else 0

        if mem_z > 2.0 or mem_usage > 85.0:
            severity = "LOW"
            if mem_z > 3.0 or mem_usage > 90.0:
                severity = "HIGH"
            elif mem_z > 2.3 or mem_usage > 80.0:
                severity = "MEDIUM"

            anomalies.append({
                "metric": "memory_usage",
                "current_value": mem_usage,
                "baseline_mean": mem_mean,
                "deviation_z": round(mem_z, 2),
                "severity": severity,
                "timestamp": time.time(),
                "description": f"Memory usage ({mem_usage}%) deviates from baseline mean ({mem_mean}%)."
            })

        # Disk I/O Anomalies
        # Calculate rates using the history if available
        if len(self.baseline.history) >= 2:
            last_point = self.baseline.history[-1]
            read_rate = last_point.get("disk_read_rate", 0.0)
            write_rate = last_point.get("disk_write_rate", 0.0)

            # Read rate deviation
            read_baseline = stats.get("disk_read_rate", {"mean": 50000.0, "std": 100000.0})
            read_mean = read_baseline["mean"]
            read_std = read_baseline["std"]
            read_z = (read_rate - read_mean) / read_std if read_std > 0 else 0

            if read_z > 3.0:
                severity = "HIGH" if read_z > 5.0 else "MEDIUM"
                anomalies.append({
                    "metric": "disk_read_rate",
                    "current_value": round(read_rate / 1024 / 1024, 2),  # MB/s
                    "baseline_mean": round(read_mean / 1024 / 1024, 2),
                    "deviation_z": round(read_z, 2),
                    "severity": severity,
                    "timestamp": time.time(),
                    "description": f"Disk Read rate ({round(read_rate/1024/1024, 2)} MB/s) exceeds baseline mean ({round(read_mean/1024/1024, 2)} MB/s)."
                })

            # Write rate deviation
            write_baseline = stats.get("disk_write_rate", {"mean": 50000.0, "std": 100000.0})
            write_mean = write_baseline["mean"]
            write_std = write_baseline["std"]
            write_z = (write_rate - write_mean) / write_std if write_std > 0 else 0

            if write_z > 3.0:
                severity = "HIGH" if write_z > 5.0 else "MEDIUM"
                anomalies.append({
                    "metric": "disk_write_rate",
                    "current_value": round(write_rate / 1024 / 1024, 2),  # MB/s
                    "baseline_mean": round(write_mean / 1024 / 1024, 2),
                    "deviation_z": round(write_z, 2),
                    "severity": severity,
                    "timestamp": time.time(),
                    "description": f"Disk Write rate ({round(write_rate/1024/1024, 2)} MB/s) exceeds baseline mean ({round(write_mean/1024/1024, 2)} MB/s)."
                })

        # Multi-Metric Correlations (behavior-based alerts)
        cpu_anomaly = next((a for a in anomalies if a["metric"] == "cpu_usage"), None)
        mem_anomaly = next((a for a in anomalies if a["metric"] == "memory_usage"), None)
        disk_read_anomaly = next((a for a in anomalies if a["metric"] == "disk_read_rate"), None)
        disk_write_anomaly = next((a for a in anomalies if a["metric"] == "disk_write_rate"), None)

        if cpu_anomaly and mem_anomaly:
            # Correlated CPU + Memory exhaustion
            correlation_severity = "HIGH" if (cpu_anomaly["severity"] == "HIGH" or mem_anomaly["severity"] == "HIGH") else "MEDIUM"
            anomalies.append({
                "metric": "correlated_cpu_memory_stress",
                "current_value": {"cpu": cpu_usage, "memory": mem_usage},
                "baseline_mean": {"cpu": cpu_mean, "memory": mem_mean},
                "deviation_z": max(cpu_anomaly["deviation_z"], mem_anomaly["deviation_z"]),
                "severity": correlation_severity,
                "timestamp": time.time(),
                "description": "System Congestion: Correlated high CPU usage and Memory pressure detected simultaneously."
            })

        if cpu_anomaly and (disk_read_anomaly or disk_write_anomaly):
            # Disk IO blocking CPU
            anomalies.append({
                "metric": "correlated_io_wait_cpu_stress",
                "current_value": cpu_usage,
                "baseline_mean": cpu_mean,
                "deviation_z": cpu_anomaly["deviation_z"],
                "severity": "MEDIUM",
                "timestamp": time.time(),
                "description": "I/O Bound CPU Overhead: High CPU utilization coinciding with abnormal Disk I/O activity."
            })

        return anomalies

    def tick(self) -> List[Dict[str, Any]]:
        """Run system metrics collection, update baseline, and returns active anomalies."""
        from syslens.core.system import SystemMetricsCollector
        collector = SystemMetricsCollector()
        metrics = collector.collect_all()
        
        # Update baseline
        self.baseline.update(metrics)
        
        # Analyze and return anomalies
        return self.analyze(metrics)
