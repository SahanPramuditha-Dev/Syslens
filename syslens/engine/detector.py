import time
from typing import Dict, Any, List
from syslens.engine.baseline import BehaviorBaseline

class AnomalyDetector:
    """Evaluates real-time telemetry against the learned baseline to identify behavior deviations."""

    def __init__(self, baseline: BehaviorBaseline = None):
        self.baseline = baseline or BehaviorBaseline()
        from syslens.utils.config import load_config
        self.config = load_config()

    def analyze(self, current_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Compare current telemetry against the baseline to return detected anomalies."""
        anomalies = []
        
        # Get hour from current_metrics timestamp for time-aware baseline query
        timestamp = current_metrics.get("timestamp", 0.0)
        hour = None
        if timestamp > 0.0:
            try:
                import time as pytime
                hour = pytime.localtime(timestamp).tm_hour
            except Exception:
                pass
        
        stats = self.baseline.get_stats(hour)

        cpu_usage = current_metrics.get("cpu", {}).get("usage_percent", 0.0)
        mem_usage = current_metrics.get("memory", {}).get("usage_percent", 0.0)
        
        # CPU Anomaly
        cpu_baseline = stats.get("cpu", {"mean": 20.0, "std": 10.0})
        cpu_mean = cpu_baseline["mean"]
        cpu_std = cpu_baseline["std"]
        
        # Calculate deviation (z-score)
        cpu_z = (cpu_usage - cpu_mean) / cpu_std if cpu_std > 0 else 0
        if cpu_z > self.config.get("cpu_z_low", 2.0) or cpu_usage > self.config.get("cpu_usage_low", 85.0):
            severity = "LOW"
            if cpu_z > self.config.get("cpu_z_high", 3.5) or cpu_usage > self.config.get("cpu_usage_high", 90.0):
                severity = "HIGH"
            elif cpu_z > self.config.get("cpu_z_medium", 2.5) or cpu_usage > self.config.get("cpu_usage_medium", 75.0):
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

        if mem_z > self.config.get("mem_z_low", 2.0) or mem_usage > self.config.get("mem_usage_low", 85.0):
            severity = "LOW"
            if mem_z > self.config.get("mem_z_high", 3.0) or mem_usage > self.config.get("mem_usage_high", 90.0):
                severity = "HIGH"
            elif mem_z > self.config.get("mem_z_medium", 2.3) or mem_usage > self.config.get("mem_usage_medium", 80.0):
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

            if read_z > self.config.get("disk_read_z_low", 3.0):
                severity = "LOW"
                if read_z > self.config.get("disk_read_z_high", 5.0):
                    severity = "HIGH"
                elif read_z > self.config.get("disk_read_z_medium", 4.0):
                    severity = "MEDIUM"
                
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

            if write_z > self.config.get("disk_write_z_low", 3.0):
                severity = "LOW"
                if write_z > self.config.get("disk_write_z_high", 5.0):
                    severity = "HIGH"
                elif write_z > self.config.get("disk_write_z_medium", 4.0):
                    severity = "MEDIUM"
                
                anomalies.append({
                    "metric": "disk_write_rate",
                    "current_value": round(write_rate / 1024 / 1024, 2),  # MB/s
                    "baseline_mean": round(write_mean / 1024 / 1024, 2),
                    "deviation_z": round(write_z, 2),
                    "severity": severity,
                    "timestamp": time.time(),
                    "description": f"Disk Write rate ({round(write_rate/1024/1024, 2)} MB/s) exceeds baseline mean ({round(write_mean/1024/1024, 2)} MB/s)."
                })

        # Network Connections Anomaly
        net_conn = current_metrics.get("plugins_data", {}).get("network_telemetry", {}).get("active_connections", 0.0)
        if net_conn > 0:
            net_baseline = stats.get("active_connections", {"mean": 25.0, "std": 10.0})
            net_mean = net_baseline["mean"]
            net_std = net_baseline["std"]
            net_z = (net_conn - net_mean) / net_std if net_std > 0 else 0

            if net_z > self.config.get("net_conn_z_low", 2.0) or net_conn > 350:
                severity = "LOW"
                if net_z > self.config.get("net_conn_z_high", 4.0) or net_conn > 600:
                    severity = "HIGH"
                elif net_z > self.config.get("net_conn_z_medium", 3.0) or net_conn > 450:
                    severity = "MEDIUM"

                anomalies.append({
                    "metric": "active_connections",
                    "current_value": net_conn,
                    "baseline_mean": net_mean,
                    "deviation_z": round(net_z, 2),
                    "severity": severity,
                    "timestamp": time.time(),
                    "description": f"Active connections ({net_conn}) deviates from baseline mean ({net_mean})."
                })

        # GPU Utilization Anomaly
        gpu_data = current_metrics.get("plugins_data", {}).get("gpu_analyzer", {})
        if gpu_data and gpu_data.get("available"):
            gpu_util = gpu_data.get("utilization_gpu_percent", 0.0)
            gpu_baseline = stats.get("gpu_utilization", {"mean": 10.0, "std": 10.0})
            gpu_mean = gpu_baseline["mean"]
            gpu_std = gpu_baseline["std"]
            gpu_z = (gpu_util - gpu_mean) / gpu_std if gpu_std > 0 else 0

            if gpu_z > self.config.get("gpu_z_low", 2.0) or gpu_util > 85.0:
                severity = "LOW"
                if gpu_z > self.config.get("gpu_z_high", 4.0) or gpu_util > 95.0:
                    severity = "HIGH"
                elif gpu_z > self.config.get("gpu_z_medium", 3.0) or gpu_util > 75.0:
                    severity = "MEDIUM"

                anomalies.append({
                    "metric": "gpu_utilization",
                    "current_value": gpu_util,
                    "baseline_mean": gpu_mean,
                    "deviation_z": round(gpu_z, 2),
                    "severity": severity,
                    "timestamp": time.time(),
                    "description": f"GPU utilization ({gpu_util}%) deviates from baseline mean ({gpu_mean}%)."
                })

        # Swap Memory Anomaly
        swap_pct = current_metrics.get("memory", {}).get("swap_usage_percent", 0.0)
        swap_baseline = stats.get("swap_usage_percent", {"mean": 10.0, "std": 10.0})
        swap_mean = swap_baseline["mean"]
        swap_std = swap_baseline["std"]
        swap_z = (swap_pct - swap_mean) / swap_std if swap_std > 0 else 0

        if swap_z > self.config.get("swap_z_low", 2.0) or swap_pct > 80.0:
            severity = "LOW"
            if swap_z > self.config.get("swap_z_high", 4.0) or swap_pct > 95.0:
                severity = "HIGH"
            elif swap_z > self.config.get("swap_z_medium", 3.0) or swap_pct > 90.0:
                severity = "MEDIUM"

            anomalies.append({
                "metric": "swap_usage_percent",
                "current_value": swap_pct,
                "baseline_mean": swap_mean,
                "deviation_z": round(swap_z, 2),
                "severity": severity,
                "timestamp": time.time(),
                "description": f"Swap memory usage ({swap_pct}%) deviates from baseline mean ({swap_mean}%)."
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
