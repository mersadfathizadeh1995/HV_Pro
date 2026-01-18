"""
Data Loaders Module for HVSR Pro
================================

Supports multiple seismic data formats:
- ASCII txt (OSCAR format)
- MiniSEED (via ObsPy)
- SAF (SESAME ASCII Format)
- SAC (Seismic Analysis Code)
- GCF (Guralp Compressed Format)
- PEER (Pacific Earthquake Engineering Research)
- MiniShark (MiniShark seismometer format)
- SeismicRecording3C (hvsrpy JSON format)
"""

from typing import Dict, Any, List, Optional

# Base loader
from hvsr_pro.loaders.base_loader import BaseDataLoader

# Existing loaders
from hvsr_pro.loaders.txt_loader import TxtDataLoader
from hvsr_pro.loaders.miniseed_loader import MiniSeedLoader

# New loaders
from hvsr_pro.loaders.saf_loader import SAFLoader
from hvsr_pro.loaders.sac_loader import SACLoader
from hvsr_pro.loaders.gcf_loader import GCFLoader
from hvsr_pro.loaders.peer_loader import PEERLoader
from hvsr_pro.loaders.minishark_loader import MiniSharkLoader
from hvsr_pro.loaders.srecord3c_loader import SeismicRecording3CLoader

# Configuration
from hvsr_pro.loaders.config import (
    LoaderConfig,
    SAFConfig,
    SACConfig,
    GCFConfig,
    PEERConfig
)

# Utilities
from hvsr_pro.loaders.orientation import (
    orient_traces,
    arrange_traces,
    trim_traces,
    rotate_horizontals,
    detect_component_from_filename,
    auto_assign_components
)

from hvsr_pro.loaders.patterns import (
    extract_saf_header,
    extract_peer_header,
    parse_peer_samples
)

# Preview utilities
from hvsr_pro.loaders.preview import (
    PreviewExtractor,
    PreviewData,
    ChannelPreview,
    get_preview,
)


# ==============================================================================
# Format Information Registry
# ==============================================================================

FORMAT_INFO: Dict[str, Dict[str, Any]] = {
    'txt': {
        'name': 'ASCII Text',
        'extensions': ['.txt', '.dat', '.asc'],
        'multi_file': False,
        'description': 'OSCAR format text files with 4 columns (Time, E, N, Z)',
        'loader_class': TxtDataLoader
    },
    'miniseed': {
        'name': 'MiniSEED',
        'extensions': ['.mseed', '.miniseed', '.ms'],
        'multi_file': 'optional',  # Can be single file or 3 separate files
        'description': 'Standard seismic format (via ObsPy)',
        'loader_class': MiniSeedLoader
    },
    'saf': {
        'name': 'SESAME ASCII Format',
        'extensions': ['.saf'],
        'multi_file': False,
        'description': 'SESAME project standard format for ambient vibration',
        'loader_class': SAFLoader
    },
    'sac': {
        'name': 'SAC',
        'extensions': ['.sac'],
        'multi_file': True,  # Always requires 3 separate files
        'description': 'Seismic Analysis Code format (requires 3 files)',
        'loader_class': SACLoader
    },
    'gcf': {
        'name': 'Guralp GCF',
        'extensions': ['.gcf'],
        'multi_file': False,
        'description': 'Guralp Compressed Format',
        'loader_class': GCFLoader
    },
    'peer': {
        'name': 'PEER NGA',
        'extensions': ['.vt2', '.at2', '.dt2'],
        'multi_file': True,  # Always requires 3 separate files
        'description': 'PEER ground motion database format (requires 3 files)',
        'loader_class': PEERLoader
    },
    'minishark': {
        'name': 'MiniShark',
        'extensions': ['.minishark'],
        'multi_file': False,
        'description': 'MiniShark seismometer format',
        'loader_class': MiniSharkLoader
    },
    'srecord3c': {
        'name': 'SeismicRecording3C (JSON)',
        'extensions': ['.json'],
        'multi_file': False,
        'description': 'hvsrpy JSON serialization format',
        'loader_class': SeismicRecording3CLoader
    }
}


def get_supported_formats() -> List[str]:
    """
    Get list of all supported format names.
    
    Returns:
        List of format identifiers (e.g., ['txt', 'miniseed', 'saf', ...])
    """
    return list(FORMAT_INFO.keys())


def get_format_info(format_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a format.
    
    Args:
        format_name: Format identifier (e.g., 'saf', 'sac')
        
    Returns:
        Dictionary with format information, or None if not found
    """
    return FORMAT_INFO.get(format_name.lower())


def get_all_extensions() -> List[str]:
    """
    Get list of all supported file extensions.
    
    Returns:
        List of extensions (e.g., ['.txt', '.mseed', '.saf', ...])
    """
    extensions = []
    for info in FORMAT_INFO.values():
        extensions.extend(info['extensions'])
    return list(set(extensions))


def get_file_filter(single_file_only: bool = False) -> str:
    """
    Get Qt file dialog filter string for all formats.
    
    Args:
        single_file_only: If True, exclude multi-file formats (SAC, PEER)
        
    Returns:
        Filter string for QFileDialog
    """
    filters = ["All Supported Files ("]
    all_extensions = []
    format_filters = []
    
    for format_id, info in FORMAT_INFO.items():
        # Skip multi-file formats if requested
        if single_file_only and info['multi_file'] is True:
            continue
        
        exts = info['extensions']
        all_extensions.extend([f"*{ext}" for ext in exts])
        
        ext_str = " ".join(f"*{ext}" for ext in exts)
        format_filters.append(f"{info['name']} ({ext_str})")
    
    # Build "All Supported Files" filter
    filters[0] += " ".join(all_extensions) + ")"
    
    # Add individual format filters
    filters.extend(format_filters)
    
    # Add "All Files" at the end
    filters.append("All Files (*)")
    
    return ";;".join(filters)


def get_loader_for_extension(extension: str) -> Optional[type]:
    """
    Get loader class for a file extension.
    
    Args:
        extension: File extension (e.g., '.saf')
        
    Returns:
        Loader class, or None if not found
    """
    ext_lower = extension.lower()
    if not ext_lower.startswith('.'):
        ext_lower = f'.{ext_lower}'
    
    for info in FORMAT_INFO.values():
        if ext_lower in info['extensions']:
            return info['loader_class']
    
    return None


def detect_format(filepath: str) -> Optional[str]:
    """
    Auto-detect file format.
    
    Args:
        filepath: Path to file
        
    Returns:
        Format identifier, or None if not detected
    """
    from pathlib import Path
    
    path = Path(filepath)
    ext_lower = path.suffix.lower()
    
    # First, try extension-based detection
    for format_id, info in FORMAT_INFO.items():
        if ext_lower in info['extensions']:
            return format_id
    
    # If no extension match, try each loader's can_load method
    loaders_to_try = [
        ('srecord3c', SeismicRecording3CLoader),
        ('minishark', MiniSharkLoader),
        ('saf', SAFLoader),
        ('gcf', GCFLoader),
        ('miniseed', MiniSeedLoader),
        ('txt', TxtDataLoader),
    ]
    
    for format_id, loader_class in loaders_to_try:
        try:
            loader = loader_class()
            if loader.can_load(filepath):
                return format_id
        except Exception:
            continue
    
    return None


# ==============================================================================
# Exports
# ==============================================================================

__all__ = [
    # Loaders
    'BaseDataLoader',
    'TxtDataLoader',
    'MiniSeedLoader',
    'SAFLoader',
    'SACLoader',
    'GCFLoader',
    'PEERLoader',
    'MiniSharkLoader',
    'SeismicRecording3CLoader',
    
    # Configuration
    'LoaderConfig',
    'SAFConfig',
    'SACConfig',
    'GCFConfig',
    'PEERConfig',
    
    # Registry
    'FORMAT_INFO',
    'get_supported_formats',
    'get_format_info',
    'get_all_extensions',
    'get_file_filter',
    'get_loader_for_extension',
    'detect_format',
    
    # Utilities
    'orient_traces',
    'arrange_traces',
    'trim_traces',
    'rotate_horizontals',
    'detect_component_from_filename',
    'auto_assign_components',
    'extract_saf_header',
    'extract_peer_header',
    'parse_peer_samples',
    
    # Preview
    'PreviewExtractor',
    'PreviewData',
    'ChannelPreview',
    'get_preview',
]
