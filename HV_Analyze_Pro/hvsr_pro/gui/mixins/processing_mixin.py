"""
Processing Mixin
================

Mixin providing HVSR processing functionality for the main window.
"""

import numpy as np
from typing import Optional, Tuple

try:
    from PyQt5.QtWidgets import QMessageBox
    from PyQt5.QtCore import Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


class ProcessingMixin:
    """
    Mixin providing HVSR processing functionality.
    
    This mixin should be used with HVSRMainWindow and provides:
    - process_hvsr(): Start processing in background thread
    - on_progress(): Update progress bar
    - on_processing_finished(): Handle processing completion
    - on_processing_error(): Handle errors
    - recompute_hvsr(): Recompute with current windows
    - _validate_processing_results(): Validate results
    - _show_qc_failure_dialog(): Show QC failure details
    - _generate_qc_diagnostic_report(): Generate diagnostic info
    - update_window_info(): Update window statistics display
    
    Expected attributes on the main class:
    - current_file: str or Path
    - hvsr_result: HVSRResult
    - windows: WindowCollection
    - data: SeismicData
    - progress_bar: QProgressBar
    - process_btn: QPushButton
    - status_bar: QStatusBar
    - canvas: InteractiveHVSRCanvas
    - layers_dock: WindowLayersDock
    - peak_picker_dock: PeakPickerDock
    - export_dock: ExportDock
    - plot_manager: PlotWindowManager
    - various spin boxes and checkboxes for settings
    """
    
    def process_hvsr(self):
        """Start HVSR processing in background thread."""
        if not self.current_file:
            QMessageBox.warning(self, "No File", "Please load a data file first.")
            return
        
        # Disable controls
        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Get settings from panel or direct widgets
        settings = self._get_processing_settings()
        
        # Validate frequency range
        if settings['f_min'] >= settings['f_max']:
            QMessageBox.warning(
                self, "Invalid Range",
                "Minimum frequency must be less than maximum frequency."
            )
            self.process_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            return
        
        # Log settings
        self._log_processing_settings(settings)
        
        # Get QC settings
        qc_settings = self._get_qc_settings_for_processing()
        
        # Import ProcessingThread
        from hvsr_pro.gui.workers import ProcessingThread
        
        # Get Cox FDWRA specific settings
        cox_fdwra_settings = qc_settings.get('cox_fdwra', {})
        
        # Start processing thread
        self.thread = ProcessingThread(
            self.current_file,
            settings['window_length'],
            settings['overlap'],
            settings['smoothing_bandwidth'],
            self.load_mode,
            self.current_time_range,
            settings['f_min'],
            settings['f_max'],
            settings['n_frequencies'],
            qc_settings['qc_mode'],
            qc_settings['apply_cox_fdwra'],
            settings['parallel'],
            settings['n_workers'],
            settings['sampling_rate'],
            qc_settings['custom_settings'],
            cox_fdwra_settings
        )
        self.thread.progress.connect(self.on_progress)
        self.thread.finished.connect(self.on_processing_finished)
        self.thread.error.connect(self.on_processing_error)
        self.thread.start()
    
    def _get_processing_settings(self) -> dict:
        """Get processing settings from UI widgets."""
        # Check if using new panel or legacy widgets
        if hasattr(self, 'settings_panel') and self.settings_panel:
            return self.settings_panel.get_settings()
        
        # Legacy: read from individual widgets
        use_parallel = self.parallel_check.isChecked()
        return {
            'window_length': self.window_length_spin.value(),
            'overlap': self.overlap_spin.value() / 100.0,
            'smoothing_bandwidth': self.smoothing_spin.value(),
            'f_min': self.freq_min_spin.value(),
            'f_max': self.freq_max_spin.value(),
            'n_frequencies': self.n_freq_spin.value(),
            'override_sampling': self.override_sampling_check.isChecked(),
            'sampling_rate': self.sampling_rate_spin.value() if self.override_sampling_check.isChecked() else None,
            'parallel': use_parallel,
            'n_workers': self.cores_spin.value() if use_parallel else 1,
        }
    
    def _get_qc_settings_for_processing(self) -> dict:
        """Get QC settings for processing."""
        # Check if using new QC panel or legacy widgets
        if hasattr(self, 'qc_panel') and self.qc_panel:
            qc_settings = self.qc_panel.get_qc_settings()
            if qc_settings['mode'] == 'preset':
                return {
                    'qc_mode': qc_settings['preset'],
                    'apply_cox_fdwra': qc_settings['cox_fdwra']['enabled'],
                    'custom_settings': None
                }
            else:
                return {
                    'qc_mode': 'custom',
                    'apply_cox_fdwra': qc_settings['cox_fdwra']['enabled'],
                    'custom_settings': qc_settings
                }
        
        # Legacy: read from individual widgets
        if self.preset_radio.isChecked():
            qc_mode = self.qc_combo.currentData()
            custom_settings = None
        else:
            qc_mode = 'custom'
            custom_settings = self._get_custom_qc_settings_from_ui()
        
        apply_cox = self.cox_fdwra_check.isChecked()
        
        # Combine with stored custom settings if needed
        final_custom = custom_settings if custom_settings else self.custom_qc_settings
        
        return {
            'qc_mode': qc_mode,
            'apply_cox_fdwra': apply_cox,
            'custom_settings': final_custom
        }
    
    def _log_processing_settings(self, settings: dict):
        """Log processing settings to info panel."""
        self.add_info(
            f"Frequency range: {settings['f_min']:.2f} - {settings['f_max']:.1f} Hz "
            f"({settings['n_frequencies']} points)"
        )
        
        if settings.get('sampling_rate'):
            self.add_info(f"Sampling rate: {settings['sampling_rate']:.4f} Hz (manual override)")
        
        # Log QC mode
        if hasattr(self, 'qc_panel') and self.qc_panel:
            if self.qc_panel.is_preset_mode():
                self.add_info(f"QC Mode: {self.qc_panel.get_preset()}")
            else:
                self.add_info("QC Mode: Custom (manual settings)")
        elif hasattr(self, 'preset_radio'):
            if self.preset_radio.isChecked():
                self.add_info(f"QC Mode: {self.qc_combo.currentText()}")
            else:
                self.add_info("QC Mode: Custom (manual settings)")
        
        # Log Cox FDWRA
        qc = self._get_qc_settings_for_processing()
        if qc['apply_cox_fdwra'] or qc['qc_mode'] in ('sesame', 'publication'):
            self.add_info("Cox FDWRA: Enabled (peak frequency consistency)")
        
        # Log parallel processing
        if settings.get('parallel'):
            cpu_count = self._get_cpu_count() if hasattr(self, '_get_cpu_count') else 4
            self.add_info(
                f"Parallel processing: Enabled (using {settings['n_workers']} of {cpu_count} cores)"
            )
    
    def on_progress(self, value: int, message: str):
        """Update progress bar."""
        self.progress_bar.setValue(value)
        self.status_bar.showMessage(message)
        self.add_info(message)
    
    def on_processing_finished(self, result, windows, data):
        """Handle processing completion."""
        # Validate results before using
        is_valid, error_msg = self._validate_processing_results(result, windows)
        
        if not is_valid:
            self._show_qc_failure_dialog(windows, error_msg)
            self.progress_bar.setVisible(False)
            self.process_btn.setEnabled(True)
            return
        
        # Store results
        self.hvsr_result = result
        self.windows = windows
        self.data = data
        
        # Update UI
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        
        # Enable action buttons
        self._enable_action_buttons()
        
        # Update window info
        self.update_window_info()
        
        # Update canvas
        if hasattr(self, 'canvas'):
            self.canvas.set_data(result, windows, data)
        
        # Update docks
        self._update_docks_after_processing(result, windows, data)
        
        # Plot in separate window
        if hasattr(self, 'plot_results_separate_window'):
            self.plot_results_separate_window(result, windows, data)
        
        # Log completion
        self.add_info("Processing complete!")
        self.add_info(f"   Windows: {windows.n_active}/{windows.n_windows}")
        if result.primary_peak:
            self.add_info(f"   Primary peak: f0 = {result.primary_peak.frequency:.2f} Hz")
        
        self.status_bar.showMessage("Ready - Use layer dock to toggle visibility")
    
    def _enable_action_buttons(self):
        """Enable action buttons after successful processing."""
        for btn_name in ['export_plot_btn', 'report_btn', 'export_btn', 'save_btn']:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setEnabled(True)
        
        if hasattr(self, 'reject_all_btn'):
            self.reject_all_btn.setEnabled(True)
        if hasattr(self, 'accept_all_btn'):
            self.accept_all_btn.setEnabled(True)
        if hasattr(self, 'recompute_btn'):
            self.recompute_btn.setEnabled(True)
    
    def _update_docks_after_processing(self, result, windows, data):
        """Update dock widgets after processing."""
        # Layers dock
        if hasattr(self, 'layers_dock'):
            self.layers_dock.set_references(self.plot_manager, windows)
        
        # Peak picker dock
        if hasattr(self, 'peak_picker_dock'):
            self.peak_picker_dock.set_hvsr_data(result, result.frequencies, result.mean_hvsr)
        
        # Export dock
        if hasattr(self, 'export_dock'):
            self.export_dock.set_references(result, windows, self.plot_manager, data)
        
        # Processing data panel
        if hasattr(self, 'processing_data_panel') and hasattr(self, 'data_load_tab'):
            self.processing_data_panel.update_from_data_load_tab(self.data_load_tab)
        
        # Azimuthal tab
        if hasattr(self, 'azimuthal_tab'):
            self.azimuthal_tab.set_windows(windows, data)
            if hasattr(self.azimuthal_tab, 'data_panel') and hasattr(self, 'data_load_tab'):
                self.azimuthal_tab.data_panel.update_from_data_load_tab(self.data_load_tab)
    
    def on_processing_error(self, error_msg: str):
        """Handle processing error."""
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        QMessageBox.critical(self, "Processing Error", error_msg)
        self.add_info(f"ERROR: {error_msg}")
    
    def recompute_hvsr(self):
        """Recompute HVSR with current window selection."""
        if self.windows is None:
            return
        
        self.add_info("Recomputing HVSR...")
        self.status_bar.showMessage("Recomputing HVSR...")
        
        try:
            from hvsr_pro.processing import HVSRProcessor
            
            # Get smoothing value
            if hasattr(self, 'settings_panel') and self.settings_panel:
                smoothing = self.settings_panel.get_smoothing_bandwidth()
            else:
                smoothing = self.smoothing_spin.value()
            
            # Recompute
            processor = HVSRProcessor(smoothing_bandwidth=smoothing)
            self.hvsr_result = processor.process(
                self.windows,
                detect_peaks_flag=True,
                save_window_spectra=True
            )
            
            # Update canvas
            if hasattr(self, 'canvas'):
                self.canvas.set_data(self.hvsr_result, self.windows, self.data)
            
            self.add_info("HVSR recomputed!")
            if self.hvsr_result.primary_peak:
                self.add_info(
                    f"   Primary peak: f0 = {self.hvsr_result.primary_peak.frequency:.2f} Hz"
                )
            
            self.status_bar.showMessage("HVSR recomputed successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to recompute HVSR: {str(e)}")
            self.add_info(f"ERROR - Recompute: {str(e)}")
    
    def update_window_info(self):
        """Update window information display."""
        if self.windows is None:
            if hasattr(self, 'window_info_label'):
                self.window_info_label.setText("No windows")
            return
        
        info = (
            f"Total: {self.windows.n_windows}\n"
            f"Active: {self.windows.n_active} "
            f"({self.windows.acceptance_rate*100:.1f}%)\n"
            f"Rejected: {self.windows.n_rejected}"
        )
        
        if hasattr(self, 'window_info_label'):
            self.window_info_label.setText(info)
    
    def _validate_processing_results(self, result, windows) -> Tuple[bool, str]:
        """
        Validate HVSR processing results before plotting.
        
        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
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
        """
        Show detailed QC failure dialog with diagnostic information.
        """
        report = self._generate_qc_diagnostic_report(windows)
        
        message = "<h3>QC Failure: Cannot Process Data</h3>"
        message += f"<p><b>Error:</b> {error_msg}</p>"
        message += "<hr>"
        message += "<h4>QC Diagnostic Report:</h4>"
        message += f"<pre>{report}</pre>"
        message += "<hr>"
        message += "<h4>Suggested Solutions:</h4>"
        message += "<ul>"
        message += "<li>Open <b>Advanced QC Settings</b> and:"
        message += "<ul>"
        message += "<li>UNCHECK 'Enable Quality Control' to bypass QC entirely</li>"
        message += "<li>OR adjust individual algorithm thresholds</li>"
        message += "</ul></li>"
        message += "<li>Check your input data quality</li>"
        message += "<li>Try different QC modes (Conservative, Balanced, Aggressive)</li>"
        message += "<li>Verify sampling rate is correct</li>"
        message += "</ul>"
        
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("QC Failure")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
        
        # Log to info panel
        self.add_info("=" * 60)
        self.add_info("QC FAILURE - No windows passed quality control")
        self.add_info("=" * 60)
        self.add_info(report)
        self.add_info("=" * 60)
    
    def _generate_qc_diagnostic_report(self, windows) -> str:
        """Generate diagnostic report showing why windows failed QC."""
        total = windows.n_windows
        active = windows.n_active
        rejected = windows.n_rejected
        
        report = f"Total Windows: {total}\n"
        report += f"Passed: {active} ({active/total*100:.1f}%)\n"
        report += f"Failed: {rejected} ({rejected/total*100:.1f}%)\n\n"
        
        # Analyze rejection reasons
        rejection_reasons = {}
        for window in windows.windows:
            if not window.is_active():
                reason = window.rejection_reason if window.rejection_reason else "Unknown"
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1
        
        if rejection_reasons:
            report += "Failure Breakdown:\n"
            report += "-" * 40 + "\n"
            for reason, count in sorted(rejection_reasons.items(), key=lambda x: -x[1]):
                pct = count / total * 100
                report += f"{reason}: {count} ({pct:.1f}%)\n"
        else:
            report += "No rejection reason data available\n"
        
        report += "\nRecommendations:\n"
        if rejected == total:
            report += "  - ALL windows failed - QC may be too strict\n"
            report += "  - Consider disabling QC entirely for diagnosis\n"
            report += "  - Check if data has unusual characteristics\n"
        elif rejected > total * 0.9:
            report += "  - >90% rejection rate - QC very strict\n"
            report += "  - Try relaxing QC thresholds\n"
            report += "  - Review individual algorithm settings\n"
        
        report += "  - Use Advanced QC Settings to customize\n"
        report += "  - Verify data quality and sensor response\n"
        
        return report

