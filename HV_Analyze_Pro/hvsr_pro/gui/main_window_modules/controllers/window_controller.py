"""
Window Controller
=================

Handles window management operations (toggle, reject, etc).
"""

from typing import Optional, Dict, Any, List, Callable

try:
    from PyQt5.QtWidgets import QWidget
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class WindowController:
        """
        Controller for window management.
        
        Handles:
        - Window toggle (accept/reject)
        - Batch operations
        - Window state synchronization
        """
        
        def __init__(self, parent: QWidget):
            """
            Initialize window controller.
            
            Args:
                parent: Parent widget (main window)
            """
            self.parent = parent
            self.windows = None
            self._change_callbacks: List[Callable] = []
        
        def set_windows(self, windows):
            """Set the WindowCollection to manage."""
            self.windows = windows
        
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
                window.mark_active()
            else:
                window.mark_rejected(reason="Manual rejection")
            
            self._notify_change()
            return new_state
        
        def reject_window(self, window_index: int, reason: str = "Manual"):
            """Reject a specific window."""
            if self.windows is None:
                return
            
            window = self.windows.get_window(window_index)
            if window:
                window.mark_rejected(reason=reason)
                self._notify_change()
        
        def accept_window(self, window_index: int):
            """Accept a specific window."""
            if self.windows is None:
                return
            
            window = self.windows.get_window(window_index)
            if window:
                window.mark_active()
                self._notify_change()
        
        def reject_all(self, reason: str = "Batch rejection"):
            """Reject all windows."""
            if self.windows is None:
                return
            
            for window in self.windows:
                window.mark_rejected(reason=reason)
            
            self._notify_change()
        
        def accept_all(self):
            """Accept all windows."""
            if self.windows is None:
                return
            
            for window in self.windows:
                window.mark_active()
            
            self._notify_change()
        
        def reset_to_original(self):
            """Reset all windows to original QC state."""
            if self.windows is None:
                return
            
            # This would need the original QC results stored
            self._notify_change()
        
        def get_statistics(self) -> Dict[str, Any]:
            """Get window statistics."""
            if self.windows is None:
                return {
                    'total': 0,
                    'active': 0,
                    'rejected': 0,
                    'acceptance_rate': 0.0
                }
            
            total = len(self.windows)
            active = self.windows.active_count
            rejected = total - active
            rate = (active / total * 100) if total > 0 else 0.0
            
            return {
                'total': total,
                'active': active,
                'rejected': rejected,
                'acceptance_rate': rate
            }
        
        def get_active_indices(self) -> List[int]:
            """Get list of active window indices."""
            if self.windows is None:
                return []
            
            return [i for i, w in enumerate(self.windows) if w.is_active()]
        
        def get_rejected_indices(self) -> List[int]:
            """Get list of rejected window indices."""
            if self.windows is None:
                return []
            
            return [i for i, w in enumerate(self.windows) if not w.is_active()]
        
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
