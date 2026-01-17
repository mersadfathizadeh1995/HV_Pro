"""
Launch HVSR Pro GUI
====================

Simple launcher for the HVSR Pro graphical interface.

Usage:
    python launch_gui.py
"""

import sys
from pathlib import Path

# CRITICAL: For Windows multiprocessing support
# This must be called before any other imports that might use multiprocessing
if __name__ == "__main__":
    from multiprocessing import freeze_support
    freeze_support()

# Add package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from PyQt5.QtWidgets import QApplication
    from hvsr_pro.gui import HVSRMainWindow, HAS_GUI
    
    if not HAS_GUI:
        print("ERROR: PyQt5 not available.")
        print("Install with: pip install PyQt5")
        sys.exit(1)
    
    def main():
        """Launch GUI application."""
        print("=" * 70)
        print("HVSR Pro - Interactive Analysis GUI")
        print("=" * 70)
        print("\nFeatures:")
        print("  + Load seismic data (ASCII .txt or MiniSEED)")
        print("  + Interactive window rejection (click to toggle)")
        print("  + Color-coded visualization (green=active, gray=rejected)")
        print("  + Real-time HVSR updates")
        print("  + Quality metrics and statistics")
        print("  + Export results and plots")
        print("\n" + "=" * 70)
        print("Starting GUI...\n")
        
        app = QApplication(sys.argv)
        app.setApplicationName("HVSR Pro")
        app.setOrganizationName("OSCAR HVSR")
        
        # Set application style
        app.setStyle('Fusion')
        
        # Create and show main window
        window = HVSRMainWindow()
        window.show()
        
        print("SUCCESS: GUI launched successfully!")
        print("\nInstructions:")
        print("  1. Click 'Load Data File' to import seismic data")
        print("  2. Adjust processing settings if needed")
        print("  3. Click 'Process HVSR' to analyze")
        print("  4. Use layer dock checkboxes to toggle window visibility")
        print("  5. Mean HVSR updates automatically when you toggle")
        print("  6. Export results when satisfied")
        print("\n" + "=" * 70)
        
        sys.exit(app.exec_())
    
    if __name__ == "__main__":
        main()

except ImportError as e:
    print("ERROR: Cannot launch GUI")
    print(f"   {e}")
    print("\nRequired dependencies:")
    print("  - PyQt5:     pip install PyQt5")
    print("  - matplotlib: pip install matplotlib")
    print("  - numpy:     pip install numpy")
    print("  - scipy:     pip install scipy")
    sys.exit(1)
