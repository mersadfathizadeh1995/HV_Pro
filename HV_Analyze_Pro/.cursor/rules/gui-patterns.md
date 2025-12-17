# HVSR Pro - GUI Component Patterns

## Widget Structure

- Inherit from appropriate Qt base class
- Use `init_ui()` method for layout setup
- Connect signals in separate `_connect_signals()` method
- Use `_` prefix for internal helper methods

```python
class MyWidget(QWidget):
    """Description of widget purpose."""
    
    # Signals declared at class level
    value_changed = pyqtSignal(float)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_state()
        self._init_ui()
        self._connect_signals()
    
    def _init_state(self):
        """Initialize internal state variables."""
        self._current_value = 0.0
    
    def _init_ui(self):
        """Create and arrange widgets."""
        layout = QVBoxLayout(self)
        self.spin = QDoubleSpinBox()
        layout.addWidget(self.spin)
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.spin.valueChanged.connect(self._on_value_changed)
    
    def _on_value_changed(self, value):
        """Handle spin box value change."""
        self._current_value = value
        self.value_changed.emit(value)
```

## Collapsible Sections

Use `CollapsibleSection` from `gui/components/` for grouping related controls:

```python
from hvsr_pro.gui.components import CollapsibleSection

section = CollapsibleSection("Section Title")
content_layout = QVBoxLayout()
content_layout.addWidget(QLabel("Content here"))
section.setContentLayout(content_layout)
```

## Color Pickers

Use `ColorPickerButton` from `gui/components/`:

```python
from hvsr_pro.gui.components import ColorPickerButton

color_btn = ColorPickerButton(initial_color="#FF0000")
color_btn.color_changed.connect(self._on_color_changed)
```

## Settings Panels

Extract reusable settings into panel classes in `gui/panels/`:

```python
class MySettingsPanel(QWidget):
    """Panel for grouped settings."""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def get_settings(self) -> dict:
        """Return current settings as dictionary."""
        return {
            'param1': self.spin1.value(),
            'param2': self.check.isChecked(),
        }
    
    def set_settings(self, settings: dict):
        """Apply settings from dictionary."""
        if 'param1' in settings:
            self.spin1.setValue(settings['param1'])
```

## Worker Threads

Use QThread for long-running operations:

```python
from PyQt5.QtCore import QThread, pyqtSignal

class ProcessingWorker(QThread):
    """Background worker for processing."""
    
    progress = pyqtSignal(int, str)  # (percentage, message)
    finished = pyqtSignal(object)    # result
    error = pyqtSignal(str)          # error message
    
    def __init__(self, data, settings):
        super().__init__()
        self.data = data
        self.settings = settings
    
    def run(self):
        try:
            self.progress.emit(0, "Starting...")
            result = self._process()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

## Dock Widgets

Structure for dockable panels:

```python
class MyDock(QDockWidget):
    """Dockable panel for X functionality."""
    
    def __init__(self, parent=None):
        super().__init__("Panel Title", parent)
        self.setObjectName("MyDock")  # For state saving
        self._create_ui()
    
    def _create_ui(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        # Add controls...
        self.setWidget(widget)
    
    def set_data(self, data):
        """Update panel with new data."""
        pass
```

## File Dialog Patterns

Always use the working directory when available:

```python
def _get_default_dir(self) -> str:
    """Get default directory for file dialogs."""
    if hasattr(self, 'working_directory') and self.working_directory:
        return self.working_directory
    return str(Path.home())

def _browse_file(self):
    file_path, _ = QFileDialog.getOpenFileName(
        self,
        "Select File",
        self._get_default_dir(),
        "All Files (*.*)"
    )
    return file_path
```

## Signal Naming

- Use past tense for events that happened: `value_changed`, `file_loaded`
- Use present tense for requests: `export_requested`, `process_requested`
- Be specific: `frequency_range_changed` not `changed`

## Layout Best Practices

- Use `QSplitter` for resizable sections
- Use `QScrollArea` for panels that may overflow
- Set margins and spacing consistently: `layout.setContentsMargins(5, 5, 5, 5)`
- Use `addStretch()` to push content to top/left

## Styling

- Prefer stylesheets over palette changes
- Use consistent color variables
- Define styles in a central location when possible

```python
BUTTON_STYLE = """
    QPushButton {
        background-color: #4CAF50;
        color: white;
        border-radius: 4px;
        padding: 8px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #45a049;
    }
    QPushButton:disabled {
        background-color: #cccccc;
    }
"""
```

