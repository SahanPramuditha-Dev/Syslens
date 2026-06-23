import os
import tempfile
import pytest

from syslens.core.system import SystemMetricsCollector
from syslens.engine.baseline import BehaviorBaseline
from syslens.engine.detector import AnomalyDetector
from syslens.core.health import SystemHealthEngine
from syslens.plugins.manager import PluginManager

def test_system_collector():
    """Verify that system collector fetches OS, CPU, memory, and processes telemetry."""
    collector = SystemMetricsCollector()
    metrics = collector.collect_all(process_limit=5)
    
    assert "os" in metrics
    assert "cpu" in metrics
    assert "memory" in metrics
    assert "disk" in metrics
    assert "processes" in metrics
    
    assert metrics["cpu"]["logical_cores"] >= 1
    assert metrics["memory"]["total_bytes"] > 0
    assert len(metrics["processes"]) <= 5

def test_behavioral_baseline():
    """Verify baseline model initialization, file creation, and stats updates."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp_path = tmp.name

    try:
        baseline = BehaviorBaseline(filepath=tmp_path)
        # Ensure default stats are loaded
        assert "cpu" in baseline.stats
        assert "memory" in baseline.stats
        
        # Inject standard mock metrics
        for i in range(15):
            mock_metrics = {
                "timestamp": 1700000000.0 + i,
                "cpu": {"usage_percent": 10.0 + i},
                "memory": {"usage_percent": 45.0},
                "disk": {"read_bytes": 1000 * i, "write_bytes": 1000 * i}
            }
            baseline.update(mock_metrics)

        # Baseline should recalculate stats with >= 10 samples
        assert baseline.stats["cpu"]["mean"] > 0.0
        assert baseline.stats["cpu"]["std"] > 0.0
        
        # Verify JSON was written
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_anomaly_detector():
    """Verify that anomaly detector recognizes CPU/Memory spikes."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp_path = tmp.name

    try:
        baseline = BehaviorBaseline(filepath=tmp_path)
        detector = AnomalyDetector(baseline)
        
        # Fit baseline with low usage
        for i in range(12):
            mock_metrics = {
                "timestamp": 1700000000.0 + i,
                "cpu": {"usage_percent": 5.0},
                "memory": {"usage_percent": 40.0},
                "disk": {"read_bytes": 0, "write_bytes": 0}
            }
            baseline.update(mock_metrics)

        # Trigger CPU spike metrics
        spike_metrics = {
            "timestamp": 1700000013.0,
            "cpu": {"usage_percent": 95.0}, # Spike!
            "memory": {"usage_percent": 40.0},
            "disk": {"read_bytes": 0, "write_bytes": 0}
        }
        
        anomalies = detector.analyze(spike_metrics)
        assert len(anomalies) > 0
        cpu_anomaly = next((a for a in anomalies if a["metric"] == "cpu_usage"), None)
        assert cpu_anomaly is not None
        assert cpu_anomaly["severity"] == "HIGH"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_health_engine():
    """Verify health score calculation and classification logic."""
    engine = SystemHealthEngine()
    
    # Healthy mock metrics
    healthy_metrics = {
        "cpu": {"usage_percent": 15.0},
        "memory": {"usage_percent": 30.0},
        "disk": {"partitions": [{"usage_percent": 25.0}]},
        "anomalies": []
    }
    
    score, status = engine.calculate_score(healthy_metrics)
    assert score >= 80.0
    assert status == "Healthy"
    
    # Critical mock metrics
    critical_metrics = {
        "cpu": {"usage_percent": 98.0},
        "memory": {"usage_percent": 95.0},
        "disk": {"partitions": [{"usage_percent": 99.0}]},
        "anomalies": [{"severity": "HIGH", "metric": "cpu_usage", "description": "Spike"}]
    }
    
    score, status = engine.calculate_score(critical_metrics)
    assert score < 50.0
    assert status == "Critical"

def test_plugin_manager():
    """Verify built-in plugin registration and basic output compilation."""
    manager = PluginManager()
    plugins = manager.get_registered_plugins()
    
    # Verify builtins registered
    plugin_names = [p["name"] for p in plugins]
    assert "battery_health" in plugin_names
    assert "gpu_analyzer" in plugin_names
    assert "network_telemetry" in plugin_names
    assert "disk_health" in plugin_names
    
    # Execute plugins
    mock_context = {
        "cpu": {"usage_percent": 10.0},
        "memory": {"usage_percent": 40.0},
        "disk": {"partitions": [{"mountpoint": "/", "usage_percent": 30.0}]}
    }
    plugins_data = manager.execute_all(mock_context)
    assert "gpu_analyzer" in plugins_data
    assert plugins_data["gpu_analyzer"]["available"] is True
    
    assert "network_telemetry" in plugins_data
    assert plugins_data["network_telemetry"]["available"] is True
    assert "bytes_recv_sec" in plugins_data["network_telemetry"]
    assert "active_connections" in plugins_data["network_telemetry"]
    
    assert "disk_health" in plugins_data
    assert plugins_data["disk_health"]["available"] is True
    assert "smart_status" in plugins_data["disk_health"]
    assert "wear_level_percent" in plugins_data["disk_health"]

def test_sdk_integration():
    """Verify SDK endpoints work correctly (Direct Library, Tick, custom plugins)."""
    from syslens.core.system import get_system_info
    from syslens.core.health import calculate_health
    from syslens.plugins.base import SysLensPlugin
    
    # 1. Direct library integration
    sys_info = get_system_info()
    assert "cpu_usage" in sys_info
    assert "memory_usage" in sys_info
    assert "disk_usage" in sys_info
    
    health_score = calculate_health(sys_info)
    assert isinstance(health_score, float)
    assert 0.0 <= health_score <= 100.0
    
    # 2. Embedded anomaly engine
    detector = AnomalyDetector()
    anomalies = detector.tick()
    assert isinstance(anomalies, list)
    
    # 3. Custom Plugin System Integration
    class MyCustomPlugin(SysLensPlugin):
        @property
        def name(self):
            return "custom_check"
            
        def run(self, context):
            return {"status": "ok"}
            
    pm = PluginManager()
    pm.register(MyCustomPlugin())
    
    # Verify it registered
    plugins = pm.get_registered_plugins()
    plugin_names = [p["name"] for p in plugins]
    assert "custom_check" in plugin_names
    
    results = pm.run_all({})
    assert "custom_check" in results
    assert results["custom_check"]["status"] == "ok"

def test_suggester():
    """Verify that suggester and auto-cleaner routines work correctly."""
    from syslens.engine.suggester import generate_suggestions, execute_safe_cleanups
    
    # Generate suggestions from mock context
    mock_metrics = {
        "cpu": {"usage_percent": 95.0},
        "memory": {"usage_percent": 90.0},
        "disk": {"partitions": [{"mountpoint": "/", "usage_percent": 88.0}]}
    }
    sugs = generate_suggestions(mock_metrics)
    assert len(sugs) > 0
    
    categories = [s["category"] for s in sugs]
    assert "CPU" in categories
    assert "STORAGE" in categories
    
    # Verify risk tags exist
    for s in sugs:
        for a in s["actions"]:
            assert a["risk"] in ["SAFE", "MEDIUM", "HIGH RISK"]
            
    # Execute safe cleanup
    cleanup_results = execute_safe_cleanups()
    assert cleanup_results["success"] is True
    assert "bytes_freed" in cleanup_results
    assert "files_deleted" in cleanup_results

def test_cleaner_engine():
    """Verify that cleaner modules execute and return correct tasks and keys."""
    from syslens.cleaner.safety import safety_check
    from syslens.cleaner.temp_cleaner import clean_temp_files
    from syslens.cleaner.recycle_bin import empty_recycle_bin
    from syslens.cleaner.browser_cleaner import clean_browser_cache
    from syslens.cleaner.disk_optimizer import analyze_disk
    from syslens.cleaner.engine import run_cleanup

    # Safety checks
    assert safety_check("c:\\temp") is True
    assert safety_check("c:\\windows\\system32") is False
    assert safety_check("hklm\\registry") is False
    assert safety_check("c:\\drivers\\ethernet") is False

    # Temp cleaner
    temp_res = clean_temp_files()
    assert temp_res["task"] == "TEMP_CLEAN"
    assert temp_res["status"] == "completed"
    assert "files_removed" in temp_res

    # Recycle bin
    rb_res = empty_recycle_bin()
    assert rb_res["task"] == "RECYCLE_BIN"
    assert rb_res["status"] in ["completed", "skipped", "failed"]

    # Browser Cache
    browser_res = clean_browser_cache()
    assert browser_res["task"] == "BROWSER_CACHE"
    assert "folders_cleaned" in browser_res

    # Disk optimizer
    disk_res = analyze_disk()
    assert disk_res["task"] == "DISK_ANALYSIS"
    assert "used_percent" in disk_res
    assert "recommendation" in disk_res

    # Run cleanup safe
    results = run_cleanup(mode="safe")
    tasks = [r["task"] for r in results]
    assert "TEMP_CLEAN" in tasks
    assert "RECYCLE_BIN" in tasks
    assert "DISK_ANALYSIS" in tasks
    assert "BROWSER_CACHE" not in tasks

    # Run cleanup full
    results_full = run_cleanup(mode="full")
    tasks_full = [r["task"] for r in results_full]
    assert "BROWSER_CACHE" in tasks_full

def test_optimizer_engine():
    """Verify that optimizer modules, power schemes, profiles, auto-fixes, and rollback history function correctly."""
    from syslens.optimizer.safety_guard import validate_action
    from syslens.optimizer.profiles import get_profile
    from syslens.optimizer.auto_fix import apply_safe_fixes
    from syslens.optimizer.scheduler import schedule_cleanup, stop_scheduler
    from syslens.optimizer.rollback import rollback_last
    from syslens.optimizer.engine import optimize

    # Safety guard
    assert validate_action("registry_edit") is False
    assert validate_action("cpu_optimization") is True

    # Profiles
    p_gaming = get_profile("gaming")
    assert p_gaming["cpu_boost"] is True
    assert p_gaming["power_mode"] == "high_performance"

    p_battery = get_profile("battery")
    assert p_battery["power_mode"] == "power_saver"

    # Auto fixes
    fixes_low = apply_safe_fixes(cpu_override=10.0, mem_override=20.0)
    assert len(fixes_low) == 0

    fixes_high = apply_safe_fixes(cpu_override=90.0, mem_override=85.0)
    assert len(fixes_high) == 2
    types = [f["type"] for f in fixes_high]
    assert "CPU_OPTIMIZATION" in types
    assert "MEMORY_OPTIMIZATION" in types

    # Scheduler
    sched_res = schedule_cleanup(interval=10)
    assert sched_res["status"] == "scheduler_started"
    stop_res = stop_scheduler()
    assert stop_res["status"] == "scheduler_stopped"

    # Engine optimization & rollback
    opt_res = optimize(mode="safe", cpu_override=95.0, mem_override=90.0)
    assert opt_res["status"] == "completed"
    assert opt_res["mode"] == "safe"

    # Rollback last action
    roll_res = rollback_last()
    assert roll_res["status"] == "rollback_executed"
    assert roll_res["reverted_action"]["mode"] == "safe"


def test_dashboard_process_kill():
    """Verify process termination endpoints and safety blocks in dashboard API."""
    from syslens.dashboard.app import post_kill_process
    from fastapi import HTTPException
    from unittest.mock import MagicMock, patch
    import os
    import psutil
    import pytest
    
    # 1. Test safety blocks (PID <= 4)
    with pytest.raises(HTTPException) as excinfo:
        post_kill_process(0)
    assert excinfo.value.status_code == 400
    assert "system process" in excinfo.value.detail.lower()
    
    with pytest.raises(HTTPException) as excinfo:
        post_kill_process(4)
    assert excinfo.value.status_code == 400
    assert "system process" in excinfo.value.detail.lower()
    
    # 2. Test safety block for SysLens itself (PID = current process)
    my_pid = os.getpid()
    with pytest.raises(HTTPException) as excinfo:
        post_kill_process(my_pid)
    assert excinfo.value.status_code == 400
    assert "cannot terminate the syslens process" in excinfo.value.detail.lower()
    
    # 3. Test safety block for svchost or system processes via mock
    mock_proc_sys = MagicMock()
    mock_proc_sys.name.return_value = "svchost.exe"
    
    with patch("psutil.Process", return_value=mock_proc_sys):
        with pytest.raises(HTTPException) as excinfo:
            post_kill_process(12345)
        assert excinfo.value.status_code == 400
        assert "protected system process" in excinfo.value.detail.lower()
        mock_proc_sys.kill.assert_not_called()
        
    # 4. Test successful termination
    mock_proc_ok = MagicMock()
    mock_proc_ok.name.return_value = "notepad.exe"
    
    with patch("psutil.Process", return_value=mock_proc_ok):
        res = post_kill_process(12345)
        assert res["status"] == "success"
        assert res["pid"] == 12345
        mock_proc_ok.kill.assert_called_once()
        
    # 5. Test non-existent PID
    with patch("psutil.Process", side_effect=psutil.NoSuchProcess(12345)):
        with pytest.raises(HTTPException) as excinfo:
            post_kill_process(12345)
        assert excinfo.value.status_code == 404
        
    # 6. Test Access Denied
    with patch("psutil.Process", side_effect=psutil.AccessDenied(12345)):
        with pytest.raises(HTTPException) as excinfo:
            post_kill_process(12345)
        assert excinfo.value.status_code == 403


def test_dashboard_playbook():
    """Verify that playbook endpoints yield correct catalog and execution outputs."""
    from syslens.dashboard.app import get_playbook_commands, post_run_playbook_command
    from fastapi import HTTPException
    from unittest.mock import MagicMock, patch
    import pytest
    import asyncio
    
    # 1. Test get_playbook_commands
    cmds_res = get_playbook_commands()
    assert "commands" in cmds_res
    assert "is_admin" in cmds_res
    commands = cmds_res["commands"]
    assert len(commands) > 0
    sfc = next((c for c in commands if c["id"] == "sfc_scannow"), None)
    assert sfc is not None
    assert sfc["category"] == "repair"
    assert sfc["type"] == "cli"
    assert sfc["requires_admin"] is True
    
    # 2. Test non-existent command ID run
    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(post_run_playbook_command("invalid_cmd"))
    assert excinfo.value.status_code == 404
    
    # 3. Test GUI command execution
    with patch("subprocess.Popen") as mock_popen:
        res = asyncio.run(post_run_playbook_command("open_resmon"))
        assert res["status"] == "success"
        mock_popen.assert_called_once()
        
    # 4. Test CLI command execution (returns StreamingResponse)
    mock_proc = MagicMock()
    
    readline_responses = [b"Line 1\n", b"Line 2\n", b""]
    async def mock_readline():
        return readline_responses.pop(0)
    mock_proc.stdout.readline.side_effect = mock_readline
    mock_proc.wait = MagicMock()
    
    # Wait is a coroutine, so it must return a future or waitable
    async def mock_wait():
        return 0
    mock_proc.wait.side_effect = mock_wait
    mock_proc.returncode = 0
    
    with patch("asyncio.create_subprocess_shell", return_value=mock_proc) as mock_shell:
        stream_res = asyncio.run(post_run_playbook_command("ping_test"))
        
        async def read_stream():
            lines = []
            async for chunk in stream_res.body_iterator:
                lines.append(chunk)
            return lines
            
        lines = asyncio.run(read_stream())
        assert len(lines) > 0
        assert "Line 1\n" in lines
        assert "Line 2\n" in lines
        assert "\n[Process completed with exit code 0]\n" in lines
        mock_shell.assert_called_once()
        
    # 5. Test CLI command execution requiring admin when not admin
    mock_proc_admin = MagicMock()
    readline_responses_admin = [b"Line A\n", b""]
    async def mock_readline_admin():
        return readline_responses_admin.pop(0)
    mock_proc_admin.stdout.readline.side_effect = mock_readline_admin
    mock_proc_admin.wait = MagicMock()
    async def mock_wait_admin():
        return 0
    mock_proc_admin.wait.side_effect = mock_wait_admin
    mock_proc_admin.returncode = 0

    with patch("syslens.utils.admin.is_admin", return_value=False):
        with patch("asyncio.create_subprocess_shell", return_value=mock_proc_admin) as mock_shell_admin:
            stream_res_admin = asyncio.run(post_run_playbook_command("sfc_scannow"))
            
            async def read_stream_admin():
                lines = []
                async for chunk in stream_res_admin.body_iterator:
                    lines.append(chunk)
                return lines
                
            lines_admin = asyncio.run(read_stream_admin())
            assert len(lines_admin) > 0
            assert any("SysLens Elevation Manager" in line for line in lines_admin)
            mock_shell_admin.assert_called_once()


def test_dashboard_server_elevation():
    """Verify the server self-elevation route logic."""
    from syslens.dashboard.app import post_elevate_server
    from fastapi import HTTPException
    from unittest.mock import patch, MagicMock
    import pytest
    import os

    # 1. Test when already running as admin
    with patch("syslens.utils.admin.is_admin", return_value=True):
        res = post_elevate_server()
        assert res["status"] == "success"
        assert "Already running" in res["message"]

    # 2. Test when not running as admin on Windows (should request UAC and start exit timer)
    with patch("syslens.utils.admin.is_admin", return_value=False):
        with patch("os.name", "nt"):
            with patch("ctypes.windll.shell32.ShellExecuteW") as mock_execute:
                res = post_elevate_server()
                assert res["status"] == "success"
                assert "UAC elevation requested" in res["message"]
                mock_execute.assert_called_once()

    # 3. Test when not running as admin on Unix (should raise 400 error)
    with patch("syslens.utils.admin.is_admin", return_value=False):
        with patch("os.name", "posix"):
            with pytest.raises(HTTPException) as excinfo:
                post_elevate_server()
            assert excinfo.value.status_code == 400
            assert "only supported on Windows" in excinfo.value.detail


def test_syslens_improvements():
    """Verify time-aware baselines, config loader, broader anomaly scopes, native Windows memory, dry-runs, dev caches, and safety check."""
    import os
    import tempfile
    import time
    from unittest.mock import patch, MagicMock
    from pathlib import Path
    
    from syslens.utils.config import load_config
    from syslens.engine.baseline import BehaviorBaseline
    from syslens.engine.detector import AnomalyDetector
    from syslens.optimizer.auto_fix import apply_safe_fixes
    from syslens.cleaner.dev_cache import clean_dev_caches
    from syslens.cleaner.safety import safety_check
    
    # 1. Test Config Loader (defaults and environment variables overrides)
    conf = load_config()
    assert conf["cpu_z_low"] == 2.0
    assert conf["mem_z_low"] == 2.0
    
    with patch.dict(os.environ, {"SYSLENS_CPU_Z_LOW": "4.5", "SYSLENS_MEM_Z_LOW": "3.5"}):
        conf_overridden = load_config()
        assert conf_overridden["cpu_z_low"] == 4.5
        assert conf_overridden["mem_z_low"] == 3.5

    # 2. Test Time-Aware Baseline Bins & Broader Metrics
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        tmp_path = tmp.name
    try:
        baseline = BehaviorBaseline(filepath=tmp_path)
        # Verify new keys in self.stats
        assert "active_connections" in baseline.stats
        assert "gpu_utilization" in baseline.stats
        assert "swap_usage_percent" in baseline.stats
        
        # Inject mock diurnal data points for hour=10
        for i in range(12):
            baseline.update({
                "timestamp": 1700000000.0 + i, # will translate to a specific hour
                "cpu": {"usage_percent": 15.0},
                "memory": {"usage_percent": 30.0, "swap_usage_percent": 5.0},
                "disk": {"read_bytes": 0, "write_bytes": 0},
                "plugins_data": {
                    "network_telemetry": {"active_connections": 50},
                    "gpu_analyzer": {"available": True, "utilization_gpu_percent": 12.0}
                }
            })
            
        # Extract the hour from one of these timestamps
        import time as pytime
        h = pytime.localtime(1700000000.0).tm_hour
        h_str = str(h)
        
        # Verify diurnal stats were calculated for this hour
        assert h_str in baseline.diurnal_stats
        assert baseline.diurnal_stats[h_str]["cpu"]["mean"] == 15.0
        assert baseline.diurnal_stats[h_str]["gpu_utilization"]["mean"] == 12.0
        
        # Querying diurnal stats
        stats_h = baseline.get_stats(h)
        assert stats_h["cpu"]["mean"] == 15.0
        
        # Querying stats for a hour without enough data (should fall back to global stats)
        stats_other = baseline.get_stats((h + 1) % 24)
        assert stats_other == baseline.stats

        # 3. Test Configurable Detector & Broader Anomaly Scopes
        detector = AnomalyDetector(baseline)
        # Mock connection spike
        metrics_spike = {
            "timestamp": 1700000015.0,
            "cpu": {"usage_percent": 15.0},
            "memory": {"usage_percent": 30.0, "swap_usage_percent": 99.0}, # Swap spike!
            "disk": {"read_bytes": 0, "write_bytes": 0},
            "plugins_data": {
                "network_telemetry": {"active_connections": 999}, # Connections spike!
                "gpu_analyzer": {"available": True, "utilization_gpu_percent": 98.0} # GPU spike!
            }
        }
        
        anomalies = detector.analyze(metrics_spike)
        metric_names = [a["metric"] for a in anomalies]
        assert "active_connections" in metric_names
        assert "gpu_utilization" in metric_names
        assert "swap_usage_percent" in metric_names
        
        # Verify configured Z-scores are respected
        with patch.object(detector, "config", {"net_conn_z_low": 100.0, "gpu_z_low": 100.0, "swap_z_low": 100.0}):
            # Thresholds are very high, but raw bounds should still catch it if raw bounds are met (e.g. connections > 350)
            anoms_high_z = detector.analyze(metrics_spike)
            # Active connections has raw bound > 350 so it's still flagged
            assert "active_connections" in [a["metric"] for a in anoms_high_z]
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # 4. Test Windows Standby List / Process Priority Dry-Run
    # Priority auto-fixes under dry-run
    fixes_dry = apply_safe_fixes(cpu_override=99.0, mem_override=95.0, dry_run=True)
    assert len(fixes_dry) == 2
    assert fixes_dry[0]["status"] == "dry_run"
    assert fixes_dry[1]["status"] == "dry_run"

    # Memory standby list flush privilege Windows NT call check (mocked NtSetSystemInformation)
    with patch("os.name", "nt"):
        with patch("ctypes.windll.ntdll.NtSetSystemInformation", return_value=0) as mock_ntset:
            fixes_mocked = apply_safe_fixes(cpu_override=10.0, mem_override=95.0, dry_run=False)
            assert len(fixes_mocked) == 1
            assert fixes_mocked[0]["status"] == "recommended_applied"
            mock_ntset.assert_called_once()

    # 5. Test Developer Cache Cleanups
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a mock git repository directory to be skipped
        git_dir = Path(tmpdir) / ".git"
        git_dir.mkdir()
        git_file = git_dir / "config"
        git_file.write_text("dummy content")
        
        # Create stale pycache directory
        pycache_dir = Path(tmpdir) / "__pycache__"
        pycache_dir.mkdir()
        pycache_file = pycache_dir / "foo.pyc"
        pycache_file.write_text("pyc bytes")
        
        # Set modification time to 10 days ago (stale)
        old_time = time.time() - (10 * 86400)
        os.utime(pycache_dir, (old_time, old_time))
        os.utime(pycache_file, (old_time, old_time))
        
        # Change current working directory to temp dir to test clean_dev_caches
        with patch("os.getcwd", return_value=tmpdir):
            # Test dry-run
            res_dry = clean_dev_caches(dry_run=True, age_days=7)
            assert res_dry["folders_cleaned"] == 1
            assert res_dry["status"] == "dry_run"
            assert pycache_dir.exists()
            assert git_dir.exists() # git is always protected
            
            # Test execution
            res_real = clean_dev_caches(dry_run=False, age_days=7)
            assert res_real["folders_cleaned"] == 1
            assert res_real["status"] == "completed"
            assert not pycache_dir.exists()
            assert git_dir.exists()

    # 6. Test Stricter Traversal Safety Checks
    assert safety_check("c:\\temp") is True
    # Test resolved traversal tricks
    assert safety_check("c:\\windows\\temp\\..\\system32") is False
    assert safety_check("c:\\windows\\system32") is False
    assert safety_check("c:\\drivers") is False
    # Root paths
    assert safety_check("c:\\") is False
    assert safety_check("/") is False

    # 7. Test Playbook Intelligent Guidance
    from syslens.dashboard.playbook_guide import get_playbook_suggestion
    
    # Test UAC cancel
    sug_cancel = get_playbook_suggestion("sfc_scannow", "UAC cancelled", 1)
    assert "UAC elevation" in sug_cancel
    
    # Test sfc healthy
    sug_sfc_ok = get_playbook_suggestion("sfc_scannow", "Windows Resource Protection did not find any integrity violations.", 0)
    assert "No system file corruption detected" in sug_sfc_ok
    
    # Test sfc fixed
    sug_sfc_fixed = get_playbook_suggestion("sfc_scannow", "Windows Resource Protection found corrupt files and successfully repaired them.", 0)
    assert "successfully repaired!" in sug_sfc_fixed
    
    # Test sfc failed to repair
    sug_sfc_fail = get_playbook_suggestion("sfc_scannow", "Windows Resource Protection found corrupt files but was unable to fix some of them.", 0)
    assert "could not be repaired" in sug_sfc_fail
    
    # Test dism restore
    sug_dism = get_playbook_suggestion("dism_restore", "The operation completed successfully.", 0)
    assert "repaired" in sug_dism.lower() and "successfully" in sug_dism.lower()
    
    # Test ping test
    sug_ping = get_playbook_suggestion("ping_test", "Packets: Sent = 4, Received = 4, Lost = 0 (0% loss)", 0)
    assert "0% packet loss" in sug_ping





