"""
Data Adapter
=============

Bridge between hvsr_pro.loaders and the batch processing workflow.

Provides:
- Auto-format detection and loading via hvsr_pro loaders
- Conversion from SeismicData -> (Z, N, E) numpy arrays
- Qt file dialog filter string for all supported formats
- Fallback to ObsPy for MiniSEED if hvsr_pro is unavailable
"""

import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List

# ── hvsr_pro loader availability ──

_LOADERS_AVAILABLE = False
_import_error_msg = ""

try:
    from hvsr_pro.loaders import (
        detect_format,
        get_loader_for_extension,
        get_file_filter,
        get_all_extensions,
        get_supported_formats,
        FORMAT_INFO,
    )
    from hvsr_pro.core.data_structures import SeismicData
    _LOADERS_AVAILABLE = True
except ImportError as e:
    _import_error_msg = str(e)


def is_available() -> bool:
    """Check if hvsr_pro loaders are available."""
    return _LOADERS_AVAILABLE


def get_import_error() -> str:
    """Return the import error message if loaders are not available."""
    return _import_error_msg


# =====================================================================
#  Format Detection & Loading
# =====================================================================

def load_seismic_file(filepath: str, **kwargs) -> Optional[Any]:
    """Load a seismic file using hvsr_pro loaders.

    Auto-detects format from extension, instantiates the correct loader,
    and returns a SeismicData object.

    Parameters
    ----------
    filepath : str
        Path to the seismic data file.
    **kwargs
        Additional keyword arguments passed to the loader's load_file method.

    Returns
    -------
    SeismicData or None
        Loaded data, or None if loading failed.

    Raises
    ------
    ImportError
        If hvsr_pro loaders are not available.
    ValueError
        If the file format is not recognized.
    """
    if not _LOADERS_AVAILABLE:
        raise ImportError(
            f"hvsr_pro loaders not available: {_import_error_msg}"
        )

    fmt = detect_format(filepath)
    if fmt is None:
        raise ValueError(f"Unrecognized file format: {filepath}")

    info = FORMAT_INFO.get(fmt)
    if info is None:
        raise ValueError(f"No format info for: {fmt}")

    loader_cls = info['loader_class']
    loader = loader_cls()

    return loader.load_file(filepath, **kwargs)


def seismic_to_arrays(seismic_data) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Convert a SeismicData object to (Z, N, E) numpy arrays.

    Parameters
    ----------
    seismic_data : SeismicData
        Three-component seismic data from hvsr_pro loader.

    Returns
    -------
    (Array1Z, Array1N, Array1E, fs) : tuple
        Z, N, E component arrays (1D float64) and sampling rate in Hz.
    """
    z = seismic_data.vertical.data.astype(np.float64)
    n = seismic_data.north.data.astype(np.float64)
    e = seismic_data.east.data.astype(np.float64)
    fs = float(seismic_data.sampling_rate)
    return z, n, e, fs


def load_and_convert(filepath: str, **kwargs) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Load a file and return (Z, N, E, fs) arrays directly.

    Convenience function combining load_seismic_file + seismic_to_arrays.

    Parameters
    ----------
    filepath : str
        Path to the seismic data file.

    Returns
    -------
    (Array1Z, Array1N, Array1E, fs) : tuple
    """
    data = load_seismic_file(filepath, **kwargs)
    return seismic_to_arrays(data)


# =====================================================================
#  File Dialog Filters
# =====================================================================

def get_file_dialog_filter() -> str:
    """Get Qt file dialog filter string for all supported formats.

    Falls back to MiniSEED-only if hvsr_pro is not available.

    Returns
    -------
    str
        Filter string for QFileDialog.getOpenFileNames().
    """
    if _LOADERS_AVAILABLE:
        return get_file_filter(single_file_only=False)
    else:
        return "MiniSEED Files (*.mseed *.miniseed);;All Files (*.*)"


def get_single_file_filter() -> str:
    """Get filter for single-file formats only (excludes SAC, PEER)."""
    if _LOADERS_AVAILABLE:
        return get_file_filter(single_file_only=True)
    else:
        return "MiniSEED Files (*.mseed *.miniseed);;All Files (*.*)"


def get_supported_extensions() -> List[str]:
    """Get all supported file extensions.

    Returns
    -------
    list of str
        Extensions like ['.mseed', '.miniseed', '.saf', '.sac', ...]
    """
    if _LOADERS_AVAILABLE:
        return get_all_extensions()
    else:
        return ['.mseed', '.miniseed']


# =====================================================================
#  Format Info Queries
# =====================================================================

def get_format_name(filepath: str) -> str:
    """Get human-readable format name for a file.

    Parameters
    ----------
    filepath : str

    Returns
    -------
    str
        Format name like 'MiniSEED', 'SESAME ASCII Format', etc.
        Returns 'Unknown' if not detected.
    """
    if not _LOADERS_AVAILABLE:
        ext = Path(filepath).suffix.lower()
        if ext in ('.mseed', '.miniseed', '.ms'):
            return 'MiniSEED'
        return 'Unknown'

    fmt = detect_format(filepath)
    if fmt and fmt in FORMAT_INFO:
        return FORMAT_INFO[fmt]['name']
    return 'Unknown'


def is_multi_file_format(filepath: str) -> bool:
    """Check if the file requires multiple component files (SAC, PEER).

    Parameters
    ----------
    filepath : str

    Returns
    -------
    bool
        True if format requires 3 separate files for E, N, Z.
    """
    if not _LOADERS_AVAILABLE:
        return False

    fmt = detect_format(filepath)
    if fmt and fmt in FORMAT_INFO:
        return FORMAT_INFO[fmt]['multi_file'] is True
    return False


def is_miniseed(filepath: str) -> bool:
    """Check if a file is MiniSEED format."""
    ext = Path(filepath).suffix.lower()
    return ext in ('.mseed', '.miniseed', '.ms')
