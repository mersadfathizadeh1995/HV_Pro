"""
HVSR Pro Processing Worker
==========================

Background thread for HVSR processing pipeline.
Delegates to ``hvsr_pro.api.HVSRAnalysis`` for the actual computation.
"""

import traceback

try:
    from PyQt5.QtCore import QThread, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False
    class QThread:
        pass
    class pyqtSignal:
        def __init__(self, *args): pass

from hvsr_pro.core import HVSRDataHandler


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
                 file_format='auto', degrees_from_north=None,
                 qc_enabled=True, phase1_enabled=True, phase2_enabled=True,
                 horizontal_method='geometric_mean'):
        super().__init__()
        self.file_input = file_input
        self.load_mode = load_mode
        self.format = file_format
        self.degrees_from_north = degrees_from_north
        self.window_length = window_length
        self.overlap = overlap
        self.smoothing_method = smoothing_method
        self.smoothing_bandwidth = smoothing_bandwidth
        self.horizontal_method = horizontal_method
        self.time_range = time_range
        self.freq_min = freq_min
        self.freq_max = freq_max
        self.n_frequencies = n_frequencies
        self.qc_mode = qc_mode
        self.apply_cox_fdwra = apply_cox_fdwra
        self.use_parallel = use_parallel
        self.n_cores = n_cores
        self.manual_sampling_rate = manual_sampling_rate
        self.custom_qc_settings = custom_qc_settings
        self.cox_fdwra_settings = cox_fdwra_settings or {}
        self.qc_enabled = qc_enabled
        self.phase1_enabled = phase1_enabled
        self.phase2_enabled = phase2_enabled

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def run(self):
        """Execute the processing pipeline via the headless API."""
        try:
            config = self._build_config()
            analysis = self._build_analysis(config)
            result = analysis.process(
                progress_callback=lambda pct, msg: self.progress.emit(pct, msg),
            )

            if result.qc_summary.errors:
                self.error.emit(result.qc_summary.errors[0])

            self.finished.emit(result.hvsr_result, result.windows, result.data)

        except Exception as exc:
            detail = f"{exc}\n\nTraceback:\n{traceback.format_exc()}"
            self.error.emit(detail)

    # ------------------------------------------------------------------
    # config bridge
    # ------------------------------------------------------------------

    def _build_config(self):
        """Map legacy thread attributes into ``HVSRAnalysisConfig``."""
        from hvsr_pro.api.config import (
            HVSRAnalysisConfig,
            ProcessingConfig,
            DataLoadConfig,
            TimeRangeConfig,
            QCConfig,
            CoxFDWRAConfig,
            AmplitudeAlgoConfig,
            QualityThresholdAlgoConfig,
            STALTAAlgoConfig,
            FrequencyDomainAlgoConfig,
            StatisticalOutlierAlgoConfig,
            HVSRAmplitudeAlgoConfig,
            FlatPeakAlgoConfig,
            CurveOutlierAlgoConfig,
        )

        processing = ProcessingConfig(
            window_length=self.window_length,
            overlap=self.overlap,
            smoothing_method=self.smoothing_method,
            smoothing_bandwidth=self.smoothing_bandwidth,
            horizontal_method=self.horizontal_method,
            freq_min=self.freq_min,
            freq_max=self.freq_max,
            n_frequencies=self.n_frequencies,
            manual_sampling_rate=self.manual_sampling_rate,
            use_parallel=self.use_parallel,
            n_cores=self.n_cores,
        )

        data_load = DataLoadConfig(
            load_mode=self.load_mode,
            file_format=self.format,
            degrees_from_north=self.degrees_from_north,
        )

        time_range = TimeRangeConfig()
        if self.time_range and self.time_range.get('enabled'):
            time_range.enabled = True
            s = self.time_range.get('start')
            e = self.time_range.get('end')
            time_range.start = s.isoformat() if hasattr(s, 'isoformat') else str(s) if s else None
            time_range.end = e.isoformat() if hasattr(e, 'isoformat') else str(e) if e else None
            time_range.timezone_offset = int(self.time_range.get('timezone_offset', 0))
            time_range.timezone_name = self.time_range.get('timezone_name')

        qc = self._build_qc_config()

        return HVSRAnalysisConfig(
            processing=processing,
            data_load=data_load,
            time_range=time_range,
            qc=qc,
        )

    def _build_qc_config(self):
        """Translate the legacy QC flags + custom_qc_settings dict into ``QCConfig``."""
        from hvsr_pro.api.config import (
            QCConfig,
            CoxFDWRAConfig,
            AmplitudeAlgoConfig,
            QualityThresholdAlgoConfig,
            STALTAAlgoConfig,
            FrequencyDomainAlgoConfig,
            StatisticalOutlierAlgoConfig,
            HVSRAmplitudeAlgoConfig,
            FlatPeakAlgoConfig,
            CurveOutlierAlgoConfig,
        )

        qc = QCConfig(
            enabled=self.qc_enabled,
            mode=self.qc_mode if self.qc_mode in ('sesame', 'custom') else 'sesame',
            phase1_enabled=self.phase1_enabled,
            phase2_enabled=self.phase2_enabled,
        )

        # Cox FDWRA
        cox_settings = self.cox_fdwra_settings or {}
        cox_enabled = self.apply_cox_fdwra or self.qc_mode == 'sesame'
        if self.custom_qc_settings:
            fdwra_s = self.custom_qc_settings.get('algorithms', {}).get('fdwra', {})
            cox_enabled = cox_enabled or fdwra_s.get('enabled', False)

        qc.cox_fdwra = CoxFDWRAConfig(
            enabled=cox_enabled,
            n=cox_settings.get('n', 2.0),
            max_iterations=cox_settings.get('max_iterations', 50),
            min_iterations=cox_settings.get('min_iterations', 1),
            distribution=cox_settings.get('distribution', 'lognormal'),
        )

        # Populate per-algorithm settings from the custom_qc_settings dict
        if self.custom_qc_settings and self.qc_mode == 'custom':
            algos = self.custom_qc_settings.get('algorithms', {})

            a = algos.get('amplitude', {})
            ap = a.get('params', {})
            qc.amplitude = AmplitudeAlgoConfig(
                enabled=a.get('enabled', False),
                max_amplitude=ap.get('max_amplitude'),
                min_rms=ap.get('min_rms', 1e-10),
                clipping_threshold=ap.get('clipping_threshold', 0.95),
            )

            qt = algos.get('quality_threshold', {})
            qtp = qt.get('params', {})
            qc.quality_threshold = QualityThresholdAlgoConfig(
                enabled=qt.get('enabled', False),
                threshold=qtp.get('threshold', 0.5),
            )

            sl = algos.get('sta_lta', {})
            slp = sl.get('params', {})
            qc.sta_lta = STALTAAlgoConfig(
                enabled=sl.get('enabled', False),
                sta_length=slp.get('sta_length', 1.0),
                lta_length=slp.get('lta_length', 30.0),
                min_ratio=slp.get('min_ratio', 0.2),
                max_ratio=slp.get('max_ratio', 2.5),
            )

            fd = algos.get('frequency_domain', algos.get('spectral_spike', {}))
            fdp = fd.get('params', {})
            qc.frequency_domain = FrequencyDomainAlgoConfig(
                enabled=fd.get('enabled', False),
                spike_threshold=fdp.get('spike_threshold', 3.0),
            )

            so = algos.get('statistical_outlier', {})
            sop = so.get('params', {})
            qc.statistical_outlier = StatisticalOutlierAlgoConfig(
                enabled=so.get('enabled', False),
                method=sop.get('method', 'iqr'),
                threshold=sop.get('threshold', 2.0),
            )

            ha = algos.get('hvsr_amplitude', {})
            hap = ha.get('params', {})
            qc.hvsr_amplitude = HVSRAmplitudeAlgoConfig(
                enabled=ha.get('enabled', False),
                min_amplitude=hap.get('min_amplitude', 1.0),
            )

            fp = algos.get('flat_peak', {})
            fpp = fp.get('params', {})
            qc.flat_peak = FlatPeakAlgoConfig(
                enabled=fp.get('enabled', False),
                flatness_threshold=fpp.get('flatness_threshold', 0.15),
            )

            co = algos.get('curve_outlier', {})
            cop = co.get('params', {})
            qc.curve_outlier = CurveOutlierAlgoConfig(
                enabled=co.get('enabled', True),
                threshold=cop.get('threshold', 3.0),
                max_iterations=cop.get('max_iterations', 5),
                metric=cop.get('metric', 'mean'),
            )
        else:
            # SESAME mode defaults: curve_outlier enabled, others at their defaults
            qc.curve_outlier = CurveOutlierAlgoConfig(enabled=True)

        return qc

    def _build_analysis(self, config):
        """Create the ``HVSRAnalysis`` and load data from ``self.file_input``."""
        from hvsr_pro.api.analysis import HVSRAnalysis

        analysis = HVSRAnalysis(config)
        handler = HVSRDataHandler()
        dl = config.data_load

        if dl.load_mode == 'single':
            analysis._data = handler.load_data(self.file_input)
        elif dl.load_mode == 'multi_type1':
            analysis._data = handler.load_multi_miniseed_type1(self.file_input)
        elif dl.load_mode == 'multi_type2':
            analysis._data = handler.load_multi_miniseed_type2(self.file_input)
        elif dl.load_mode == 'multi_component':
            fi = self.file_input
            if isinstance(fi, dict):
                files = [str(fi.get(c)) for c in ('N', 'E', 'Z') if c in fi]
            else:
                files = fi
            analysis._data = handler.load_multi_component(
                files,
                format=dl.file_format,
                degrees_from_north=dl.degrees_from_north,
            )
        else:
            raise ValueError(f"Unknown load mode: {dl.load_mode}")

        return analysis
