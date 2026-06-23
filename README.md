# 🧠 SysLens

**SysLens** is a lightweight, local-first system telemetry intelligence and observability platform designed for developers. It combines low-overhead metrics collection with a behavioral anomaly engine, actionable troubleshooting diagnostics, a modular plugin system, and dual frontend options (a dark-glass web dashboard and a premium terminal interface).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)

---

## ✨ Features

- **📊 Comprehensive Telemetry**: Real-time tracking of CPU utilization, logical core frequencies, virtual memory state, disk partition IO, system uptime, and top resource-hogging processes.
- **📈 Rolling Behavioral Baselines**: Learns system behavior patterns dynamically. Calculates rolling means and standard deviations locally to detect subtle deviations without external DBs.
- **⚠ Z-Score Anomaly Engine**: Identifies CPU, memory, and disk IO spikes, categorizes severity (`LOW`, `MEDIUM`, `HIGH`), and detects correlated bottlenecks (e.g. concurrent CPU and RAM stress).
- **🔌 Extensible Plugins**: Supports built-in plugins for Battery Health and GPU utilization, with runtime loading for custom external scripts.
- **🖥️ Premium CLI Toolkit**:
  - `syslens scan` - Side-by-side terminal dashboard pane.
  - `syslens health` - Quick diagnostic checklist and score (`0-100`).
  - `syslens live` - Real-time btop-inspired terminal stream.
- **glassmorphic Web UI**: Stunning dark-glass design running on a FastAPI + WebSocket backend with live Chart.js animations.

---

## 🚀 Quick Start

### Installation

Install dependencies and run SysLens in editable mode:

```bash
# Clone the repository
git clone https://github.com/your-username/syslens.git
cd syslens

# Install requirements and CLI package
pip install -r requirements.txt
pip install -e .
```

### CLI Command Reference

SysLens packages itself into two console command scripts (`syslens` and `syslensd`):

| Command | Action |
|:---|:---|
| `syslens scan` | Fetch a structured, double-column telemetry summary. |
| `syslens scan --json` | Output system snapshot as a clean JSON structure. |
| `syslens health` | Execute diagnostics, check anomalies, and view recommendations. |
| `syslens live` | Run the real-time split-pane terminal dashboard stream. |
| `syslens serve` / `syslensd` | Launch the FastAPI local server (default: `http://127.0.0.1:8000`). |
| `syslens export` | Export the current snapshot to a glassmorphism HTML report. |

---

## 🎨 Terminal Preview

### `syslens scan`
```text
--------------------- SYSLENS - ENTERPRISE TELEMETRY SCAN ---------------------

+------- ENVIRONMENT METADATA -------+  +--------- SYSTEM HEALTH KPI ---------+
|   * OS Platform : Windows 11       |  |                                     |
| (AMD64)                            |  |   Overall Rating : DEGRADED         |
|   * Hostname    : Dev-Station      |  |   Health Score   : 64.3 / 100       |
|   * Local IP    : 192.168.1.6      |  |   Status Gauge   :                  |
|   * Uptime      : 1h 42m 2s        |  | ##############-------- 64.3%        |
+------------------------------------+  +-------------------------------------+

+------- TELEMETRY STATISTICS -------+  +--------- TOP PROCESS HOGS ----------+
|  Resource   Meter       Details    |  |  PID    Name   CPU %      %  Status |
|  CPU        ##-------   16 Cores   |  |  7820   Code   0.0%  2.92%  running |
|             16.1%       @ 2400MHz  |  |  22448  Code   0.0%  2.88%  running |
|  Memory     #########   11.25 GB   |  |  13084  chrome 0.0%  2.78%  running |
+------------------------------------+  +-------------------------------------+
```

---

## 📦 Developer SDK Usage

SysLens can be directly embedded into your Python application or backend script.

### 1. Library Telemetry Snapshot
```python
from syslens.core.system import get_system_info
from syslens.core.health import calculate_health

# Fetch raw metrics dict
metrics = get_system_info()
print(f"CPU usage: {metrics['cpu_usage']}%, Memory usage: {metrics['memory_usage']}%")

# Generate Health Score
score = calculate_health(metrics)
print(f"System Health Rating: {score}/100")
```

### 2. Runtime Anomaly Detection
```python
from syslens.engine.detector import AnomalyDetector

detector = AnomalyDetector()

# Periodic tick checks (returns any deviations matching the rolling baseline)
anomalies = detector.tick()
if anomalies:
    for anomaly in anomalies:
         print(f"[{anomaly['severity']}] {anomaly['metric']}: {anomaly['description']}")
```

---

## 🛠️ Repository Navigation

To learn more about SysLens, read the comprehensive guides in the repository:
- **[ARCHITECTURE.md](file:///c:/D/Projects/Python/Syslens/ARCHITECTURE.md)**: Explore the data flow, Mermaid architecture diagrams, and baseline Z-score formulas.
- **[TESTING.md](file:///c:/D/Projects/Python/Syslens/TESTING.md)**: Guidelines for running pytest, mocking hardware info, and reviewing code coverage.
- **[CONTRIBUTING.md](file:///c:/D/Projects/Python/Syslens/CONTRIBUTING.md)**: How to submit bug reports, pull requests, and code extensions.
- **[ROADMAP.md](file:///c:/D/Projects/Python/Syslens/ROADMAP.md)**: Development milestones and future goals.
- **[CHANGELOG.md](file:///c:/D/Projects/Python/Syslens/CHANGELOG.md)**: Detailed version history and release notes.

---

## 📜 License

Distributed under the MIT License. See [LICENSE](file:///c:/D/Projects/Python/Syslens/LICENSE) for more details.
