# 🧪 Testing SysLens

SysLens uses **pytest** as its primary testing framework. We enforce unit tests on all core mathematical equations, telemetry parsing functions, baseline storage IO, and diagnostic metrics.

---

## 🚀 Setting Up the Test Environment

To run SysLens tests, ensure you have installed the core dependencies and pytest packages.

```bash
# Install core requirements
pip install -r requirements.txt

# Install pytest if not already present
pip install pytest
```

---

## 🏃 Running the Tests

To run the automated tests, execute pytest from the project root directory:

```bash
# Run all tests
python -m pytest

# Run with verbose output
python -m pytest -v

# Run a specific test file
python -m pytest tests/test_core.py -v
```

---

## 📂 Test Suite Structure

The tests are located in the `tests/` directory.

### Core Test File: `tests/test_core.py`
This suite validates the core logical modules of SysLens:

1. **`test_system_collector`**:
   - Validates that the `SystemMetricsCollector` correctly reads OS info, CPU cores, physical memory counts, and disk details.
   - Ensures the process list is properly fetched and respects the `process_limit` argument.
2. **`test_behavioral_baseline`**:
   - Uses Python's `tempfile` module to simulate loading/saving `~/.syslens/baseline.json`.
   - Injects mock telemetry iterations to confirm baseline parameters (means, standard deviations) update correctly once sample requirements are satisfied.
3. **`test_anomaly_detector`**:
   - Populates a mock baseline with stable values and injects a sudden spike in CPU usage.
   - Asserts that the Z-score logic triggers a `HIGH` severity anomaly correctly.
4. **`test_health_engine`**:
   - Evaluates the Health Evaluation weight formulas.
   - Asserts that standard metrics generate the correct status (`HEALTHY` vs `DEGRADED` vs `CRITICAL`) and that threshold score bounds are adhered to.
5. **`test_plugin_manager`**:
   - Registers simulated plugins (such as simulated GPU stats) and validates that the manager correctly executes them, merging results cleanly into system snapshots.

---

## 🛠️ Guidelines for Writing New Tests

If you are adding new features, files, or custom plugins:
- Create matching tests under `tests/`.
- Mock external network calls or heavy hardware executions (e.g. GPU, disk partition sizes) using `unittest.mock` or local temporary data files.
- Run `python -m pytest` before publishing code. Ensure all tests pass with zero exceptions.
