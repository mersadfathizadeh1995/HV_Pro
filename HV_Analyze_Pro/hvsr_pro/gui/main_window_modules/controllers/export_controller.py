"""
Export Controller
=================

Handles export operations for the main window.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

try:
    from PyQt5.QtWidgets import QWidget, QMessageBox, QFileDialog, QInputDialog
    from PyQt5.QtCore import QObject, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


@dataclass
class ExportResult:
    """Result from an export operation."""
    success: bool
    file_path: str = ''
    created_files: Dict[str, str] = None
    error_message: str = ''
    
    def __post_init__(self):
        if self.created_files is None:
            self.created_files = {}


if HAS_PYQT5:
    class ExportController(QObject):
        """
        Controller for export operations.
        
        Handles:
        - HVSR results export (CSV, JSON, metadata)
        - Plot image export (PNG, PDF, SVG)
        - Report generation
        
        Signals:
            export_started: Emitted when export begins
            export_finished: Emitted with ExportResult when complete
            info_message: Emitted with info messages
            error_occurred: Emitted with error messages
        """
        
        export_started = pyqtSignal()
        export_finished = pyqtSignal(object)  # ExportResult
        info_message = pyqtSignal(str)
        error_occurred = pyqtSignal(str)
        
        def __init__(self, parent: QWidget):
            """
            Initialize export controller.
            
            Args:
                parent: Parent widget (main window)
            """
            super().__init__(parent)
            self.parent = parent
            self.hvsr_result = None
            self.windows = None
            self.data = None
            self.plot_manager = None
        
        def set_references(self, hvsr_result, windows, data, plot_manager):
            """
            Set references to required objects.
            
            Args:
                hvsr_result: HVSRResult object
                windows: WindowCollection object
                data: SeismicData object
                plot_manager: PlotWindowManager object
            """
            self.hvsr_result = hvsr_result
            self.windows = windows
            self.data = data
            self.plot_manager = plot_manager
        
        def export_results(self, output_dir: str = None) -> ExportResult:
            """
            Export HVSR results (curve data, peaks, metadata).
            
            Args:
                output_dir: Output directory path (prompts if None)
                
            Returns:
                ExportResult with success status and created files
            """
            if self.hvsr_result is None:
                return ExportResult(
                    success=False, 
                    error_message="No HVSR results to export."
                )
            
            # Prompt for output directory if not provided
            if not output_dir:
                output_dir = QFileDialog.getExistingDirectory(
                    self.parent, "Select Output Directory"
                )
                
            if not output_dir:
                return ExportResult(success=False, error_message="No directory selected")
            
            self.export_started.emit()
            
            try:
                from hvsr_pro.utils.export_utils import export_complete_dataset
                
                created_files = export_complete_dataset(
                    self.hvsr_result,
                    output_dir,
                    base_filename="hvsr"
                )
                
                self.info_message.emit(f"Exported to: {output_dir}")
                for file_type, filepath in created_files.items():
                    filename = Path(filepath).name
                    self.info_message.emit(f"   - {filename} ({file_type})")
                
                result = ExportResult(
                    success=True,
                    file_path=output_dir,
                    created_files=created_files
                )
                self.export_finished.emit(result)
                return result
                
            except Exception as e:
                import traceback
                error_msg = f"Export failed: {str(e)}\n{traceback.format_exc()}"
                self.error_occurred.emit(error_msg)
                return ExportResult(success=False, error_message=error_msg)
        
        def export_plot_image(
            self,
            file_path: str = None,
            dpi: int = None
        ) -> ExportResult:
            """
            Export current plot view as image.
            
            Args:
                file_path: Output file path (prompts if None)
                dpi: Resolution in DPI (prompts for raster if None)
                
            Returns:
                ExportResult with success status
            """
            if self.hvsr_result is None:
                return ExportResult(
                    success=False,
                    error_message="No plot to export. Please process data first."
                )
            
            if self.plot_manager is None or self.plot_manager.fig is None:
                return ExportResult(
                    success=False,
                    error_message="No plot figure available."
                )
            
            # Prompt for file path if not provided
            if not file_path:
                file_path, _ = QFileDialog.getSaveFileName(
                    self.parent,
                    "Export Plot as Image",
                    "hvsr_plot.png",
                    "PNG Image (*.png);;PDF Document (*.pdf);;SVG Vector (*.svg);;JPEG Image (*.jpg)"
                )
            
            if not file_path:
                return ExportResult(success=False, error_message="No file path selected")
            
            self.export_started.emit()
            
            try:
                # Determine DPI
                if dpi is None:
                    if file_path.endswith('.pdf') or file_path.endswith('.svg'):
                        dpi = 300  # Vector formats
                    else:
                        # Prompt for DPI for raster formats
                        dpi_str, ok = QInputDialog.getItem(
                            self.parent,
                            "Select Resolution",
                            "Choose image resolution (DPI):",
                            ["150 (Screen)", "300 (Print)", "600 (High Quality)"],
                            1,  # Default to 300
                            False
                        )
                        
                        if not ok:
                            return ExportResult(success=False, error_message="DPI selection cancelled")
                        
                        dpi = int(dpi_str.split()[0])
                
                # Save the figure
                self.plot_manager.fig.savefig(
                    file_path,
                    dpi=dpi,
                    bbox_inches='tight',
                    facecolor='white',
                    edgecolor='none'
                )
                
                # Log success
                file_size = Path(file_path).stat().st_size / 1024  # KB
                self.info_message.emit(f"Plot exported to: {Path(file_path).name}")
                self.info_message.emit(f"  Resolution: {dpi} DPI, Size: {file_size:.1f} KB")
                
                result = ExportResult(
                    success=True,
                    file_path=file_path,
                    created_files={'plot': file_path}
                )
                self.export_finished.emit(result)
                return result
                
            except Exception as e:
                error_msg = f"Failed to export plot: {str(e)}"
                self.error_occurred.emit(error_msg)
                return ExportResult(success=False, error_message=error_msg)
        
        def open_report_dialog(self):
            """Open advanced export dialog for comprehensive visualizations."""
            if self.hvsr_result is None:
                QMessageBox.warning(
                    self.parent, "No Results", 
                    "No results to export."
                )
                return
            
            from hvsr_pro.gui.dialogs import ExportDialog
            
            dialog = ExportDialog(
                self.parent, 
                self.hvsr_result, 
                self.windows, 
                self.data
            )
            dialog.exec_()
        
        def get_export_info(self) -> Dict[str, Any]:
            """Get information about what can be exported."""
            return {
                'has_hvsr_result': self.hvsr_result is not None,
                'has_windows': self.windows is not None,
                'has_data': self.data is not None,
                'has_plot': self.plot_manager is not None and self.plot_manager.fig is not None
            }


else:
    @dataclass
    class ExportResult:
        """Dummy class when PyQt5 not available."""
        success: bool = False
        file_path: str = ''
        created_files: Dict[str, str] = None
        error_message: str = ''
    
    class ExportController:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
