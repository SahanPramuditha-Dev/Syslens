from typing import Dict, Any, List
from syslens.core.system import SystemMetricsCollector
from syslens.engine.baseline import BehaviorBaseline
from syslens.engine.detector import AnomalyDetector

class AnomalyInterface:
    """Interface layer coordinating metrics collection, baseline refinement, and anomaly detection."""

    def __init__(self, baseline_file: str = None):
        self.collector = SystemMetricsCollector()
        self.baseline = BehaviorBaseline(filepath=baseline_file)
        self.detector = AnomalyDetector(self.baseline)

    def scan_system(self, process_limit: int = 10) -> Dict[str, Any]:
        """Perform a complete telemetry poll, update the behavioral baseline, and inspect for anomalies."""
        metrics = self.collector.collect_all(process_limit=process_limit)
        
        # Feed metrics into baseline model to learn normal behavior
        self.baseline.update(metrics)
        
        # Analyze metrics for anomalies
        anomalies = self.detector.analyze(metrics)
        
        # Attach baseline stats and anomalies to the returned data
        metrics["anomalies"] = anomalies
        metrics["baseline_stats"] = self.baseline.get_stats()
        
        return metrics
