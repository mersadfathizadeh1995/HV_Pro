"""
Processing Controller
=====================

Controller for managing HVSR processing operations.
Handles processing thread management, progress updates, and result validation.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, Any, Dict

try:
    from PyQt5.QtCore import QObject, pyqtSignal
    from PyQt5.QtWidgets import QMessageBox
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

from hvsr_pro.gui.main_window_modules.panels import ProcessingSettings
from hvsr_pro.processing.rejection.settings import QCSettings, CoxFDWRASettings


@dataclass
class FullProcessingSettings:
    """Combined settings for a complete processing run."""
    processing: ProcessingSettings
    qc: QCSettings
    cox_fdwra: CoxFDWRASettings
    use_parallel: bool = True
    n_cores: int = 4
    load_mode: str = 'single'
    time_range: Optional[Dict] = None
    current_file: Any = None


if HAS_PYQT5:
    class ProcessingController(QObject):
        """
        Controller for HVSR processing operations.
        
        Manages:
        - Starting and stopping processing threads
        - Progress reporting
        - Result validation
        - QC failure handling
        
        Signals:
            processing_started: Emitted when processing begins
            processing_finished: Emitted with (result, windows, data) on success
            processing_error: Emitted with error message on failure
            progress_updated: Emitted with (percent, message) during processing
        """
        
        processing_started = pyqtSignal()
        processing_finished = pyqtSignal(object, object, object)  # result, windows, data
        processing_error = pyqtSignal(str)
        progress_updated = pyqtSignal(int, str)
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.parent_window = parent
            self._thread = None
            self._hvsr_result = None
            self._windows = None
            self._data = None
        
        @property
        def hvsr_result(self):
            """Get the last HVSR result."""
            return self._hvsr_result
        
        @property
        def windows(self):
            """Get the last window collection."""
            return self._windows
        
        @property
        def data(self):
            """Get the last seismic data."""
            return self._data
        
        def start_processing(self, settings: FullProcessingSettings):
            """
            Start HVSR processing with given settings.
            
            Args:
                settings: FullProcessingSettings with all parameters
            """
            if not settings.current_file:
                self.processing_error.emit("No file loaded. Please load a data file first.")
                return
            
            # Validate frequency range
            if settings.processing.freq_min >= settings.processing.freq_max:
                self.processing_error.emit(
                    "Invalid frequency range: minimum must be less than maximum"
                )
                return
            
            self.processing_started.emit()
            
            # Get custom QC settings if in custom mode
            custom_qc_settings = None
            if settings.qc.mode == 'custom':
                custom_qc_settings = self._build_custom_qc_settings(settings.qc)
            
            # Build Cox FDWRA settings dict
            cox_fdwra_settings = {
                'n': settings.cox_fdwra.n_value,
                'max_iterations': settings.cox_fdwra.max_iterations,
                'min_iterations': settings.cox_fdwra.min_iterations,
                'distribution': settings.cox_fdwra.distribution
            }
            
            # Import and create processing thread
            from hvsr_pro.gui.workers import ProcessingThread
            
            self._thread = ProcessingThread(
                settings.current_file,
                settings.processing.window_length,
                settings.processing.overlap,
                settings.processing.smoothing_bandwidth,
                settings.load_mode,
                settings.time_range,
                settings.processing.freq_min,
                settings.processing.freq_max,
                settings.processing.n_frequencies,
                settings.qc.preset if settings.qc.mode == 'preset' else 'custom',
                settings.cox_fdwra.enabled,
                settings.use_parallel,
                settings.n_cores,
                settings.processing.manual_sampling_rate,
                custom_qc_settings,
                cox_fdwra_settings,
                getattr(settings.processing, 'smoothing_method', 'konno_ohmachi'),
                qc_enabled=settings.qc.enabled,
                phase1_enabled=getattr(settings.qc, 'phase1_enabled', True),
                phase2_enabled=getattr(settings.qc, 'phase2_enabled', True)
            )
            
            # Connect signals
            self._thread.progress.connect(self._on_progress)
            self._thread.finished.connect(self._on_finished)
            self._thread.error.connect(self._on_error)
            
            # Start processing
            self._thread.start()
        
        def _build_custom_qc_settings(self, qc: QCSettings) -> Dict:
            """Build custom QC settings dictionary from QCSettings."""
            return {
                'enabled': qc.enabled,
                'mode': 'custom',
                'algorithms': {
                    'amplitude': {
                        'enabled': qc.custom_algorithms.get('amplitude', {}).get('enabled', False),
                        'params': {}
                    },
                    'quality_threshold': {
                        'enabled': qc.custom_algorithms.get('quality_threshold', {}).get('enabled', False),
                        'params': {'threshold': 0.5}
                    },
                    'sta_lta': {
                        'enabled': qc.custom_algorithms.get('sta_lta', {}).get('enabled', False),
                        'params': {
                            'sta_length': 1.0, 'lta_length': 30.0,
                            'min_ratio': 0.15, 'max_ratio': 2.5
                        }
                    },
                    'frequency_domain': {
                        'enabled': qc.custom_algorithms.get('frequency_domain', {}).get('enabled', False),
                        'params': {'spike_threshold': 3.0}
                    },
                    'statistical_outlier': {
                        'enabled': qc.custom_algorithms.get('statistical_outlier', {}).get('enabled', False),
                        'params': {'method': 'iqr', 'threshold': 2.0}
                    },
                    'hvsr_amplitude': {
                        'enabled': qc.custom_algorithms.get('hvsr_amplitude', {}).get('enabled', False),
                        'params': {'min_amplitude': 1.0}
                    },
                    'flat_peak': {
                        'enabled': qc.custom_algorithms.get('flat_peak', {}).get('enabled', False),
                        'params': {'flatness_threshold': 0.15}
                    },
                    'curve_outlier': {
                        'enabled': qc.custom_algorithms.get('curve_outlier', {}).get('enabled', True),
                        'params': qc.custom_algorithms.get('curve_outlier', {}).get('params', {
                            'threshold': 3.0, 'max_iterations': 5, 'metric': 'mean'
                        })
                    },
                    'cox_fdwra': {
                        'enabled': qc.custom_algorithms.get('cox_fdwra', {}).get('enabled', False),
                        'params': {'n': 2.0, 'max_iterations': 20}
                    }
                }
            }
        
        def _on_progress(self, value: int, message: str):
            """Handle progress updates from thread."""
            self.progress_updated.emit(value, message)
        
        def _on_finished(self, result, windows, data):
            """Handle processing completion."""
            # Validate results
            is_valid, error_msg = self.validate_results(result, windows)
            
            if not is_valid:
                # Emit error but also provide diagnostic info
                self.processing_error.emit(f"QC Failure: {error_msg}")
                self._show_qc_failure_dialog(windows, error_msg)
                return
            
            # Store results
            self._hvsr_result = result
            self._windows = windows
            self._data = data
            
            # Emit success signal
            self.processing_finished.emit(result, windows, data)
        
        def _on_error(self, error_msg: str):
            """Handle processing error."""
            self.processing_error.emit(error_msg)
        
        def validate_results(self, result, windows) -> Tuple[bool, str]:
            """
            Validate HVSR processing results.
            
            Args:
                result: HVSRResult object
                windows: WindowCollection object
            
            Returns:
                Tuple of (is_valid, error_message)
            """
            import numpy as np
            
            # Check 1: Any windows passed QC?
            if windows.n_active == 0:
                return False, f"No windows passed QC (0/{windows.n_windows} rejected)"
            
            # Check 2: Valid frequency data?
            if result is None or len(result.frequencies) == 0:
                return False, "No frequency data generated"
            
            # Check 3: Valid HVSR values?
            if result.mean_hvsr is None:
                return False, "HVSR computation failed - no mean values"
            
            if np.all(np.isnan(result.mean_hvsr)):
                return False, "All HVSR values are NaN"
            
            return True, "OK"
        
        def _show_qc_failure_dialog(self, windows, error_msg: str):
            """Show QC failure dialog with diagnostic information."""
            if self.parent_window is None:
                return
            
            report = self._generate_qc_report(windows)
            
            message = f"<h3>QC Failure: Cannot Process Data</h3>"
            message += f"<p><b>Error:</b> {error_msg}</p>"
            message += f"<hr>"
            message += f"<h4>QC Diagnostic Report:</h4>"
            message += f"<pre>{report}</pre>"
            message += f"<hr>"
            message += f"<h4>Suggested Solutions:</h4>"
            message += f"<ul>"
            message += f"<li>Try using 'Conservative' or 'Balanced' QC preset</li>"
            message += f"<li>Disable QC temporarily to diagnose data issues</li>"
            message += f"<li>Check if data has unusual characteristics</li>"
            message += f"</ul>"
            
            from PyQt5.QtCore import Qt
            msg_box = QMessageBox(self.parent_window)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle("QC Failure")
            msg_box.setTextFormat(Qt.RichText)
            msg_box.setText(message)
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec_()
        
        def _generate_qc_report(self, windows) -> str:
            """Generate diagnostic report for QC failure."""
            total = windows.n_windows
            active = windows.n_active
            rejected = windows.n_rejected
            
            report = f"Total Windows: {total}\n"
            report += f"Passed: {active} ({active/total*100:.1f}%)\n"
            report += f"Failed: {rejected} ({rejected/total*100:.1f}%)\n"
            report += f"\n"
            
            # Analyze rejection reasons
            rejection_reasons = {}
            for window in windows.windows:
                if not window.is_active():
                    reason = window.rejection_reason if window.rejection_reason else "Unknown"
                    rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
            
            if rejection_reasons:
                report += f"Failure Breakdown:\n"
                report += f"{'-' * 40}\n"
                for reason, count in sorted(rejection_reasons.items(), key=lambda x: -x[1]):
                    pct = count / total * 100
                    report += f"{reason}: {count} ({pct:.1f}%)\n"
            
            return report
        
        def recompute_hvsr(self, windows, smoothing: float):
            """
            Recompute HVSR with current window selection.
            
            Args:
                windows: WindowCollection with updated states
                smoothing: Smoothing bandwidth parameter
            
            Returns:
                Updated HVSRResult
            """
            from hvsr_pro.processing import HVSRProcessor
            
            processor = HVSRProcessor(smoothing_bandwidth=smoothing)
            result = processor.process(windows, detect_peaks_flag=True, save_window_spectra=True)
            
            self._hvsr_result = result
            return result
        
        def stop_processing(self):
            """Stop any running processing thread."""
            if self._thread and self._thread.isRunning():
                self._thread.terminate()
                self._thread.wait()
                self._thread = None


else:
    class ProcessingController:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
