"""
View State Manager
==================

Manages view state for the main window (dock visibility, tab visibility, etc).
"""

from typing import Optional, Dict, Any

try:
    from PyQt5.QtWidgets import QWidget, QMainWindow, QDockWidget, QTabWidget
    from PyQt5.QtCore import QObject, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class ViewStateManager(QObject):
        """
        Manages view state for HVSRMainWindow.
        
        Handles:
        - Dock visibility
        - Tab visibility
        - Plot window mode
        - View state persistence
        
        Signals:
            state_changed: Emitted when view state changes
            tab_changed: Emitted when current tab changes
        """
        
        state_changed = pyqtSignal(str, bool)  # component_name, is_visible
        tab_changed = pyqtSignal(int)  # tab_index
        
        def __init__(self, parent: QMainWindow):
            """
            Initialize view state manager.
            
            Args:
                parent: Parent main window
            """
            super().__init__(parent)
            self.parent = parent
            self._dock_states: Dict[str, bool] = {}
            self._tab_states: Dict[str, bool] = {}
        
        def toggle_plot_window(self):
            """Toggle between separate and embedded plot modes."""
            plot_manager = getattr(self.parent, 'plot_manager', None)
            if not plot_manager:
                return
            
            if plot_manager.mode == 'separate':
                plot_manager.show_separate()
                # Update button text if exists
                button = getattr(self.parent, 'plot_mode_button', None)
                if button:
                    button.setText("Dock Plot")
            else:
                plot_manager.show_embedded()
                button = getattr(self.parent, 'plot_mode_button', None)
                if button:
                    button.setText("Show Plot")
        
        def toggle_preview_canvas(self, visible: bool):
            """
            Toggle preview canvas visibility.
            
            Args:
                visible: True to show, False to hide
            """
            data_load_tab = getattr(self.parent, 'data_load_tab', None)
            if data_load_tab and hasattr(data_load_tab, 'preview_canvas'):
                data_load_tab.preview_canvas.setVisible(visible)
                self.state_changed.emit('preview_canvas', visible)
        
        def toggle_loaded_data_column(self, visible: bool):
            """
            Toggle loaded data column visibility.
            
            Args:
                visible: True to show, False to hide
            """
            data_load_tab = getattr(self.parent, 'data_load_tab', None)
            if data_load_tab and hasattr(data_load_tab, 'set_loaded_list_visible'):
                data_load_tab.set_loaded_list_visible(visible)
                self.state_changed.emit('loaded_data_column', visible)
        
        def toggle_azimuthal_tab(self, visible: bool):
            """
            Toggle azimuthal tab visibility.
            
            Args:
                visible: True to show, False to hide
            """
            mode_tabs = getattr(self.parent, 'mode_tabs', None)
            azimuthal_tab = getattr(self.parent, 'azimuthal_tab', None)
            
            if not mode_tabs or not azimuthal_tab:
                return
            
            # Find the tab index
            for i in range(mode_tabs.count()):
                if mode_tabs.widget(i) == azimuthal_tab:
                    mode_tabs.setTabVisible(i, visible)
                    if not visible and mode_tabs.currentIndex() == i:
                        # Switch to processing tab if hiding current tab
                        mode_tabs.setCurrentIndex(1)
                    self.state_changed.emit('azimuthal_tab', visible)
                    break
        
        def toggle_dock(self, dock_name: str, visible: bool):
            """
            Toggle a dock widget visibility.
            
            Args:
                dock_name: Name of dock ('layers', 'peaks', 'properties', 'export', 'azimuthal')
                visible: True to show, False to hide
            """
            dock_map = {
                'layers': 'layers_dock',
                'peaks': 'peak_picker_dock', 
                'properties': 'properties_dock',
                'export': 'export_dock',
                'azimuthal': 'azimuthal_properties_dock'
            }
            
            dock_attr = dock_map.get(dock_name)
            if dock_attr:
                dock = getattr(self.parent, dock_attr, None)
                if dock:
                    dock.setVisible(visible)
                    self._dock_states[dock_name] = visible
                    self.state_changed.emit(f'dock_{dock_name}', visible)
        
        def handle_tab_changed(self, index: int):
            """
            Handle tab change and update dock visibility accordingly.
            
            Args:
                index: New tab index (0=Data Load, 1=Processing, 2=Azimuthal)
            """
            if index == 0:  # Data Load tab
                self._hide_all_docks()
                self.parent.status_bar.showMessage("Data Load mode - Load and preview seismic data")
                
            elif index == 1:  # Processing tab
                self._show_processing_docks()
                self.parent.status_bar.showMessage("Processing mode - Configure and run HVSR analysis")
                
            elif index == 2:  # Azimuthal tab
                self._show_azimuthal_docks()
                self.parent.status_bar.showMessage("Azimuthal mode - Analyze directional site response")
                
                # Pass windows to azimuthal tab if available
                windows = getattr(self.parent, 'windows', None)
                if windows and hasattr(self.parent, 'azimuthal_tab'):
                    self.parent.azimuthal_tab.set_windows(windows)
            
            self.tab_changed.emit(index)
        
        def _hide_all_docks(self):
            """Hide all docks."""
            dock_names = ['layers', 'peaks', 'properties', 'export', 'azimuthal']
            for name in dock_names:
                self.toggle_dock(name, False)
        
        def _show_processing_docks(self):
            """Show processing-related docks."""
            self.toggle_dock('layers', True)
            self.toggle_dock('peaks', True)
            self.toggle_dock('properties', True)
            self.toggle_dock('export', True)
            self.toggle_dock('azimuthal', False)
        
        def _show_azimuthal_docks(self):
            """Show azimuthal-related docks."""
            self.toggle_dock('layers', False)
            self.toggle_dock('peaks', False)
            self.toggle_dock('properties', False)
            self.toggle_dock('export', False)
            self.toggle_dock('azimuthal', True)
            
            # Raise azimuthal dock
            azimuthal_dock = getattr(self.parent, 'azimuthal_properties_dock', None)
            if azimuthal_dock:
                azimuthal_dock.raise_()
        
        def get_view_state(self) -> Dict[str, Any]:
            """Get current view state for persistence."""
            return {
                'docks': self._dock_states.copy(),
                'tabs': self._tab_states.copy()
            }
        
        def restore_view_state(self, state: Dict[str, Any]):
            """Restore view state from saved data."""
            if 'docks' in state:
                for name, visible in state['docks'].items():
                    self.toggle_dock(name, visible)
            
            if 'tabs' in state:
                for name, visible in state['tabs'].items():
                    if name == 'azimuthal':
                        self.toggle_azimuthal_tab(visible)
        
        def handle_view_mode_changed(self, mode: str) -> bool:
            """
            Handle view mode change (statistical, windows, both).
            
            Updates plot line visibility based on selected mode.
            
            Args:
                mode: View mode ('statistical', 'windows', 'both')
            
            Returns:
                True if handled successfully, False otherwise
            """
            # Get references from parent
            window_lines = getattr(self.parent, 'window_lines', None)
            stat_lines = getattr(self.parent, 'stat_lines', None)
            windows = getattr(self.parent, 'windows', None)
            plot_manager = getattr(self.parent, 'plot_manager', None)
            
            if not window_lines or not stat_lines:
                return False
            
            # Update line visibility based on mode
            if mode == 'statistical':
                # Hide individual windows, show statistics
                for line in window_lines.values():
                    line.set_visible(False)
                for line in stat_lines.values():
                    line.set_visible(True)
            
            elif mode == 'windows':
                # Show individual windows + stats, respect visibility flags
                if windows:
                    for idx, line in window_lines.items():
                        window = windows.get_window(idx)
                        if window:
                            line.set_visible(window.is_active() and window.visible)
                for line in stat_lines.values():
                    line.set_visible(True)
            
            elif mode == 'both':
                # Show everything
                if windows:
                    for idx, line in window_lines.items():
                        window = windows.get_window(idx)
                        if window:
                            line.set_visible(window.is_active() and window.visible)
                for line in stat_lines.values():
                    line.set_visible(True)
            
            # Redraw
            if plot_manager and hasattr(plot_manager, 'fig') and plot_manager.fig:
                plot_manager.fig.canvas.draw_idle()
            
            self.state_changed.emit('view_mode', True)
            return True

else:
    class ViewStateManager:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
