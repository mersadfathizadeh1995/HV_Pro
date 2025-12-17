"""
HVSR Pro Azimuthal Processing Worker
====================================

Background thread for azimuthal HVSR processing.
"""

import numpy as np
from typing import Dict, Optional, Callable

try:
    from PyQt5.QtCore import QThread, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False
    class QThread:
        pass
    class pyqtSignal:
        def __init__(self, *args): pass


class AzimuthalProcessingThread(QThread):
    """Background thread for azimuthal HVSR processing."""
    
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)  # AzimuthalHVSRResult
    error = pyqtSignal(str)
    
    def __init__(self, windows, settings: Dict):
        """
        Initialize azimuthal processing thread.
        
        Args:
            windows: WindowCollection from main processing
            settings: Dict with processing settings including:
                - azimuth_start: Starting azimuth in degrees
                - azimuth_end: Ending azimuth in degrees
                - azimuth_step: Azimuth step in degrees
                - smoothing_bandwidth: Konno-Ohmachi smoothing bandwidth
                - f_min: Minimum frequency (Hz)
                - f_max: Maximum frequency (Hz)
                - n_frequencies: Number of frequency points
                - parallel: Whether to use parallel processing
                - n_workers: Number of worker threads (optional)
        """
        super().__init__()
        self.windows = windows
        self.settings = settings
    
    def run(self):
        """Execute azimuthal processing."""
        try:
            from hvsr_pro.processing.azimuthal import AzimuthalHVSRProcessor
            
            # Create azimuths array
            azimuths = np.arange(
                self.settings['azimuth_start'],
                self.settings['azimuth_end'],
                self.settings['azimuth_step']
            )
            
            # Create processor
            processor = AzimuthalHVSRProcessor(
                azimuths=azimuths,
                smoothing_bandwidth=self.settings['smoothing_bandwidth'],
                f_min=self.settings['f_min'],
                f_max=self.settings['f_max'],
                n_frequencies=self.settings['n_frequencies'],
                parallel=self.settings['parallel'],
                n_workers=self.settings.get('n_workers')
            )
            
            # Progress callback
            def progress_callback(progress: int, message: str):
                self.progress.emit(progress, message)
            
            # Process
            result = processor.process(self.windows, progress_callback=progress_callback)
            
            self.finished.emit(result)
            
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n\n{traceback.format_exc()}")

