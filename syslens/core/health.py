from typing import Dict, Any, List, Tuple

class SystemHealthEngine:
    """Scoring engine evaluating metrics, computing KPIs, and delivering diagnostic reports."""

    def __init__(self):
        # Weighted metric components for the scoring logic
        self.weight_cpu = 0.30
        self.weight_memory = 0.35
        self.weight_disk = 0.15
        self.weight_anomaly = 0.20

    def calculate_score(self, metrics: Dict[str, Any]) -> Tuple[float, str]:
        """Compute system health score (0-100) and status classification."""
        # 1. CPU Penalty (Max weight: 30)
        cpu_usage = metrics.get("cpu", {}).get("usage_percent", 0.0)
        cpu_penalty = (cpu_usage / 100.0) * (self.weight_cpu * 100)

        # 2. Memory Penalty (Max weight: 35)
        mem_usage = metrics.get("memory", {}).get("usage_percent", 0.0)
        mem_penalty = (mem_usage / 100.0) * (self.weight_memory * 100)

        # 3. Disk Space Penalty (Max weight: 15)
        disk_partitions = metrics.get("disk", {}).get("partitions", [])
        max_disk_usage = 0.0
        if disk_partitions:
            max_disk_usage = max(p.get("usage_percent", 0.0) for p in disk_partitions)
        disk_penalty = (max_disk_usage / 100.0) * (self.weight_disk * 100)

        # 4. Anomaly Penalty (Max weight: 20)
        anomalies = metrics.get("anomalies", [])
        anomaly_penalty = 0.0
        for anomaly in anomalies:
            severity = anomaly.get("severity", "LOW")
            if severity == "HIGH":
                anomaly_penalty += 15.0
            elif severity == "MEDIUM":
                anomaly_penalty += 10.0
            else:
                anomaly_penalty += 5.0
        anomaly_penalty = min(anomaly_penalty, self.weight_anomaly * 100)

        # Calculate final health score (bounded 0 - 100)
        raw_score = 100.0 - (cpu_penalty + mem_penalty + disk_penalty + anomaly_penalty)
        score = max(0.0, min(100.0, raw_score))
        score = round(score, 1)

        # Status classification
        if score >= 80.0:
            status = "Healthy"
        elif score >= 50.0:
            status = "Degraded"
        else:
            status = "Critical"

        return score, status

    def diagnose_issues(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run diagnostic engine to identify CPU, Memory, Disk, and Process issues and provide recommendations."""
        diagnoses = []
        cpu_usage = metrics.get("cpu", {}).get("usage_percent", 0.0)
        mem_usage = metrics.get("memory", {}).get("usage_percent", 0.0)
        processes = metrics.get("processes", [])
        disk_partitions = metrics.get("disk", {}).get("partitions", [])

        # CPU diagnostics
        if cpu_usage > 75.0:
            cpu_hogs = [p for p in processes if p.get("cpu_percent", 0.0) > 20.0]
            recommendations = ["Consider closing heavy applications or background services."]
            if cpu_hogs:
                hogs_list = ", ".join([f"{p['name']} (PID: {p['pid']} - {p['cpu_percent']}%)" for p in cpu_hogs])
                recommendations.append(f"Inspect or terminate CPU hog processes: {hogs_list}")
            
            diagnoses.append({
                "type": "CPU Overload",
                "severity": "HIGH" if cpu_usage > 90.0 else "MEDIUM",
                "message": f"High CPU utilization detected ({cpu_usage}%).",
                "recommendations": recommendations
            })

        # Memory diagnostics
        if mem_usage > 80.0:
            mem_hogs = [p for p in processes if p.get("memory_percent", 0.0) > 10.0]
            recommendations = ["Consider closing browser tabs or IDEs.", "Check for active memory leaks in running scripts."]
            if mem_hogs:
                hogs_list = ", ".join([f"{p['name']} (PID: {p['pid']} - {p['memory_percent']}%)" for p in mem_hogs])
                recommendations.append(f"Terminate or restart memory hog processes: {hogs_list}")
            
            diagnoses.append({
                "type": "Memory Pressure",
                "severity": "HIGH" if mem_usage > 90.0 else "MEDIUM",
                "message": f"System memory utilization is high ({mem_usage}%).",
                "recommendations": recommendations
            })

        # Disk Capacity diagnostics
        for part in disk_partitions:
            usage = part.get("usage_percent", 0.0)
            if usage > 85.0:
                diagnoses.append({
                    "type": "Disk Capacity Limit",
                    "severity": "HIGH" if usage > 95.0 else "MEDIUM",
                    "message": f"Disk partition '{part['mountpoint']}' is nearly full ({usage}%).",
                    "recommendations": [
                        f"Clean temporary files and cache on '{part['mountpoint']}'.",
                        "Archive or compress historical application logs.",
                        "Remove unused large media files or packages."
                    ]
                })

        # Anomalies diagnostic link
        anomalies = metrics.get("anomalies", [])
        for anomaly in anomalies:
            # Avoid repeating the generic CPU/Memory usage alerts but provide diagnostic suggestions
            metric = anomaly.get("metric", "")
            severity = anomaly.get("severity", "LOW")
            if "correlated" in metric:
                diagnoses.append({
                    "type": "Behavioral Anomaly (Correlated)",
                    "severity": severity,
                    "message": anomaly.get("description", ""),
                    "recommendations": [
                        "The system is bottlenecked across multiple hardware subsystems.",
                        "Run 'syslens scan' to inspect the full list of resource-heavy processes.",
                        "Check hardware temperatures or throttling status if performance is severely degraded."
                    ]
                })

        return diagnoses

def calculate_health(system_info: Dict[str, Any]) -> float:
    """Compute overall system health score (0-100) (SDK Integration).
    
    Args:
        system_info: Dict containing cpu_usage, memory_usage, disk_usage
    """
    engine = SystemHealthEngine()
    
    # Format payload structure to align with Health Scoring Engine expectation
    mock_metrics = {
        "cpu": {"usage_percent": system_info.get("cpu_usage", 0.0)},
        "memory": {"usage_percent": system_info.get("memory_usage", 0.0)},
        "disk": {"partitions": [{"usage_percent": system_info.get("disk_usage", 0.0)}]},
        "anomalies": system_info.get("raw", {}).get("anomalies", []) if isinstance(system_info.get("raw"), dict) else []
    }
    
    score, _ = engine.calculate_score(mock_metrics)
    return score
