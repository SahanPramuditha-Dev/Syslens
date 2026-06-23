from abc import ABC, abstractmethod
from typing import Dict, Any

class SystemPlugin(ABC):
    """Abstract Base Class for SysLens telemetry and health plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier of the plugin."""
        pass

    @property
    def description(self) -> str:
        """A brief description of what the plugin monitors or optimizes."""
        return "Custom registered developer plugin."

    def initialize(self) -> None:
        """Run any setup tasks or verify system compatibility for the plugin."""
        pass

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Custom execution logic (to be overridden by subclasses)."""
        return {}

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Unified runner, falls back to run() if not overridden."""
        return self.run(context)

    def modify_health_score(self, current_score: float, context: Dict[str, Any]) -> float:
        """Modify overall system health score based on plugin telemetry observations (optional).
        
        Args:
            current_score: Pre-calculated health score (0-100).
            context: Current system telemetry dictionary.
        """
        return current_score

# Alias for SDK compatibility
SysLensPlugin = SystemPlugin
