"""
Base data loader for HVSR Pro
==============================

Abstract base class for all data loaders.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Union, TYPE_CHECKING
from pathlib import Path
import logging

from hvsr_pro.core.data_structures import SeismicData

if TYPE_CHECKING:
    from hvsr_pro.loaders.preview import PreviewData

logger = logging.getLogger(__name__)


class BaseDataLoader(ABC):
    """
    Abstract base class for data loaders.
    
    All data loaders must implement:
    - load_file: Load data from file
    - can_load: Check if file is supported
    
    Optional methods for enhanced functionality:
    - get_preview: Get preview data for mapper dialog
    - get_detected_mapping: Get auto-detected component mapping
    - load_with_mapping: Load with explicit component mapping
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
    
    def get_preview(
        self,
        filepath: Union[str, List[str]],
        n_samples: int = 1000
    ) -> 'PreviewData':
        """
        Get preview data for component mapper dialog.
        
        This method extracts sample waveforms and metadata without fully loading
        the file. Override in subclasses for format-specific preview.
        
        Args:
            filepath: Path to file, or list of paths for multi-file formats
            n_samples: Number of samples to include in preview
            
        Returns:
            PreviewData with channel information and waveform samples
        """
        # Default implementation uses the global preview extractor
        from hvsr_pro.loaders.preview import get_preview
        
        # Determine format from loader name
        format_map = {
            'SAFLoader': 'saf',
            'SACLoader': 'sac',
            'GCFLoader': 'gcf',
            'PEERLoader': 'peer',
            'MiniSeedLoader': 'miniseed',
            'TxtDataLoader': 'txt',
        }
        format_name = format_map.get(self.loader_name, 'unknown')
        
        return get_preview(filepath, format=format_name, n_samples=n_samples)
    
    def get_detected_mapping(
        self,
        filepath: Union[str, List[str]]
    ) -> Dict[str, int]:
        """
        Get auto-detected component mapping.
        
        Returns a mapping from component names (E, N, Z) to channel indices.
        
        Args:
            filepath: Path to file, or list of paths for multi-file formats
            
        Returns:
            Dictionary mapping component to channel index, e.g. {'E': 0, 'N': 1, 'Z': 2}
        """
        preview = self.get_preview(filepath, n_samples=100)
        return preview.detected_mapping
    
    def load_with_mapping(
        self,
        filepath: Union[str, List[str]],
        mapping: Dict[str, int],
        **kwargs
    ) -> SeismicData:
        """
        Load file using explicit component mapping.
        
        This allows users to override auto-detected component assignments.
        
        Args:
            filepath: Path to file, or list of paths for multi-file formats
            mapping: Dictionary mapping component (E, N, Z) to channel index
            **kwargs: Additional loader options
            
        Returns:
            SeismicData object with mapped components
        """
        # Default implementation: load normally and rearrange
        # Subclasses can override for more efficient implementation
        
        # For single file formats, load normally
        if isinstance(filepath, str):
            data = self.load_file(filepath, **kwargs)
        else:
            # For multi-file, pass as list
            data = self.load_file(filepath, **kwargs)
        
        # Rearrange components if mapping differs from default
        # This is a simple swap approach - subclasses should override
        # for more sophisticated handling
        
        return data
    
    def get_file_preview(self, filepath: str, n_lines: int = 20) -> str:
        """
        Get text preview of file content (for display in mapper dialog).
        
        Args:
            filepath: Path to file
            n_lines: Number of lines to preview
            
        Returns:
            String with first n_lines of file content
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= n_lines:
                        break
                    lines.append(line)
                return ''.join(lines)
        except Exception as e:
            return f"Error reading file: {e}"
    
    def __repr__(self) -> str:
        return f"{self.loader_name}(extensions={self.supported_extensions})"
