# Refactoring Rules for HVSR Pro

## CRITICAL: Proactive Modularity Rules

### Rule 0: Detect Code That Needs Refactoring DURING Development

**Check these thresholds when writing new code:**

| Metric | Warning | Must Refactor |
|--------|---------|---------------|
| Single file lines | >200 lines | >300 lines |
| Single function lines | >30 lines | >50 lines |
| Single class methods | >10 methods | >15 methods |
| Function parameters | >5 params | >7 params |
| Nested conditionals | >2 levels | >3 levels |
| Imports from same module | >5 imports | Consider splitting |

**Red Flags (Stop and Refactor Immediately):**
1. ❌ Method has `and` in name (e.g., `load_and_process`) → Split into two methods
2. ❌ Class does more than one thing → Extract separate class
3. ❌ Function returns multiple unrelated values → Create dataclass
4. ❌ Copy-pasting code between files → Create shared utility
5. ❌ UI code mixed with business logic → Extract controller/service
6. ❌ Hard-coded values → Extract to config/constants
7. ❌ Callback hell (>2 nested callbacks) → Use signals or composition

**Modular Design Checklist (Before Adding New Feature):**
```
□ Is this a new file or adding to existing?
  - New file: Does it belong in existing module or need new one?
  - Existing: Will it push file over 300 lines? → Plan split first

□ Does the feature need GUI?
  - YES: Create processing logic in core/ FIRST, then GUI in gui/
  - GUI should only call core functions, never contain processing logic

□ Does feature have settings/configuration?
  - Create dataclass in config/schemas.py
  - Create GUI panel in gui/panels/ if needed

□ Does feature produce output/export?
  - Create exporter in appropriate exporters/ folder
  - Keep export logic separate from UI

□ Will this code be useful elsewhere (API, CLI)?
  - Write core logic as standalone function
  - GUI and CLI both call the same core function
```

**The Golden Rule:** If you're adding >100 lines to any single file, STOP and plan how to split it first.

---

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
