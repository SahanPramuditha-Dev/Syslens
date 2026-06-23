"""
SysLens CLI commands package.

Each subcommand lives in its own module for maintainability:
  - _shared.py   : Console, symbols, and shared helpers used by all commands
  - scan.py      : `syslens scan`
  - health.py    : `syslens health`
  - live.py      : `syslens live`
  - suggest.py   : `syslens suggest`
  - clean.py     : `syslens clean`
  - optimize.py  : `syslens optimize`
  - schedule.py  : `syslens schedule`
  - rollback.py  : `syslens rollback`
  - export.py    : `syslens export`
  - serve.py     : `syslens serve`
"""

__all__ = [
    "scan",
    "health",
    "live",
    "suggest",
    "clean",
    "optimize",
    "schedule",
    "rollback",
    "export",
    "serve",
]
