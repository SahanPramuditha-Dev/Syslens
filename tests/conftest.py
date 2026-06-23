"""
Shared pytest fixtures for the SysLens test suite.

These fixtures provide pre-built mock metric dictionaries so individual tests
do not have to call real hardware APIs unless they specifically need to.
"""
import pytest


# ---------------------------------------------------------------------------
# Mock telemetry dictionaries
# ---------------------------------------------------------------------------

@pytest.fixture()
def healthy_metrics():
    """System snapshot representing a low-load, healthy machine."""
    return {
        "timestamp": 1_700_000_000.0,
        "cpu": {"usage_percent": 12.0, "logical_cores": 8, "physical_cores": 4,
                "frequency_mhz_current": 2400.0, "frequency_mhz_max": 3600.0,
                "cores_usage_percent": [10.0, 15.0, 8.0, 14.0]},
        "memory": {"usage_percent": 35.0, "total_bytes": 16 * 1024**3,
                   "available_bytes": 10 * 1024**3, "used_bytes": 6 * 1024**3,
                   "swap_total_bytes": 4 * 1024**3, "swap_used_bytes": 0,
                   "swap_usage_percent": 0.0},
        "disk": {"partitions": [{"device": "C:\\", "mountpoint": "C:\\",
                                  "fstype": "NTFS", "total_bytes": 500 * 1024**3,
                                  "used_bytes": 150 * 1024**3,
                                  "free_bytes": 350 * 1024**3,
                                  "usage_percent": 30.0}],
                 "read_bytes": 1_000_000, "write_bytes": 500_000},
        "processes": [{"pid": 1234, "name": "python.exe", "username": "user",
                        "status": "running", "cpu_percent": 1.5, "memory_bytes": 50 * 1024**2,
                        "memory_percent": 0.3}],
        "anomalies": [],
    }


@pytest.fixture()
def critical_metrics():
    """System snapshot representing a severely overloaded machine."""
    return {
        "timestamp": 1_700_001_000.0,
        "cpu": {"usage_percent": 97.0, "logical_cores": 8, "physical_cores": 4,
                "frequency_mhz_current": 3600.0, "frequency_mhz_max": 3600.0,
                "cores_usage_percent": [98.0, 96.0, 97.0, 98.0]},
        "memory": {"usage_percent": 94.0, "total_bytes": 16 * 1024**3,
                   "available_bytes": 1 * 1024**3, "used_bytes": 15 * 1024**3,
                   "swap_total_bytes": 4 * 1024**3, "swap_used_bytes": 3 * 1024**3,
                   "swap_usage_percent": 75.0},
        "disk": {"partitions": [{"device": "C:\\", "mountpoint": "C:\\",
                                  "fstype": "NTFS", "total_bytes": 500 * 1024**3,
                                  "used_bytes": 490 * 1024**3,
                                  "free_bytes": 10 * 1024**3,
                                  "usage_percent": 98.0}],
                 "read_bytes": 10_000_000, "write_bytes": 8_000_000},
        "processes": [{"pid": 5678, "name": "heavy_app.exe", "username": "user",
                        "status": "running", "cpu_percent": 85.0,
                        "memory_bytes": 8 * 1024**3, "memory_percent": 50.0}],
        "anomalies": [
            {"metric": "cpu_usage", "severity": "HIGH",
             "description": "CPU spike detected", "current_value": 97.0,
             "baseline_mean": 20.0, "deviation_z": 7.7}
        ],
    }


@pytest.fixture()
def mock_plugin_context():
    """Minimal context dict suitable for running plugins."""
    return {
        "cpu": {"usage_percent": 20.0},
        "memory": {"usage_percent": 50.0},
        "disk": {"partitions": [{"mountpoint": "C:\\", "usage_percent": 40.0}]},
        "plugins_data": {},
    }
