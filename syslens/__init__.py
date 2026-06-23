"""
SysLens: Lightweight system telemetry, diagnostics, and anomaly detection platform.

Quick start
-----------
>>> import syslens
>>> metrics = syslens.get_system_info()
>>> print(metrics['cpu_usage'], metrics['memory_usage'])

>>> score = syslens.calculate_health(metrics)
>>> print(f"Health: {score}/100")

>>> detector = syslens.AnomalyDetector()
>>> anomalies = detector.tick()
"""
__version__ = "1.0.0"
__author__ = "Sahan Pramuditha"
__email__ = "sahan.dev.tech@gmail.com"
__license__ = "MIT"

# -- Core public API ----------------------------------------------------------
from syslens.core.system import get_system_info, SystemMetricsCollector
from syslens.core.health import calculate_health, SystemHealthEngine
from syslens.core.anomaly import AnomalyInterface

# -- Engine -------------------------------------------------------------------
from syslens.engine.detector import AnomalyDetector
from syslens.engine.baseline import BehaviorBaseline

# -- Plugin system ------------------------------------------------------------
from syslens.plugins.base import SysLensPlugin, SystemPlugin
from syslens.plugins.manager import PluginManager

__all__ = [
    # meta
    "__version__",
    "__author__",
    # core
    "get_system_info",
    "SystemMetricsCollector",
    "calculate_health",
    "SystemHealthEngine",
    "AnomalyInterface",
    # engine
    "AnomalyDetector",
    "BehaviorBaseline",
    # plugins
    "SysLensPlugin",
    "SystemPlugin",
    "PluginManager",
]
