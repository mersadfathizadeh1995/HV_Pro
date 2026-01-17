"""
Peak Controller
===============

Handles peak detection and management operations for the main window.
"""

from typing import Optional, Dict, Any, List, Callable, Tuple

try:
    from PyQt5.QtWidgets import QWidget, QMessageBox
    from PyQt5.QtCore import QObject, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class PeakController(QObject):
        """
        Controller for peak detection and management.
        
        Handles:
        - Automatic peak detection (top-N, multi-peak)
        - Manual peak picking mode
        - Peak list management
        
        Signals:
            peaks_detected: Emitted with list of peaks after detection
            manual_mode_changed: Emitted when manual picking mode changes
            info_message: Emitted with info messages
            error_occurred: Emitted with error messages
        """
        
        peaks_detected = pyqtSignal(list)
        manual_mode_changed = pyqtSignal(bool)
        info_message = pyqtSignal(str)
        error_occurred = pyqtSignal(str)
        
        def __init__(self, parent: QWidget):
            """
            Initialize peak controller.
            
            Args:
                parent: Parent widget (main window)
            """
            super().__init__(parent)
            self.parent = parent
            self.hvsr_result = None
            self.peak_picker_dock = None
            self.plot_manager = None
            self._manual_mode = False
            self._detected_peaks: List[Dict] = []
        
        def set_references(self, hvsr_result, peak_picker_dock, plot_manager):
            """
            Set references to required objects.
            
            Args:
                hvsr_result: HVSRResult object
                peak_picker_dock: PeakPickerDock widget
                plot_manager: PlotWindowManager object
            """
            self.hvsr_result = hvsr_result
            self.peak_picker_dock = peak_picker_dock
            self.plot_manager = plot_manager
        
        def set_hvsr_result(self, hvsr_result):
            """Set the HVSR result for peak detection."""
            self.hvsr_result = hvsr_result
        
        def detect_peaks(self, mode: str, settings: dict) -> List[Dict]:
            """
            Detect peaks using specified algorithm.
            
            Args:
                mode: Detection mode ('auto_top_n' or 'auto_multi')
                settings: Detection settings dict with keys:
                    - n_peaks: Number of peaks to find (auto_top_n)
                    - prominence: Peak prominence threshold
                    - min_distance: Minimum distance between peaks (auto_multi)
                    - freq_min, freq_max: Frequency range
                    
            Returns:
                List of peak dictionaries with 'frequency' and 'amplitude' keys
            """
            if self.hvsr_result is None:
                self.error_occurred.emit("No HVSR data available for peak detection")
                return []
            
            self.info_message.emit(f"Peak detection: mode={mode}, settings={settings}")
            
            try:
                from hvsr_pro.processing.windows import find_top_n_peaks, find_multi_peaks
                
                frequencies = self.hvsr_result.frequencies
                mean_hvsr = self.hvsr_result.mean_hvsr
                
                peaks = []
                
                if mode == "auto_top_n":
                    peaks = find_top_n_peaks(
                        frequencies,
                        mean_hvsr,
                        n_peaks=settings.get('n_peaks', 3),
                        prominence=settings.get('prominence', 0.5),
                        freq_range=(settings.get('freq_min', 0.1), settings.get('freq_max', 20.0))
                    )
                    self.info_message.emit(f"Auto Top N: Found {len(peaks)} peak(s)")
                    
                elif mode == "auto_multi":
                    peaks = find_multi_peaks(
                        frequencies,
                        mean_hvsr,
                        prominence=settings.get('prominence', 0.5),
                        min_distance=settings.get('min_distance', 5),
                        freq_range=(settings.get('freq_min', 0.1), settings.get('freq_max', 20.0))
                    )
                    self.info_message.emit(f"Auto Multi: Found {len(peaks)} peak(s)")
                
                else:
                    self.info_message.emit(f"Unknown detection mode: {mode}")
                    return []
                
                # Store detected peaks
                self._detected_peaks = peaks
                
                # Log peak details
                for i, peak in enumerate(peaks, 1):
                    self.info_message.emit(
                        f"  Peak {i}: f={peak['frequency']:.2f} Hz, A={peak['amplitude']:.2f}"
                    )
                
                self.peaks_detected.emit(peaks)
                return peaks
                
            except Exception as e:
                self.error_occurred.emit(f"Peak detection failed: {str(e)}")
                return []
        
        def on_peaks_changed(self, peaks: list):
            """
            Handle peak list changes (from dock).
            Updates plot markers.
            
            Args:
                peaks: List of peak dictionaries
            """
            if self.plot_manager:
                self.plot_manager.add_peak_markers(peaks)
            self.info_message.emit(f"Peaks updated: {len(peaks)} peak(s) - markers updated on plot")
        
        def enable_manual_mode(self, callback: Callable[[float, float], None] = None):
            """
            Enable manual peak picking mode.
            
            Args:
                callback: Callback function for when a peak is selected (frequency, amplitude)
            """
            self._manual_mode = True
            if self.plot_manager:
                self.plot_manager.enable_manual_picking(callback or self._on_manual_peak_selected)
            self.info_message.emit("Manual peak picking ACTIVE - Click on HVSR curve to add peak")
            self.manual_mode_changed.emit(True)
        
        def disable_manual_mode(self):
            """Disable manual peak picking mode."""
            self._manual_mode = False
            if self.plot_manager:
                self.plot_manager.disable_manual_picking()
            self.info_message.emit("Manual peak picking deactivated")
            self.manual_mode_changed.emit(False)
        
        def toggle_manual_mode(self, activate: bool):
            """
            Toggle manual peak picking mode.
            
            Args:
                activate: True to enable, False to disable
            """
            if activate:
                self.enable_manual_mode()
            else:
                self.disable_manual_mode()
        
        def _on_manual_peak_selected(self, frequency: float, amplitude: float):
            """
            Handle manual peak selection from plot click.
            
            Args:
                frequency: Clicked frequency (Hz)
                amplitude: Clicked amplitude (H/V ratio)
            """
            if self.peak_picker_dock:
                self.peak_picker_dock.add_peak(frequency, amplitude, source='Manual')
            self.info_message.emit(f"Manual peak added: f={frequency:.2f} Hz, A={amplitude:.2f}")
        
        def add_manual_peak(self, frequency: float, amplitude: float):
            """
            Add a manually selected peak.
            
            Args:
                frequency: Peak frequency (Hz)
                amplitude: Peak amplitude (H/V ratio)
            """
            if self.peak_picker_dock:
                self.peak_picker_dock.add_peak(frequency, amplitude, source='Manual')
            self.info_message.emit(f"Manual peak added: f={frequency:.2f} Hz, A={amplitude:.2f}")
        
        def get_detected_peaks(self) -> List[Dict]:
            """Get list of detected peaks."""
            return self._detected_peaks.copy()
        
        def clear_peaks(self):
            """Clear all detected peaks."""
            self._detected_peaks = []
            if self.peak_picker_dock:
                self.peak_picker_dock.clear_peaks()
            if self.plot_manager:
                self.plot_manager.clear_peak_markers()
        
        @property
        def is_manual_mode(self) -> bool:
            """Check if manual picking mode is active."""
            return self._manual_mode


else:
    class PeakController:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
