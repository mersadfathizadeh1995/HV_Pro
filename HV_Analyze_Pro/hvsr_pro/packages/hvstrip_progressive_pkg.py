"""
Bridge module for importing HV_Strip_Progressive from the hvstrip-progressive folder.

The folder name contains a hyphen which is not valid in Python identifiers,
so we add the parent directory to sys.path and import directly.
"""
import sys
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent / 'hvstrip-progressive' / 'HV_Strip_Progressive'

if str(_pkg_dir.parent) not in sys.path:
    sys.path.insert(0, str(_pkg_dir.parent))

_import_error = None
try:
    import HV_Strip_Progressive as _mod
    HVStripWindow = _mod.HVStripWindow
except Exception as _e:
    HVStripWindow = None
    _import_error = _e


def get_import_error():
    """Return the exception that prevented import, or None if successful."""
    return _import_error
