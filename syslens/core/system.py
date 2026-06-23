import os
import platform
import socket
import time
from typing import Any, Dict, List
import psutil

class SystemMetricsCollector:
    """Collector for system hardware, OS telemetry, and process execution snapshots."""

    @staticmethod
    def get_os_metadata() -> Dict[str, Any]:
        """Detect OS and hardware metadata information."""
        try:
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
        except Exception:
            boot_time = 0.0
            uptime = 0.0

        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            hostname = "unknown"
            local_ip = "127.0.0.1"

        return {
            "os_name": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "architecture": platform.machine(),
            "processor": platform.processor(),
            "hostname": hostname,
            "local_ip": local_ip,
            "boot_time": boot_time,
            "uptime_seconds": uptime
        }

    @staticmethod
    def get_cpu_metrics() -> Dict[str, Any]:
        """Track CPU statistics in real-time."""
        try:
            # We don't block. We do a non-blocking check, but a blocking check of 0.1s could be used if needed.
            # Usually psutil.cpu_percent(interval=None) returns percent since last call.
            # To get a quick real-time metric, we do interval=0.1
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_per_cpu = psutil.cpu_percent(interval=None, percpu=True)
            freq = psutil.cpu_freq()
            cpu_freq_current = freq.current if freq else 0.0
            cpu_freq_max = freq.max if freq else 0.0
        except Exception:
            cpu_percent = 0.0
            cpu_per_cpu = []
            cpu_freq_current = 0.0
            cpu_freq_max = 0.0

        return {
            "logical_cores": psutil.cpu_count(logical=True),
            "physical_cores": psutil.cpu_count(logical=False),
            "usage_percent": cpu_percent,
            "cores_usage_percent": cpu_per_cpu,
            "frequency_mhz_current": cpu_freq_current,
            "frequency_mhz_max": cpu_freq_max
        }

    @staticmethod
    def get_memory_metrics() -> Dict[str, Any]:
        """Analyze physical and swap memory utilization."""
        try:
            vm = psutil.virtual_memory()
            swap = psutil.swap_memory()
        except Exception:
            return {
                "total_bytes": 0, "available_bytes": 0, "used_bytes": 0, "usage_percent": 0.0,
                "swap_total_bytes": 0, "swap_used_bytes": 0, "swap_usage_percent": 0.0
            }

        return {
            "total_bytes": vm.total,
            "available_bytes": vm.available,
            "used_bytes": vm.used,
            "usage_percent": vm.percent,
            "swap_total_bytes": swap.total,
            "swap_used_bytes": swap.used,
            "swap_usage_percent": swap.percent
        }

    @staticmethod
    def get_disk_metrics() -> Dict[str, Any]:
        """Monitor disk utilization, capacities, and read/write I/O performance."""
        partitions_data = []
        try:
            partitions = psutil.disk_partitions(all=False)
            for p in partitions:
                # Avoid network drives or empty CD-ROM drives on Windows
                if 'cdrom' in p.opts or not p.device:
                    continue
                try:
                    usage = psutil.disk_usage(p.mountpoint)
                    partitions_data.append({
                        "device": p.device,
                        "mountpoint": p.mountpoint,
                        "fstype": p.fstype,
                        "total_bytes": usage.total,
                        "used_bytes": usage.used,
                        "free_bytes": usage.free,
                        "usage_percent": usage.percent
                    })
                except PermissionError:
                    # Ignore inaccessible partitions
                    continue
                except Exception:
                    continue
        except Exception:
            pass

        try:
            io = psutil.disk_io_counters()
            read_bytes = io.read_bytes if io else 0
            write_bytes = io.write_bytes if io else 0
        except Exception:
            read_bytes = 0
            write_bytes = 0

        return {
            "partitions": partitions_data,
            "read_bytes": read_bytes,
            "write_bytes": write_bytes
        }

    @staticmethod
    def get_process_snapshot(limit: int = 10) -> List[Dict[str, Any]]:
        """Inspect running processes, sort by CPU + memory footprint to locate hogs."""
        processes = []
        attrs = ['pid', 'name', 'username', 'status', 'cpu_percent', 'memory_info', 'memory_percent']
        for proc in psutil.process_iter(attrs=attrs):
            try:
                info = proc.info
                # Skip System Idle Process (PID 0) which reports cumulative idle core time
                if info['pid'] == 0:
                    continue
                
                cpu = info.get('cpu_percent') or 0.0
                mem_info = info.get('memory_info')
                mem_bytes = mem_info.rss if mem_info else 0
                mem_percent = info.get('memory_percent') or 0.0

                processes.append({
                    "pid": info['pid'],
                    "name": info['name'] or "Unknown",
                    "username": info['username'] or "N/A",
                    "status": info['status'] or "N/A",
                    "cpu_percent": round(cpu, 2),
                    "memory_bytes": mem_bytes,
                    "memory_percent": round(mem_percent, 2)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            except Exception:
                continue

        # Sort by CPU usage first, then Memory usage, descending
        processes.sort(key=lambda x: (x["cpu_percent"], x["memory_percent"]), reverse=True)
        return processes[:limit]

    def collect_all(self, process_limit: int = 10) -> Dict[str, Any]:
        """Collect unified system snapshot telemetry."""
        return {
            "timestamp": time.time(),
            "os": self.get_os_metadata(),
            "cpu": self.get_cpu_metrics(),
            "memory": self.get_memory_metrics(),
            "disk": self.get_disk_metrics(),
            "processes": self.get_process_snapshot(limit=process_limit)
        }

def get_system_info() -> Dict[str, Any]:
    """Retrieve current system metrics summary (SDK Integration)."""
    collector = SystemMetricsCollector()
    cpu = collector.get_cpu_metrics()
    mem = collector.get_memory_metrics()
    disk = collector.get_disk_metrics()
    
    # Calculate aggregate disk usage percent
    disk_usage = 0.0
    if disk.get("partitions"):
        disk_usage = max(p.get("usage_percent", 0.0) for p in disk.get("partitions"))
        
    return {
        "cpu_usage": cpu.get("usage_percent", 0.0),
        "memory_usage": mem.get("usage_percent", 0.0),
        "disk_usage": disk_usage,
        "raw": collector.collect_all()
    }
