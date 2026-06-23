# SysLens v1.0

SysLens is a lightweight system telemetry and observability engine built for developers. It offers:
- **Core System Telemetry**: Live CPU, memory, disk, OS info, and process list metrics.
- **Behavioral Anomaly Detection**: Automatic baseline model learning, severity scoring, and multi-metric anomaly alerts.
- **Troubleshooting Diagnostics**: Actionable fix recommendations and severity classification.
- **Modular Plugin System**: Extensibility for battery stats, GPU parameters, and custom external scripts.
- **Real-Time Live Web Dashboard**: Stunning dark-glass FastAPI web interface using WebSockets.
- **Developer CLI**: Terminal-first reporting (`syslens scan`, `syslens health`, `syslens live`).

## Installation
```bash
pip install -r requirements.txt
pip install -e .
```

## Running the Application
- Scan current system metrics: `syslens scan`
- Perform diagnostics & health check: `syslens health`
- Run live terminal telemetry: `syslens live`
- Launch the FastAPI local dashboard: `syslensd`
