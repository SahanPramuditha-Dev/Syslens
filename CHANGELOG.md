# 🔄 Changelog

All notable changes to the SysLens project will be documented in this file. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and adheres to Semantic Versioning.

---

## [1.3.0] - 2026-06-23

### Added
- Created complete developer repository documentation suite:
  - `ARCHITECTURE.md` describing Mermaid design diagrams and Z-score mathematics.
  - `TESTING.md` outlining mock structures and command usage.
  - `CONTRIBUTING.md` listing style guides and custom plugin development templates.
  - `ROADMAP.md` mapping future project iterations.
  - `CHANGELOG.md` documenting history.

### Fixed
- **CLI Color Rendering**: Resolved an issue in the live dashboard loops and scan commands where Rich console markup syntax tags (e.g. `[yellow]`, `[cyan]`, `[purple]`) were printed as literal text to stdout. Separated text buffers from styling parameters in `Text.append(...)` calls, and wrapped progress bars in `Text.from_markup()`.

---

## [1.2.0] - 2026-06-18

### Added
- Integrated `battery_health` plugin utilizing `psutil` sensors.
- Integrated `gpu_analyzer` plugin parsing `nvidia-smi` outputs with fallback simulators for cross-platform environments.
- Implemented `syslens export` subcommand compile task that outputs glassmorphic HTML telemetry reports.
- Added System Idle Process (PID 0) filtering logic to prevent Windows systems from reporting false CPU spikes of 1000%+.

---

## [1.1.0] - 2026-06-10

### Added
- Implemented side-by-side double column visual pane console interface using `rich.columns` and `rich.table.Table`.
- Added unicode console check (`supports_unicode()`) to fall back dynamically to safe ASCII symbols (`#`, `-`, `*`) on ANSI Western codepages to prevent console script crashes.

---

## [1.0.0] - 2026-06-05

### Added
- Initial core release of SysLens:
  - Telemetry collector (`system.py`).
  - Rolling mean/standard deviation baseline compiler (`baseline.py`).
  - Z-score anomaly detector (`detector.py`).
  - Diagnostics scoring logic (`health.py`).
  - FastAPI uvicorn daemon and WebSockets metrics streaming server (`app.py`, `socket.py`).
  - Dark-glass responsive Web UI (`index.html`, `app.js`).
  - Pytest unit tests coverages (`test_core.py`).

---

## [0.9.0] - 2026-05-25

### Added
- Designed and built the glassmorphic Web UI dashboard with CSS transitions.
- Integrated Chart.js modules to plot real-time memory and CPU timeline graphs.
- Connected the frontend WebSocket client to animate active telemetry streams dynamically.

---

## [0.8.0] - 2026-05-12

### Added
- Created the initial local FastAPI web server structure to host metrics and health check APIs.
- Built a proof-of-concept web interface featuring basic Chart.js graphs for memory and CPU streaming.
- Added WebSocket server connection handles to stream metrics updates every second.

---

## [0.5.0] - 2026-05-02

### Added
- Designed the Health evaluation engine weighting calculations.
- Integrated automated Troubleshooting recommendation engine to generate fix guidelines for high CPU/memory anomalies.
- Set up warning notifications trigger structure.

---

## [0.3.0] - 2026-04-22

### Added
- Implemented Z-score mathematical formulas for calculating telemetry metric drift.
- Categorized anomaly severity classifications to LOW, MEDIUM, and HIGH thresholds.
- Created correlation checks to flag concurrent spikes across multiple resources.

---

## [0.2.0] - 2026-04-10

### Added
- Introduced the baseline behavior engine to compile rolling system metrics.
- Added Z-score calculation module to check telemetry metrics deviations from normal bounds.
- Set up unit testing configuration and initial standard metrics collector mocks.

---

## [0.1.1] - 2026-03-24

### Added
- Built process telemetry monitor to list and filter top memory/CPU consumer PIDs.
- Added preliminary console command argument flag parsers.

---

## [0.1.0] - 2026-03-15

### Added
- Initial prototype of the telemetry metrics collection layer utilizing raw `psutil` data.
- Built core CPU, memory, and disk usage checks logic.
- Configured package directory tree skeleton and setup files (`pyproject.toml`, `requirements.txt`).
