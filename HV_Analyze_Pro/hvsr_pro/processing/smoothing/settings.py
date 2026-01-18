"""
Smoothing Settings
==================

Configuration dataclasses and enums for smoothing methods.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List


class SmoothingMethod(Enum):
    """Available smoothing methods."""
    KONNO_OHMACHI = "konno_ohmachi"
    PARZEN = "parzen"
    SAVITZKY_GOLAY = "savitzky_golay"
    LINEAR_RECTANGULAR = "linear_rectangular"
    LOG_RECTANGULAR = "log_rectangular"
    LINEAR_TRIANGULAR = "linear_triangular"
    LOG_TRIANGULAR = "log_triangular"
    NONE = "none"
    
    @classmethod
    def from_string(cls, name: str) -> 'SmoothingMethod':
        """Get enum member from string name."""
        name_lower = name.lower().replace(" ", "_").replace("-", "_")
        for member in cls:
            if member.value == name_lower:
                return member
        raise ValueError(f"Unknown smoothing method: {name}")
    
    def display_name(self) -> str:
        """Get human-readable display name."""
        display_names = {
            SmoothingMethod.KONNO_OHMACHI: "Konno-Ohmachi",
            SmoothingMethod.PARZEN: "Parzen",
            SmoothingMethod.SAVITZKY_GOLAY: "Savitzky-Golay",
            SmoothingMethod.LINEAR_RECTANGULAR: "Linear Rectangular",
            SmoothingMethod.LOG_RECTANGULAR: "Log Rectangular",
            SmoothingMethod.LINEAR_TRIANGULAR: "Linear Triangular",
            SmoothingMethod.LOG_TRIANGULAR: "Log Triangular",
            SmoothingMethod.NONE: "None",
        }
        return display_names.get(self, self.value)


# Default bandwidths for each method
DEFAULT_BANDWIDTHS: Dict[SmoothingMethod, float] = {
    SmoothingMethod.KONNO_OHMACHI: 40.0,
    SmoothingMethod.PARZEN: 0.5,
    SmoothingMethod.SAVITZKY_GOLAY: 9,
    SmoothingMethod.LINEAR_RECTANGULAR: 0.5,
    SmoothingMethod.LOG_RECTANGULAR: 0.05,
    SmoothingMethod.LINEAR_TRIANGULAR: 0.5,
    SmoothingMethod.LOG_TRIANGULAR: 0.05,
    SmoothingMethod.NONE: 0,
}


# Bandwidth parameter descriptions
BANDWIDTH_DESCRIPTIONS: Dict[SmoothingMethod, str] = {
    SmoothingMethod.KONNO_OHMACHI: (
        "Smoothing bandwidth parameter (b). Higher values = less smoothing. "
        "Typical values: 20-80. Standard: 40."
    ),
    SmoothingMethod.PARZEN: (
        "Window width in Hz. Lower values = less smoothing. "
        "Typical values: 0.1-2.0 Hz."
    ),
    SmoothingMethod.SAVITZKY_GOLAY: (
        "Number of points (must be odd integer). More points = more smoothing. "
        "Typical values: 5, 9, 11, 15."
    ),
    SmoothingMethod.LINEAR_RECTANGULAR: (
        "Window width in Hz. Lower values = less smoothing. "
        "Typical values: 0.1-2.0 Hz."
    ),
    SmoothingMethod.LOG_RECTANGULAR: (
        "Window width in log10 scale. Lower values = less smoothing. "
        "Typical values: 0.01-0.2."
    ),
    SmoothingMethod.LINEAR_TRIANGULAR: (
        "Window width in Hz. Lower values = less smoothing. "
        "Typical values: 0.1-2.0 Hz."
    ),
    SmoothingMethod.LOG_TRIANGULAR: (
        "Window width in log10 scale. Lower values = less smoothing. "
        "Typical values: 0.01-0.2."
    ),
    SmoothingMethod.NONE: "No smoothing applied.",
}


# Bandwidth validation ranges
BANDWIDTH_RANGES: Dict[SmoothingMethod, tuple] = {
    SmoothingMethod.KONNO_OHMACHI: (1.0, 200.0),
    SmoothingMethod.PARZEN: (0.01, 10.0),
    SmoothingMethod.SAVITZKY_GOLAY: (3, 51),  # Must be odd
    SmoothingMethod.LINEAR_RECTANGULAR: (0.01, 10.0),
    SmoothingMethod.LOG_RECTANGULAR: (0.001, 1.0),
    SmoothingMethod.LINEAR_TRIANGULAR: (0.01, 10.0),
    SmoothingMethod.LOG_TRIANGULAR: (0.001, 1.0),
    SmoothingMethod.NONE: (0, 0),
}


@dataclass
class SmoothingConfig:
    """
    Configuration for spectral smoothing.
    
    Attributes
    ----------
    method : SmoothingMethod
        The smoothing method to use. Default is Konno-Ohmachi.
    bandwidth : float
        Method-specific bandwidth parameter. See BANDWIDTH_DESCRIPTIONS
        for meaning of this parameter for each method.
    center_frequencies_hz : list, optional
        Custom center frequencies for smoothing output. If None,
        input frequencies are used.
    """
    method: SmoothingMethod = SmoothingMethod.KONNO_OHMACHI
    bandwidth: float = 40.0
    center_frequencies_hz: Optional[List[float]] = None
    
    def __post_init__(self):
        """Validate and convert types after initialization."""
        if isinstance(self.method, str):
            self.method = SmoothingMethod.from_string(self.method)
    
    def get_default_bandwidth(self) -> float:
        """Get default bandwidth for current method."""
        return DEFAULT_BANDWIDTHS.get(self.method, 40.0)
    
    def get_bandwidth_description(self) -> str:
        """Get description of bandwidth parameter for current method."""
        return BANDWIDTH_DESCRIPTIONS.get(self.method, "")
    
    def get_bandwidth_range(self) -> tuple:
        """Get valid range for bandwidth parameter."""
        return BANDWIDTH_RANGES.get(self.method, (0, 100))
    
    def validate(self) -> List[str]:
        """
        Validate configuration.
        
        Returns
        -------
        list
            List of validation error messages (empty if valid).
        """
        errors = []
        
        # Check bandwidth range
        min_bw, max_bw = self.get_bandwidth_range()
        if self.method != SmoothingMethod.NONE:
            if self.bandwidth < min_bw or self.bandwidth > max_bw:
                errors.append(
                    f"Bandwidth must be between {min_bw} and {max_bw} "
                    f"for {self.method.display_name()}"
                )
        
        # Savitzky-Golay specific: must be odd integer
        if self.method == SmoothingMethod.SAVITZKY_GOLAY:
            bw_int = int(self.bandwidth)
            if bw_int % 2 != 1:
                errors.append("Savitzky-Golay bandwidth must be an odd integer")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'method': self.method.value,
            'bandwidth': self.bandwidth,
            'center_frequencies_hz': self.center_frequencies_hz,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SmoothingConfig':
        """Create from dictionary."""
        return cls(
            method=SmoothingMethod.from_string(data.get('method', 'konno_ohmachi')),
            bandwidth=data.get('bandwidth', 40.0),
            center_frequencies_hz=data.get('center_frequencies_hz'),
        )
    
    def with_defaults(self) -> 'SmoothingConfig':
        """Return a copy with default bandwidth for current method."""
        return SmoothingConfig(
            method=self.method,
            bandwidth=self.get_default_bandwidth(),
            center_frequencies_hz=self.center_frequencies_hz,
        )


def get_method_info(method: SmoothingMethod) -> Dict[str, Any]:
    """
    Get comprehensive information about a smoothing method.
    
    Parameters
    ----------
    method : SmoothingMethod
        The smoothing method.
        
    Returns
    -------
    dict
        Dictionary with keys: display_name, default_bandwidth, 
        bandwidth_range, description.
    """
    return {
        'display_name': method.display_name(),
        'default_bandwidth': DEFAULT_BANDWIDTHS.get(method, 40.0),
        'bandwidth_range': BANDWIDTH_RANGES.get(method, (0, 100)),
        'description': BANDWIDTH_DESCRIPTIONS.get(method, ""),
    }


def list_available_methods() -> List[Dict[str, Any]]:
    """
    List all available smoothing methods with their info.
    
    Returns
    -------
    list
        List of method info dictionaries.
    """
    return [
        {'method': m, **get_method_info(m)}
        for m in SmoothingMethod
    ]
