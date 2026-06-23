# 🤝 Contributing to SysLens

Thank you for your interest in contributing to SysLens! We welcome all contributions, including bug reports, feature requests, documentation improvements, and custom telemetry plugins.

---

## 🛠️ Code of Conduct & Standards

To maintain a clean and maintainable codebase, we ask that all contributors follow these guidelines:

### Coding Style
- Follow **PEP 8** style guidelines for all Python code.
- Write descriptive variable and function names.
- Provide type hints for function arguments and return types.
- Document classes and public methods with clear docstrings.
- Ensure cross-platform compatibility (especially for terminal symbols and paths on Windows and Unix).

### Clean Commits
- Use descriptive commit messages following the Conventional Commits format:
  - `feat: add network monitor plugin`
  - `fix: resolve live memory graph overflow`
  - `docs: update setup steps in README`
- Keep commits focused and atomic (avoid giant commits touching unrelated parts of the codebase).

---

## 🔌 Writing Custom Plugins

SysLens features a runtime-extendable plugin system. You can write custom plugins to gather new telemetry or modify the overall health score calculation.

### Plugin Location
- Place your custom Python files inside the user plugins directory:
  - Windows: `C:\Users\<username>\.syslens\plugins\`
  - Linux/macOS: `~/.syslens/plugins/`

### Plugin Implementation
Every plugin must subclass `SystemPlugin` from `syslens.plugins.base` and implement:
1. `name` (string): Unique identifier for the plugin.
2. `execute(context: dict) -> dict`: Perform the telemetry extraction. The results will be automatically merged into the main metrics feed.
3. `modify_health_score(score: float, context: dict) -> float` (optional): Alter the final computed system health score.

#### Example Plugin Structure (`~/.syslens/plugins/network_monitor.py`)
```python
from syslens.plugins.base import SystemPlugin
import psutil

class NetworkMonitorPlugin(SystemPlugin):
    name = "network_monitor"

    def execute(self, context: dict) -> dict:
        """
        Gathers raw network stats and formats the return dictionary.
        Must return a dict containing 'available': True/False and metrics.
        """
        try:
            net_io = psutil.net_io_counters()
            return {
                "available": True,
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e)
            }

    def modify_health_score(self, score: float, context: dict) -> float:
        """
        Optionally lowers the health score if network errors or heavy packet drops occur.
        """
        # If we had a packet drop check, we could subtract score here
        return score
```

---

## 📥 Submitting Contributions

### Reporting Issues
- Check the issue tracker before submitting to see if it has already been reported.
- Provide a clear description of the bug, steps to reproduce, and environment details (Python version, OS, terminal type).

### Pull Request Process
1. **Fork the Repository** and create a feature branch (`git checkout -b feature/cool-new-feature`).
2. **Add Tests**: If adding code logic, include unit tests under `tests/`.
3. **Verify All Tests Pass**: Run `python -m pytest` before pushing.
4. **Push to GitHub**: Push your branch (`git push origin feature/cool-new-feature`) and submit a Pull Request.
5. **Code Review**: A maintainer will review your code. Address any requested changes promptly.
