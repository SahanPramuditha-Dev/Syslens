"""
SysLens CLI entry-point.

This module is intentionally thin: it only parses arguments and delegates
each subcommand to the corresponding module in ``syslens.commands``.

Command modules
---------------
``syslens.commands.scan``      — ``syslens scan``
``syslens.commands.health``    — ``syslens health``
``syslens.commands.live``      — ``syslens live``
``syslens.commands.suggest``   — ``syslens suggest``
``syslens.commands.clean``     — ``syslens clean``
``syslens.commands.optimize``  — ``syslens optimize``
``syslens.commands.schedule``  — ``syslens schedule``
``syslens.commands.rollback``  — ``syslens rollback``
``syslens.commands.export``    — ``syslens export``
``syslens.commands.serve``     — ``syslens serve``
"""
import argparse

from syslens.core.anomaly import AnomalyInterface
from syslens.core.health import SystemHealthEngine
from syslens.plugins.manager import PluginManager


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="syslens",
        description="SysLens v1.0 — Developer Observability & Diagnostics CLI",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>", help="Available subcommands")

    # scan
    scan_p = sub.add_parser("scan", help="Full system telemetry snapshot")
    scan_p.add_argument("--json", action="store_true", help="Output raw JSON instead of formatted view")

    # health
    sub.add_parser("health", help="Run diagnostics & health checklist")

    # live
    sub.add_parser("live", help="Real-time split-pane terminal dashboard")

    # suggest
    sub.add_parser("suggest", help="Optimization suggestions report")

    # clean
    clean_p = sub.add_parser("clean", help="Auto-clean temp files, recycle bin, browser cache")
    clean_p.add_argument("--mode", default="safe", choices=["safe", "full"],
                         help="safe = temp+recycle; full = also cleans browser cache")
    clean_p.add_argument("--dry-run", action="store_true",
                         help="Audit and display actions without modifying files")

    # optimize
    opt_p = sub.add_parser("optimize", help="Profile-based system optimization")
    opt_p.add_argument("--profile", default="safe",
                       choices=["safe", "gaming", "dev", "battery"],
                       help="Optimization profile to apply")
    opt_p.add_argument("--dry-run", action="store_true",
                         help="Audit and display actions without applying optimization fixes")

    # schedule
    sched_p = sub.add_parser("schedule", help="Schedule recurring background cleanups")
    sched_p.add_argument("--interval", type=int, default=3600,
                         help="Cleanup interval in seconds (default: 3600)")

    # rollback
    sub.add_parser("rollback", help="Undo the last optimization action")

    # export
    exp_p = sub.add_parser("export", help="Export telemetry snapshot to HTML report")
    exp_p.add_argument("--output", default="syslens_report.html",
                       help="Output HTML file path (default: syslens_report.html)")

    # serve
    sub.add_parser("serve", help="Launch FastAPI web dashboard on http://127.0.0.1:8000")

    return parser


def main() -> None:
    """Parse CLI arguments and dispatch to the appropriate command module."""
    parser = _build_parser()
    args   = parser.parse_args()

    # Lazy-import shared subsystems (avoids import overhead for e.g. --help)
    anomaly_interface = AnomalyInterface()
    health_engine     = SystemHealthEngine()
    plugin_manager    = PluginManager()

    cmd = args.command

    if cmd == "scan":
        from syslens.commands import scan
        scan.run(anomaly_interface, plugin_manager, health_engine, output_json=args.json)

    elif cmd == "health":
        from syslens.commands import health
        health.run(anomaly_interface, plugin_manager, health_engine)

    elif cmd == "live":
        from syslens.commands import live
        live.run(anomaly_interface, plugin_manager, health_engine)

    elif cmd == "suggest":
        from syslens.commands import suggest
        suggest.run(anomaly_interface)

    elif cmd == "clean":
        from syslens.commands import clean
        clean.run(mode=args.mode, dry_run=args.dry_run)

    elif cmd == "optimize":
        from syslens.commands import optimize
        optimize.run(profile=args.profile, dry_run=args.dry_run)

    elif cmd == "schedule":
        from syslens.commands import schedule
        schedule.run(interval=args.interval)

    elif cmd == "rollback":
        from syslens.commands import rollback
        rollback.run()

    elif cmd == "export":
        from syslens.commands import export
        export.run(anomaly_interface, plugin_manager, health_engine, output=args.output)

    elif cmd == "serve":
        from syslens.commands import serve
        serve.run()

    else:
        # Default: full scan when no subcommand is given
        from syslens.commands import scan
        scan.run(anomaly_interface, plugin_manager, health_engine)


if __name__ == "__main__":
    main()
