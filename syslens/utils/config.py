import os

DEFAULTS = {
    "cpu_z_low": 2.0,
    "cpu_z_medium": 2.5,
    "cpu_z_high": 3.5,
    "cpu_usage_low": 85.0,
    "cpu_usage_medium": 75.0,
    "cpu_usage_high": 90.0,

    "mem_z_low": 2.0,
    "mem_z_medium": 2.3,
    "mem_z_high": 3.0,
    "mem_usage_low": 85.0,
    "mem_usage_medium": 80.0,
    "mem_usage_high": 90.0,

    "disk_read_z_low": 3.0,
    "disk_read_z_medium": 4.0,
    "disk_read_z_high": 5.0,

    "disk_write_z_low": 3.0,
    "disk_write_z_medium": 4.0,
    "disk_write_z_high": 5.0,

    "net_conn_z_low": 2.0,
    "net_conn_z_medium": 3.0,
    "net_conn_z_high": 4.0,

    "gpu_z_low": 2.0,
    "gpu_z_medium": 3.0,
    "gpu_z_high": 4.0,

    "swap_z_low": 2.0,
    "swap_z_medium": 3.0,
    "swap_z_high": 4.0,
}

def load_config() -> dict:
    """Loads configuration settings from files or environment variables, falling back to defaults."""
    config = DEFAULTS.copy()

    # Define paths to load from (highest priority is current working directory)
    paths = [
        os.path.join(os.path.expanduser("~"), ".syslens", "config.toml"),
        os.path.join(os.getcwd(), ".syslens.toml")
    ]

    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, "r") as f:
                    for line in f:
                        line = line.split("#")[0].strip()
                        if not line or line.startswith("["):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip().lower()
                            v = v.strip().strip('"').strip("'")
                            if k in config:
                                if v.lower() == "true":
                                    config[k] = True
                                elif v.lower() == "false":
                                    config[k] = False
                                else:
                                    try:
                                        config[k] = float(v) if "." in v else int(v)
                                    except ValueError:
                                        config[k] = v
            except Exception:
                pass

    # Override with environment variables (e.g. SYSLENS_CPU_Z_LOW)
    for k in config:
        env_key = f"SYSLENS_{k.upper()}"
        if env_key in os.environ:
            val = os.environ[env_key]
            if val.lower() == "true":
                config[k] = True
            elif val.lower() == "false":
                config[k] = False
            else:
                try:
                    config[k] = float(val) if "." in val else int(val)
                except ValueError:
                    config[k] = val

    return config
