import os
import tempfile
import pytest

from syslens.core.system import SystemMetricsCollector
from syslens.engine.baseline import BehaviorBaseline
from syslens.engine.detector import AnomalyDetector
from syslens.core.health import SystemHealthEngine
from syslens.plugins.manager import PluginManager

def test_system_collector():
    """Verify that system collector fetches OS, CPU, memory, and processes telemetry."""
    collector = SystemMetricsCollector()
    metrics = collector.collect_all(process_limit=5)
    
    assert "os" in metrics
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "disk" in metrics
    assert "processes" in metrics
    
    assert metrics["cpu"]["logical_cores"] >= 1
    assert metrics["memory"]["total_bytes"] > 0
    assert len(metrics["processes"]) <= 5

def test_behavioral_baseline():
    """Verify baseline model initialization, file creation, and stats updates."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp_path = tmp.name

    try:
        baseline = BehaviorBaseline(filepath=tmp_path)
        # Ensure default stats are loaded
        assert "cpu" in baseline.stats
        assert "memory" in baseline.stats
        
        # Inject standard mock metrics
        for i in range(15):
            mock_metrics = {
                "timestamp": 1700000000.0 + i,
                "cpu": {"usage_percent": 10.0 + i},
                "memory": {"usage_percent": 45.0},
                "disk": {"read_bytes": 1000 * i, "write_bytes": 1000 * i}
            }
            baseline.update(mock_metrics)

        # Baseline should recalculate stats with >= 10 samples
        assert baseline.stats["cpu"]["mean"] > 0.0
        assert baseline.stats["cpu"]["std"] > 0.0
        
        # Verify JSON was written
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_anomaly_detector():
    """Verify that anomaly detector recognizes CPU/Memory spikes."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp_path = tmp.name

    try:
        baseline = BehaviorBaseline(filepath=tmp_path)
        detector = AnomalyDetector(baseline)
        
        # Fit baseline with low usage
        for i in range(12):
            mock_metrics = {
                "timestamp": 1700000000.0 + i,
                "cpu": {"usage_percent": 5.0},
                "memory": {"usage_percent": 40.0},
                "disk": {"read_bytes": 0, "write_bytes": 0}
            }
            baseline.update(mock_metrics)

        # Trigger CPU spike metrics
        spike_metrics = {
            "timestamp": 1700000013.0,
            "cpu": {"usage_percent": 95.0}, # Spike!
            "memory": {"usage_percent": 40.0},
            "disk": {"read_bytes": 0, "write_bytes": 0}
        }
        
        anomalies = detector.analyze(spike_metrics)
        assert len(anomalies) > 0
        cpu_anomaly = next((a for a in anomalies if a["metric"] == "cpu_usage"), None)
        assert cpu_anomaly is not None
        assert cpu_anomaly["severity"] == "HIGH"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_health_engine():
    """Verify health score calculation and classification logic."""
    engine = SystemHealthEngine()
    
    # Healthy mock metrics
    healthy_metrics = {
        "cpu": {"usage_percent": 15.0},
        "memory": {"usage_percent": 30.0},
        "disk": {"partitions": [{"usage_percent": 25.0}]},
        "anomalies": []
    }
    
    score, status = engine.calculate_score(healthy_metrics)
    assert score >= 80.0
    assert status == "Healthy"
    
    # Critical mock metrics
    critical_metrics = {
        "cpu": {"usage_percent": 98.0},
        "memory": {"usage_percent": 95.0},
        "disk": {"partitions": [{"usage_percent": 99.0}]},
        "anomalies": [{"severity": "HIGH", "metric": "cpu_usage", "description": "Spike"}]
    }
    
    score, status = engine.calculate_score(critical_metrics)
    assert score < 50.0
    assert status == "Critical"

def test_plugin_manager():
    """Verify built-in plugin registration and basic output compilation."""
    manager = PluginManager()
    plugins = manager.get_registered_plugins()
    
    # Verify builtins registered
    plugin_names = [p["name"] for p in plugins]
    assert "battery_health" in plugin_names
    assert "gpu_analyzer" in plugin_names
    
    # Execute plugins
    mock_context = {
        "cpu": {"usage_percent": 10.0},
        "memory": {"usage_percent": 40.0}
    }
    plugins_data = manager.execute_all(mock_context)
    assert "gpu_analyzer" in plugins_data
    assert plugins_data["gpu_analyzer"]["available"] is True

def test_sdk_integration():
    """Verify SDK endpoints work correctly (Direct Library, Tick, custom plugins)."""
    from syslens.core.system import get_system_info
    from syslens.core.health import calculate_health
    from syslens.plugins.base import SysLensPlugin
    
    # 1. Direct library integration
    sys_info = get_system_info()
    assert "cpu_usage" in sys_info
    assert "memory_usage" in sys_info
    assert "disk_usage" in sys_info
    
    health_score = calculate_health(sys_info)
    assert isinstance(health_score, float)
    assert 0.0 <= health_score <= 100.0
    
    # 2. Embedded anomaly engine
    detector = AnomalyDetector()
    anomalies = detector.tick()
    assert isinstance(anomalies, list)
    
    # 3. Custom Plugin System Integration
    class MyCustomPlugin(SysLensPlugin):
        @property
        def name(self):
            return "custom_check"
            
        def run(self, context):
            return {"status": "ok"}
            
    pm = PluginManager()
    pm.register(MyCustomPlugin())
    
    # Verify it registered
    plugins = pm.get_registered_plugins()
    plugin_names = [p["name"] for p in plugins]
    assert "custom_check" in plugin_names
    
    results = pm.run_all({})
    assert "custom_check" in results
    assert results["custom_check"]["status"] == "ok"

