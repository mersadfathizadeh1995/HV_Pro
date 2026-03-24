"""Bridge module to import Invert_HVSR from the submodule.

This handles the hyphenated/submodule folder name and provides
a clean import interface for the main HV Pro application.
"""

import sys
from pathlib import Path

# Store any import error for later display
_import_error = None
MainWindow = None

try:
    # Add the invert_hvsr submodule to sys.path if needed
    _pkg_dir = Path(__file__).parent / "invert_hvsr"
    if _pkg_dir.exists() and str(_pkg_dir) not in sys.path:
        sys.path.insert(0, str(_pkg_dir))
    
    # Import the main window class
    from invert_hvsr.gui.main_window import MainWindow
    
except ImportError as e:
    _import_error = str(e)
    MainWindow = None


def get_import_error() -> str:
    """Return any import error message, or empty string if successful."""
    return _import_error or ""


def is_available() -> bool:
    """Check if the Invert HVSR module is available."""
    return MainWindow is not None
