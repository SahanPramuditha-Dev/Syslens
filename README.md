# SysLens

SysLens is a lightweight, local-first **system observability, diagnostics, and anomaly-detection toolkit for Python**. It combines system telemetry, health scoring, behavioral baselines, CLI workflows, an extensible plugin model, and an optional FastAPI/WebSocket dashboard.

[![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.0.0-blue)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/status-beta-orange)](ROADMAP.md)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Features

- **System telemetry** — CPU, memory, disk, uptime, frequencies, and process-level resource information.
- **Health scoring** — produces a high-level system health score for quick diagnostics.
- **Behavioral baselines** — tracks rolling statistics to identify unusual system behavior.
- **Z-score anomaly detection** — flags resource deviations and assigns severity levels.
- **Plugin architecture** — supports additional system-information and diagnostics modules.
- **CLI toolkit** — scan, health, live monitoring, export, and server commands.
- **Optional web dashboard** — FastAPI + WebSocket backend for live browser-based monitoring.
- **Developer SDK** — core telemetry and diagnostics can be imported directly into Python applications.

## Installation

### Core CLI / Library

```bash
git clone https://github.com/SahanPramuditha-Dev/Syslens.git
cd Syslens
pip install -e .
```

### With Web Dashboard

```bash
pip install -e .[dashboard]
```

### Development Dependencies

```bash
pip install -e .[dev]
```

SysLens requires **Python 3.8 or newer**.

## CLI Reference

| Command | Purpose |
| --- | --- |
| `syslens scan` | Display a structured system telemetry snapshot |
| `syslens scan --json` | Output telemetry in JSON form |
| `syslens health` | Run health checks and show the current health score |
| `syslens live` | Start the live terminal monitoring view |
| `syslens serve` | Start the optional local web dashboard |
| `syslensd` | Alternate entry point for the dashboard server |
| `syslens export` | Export the current snapshot/report |

## Quick SDK Example

```python
import syslens

metrics = syslens.get_system_info()
score = syslens.calculate_health(metrics)

print(f"CPU: {metrics['cpu_usage']}%")
print(f"Memory: {metrics['memory_usage']}%")
print(f"Health: {score:.1f}/100")
```

## Anomaly Detection Example

```python
from syslens.engine.detector import AnomalyDetector

detector = AnomalyDetector()

for anomaly in detector.tick():
    print(
        f"[{anomaly['severity']}] "
        f"{anomaly['metric']}: {anomaly['description']}"
    )
```

## Architecture

```text
System / OS
    │
    ▼
Telemetry Collectors
    │
    ├── CPU / memory / disk / processes
    └── optional plugins
    │
    ▼
Health & Anomaly Engine
    │
    ├── health score
    ├── rolling baselines
    └── anomaly detection
    │
    ├──────────────► CLI
    │
    ├──────────────► Python SDK
    │
    └──────────────► FastAPI / WebSocket Dashboard
```

## Testing

```bash
pytest
```

Pytest configuration is defined in `pyproject.toml`, with tests located under `tests/`.

## Repository Documentation

- [Architecture](ARCHITECTURE.md) — data flow, design decisions, and anomaly-detection details.
- [Testing](TESTING.md) — test strategy and hardware/system mocking guidance.
- [Contributing](CONTRIBUTING.md) — contribution workflow.
- [Roadmap](ROADMAP.md) — planned improvements and development milestones.
- [Changelog](CHANGELOG.md) — version history.
- [License](LICENSE) — MIT license terms.

## Project Status

SysLens is currently marked as **Beta** in the package metadata. The API, diagnostics logic, dashboard, and plugin interfaces may continue to evolve.

## Author

**Sahan Pramuditha**  
BICT Undergraduate — University of Colombo

## License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
