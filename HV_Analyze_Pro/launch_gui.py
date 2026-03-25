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
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication
    # QWebEngineView MUST be imported before QApplication is created
    try:
        QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
        from PyQt5.QtWebEngineWidgets import QWebEngineView  # noqa: F401
    except ImportError:
        pass  # graceful fallback to matplotlib maps
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
        print("\nStarting GUI...\n")
        
        app = QApplication(sys.argv)
        app.setApplicationName("HVSR Pro")
        app.setOrganizationName("OSCAR HVSR")
        
        # Set application style
        app.setStyle('Fusion')
        
        # Show Welcome Dialog first
        try:
            from hvsr_pro.packages.project_manager.gui.welcome_dialog import WelcomeDialog
            from hvsr_pro.packages.project_manager.project import Project
            from hvsr_pro.packages.project_manager.station_registry import StationRegistry
            from hvsr_pro.packages.project_manager.project_io import add_recent_project

            welcome = WelcomeDialog()
            result = welcome.exec_()

            if result and welcome.result_action == "new":
                # Create main window then show New Project dialog
                window = HVSRMainWindow()
                window.show()
                window.new_project()

            elif result and welcome.result_action == "open":
                window = HVSRMainWindow()
                window.show()
                proj = Project.load(welcome.result_path)
                add_recent_project(welcome.result_path)
                window._open_hub_for_project(proj)

            elif result and welcome.result_action == "quick":
                # Quick Analysis — just open the main window
                window = HVSRMainWindow()
                window.show()

            else:
                # Cancelled — still open main window
                window = HVSRMainWindow()
                window.show()

        except Exception as e:
            print(f"Welcome dialog error: {e}")
            print("Falling back to direct launch...")
            window = HVSRMainWindow()
            window.show()
        
        print("SUCCESS: GUI launched successfully!")
        print("=" * 70)
        
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
