"""
ASCII text file loader for HVSR Pro
====================================

Loads OSCAR format ASCII text files with three-component data.
"""

import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from hvsr_pro.loaders.base_loader import BaseDataLoader
from hvsr_pro.core.data_structures import SeismicData, ComponentData
from hvsr_pro.core.metadata import MetadataManager


class TxtDataLoader(BaseDataLoader):
    """
    Loader for OSCAR ASCII text format.
    
    Expected format:
        Site: XX01
        Duration[s]: 18000.00
        Sensor_Type: CMG6TD
        Depth[m]: 0.4
        Units: m/s
        Time[s]    E-W    N-S    Z
        0.00000  -1.292e-06   1.638e-06  -2.523e-06
        ...
    """
    
    def __init__(self):
        """Initialize ASCII text loader."""
        super().__init__()
        self.supported_extensions = ['.txt', '.dat', '.asc']
        self.loader_name = "TxtDataLoader"
        self.metadata_manager = MetadataManager()
    
    def can_load(self, filepath: str) -> bool:
        """
        Check if file is loadable ASCII text.
        
        Args:
            filepath: Path to check
            
        Returns:
            True if file can be loaded
        """
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() not in self.supported_extensions:
            return False
        
        # Try to read first few lines
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                first_lines = [f.readline() for _ in range(10)]
            
            # Look for characteristic headers
            header_text = ''.join(first_lines).lower()
            if 'site' in header_text or 'duration' in header_text:
                return True
            
            # Check if contains numeric data in columns
            for line in first_lines:
                if line.strip() and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            # Try to parse as numbers
                            [float(p) for p in parts[:4]]
                            return True
                        except ValueError:
                            continue
            
            return False
            
        except (UnicodeDecodeError, PermissionError):
            return False
    
    def load_file(self, filepath: str, **kwargs) -> SeismicData:
        """
        Load OSCAR ASCII text file.
        
        Args:
            filepath: Path to ASCII file
            **kwargs: Optional parameters
                - skip_validation: Skip file validation (default: False)
                
        Returns:
            SeismicData object with loaded data
        """
        # Validate file
        if not kwargs.get('skip_validation', False):
            self.validate_file(filepath)
        
        # Read file content
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Parse header and data
        header_lines, data_start = self._find_data_start(lines)
        metadata = self._parse_header(header_lines, filepath)
        
        # Load numeric data
        data_array = self._load_data_array(lines[data_start:])
        
        # Extract time and components
        if data_array.shape[1] < 4:
            raise ValueError(
                f"Expected at least 4 columns (Time, E, N, Z), got {data_array.shape[1]}"
            )
        
        time_data = data_array[:, 0]
        east_data = data_array[:, 1]
        north_data = data_array[:, 2]
        vertical_data = data_array[:, 3]
        
        # Calculate sampling rate from time data
        if 'sampling_rate' not in metadata:
            dt = np.median(np.diff(time_data))
            sampling_rate = 1.0 / dt
            metadata['sampling_rate'] = sampling_rate
        else:
            sampling_rate = metadata['sampling_rate']
        
        # Get units
        units = metadata.get('units', 'm/s')
        
        # Create ComponentData objects
        east = ComponentData(
            name='E',
            data=east_data,
            sampling_rate=sampling_rate,
            units=units,
            metadata={'component': 'East', 'original_column': 1}
        )
        
        north = ComponentData(
            name='N',
            data=north_data,
            sampling_rate=sampling_rate,
            units=units,
            metadata={'component': 'North', 'original_column': 2}
        )
        
        vertical = ComponentData(
            name='Z',
            data=vertical_data,
            sampling_rate=sampling_rate,
            units=units,
            metadata={'component': 'Vertical', 'original_column': 3}
        )
        
        # Create SeismicData object
        seismic_data = SeismicData(
            east=east,
            north=north,
            vertical=vertical,
            station_name=metadata.get('station_name', 'UNKNOWN'),
            location=metadata.get('location', ''),
            source_file=filepath,
            metadata=metadata
        )
        
        return seismic_data
    
    def _find_data_start(self, lines: list) -> tuple[list, int]:
        """
        Find where numeric data starts in file.
        
        Args:
            lines: List of file lines
            
        Returns:
            Tuple of (header_lines, data_start_index)
        """
        header_lines = []
        data_start = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Skip comment lines
            if line_stripped.startswith('#'):
                header_lines.append(line_stripped)
                continue
            
            # Check if line contains header keyword
            if ':' in line_stripped and any(
                keyword in line_stripped.lower() 
                for keyword in ['site', 'duration', 'sensor', 'depth', 'units']
            ):
                header_lines.append(line_stripped)
                continue
            
            # Check if column header line
            if 'time' in line_stripped.lower() and any(
                comp in line_stripped.lower() for comp in ['e-w', 'n-s', 'z']
            ):
                header_lines.append(line_stripped)
                continue
            
            # Try to parse as numeric data
            try:
                parts = line_stripped.split()
                if len(parts) >= 4:
                    [float(p) for p in parts[:4]]
                    data_start = i
                    break
            except ValueError:
                header_lines.append(line_stripped)
        
        return header_lines, data_start
    
    def _parse_header(self, header_lines: list, filepath: str) -> Dict[str, Any]:
        """
        Parse header information.
        
        Args:
            header_lines: List of header lines
            filepath: Source file path
            
        Returns:
            Metadata dictionary
        """
        # Parse OSCAR header format
        metadata = self.metadata_manager.parse_oscar_header(header_lines)
        
        # Extract from filename
        file_metadata = self.metadata_manager.extract_from_filename(filepath)
        
        # Merge metadata
        metadata = self.metadata_manager.merge_metadata(file_metadata, metadata)
        
        # Add loader info
        metadata['loader'] = self.loader_name
        metadata['format'] = 'ASCII_TXT'
        
        return metadata
    
    def _load_data_array(self, data_lines: list) -> np.ndarray:
        """
        Load numeric data from lines.
        
        Args:
            data_lines: Lines containing numeric data
            
        Returns:
            NumPy array with shape (n_samples, n_columns)
        """
        data_rows = []
        
        for line in data_lines:
            line_stripped = line.strip()
            if not line_stripped or line_stripped.startswith('#'):
                continue
            
            try:
                values = [float(x) for x in line_stripped.split()]
                if len(values) >= 4:
                    data_rows.append(values[:4])  # Time, E, N, Z
            except ValueError:
                continue
        
        if not data_rows:
            raise ValueError("No valid numeric data found in file")
        
        return np.array(data_rows)
    
    def get_file_preview(self, filepath: str, n_lines: int = 10) -> str:
        """
        Get preview of file content.
        
        Args:
            filepath: Path to file
            n_lines: Number of lines to preview
            
        Returns:
            String with file preview
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [f.readline() for _ in range(n_lines)]
        
        return ''.join(lines)
