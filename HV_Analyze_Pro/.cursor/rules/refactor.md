# Refactoring Rules for HVSR Pro

## Import Management

### Rule 1: Update All Import References
When moving/renaming a module, search for imports in:
```
grep -r "from hvsr_pro.gui.old_module import" hvsr_pro/
grep -r "import hvsr_pro.gui.old_module" hvsr_pro/
```
Update: `__init__.py` files at all levels (package, subpackage, parent).

### Rule 2: Backward Compatibility Aliases
When renaming a class, add alias in `__init__.py`:
```python
from .new_module import NewClassName
OldClassName = NewClassName  # Backward compatibility
```

### Rule 3: Check These Files First
Before modifying any module, check for imports in:
- `hvsr_pro/__init__.py`
- `hvsr_pro/gui/__init__.py`
- `hvsr_pro/gui/main_window.py`
- Parent package's `__init__.py`

## File Organization

### Rule 4: Dock Package Structure
When creating/refactoring a dock, follow this pattern:
```
docks/dock_name/
├── __init__.py           # Export main class + alias
├── dock_name.py          # Main widget (max ~300 lines)
├── sections/             # If >2 sections
│   ├── __init__.py
│   └── *_section.py      # Each section ~50-100 lines
├── dialogs/              # If has dialogs
└── exporters/            # If has export logic
```

### Rule 5: Dialog Package Structure
When creating/refactoring a dialog with multiple components:
```
dialogs/dialog_name/
├── __init__.py
├── dialog.py             # Main dialog
├── panels/               # Embedded panels
└── tabs/                 # If has tabs
```

### Rule 6: Section Classes
Section classes must:
- Extend `CollapsibleSection` (from `hvsr_pro.gui.components`)
- Emit signals for changes
- Provide `get_*()` and `set_*()` methods
- Be ~50-100 lines

## Code Patterns

### Rule 7: PyQt5 Optional Guard
All GUI modules must handle missing PyQt5:
```python
try:
    from PyQt5.QtWidgets import ...
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    class ActualClass(...):
        ...
else:
    class ActualClass:
        def __init__(self, *args, **kwargs):
            pass
```

### Rule 8: Processing Functions Should Be Pure
Export functions in `exporters/` should:
- Not import PyQt5
- Take data as parameters
- Return data or write to file
- Be testable without GUI

### Rule 9: Signal Naming
- Section signals: `{option}_changed` (e.g., `theme_changed`)
- Export signals: `export_{type}_requested` (e.g., `export_csv_requested`)
- Action signals: `{action}_requested` (e.g., `apply_requested`)

## Testing Imports

### Rule 10: Verify After Refactoring
Always run these tests after moving files:
```python
# Test direct import
from hvsr_pro.gui.docks.{package} import {MainClass}

# Test from parent
from hvsr_pro.gui.docks import {MainClass}

# Test full GUI import
from hvsr_pro.gui import HVSRMainWindow, HAS_GUI
assert HAS_GUI == True
```

## Common Mistakes to Avoid

1. **Forgetting `__init__.py` updates** - Always update exports
2. **Breaking backward compatibility** - Always add aliases
3. **Circular imports** - Import inside methods if needed
4. **Missing dummy classes** - Always provide fallback when PyQt5 unavailable
5. **Large single files** - Split at 300+ lines using sections pattern
6. **Temporary file names** - NEVER create files with `_new`, `_old`, `_temp`, `_backup` suffixes in the active codebase. Instead:
   - Move old file to `old/` folder first
   - Create new file with the proper final name directly
   - Delete or archive the old file after verification

## Quick Reference: Import Chain

```
hvsr_pro/__init__.py
    └── hvsr_pro/gui/__init__.py
            └── hvsr_pro/gui/docks/__init__.py
                    └── hvsr_pro/gui/docks/{package}/__init__.py
```

Each level must export what the parent needs to import.
