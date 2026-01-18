"""
Trace Orientation Utilities
===========================

Functions for standardizing seismic trace orientation across different formats.
Handles NEZ, XYZ, 123, and 12Z naming conventions.
"""

from typing import List, Tuple, Optional
import logging
import numpy as np

try:
    from obspy import Trace, Stream
    HAS_OBSPY = True
except ImportError:
    HAS_OBSPY = False
    Trace = None
    Stream = None

logger = logging.getLogger(__name__)


def arrange_traces(traces: List, components: str = "NEZ") -> Tuple:
    """
    Sort a list of 3 traces according to component direction.
    
    Args:
        traces: List of 3 ObsPy Trace objects
        components: 3-character string specifying component order.
            Common patterns:
            - "NEZ": Standard north, east, vertical
            - "XYZ": Alternative horizontal naming
            - "123": Numeric component naming
            - "12Z": Mixed numeric/letter naming
            
    Returns:
        Tuple of (ns_trace, ew_trace, vt_trace)
        
    Raises:
        ValueError: If components cannot be matched or are missing/duplicate
    """
    if len(traces) != 3:
        raise ValueError(f"Expected 3 traces, got {len(traces)}")
    
    if len(components) != 3:
        raise ValueError(f"Components string must be 3 characters, got '{components}'")
    
    ns, ew, vt = None, None, None
    found_ns, found_ew, found_vt = False, False, False
    
    for trace in traces:
        channel = trace.stats.channel
        
        # Check for north/component[0]
        if channel.endswith(components[0]) and not found_ns:
            ns = trace
            found_ns = True
        # Check for east/component[1]
        elif channel.endswith(components[1]) and not found_ew:
            ew = trace
            found_ew = True
        # Check for vertical/component[2]
        elif channel.endswith(components[2]) and not found_vt:
            vt = trace
            found_vt = True
    
    if not (found_ns and found_ew and found_vt):
        missing = []
        if not found_ns:
            missing.append(f"N ({components[0]})")
        if not found_ew:
            missing.append(f"E ({components[1]})")
        if not found_vt:
            missing.append(f"Z ({components[2]})")
        
        channels = [t.stats.channel for t in traces]
        raise ValueError(
            f"Missing components {missing} for pattern '{components}'. "
            f"Available channels: {channels}"
        )
    
    return ns, ew, vt


def orient_traces(
    traces: List,
    degrees_from_north: Optional[float] = None
) -> Tuple:
    """
    Orient traces to standard N, E, Z components.
    
    Tries multiple naming conventions in order:
    1. NEZ - Standard seismic convention
    2. XYZ - Alternative horizontal naming
    3. 123 - Numeric (requires degrees_from_north)
    4. 12Z - Mixed numeric/letter
    
    Args:
        traces: List of 3 ObsPy Trace objects
        degrees_from_north: Rotation in degrees of sensor's north component
            relative to magnetic north (clockwise positive). Required for
            123/12Z patterns where orientation is not implicit.
            
    Returns:
        Tuple of (ns_trace, ew_trace, vt_trace, final_degrees_from_north)
        
    Raises:
        ValueError: If no valid pattern matches or degrees_from_north
            is required but not provided
    """
    # Try NEZ first
    try:
        ns, ew, vt = arrange_traces(traces, components="NEZ")
        final_degrees = 0.0 if degrees_from_north is None else float(degrees_from_north)
        logger.debug("Matched NEZ pattern")
        return ns, ew, vt, final_degrees
    except ValueError:
        pass
    
    # Try XYZ next
    try:
        ns, ew, vt = arrange_traces(traces, components="XYZ")
        final_degrees = 0.0 if degrees_from_north is None else float(degrees_from_north)
        logger.debug("Matched XYZ pattern")
        return ns, ew, vt, final_degrees
    except ValueError:
        pass
    
    # For 123/12Z, degrees_from_north is required
    if degrees_from_north is None:
        channels = [t.stats.channel for t in traces]
        raise ValueError(
            f"Components do not match NEZ or XYZ patterns. "
            f"Available channels: {channels}. "
            f"For 123/12Z patterns, you must specify 'degrees_from_north'."
        )
    
    # Try 123
    try:
        ns, ew, vt = arrange_traces(traces, components="123")
        logger.debug("Matched 123 pattern")
        return ns, ew, vt, float(degrees_from_north)
    except ValueError:
        pass
    
    # Try 12Z
    try:
        ns, ew, vt = arrange_traces(traces, components="12Z")
        logger.debug("Matched 12Z pattern")
        return ns, ew, vt, float(degrees_from_north)
    except ValueError:
        pass
    
    # No pattern matched
    channels = [t.stats.channel for t in traces]
    raise ValueError(
        f"Could not identify components from channels: {channels}. "
        f"Expected patterns: NEZ, XYZ, 123, or 12Z"
    )


def trim_traces(traces: List) -> List:
    """
    Trim traces to their common time window.
    
    Finds the overlapping time range across all traces and trims each
    trace to that window. Required when traces have slightly different
    start/end times.
    
    Args:
        traces: List of ObsPy Trace objects
        
    Returns:
        List of trimmed traces (same objects, modified in place)
        
    Raises:
        ValueError: If traces do not overlap or overlap is too short
    """
    if not traces:
        return traces
    
    # Find common start and end times
    start_time = max(trace.stats.starttime for trace in traces)
    end_time = min(trace.stats.endtime for trace in traces)
    
    duration = end_time - start_time
    if duration < 0.1:
        raise ValueError(
            "Time series do not overlap sufficiently. "
            f"Common window is only {duration:.3f} seconds."
        )
    
    # Trim each trace
    for trace in traces:
        trace.trim(starttime=start_time, endtime=end_time)
    
    logger.debug(f"Trimmed traces to common window: {duration:.2f} seconds")
    
    return traces


def rotate_horizontals(
    ns_data: np.ndarray,
    ew_data: np.ndarray,
    angle_degrees: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Rotate horizontal components by specified angle.
    
    Args:
        ns_data: North-south component amplitude data
        ew_data: East-west component amplitude data
        angle_degrees: Rotation angle in degrees (clockwise positive)
        
    Returns:
        Tuple of (rotated_ns, rotated_ew) arrays
    """
    angle_rad = np.radians(angle_degrees)
    c = np.cos(angle_rad)
    s = np.sin(angle_rad)
    
    rotated_ns = ns_data * c + ew_data * s
    rotated_ew = -ns_data * s + ew_data * c
    
    return rotated_ns, rotated_ew


def detect_component_from_filename(filename: str) -> Optional[str]:
    """
    Try to detect component (N/E/Z) from filename.
    
    Args:
        filename: File name to analyze
        
    Returns:
        Component letter ('N', 'E', 'Z') or None if not detected
    """
    filename_upper = filename.upper()
    
    # Check for explicit component markers
    patterns = [
        # Explicit component in name
        ('_N.', 'N'), ('_E.', 'E'), ('_Z.', 'Z'),
        ('_NS.', 'N'), ('_EW.', 'E'), ('_UD.', 'Z'),
        ('_NORTH.', 'N'), ('_EAST.', 'E'), ('_VERT.', 'Z'),
        # Channel codes
        ('BHN', 'N'), ('BHE', 'E'), ('BHZ', 'Z'),
        ('HHN', 'N'), ('HHE', 'E'), ('HHZ', 'Z'),
        ('HNE', 'E'), ('HNN', 'N'), ('HNZ', 'Z'),
        # PEER format
        ('-UP.', 'Z'), ('090.', 'E'), ('360.', 'N'), ('000.', 'N'),
    ]
    
    for pattern, component in patterns:
        if pattern in filename_upper:
            return component
    
    return None


def auto_assign_components(filepaths: List[str]) -> dict:
    """
    Automatically assign component labels to file paths.
    
    Args:
        filepaths: List of 3 file paths
        
    Returns:
        Dictionary mapping component to filepath: {'N': path, 'E': path, 'Z': path}
        
    Raises:
        ValueError: If components cannot be determined or are ambiguous
    """
    if len(filepaths) != 3:
        raise ValueError(f"Expected 3 files, got {len(filepaths)}")
    
    from pathlib import Path
    
    assignments = {}
    unassigned = list(filepaths)
    
    # First pass: try to detect from filenames
    for filepath in filepaths:
        filename = Path(filepath).name
        component = detect_component_from_filename(filename)
        
        if component and component not in assignments:
            assignments[component] = filepath
            unassigned.remove(filepath)
    
    # Check if we got all three
    if len(assignments) == 3:
        return assignments
    
    # If we couldn't auto-detect all, raise error
    detected = list(assignments.keys())
    missing = [c for c in ['N', 'E', 'Z'] if c not in detected]
    
    raise ValueError(
        f"Could not auto-detect all components. "
        f"Detected: {detected}, Missing: {missing}. "
        f"Please specify component mapping manually."
    )
