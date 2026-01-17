"""
Backward Compatibility Mixin
============================

Contains deprecated property proxies for backward compatibility.
These properties will be removed in a future version.

Migration Guide
---------------
Instead of accessing widgets via main_window properties:
    main_window.window_length_spin.value()
    
Use the ProcessingTab's widgets directly:
    main_window.processing_tab.window_length_spin.value()
    
Or use ProcessingTab's settings methods:
    settings = main_window.processing_tab.get_settings()
"""

import warnings

try:
    from PyQt5.QtWidgets import QMainWindow
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class BackwardCompatMixin:
        """
        Backward compatibility properties for HVSRMainWindow.
        
        These proxy to processing_tab widgets for code that references them directly.
        
        .. deprecated::
            These properties are maintained for backward compatibility only.
            New code should access widgets directly via self.processing_tab:
                main_window.processing_tab.window_length_spin
            Or use the ProcessingTab's settings methods:
                main_window.processing_tab.get_settings()
        
        These properties will be removed in a future version.
        """
        
        @property
        def window_length_spin(self):
            """Backward compatibility: access window length spin via processing_tab."""
            return self.processing_tab.window_length_spin
        
        @property
        def overlap_spin(self):
            """Backward compatibility: access overlap spin via processing_tab."""
            return self.processing_tab.overlap_spin
        
        @property
        def smoothing_spin(self):
            """Backward compatibility: access smoothing spin via processing_tab."""
            return self.processing_tab.smoothing_spin
        
        @property
        def freq_min_spin(self):
            """Backward compatibility: access freq min spin via processing_tab."""
            return self.processing_tab.freq_min_spin
        
        @property
        def freq_max_spin(self):
            """Backward compatibility: access freq max spin via processing_tab."""
            return self.processing_tab.freq_max_spin
        
        @property
        def n_freq_spin(self):
            """Backward compatibility: access n freq spin via processing_tab."""
            return self.processing_tab.n_freq_spin
        
        @property
        def override_sampling_check(self):
            """Backward compatibility: access override sampling check via processing_tab."""
            return self.processing_tab.override_sampling_check
        
        @property
        def sampling_rate_spin(self):
            """Backward compatibility: access sampling rate spin via processing_tab."""
            return self.processing_tab.sampling_rate_spin
        
        @property
        def qc_enable_check(self):
            """Backward compatibility: access QC enable check via processing_tab."""
            return self.processing_tab.qc_enable_check
        
        @property
        def preset_radio(self):
            """Backward compatibility: access preset radio via processing_tab."""
            return self.processing_tab.preset_radio
        
        @property
        def custom_radio(self):
            """Backward compatibility: access custom radio via processing_tab."""
            return self.processing_tab.custom_radio
        
        @property
        def qc_combo(self):
            """Backward compatibility: access QC preset combo via processing_tab."""
            return self.processing_tab.qc_combo
        
        @property
        def cox_fdwra_check(self):
            """Backward compatibility: access Cox enable check via processing_tab."""
            return self.processing_tab.cox_fdwra_check
        
        @property
        def cox_n_spin(self):
            """Backward compatibility: access Cox n spin via processing_tab."""
            return self.processing_tab.cox_n_spin
        
        @property
        def cox_iterations_spin(self):
            """Backward compatibility: access Cox max iterations spin via processing_tab."""
            return self.processing_tab.cox_iterations_spin
        
        @property
        def cox_min_iterations_spin(self):
            """Backward compatibility: access Cox min iterations spin via processing_tab."""
            return self.processing_tab.cox_min_iterations_spin
        
        @property
        def cox_dist_combo(self):
            """Backward compatibility: access Cox distribution combo via processing_tab."""
            return self.processing_tab.cox_dist_combo
        
        @property
        def parallel_check(self):
            """Backward compatibility: access parallel check via processing_tab."""
            return self.processing_tab.parallel_check
        
        @property
        def cores_spin(self):
            """Backward compatibility: access cores spin via processing_tab."""
            return self.processing_tab.cores_spin
        
        @property
        def process_btn(self):
            """Backward compatibility: access process button via processing_tab."""
            return self.processing_tab.process_btn
        
        @property
        def progress_bar(self):
            """Backward compatibility: access progress bar via processing_tab."""
            return self.processing_tab.progress_bar
        
        @property
        def info_text(self):
            """Backward compatibility: access info text via processing_tab."""
            return self.processing_tab.info_text
        
        @property
        def window_info_label(self):
            """Backward compatibility: access window info label via processing_tab."""
            return self.processing_tab.window_info_label
        
        @property
        def reject_all_btn(self):
            """Backward compatibility: access reject all button via processing_tab."""
            return self.processing_tab.reject_all_btn
        
        @property
        def accept_all_btn(self):
            """Backward compatibility: access accept all button via processing_tab."""
            return self.processing_tab.accept_all_btn
        
        @property
        def recompute_btn(self):
            """Backward compatibility: access recompute button via processing_tab."""
            return self.processing_tab.recompute_btn


else:
    class BackwardCompatMixin:
        """Dummy class when PyQt5 not available."""
        pass
