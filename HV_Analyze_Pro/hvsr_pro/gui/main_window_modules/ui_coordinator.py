"""
UI Update Coordinator
=====================

Consolidates UI update logic shared between on_processing_finished() 
and restore_session_gui() methods.

This coordinator handles the common workflow of updating all UI components
when new HVSR processing results are available.
"""

from typing import Optional, Dict, Any, Tuple

try:
    from PyQt5.QtCore import QObject, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class UIUpdateCoordinator(QObject):
        """
        Coordinates UI updates after processing or session restore.
        
        This class consolidates the shared logic between:
        - on_processing_finished(): Called after HVSR processing completes
        - restore_session_gui(): Called after loading a saved session
        
        Both workflows need to update the same UI components with new data.
        
        Signals:
            update_started: Emitted when update begins
            update_completed: Emitted when all updates finish
            update_error: Emitted with error message on failure
            info_message: Emitted with status messages for logging
        """
        
        update_started = pyqtSignal()
        update_completed = pyqtSignal()
        update_error = pyqtSignal(str)
        info_message = pyqtSignal(str)
        
        def __init__(self, parent=None):
            """
            Initialize coordinator.
            
            Args:
                parent: Parent main window (HVSRMainWindow)
            """
            super().__init__(parent)
            self.parent = parent
        
        def update_after_processing(
            self,
            result,
            windows,
            data,
            show_info: bool = True
        ) -> bool:
            """
            Update all UI components after HVSR processing completes.
            
            This is the main entry point for post-processing UI updates.
            
            Args:
                result: HVSRResult object
                windows: WindowCollection object
                data: SeismicData object
                show_info: Whether to emit info messages
            
            Returns:
                True if successful, False otherwise
            """
            self.update_started.emit()
            
            try:
                # 1. Store data in main window
                self._store_data(result, windows, data)
                
                # 2. Update UI state (progress bar, buttons)
                self._reset_processing_state()
                
                # 3. Update all docks and components
                self._update_all_docks(result, windows, data, show_info)
                
                # 4. Update data panels
                self._update_data_panels()
                
                # 5. Enable action buttons
                self._enable_post_processing_controls()
                
                # 6. Update window info display
                self._update_window_info()
                
                # 7. Plot results
                self._plot_results(result, windows, data)
                
                # 8. Show completion info
                if show_info:
                    self._emit_completion_info(result, windows)
                
                self.update_completed.emit()
                return True
                
            except Exception as e:
                self.update_error.emit(f"UI update failed: {str(e)}")
                return False
        
        def update_after_session_restore(
            self,
            hvsr_result,
            windows,
            seismic_data
        ) -> bool:
            """
            Update UI components after loading a saved session.
            
            Similar to update_after_processing but with additional
            error handling and logging for restore operations.
            
            Args:
                hvsr_result: HVSRResult object (can be None)
                windows: WindowCollection object (can be None)
                seismic_data: SeismicData object (can be None)
            
            Returns:
                True if successful, False otherwise
            """
            self.update_started.emit()
            
            try:
                # Log data availability
                self.info_message.emit(
                    f"Session data: HVSR={'Yes' if hvsr_result else 'No'}, "
                    f"Windows={'Yes' if windows else 'No'}, "
                    f"SeismicData={'Yes' if seismic_data else 'No'}"
                )
                
                # 1. Store data in main window
                self._store_data(hvsr_result, windows, seismic_data)
                
                # 2. Update all docks (with extra error handling)
                self._update_all_docks_safe(hvsr_result, windows, seismic_data)
                
                # 3. Update data panels
                self._update_data_panels()
                
                # 4. Enable buttons
                self._enable_post_processing_controls()
                
                # 5. Update window info
                self._update_window_info()
                
                # 6. Plot results (if we have data)
                if hvsr_result is not None and windows is not None:
                    try:
                        self._plot_results(hvsr_result, windows, seismic_data)
                    except Exception as e:
                        self.info_message.emit(f"Warning: Could not open plot window: {str(e)}")
                
                # 7. Switch to Processing tab
                if hasattr(self.parent, 'mode_tabs'):
                    self.parent.mode_tabs.setCurrentIndex(1)
                
                # 8. Update status bar
                if hasattr(self.parent, 'status_bar'):
                    self.parent.status_bar.showMessage(
                        "Session restored - Use layer dock to toggle visibility"
                    )
                
                self.update_completed.emit()
                return True
                
            except Exception as e:
                self.update_error.emit(f"Session restore failed: {str(e)}")
                return False
        
        def _store_data(self, result, windows, data):
            """Store data in main window instance variables."""
            self.parent.hvsr_result = result
            self.parent.windows = windows
            self.parent.data = data
            
            # Update WindowController with windows reference
            if windows is not None and hasattr(self.parent, 'window_ctrl'):
                self.parent.window_ctrl.set_windows(windows)
        
        def _reset_processing_state(self):
            """Reset processing UI state (progress bar, enable controls)."""
            if hasattr(self.parent, 'processing_tab'):
                self.parent.processing_tab.set_progress(0, visible=False)
                self.parent.processing_tab.set_processing_enabled(True)
                self.parent.processing_tab.set_window_buttons_enabled(True)
        
        def _update_all_docks(self, result, windows, data, emit_info: bool = True):
            """Update all dock widgets with new data."""
            # Update canvas (old method - keep for compatibility)
            if hasattr(self.parent, 'canvas'):
                self.parent.canvas.set_data(result, windows, data)
            
            # Update layers dock with windows reference
            if hasattr(self.parent, 'layers_dock') and hasattr(self.parent, 'plot_manager'):
                self.parent.layers_dock.set_references(self.parent.plot_manager, windows)
            
            # Update peak picker dock with HVSR data
            if hasattr(self.parent, 'peak_picker_dock') and result is not None:
                self.parent.peak_picker_dock.set_hvsr_data(
                    result, result.frequencies, result.mean_hvsr
                )
            
            # Update export dock with results and seismic data
            if hasattr(self.parent, 'export_dock') and hasattr(self.parent, 'plot_manager'):
                self.parent.export_dock.set_references(
                    result, windows, self.parent.plot_manager, data
                )
                if emit_info and data is not None:
                    self.info_message.emit(
                        "Export dock: All figure types available (including waveform plots)"
                    )
        
        def _update_all_docks_safe(self, result, windows, data):
            """Update all docks with extra error handling (for session restore)."""
            # Update canvas
            if hasattr(self.parent, 'canvas') and result is not None:
                try:
                    self.parent.canvas.set_data(result, windows, data)
                except Exception as e:
                    self.info_message.emit(f"Warning: Could not update canvas: {str(e)}")
            
            # Update layers dock
            if hasattr(self.parent, 'layers_dock') and windows is not None:
                try:
                    self.parent.layers_dock.set_references(self.parent.plot_manager, windows)
                except Exception as e:
                    self.info_message.emit(f"Warning: Could not update layers dock: {str(e)}")
            
            # Update peak picker dock
            if hasattr(self.parent, 'peak_picker_dock') and result is not None:
                try:
                    self.parent.peak_picker_dock.set_hvsr_data(
                        result, result.frequencies, result.mean_hvsr
                    )
                except Exception as e:
                    self.info_message.emit(f"Warning: Could not update peak picker: {str(e)}")
            
            # Update export dock
            if hasattr(self.parent, 'export_dock'):
                try:
                    self.parent.export_dock.set_references(
                        result, windows, self.parent.plot_manager, data
                    )
                    if data is not None:
                        self.info_message.emit(
                            "Export dock: All figure types available (including waveform plots)"
                        )
                    else:
                        self.info_message.emit(
                            "Export dock: Waveform plots unavailable (no seismic data)"
                        )
                except Exception as e:
                    self.info_message.emit(f"Warning: Could not update export dock: {str(e)}")
        
        def _update_data_panels(self):
            """Update collapsible data panels in tabs."""
            # Update processing tab data panel
            if hasattr(self.parent, 'processing_data_panel') and hasattr(self.parent, 'data_load_tab'):
                try:
                    self.parent.processing_data_panel.update_from_data_load_tab(
                        self.parent.data_load_tab
                    )
                except Exception as e:
                    self.info_message.emit(f"Warning: Could not update data panel: {str(e)}")
            
            # Update azimuthal tab with windows and data
            if hasattr(self.parent, 'azimuthal_tab') and self.parent.windows is not None:
                try:
                    self.parent.azimuthal_tab.set_windows(
                        self.parent.windows, self.parent.data
                    )
                    if hasattr(self.parent.azimuthal_tab, 'data_panel') and hasattr(self.parent, 'data_load_tab'):
                        self.parent.azimuthal_tab.data_panel.update_from_data_load_tab(
                            self.parent.data_load_tab
                        )
                except Exception as e:
                    self.info_message.emit(f"Warning: Could not update azimuthal tab: {str(e)}")
        
        def _enable_post_processing_controls(self):
            """Enable action buttons after processing/restore."""
            # Check for buttons that may be in different locations
            button_names = ['export_plot_btn', 'report_btn', 'export_btn', 'save_btn']
            for btn_name in button_names:
                if hasattr(self.parent, btn_name):
                    btn = getattr(self.parent, btn_name)
                    if btn is not None:
                        btn.setEnabled(True)
        
        def _update_window_info(self):
            """Update window info display."""
            if hasattr(self.parent, 'update_window_info'):
                self.parent.update_window_info()
        
        def _plot_results(self, result, windows, data):
            """Plot HVSR results in the plot window."""
            if not hasattr(self.parent, 'plotting_ctrl') or not hasattr(self.parent, 'plot_manager'):
                return
            
            # Set data in plotting controller
            self.parent.plotting_ctrl.set_data(result, windows, data)
            self.parent.plotting_ctrl.set_plot_manager(self.parent.plot_manager)
            
            # Plot using controller
            lines = self.parent.plotting_ctrl.plot_hvsr_results(result, windows, data)
            self.parent.window_lines = lines.get('window_lines', {})
            self.parent.stat_lines = lines.get('stat_lines', {})
            
            # Rebuild layer dock with lines
            if hasattr(self.parent, 'layers_dock'):
                self.parent.layers_dock.rebuild(
                    self.parent.window_lines, self.parent.stat_lines
                )
            
            # Show plot window
            self.parent.plot_manager.show_separate()
        
        def _emit_completion_info(self, result, windows):
            """Emit completion info messages."""
            self.info_message.emit("Processing complete!")
            self.info_message.emit(f"   Windows: {windows.n_active}/{windows.n_windows}")
            
            if result.primary_peak:
                self.info_message.emit(
                    f"   Primary peak: f0 = {result.primary_peak.frequency:.2f} Hz"
                )
            
            if hasattr(self.parent, 'status_bar'):
                self.parent.status_bar.showMessage(
                    "Ready - Use layer dock to toggle visibility"
                )
        
        def update_docks_only(self, result, windows, data):
            """
            Update only dock widgets (no plotting).
            
            Useful for partial updates or when plot already exists.
            """
            self._update_all_docks(result, windows, data, emit_info=False)
            self._update_data_panels()


else:
    class UIUpdateCoordinator:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
