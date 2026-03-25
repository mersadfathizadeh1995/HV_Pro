"""
Menu Bar Module
===============

Menu bar creation and action handlers for the main window.
"""

from typing import Callable, Dict, Any, Optional, TYPE_CHECKING

try:
    from PyQt5.QtWidgets import (
        QMainWindow, QMenuBar, QMenu, QAction, QMessageBox, QApplication
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QKeySequence
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if TYPE_CHECKING:
    from hvsr_pro.gui.main_window import HVSRMainWindow


if HAS_PYQT5:
    class MenuBarHelper:
        """
        Helper class for creating and managing menu bars.
        
        Manages complete menu bar setup for HVSRMainWindow, including:
        - File menu (open, save, session, export, exit)
        - Edit menu (copy, clear)
        - View menu with submenus for docks, tabs
        - Mode menu for tab switching
        - Help menu
        
        Usage:
            helper = MenuBarHelper(main_window)
            helper.build_complete_menu_bar()
            # Access stored actions via helper.actions['action_name']
        """
        
        def __init__(self, parent: QMainWindow):
            """
            Initialize menu bar helper.
            
            Args:
                parent: Parent main window
            """
            self.parent = parent
            self.menubar = parent.menuBar()
            self.menubar.setNativeMenuBar(False)  # Fix Windows issues
            self.menubar.setVisible(True)
            
            self.menus: Dict[str, QMenu] = {}
            self.actions: Dict[str, QAction] = {}
        
        def build_complete_menu_bar(self) -> None:
            """
            Build the complete menu bar for HVSRMainWindow.
            
            This creates all menus and actions, storing references in self.actions
            for later access by the main window.
            """
            self._build_project_menu()
            self._build_file_menu()
            self._build_edit_menu()
            self._build_view_menu()
            self._build_tools_menu()
            self._build_mode_menu()
            self._build_help_menu()
        
        def _build_project_menu(self) -> QMenu:
            """Build the Project menu (project manager integration)."""
            project_menu = self.menubar.addMenu('&Project')
            self.menus['project'] = project_menu
            
            new_action = project_menu.addAction('&New Project...')
            new_action.setShortcut('Ctrl+Shift+N')
            new_action.setStatusTip('Create a new HV Pro project')
            new_action.triggered.connect(self.parent.new_project)
            self.actions['new_project'] = new_action
            
            open_action = project_menu.addAction('&Open Project...')
            open_action.setShortcut('Ctrl+Shift+O')
            open_action.setStatusTip('Open an existing HV Pro project')
            open_action.triggered.connect(self.parent.open_project)
            self.actions['open_project'] = open_action
            
            project_menu.addSeparator()
            
            hub_action = project_menu.addAction('Project &Hub...')
            hub_action.setShortcut('Ctrl+H')
            hub_action.setStatusTip('Open the Project Hub dashboard')
            hub_action.triggered.connect(self.parent.open_project_hub)
            self.actions['project_hub'] = hub_action
            
            return project_menu
        
        def _build_file_menu(self) -> QMenu:
            """Build the File menu."""
            file_menu = self.menubar.addMenu('&File')
            self.menus['file'] = file_menu
            
            # Open action
            open_action = file_menu.addAction('&Open...')
            open_action.setShortcut('Ctrl+O')
            open_action.triggered.connect(self.parent.load_data_file)
            self.actions['open'] = open_action
            
            # Save results action
            save_action = file_menu.addAction('&Save Results...')
            save_action.setShortcut('Ctrl+S')
            save_action.triggered.connect(self.parent.export_results)
            self.actions['save'] = save_action
            
            file_menu.addSeparator()
            
            # Session menu items
            save_session_action = file_menu.addAction('Save &Session...')
            save_session_action.setShortcut('Ctrl+Shift+S')
            save_session_action.triggered.connect(self.parent.save_session)
            save_session_action.setToolTip("Save current settings and state to resume later")
            self.actions['save_session'] = save_session_action
            
            load_session_action = file_menu.addAction('&Load Session...')
            load_session_action.setShortcut('Ctrl+Shift+O')
            load_session_action.triggered.connect(self.parent.load_session)
            load_session_action.setToolTip("Load a saved session file")
            self.actions['load_session'] = load_session_action
            
            file_menu.addSeparator()
            
            # Export figure action
            export_fig_action = file_menu.addAction('&Export Figure...')
            export_fig_action.setShortcut('Ctrl+E')
            export_fig_action.triggered.connect(self.parent.export_figure)
            self.actions['export_figure'] = export_fig_action
            
            file_menu.addSeparator()
            
            # Exit action
            exit_action = file_menu.addAction('E&xit')
            exit_action.setShortcut('Ctrl+Q')
            exit_action.triggered.connect(self.parent.close)
            self.actions['exit'] = exit_action
            
            return file_menu
        
        def _build_edit_menu(self) -> QMenu:
            """Build the Edit menu."""
            edit_menu = self.menubar.addMenu('&Edit')
            self.menus['edit'] = edit_menu
            
            # Copy info action
            copy_action = edit_menu.addAction('&Copy Info')
            copy_action.setShortcut('Ctrl+C')
            copy_action.triggered.connect(self.parent.copy_info)
            self.actions['copy'] = copy_action
            
            # Clear info action
            clear_action = edit_menu.addAction('C&lear Info')
            clear_action.triggered.connect(lambda: self.parent.info_text.clear())
            self.actions['clear'] = clear_action
            
            return edit_menu
        
        def _build_view_menu(self) -> QMenu:
            """Build the View menu with submenus."""
            view_menu = self.menubar.addMenu('&View')
            self.menus['view'] = view_menu
            
            # === Processing Tab submenu ===
            processing_submenu = QMenu('Processing Tab', self.parent)
            self.menus['processing_submenu'] = processing_submenu
            
            layers_action = processing_submenu.addAction('&Layers Dock')
            layers_action.setShortcut('Ctrl+Shift+L')
            layers_action.setCheckable(True)
            layers_action.setChecked(True)
            layers_action.triggered.connect(lambda checked: self.parent.layers_dock.setVisible(checked))
            self.actions['layers'] = layers_action
            # Also store on parent for backward compatibility
            self.parent.layers_action = layers_action
            
            peaks_action = processing_submenu.addAction('&Peak Picker Dock')
            peaks_action.setShortcut('Ctrl+Shift+P')
            peaks_action.setCheckable(True)
            peaks_action.setChecked(True)
            peaks_action.triggered.connect(lambda checked: self.parent.peak_picker_dock.setVisible(checked))
            self.actions['peaks'] = peaks_action
            self.parent.peaks_action = peaks_action
            
            props_action = processing_submenu.addAction('P&roperties Dock')
            props_action.setShortcut('Ctrl+Shift+R')
            props_action.setCheckable(True)
            props_action.setChecked(True)
            props_action.triggered.connect(lambda checked: self.parent.properties_dock.setVisible(checked))
            self.actions['props'] = props_action
            self.parent.props_action = props_action
            
            view_menu.addMenu(processing_submenu)
            view_menu.addSeparator()
            
            # === Data Load Tab submenu ===
            dataload_submenu = QMenu('Data Load Tab', self.parent)
            self.menus['dataload_submenu'] = dataload_submenu
            
            preview_action = dataload_submenu.addAction('&Preview Canvas')
            preview_action.setShortcut('Ctrl+Shift+V')
            preview_action.setCheckable(True)
            preview_action.setChecked(True)
            preview_action.triggered.connect(self.parent.toggle_preview_canvas)
            self.actions['preview'] = preview_action
            self.parent.preview_action = preview_action
            
            view_menu.addMenu(dataload_submenu)
            view_menu.addSeparator()
            
            # === Tabs submenu ===
            tabs_submenu = QMenu('Tabs', self.parent)
            self.menus['tabs_submenu'] = tabs_submenu
            
            azimuthal_tab_action = tabs_submenu.addAction('&Azimuthal Tab')
            azimuthal_tab_action.setShortcut('Ctrl+3')
            azimuthal_tab_action.setCheckable(True)
            azimuthal_tab_action.setChecked(True)
            azimuthal_tab_action.triggered.connect(self.parent.toggle_azimuthal_tab)
            self.actions['azimuthal_tab'] = azimuthal_tab_action
            self.parent.azimuthal_tab_action = azimuthal_tab_action
            
            view_menu.addMenu(tabs_submenu)
            view_menu.addSeparator()
            
            # === Global view items ===
            loaded_data_action = view_menu.addAction('&Loaded Data Column')
            loaded_data_action.setShortcut('Ctrl+Shift+D')
            loaded_data_action.setCheckable(True)
            loaded_data_action.setChecked(True)
            loaded_data_action.triggered.connect(self.parent.toggle_loaded_data_column)
            self.actions['loaded_data'] = loaded_data_action
            self.parent.loaded_data_action = loaded_data_action
            
            view_menu.addSeparator()
            
            plot_action = view_menu.addAction('&Plot Window')
            plot_action.setShortcut('Ctrl+P')
            plot_action.triggered.connect(self.parent.toggle_plot_window)
            self.actions['plot_window'] = plot_action
            
            return view_menu
        
        def _build_tools_menu(self) -> QMenu:
            """Build the Tools menu."""
            tools_menu = self.menubar.addMenu('&Tools')
            self.menus['tools'] = tools_menu
            
            batch_action = tools_menu.addAction('&Batch Processing...')
            batch_action.setShortcut('Ctrl+B')
            batch_action.setStatusTip('Open batch HVSR processing for multiple stations')
            batch_action.setToolTip('Process multiple stations with time windows (Ctrl+B)')
            batch_action.triggered.connect(self.parent.open_batch_processing)
            self.actions['batch_processing'] = batch_action
            
            bedrock_action = tools_menu.addAction('3D &Bedrock Mapping...')
            bedrock_action.setShortcut('Ctrl+M')
            bedrock_action.setStatusTip('Open 3D bedrock depth mapping from HVSR and borehole data')
            bedrock_action.setToolTip('3D bedrock depth mapping (Ctrl+M)')
            bedrock_action.triggered.connect(self.parent.open_bedrock_mapping)
            self.actions['bedrock_mapping'] = bedrock_action
            
            hvstrip_action = tools_menu.addAction('HV &Strip Progressive...')
            hvstrip_action.setShortcut('Ctrl+Shift+S')
            hvstrip_action.setStatusTip('Open HV Strip Progressive layer stripping analysis')
            hvstrip_action.setToolTip('HV Strip Progressive analysis (Ctrl+Shift+S)')
            hvstrip_action.triggered.connect(self.parent.open_hvstrip_progressive)
            self.actions['hvstrip_progressive'] = hvstrip_action
            
            tools_menu.addSeparator()
            
            invert_action = tools_menu.addAction('&Invert HVSR...')
            invert_action.setShortcut('Ctrl+I')
            invert_action.setStatusTip('Open HVSR Inversion Wizard for curve inversion')
            invert_action.setToolTip('HVSR curve inversion wizard (Ctrl+I)')
            invert_action.triggered.connect(self.parent.open_invert_hvsr)
            self.actions['invert_hvsr'] = invert_action
            
            return tools_menu
        
        def _build_mode_menu(self) -> QMenu:
            """Build the Mode menu."""
            mode_menu = self.menubar.addMenu('&Mode')
            self.menus['mode'] = mode_menu
            
            dataload_action = mode_menu.addAction('&Data Load')
            dataload_action.setShortcut('Ctrl+1')
            dataload_action.triggered.connect(lambda: self.parent.mode_tabs.setCurrentIndex(0))
            dataload_action.setToolTip("Switch to Data Load tab (Ctrl+1)")
            self.actions['mode_dataload'] = dataload_action
            
            processing_action = mode_menu.addAction('&Processing')
            processing_action.setShortcut('Ctrl+2')
            processing_action.triggered.connect(lambda: self.parent.mode_tabs.setCurrentIndex(1))
            processing_action.setToolTip("Switch to Processing tab (Ctrl+2)")
            self.actions['mode_processing'] = processing_action
            
            return mode_menu
        
        def _build_help_menu(self) -> QMenu:
            """Build the Help menu."""
            help_menu = self.menubar.addMenu('&Help')
            self.menus['help'] = help_menu
            
            about_action = help_menu.addAction('&About')
            about_action.triggered.connect(lambda: show_about_dialog(self.parent))
            self.actions['about'] = about_action
            
            shortcuts_action = help_menu.addAction('&Keyboard Shortcuts')
            shortcuts_action.setShortcut('F1')
            shortcuts_action.triggered.connect(lambda: show_shortcuts_dialog(self.parent))
            self.actions['shortcuts'] = shortcuts_action
            
            return help_menu
        
        # === Legacy methods for backward compatibility ===
        
        def create_file_menu(
            self,
            on_open: Optional[Callable] = None,
            on_save: Optional[Callable] = None,
            on_save_session: Optional[Callable] = None,
            on_load_session: Optional[Callable] = None,
            on_exit: Optional[Callable] = None
        ) -> QMenu:
            """Create the File menu (legacy interface)."""
            file_menu = self.menubar.addMenu('&File')
            self.menus['file'] = file_menu
            
            if on_open:
                open_action = file_menu.addAction('&Open...')
                open_action.setShortcut('Ctrl+O')
                open_action.triggered.connect(on_open)
                self.actions['open'] = open_action
            
            if on_save:
                save_action = file_menu.addAction('&Save Results...')
                save_action.setShortcut('Ctrl+S')
                save_action.triggered.connect(on_save)
                self.actions['save'] = save_action
            
            file_menu.addSeparator()
            
            if on_save_session:
                save_session = file_menu.addAction('Save &Session...')
                save_session.setShortcut('Ctrl+Shift+S')
                save_session.triggered.connect(on_save_session)
                self.actions['save_session'] = save_session
            
            if on_load_session:
                load_session = file_menu.addAction('&Load Session...')
                load_session.setShortcut('Ctrl+Shift+O')
                load_session.triggered.connect(on_load_session)
                self.actions['load_session'] = load_session
            
            file_menu.addSeparator()
            
            if on_exit:
                exit_action = file_menu.addAction('E&xit')
                exit_action.setShortcut('Ctrl+Q')
                exit_action.triggered.connect(on_exit)
                self.actions['exit'] = exit_action
            
            return file_menu
        
        def create_edit_menu(
            self,
            on_copy_info: Optional[Callable] = None
        ) -> QMenu:
            """Create the Edit menu (legacy interface)."""
            edit_menu = self.menubar.addMenu('&Edit')
            self.menus['edit'] = edit_menu
            
            if on_copy_info:
                copy_action = edit_menu.addAction('&Copy Results to Clipboard')
                copy_action.setShortcut('Ctrl+C')
                copy_action.triggered.connect(on_copy_info)
                self.actions['copy'] = copy_action
            
            return edit_menu
        
        def create_view_menu(
            self,
            toggles: Dict[str, tuple] = None
        ) -> QMenu:
            """Create the View menu with toggle actions (legacy interface)."""
            view_menu = self.menubar.addMenu('&View')
            self.menus['view'] = view_menu
            
            if toggles:
                for name, (label, callback, checked) in toggles.items():
                    action = view_menu.addAction(label)
                    action.setCheckable(True)
                    action.setChecked(checked)
                    action.triggered.connect(callback)
                    self.actions[f'view_{name}'] = action
            
            return view_menu
        
        def create_mode_menu(
            self,
            mode_actions: Dict[str, tuple] = None
        ) -> QMenu:
            """Create the Mode menu (legacy interface)."""
            mode_menu = self.menubar.addMenu('&Mode')
            self.menus['mode'] = mode_menu
            
            if mode_actions:
                for name, (label, callback, shortcut) in mode_actions.items():
                    action = mode_menu.addAction(label)
                    if shortcut:
                        action.setShortcut(shortcut)
                    action.triggered.connect(callback)
                    self.actions[f'mode_{name}'] = action
            
            return mode_menu
        
        def create_help_menu(
            self,
            on_about: Optional[Callable] = None,
            on_shortcuts: Optional[Callable] = None
        ) -> QMenu:
            """Create the Help menu (legacy interface)."""
            help_menu = self.menubar.addMenu('&Help')
            self.menus['help'] = help_menu
            
            if on_shortcuts:
                shortcuts_action = help_menu.addAction('&Keyboard Shortcuts')
                shortcuts_action.setShortcut('F1')
                shortcuts_action.triggered.connect(on_shortcuts)
                self.actions['shortcuts'] = shortcuts_action
            
            help_menu.addSeparator()
            
            if on_about:
                about_action = help_menu.addAction('&About HVSR Pro')
                about_action.triggered.connect(on_about)
                self.actions['about'] = about_action
            
            return help_menu
        
        def get_menu(self, name: str) -> Optional[QMenu]:
            """Get a menu by name."""
            return self.menus.get(name)
        
        def get_action(self, name: str) -> Optional[QAction]:
            """Get an action by name."""
            return self.actions.get(name)
        
        def set_action_enabled(self, name: str, enabled: bool):
            """Enable/disable an action."""
            action = self.actions.get(name)
            if action:
                action.setEnabled(enabled)

    def show_about_dialog(parent, version: str = "2.0.0"):
        """Show the About dialog."""
        QMessageBox.about(parent, "About HVSR Pro",
            "<h2>HVSR Pro v2.0</h2>"
            "<p>Professional Horizontal-to-Vertical Spectral Ratio Analysis</p>"
            "<p>A comprehensive tool for seismic data processing and HVSR computation.</p>"
            "<br>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Single and multi-file processing</li>"
            "<li>Advanced quality control algorithms</li>"
            "<li>Cox FDWRA peak consistency analysis</li>"
            "<li>Interactive visualization</li>"
            "<li>Azimuthal HVSR analysis</li>"
            "<li>Customizable processing parameters</li>"
            "</ul>"
            "<br>"
            "<p>&copy; 2024 HVSR Pro Development Team</p>")

    def show_shortcuts_dialog(parent):
        """Show keyboard shortcuts dialog."""
        shortcuts_text = """
        <h3>Keyboard Shortcuts</h3>
        <table cellpadding="5">
        <tr><th colspan="2" align="left">File Operations</th></tr>
        <tr><td><b>Ctrl+O</b></td><td>Open file</td></tr>
        <tr><td><b>Ctrl+S</b></td><td>Save results</td></tr>
        <tr><td><b>Ctrl+E</b></td><td>Export figure</td></tr>
        <tr><td><b>Ctrl+Q</b></td><td>Exit</td></tr>

        <tr><th colspan="2" align="left"><br>Tab Navigation</th></tr>
        <tr><td><b>Ctrl+1</b></td><td>Switch to Data Load tab</td></tr>
        <tr><td><b>Ctrl+2</b></td><td>Switch to Processing tab</td></tr>

        <tr><th colspan="2" align="left"><br>View Controls</th></tr>
        <tr><td><b>Ctrl+P</b></td><td>Toggle plot window</td></tr>
        <tr><td><b>Ctrl+Shift+L</b></td><td>Toggle Layers Dock</td></tr>
        <tr><td><b>Ctrl+Shift+P</b></td><td>Toggle Peak Picker Dock</td></tr>
        <tr><td><b>Ctrl+Shift+R</b></td><td>Toggle Properties Dock</td></tr>
        <tr><td><b>Ctrl+Shift+V</b></td><td>Toggle Preview Canvas</td></tr>
        <tr><td><b>Ctrl+Shift+D</b></td><td>Toggle Loaded Data Column</td></tr>

        <tr><th colspan="2" align="left"><br>Other</th></tr>
        <tr><td><b>F1</b></td><td>Show this help</td></tr>
        </table>
        """
        QMessageBox.information(parent, "Keyboard Shortcuts", shortcuts_text)

else:
    # Dummy implementations when PyQt5 is not available
    class MenuBarHelper:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
    
    def show_about_dialog(*args, **kwargs):
        pass
    
    def show_shortcuts_dialog(*args, **kwargs):
        pass
