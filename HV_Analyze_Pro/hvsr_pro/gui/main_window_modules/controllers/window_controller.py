"""
Window Controller
=================

Handles window management operations (toggle, reject, visibility, etc).
Manages window state synchronization between UI and data.
"""

from typing import Optional, Dict, Any, List, Callable

try:
    from PyQt5.QtWidgets import QWidget
    from PyQt5.QtCore import QObject, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class WindowController(QObject):
        """
        Controller for window management.
        
        Handles:
        - Window toggle (accept/reject)
        - Batch operations
        - Window state synchronization
        - Layer visibility management
        
        Signals:
            window_toggled: Emitted with (index, is_active) when a window is toggled
            all_rejected: Emitted when all windows are rejected
            all_accepted: Emitted when all windows are accepted
            visibility_changed: Emitted with (index, is_visible) when visibility changes
            statistics_updated: Emitted with statistics dict when stats change
        """
        
        window_toggled = pyqtSignal(int, bool)  # window_index, is_active
        all_rejected = pyqtSignal()
        all_accepted = pyqtSignal()
        visibility_changed = pyqtSignal(int, bool)  # window_index, is_visible
        statistics_updated = pyqtSignal(dict)
        
        def __init__(self, parent: QWidget):
            """
            Initialize window controller.
            
            Args:
                parent: Parent widget (main window)
            """
            super().__init__(parent)
            self.parent = parent
            self.windows = None
            self._change_callbacks: List[Callable] = []
            self._original_states: Dict[int, bool] = {}  # Store original QC states
        
        def toggle_window(self, window_index: int) -> bool:
            """
            Toggle window acceptance state.
            
            Args:
                window_index: Index of window to toggle
                
            Returns:
                New state (True = active)
            """
            if self.windows is None:
                return False
            
            window = self.windows.get_window(window_index)
            if window is None:
                return False
            
            new_state = not window.is_active()
            
            if new_state:
                window.activate()
            else:
                window.reject("Manual rejection", manual=True)
            
            self._notify_change()
            self.window_toggled.emit(window_index, new_state)
            self.statistics_updated.emit(self.get_statistics())
            return new_state
        
        def reject_window(self, window_index: int, reason: str = "Manual"):
            """Reject a specific window."""
            if self.windows is None:
                return
            
            window = self.windows.get_window(window_index)
            if window:
                window.reject(reason, manual=True)
                self._notify_change()
                self.window_toggled.emit(window_index, False)
                self.statistics_updated.emit(self.get_statistics())
        
        def accept_window(self, window_index: int):
            """Accept a specific window."""
            if self.windows is None:
                return
            
            window = self.windows.get_window(window_index)
            if window:
                window.activate()
                self._notify_change()
                self.window_toggled.emit(window_index, True)
                self.statistics_updated.emit(self.get_statistics())
        
        def reject_all(self, reason: str = "Batch rejection"):
            """Reject all windows."""
            if self.windows is None:
                return
            
            for window in self.windows.windows:
                if window.is_active():
                    window.reject(reason, manual=True)
            
            self._notify_change()
            self.all_rejected.emit()
            self.statistics_updated.emit(self.get_statistics())
        
        def accept_all(self):
            """Accept all windows."""
            if self.windows is None:
                return
            
            for window in self.windows.windows:
                if window.is_rejected():
                    window.activate()
            
            self._notify_change()
            self.all_accepted.emit()
            self.statistics_updated.emit(self.get_statistics())
        
        def set_windows(self, windows):
            """
            Set the WindowCollection to manage.
            Also stores original states for reset functionality.
            
            Args:
                windows: WindowCollection object
            """
            self.windows = windows
            
            # Store original states
            if windows:
                self._original_states = {
                    i: w.is_active() for i, w in enumerate(windows.windows)
                }
        
        def reset_to_original(self):
            """Reset all windows to original QC state."""
            if self.windows is None or not self._original_states:
                return
            
            for i, original_state in self._original_states.items():
                window = self.windows.get_window(i)
                if window:
                    if original_state:
                        window.activate()
                    else:
                        window.reject("Restored from original QC")
            
            self._notify_change()
            self.statistics_updated.emit(self.get_statistics())
        
        def toggle_visibility(self, window_index: int) -> bool:
            """
            Toggle window visibility (for layer management).
            
            Args:
                window_index: Index of window to toggle
            
            Returns:
                New visibility state
            """
            if self.windows is None:
                return False
            
            window = self.windows.get_window(window_index)
            if window is None:
                return False
            
            # Toggle visibility flag
            window.visible = not getattr(window, 'visible', True)
            new_visible = window.visible
            
            self.visibility_changed.emit(window_index, new_visible)
            return new_visible
        
        def set_visibility(self, window_index: int, visible: bool):
            """
            Set window visibility explicitly.
            
            Args:
                window_index: Index of window
                visible: New visibility state
            """
            if self.windows is None:
                return
            
            window = self.windows.get_window(window_index)
            if window:
                window.visible = visible
                self.visibility_changed.emit(window_index, visible)
        
        def show_all(self):
            """Show all windows (set visibility to True)."""
            if self.windows is None:
                return
            
            for i, window in enumerate(self.windows.windows):
                window.visible = True
                self.visibility_changed.emit(i, True)
        
        def hide_rejected(self):
            """Hide all rejected windows."""
            if self.windows is None:
                return
            
            for i, window in enumerate(self.windows.windows):
                if not window.is_active():
                    window.visible = False
                    self.visibility_changed.emit(i, False)
        
        def get_visible_indices(self) -> List[int]:
            """Get list of visible window indices."""
            if self.windows is None:
                return []
            
            return [i for i, w in enumerate(self.windows.windows) 
                   if getattr(w, 'visible', True)]
        
        def get_hidden_indices(self) -> List[int]:
            """Get list of hidden window indices."""
            if self.windows is None:
                return []
            
            return [i for i, w in enumerate(self.windows.windows) 
                   if not getattr(w, 'visible', True)]
        
        def get_window_info(self, window_index: int) -> Optional[Dict[str, Any]]:
            """
            Get detailed info about a specific window.
            
            Args:
                window_index: Index of window
            
            Returns:
                Dict with window info or None
            """
            if self.windows is None:
                return None
            
            window = self.windows.get_window(window_index)
            if window is None:
                return None
            
            return {
                'index': window_index,
                'active': window.is_active(),
                'visible': getattr(window, 'visible', True),
                'start_time': getattr(window, 'start_time', 0),
                'duration': getattr(window, 'duration', 0),
                'rejection_reason': getattr(window, 'rejection_reason', None),
                'quality_metrics': getattr(window, 'quality_metrics', {}),
            }
        
        def get_statistics(self) -> Dict[str, Any]:
            """Get window statistics."""
            if self.windows is None:
                return {
                    'total': 0,
                    'active': 0,
                    'rejected': 0,
                    'acceptance_rate': 0.0,
                    'visible': 0
                }
            
            total = self.windows.n_windows
            active = self.windows.n_active
            rejected = self.windows.n_rejected
            rate = self.windows.acceptance_rate * 100
            visible = len(self.get_visible_indices())
            
            return {
                'total': total,
                'active': active,
                'rejected': rejected,
                'acceptance_rate': rate,
                'visible': visible
            }
        
        def get_active_indices(self) -> List[int]:
            """Get list of active window indices."""
            if self.windows is None:
                return []
            
            return [i for i, w in enumerate(self.windows.windows) if w.is_active()]
        
        def get_rejected_indices(self) -> List[int]:
            """Get list of rejected window indices."""
            if self.windows is None:
                return []
            
            return [i for i, w in enumerate(self.windows.windows) if not w.is_active()]
        
        def add_change_callback(self, callback: Callable):
            """Add callback for window state changes."""
            self._change_callbacks.append(callback)
        
        def remove_change_callback(self, callback: Callable):
            """Remove change callback."""
            if callback in self._change_callbacks:
                self._change_callbacks.remove(callback)
        
        def _notify_change(self):
            """Notify all callbacks of state change."""
            for callback in self._change_callbacks:
                try:
                    callback()
                except Exception:
                    pass

else:
    class WindowController:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
