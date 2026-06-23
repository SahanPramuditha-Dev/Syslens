"""SysLens plugins — base class and plugin manager."""
from syslens.plugins.base import SysLensPlugin, SystemPlugin
from syslens.plugins.manager import PluginManager

__all__ = [
    "SysLensPlugin",
    "SystemPlugin",
    "PluginManager",
]
