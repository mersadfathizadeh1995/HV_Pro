"""
Base data loader for HVSR Pro
==============================

Abstract base class for all data loaders.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pathlib import Path

from hvsr_pro.core.data_structures import SeismicData


class BaseDataLoader(ABC):
    """
    Abstract base class for data loaders.
    
    All data loaders must implement:
    - load_file: Load data from file
    - can_load: Check if file is supported
    - get_file_info: Extract basic file information
    """
    
    def __init__(self):
        """Initialize base loader."""
        self.supported_extensions = []
        self.loader_name = "BaseLoader"
    
    @abstractmethod
    def load_file(self, filepath: str, **kwargs) -> SeismicData:
        """
        Load seismic data from file.
        
        Args:
            filepath: Path to data file
            **kwargs: Loader-specific options
            
        Returns:
            SeismicData object with three components
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        pass
    
    @abstractmethod
    def can_load(self, filepath: str) -> bool:
        """
        Check if this loader can handle the file.
        
        Args:
            filepath: Path to check
            
        Returns:
            True if loader can handle this file
        """
        pass
    
    def validate_file(self, filepath: str) -> None:
        """
        Validate file exists and is accessible.
        
        Args:
            filepath: Path to validate
            
        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If file is not readable
        """
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        if not path.is_file():
            raise ValueError(f"Path is not a file: {filepath}")
        
        # Try to open for reading
        try:
            with open(filepath, 'r') as f:
                pass
        except PermissionError:
            raise PermissionError(f"Cannot read file: {filepath}")
    
    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """
        Extract basic file information.
        
        Args:
            filepath: Path to file
            
        Returns:
            Dictionary with file metadata
        """
        path = Path(filepath)
        stat = path.stat()
        
        return {
            'filename': path.name,
            'filepath': str(path.absolute()),
            'size_bytes': stat.st_size,
            'size_mb': stat.st_size / (1024 * 1024),
            'modified_time': stat.st_mtime,
            'extension': path.suffix
        }
    
    def __repr__(self) -> str:
        return f"{self.loader_name}(extensions={self.supported_extensions})"
