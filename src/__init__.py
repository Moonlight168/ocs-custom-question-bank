"""OCS API server package.

The explicit imports below help PyInstaller's static analyzer discover
`config` and `server` as members of this package, even when packaging
`run.py` (which sits one level up and imports from this package).
"""
from src import config, server

__all__ = ["config", "server"]
