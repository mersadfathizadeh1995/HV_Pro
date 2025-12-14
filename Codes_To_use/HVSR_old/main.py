"""main.py – simple launcher for the tab‑based HVSR workflow UI."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication, QTabWidget

# ───────────────────────────────────────────────────────── Tab imports ──────
# Tabs live in the same package / folder, so plain relative imports work.
from NewTab0_Automatic import NewTab0_Automatic  # Tab 0 – Automatic Workflow
from NewTab1_Windows import NewTab1_Windows      # Tab 1 – Define Windows
from NewTab2_FsCheck   import NewTab2_FsCheck    # Tab 2 – Check Fs
from NewTab3_Reduce    import NewTab3_Reduce     # Tab 3 – Reduce → MAT (Single Station)
from NewTab3_CircularArray import NewTab3_CircularArray  # Tab 3b – Circular Array Reduction
from NewTab4_WriteMiniseed import NewTab4_WriteMiniseed  # Tab 4 – Write MiniSEED for Geopsy
from NewTab4_HVSRPicker import NewTab4_HVSRPicker # Tab 5 – HVSR Peaks

# (Optional future tabs can be added here, e.g. Tab 6 Aggregate, Tab 7 Settings.)

# ──────────────────────────────────────────────────────────── main() ────────

def main() -> None:
    """Spin up the QApplication, build the QTabWidget and enter the event‑loop."""
    app  = QApplication(sys.argv)

    tabs = QTabWidget()
    tabs.addTab(NewTab0_Automatic(),  "0  Automatic")
    tabs.addTab(NewTab1_Windows(),  "1  Windows")
    tabs.addTab(NewTab2_FsCheck(),  "2  Check Fs")
    tabs.addTab(NewTab3_Reduce(),   "3  Reduce MAT (Single)")
    tabs.addTab(NewTab3_CircularArray(), "3b Circular Array")
    tabs.addTab(NewTab4_WriteMiniseed(), "4  Write MiniSEED")
    tabs.addTab(NewTab4_HVSRPicker(), "5  HVSR Peaks")

    tabs.setWindowTitle("HVSR Workflow")
    tabs.resize(1200, 700)
    tabs.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
