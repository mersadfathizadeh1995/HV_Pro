"""
Data Input Tabs
===============

Tab widgets for different data loading modes.
"""

from .single_file_tab import SingleFileTab
from .multi_type1_tab import MultiType1Tab
from .multi_type2_tab import MultiType2Tab
from .multi_component_tab import MultiComponentTab
from .advanced_tab import AdvancedOptionsTab

__all__ = [
    'SingleFileTab',
    'MultiType1Tab',
    'MultiType2Tab',
    'MultiComponentTab',
    'AdvancedOptionsTab',
]
