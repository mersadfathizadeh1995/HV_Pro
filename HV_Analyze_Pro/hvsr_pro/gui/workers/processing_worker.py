"""
HVSR Pro Processing Worker
==========================

Background thread for HVSR processing pipeline.
"""

import numpy as np

try:
    from PyQt5.QtCore import QThread, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False
    # Provide dummy classes for when PyQt5 is not available
    class QThread:
        pass
    class pyqtSignal:
        def __init__(self, *args): pass

from hvsr_pro.core import HVSRDataHandler
from hvsr_pro.processing import WindowManager, RejectionEngine, HVSRProcessor
from hvsr_pro.processing.hvsr import HVSRResult


class ProcessingThread(QThread):
    """Background thread for HVSR processing with multi-file support."""
    
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object, object, object)  # result, windows, data
    error = pyqtSignal(str)
    
    def __init__(self, file_input, window_length, overlap, smoothing_bandwidth, 
                 load_mode='single', time_range=None,
                 freq_min=0.2, freq_max=20.0, n_frequencies=100, 
                 qc_mode='balanced', apply_cox_fdwra=False,
                 use_parallel=False, n_cores=None, 
                 manual_sampling_rate=None, custom_qc_settings=None,
                 cox_fdwra_settings=None, smoothing_method='konno_ohmachi',
                 file_format='auto', degrees_from_north=None):
        super().__init__()
        self.file_input = file_input  # Can be str, list, or dict
        self.load_mode = load_mode  # 'single', 'multi_type1', 'multi_type2', 'multi_component'
        self.format = file_format  # File format for multi-component loading
        self.degrees_from_north = degrees_from_north  # Sensor orientation for multi-component
        self.window_length = window_length
        self.overlap = overlap
        self.smoothing_method = smoothing_method  # Smoothing method name
        self.smoothing_bandwidth = smoothing_bandwidth
        self.time_range = time_range  # Optional time range filter
        self.freq_min = freq_min
        self.freq_max = freq_max
        self.n_frequencies = n_frequencies
        self.qc_mode = qc_mode  # QC strictness mode
        self.apply_cox_fdwra = apply_cox_fdwra  # Apply Cox FDWRA after HVSR
        self.use_parallel = use_parallel  # Enable parallel processing
        self.n_cores = n_cores  # Number of cores to use for parallel processing
        self.manual_sampling_rate = manual_sampling_rate  # Optional manual sampling rate override
        self.custom_qc_settings = custom_qc_settings  # Optional custom QC settings
        # Cox FDWRA settings: {'n': float, 'max_iterations': int, 'min_iterations': int, 'distribution': str}
        self.cox_fdwra_settings = cox_fdwra_settings or {}
    
    def run(self):
        """Execute processing pipeline with multi-file support."""
        try:
            # Step 1: Load data
            handler = HVSRDataHandler()
            
            if self.load_mode == 'single':
                self.progress.emit(10, "Loading seismic data...")
                data = handler.load_data(self.file_input)
                
            elif self.load_mode == 'multi_type1':
                self.progress.emit(10, f"Loading {len(self.file_input)} MiniSEED files (Type 1)...")
                data = handler.load_multi_miniseed_type1(self.file_input)
                
            elif self.load_mode == 'multi_type2':
                complete_groups = [g for g in self.file_input.values() 
                                 if 'E' in g and 'N' in g and 'Z' in g]
                self.progress.emit(10, f"Loading {len(complete_groups)} file groups (Type 2)...")
                data = handler.load_multi_miniseed_type2(self.file_input)
            
            elif self.load_mode == 'multi_component':
                # Multi-component file loading (SAC, PEER formats)
                # file_input can be dict {'N': path, 'E': path, 'Z': path} or list of paths
                self.progress.emit(10, "Loading multi-component files...")
                if isinstance(self.file_input, dict):
                    # Extract files in order N, E, Z
                    files = [str(self.file_input.get(c)) for c in ['N', 'E', 'Z'] if c in self.file_input]
                else:
                    files = self.file_input
                
                # Get format and orientation if available
                file_format = getattr(self, 'format', 'auto')
                degrees_from_north = getattr(self, 'degrees_from_north', None)
                
                data = handler.load_multi_component(
                    files,
                    format=file_format,
                    degrees_from_north=degrees_from_north
                )
            
            else:
                raise ValueError(f"Unknown load mode: {self.load_mode}")

            # Step 1.2: Apply manual sampling rate override (if enabled)
            if self.manual_sampling_rate:
                self.progress.emit(12, f"Overriding sampling rate to {self.manual_sampling_rate:.4f} Hz...")
                data.east.sampling_rate = self.manual_sampling_rate
                data.north.sampling_rate = self.manual_sampling_rate
                data.vertical.sampling_rate = self.manual_sampling_rate

            # Step 1.5: Apply time range slicing (if enabled)
            if self.time_range and self.time_range.get('enabled'):
                self.progress.emit(15, "Applying time range filter...")
                
                start_local = self.time_range['start']
                end_local = self.time_range['end']
                tz_offset = self.time_range['timezone_offset']
                tz_name = self.time_range.get('timezone_name', f'UTC{tz_offset:+d}')
                
                self.progress.emit(17, f"Time range: {start_local.strftime('%Y-%m-%d %H:%M')} to {end_local.strftime('%H:%M')} ({tz_name})")
                
                try:
                    # Apply time slicing
                    data = handler.slice_by_time(data, start_local, end_local, tz_offset)
                    
                    duration_hours = data.duration / 3600
                    self.progress.emit(20, f"Sliced to {duration_hours:.2f} hours")
                    
                except ValueError as e:
                    # Time range error - show detailed message
                    raise ValueError(f"Time range error: {str(e)}")
            
            # Step 2: Create windows
            self.progress.emit(30, "Creating windows...")
            manager = WindowManager(
                window_length=self.window_length,
                overlap=self.overlap
            )
            windows = manager.create_windows(data, calculate_quality=True)
            
            # Step 3: Quality control
            engine = RejectionEngine()

            # Check if QC is completely disabled
            if self.custom_qc_settings and not self.custom_qc_settings.get('enabled', True):
                self.progress.emit(50, "Quality control disabled (skipping)...")
                # Skip QC entirely - all windows remain active
            elif self.custom_qc_settings and self.qc_mode == 'custom':
                # Use custom QC settings
                self.progress.emit(50, "Applying quality control (custom settings)...")
                self._apply_custom_qc(engine, self.custom_qc_settings)
                engine.evaluate(windows, auto_apply=True)
            else:
                # Use default pipeline
                self.progress.emit(50, f"Applying quality control ({self.qc_mode} mode)...")
                engine.create_default_pipeline(mode=self.qc_mode)
                engine.evaluate(windows, auto_apply=True)
            
            # Log QC results
            self.progress.emit(60, f"QC: {windows.n_active}/{windows.n_windows} windows active ({windows.acceptance_rate*100:.1f}%)")
            
            # Check if NO windows passed QC
            if windows.n_active == 0:
                self.progress.emit(65, f"ERROR: No windows passed QC (0/{windows.n_windows})")
                
                # Create a dummy result with valid but empty data to prevent crash
                # Create frequency array
                frequencies = np.logspace(np.log10(self.freq_min), np.log10(self.freq_max), self.n_frequencies)
                
                # Create dummy HVSR values (all ones to avoid division issues)
                dummy_hvsr = np.ones_like(frequencies)
                
                result = HVSRResult(
                    frequencies=frequencies,
                    mean_hvsr=dummy_hvsr,
                    median_hvsr=dummy_hvsr,
                    std_hvsr=np.zeros_like(frequencies),
                    percentile_16=dummy_hvsr * 0.9,
                    percentile_84=dummy_hvsr * 1.1,
                    window_spectra=[],
                    peaks=[],
                    total_windows=windows.n_windows,
                    valid_windows=0,
                    metadata={'qc_failure': True, 'message': 'No windows passed QC'}
                )
                
                # Emit error but continue to show the empty result
                self.error.emit("No windows passed QC. Please adjust QC settings or check data quality.")
                self.finished.emit(result, windows, data)
                return
            
            # If too many rejected, warn but continue
            if windows.n_active < 10 and windows.n_windows > 50:
                self.progress.emit(65, f"WARNING: Only {windows.n_active} windows passed QC. Consider relaxing quality settings.")
            
            # Step 4: Compute HVSR
            if self.use_parallel:
                cores_msg = f" using {self.n_cores} cores" if self.n_cores else ""
                self.progress.emit(70, f"Computing HVSR (parallel processing{cores_msg})...")
            else:
                self.progress.emit(70, "Computing HVSR...")

            # Note: n_cores is stored for future use when HVSRProcessor supports it
            # Currently, parallel processing uses all available cores
            processor = HVSRProcessor(
                smoothing_method=self.smoothing_method,
                smoothing_bandwidth=self.smoothing_bandwidth,
                f_min=self.freq_min,
                f_max=self.freq_max,
                n_frequencies=self.n_frequencies,
                parallel=self.use_parallel
            )
            result = processor.process(windows, detect_peaks_flag=True, save_window_spectra=True)
            
            # Step 5: Apply Cox FDWRA (if enabled or SESAME mode)
            if self.apply_cox_fdwra or self.qc_mode == 'sesame':
                self.progress.emit(85, "Applying Cox FDWRA (peak consistency)...")
                
                # Store raw spectra BEFORE Cox FDWRA rejection (for comparison plot)
                raw_window_spectra = list(result.window_spectra)  # Copy before modification
                
                # Get Cox FDWRA settings (with defaults)
                cox_n = self.cox_fdwra_settings.get('n', 2.0)
                cox_max_iter = self.cox_fdwra_settings.get('max_iterations', 50)
                cox_min_iter = self.cox_fdwra_settings.get('min_iterations', 1)
                cox_dist = self.cox_fdwra_settings.get('distribution', 'lognormal')
                
                fdwra_result = engine.evaluate_fdwra(
                    windows,
                    result,
                    n=cox_n,
                    max_iterations=cox_max_iter,
                    min_iterations=cox_min_iter,
                    distribution_fn=cox_dist,
                    distribution_mc=cox_dist,
                    search_range_hz=(self.freq_min, self.freq_max),
                    auto_apply=True
                )
                
                n_rejected = fdwra_result['n_rejected']
                converged = fdwra_result['converged']
                iterations = fdwra_result['iterations']
                
                self.progress.emit(90, f"Cox FDWRA: {n_rejected} windows rejected, converged in {iterations} iterations")
                
                # Recompute HVSR with updated window states
                if n_rejected > 0:
                    # Check if Cox FDWRA rejected ALL windows
                    if windows.n_active == 0:
                        self.progress.emit(92, f"ERROR: Cox FDWRA rejected all windows")
                        
                        # Create dummy result like before
                        frequencies = np.logspace(np.log10(self.freq_min), np.log10(self.freq_max), self.n_frequencies)
                        dummy_hvsr = np.ones_like(frequencies)
                        
                        result = HVSRResult(
                            frequencies=frequencies,
                            mean_hvsr=dummy_hvsr,
                            median_hvsr=dummy_hvsr,
                            std_hvsr=np.zeros_like(frequencies),
                            percentile_16=dummy_hvsr * 0.9,
                            percentile_84=dummy_hvsr * 1.1,
                            window_spectra=[],
                            peaks=[],
                            total_windows=windows.n_windows,
                            valid_windows=0,
                            metadata={'qc_failure': True, 'message': 'Cox FDWRA rejected all windows'}
                        )
                        
                        self.error.emit("Cox FDWRA rejected all windows. Please disable Cox FDWRA or adjust settings.")
                        self.finished.emit(result, windows, data)
                        return
                    else:
                        self.progress.emit(92, "Recomputing HVSR after Cox FDWRA...")
                        result = processor.process(windows, detect_peaks_flag=True, save_window_spectra=True)
                        
                        # Store raw spectra in result metadata for comparison plot
                        result.metadata['raw_window_spectra'] = raw_window_spectra
                else:
                    # No rejection, raw and final are the same
                    result.metadata['raw_window_spectra'] = raw_window_spectra
            
            self.progress.emit(100, "Complete!")
            self.finished.emit(result, windows, data)
            
        except Exception as e:
            import traceback
            error_detail = f"{str(e)}\n\nTraceback:\n{traceback.format_exc()}"
            self.error.emit(error_detail)

    def _apply_custom_qc(self, engine, settings):
        """Apply custom QC settings to rejection engine."""
        from hvsr_pro.processing.rejection import QualityThresholdRejection, StatisticalOutlierRejection
        from hvsr_pro.processing.rejection import STALTARejection, FrequencyDomainRejection, AmplitudeRejection

        algorithms = settings.get('algorithms', {})

        # Add algorithms based on settings
        if algorithms.get('amplitude', {}).get('enabled', False):
            engine.add_algorithm(AmplitudeRejection())

        if algorithms.get('quality_threshold', {}).get('enabled', False):
            threshold = algorithms['quality_threshold']['params'].get('threshold', 0.5)
            engine.add_algorithm(QualityThresholdRejection(threshold=threshold))

        if algorithms.get('sta_lta', {}).get('enabled', False):
            params = algorithms['sta_lta']['params']
            engine.add_algorithm(STALTARejection(
                sta_length=params.get('sta_length', 1.0),
                lta_length=params.get('lta_length', 30.0),
                min_ratio=params.get('min_ratio', 0.15),
                max_ratio=params.get('max_ratio', 2.5)
            ))

        if algorithms.get('frequency_domain', {}).get('enabled', False):
            spike_threshold = algorithms['frequency_domain']['params'].get('spike_threshold', 3.0)
            engine.add_algorithm(FrequencyDomainRejection(spike_threshold=spike_threshold))

        if algorithms.get('statistical_outlier', {}).get('enabled', False):
            threshold = algorithms['statistical_outlier']['params'].get('threshold', 2.0)
            engine.add_algorithm(StatisticalOutlierRejection(method='iqr', threshold=threshold))

