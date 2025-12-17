"""
HVSR Pro GUI Dialogs
====================

Dialog windows for the application.
"""

# Import from original locations for backward compatibility
from hvsr_pro.gui.data_input_dialog import DataInputDialog
from hvsr_pro.gui.export_dialog import ExportDialog
from hvsr_pro.gui.data_export_dialog import DataExportDialog
from hvsr_pro.gui.channel_mapper_dialog import ChannelMapperDialog
from hvsr_pro.gui.column_mapper_dialog import SeismicColumnMapperDialog
from hvsr_pro.gui.advanced_qc_dialog import AdvancedQCDialog

# New modular data_input components
from hvsr_pro.gui.dialogs import data_input

__all__ = [
    'DataInputDialog',
    'ExportDialog',
    'DataExportDialog',
    'ChannelMapperDialog',
    'SeismicColumnMapperDialog',
    'AdvancedQCDialog',
    'data_input',
]

