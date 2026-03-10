# BEDROCK_MAPPING GUI STYLE PATTERNS - COMPLETE REFERENCE
# =========================================================

## 1. COLLAPSIBLE GROUP BOX - FULL IMPLEMENTATION

Location: D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro\packages\bedrock_mapping\widgets\collapsible_group.py

`python
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton, QLabel,
    QSizePolicy, QFrame
)
from PyQt5.QtCore import Qt, QPropertyAnimation, QParallelAnimationGroup


class CollapsibleGroupBox(QWidget):
    """A collapsible container with an animated toggle header.

    Usage::
        group = CollapsibleGroupBox("📊 Settings", collapsed=True)
        content = QVBoxLayout()
        content.addWidget(QLabel("hello"))
        group.setContentLayout(content)
    """

    def __init__(self, title: str = "", collapsed: bool = False, parent=None):
        super().__init__(parent)

        # Toggle button with NO BORDER (CSS removed border)
        self._toggle = QToolButton(self)
        self._toggle.setStyleSheet("QToolButton { border: none; }")
        self._toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._toggle.setText(title)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(not collapsed)
        self._toggle.setArrowType(Qt.DownArrow if not collapsed else Qt.RightArrow)
        self._toggle.toggled.connect(self._on_toggled)
        self._toggle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Separator line
        self._line = QFrame(self)
        self._line.setFrameShape(QFrame.HLine)
        self._line.setFrameShadow(QFrame.Sunken)

        # Content area
        self._content = QWidget(self)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(8, 0, 0, 4)  # LEFT INDENT PATTERN
        self._content.setVisible(not collapsed)

        # Main layout - ZERO SPACING AND MARGINS
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._toggle)
        main_layout.addWidget(self._line)
        main_layout.addWidget(self._content)

    def _on_toggled(self, checked: bool):
        self._toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
        self._content.setVisible(checked)

    def setContentLayout(self, layout):
        """Set the content layout for the collapsible area."""
        old = self._content.layout()
        if old is not None:
            while old.count():
                old.takeAt(0)
        QWidget().setLayout(self._content.layout())
        self._content.setLayout(layout)
        layout.setContentsMargins(8, 4, 4, 4)  # CONTENT PADDING

    def addWidget(self, widget):
        """Convenience: add a widget to the content area."""
        self._content_layout.addWidget(widget)

    def addLayout(self, layout):
        """Convenience: add a sub-layout to the content area."""
        self._content_layout.addLayout(layout)

    def setCollapsed(self, collapsed: bool):
        """Programmatically set collapsed state."""
        self._toggle.setChecked(not collapsed)

    def isCollapsed(self) -> bool:
        return not self._toggle.isChecked()

    def title(self) -> str:
        return self._toggle.text()

    def setTitle(self, title: str):
        self._toggle.setText(title)
`

## 2. CSS/STYLESHEET PATTERNS USED

Only THREE types of stylesheets in the codebase:

### 2.1 Toggle Button (Collapsible Header)
`python
self._toggle.setStyleSheet("QToolButton { border: none; }")
`

### 2.2 Info Labels (Help text)
`python
self.surface_mapping_label.setStyleSheet("color:#555; font-size:11px;")
self.bedrock_mapping_label.setStyleSheet("color:#555; font-size:11px;")
self.format_info_label.setStyleSheet("color: #555; font-size: 11px;")
stats_lbl.setStyleSheet("color:#777; font-size:10px;")
`

COLORS: #555 or #777 (dim gray)
SIZES: 10px or 11px (small)

### 2.3 No Global Stylesheet
- Relies on PyQt5 system defaults
- Only targeted widget-specific CSS applied

## 3. EMOJI PREFIXES IN TITLES

**Tab titles (window level):**
- 🗺️ Map
- 📊 2D Plot
- 📈 3D Plot
- 🔺 3D View

**Control panel tabs:**
- 📁 Data
- 📐 Interpolation
- 📍 Stations
- 📏 Depth

**Export sections:**
- 🌍 Google Earth
- 🖼️ Image Export
- 🌐 Interactive HTML

**Data groups:**
- 📁 Surface Elevation Data
- 🪨 Bedrock Elevation Data

**Action buttons:**
- ✅ Apply Surface Data
- 💾 Save Image
- 🌍 Export to Google Earth

**Usage example:**
`python
ge_main = CollapsibleGroupBox("🌍 Google Earth")
img_group = CollapsibleGroupBox("🖼️ Image Export")
btn_ge = QPushButton("🌍 Export to Google Earth")
self.control_tabs.addTab(self.data_loader, "📁 Data")
`

## 4. TIGHT MARGINS PATTERNS

### Main Window Central Layout
`python
central = QWidget()
self.setCentralWidget(central)
layout = QHBoxLayout(central)
layout.setContentsMargins(4, 4, 4, 4)  # VERY TIGHT: 4 pixels
`

### Standard Widget Layouts
`python
layout = QVBoxLayout(self)
layout.setContentsMargins(6, 6, 6, 6)  # STANDARD: 6 pixels all sides
`

### Collapsible Content Area (left indent for visual nesting)
`python
self._content_layout.setContentsMargins(8, 0, 0, 4)  # LEFT=8, others=0 or 4
# When setting content:
layout.setContentsMargins(8, 4, 4, 4)  # LEFT=8, TOP=4, RIGHT=4, BOTTOM=4
`

### Collapsible Main Structure (zero margins)
`python
main_layout = QVBoxLayout(self)
main_layout.setSpacing(0)  # NO SPACE BETWEEN ITEMS
main_layout.setContentsMargins(0, 0, 0, 0)  # NO MARGINS
`

### Export Panels with Scroll
`python
# Container layout (content area)
layout = QVBoxLayout(container)
layout.setContentsMargins(6, 6, 6, 6)

# Outer scroll wrapper (zero margins for seamless look)
outer = QVBoxLayout(self)
outer.setContentsMargins(0, 0, 0, 0)
outer.addWidget(scroll)
`

### Nested Layout Indentation
`python
wl.setContentsMargins(indent, 0, 0, 0)  # Common: 12-20px left indent only
`

## 5. SPLITTER STRETCH PATTERNS

`python
# Create main horizontal splitter
self.splitter = QSplitter(Qt.Horizontal)
layout.addWidget(self.splitter)

# LEFT: Control panel (fixed width, doesn't stretch)
self.control_tabs = QTabWidget()
self.control_tabs.setMinimumWidth(350)   # Won't go below 350
self.control_tabs.setMaximumWidth(550)   # Won't go above 550
self.splitter.addWidget(self.control_tabs)

# RIGHT: View area (stretches to fill)
self.view_tabs = QTabWidget()
self.splitter.addWidget(self.view_tabs)

# KEY PATTERN: Stretch factors
self.splitter.setStretchFactor(0, 0)  # Left: stretch factor 0 (fixed)
self.splitter.setStretchFactor(1, 1)  # Right: stretch factor 1 (fills)
self.splitter.setSizes([400, 1000])   # Initial sizes

Result: Left stays ~400px, right expands with window
`

## 6. QGROUPBOX CARD STYLING

Standard QGroupBox (uses PyQt5 defaults, NO custom CSS):

`python
surf_group = QGroupBox("📁 Surface Elevation Data")
surf_lay = QVBoxLayout(surf_group)

# Add content
row1 = QHBoxLayout()
self.surface_file_label = QLabel("No file loaded")
self.surface_file_label.setWordWrap(True)
btn_surf = QPushButton("Browse…")
row1.addWidget(self.surface_file_label, 1)  # stretch=1 (expands)
row1.addWidget(btn_surf)                     # stretch=0 (fixed)
surf_lay.addLayout(row1)

layout.addWidget(surf_group)
`

**Features:**
- Bold title in system font
- Default gray border around group
- Standard PyQt5 styling (no custom CSS)
- Uses emoji prefixes in title

## 7. SCROLL AREA PATTERN (Export panels)

`python
from PyQt5.QtWidgets import QScrollArea, QFrame

scroll = QScrollArea(self)
scroll.setWidgetResizable(True)
scroll.setFrameShape(QFrame.NoFrame)  # KEY: removes frame for clean look

container = QWidget()
layout = QVBoxLayout(container)
layout.setContentsMargins(6, 6, 6, 6)

# Build content in container
ge_main = CollapsibleGroupBox("🌍 Google Earth")
ge_lay = QVBoxLayout()
grp, refs = build_presets_section()
ge_lay.addWidget(grp)
# ... more sections ...
ge_main.setContentLayout(ge_lay)
layout.addWidget(ge_main)

btn_ge = QPushButton("🌍 Export to Google Earth")
layout.addWidget(btn_ge)

layout.addStretch()  # Push content to top
scroll.setWidget(container)

# Outer wrapper with zero margins
outer = QVBoxLayout(self)
outer.setContentsMargins(0, 0, 0, 0)
outer.addWidget(scroll)
`

Result: Clean, frameless scroll area blending with content

## 8. COMPLETE WINDOW ARCHITECTURE

Location: D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro\packages\bedrock_mapping\bedrock_window.py

`python
class BedrockMappingWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HVSR Pro — 3D Bedrock Mapping")
        self.resize(1400, 900)
        self.setMinimumSize(1000, 650)
        
        self._build_menu_bar()
        self._build_ui()
        self._build_status_bar()

    def _build_ui(self):
        # Central widget with VERY TIGHT margins
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(4, 4, 4, 4)

        # Main splitter
        self.splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.splitter)

        # LEFT PANEL: Tabbed controls
        self.control_tabs = QTabWidget()
        self.control_tabs.setMinimumWidth(350)
        self.control_tabs.setMaximumWidth(550)
        
        self.data_loader = DataLoaderWidget(self.state, self)
        self.interp_panel = InterpolationWidget(self.state, self)
        self.station_mgr = StationManagerWidget(self.state, self)
        self.depth_calc = DepthCalcWidget(self.state, self)

        self.control_tabs.addTab(self.data_loader, "📁 Data")
        self.control_tabs.addTab(self.interp_panel, "📐 Interpolation")
        self.control_tabs.addTab(self.station_mgr, "📍 Stations")
        self.control_tabs.addTab(self.depth_calc, "📏 Depth")

        self.splitter.addWidget(self.control_tabs)

        # RIGHT PANEL: View tabs
        self.view_tabs = QTabWidget()
        
        self.map_widget = MapWidget(self.state, self)
        self.view_2d = View2DWidget(self.state, self)
        self.view_3d_plotly = View3DPlotlyWidget(self.state, self)
        self.view_3d = View3DWidget(self.state, self)

        self.view_tabs.addTab(self.map_widget, "🗺️ Map")
        self.view_tabs.addTab(self.view_2d, "📊 2D Plot")
        self.view_tabs.addTab(self.view_3d_plotly, "📈 3D Plot")
        self.view_tabs.addTab(self.view_3d, "🔺 3D View")

        self.splitter.addWidget(self.view_tabs)

        # Splitter configuration
        self.splitter.setStretchFactor(0, 0)  # Left: fixed width
        self.splitter.setStretchFactor(1, 1)  # Right: expands
        self.splitter.setSizes([400, 1000])

        # RIGHT DOCK: Layers and export panels
        self.layer_dock = QDockWidget("Layers: Map", self)
        self.layer_dock.setAllowedAreas(
            Qt.RightDockWidgetArea | Qt.LeftDockWidgetArea)

        self.right_tabs = QTabWidget()
        self.layer_panel = LayerPanelWidget(self.state, self)
        self.right_tabs.addTab(self.layer_panel, "Layers")

        # Export stack (per-tab export panels)
        self.export_stack = QStackedWidget()
        self.export_map = ExportMapWidget(self.state, self)
        self.export_2d = Export2DWidget(self.state, self.view_2d, self)
        self.export_3d_plotly = Export3DPlotlyWidget(self.state, self.view_3d_plotly, self)
        self.export_3d_view = Export3DViewWidget(self.state, self.view_3d, self)
        
        self.export_stack.addWidget(self.export_map)       # 0 → map
        self.export_stack.addWidget(self.export_2d)        # 1 → 2d
        self.export_stack.addWidget(self.export_3d_plotly) # 2 → 3d_plotly
        self.export_stack.addWidget(self.export_3d_view)   # 3 → 3d
        self.right_tabs.addTab(self.export_stack, "Export")

        self.layer_dock.setWidget(self.right_tabs)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layer_dock)
`

## 9. EXPORT PANEL USAGE EXAMPLE

Location: D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro\packages\bedrock_mapping\widgets\export_2d.py

`python
class Export2DWidget(QWidget):
    def __init__(self, state, view_2d_ref, parent=None):
        super().__init__(parent)
        self.state = state
        self._view_2d = view_2d_ref
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # IMAGE EXPORT SECTION
        img_group = CollapsibleGroupBox("🖼️ Image Export")
        ig_lay = QVBoxLayout()

        # Format row
        row_fmt = QHBoxLayout()
        row_fmt.addWidget(QLabel("Format:"))
        self.fmt_combo = QComboBox()
        self.fmt_combo.addItems(["PNG", "SVG", "PDF"])
        row_fmt.addWidget(self.fmt_combo)
        ig_lay.addLayout(row_fmt)

        # DPI row
        row_dpi = QHBoxLayout()
        row_dpi.addWidget(QLabel("DPI:"))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(200)
        self.dpi_spin.setSingleStep(50)
        row_dpi.addWidget(self.dpi_spin)
        ig_lay.addLayout(row_dpi)

        # Action button
        btn_img = QPushButton("💾 Save Image")
        btn_img.clicked.connect(self._export_image)
        ig_lay.addWidget(btn_img)

        img_group.setContentLayout(ig_lay)
        layout.addWidget(img_group)

        # HTML EXPORT SECTION
        html_group = CollapsibleGroupBox("🌐 Interactive HTML")
        hg_lay = QVBoxLayout()
        hg_lay.addWidget(QLabel("Full interactive Plotly chart"))
        btn_html = QPushButton("💾 Save HTML")
        btn_html.clicked.connect(self._export_html)
        hg_lay.addWidget(btn_html)
        html_group.setContentLayout(hg_lay)
        layout.addWidget(html_group)

        layout.addStretch()  # Push content to top
`

## 10. DATA LOADER WIDGET EXAMPLE

Location: D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro\packages\bedrock_mapping\widgets\data_loader.py

`python
class DataLoaderWidget(QWidget):
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        # SURFACE DATA GROUP
        surf_group = QGroupBox("📁 Surface Elevation Data")
        surf_lay = QVBoxLayout(surf_group)

        # File selection row
        row1 = QHBoxLayout()
        self.surface_file_label = QLabel("No file loaded")
        self.surface_file_label.setWordWrap(True)
        btn_surf = QPushButton("Browse…")
        btn_surf.clicked.connect(self.load_surface)
        row1.addWidget(self.surface_file_label, 1)
        row1.addWidget(btn_surf)
        surf_lay.addLayout(row1)

        # Mapping info (small gray text)
        self.surface_mapping_label = QLabel("")
        self.surface_mapping_label.setStyleSheet("color:#555; font-size:11px;")
        self.surface_mapping_label.setWordWrap(True)
        surf_lay.addWidget(self.surface_mapping_label)

        # Coordinate system selector
        self.surface_crs = CoordinateSystemSelector()
        surf_lay.addWidget(self.surface_crs)

        # Unit selection
        unit_row = QHBoxLayout()
        unit_row.addWidget(QLabel("Unit:"))
        self.surface_unit_combo = QComboBox()
        self.surface_unit_combo.addItems(["meters", "feet"])
        unit_row.addWidget(self.surface_unit_combo)
        unit_row.addStretch()
        surf_lay.addLayout(unit_row)

        # Apply button
        self.btn_apply_surface = QPushButton("✅ Apply Surface Data")
        self.btn_apply_surface.setEnabled(False)
        self.btn_apply_surface.clicked.connect(self._apply_surface)
        surf_lay.addWidget(self.btn_apply_surface)

        layout.addWidget(surf_group)

        # BEDROCK DATA GROUP (similar structure)
        bed_group = QGroupBox("🪨 Bedrock Elevation Data")
        # ... similar to surface ...
        layout.addWidget(bed_group)

        # PREVIEW GROUP
        preview_group = QGroupBox("Preview (first 10 rows)")
        preview_lay = QVBoxLayout(preview_group)
        self.format_info_label = QLabel("")
        self.format_info_label.setStyleSheet("color: #555; font-size: 11px;")
        preview_lay.addWidget(self.format_info_label)
        self.preview_table = QTableWidget()
        self.preview_table.setMaximumHeight(180)
        self.preview_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        preview_lay.addWidget(self.preview_table)
        layout.addWidget(preview_group)

        layout.addStretch()
`

---

## QUICK REFERENCE: KEY NUMBERS

Margins:
- Main window: 4px
- Widgets: 6px
- Collapsible content: 8 (left), 0 or 4 (other)
- Scroll wrappers: 0px

Splitter:
- Left panel min: 350px
- Left panel max: 550px
- Stretch: (0, 1) = left fixed, right expands

Font sizes (helpers):
- Info labels: 10px or 11px

Colors (helpers):
- Info text: #555 or #777

---

## FILES REFERENCED

1. CollapsibleGroupBox class:
   D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro\packages\bedrock_mapping\widgets\collapsible_group.py

2. Main window architecture:
   D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro\packages\bedrock_mapping\bedrock_window.py

3. Export panel example:
   D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro\packages\bedrock_mapping\widgets\export_2d.py
   D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro\packages\bedrock_mapping\widgets\export_map.py

4. Data loader example:
   D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro\packages\bedrock_mapping\widgets\data_loader.py

