"""
PEER (Pacific Earthquake Engineering Research) Loader
=====================================================

Loads seismic data from PEER NGA format files.
Requires 3 separate files (one per component).
Reference: https://strike.scec.org/scecpedia/PEER_Data_Format
"""

import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import logging

from hvsr_pro.loaders.base_loader import BaseDataLoader
from hvsr_pro.loaders.config import PEERConfig
from hvsr_pro.loaders.patterns import (
    PEER_DIRECTION, PEER_NPTS, PEER_DT, PEER_SAMPLE,
    extract_peer_header, parse_peer_samples
)
from hvsr_pro.core.data_structures import SeismicData, ComponentData

logger = logging.getLogger(__name__)


class PEERLoader(BaseDataLoader):
    """
    Loader for PEER NGA (Pacific Earthquake Engineering Research) format files.
    
    PEER format stores one component per file with headers describing
    the motion direction. Three files are required for a complete
    3-component recording.
    
    Header example:
        PEER NGA STRONG MOTION DATABASE RECORD
        Northridge-01, 1/17/1994, Station Name, UP
        VELOCITY TIME SERIES IN UNITS OF CM/S
        NPTS=   3000, DT=   .0200 SEC
    
    Direction identifiers:
        - UP, VER: Vertical component
        - Numeric (0-360): Horizontal azimuth in degrees
        - Channel codes (e.g., BHN, HHE): Standard naming
    
    Usage:
        loader = PEERLoader()
        data = loader.load_file([
            'rsn942_northr_alh090.vt2',
            'rsn942_northr_alh360.vt2',
            'rsn942_northr_alh-up.vt2'
        ])
    """
    
    def __init__(self):
        """Initialize PEER loader."""
        super().__init__()
        self.supported_extensions = ['.vt2', '.at2', '.dt2']
        self.loader_name = "PEERLoader"
    
    def can_load(self, filepath: str) -> bool:
        """
        Check if file is PEER format.
        
        Args:
            filepath: Path to file
            
        Returns:
            True if file appears to be PEER format
        """
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() not in self.supported_extensions:
            return False
        
        # Try to read and verify PEER header
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                first_lines = f.read(500)
            
            # Check for PEER header markers
            if 'PEER' in first_lines.upper() or 'NPTS=' in first_lines:
                return True
                
        except Exception:
            pass
        
        return False
    
    def load_file(
        self,
        filepaths: Union[str, List[str]],
        config: PEERConfig = None,
        **kwargs
    ) -> SeismicData:
        """
        Load PEER files.
        
        Args:
            filepaths: List of 3 PEER file paths (one per component)
            config: Optional PEERConfig with loading options
            **kwargs: Additional options (for compatibility)
            
        Returns:
            SeismicData object with loaded data
            
        Raises:
            ValueError: If not exactly 3 files provided or format is invalid
            FileNotFoundError: If any file doesn't exist
        """
        # Handle single file path (convert to list)
        if isinstance(filepaths, (str, Path)):
            raise ValueError(
                "PEER format requires 3 separate files (one per component). "
                "Please provide a list of 3 file paths."
            )
        
        if len(filepaths) != 3:
            raise ValueError(
                f"PEER format requires exactly 3 files, got {len(filepaths)}"
            )
        
        # Use default config if not provided
        if config is None:
            config = PEERConfig(
                degrees_from_north=kwargs.get('degrees_from_north'),
                verbose=kwargs.get('verbose', False)
            )
        
        if config.verbose:
            logger.info(f"Loading {len(filepaths)} PEER files...")
        
        # Load each file
        components = []  # List of (direction, dt, data) tuples
        dts = []
        
        for filepath in filepaths:
            self.validate_file(filepath)
            
            # Read file
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Extract header
            header = extract_peer_header(text)
            
            if 'direction' not in header:
                raise ValueError(f"Could not determine direction from PEER file: {filepath}")
            if 'npts' not in header:
                raise ValueError(f"Missing NPTS in PEER file: {filepath}")
            if 'dt' not in header:
                raise ValueError(f"Missing DT in PEER file: {filepath}")
            
            direction = header['direction']
            npts = header['npts']
            dt = header['dt']
            dts.append(dt)
            
            # Parse samples
            samples = parse_peer_samples(text)
            
            if len(samples) != npts:
                logger.warning(
                    f"PEER header specifies {npts} samples, found {len(samples)}. "
                    f"Using {len(samples)} samples."
                )
            
            amplitude = np.array(samples, dtype=np.float64)
            components.append((direction, dt, amplitude, filepath))
        
        # Check all dt values are equal
        if not all(abs(dt - dts[0]) < 1e-8 for dt in dts):
            raise ValueError(
                f"Time steps differ between files: {dts}. "
                "All PEER files must have the same DT."
            )
        
        dt = dts[0]
        sampling_rate = 1.0 / dt
        
        # Organize components - find vertical first
        vt_data = None
        vt_direction = None
        horizontal_components = []
        
        for direction, _, amplitude, fpath in components:
            if self._is_vertical(direction):
                vt_data = amplitude
                vt_direction = direction
            else:
                horizontal_components.append((direction, amplitude, fpath))
        
        if vt_data is None:
            directions = [c[0] for c in components]
            raise ValueError(
                f"Could not identify vertical component. "
                f"Directions found: {directions}"
            )
        
        if len(horizontal_components) != 2:
            raise ValueError(
                f"Expected 2 horizontal components, found {len(horizontal_components)}"
            )
        
        # Organize horizontal components
        ns_data, ew_data, degrees_from_north = self._organize_horizontals(
            horizontal_components,
            config.degrees_from_north
        )
        
        # Trim to shortest length
        min_length = min(len(ns_data), len(ew_data), len(vt_data))
        ns_data = ns_data[:min_length]
        ew_data = ew_data[:min_length]
        vt_data = vt_data[:min_length]
        
        # Create ComponentData objects
        east = ComponentData(
            name='E',
            data=ew_data,
            sampling_rate=sampling_rate,
            units='cm/s',  # PEER typically uses cm/s
            metadata={'direction': 'E'}
        )
        
        north = ComponentData(
            name='N',
            data=ns_data,
            sampling_rate=sampling_rate,
            units='cm/s',
            metadata={'direction': 'N'}
        )
        
        vertical = ComponentData(
            name='Z',
            data=vt_data,
            sampling_rate=sampling_rate,
            units='cm/s',
            metadata={'direction': vt_direction}
        )
        
        # Create SeismicData
        seismic_data = SeismicData(
            east=east,
            north=north,
            vertical=vertical,
            station_name='PEER',
            source_file=f"PEER: {len(filepaths)} files",
            metadata={
                'format': 'PEER',
                'loader': self.loader_name,
                'degrees_from_north': degrees_from_north,
                'source_files': [str(f) for f in filepaths],
                'dt': dt
            }
        )
        
        if config.verbose:
            logger.info(
                f"Loaded PEER: {min_length} samples @ {sampling_rate:.1f} Hz, "
                f"rotation={degrees_from_north}°"
            )
        
        return seismic_data
    
    def _is_vertical(self, direction: str) -> bool:
        """Check if direction indicates vertical component."""
        direction_upper = direction.upper()
        
        # Check explicit vertical markers
        if direction_upper in ('UP', 'VER'):
            return True
        
        # Check channel codes ending in Z
        if len(direction) == 3 and direction_upper.endswith('Z'):
            return True
        
        return False
    
    def _organize_horizontals(
        self,
        horizontals: List[tuple],
        degrees_from_north: Optional[float]
    ) -> tuple:
        """
        Organize horizontal components into N and E.
        
        Args:
            horizontals: List of (direction, amplitude, filepath) tuples
            degrees_from_north: User-specified orientation
            
        Returns:
            Tuple of (ns_data, ew_data, final_degrees_from_north)
        """
        # Check if directions are numeric (azimuths)
        orientation_is_numeric = False
        
        try:
            azimuths = [int(h[0]) for h in horizontals]
            orientation_is_numeric = True
        except ValueError:
            pass
        
        if orientation_is_numeric:
            # Numeric azimuths - organize by angle
            azimuths_abs = np.array(azimuths, dtype=int)
            azimuths_rel = azimuths_abs.copy()
            azimuths_rel[azimuths_abs > 180] -= 360
            
            # Component closest to 0/360 is NS
            ns_idx = np.argmin(np.abs(azimuths_rel))
            ew_idx = 1 - ns_idx  # The other one
            
            ns_data = horizontals[ns_idx][1]
            ew_data = horizontals[ew_idx][1]
            
            if degrees_from_north is None:
                # Use the azimuth of the NS component
                final_degrees = float(azimuths_abs[ns_idx])
                final_degrees = final_degrees - 360 * (final_degrees // 360)
            else:
                final_degrees = degrees_from_north
            
            return ns_data, ew_data, final_degrees
        
        else:
            # Try to identify from channel codes
            ns_data = None
            ew_data = None
            
            for direction, amplitude, fpath in horizontals:
                direction_upper = direction.upper()
                
                if direction_upper.endswith('N'):
                    ns_data = amplitude
                elif direction_upper.endswith('E'):
                    ew_data = amplitude
            
            if ns_data is None or ew_data is None:
                directions = [h[0] for h in horizontals]
                raise ValueError(
                    f"Could not identify N/E from directions: {directions}"
                )
            
            final_degrees = 0.0 if degrees_from_north is None else degrees_from_north
            
            return ns_data, ew_data, final_degrees
    
    def get_file_preview(self, filepath: str, n_lines: int = 10) -> str:
        """
        Get preview of PEER file header.
        
        Args:
            filepath: Path to file
            n_lines: Number of header lines to preview
            
        Returns:
            String with file preview
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [f.readline() for _ in range(n_lines)]
        
        return ''.join(lines)
