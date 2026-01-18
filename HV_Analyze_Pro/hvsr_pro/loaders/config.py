"""
Loader Configuration Module
===========================

Configuration dataclasses for all data loaders.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LoaderConfig:
    """
    Base configuration for all data loaders.
    
    Attributes:
        degrees_from_north: Rotation in degrees of the sensor's north component
            relative to magnetic north (clockwise positive). Default is None,
            indicating either use metadata from file or assume 0.
        verbose: Enable verbose logging during loading.
    """
    degrees_from_north: Optional[float] = None
    verbose: bool = False
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.degrees_from_north is not None:
            # Normalize to 0-360 range
            self.degrees_from_north = float(
                self.degrees_from_north - 360 * (self.degrees_from_north // 360)
            )


@dataclass
class SAFConfig(LoaderConfig):
    """
    Configuration for SAF (SESAME ASCII Format) loader.
    
    SAF files typically contain NORTH_ROT in the header, which will be used
    if degrees_from_north is not explicitly provided.
    """
    pass


@dataclass
class SACConfig(LoaderConfig):
    """
    Configuration for SAC (Seismic Analysis Code) loader.
    
    Attributes:
        byteorder: Byte order for reading SAC files.
            - 'auto': Try little endian first, fall back to big endian
            - 'little': Force little endian
            - 'big': Force big endian
    """
    byteorder: str = 'auto'
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        super().__post_init__()
        valid_byteorders = ('auto', 'little', 'big')
        if self.byteorder not in valid_byteorders:
            raise ValueError(
                f"Invalid byteorder '{self.byteorder}'. "
                f"Must be one of: {valid_byteorders}"
            )


@dataclass
class GCFConfig(LoaderConfig):
    """
    Configuration for GCF (Guralp Compressed Format) loader.
    
    GCF files are read using ObsPy's GCF reader.
    """
    pass


@dataclass
class PEERConfig(LoaderConfig):
    """
    Configuration for PEER (Pacific Earthquake Engineering Research) loader.
    
    PEER files contain orientation information in the header which is used
    to determine component directions.
    """
    pass


@dataclass
class MiniSharkConfig(LoaderConfig):
    """
    Configuration for MiniShark format loader.
    
    MiniShark files contain gain and conversion factors in the header.
    """
    pass
