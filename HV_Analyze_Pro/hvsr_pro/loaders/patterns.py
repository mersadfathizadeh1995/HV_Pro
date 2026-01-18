"""
Regex Patterns for Data File Parsing
=====================================

Compiled regular expressions for parsing various seismic data formats.
"""

import re

# ==============================================================================
# SAF (SESAME ASCII Format) Patterns
# ==============================================================================

# Header patterns
SAF_VERSION = re.compile(r"SESAME ASCII data format \(saf\) v\. (\d)")
SAF_NPTS = re.compile(r"NDAT = (\d+)")
SAF_FS = re.compile(r"SAMP_FREQ = (\d+)")
SAF_V_CH = re.compile(r"CH(\d)_ID = V")
SAF_N_CH = re.compile(r"CH(\d)_ID = N")
SAF_E_CH = re.compile(r"CH(\d)_ID = E")
SAF_NORTH_ROT = re.compile(r"NORTH_ROT = (\d+)")
SAF_START_TIME = re.compile(r"START_TIME = (\d{4} \d{2} \d{2} \d{2} \d{2} \d{2}\.\d+)")

# Data row pattern - 3 space-separated values (integers or floats)
SAF_DATA_ROW = re.compile(
    r"^(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s*$",
    re.MULTILINE
)


# ==============================================================================
# PEER (Pacific Earthquake Engineering Research) Format Patterns
# ==============================================================================

# Direction pattern - matches UP, VER, numeric degrees, or SEED channel codes
PEER_DIRECTION = re.compile(
    r",\s*(UP|VER|\d{1,3}|[FGDCESHB][HLGMN][ENZ])\s*[\r\n]"
)

# Header patterns
PEER_NPTS = re.compile(r"NPTS\s*=\s*(\d+)\s*,")
PEER_DT = re.compile(r"DT\s*=\s*(\d*\.\d+)\s")

# Data sample pattern - scientific notation
PEER_SAMPLE = re.compile(r"(-?\d*\.\d+[eE][+-]?\d+)")


# ==============================================================================
# MiniShark Format Patterns
# ==============================================================================

MSHARK_NPTS = re.compile(r"#Sample number:\t(\d+)")
MSHARK_FS = re.compile(r"#Sample rate \(sps\):\t(\d+)")
MSHARK_GAIN = re.compile(r"#Gain:\t(\d+)")
MSHARK_CONVERSION = re.compile(r"#Conversion factor:\t(\d+)")
MSHARK_DATA_ROW = re.compile(r"(-?\d+)\t(-?\d+)\t(-?\d+)")


# ==============================================================================
# Geopsy Format Patterns
# ==============================================================================

GEOPSY_LINE = re.compile(r"(\d+\.\d+)\t(\d+\.\d+)\t(\d+\.\d+)\t\d+\.\d+")


# ==============================================================================
# Azimuth Parsing (for result files)
# ==============================================================================

AZIMUTH_PATTERN = re.compile(r"azimuth (\d+\.\d+) deg \| hvsr curve \d+")


# ==============================================================================
# Helper Functions
# ==============================================================================

def extract_saf_header(text: str) -> dict:
    """
    Extract all header information from SAF file text.
    
    Args:
        text: Full file text content
        
    Returns:
        Dictionary with extracted header values
    """
    header = {}
    
    # Version
    match = SAF_VERSION.search(text)
    if match:
        header['version'] = int(match.group(1))
    
    # Number of points
    match = SAF_NPTS.search(text)
    if match:
        header['npts'] = int(match.group(1))
    
    # Sampling frequency
    match = SAF_FS.search(text)
    if match:
        header['sampling_rate'] = float(match.group(1))
    
    # Channel assignments (0, 1, or 2)
    match = SAF_V_CH.search(text)
    if match:
        header['v_channel'] = int(match.group(1))
    
    match = SAF_N_CH.search(text)
    if match:
        header['n_channel'] = int(match.group(1))
    
    match = SAF_E_CH.search(text)
    if match:
        header['e_channel'] = int(match.group(1))
    
    # North rotation
    match = SAF_NORTH_ROT.search(text)
    if match:
        header['north_rot'] = float(match.group(1))
    else:
        header['north_rot'] = 0.0
    
    # Start time
    match = SAF_START_TIME.search(text)
    if match:
        header['start_time_str'] = match.group(1)
    
    return header


def extract_peer_header(text: str) -> dict:
    """
    Extract header information from PEER file text.
    
    Args:
        text: Full file text content
        
    Returns:
        Dictionary with extracted header values
    """
    header = {}
    
    # Direction
    match = PEER_DIRECTION.search(text)
    if match:
        header['direction'] = match.group(1)
    
    # Number of points
    match = PEER_NPTS.search(text)
    if match:
        header['npts'] = int(match.group(1))
    
    # Time step
    match = PEER_DT.search(text)
    if match:
        header['dt'] = float(match.group(1))
    
    return header


def parse_peer_samples(text: str) -> list:
    """
    Extract all amplitude samples from PEER file.
    
    Args:
        text: Full file text content
        
    Returns:
        List of float amplitude values
    """
    samples = []
    for match in PEER_SAMPLE.finditer(text):
        samples.append(float(match.group(1)))
    return samples
