"""
File Detection Utilities
========================

Utilities for detecting and grouping MiniSEED files.
Extracted from data_input_dialog.py.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re


def can_auto_detect_channels(channel_codes: List[str]) -> bool:
    """
    Check if channels can be auto-detected based on naming conventions.
    
    Args:
        channel_codes: List of channel codes (e.g., ['HHE', 'HHN', 'HHZ'])
        
    Returns:
        True if E/N/Z components can be identified
    """
    has_e = any(c.upper().endswith('E') or c.upper().endswith('1') for c in channel_codes)
    has_n = any(c.upper().endswith('N') or c.upper().endswith('2') for c in channel_codes)
    has_z = any(c.upper().endswith('Z') or c.upper().endswith('3') for c in channel_codes)
    return has_e and has_n and has_z


def detect_type1_files(dir_path: str) -> Tuple[List[Path], Dict[str, List[dict]]]:
    """
    Detect Type 1 MiniSEED files (3-channel per file).
    
    Args:
        dir_path: Directory path to scan
        
    Returns:
        Tuple of (list of file paths, dict of channel info per file)
    """
    path = Path(dir_path)
    mseed_files = sorted(list(path.glob("*.mseed")) + list(path.glob("*.miniseed")))
    
    file_channels = {}
    
    try:
        from obspy import read
        has_obspy = True
    except ImportError:
        has_obspy = False
    
    if has_obspy:
        for file in mseed_files:
            file_path = str(file)
            try:
                stream = read(file_path, headonly=True)
                channels_info = [{
                    'code': tr.stats.channel,
                    'location': tr.stats.location,
                    'sampling_rate': tr.stats.sampling_rate,
                    'npts': tr.stats.npts,
                    'station': tr.stats.station,
                    'network': tr.stats.network
                } for tr in stream]
                file_channels[file_path] = channels_info
            except Exception:
                file_channels[file_path] = []
    
    return mseed_files, file_channels


def detect_type2_files(dir_path: str) -> Dict[str, Dict[str, Path]]:
    """
    Detect Type 2 MiniSEED files (separate E, N, Z files).
    
    Args:
        dir_path: Directory path to scan
        
    Returns:
        Dict of {base_name: {'E': path, 'N': path, 'Z': path}}
    """
    path = Path(dir_path)
    all_files = list(path.glob("*.mseed")) + list(path.glob("*.miniseed"))
    
    return group_component_files(all_files)


def group_component_files(files: List[Path]) -> Dict[str, Dict[str, Path]]:
    """
    Group files by base name, detecting E/N/Z components.
    
    Patterns recognized:
    - *_E.*, *_N.*, *_Z.*
    - *.E.*, *.N.*, *.Z.*
    - *E.mseed, *N.mseed, *Z.mseed (last char before ext)
    
    Args:
        files: List of file paths
        
    Returns:
        Dict of {base_name: {'E': path, 'N': path, 'Z': path}}
    """
    groups = {}
    
    for file_path in files:
        file = Path(file_path)
        name = file.stem
        
        # Try different patterns
        base_name, component = extract_base_and_component(name)
        
        if base_name and component:
            if base_name not in groups:
                groups[base_name] = {}
            groups[base_name][component] = file_path
    
    return groups


def extract_base_and_component(name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract base name and component (E/N/Z) from filename.
    
    Args:
        name: Filename without extension
        
    Returns:
        Tuple of (base_name, component) or (None, None) if not matched
    """
    # Pattern 1: *_E, *_N, *_Z
    match = re.match(r'(.+)_([ENZ])$', name, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2).upper()
    
    # Pattern 2: *.E, *.N, *.Z
    match = re.match(r'(.+)\.([ENZ])$', name, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2).upper()
    
    # Pattern 3: *E, *N, *Z (single letter at end)
    match = re.match(r'(.+[^ENZ])([ENZ])$', name, re.IGNORECASE)
    if match:
        return match.group(1), match.group(2).upper()
    
    # Pattern 4: corrected_E, corrected_N, corrected_Z pattern
    match = re.match(r'(.+?)_?corrected_?([ENZ])$', name, re.IGNORECASE)
    if match:
        return match.group(1) + '_corrected', match.group(2).upper()
    
    return None, None


def get_file_info(file_path: str) -> Dict:
    """
    Get basic information about a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Dict with file information
    """
    path = Path(file_path)
    
    info = {
        'name': path.name,
        'path': str(path),
        'size_mb': path.stat().st_size / (1024 * 1024),
        'extension': path.suffix.lower(),
        'is_miniseed': path.suffix.lower() in ['.mseed', '.miniseed'],
        'is_text': path.suffix.lower() in ['.txt', '.csv', '.dat', '.asc'],
    }
    
    return info


def get_miniseed_info(file_path: str) -> Optional[Dict]:
    """
    Get MiniSEED file information using ObsPy.
    
    Args:
        file_path: Path to MiniSEED file
        
    Returns:
        Dict with stream information or None if error
    """
    try:
        from obspy import read
        
        stream = read(file_path, headonly=True)
        
        info = {
            'n_traces': len(stream),
            'channels': [tr.stats.channel for tr in stream],
            'stations': list(set(tr.stats.station for tr in stream)),
            'networks': list(set(tr.stats.network for tr in stream)),
            'sampling_rates': list(set(tr.stats.sampling_rate for tr in stream)),
            'start_time': min(tr.stats.starttime for tr in stream).datetime,
            'end_time': max(tr.stats.endtime for tr in stream).datetime,
        }
        
        return info
    except ImportError:
        return None
    except Exception:
        return None


def scan_directory_for_seismic_files(dir_path: str) -> Dict[str, List[Path]]:
    """
    Scan directory for all supported seismic data files.
    
    Args:
        dir_path: Directory path to scan
        
    Returns:
        Dict with categorized files:
        - 'miniseed': List of MiniSEED files
        - 'text': List of text/CSV files
        - 'other': List of other files
    """
    path = Path(dir_path)
    
    result = {
        'miniseed': [],
        'text': [],
        'other': []
    }
    
    miniseed_exts = {'.mseed', '.miniseed'}
    text_exts = {'.txt', '.csv', '.dat', '.asc'}
    
    for file in path.iterdir():
        if file.is_file():
            ext = file.suffix.lower()
            if ext in miniseed_exts:
                result['miniseed'].append(file)
            elif ext in text_exts:
                result['text'].append(file)
            else:
                result['other'].append(file)
    
    # Sort all lists
    for key in result:
        result[key] = sorted(result[key])
    
    return result
