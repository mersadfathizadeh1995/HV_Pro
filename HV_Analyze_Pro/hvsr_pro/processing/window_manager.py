"""
Window Manager for HVSR Pro
============================

Advanced window management with overlap, tapering, and state tracking.
"""

import numpy as np
from typing import Optional, Dict, Any, List, Callable
from scipy import signal
import logging

from hvsr_pro.core.data_structures import SeismicData
from hvsr_pro.processing.window_structures import Window, WindowState, WindowCollection
from hvsr_pro.processing.quality_metrics import WindowQualityCalculator

logger = logging.getLogger(__name__)


class WindowManager:
    """
    Advanced window management system for HVSR analysis.
    
    Features:
    - Configurable window length and overlap
    - Multiple tapering functions
    - Window state tracking
    - Quality metrics calculation
    - Persistence and recovery
    
    Example:
        >>> manager = WindowManager(window_length=30, overlap=0.5)
        >>> windows = manager.create_windows(seismic_data)
        >>> print(f"Created {windows.n_windows} windows")
    """
    
    def __init__(self,
                 window_length: float = 30.0,
                 overlap: float = 0.5,
                 taper_type: str = 'tukey',
                 taper_width: float = 0.1,
                 min_window_length: Optional[float] = None):
        """
        Initialize window manager.
        
        Args:
            window_length: Length of each window in seconds (default: 30)
            overlap: Overlap fraction 0.0-1.0 (default: 0.5 = 50%)
            taper_type: Taper function ('tukey', 'hann', 'hamming', 'blackman', 'none')
            taper_width: Taper width parameter (for tukey, default: 0.1)
            min_window_length: Minimum window length in seconds (default: window_length)
        """
        if not 0 <= overlap < 1.0:
            raise ValueError(f"Overlap must be between 0 and 1, got {overlap}")
        
        if window_length <= 0:
            raise ValueError(f"Window length must be positive, got {window_length}")
        
        self.window_length = window_length
        self.overlap = overlap
        self.taper_type = taper_type
        self.taper_width = taper_width
        self.min_window_length = min_window_length or window_length
        
        # Quality calculator
        self.quality_calculator = WindowQualityCalculator()
        
        logger.info(
            f"WindowManager initialized: length={window_length}s, "
            f"overlap={overlap:.1%}, taper={taper_type}"
        )
    
    def create_windows(self,
                      data: SeismicData,
                      calculate_quality: bool = True) -> WindowCollection:
        """
        Create windows from seismic data.
        
        Args:
            data: SeismicData object
            calculate_quality: Calculate quality metrics for each window
            
        Returns:
            WindowCollection with all windows
        """
        # Calculate window parameters
        samples_per_window = int(self.window_length * data.sampling_rate)
        step_size = int(samples_per_window * (1 - self.overlap))
        
        if samples_per_window > data.n_samples:
            raise ValueError(
                f"Window length ({self.window_length}s = {samples_per_window} samples) "
                f"is longer than data ({data.duration:.1f}s = {data.n_samples} samples)"
            )
        
        # Generate window boundaries
        windows = []
        window_idx = 0
        start_sample = 0
        
        while start_sample + samples_per_window <= data.n_samples:
            end_sample = start_sample + samples_per_window
            
            # Extract window data
            window_data = data.get_slice(start_sample, end_sample)
            
            # Apply taper
            if self.taper_type != 'none':
                window_data = self._apply_taper(window_data)
            
            # Create window object
            window = Window(
                index=window_idx,
                start_sample=start_sample,
                end_sample=end_sample,
                data=window_data,
                state=WindowState.PENDING,
                metadata={
                    'taper_type': self.taper_type,
                    'taper_width': self.taper_width,
                    'overlap': self.overlap
                }
            )
            
            # Calculate quality metrics
            if calculate_quality:
                metrics = self.quality_calculator.calculate_all(window)
                window.quality_metrics = metrics
            
            windows.append(window)
            
            # Move to next window
            window_idx += 1
            start_sample += step_size
        
        # Handle last partial window if needed
        if start_sample < data.n_samples and self._should_include_last_window(start_sample, data.n_samples):
            end_sample = data.n_samples
            window_data = data.get_slice(start_sample, end_sample)
            
            if self.taper_type != 'none':
                window_data = self._apply_taper(window_data)
            
            window = Window(
                index=window_idx,
                start_sample=start_sample,
                end_sample=end_sample,
                data=window_data,
                state=WindowState.PENDING,
                metadata={
                    'taper_type': self.taper_type,
                    'partial': True
                }
            )
            
            if calculate_quality:
                metrics = self.quality_calculator.calculate_all(window)
                window.quality_metrics = metrics
            
            windows.append(window)
        
        # Create collection
        collection = WindowCollection(
            windows=windows,
            source_data=data,
            window_length=self.window_length,
            overlap=self.overlap,
            metadata={
                'taper_type': self.taper_type,
                'samples_per_window': samples_per_window,
                'step_size': step_size
            }
        )
        
        # Set all windows to active by default
        for window in collection.windows:
            window.state = WindowState.ACTIVE
        
        logger.info(
            f"Created {collection.n_windows} windows from "
            f"{data.duration:.1f}s of data"
        )
        
        return collection
    
    def _should_include_last_window(self, start_sample: int, total_samples: int) -> bool:
        """Check if last partial window should be included."""
        remaining_samples = total_samples - start_sample
        min_samples = int(self.min_window_length * (total_samples / start_sample))
        return remaining_samples >= min_samples
    
    def _apply_taper(self, data: SeismicData) -> SeismicData:
        """
        Apply taper to window data.
        
        Args:
            data: Window data
            
        Returns:
            Tapered data
        """
        n_samples = data.n_samples
        
        # Generate taper window
        if self.taper_type == 'tukey':
            taper = signal.windows.tukey(n_samples, alpha=self.taper_width)
        elif self.taper_type == 'hann':
            taper = signal.windows.hann(n_samples)
        elif self.taper_type == 'hamming':
            taper = signal.windows.hamming(n_samples)
        elif self.taper_type == 'blackman':
            taper = signal.windows.blackman(n_samples)
        else:
            return data  # No taper
        
        # Apply taper to each component
        from hvsr_pro.core.data_structures import ComponentData, SeismicData
        
        east = ComponentData(
            name=data.east.name,
            data=data.east.data * taper,
            sampling_rate=data.east.sampling_rate,
            start_time=data.east.start_time,
            units=data.east.units,
            metadata=data.east.metadata.copy()
        )
        
        north = ComponentData(
            name=data.north.name,
            data=data.north.data * taper,
            sampling_rate=data.north.sampling_rate,
            start_time=data.north.start_time,
            units=data.north.units,
            metadata=data.north.metadata.copy()
        )
        
        vertical = ComponentData(
            name=data.vertical.name,
            data=data.vertical.data * taper,
            sampling_rate=data.vertical.sampling_rate,
            start_time=data.vertical.start_time,
            units=data.vertical.units,
            metadata=data.vertical.metadata.copy()
        )
        
        tapered_data = SeismicData(
            east=east,
            north=north,
            vertical=vertical,
            station_name=data.station_name,
            location=data.location,
            source_file=data.source_file,
            metadata=data.metadata.copy()
        )
        
        return tapered_data
    
    def recalculate_quality(self, collection: WindowCollection) -> WindowCollection:
        """
        Recalculate quality metrics for all windows.
        
        Args:
            collection: Window collection
            
        Returns:
            Updated collection
        """
        for window in collection.windows:
            metrics = self.quality_calculator.calculate_all(window)
            window.quality_metrics = metrics
        
        logger.info(f"Recalculated quality metrics for {collection.n_windows} windows")
        return collection
    
    def apply_state_to_all(self, 
                          collection: WindowCollection,
                          state: WindowState,
                          reason: Optional[str] = None) -> WindowCollection:
        """
        Apply state to all windows.
        
        Args:
            collection: Window collection
            state: State to apply
            reason: Reason for state change
            
        Returns:
            Updated collection
        """
        for window in collection.windows:
            window.state = state
            if reason:
                window.rejection_reason = reason
        
        logger.info(f"Applied state {state.value} to all {collection.n_windows} windows")
        return collection
    
    def get_window_boundaries(self, 
                             data_duration: float,
                             sampling_rate: float) -> List[tuple[int, int]]:
        """
        Calculate window boundaries without creating full windows.
        
        Args:
            data_duration: Duration of data in seconds
            sampling_rate: Sampling rate in Hz
            
        Returns:
            List of (start_sample, end_sample) tuples
        """
        total_samples = int(data_duration * sampling_rate)
        samples_per_window = int(self.window_length * sampling_rate)
        step_size = int(samples_per_window * (1 - self.overlap))
        
        boundaries = []
        start_sample = 0
        
        while start_sample + samples_per_window <= total_samples:
            end_sample = start_sample + samples_per_window
            boundaries.append((start_sample, end_sample))
            start_sample += step_size
        
        return boundaries
    
    def save_collection(self, 
                       collection: WindowCollection,
                       filepath: str) -> None:
        """
        Save window collection to file.
        
        Args:
            collection: Window collection
            filepath: Output file path (JSON format)
        """
        import json
        from pathlib import Path
        
        output = collection.to_dict()
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Saved window collection to {filepath}")
    
    def load_collection_state(self,
                             collection: WindowCollection,
                             filepath: str) -> WindowCollection:
        """
        Load window states from file.
        
        Args:
            collection: Existing window collection
            filepath: Input file path
            
        Returns:
            Updated collection with loaded states
        """
        import json
        
        with open(filepath, 'r') as f:
            saved_data = json.load(f)
        
        # Update window states
        for saved_window in saved_data['windows']:
            idx = saved_window['index']
            window = collection.get_window(idx)
            
            if window:
                window.state = WindowState(saved_window['state'])
                window.rejection_reason = saved_window.get('rejection_reason')
        
        logger.info(f"Loaded window states from {filepath}")
        return collection
    
    def __repr__(self) -> str:
        return (f"WindowManager(length={self.window_length}s, "
                f"overlap={self.overlap:.1%}, taper={self.taper_type})")
