# BEDROCK_MAPPING GUI PATTERNS - QUICK INDEX
==============================================

## 📍 Files & Locations

### Main Reference Document
**File:** D:\Research\Narm_Afzar\Git_hub\HV_Pro\GUI_STYLE_REFERENCE.md
- 10 comprehensive sections
- Complete code implementations  
- All 10 copy-paste snippets
- Quick reference numbers

### Source Files (Bedrock Mapping)

1. **CollapsibleGroupBox (Complete Class)**
   - File: hvsr_pro\packages\bedrock_mapping\widgets\collapsible_group.py
   - Lines: 17-103
   - Size: ~87 lines
   - Status: Ready to copy

2. **Main Window Architecture**
   - File: hvsr_pro\packages\bedrock_mapping\bedrock_window.py
   - Lines: 122-211
   - Shows: Splitter, tabs, dock widgets, layout margins

3. **Export Map Panel (Real Example)**
   - File: hvsr_pro\packages\bedrock_mapping\widgets\export_map.py
   - Lines: 55-127
   - Shows: ScrollArea, CollapsibleGroupBox usage, margins

4. **Export 2D Panel (Real Example)**
   - File: hvsr_pro\packages\bedrock_mapping\widgets\export_2d.py
   - Lines: 20-70
   - Shows: CollapsibleGroupBox with content layout

5. **Data Loader Widget (Real Example)**
   - File: hvsr_pro\packages\bedrock_mapping\widgets\data_loader.py
   - Lines: 100-192
   - Shows: QGroupBox, margins, info labels, CSS

---

## 🎯 QUICK LOOKUP BY TOPIC

### Margin Patterns
**Reference Document:** Section 4 - "Tight Margins Patterns"
- Main window: 4px
- Widgets: 6px
- Collapsible content: 8px left
- Scroll wrappers: 0px

### Emoji Usage
**Reference Document:** Section 3 - "Emoji Usage Guide"
`
Views:        🗺️ 📊 📈 🔺
Data:         📁 🪨 📐 📍 📏
Export:       🌍 🖼️ 🌐
Actions:      ✅ 💾
Tools:        ⚙️
`

### Splitter Configuration
**Reference Document:** Section 5 - "Splitter Stretch Patterns"
`python
splitter.setStretchFactor(0, 0)  # Left: fixed
splitter.setStretchFactor(1, 1)  # Right: expands
splitter.setSizes([400, 1000])
`

### CollapsibleGroupBox Usage
**Reference Document:** Section 1 - "Collapsible Group Box - Full Implementation"
**Ready-to-Copy Snippet:** #1, #8, #10

### CSS Stylesheets
**Reference Document:** Section 2 - "CSS/Stylesheet Patterns"
`
QToolButton { border: none; }
color:#555; font-size:11px;  // info labels
`

### ScrollArea Pattern
**Reference Document:** Section 7 - "Scroll Area Pattern"
**Ready-to-Copy Snippet:** #4

### Window Architecture
**Reference Document:** Section 8 - "Complete Window Architecture"
**Ready-to-Copy Snippet:** #2

---

## 📋 QUICK COPY SNIPPETS

All in Reference Document (under "DIRECT COPY SNIPPETS"):

1. **CollapsibleGroupBox usage** - Import and basic usage
2. **Main window layout** - Splitter, tabs, margins
3. **Standard widget layout** - 6px margins pattern
4. **Export panel with scroll** - Frameless scroll area
5. **Info labels** - Gray #555, 11px font
6. **Emoji tab titles** - All standard tabs
7. **Emoji action buttons** - All button styles
8. **Collapsible factory pattern** - Modular sections
9. **Nested indented layouts** - 20px left indent
10. **Complete minimal template** - Full working widget

---

## 🔧 IMPLEMENTATION CHECKLIST

When porting to hvstrip-progressive:

### Phase 1: Core Widget
- [ ] Copy CollapsibleGroupBox class
- [ ] Import all dependencies
- [ ] Test toggle/expand functionality

### Phase 2: Layout Structure  
- [ ] Main window: 4px margins
- [ ] Widgets: 6px margins
- [ ] Splitter: (0,1) stretch factors
- [ ] Collapsible content: 8px left indent

### Phase 3: Styling
- [ ] Add emoji to all tab titles
- [ ] Apply CSS to toggle buttons
- [ ] Apply CSS to info labels (#555, 11px)
- [ ] Remove unnecessary borders

### Phase 4: ScrollAreas
- [ ] Wrap export panels with QScrollArea
- [ ] setFrameShape(QFrame.NoFrame)
- [ ] Container margins: 6px
- [ ] Outer margins: 0px

### Phase 5: Polish
- [ ] Test window resize
- [ ] Verify splitter drag
- [ ] Check emoji rendering
- [ ] Validate margins

---

## 💾 COPY-PASTE READY CODE

### Minimal Example (Complete Widget)

`python
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox
)
from collapsible_group import CollapsibleGroupBox

class MyWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        
        # Collapsible section
        group = CollapsibleGroupBox("📊 Settings")
        content = QVBoxLayout()
        
        row = QHBoxLayout()
        row.addWidget(QLabel("Format:"))
        row.addWidget(QComboBox())
        row.addStretch()
        content.addLayout(row)
        
        btn = QPushButton("✅ Apply")
        content.addWidget(btn)
        
        group.setContentLayout(content)
        layout.addWidget(group)
        
        # Info label
        info = QLabel("Ready")
        info.setStyleSheet("color:#555; font-size:11px;")
        layout.addWidget(info)
        
        layout.addStretch()
`

---

## 🎨 DESIGN PRINCIPLES

These 8 principles underpin the bedrock_mapping GUI:

1. **MINIMAL CSS** - Only buttons and labels
2. **CONSISTENT MARGINS** - 4/6/8px hierarchy
3. **EMOJI-FIRST** - Every title starts with emoji
4. **TIGHT LAYOUTS** - setSpacing(0), no padding
5. **RESPONSIVE** - Splitter with stretch factors
6. **MODULAR** - Factory functions for sections
7. **ACCESSIBLE** - Toggle arrows show state
8. **CLEAN** - Frameless, minimal borders

---

## 🚀 START HERE

1. **First:** Read GUI_STYLE_REFERENCE.md (2-3 min skim)
2. **Second:** Copy CollapsibleGroupBox class
3. **Third:** Use Snippet #2 for main layout
4. **Fourth:** Reference margin numbers when building widgets
5. **Fifth:** Copy emoji usage from Section 3

**Total time to integrate:** ~30 minutes

---

## ❓ REFERENCE LOOKUP

Need to find something? Search the main reference document:

`
"Margin" → Section 4
"Emoji" → Section 3  
"CSS" → Section 2
"Collapsible" → Sections 1, 8, Snippets 1, 8, 10
"Splitter" → Section 5, Snippet 2
"ScrollArea" → Section 7, Snippet 4
"QGroupBox" → Section 6
"Window" → Section 8, Snippet 2
`

---

📖 **MAIN REFERENCE:** D:\Research\Narm_Afzar\Git_hub\HV_Pro\GUI_STYLE_REFERENCE.md
