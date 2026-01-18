"""
Mapper Dialogs
==============

Dialog windows for channel and column mapping.
"""

from .channel_mapper_dialog import ChannelMapperDialog
from .column_mapper_dialog import SeismicColumnMapperDialog
from .component_mapper_dialog import ComponentMapperDialog

__all__ = [
    'ChannelMapperDialog',
    'SeismicColumnMapperDialog',
    'ComponentMapperDialog',
]
