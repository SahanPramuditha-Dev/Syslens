import os
import sys
import importlib.util
import subprocess
import shutil
from typing import Dict, Any, List, Type
import psutil

from syslens.plugins.base import SystemPlugin

# --- Built-in Plugins ---

class BatteryHealthPlugin(SystemPlugin):
    """Monitors battery capacity, power status, and modifies health score under battery stress."""

    @property
    def name(self) -> str:
        return "battery_health"

    @property
    def description(self) -> str:
        return "Tracks system battery levels, charging status, and critical battery warnings."

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            battery = psutil.sensors_battery()
        except Exception:
            battery = None

        if not battery:
            return {
                "available": False,
                "message": "No system battery detected."
            }

        return {
            "available": True,
            "percent": battery.percent,
            "power_plugged": battery.power_plugged,
            "seconds_remaining": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else -1
        }

    def modify_health_score(self, current_score: float, context: Dict[str, Any]) -> float:
        battery_data = context.get("plugins_data", {}).get(self.name, {})
        if not battery_data.get("available", False):
            return current_score

        percent = battery_data.get("percent", 100.0)
        plugged = battery_data.get("power_plugged", True)

        # Penalize health if battery is under 15% and discharging
        if percent < 15.0 and not plugged:
            penalty = 15.0 if percent < 8.0 else 10.0
            return max(0.0, current_score - penalty)
        return current_score


class GPUAnalyzerPlugin(SystemPlugin):
    """Monitors discrete GPU metrics using nvidia-smi if available, falling back to dynamic simulation."""

    @property
    def name(self) -> str:
        return "gpu_analyzer"

    @property
    def description(self) -> str:
        return "Extracts GPU temperature, memory utilization, and processor load details."

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                # Call nvidia-smi to query load, memory, temp
                res = subprocess.run(
                    [nvidia_smi, "--query-gpu=name,temperature.gpu,utilization.gpu,utilization.memory,memory.total,memory.used", "--format=csv,noheader,nounits"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=2.0
                )
                if res.returncode == 0:
                    parts = [p.strip() for p in res.stdout.strip().split(",")]
                    if len(parts) >= 6:
                        return {
                            "available": True,
                            "gpu_name": parts[0],
                            "temperature_c": float(parts[1]),
                            "utilization_gpu_percent": float(parts[2]),
                            "utilization_memory_percent": float(parts[3]),
                            "memory_total_mb": float(parts[4]),
                            "memory_used_mb": float(parts[5]),
                            "simulated": False
                        }
            except Exception:
                pass

        # Simulator fallback for demonstration/development setups
        return {
            "available": True,
            "gpu_name": "NVIDIA GeForce RTX 4080 (Simulated)",
            "temperature_c": 52.0,
            "utilization_gpu_percent": 12.5,
            "utilization_memory_percent": 24.1,
            "memory_total_mb": 16384.0,
            "memory_used_mb": 3948.0,
            "simulated": True
        }

    def modify_health_score(self, current_score: float, context: Dict[str, Any]) -> float:
        gpu_data = context.get("plugins_data", {}).get(self.name, {})
        if not gpu_data.get("available", False):
            return current_score

        temp = gpu_data.get("temperature_c", 0.0)
        # Deduct health if GPU is overheating (> 85C)
        if temp > 85.0:
            penalty = 15.0 if temp > 92.0 else 8.0
            return max(0.0, current_score - penalty)
        return current_score


# --- Plugin Manager ---

class PluginManager:
    """Enterprise-grade manager for loading, registering, and running system plugins."""

    def __init__(self, custom_plugins_dir: str = None):
        if custom_plugins_dir is None:
            home = os.path.expanduser("~")
            self.plugins_dir = os.path.join(home, ".syslens", "plugins")
        else:
            self.plugins_dir = custom_plugins_dir

        self.plugins: Dict[str, SystemPlugin] = {}
        self.register_builtins()
        self.load_third_party_plugins()

    def register_builtins(self) -> None:
        """Register default out-of-the-box SysLens plugins."""
        for plugin_cls in [BatteryHealthPlugin, GPUAnalyzerPlugin]:
            plugin = plugin_cls()
            try:
                plugin.initialize()
                self.plugins[plugin.name] = plugin
            except Exception:
                pass

    def load_third_party_plugins(self) -> None:
        """Scan and import plugins from external scripts folder dynamically."""
        if not os.path.exists(self.plugins_dir):
            try:
                os.makedirs(self.plugins_dir, exist_ok=True)
            except Exception:
                return

        # Scan directory for .py files
        for filename in os.listdir(self.plugins_dir):
            if filename.endswith(".py") and not filename.startswith("__"):
                filepath = os.path.join(self.plugins_dir, filename)
                plugin_name = filename[:-3]
                try:
                    spec = importlib.util.spec_from_file_location(plugin_name, filepath)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        sys.modules[plugin_name] = module
                        spec.loader.exec_module(module)

                        # Search for SystemPlugin implementations
                        for item_name in dir(module):
                            item = getattr(module, item_name)
                            if (isinstance(item, type) and 
                                    issubclass(item, SystemPlugin) and 
                                    item is not SystemPlugin):
                                plugin_instance = item()
                                plugin_instance.initialize()
                                self.plugins[plugin_instance.name] = plugin_instance
                except Exception as e:
                    print(f"Error loading custom plugin '{filename}': {e}", file=sys.stderr)

    def execute_all(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run all registered plugins, updates context, and outputs the aggregate telemetry."""
        plugins_data = {}
        context["plugins_data"] = plugins_data  # Reference for health modifiers
        
        for name, plugin in self.plugins.items():
            try:
                plugins_data[name] = plugin.execute(context)
            except Exception as e:
                plugins_data[name] = {"error": str(e), "available": False}

        return plugins_data

    def modify_health_score(self, current_score: float, context: Dict[str, Any]) -> float:
        """Modify overall health score by evaluating each active plugin's telemetry checks."""
        modified_score = current_score
        for name, plugin in self.plugins.items():
            try:
                modified_score = plugin.modify_health_score(modified_score, context)
            except Exception:
                pass
        return round(modified_score, 1)

    def register(self, plugin: SystemPlugin) -> None:
        """Register a plugin instance explicitly (SDK Integration)."""
        try:
            plugin.initialize()
            self.plugins[plugin.name] = plugin
        except Exception as e:
            raise ValueError(f"Failed to initialize plugin: {e}")

    def run_all(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all plugins (SDK wrapper for execute_all)."""
        return self.execute_all(context)

    def get_registered_plugins(self) -> List[Dict[str, str]]:
        """Return descriptions of all registered plugins."""
        return [
            {"name": p.name, "description": p.description}
            for p in self.plugins.values()
        ]
