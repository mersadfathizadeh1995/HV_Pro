"""
Session Mixin
=============

Mixin providing session management functionality for the main window.
"""

from pathlib import Path
from typing import Optional, Dict, Any

try:
    from PyQt5.QtWidgets import QMessageBox, QFileDialog
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


class SessionMixin:
    """
    Mixin providing session management functionality.
    
    This mixin should be used with HVSRMainWindow and provides:
    - save_session(): Save current session to file
    - load_session(): Load session from file
    - export_results(): Export HVSR results to files
    - generate_report_plots(): Open export dialog for visualizations
    
    Expected attributes on the main class:
    - hvsr_result: HVSRResult
    - windows: WindowCollection
    - data: SeismicData
    """
    
    def save_session(self):
        """Save current session to JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Session", "", "JSON Files (*.json)"
        )
        
        if file_path and self.hvsr_result:
            try:
                self.hvsr_result.save(file_path, include_windows=False)
                self.add_info(f"Session saved: {file_path}")
                QMessageBox.information(self, "Saved", "Session saved successfully")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", str(e))
                self.add_info(f"ERROR - Save session: {str(e)}")
    
    def load_session(self):
        """Load session from JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Session", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                from hvsr_pro.processing.hvsr import HVSRResult
                
                result = HVSRResult.load(file_path)
                self.hvsr_result = result
                self.add_info(f"Session loaded: {file_path}")
                
                QMessageBox.information(
                    self, "Loaded",
                    "Session loaded successfully\n"
                    "(Note: Window states not restored)"
                )
            except Exception as e:
                QMessageBox.critical(self, "Load Error", str(e))
                self.add_info(f"ERROR - Load session: {str(e)}")
    
    def export_results(self):
        """Export HVSR results (curve data, peaks, metadata)."""
        if self.hvsr_result is None:
            QMessageBox.warning(self, "No Results", "No results to export.")
            return
        
        # Select output directory
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        
        if not output_dir:
            return
        
        try:
            from hvsr_pro.utils.export_utils import export_complete_dataset
            
            # Export complete dataset
            created_files = export_complete_dataset(
                self.hvsr_result,
                output_dir,
                base_filename="hvsr"
            )
            
            self.add_info(f"Exported to: {output_dir}")
            for file_type, filepath in created_files.items():
                filename = Path(filepath).name
                self.add_info(f"   - {filename} ({file_type})")
            
            QMessageBox.information(
                self, "Export Complete",
                f"Results exported to:\n{output_dir}\n\n"
                f"Files created:\n" +
                "\n".join([f"- {Path(f).name}" for f in created_files.values()])
            )
            
        except Exception as e:
            import traceback
            error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
            QMessageBox.critical(self, "Export Error", error_msg)
            self.add_info(f"ERROR - Export: {str(e)}")
    
    def generate_report_plots(self):
        """Open advanced export dialog for comprehensive visualizations."""
        if self.hvsr_result is None:
            QMessageBox.warning(self, "No Results", "No results to export.")
            return
        
        from hvsr_pro.gui.export_dialog import ExportDialog
        
        dialog = ExportDialog(self, self.hvsr_result, self.windows, self.data)
        dialog.exec_()
    
    def get_session_state(self) -> Dict[str, Any]:
        """
        Get current session state as dictionary.
        
        Returns:
            Dictionary containing current session state
        """
        state = {
            'has_result': self.hvsr_result is not None,
            'has_windows': self.windows is not None,
            'has_data': self.data is not None,
            'current_file': str(self.current_file) if self.current_file else None,
            'load_mode': getattr(self, 'load_mode', 'single'),
        }
        
        if self.hvsr_result:
            state['result_info'] = {
                'n_frequencies': len(self.hvsr_result.frequencies),
                'has_primary_peak': self.hvsr_result.primary_peak is not None,
            }
            if self.hvsr_result.primary_peak:
                state['result_info']['f0'] = self.hvsr_result.primary_peak.frequency
        
        if self.windows:
            state['windows_info'] = {
                'total': self.windows.n_windows,
                'active': self.windows.n_active,
                'rejected': self.windows.n_rejected,
                'acceptance_rate': self.windows.acceptance_rate,
            }
        
        return state
    
    def restore_session_state(self, state: Dict[str, Any]) -> bool:
        """
        Restore session state from dictionary.
        
        Args:
            state: Session state dictionary
            
        Returns:
            True if restoration successful, False otherwise
        """
        # This is a placeholder for more complete session restoration
        # Full restoration would require saving/loading window states
        if 'current_file' in state and state['current_file']:
            self.current_file = state['current_file']
        
        if 'load_mode' in state:
            self.load_mode = state['load_mode']
        
        return True
    
    def export_session_summary(self, output_path: str) -> bool:
        """
        Export a text summary of the current session.
        
        Args:
            output_path: Path for output file
            
        Returns:
            True if export successful
        """
        if self.hvsr_result is None:
            return False
        
        try:
            state = self.get_session_state()
            
            with open(output_path, 'w') as f:
                f.write("HVSR Pro Session Summary\n")
                f.write("=" * 50 + "\n\n")
                
                if state.get('current_file'):
                    f.write(f"Data File: {state['current_file']}\n")
                
                if state.get('windows_info'):
                    wi = state['windows_info']
                    f.write(f"\nWindow Statistics:\n")
                    f.write(f"  Total windows: {wi['total']}\n")
                    f.write(f"  Active windows: {wi['active']}\n")
                    f.write(f"  Rejected windows: {wi['rejected']}\n")
                    f.write(f"  Acceptance rate: {wi['acceptance_rate']*100:.1f}%\n")
                
                if state.get('result_info'):
                    ri = state['result_info']
                    f.write(f"\nHVSR Results:\n")
                    f.write(f"  Frequency points: {ri['n_frequencies']}\n")
                    if ri.get('f0'):
                        f.write(f"  Fundamental frequency: {ri['f0']:.2f} Hz\n")
            
            self.add_info(f"Session summary exported to: {output_path}")
            return True
            
        except Exception as e:
            self.add_info(f"ERROR - Export summary: {str(e)}")
            return False

