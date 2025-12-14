"""
Plot Window Manager for HVSR Pro
=================================

Manages plot display in separate window or embedded mode.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QAction, QMenu
)
from PyQt5.QtCore import Qt, pyqtSignal
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT
)


class PlotWindowManager:
    """
    Manages matplotlib plot display modes (separate vs embedded).
    
    Features:
    - Separate window mode (default): Plot in own window for max space
    - Embedded mode (optional): Plot in main window
    - Easy toggle between modes
    - Connected to layer dock controls
    
    Example:
        >>> manager = PlotWindowManager(main_window)
        >>> manager.show_separate()  # Open plot in separate window
        >>> manager.switch_to_embedded()  # Switch to embedded mode
    """
    
    def __init__(self, parent_window):
        """
        Initialize plot window manager.
        
        Args:
            parent_window: Main window reference
        """
        self.parent = parent_window
        self.mode = 'separate'  # 'separate' or 'embedded'
        
        # Create matplotlib figure
        self.fig = Figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvas(self.fig)
        
        # Panel visibility flags (default: only HVSR)
        self.show_timeline = False
        self.show_quality_stats = False
        
        # Create axes for plots
        self.ax_timeline = None
        self.ax_hvsr = None
        self.ax_stats = None
        self._create_axes()
        
        # Separate window reference
        self.plot_window = None
        
        # Track if window was closed by user
        self._user_closed = False
        
        # View menu actions (set when window created)
        self.action_show_timeline = None
        self.action_show_stats = None
        
        # Store data for replotting with properties
        self.hvsr_result = None
        self.windows = None
        self.data = None
        self.current_properties = None
    
    def _create_axes(self):
        """Create subplot axes based on visibility flags."""
        # Clear existing axes
        self.fig.clear()
        
        # Count how many panels to show
        panels = []
        if self.show_timeline:
            panels.append('timeline')
        panels.append('hvsr')  # HVSR always shown
        if self.show_quality_stats:
            panels.append('stats')
        
        n_panels = len(panels)
        
        # Create subplots
        panel_idx = 1
        for panel_name in panels:
            ax = self.fig.add_subplot(n_panels, 1, panel_idx)
            
            if panel_name == 'timeline':
                self.ax_timeline = ax
                ax.set_title('Window Timeline (Click to Toggle State)')
            elif panel_name == 'hvsr':
                self.ax_hvsr = ax
                ax.set_title('HVSR Curve')
            elif panel_name == 'stats':
                self.ax_stats = ax
                ax.set_title('Window Quality Statistics')
            
            panel_idx += 1
        
        # Set axes to None if not shown
        if not self.show_timeline:
            self.ax_timeline = None
        if not self.show_quality_stats:
            self.ax_stats = None
        
        # Adjust spacing
        self.fig.tight_layout()
    
    def create_separate_window(self):
        """Create standalone plot window."""
        if self.plot_window is not None:
            return self.plot_window
        
        self.plot_window = QMainWindow()
        self.plot_window.setWindowTitle("HVSR Analysis - Plot Window")
        self.plot_window.resize(1200, 900)
        
        # Connect canvas events
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        
        # Manual peak picking state
        self.manual_picking_enabled = False
        self.pick_callback = None  # Callback for manual peak selection
        
        # Handle close event
        self.plot_window.closeEvent = self._on_window_close
        
        # Add menu bar
        menubar = self.plot_window.menuBar()
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Timeline checkbox
        self.action_show_timeline = QAction("Show Timeline", self.plot_window, checkable=True)
        self.action_show_timeline.setChecked(self.show_timeline)
        self.action_show_timeline.setToolTip("Show/hide window timeline panel")
        self.action_show_timeline.triggered.connect(self.toggle_timeline)
        view_menu.addAction(self.action_show_timeline)
        
        # Quality Stats checkbox
        self.action_show_stats = QAction("Show Quality Statistics", self.plot_window, checkable=True)
        self.action_show_stats.setChecked(self.show_quality_stats)
        self.action_show_stats.setToolTip("Show/hide quality statistics panel")
        self.action_show_stats.triggered.connect(self.toggle_quality_stats)
        view_menu.addAction(self.action_show_stats)
        
        view_menu.addSeparator()
        
        # Reset view action
        reset_action = QAction("Reset to Default View", self.plot_window)
        reset_action.setToolTip("Show only HVSR curve (default)")
        reset_action.triggered.connect(self.reset_view)
        view_menu.addAction(reset_action)
        
        # Add matplotlib toolbar
        toolbar = NavigationToolbar2QT(self.canvas, self.plot_window)
        
        # Add custom "Dock" button to toolbar
        dock_action = QAction("Dock Plot", self.plot_window)
        dock_action.setToolTip("Embed plot in main window")
        dock_action.triggered.connect(self.switch_to_embedded)
        toolbar.addAction(dock_action)
        
        # Layout
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbar)
        layout.addWidget(self.canvas)
        self.plot_window.setCentralWidget(central)
        
        return self.plot_window
    
    def _on_window_close(self, event):
        """Handle plot window close event."""
        self._user_closed = True
        event.accept()
    
    def show_separate(self):
        """Show plot in separate window."""
        if self.mode == 'embedded':
            # Remove canvas from parent
            if self.canvas.parent():
                self.canvas.setParent(None)
        
        # Create window if needed
        if self.plot_window is None:
            self.create_separate_window()
        
        # Reset close flag
        self._user_closed = False
        
        # Show window
        self.plot_window.show()
        self.plot_window.raise_()
        self.plot_window.activateWindow()
        self.mode = 'separate'
        
        print("[PlotWindowManager] Showing plot in separate window")
    
    def show_embedded(self):
        """Embed plot in main window."""
        if self.plot_window and self.plot_window.isVisible():
            self.plot_window.hide()
        
        # Remove canvas from plot window
        if self.canvas.parent() == self.plot_window:
            self.canvas.setParent(None)
        
        self.mode = 'embedded'
        print("[PlotWindowManager] Switching to embedded mode")
        
        # Note: Parent window should add canvas to its layout
        # This is done in main_window.py when mode changes
    
    def switch_to_separate(self):
        """Toggle to separate window mode."""
        self.show_separate()
        
        # Update parent button text
        if hasattr(self.parent, 'plot_mode_button'):
            self.parent.plot_mode_button.setText("Dock Plot")
            self.parent.plot_mode_button.setToolTip("Embed plot in main window")
    
    def switch_to_embedded(self):
        """Toggle to embedded mode."""
        self.show_embedded()
        
        # Update parent button text
        if hasattr(self.parent, 'plot_mode_button'):
            self.parent.plot_mode_button.setText("Pop Out Plot")
            self.parent.plot_mode_button.setToolTip("Open plot in separate window")
        
        # Tell parent to embed canvas
        if hasattr(self.parent, 'embed_plot_canvas'):
            self.parent.embed_plot_canvas()
    
    def is_visible(self):
        """Check if plot is currently visible."""
        if self.mode == 'separate':
            return self.plot_window is not None and self.plot_window.isVisible() and not self._user_closed
        else:
            return self.canvas.isVisible()
    
    def raise_window(self):
        """Bring plot window to front."""
        if self.mode == 'separate' and self.plot_window:
            self.plot_window.raise_()
            self.plot_window.activateWindow()
    
    def toggle_timeline(self):
        """Toggle timeline panel visibility."""
        self.show_timeline = not self.show_timeline
        print(f"[PlotWindowManager] Timeline: {'ON' if self.show_timeline else 'OFF'}")
        
        # Update menu action if it exists
        if self.action_show_timeline:
            self.action_show_timeline.setChecked(self.show_timeline)
        
        # Request replot from parent
        self._request_replot()
    
    def toggle_quality_stats(self):
        """Toggle quality statistics panel visibility."""
        self.show_quality_stats = not self.show_quality_stats
        print(f"[PlotWindowManager] Quality Stats: {'ON' if self.show_quality_stats else 'OFF'}")
        
        # Update menu action if it exists
        if self.action_show_stats:
            self.action_show_stats.setChecked(self.show_quality_stats)
        
        # Request replot from parent
        self._request_replot()
    
    def reset_view(self):
        """Reset to default view (only HVSR curve)."""
        self.show_timeline = False
        self.show_quality_stats = False
        print("[PlotWindowManager] View reset to default (HVSR only)")
        
        # Update menu actions
        if self.action_show_timeline:
            self.action_show_timeline.setChecked(False)
        if self.action_show_stats:
            self.action_show_stats.setChecked(False)
        
        # Request replot from parent
        self._request_replot()
    
    def _request_replot(self):
        """Request parent to replot with new layout."""
        if hasattr(self.parent, 'refresh_plot'):
            self.parent.refresh_plot()
        else:
            # Fallback: just recreate axes
            self._create_axes()
            self.canvas.draw_idle()
    
    def clear_all(self):
        """Clear all axes."""
        if self.ax_timeline:
            self.ax_timeline.clear()
            self.ax_timeline.set_title('Window Timeline (Click to Toggle State)')
        
        if self.ax_hvsr:
            self.ax_hvsr.clear()
            self.ax_hvsr.set_title('HVSR Curve')
        
        if self.ax_stats:
            self.ax_stats.clear()
            self.ax_stats.set_title('Window Quality Statistics')
        
        self.fig.canvas.draw_idle()
    
    def get_canvas(self):
        """Get matplotlib canvas."""
        return self.canvas
    
    def get_figure(self):
        """Get matplotlib figure."""
        return self.fig
    
    def get_axes(self):
        """
        Get all axes.
        
        Returns:
            tuple: (ax_timeline, ax_hvsr, ax_stats)
        """
        return (self.ax_timeline, self.ax_hvsr, self.ax_stats)
    
    def add_peak_markers(self, peaks: list, label_style: str = "full"):
        """
        Add peak markers to HVSR plot.
        
        Shows ALL peaks with blue circles initially.
        Only the peak marked as f₀ gets special red circle + yellow annotation.
        
        Args:
            peaks: List of peak dicts with 'frequency', 'amplitude', 'source', 'is_f0'
        """
        if self.ax_hvsr is None:
            print("[PlotWindowManager] Cannot add peaks: HVSR axis not available")
            return
        
        # Clear existing peak markers
        self.clear_peak_markers()
        
        if not peaks:
            self.canvas.draw_idle()
            return
        
        print(f"[PlotWindowManager] Adding {len(peaks)} peak markers to plot")
        
        # Find f0 peak if any
        f0_peak_idx = None
        for i, peak in enumerate(peaks):
            if peak.get('is_f0', False):
                f0_peak_idx = i
                break
        
        # Plot each peak
        for i, peak in enumerate(peaks):
            freq = peak['frequency']
            amp = peak['amplitude']
            is_f0 = peak.get('is_f0', False)
            source = peak.get('source', '')
            
            if is_f0:
                # f₀ peak: Red circle with yellow annotation
                color = 'red'
                size = 140
                edgecolor = 'darkred'
                linewidth = 2.5
                zorder = 200
                
                # Plot marker
                scatter = self.ax_hvsr.scatter(freq, amp, c=color, s=size, 
                                    edgecolors=edgecolor, linewidths=linewidth,
                                    zorder=zorder, marker='o', label='_peak_marker')
                
                # Add annotation with arrow (smart positioning to avoid overlap)
                # Position to the right if possible, otherwise left
                if freq < self.ax_hvsr.get_xlim()[1] / 2:
                    xytext = (freq * 2.5, amp * 1.15)
                else:
                    xytext = (freq * 0.4, amp * 1.15)
                
                annot = self.ax_hvsr.annotate(
                    f'f₀ = {freq:.2f} Hz\nA = {amp:.2f}',
                    xy=(freq, amp),
                    xytext=xytext,
                    fontsize=10,
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.9, edgecolor='red', linewidth=2),
                    arrowprops=dict(arrowstyle='->', lw=2, color='red', connectionstyle='arc3,rad=0.2'),
                    zorder=201
                )
                annot.set_gid('_peak_annotation')
                
            elif 'Manual' in source:
                # Manual peaks: Green circles
                color = 'green'
                size = 100
                edgecolor = 'darkgreen'
                linewidth = 1.8
                zorder = 198
                
                scatter = self.ax_hvsr.scatter(freq, amp, c=color, s=size,
                                    edgecolors=edgecolor, linewidths=linewidth,
                                    zorder=zorder, marker='o', label='_peak_marker')
                
                # Generate label text based on style
                if label_style != "minimal":
                    label_text = self._get_peak_label_text(freq, amp, label_style)
                    txt = self.ax_hvsr.text(
                        freq, amp * 1.12,
                        label_text,
                        fontsize=9,
                        ha='center',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='lightgreen', alpha=0.8, edgecolor='darkgreen'),
                        zorder=198
                    )
                    txt.set_gid('_peak_text')
                
            else:
                # Regular auto-detected peaks: Blue circles
                color = 'blue'
                size = 90
                edgecolor = 'darkblue'
                linewidth = 1.5
                zorder = 197
                
                scatter = self.ax_hvsr.scatter(freq, amp, c=color, s=size,
                                    edgecolors=edgecolor, linewidths=linewidth,
                                    zorder=zorder, marker='o', label='_peak_marker')
                
                # Generate label text based on style
                if label_style != "minimal":
                    label_text = self._get_peak_label_text(freq, amp, label_style)
                    txt = self.ax_hvsr.text(
                        freq, amp * 1.12,
                        label_text,
                        fontsize=8,
                        ha='center',
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='lightblue', alpha=0.75, edgecolor='blue'),
                        zorder=197
                    )
                    txt.set_gid('_peak_text')
        
        # Redraw canvas
        self.canvas.draw_idle()
        print(f"[PlotWindowManager] Peak markers added successfully")
    
    def _get_peak_label_text(self, freq: float, amp: float, style: str) -> str:
        """
        Generate peak label text based on style.
        
        Args:
            freq: Frequency (Hz)
            amp: Amplitude (H/V ratio)
            style: Label style ('full', 'freq_only', 'amp_only', 'minimal')
            
        Returns:
            Label text string
        """
        if style == "full":
            return f'{freq:.2f} Hz'
        elif style == "freq_only":
            return f'{freq:.2f} Hz'
        elif style == "amp_only":
            return f'{amp:.2f}'
        elif style == "minimal":
            return ''  # No label
        else:
            return f'{freq:.2f} Hz'  # Default to frequency
    
    def clear_peak_markers(self):
        """Clear all peak markers from plot."""
        if self.ax_hvsr is None:
            return
        
        # Remove peak-related artists using gid tags and label
        artists_to_remove = []
        for artist in self.ax_hvsr.get_children():
            # Check for our peak markers using label or gid
            if hasattr(artist, 'get_label') and artist.get_label() == '_peak_marker':
                artists_to_remove.append(artist)
            elif hasattr(artist, 'get_gid'):
                gid = artist.get_gid()
                if gid in ['_peak_annotation', '_peak_text']:
                    artists_to_remove.append(artist)
        
        for artist in artists_to_remove:
            artist.remove()
        
        if artists_to_remove:
            print(f"[PlotWindowManager] Removed {len(artists_to_remove)} peak markers")
            self.canvas.draw_idle()
    
    def enable_manual_picking(self, callback):
        """
        Enable manual peak picking mode.
        
        Args:
            callback: Function to call with (frequency, amplitude) when user clicks
        """
        self.manual_picking_enabled = True
        self.pick_callback = callback
        
        # Change cursor to crosshair
        if self.plot_window:
            self.plot_window.setCursor(Qt.CrossCursor)
        
        print("[PlotWindowManager] Manual peak picking ENABLED - Click on HVSR curve to add peak")
    
    def disable_manual_picking(self):
        """Disable manual peak picking mode."""
        self.manual_picking_enabled = False
        self.pick_callback = None
        
        # Reset cursor
        if self.plot_window:
            self.plot_window.setCursor(Qt.ArrowCursor)
        
        print("[PlotWindowManager] Manual peak picking DISABLED")
    
    def on_canvas_click(self, event):
        """
        Handle canvas click events for manual peak picking.
        
        Args:
            event: Matplotlib mouse event
        """
        # Only process if manual picking is enabled and click is on HVSR axis
        if not self.manual_picking_enabled or event.inaxes != self.ax_hvsr:
            return
        
        # Only process left mouse button
        if event.button != 1:
            return
        
        # Get click coordinates
        freq_clicked = event.xdata
        amp_clicked = event.ydata
        
        if freq_clicked is None or amp_clicked is None:
            return
        
        print(f"[PlotWindowManager] Click detected: f={freq_clicked:.2f} Hz, A={amp_clicked:.2f}")
        
        # Call callback if set
        if self.pick_callback:
            self.pick_callback(freq_clicked, amp_clicked)
    
    def set_plot_data(self, hvsr_result, windows, data):
        """
        Store data for property-based replotting.
        
        Args:
            hvsr_result: HVSRResult object
            windows: WindowCollection object
            data: SeismicData object
        """
        self.hvsr_result = hvsr_result
        self.windows = windows
        self.data = data
    
    def apply_properties(self, properties):
        """
        Apply plot properties and replot.
        
        Args:
            properties: PlotProperties object from properties_dock
        """
        if self.hvsr_result is None:
            print("[PlotWindowManager] No data to plot")
            return
        
        self.current_properties = properties
        
        # Trigger parent to replot with properties
        if hasattr(self.parent, 'replot_with_properties'):
            self.parent.replot_with_properties(properties)
    
    def calculate_y_limits(self, properties, hvsr_result):
        """
        Calculate Y-axis limits based on properties.
        
        Args:
            properties: PlotProperties object
            hvsr_result: HVSRResult object
            
        Returns:
            tuple: (y_min, y_max)
        """
        import numpy as np
        
        if properties.y_mode == "auto":
            # Auto: based on all data
            all_vals = []
            all_vals.extend(hvsr_result.mean_hvsr)
            if hvsr_result.std_hvsr is not None:
                all_vals.extend(hvsr_result.mean_hvsr + hvsr_result.std_hvsr)
            y_max = np.max(all_vals) * 1.1
            return (0.0, y_max)
        
        elif properties.y_mode == "mean_std":
            # Mean + N*Std
            mean_max = np.max(hvsr_result.mean_hvsr)
            if hvsr_result.std_hvsr is not None:
                std_max = np.max(hvsr_result.std_hvsr)
                y_max = mean_max + properties.y_std_multiplier * std_max
            else:
                y_max = mean_max * 1.2
            return (0.0, max(y_max, 1.0))
        
        elif properties.y_mode == "percentile":
            # Percentile-based
            all_vals = []
            all_vals.extend(hvsr_result.mean_hvsr)
            if hvsr_result.std_hvsr is not None:
                all_vals.extend(hvsr_result.mean_hvsr + hvsr_result.std_hvsr)
            y_max = np.percentile(all_vals, properties.y_percentile)
            return (0.0, max(y_max, 1.0))
        
        elif properties.y_mode == "manual":
            # Manual
            return (properties.y_min, properties.y_max)
        
        else:
            # Default
            return (0.0, 10.0)
    
    def get_background_color(self, properties):
        """Get background color from properties."""
        colors = {
            "white": "#FFFFFF",
            "light_gray": "#F5F5F5",
            "gray": "#E0E0E0"
        }
        return colors.get(properties.background_color, "#FFFFFF")
