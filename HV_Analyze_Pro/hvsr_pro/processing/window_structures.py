"""
Window data structures for HVSR Pro
====================================

Defines window objects and state management.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum
from datetime import datetime

from hvsr_pro.core.data_structures import SeismicData


class WindowState(Enum):
    """
    Enumeration of possible window states.
    
    States:
        ACTIVE: Window is active and will be used in processing
        REJECTED_AUTO: Window was automatically rejected by algorithm
        REJECTED_MANUAL: Window was manually rejected by user
        BORDERLINE: Window is borderline quality (user should review)
        PENDING: Window status not yet determined
    """
    ACTIVE = "active"
    REJECTED_AUTO = "rejected_auto"
    REJECTED_MANUAL = "rejected_manual"
    BORDERLINE = "borderline"
    PENDING = "pending"
    
    def is_rejected(self) -> bool:
        """Check if window is in a rejected state."""
        return self in [WindowState.REJECTED_AUTO, WindowState.REJECTED_MANUAL]
    
    def is_usable(self) -> bool:
        """Check if window can be used in processing."""
        return self == WindowState.ACTIVE


@dataclass
class Window:
    """
    Represents a single time window of seismic data.
    
    Attributes:
        index: Window index in sequence
        start_sample: Start sample index in full record
        end_sample: End sample index in full record
        data: Three-component window data
        state: Current window state
        visible: Visibility flag for layer management (True = shown in plot)
        quality_metrics: Dictionary of quality metrics
        rejection_reason: Reason for rejection (if rejected)
        metadata: Additional metadata
        
    Note:
        The dual state system:
        - `state`: ACTIVE/REJECTED (controlled by QC algorithms + timeline clicks)
        - `visible`: True/False (controlled by layer dock checkboxes)
        - Window included in HVSR if: state==ACTIVE AND visible==True
    """
    index: int
    start_sample: int
    end_sample: int
    data: SeismicData
    state: WindowState = WindowState.PENDING
    visible: bool = True  # Default: visible
    quality_metrics: Dict[str, float] = field(default_factory=dict)
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate window after initialization."""
        if self.end_sample <= self.start_sample:
            raise ValueError("End sample must be greater than start sample")
        
        if self.data.n_samples != (self.end_sample - self.start_sample):
            raise ValueError(
                f"Data length ({self.data.n_samples}) does not match "
                f"window span ({self.end_sample - self.start_sample})"
            )
    
    @property
    def duration(self) -> float:
        """Return window duration in seconds."""
        return self.data.duration
    
    @property
    def start_time(self) -> float:
        """Return start time in seconds from beginning of record."""
        return self.start_sample / self.data.sampling_rate
    
    @property
    def end_time(self) -> float:
        """Return end time in seconds from beginning of record."""
        return self.end_sample / self.data.sampling_rate
    
    @property
    def center_time(self) -> float:
        """Return center time in seconds."""
        return (self.start_time + self.end_time) / 2.0
    
    @property
    def n_samples(self) -> int:
        """Return number of samples in window."""
        return self.end_sample - self.start_sample
    
    def is_active(self) -> bool:
        """Check if window is active."""
        return self.state.is_usable()
    
    def is_rejected(self) -> bool:
        """Check if window is rejected."""
        return self.state.is_rejected()
    
    def reject(self, reason: str, manual: bool = False) -> None:
        """
        Reject this window.
        
        Args:
            reason: Reason for rejection
            manual: True if manual rejection by user
        """
        self.state = WindowState.REJECTED_MANUAL if manual else WindowState.REJECTED_AUTO
        self.rejection_reason = reason
    
    def activate(self) -> None:
        """Activate this window."""
        self.state = WindowState.ACTIVE
        self.rejection_reason = None
    
    def toggle_state(self) -> None:
        """Toggle between active and manually rejected."""
        if self.state == WindowState.ACTIVE:
            self.reject("Manually toggled", manual=True)
        else:
            self.activate()
    
    def should_include_in_hvsr(self) -> bool:
        """
        Check if window should be included in HVSR calculation.
        
        Returns:
            True if window is active AND visible, False otherwise
        """
        return self.is_active() and self.visible
    
    def set_visibility(self, visible: bool) -> None:
        """
        Set visibility flag.
        
        Args:
            visible: True to show window, False to hide
        """
        self.visible = visible
    
    def is_visible(self) -> bool:
        """
        Check if window is currently visible.
        
        Returns:
            True if visible, False otherwise
        """
        return self.visible
    
    def get_quality_score(self, metric: str = 'overall') -> Optional[float]:
        """
        Get quality score for this window.
        
        Args:
            metric: Metric name ('overall', 'snr', 'stationarity', etc.)
            
        Returns:
            Quality score or None if not available
        """
        return self.quality_metrics.get(metric)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert window to dictionary representation.
        
        Returns:
            Dictionary with window information
        """
        return {
            'index': self.index,
            'start_sample': self.start_sample,
            'end_sample': self.end_sample,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'state': self.state.value,
            'rejection_reason': self.rejection_reason,
            'quality_metrics': self.quality_metrics,
            'metadata': self.metadata
        }
    
    def __repr__(self) -> str:
        return (f"Window(index={self.index}, "
                f"time={self.start_time:.1f}-{self.end_time:.1f}s, "
                f"state={self.state.value})")
    
    def __str__(self) -> str:
        lines = [
            f"Window #{self.index}",
            f"  Time: {self.start_time:.2f} - {self.end_time:.2f}s (duration: {self.duration:.2f}s)",
            f"  Samples: {self.start_sample} - {self.end_sample} ({self.n_samples} samples)",
            f"  State: {self.state.value}",
        ]
        
        if self.rejection_reason:
            lines.append(f"  Rejection: {self.rejection_reason}")
        
        if self.quality_metrics:
            lines.append("  Quality Metrics:")
            for metric, value in self.quality_metrics.items():
                lines.append(f"    {metric}: {value:.3f}")
        
        return "\n".join(lines)


@dataclass
class WindowCollection:
    """
    Collection of windows with state management.
    
    Attributes:
        windows: List of Window objects
        source_data: Original seismic data
        window_length: Length of each window in seconds
        overlap: Overlap fraction (0.0 - 1.0)
        metadata: Collection metadata
    """
    windows: List[Window]
    source_data: SeismicData
    window_length: float
    overlap: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize collection."""
        self.metadata['created_at'] = datetime.now().isoformat()
        self.metadata['n_windows'] = len(self.windows)
    
    @property
    def n_windows(self) -> int:
        """Return total number of windows."""
        return len(self.windows)
    
    @property
    def n_active(self) -> int:
        """Return number of active windows."""
        return sum(1 for w in self.windows if w.is_active())
    
    @property
    def n_rejected(self) -> int:
        """Return number of rejected windows."""
        return sum(1 for w in self.windows if w.is_rejected())
    
    @property
    def acceptance_rate(self) -> float:
        """Return acceptance rate (0.0 - 1.0)."""
        if self.n_windows == 0:
            return 0.0
        return self.n_active / self.n_windows
    
    def get_active_windows(self) -> List[Window]:
        """Return list of active windows."""
        return [w for w in self.windows if w.is_active()]
    
    def get_rejected_windows(self) -> List[Window]:
        """Return list of rejected windows."""
        return [w for w in self.windows if w.is_rejected()]
    
    def get_window(self, index: int) -> Optional[Window]:
        """
        Get window by index.
        
        Args:
            index: Window index
            
        Returns:
            Window object or None if not found
        """
        for window in self.windows:
            if window.index == index:
                return window
        return None
    
    def get_windows_by_state(self, state: WindowState) -> List[Window]:
        """Get all windows with specified state."""
        return [w for w in self.windows if w.state == state]
    
    def reject_window(self, index: int, reason: str, manual: bool = False) -> bool:
        """
        Reject a window by index.
        
        Args:
            index: Window index
            reason: Rejection reason
            manual: Manual rejection flag
            
        Returns:
            True if window was found and rejected
        """
        window = self.get_window(index)
        if window:
            window.reject(reason, manual=manual)
            return True
        return False
    
    def activate_window(self, index: int) -> bool:
        """
        Activate a window by index.
        
        Args:
            index: Window index
            
        Returns:
            True if window was found and activated
        """
        window = self.get_window(index)
        if window:
            window.activate()
            return True
        return False
    
    def toggle_window(self, index: int) -> bool:
        """
        Toggle window state.
        
        Args:
            index: Window index
            
        Returns:
            True if window was found and toggled
        """
        window = self.get_window(index)
        if window:
            window.toggle_state()
            return True
        return False
    
    def get_quality_statistics(self, metric: str = 'overall') -> Dict[str, float]:
        """
        Get statistics for a quality metric across all windows.
        
        Args:
            metric: Quality metric name
            
        Returns:
            Dictionary with min, max, mean, std, median
        """
        active_windows = self.get_active_windows()
        if not active_windows:
            return {}
        
        scores = [w.get_quality_score(metric) for w in active_windows]
        scores = [s for s in scores if s is not None]
        
        if not scores:
            return {}
        
        scores_array = np.array(scores)
        return {
            'min': float(np.min(scores_array)),
            'max': float(np.max(scores_array)),
            'mean': float(np.mean(scores_array)),
            'std': float(np.std(scores_array)),
            'median': float(np.median(scores_array))
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert collection to dictionary."""
        return {
            'n_windows': self.n_windows,
            'n_active': self.n_active,
            'n_rejected': self.n_rejected,
            'acceptance_rate': self.acceptance_rate,
            'window_length': self.window_length,
            'overlap': self.overlap,
            'windows': [w.to_dict() for w in self.windows],
            'metadata': self.metadata
        }
    
    def __repr__(self) -> str:
        return (f"WindowCollection(n_windows={self.n_windows}, "
                f"active={self.n_active}, rejected={self.n_rejected})")
    
    def __str__(self) -> str:
        return (f"Window Collection\n"
                f"  Total Windows: {self.n_windows}\n"
                f"  Active: {self.n_active}\n"
                f"  Rejected: {self.n_rejected}\n"
                f"  Acceptance Rate: {self.acceptance_rate:.1%}\n"
                f"  Window Length: {self.window_length}s\n"
                f"  Overlap: {self.overlap:.1%}")
