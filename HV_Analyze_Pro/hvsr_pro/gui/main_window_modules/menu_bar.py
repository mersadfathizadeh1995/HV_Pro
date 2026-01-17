"""
Menu Bar Module
===============

Menu bar creation and action handlers for the main window.
"""

from typing import Callable, Dict, Any, Optional

try:
    from PyQt5.QtWidgets import (
        QMainWindow, QMenuBar, QMenu, QAction, QMessageBox, QApplication
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QKeySequence
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class MenuBarHelper:
        """
        Helper class for creating and managing menu bars.
        
        Usage:
            helper = MenuBarHelper(main_window)
            helper.create_file_menu(on_open, on_save, on_exit)
            helper.create_view_menu(view_toggles)
            helper.create_help_menu()
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
        
        def create_file_menu(
            self,
            on_open: Optional[Callable] = None,
            on_save: Optional[Callable] = None,
            on_save_session: Optional[Callable] = None,
            on_load_session: Optional[Callable] = None,
            on_exit: Optional[Callable] = None
        ) -> QMenu:
            """Create the File menu."""
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
            """Create the Edit menu."""
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
            """
            Create the View menu with toggle actions.
            
            Args:
                toggles: Dict of {name: (label, callback, default_checked)}
            """
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
            """Create the Mode menu."""
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
            """Create the Help menu."""
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

    def show_about_dialog(parent, version: str = "1.0.0"):
        """Show the About dialog."""
        about_text = f"""
        <h2>HVSR Pro</h2>
        <p><b>Version:</b> {version}</p>
        <p>Professional HVSR (Horizontal-to-Vertical Spectral Ratio) Analysis Software</p>
        
        <h3>Features:</h3>
        <ul>
            <li>Load seismic data (ASCII, MiniSEED)</li>
            <li>Interactive window rejection</li>
            <li>Color-coded visualization</li>
            <li>Real-time HVSR updates</li>
            <li>Quality metrics and statistics</li>
            <li>Export results and plots</li>
            <li>Azimuthal HVSR analysis</li>
        </ul>
        
        <p>Built with PyQt5 and scientific Python libraries.</p>
        """
        QMessageBox.about(parent, "About HVSR Pro", about_text)

    def show_shortcuts_dialog(parent):
        """Show keyboard shortcuts dialog."""
        shortcuts_text = """
        <h3>Keyboard Shortcuts</h3>
        <table>
            <tr><td><b>Ctrl+O</b></td><td>Open file</td></tr>
            <tr><td><b>Ctrl+S</b></td><td>Save results</td></tr>
            <tr><td><b>Ctrl+Shift+S</b></td><td>Save session</td></tr>
            <tr><td><b>Ctrl+Shift+O</b></td><td>Load session</td></tr>
            <tr><td><b>Ctrl+P</b></td><td>Process HVSR</td></tr>
            <tr><td><b>Ctrl+R</b></td><td>Recompute HVSR</td></tr>
            <tr><td><b>Ctrl+E</b></td><td>Export figure</td></tr>
            <tr><td><b>Ctrl+Q</b></td><td>Quit</td></tr>
            <tr><td><b>F1</b></td><td>Show shortcuts</td></tr>
        </table>
        
        <h3>Window Interaction</h3>
        <ul>
            <li><b>Click window curve:</b> Toggle acceptance</li>
            <li><b>Layers panel:</b> Toggle visibility</li>
        </ul>
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
