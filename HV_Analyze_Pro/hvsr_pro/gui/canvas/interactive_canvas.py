"""
Interactive Matplotlib Canvas for HVSR Analysis
================================================

Canvas with click-to-toggle window rejection and color-coded visualization.
"""

import numpy as np
from typing import Optional

try:
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
    from PyQt5.QtCore import pyqtSignal
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
    from matplotlib.figure import Figure
    from matplotlib.patches import Rectangle
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


class InteractiveHVSRCanvas(QWidget):
    """
    Interactive canvas for HVSR visualization with window rejection.
    
    Features:
    - Click on windows to toggle active/rejected state
    - Color-coded: green=active, gray=rejected
    - Real-time updates
    - Multi-panel display (time series, HVSR, window status)
    
    Signals:
        window_toggled: Emitted when window is clicked (window_index)
        status_message: Emitted for status bar updates (message)
    """
    
    window_toggled = pyqtSignal(int)
    status_message = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Data storage
        self.hvsr_result = None
        self.windows = None
        self.data = None
        
        # Interactive state
        self.window_rectangles = {}  # Map window_index -> Rectangle patch
        self.current_hover = None
        
        # Setup UI
        self.init_ui()
    
    def init_ui(self):
        """Initialize canvas UI."""
        layout = QVBoxLayout(self)
        
        # Info label
        self.info_label = QLabel("No data loaded - Load a file to begin")
        self.info_label.setStyleSheet("QLabel { padding: 5px; background-color: #f0f0f0; }")
        layout.addWidget(self.info_label)
        
        # Create matplotlib figure
        self.figure = Figure(figsize=(12, 10))
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)
        
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        
        # Connect events
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_hover)
        
        # Initial empty plot
        self.init_empty_plot()
    
    def init_empty_plot(self):
        """Initialize empty plot."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Load data to begin analysis',
               ha='center', va='center', fontsize=14, color='gray')
        ax.axis('off')
        self.canvas.draw()
    
    def set_data(self, hvsr_result, windows, data):
        """Set data and create interactive visualization."""
        self.hvsr_result = hvsr_result
        self.windows = windows
        self.data = data
        
        # Check if this is a QC failure result
        if hasattr(hvsr_result, 'metadata') and hvsr_result.metadata.get('qc_failure', False):
            # Show error message instead of plots
            self.show_qc_failure_message()
            return
        
        # Update info
        info_text = (f"Windows: {windows.n_active}/{windows.n_windows} active | "
                    f"Peak: {hvsr_result.primary_peak.frequency:.2f} Hz" 
                    if hvsr_result.primary_peak else 
                    f"Windows: {windows.n_active}/{windows.n_windows} active")
        self.info_label.setText(info_text)
        
        # Create plots
        self.create_interactive_plots()
    
    def show_qc_failure_message(self):
        """Show message when all windows fail QC."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        
        # Create error message
        error_text = (
            "⚠️ QUALITY CONTROL FAILURE\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"All {self.windows.n_windows} windows were rejected by QC\n"
            f"No HVSR curve can be computed\n\n"
            "POSSIBLE CAUSES:\n"
            "• Data quality issues (high noise, spikes, gaps)\n"
            "• QC criteria too strict for this dataset\n"
            "• Sensor coupling problems\n"
            "• Site-specific conditions\n\n"
            "SUGGESTED ACTIONS:\n"
            "1. Try 'Aggressive' QC mode\n"
            "2. Use Custom QC with relaxed thresholds\n"
            "3. Check data quality visually\n"
            "4. Verify sensor installation\n"
            "5. Consider site conditions (noise sources)\n\n"
            "Click 'QC Settings' to adjust parameters"
        )
        
        ax.text(0.5, 0.5, error_text,
               ha='center', va='center',
               fontsize=11, color='darkred',
               bbox=dict(boxstyle='round,pad=1', facecolor='#ffeeee', edgecolor='red', linewidth=2))
        ax.axis('off')
        
        # Update info label
        self.info_label.setText(f"❌ QC FAILURE: 0/{self.windows.n_windows} windows passed")
        
        self.canvas.draw()
        self.status_message.emit("All windows rejected by QC. Adjust QC settings and reprocess.")
    
    def create_interactive_plots(self):
        """Create multi-panel interactive plots."""
        import numpy as np
        
        # CRITICAL: Validate data before plotting to prevent singular matrix error
        try:
            # Check 1: Do we have active windows?
            if self.windows.n_active == 0:
                self.show_qc_failure_message()
                return
            
            # Check 2: Valid frequency array?
            if len(self.hvsr_result.frequencies) == 0:
                self.show_qc_failure_message()
                return
            
            # Check 3: Valid HVSR data (not all NaN or invalid range)?
            if np.all(np.isnan(self.hvsr_result.mean_hvsr)):
                self.show_qc_failure_message()
                return
            
            # Check 4: Valid data range (not all same value)?
            data_range = np.ptp(self.hvsr_result.mean_hvsr[~np.isnan(self.hvsr_result.mean_hvsr)])
            if data_range < 1e-10:
                self.show_qc_failure_message()
                return
                
        except Exception as e:
            print(f"Data validation error: {e}")
            self.show_qc_failure_message()
            return
        
        # Wrap entire plotting in try-except to catch singular matrix errors
        try:
            self.figure.clear()
            
            # Create 3 subplots
            gs = self.figure.add_gridspec(3, 1, height_ratios=[1, 2, 1], hspace=0.3)
            
            # Panel 1: Window timeline (top)
            self.ax_timeline = self.figure.add_subplot(gs[0])
            self.plot_window_timeline()
            
            # Panel 2: HVSR curve (middle, large)
            self.ax_hvsr = self.figure.add_subplot(gs[1])
            self.plot_hvsr_curve()
            
            # Panel 3: Window statistics (bottom)
            self.ax_stats = self.figure.add_subplot(gs[2])
            self.plot_window_statistics()
            
            self.canvas.draw()
            self.status_message.emit("Click on windows in timeline to toggle rejection")
            
        except (np.linalg.LinAlgError, ValueError, RuntimeError) as e:
            # Catch singular matrix or other plotting errors
            print(f"Plotting error caught: {type(e).__name__}: {e}")
            self.show_qc_failure_message()
    
    def plot_window_timeline(self):
        """Plot interactive window timeline with color-coding."""
        ax = self.ax_timeline
        ax.clear()
        
        # Clear rectangle mapping
        self.window_rectangles.clear()
        
        # Get total duration
        total_duration = self.data.duration
        
        # Plot each window as rectangle
        for window in self.windows.windows:
            # Color based on state
            if window.is_active():
                color = 'green'
                alpha = 0.7
                edgecolor = 'darkgreen'
            else:
                color = 'lightgray'
                alpha = 0.3
                edgecolor = 'gray'
            
            # Create rectangle
            rect = Rectangle(
                (window.start_time, 0),
                window.duration,
                1,
                facecolor=color,
                edgecolor=edgecolor,
                linewidth=1,
                alpha=alpha,
                picker=True  # Enable picking
            )
            
            ax.add_patch(rect)
            self.window_rectangles[window.index] = rect
        
        ax.set_xlim(0, total_duration)
        ax.set_ylim(0, 1)
        ax.set_xlabel('Time (s)', fontsize=10)
        ax.set_ylabel('Windows', fontsize=10)
        ax.set_title('Window Timeline (Click to Toggle) - Green=Active, Gray=Rejected',
                    fontsize=11, fontweight='bold')
        ax.set_yticks([])
        ax.grid(True, axis='x', alpha=0.3)
        
        # Add stats text
        stats_text = f'Active: {self.windows.n_active}/{self.windows.n_windows} ({self.windows.acceptance_rate:.1%})'
        ax.text(0.02, 0.95, stats_text, transform=ax.transAxes,
               verticalalignment='top', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
    
    def plot_hvsr_curve(self):
        """Plot HVSR curve with uncertainty."""
        ax = self.ax_hvsr
        ax.clear()

        result = self.hvsr_result

        # Check for degenerate data (all zeros or extremely small values)
        mean_max = np.max(np.abs(result.mean_hvsr))
        mean_min = np.min(np.abs(result.mean_hvsr))
        data_range = np.ptp(result.mean_hvsr)  # peak-to-peak range

        is_degenerate = (data_range < 1e-10) or (mean_max < 1e-10)

        if is_degenerate:
            # Data is degenerate (all zeros or extremely small)
            ax.semilogx(result.frequencies, result.mean_hvsr,
                       'b-', linewidth=2, label='Mean H/V (degenerate data)')

            # Set reasonable default y-limits for degenerate data
            ax.set_ylim(-0.1, 0.1)

            # Add warning annotation
            ax.text(0.5, 0.5,
                   '⚠️ WARNING: HVSR values are extremely small or zero\n'
                   'This may indicate:\n'
                   '• Input data has very low amplitudes\n'
                   '• All components have identical values\n'
                   '• Numerical precision issues\n\n'
                   'Check your input data quality',
                   transform=ax.transAxes,
                   ha='center', va='center',
                   fontsize=10, color='red',
                   bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8))
        else:
            # Normal data - plot as usual
            ax.semilogx(result.frequencies, result.mean_hvsr,
                       'b-', linewidth=2, label='Mean H/V')

            # Plot uncertainty (16-84 percentile)
            ax.fill_between(result.frequencies,
                           result.percentile_16,
                           result.percentile_84,
                           alpha=0.3, color='blue', label='16-84th percentile')

            # Mark primary peak
            if result.primary_peak:
                peak = result.primary_peak
                ax.plot(peak.frequency, peak.amplitude,
                       'ro', markersize=10, markeredgecolor='black',
                       markeredgewidth=2, zorder=5, label='Primary Peak')

                # Annotate
                ax.annotate(f'f₀ = {peak.frequency:.2f} Hz\nA = {peak.amplitude:.2f}',
                           xy=(peak.frequency, peak.amplitude),
                           xytext=(20, 20), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.8),
                           arrowprops=dict(arrowstyle='->', lw=2),
                           fontsize=10, fontweight='bold')

        ax.set_xlabel('Frequency (Hz)', fontsize=11)
        ax.set_ylabel('H/V Spectral Ratio', fontsize=11)
        ax.set_title(f'HVSR Curve ({result.valid_windows} windows)',
                    fontsize=12, fontweight='bold')
        ax.grid(True, which='both', alpha=0.3, linestyle=':')
        ax.legend(loc='best', fontsize=9)

        # Always set x-limits
        ax.set_xlim(result.frequencies[0], result.frequencies[-1])
    
    def plot_window_statistics(self):
        """Plot window quality statistics."""
        ax = self.ax_stats
        ax.clear()

        # Extract quality scores
        active_scores = []
        rejected_scores = []
        active_indices = []
        rejected_indices = []

        for window in self.windows.windows:
            if 'overall' in window.quality_metrics:
                score = window.quality_metrics['overall']
                if window.is_active():
                    active_scores.append(score)
                    active_indices.append(window.index)
                else:
                    rejected_scores.append(score)
                    rejected_indices.append(window.index)

        # Plot
        if active_scores:
            ax.scatter(active_indices, active_scores, c='green', s=30,
                      alpha=0.6, label=f'Active ({len(active_scores)})')
        if rejected_scores:
            ax.scatter(rejected_indices, rejected_scores, c='red', s=30,
                      alpha=0.4, marker='x', label=f'Rejected ({len(rejected_scores)})')

        ax.set_xlabel('Window Index', fontsize=10)
        ax.set_ylabel('Quality Score', fontsize=10)
        ax.set_title('Window Quality Scores', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=9)
        ax.set_xlim(-5, self.windows.n_windows + 5)

        # Safety: Set default y-limits if no data
        if not active_scores and not rejected_scores:
            ax.set_ylim(0, 1)
    
    def update_window_states(self):
        """Update visualization after window states change."""
        if self.hvsr_result is None:
            return
        
        # Replot timeline with new colors
        self.plot_window_timeline()
        
        # Update HVSR curve might change
        # (Note: Not recomputing here, just updating display)
        
        # Update statistics
        self.plot_window_statistics()
        
        # Update info label
        info_text = (f"Windows: {self.windows.n_active}/{self.windows.n_windows} active | "
                    f"Peak: {self.hvsr_result.primary_peak.frequency:.2f} Hz"
                    if self.hvsr_result.primary_peak else
                    f"Windows: {self.windows.n_active}/{self.windows.n_windows} active")
        self.info_label.setText(info_text)
        
        self.canvas.draw()
    
    def on_click(self, event):
        """Handle mouse click events."""
        # Only process clicks on timeline
        if event.inaxes != self.ax_timeline:
            return
        
        if event.xdata is None:
            return
        
        # Find clicked window
        clicked_time = event.xdata
        
        for window in self.windows.windows:
            if window.start_time <= clicked_time <= (window.start_time + window.duration):
                # Toggle this window
                self.window_toggled.emit(window.index)
                return
    
    def on_hover(self, event):
        """Handle mouse hover for tooltip."""
        if event.inaxes != self.ax_timeline:
            if self.current_hover is not None:
                self.status_message.emit("Click on windows to toggle rejection")
                self.current_hover = None
            return
        
        if event.xdata is None:
            return
        
        # Find hovered window
        hover_time = event.xdata
        
        for window in self.windows.windows:
            if window.start_time <= hover_time <= (window.start_time + window.duration):
                if self.current_hover != window.index:
                    self.current_hover = window.index
                    
                    # Show window info
                    state = "ACTIVE" if window.is_active() else "REJECTED"
                    quality = window.quality_metrics.get('overall', 0.0)
                    message = f"Window {window.index}: {state} (Quality: {quality:.2f}) - Click to toggle"
                    self.status_message.emit(message)
                return
        
        # No window hovered
        if self.current_hover is not None:
            self.status_message.emit("Click on windows to toggle rejection")
            self.current_hover = None


if not HAS_PYQT5:
    class InteractiveHVSRCanvas:
        """Dummy class when PyQt5 not available."""
        def __init__(self, parent=None):
            raise ImportError("PyQt5 is required for GUI functionality")
