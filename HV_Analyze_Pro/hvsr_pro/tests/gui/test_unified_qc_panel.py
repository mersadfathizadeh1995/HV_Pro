"""
Tests for UnifiedQCPanel
========================

Tests for the unified quality control panel with hierarchical checkboxes,
SESAME defaults, and settings persistence.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Check if PyQt5 is available for GUI tests
try:
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtCore import Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

# Skip all tests if PyQt5 not available
pytestmark = pytest.mark.skipif(not HAS_PYQT5, reason="PyQt5 required for GUI tests")


@pytest.fixture(scope='module')
def qapp():
    """Create QApplication for GUI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def unified_panel(qapp):
    """Create UnifiedQCPanel for testing."""
    from hvsr_pro.gui.panels.unified_qc_panel import UnifiedQCPanel
    panel = UnifiedQCPanel()
    yield panel


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary config directory."""
    config_dir = tmp_path / '.hvsr_pro'
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


class TestUnifiedQCPanel:
    """Tests for the UnifiedQCPanel widget."""
    
    def test_panel_creation(self, unified_panel):
        """Panel should be created with default SESAME settings."""
        assert unified_panel is not None
        assert unified_panel.master_enable.isChecked()  # Master enabled by default
        assert unified_panel._sesame_radio.isChecked()  # SESAME mode by default
    
    def test_master_checkbox_disables_all(self, unified_panel):
        """Master 'Enable QC' checkbox should disable all phases when unchecked."""
        # Initially enabled
        assert unified_panel.master_enable.isChecked()
        assert unified_panel.phase1_enable.isEnabled()
        assert unified_panel.phase2_enable.isEnabled()
        
        # Uncheck master
        unified_panel.master_enable.setChecked(False)
        
        # All should be disabled now
        assert not unified_panel.phase1_enable.isEnabled()
        assert not unified_panel.phase2_enable.isEnabled()
        
        # Algorithm checkboxes should also be disabled
        assert not unified_panel.amplitude_row['checkbox'].isEnabled()
        assert not unified_panel.fdwra_row['checkbox'].isEnabled()
        
        # Settings from get_settings should show disabled
        settings = unified_panel.get_settings()
        assert settings['enabled'] == False
    
    def test_phase1_checkbox_toggles_phase1_algorithms(self, unified_panel):
        """Phase 1 checkbox should enable/disable all Phase 1 algorithms."""
        # Initially Phase 1 enabled
        assert unified_panel.phase1_enable.isChecked()
        assert unified_panel.amplitude_row['checkbox'].isEnabled()
        assert unified_panel.stalta_row['checkbox'].isEnabled()
        assert unified_panel.spectral_row['checkbox'].isEnabled()
        assert unified_panel.statistical_row['checkbox'].isEnabled()
        
        # Uncheck Phase 1
        unified_panel.phase1_enable.setChecked(False)
        
        # All Phase 1 algorithms should be disabled
        assert not unified_panel.amplitude_row['checkbox'].isEnabled()
        assert not unified_panel.stalta_row['checkbox'].isEnabled()
        assert not unified_panel.spectral_row['checkbox'].isEnabled()
        assert not unified_panel.statistical_row['checkbox'].isEnabled()
        
        # Phase 2 algorithms should still be enabled
        assert unified_panel.fdwra_row['checkbox'].isEnabled()
        
        # Check settings
        settings = unified_panel.get_settings()
        assert settings['phase1_enabled'] == False
        assert settings['phase2_enabled'] == True
    
    def test_phase2_checkbox_toggles_phase2_algorithms(self, unified_panel):
        """Phase 2 checkbox should enable/disable all Phase 2 algorithms."""
        # Initially Phase 2 enabled
        assert unified_panel.phase2_enable.isChecked()
        assert unified_panel.fdwra_row['checkbox'].isEnabled()
        assert unified_panel.hvsr_amp_row['checkbox'].isEnabled()
        assert unified_panel.flat_peak_row['checkbox'].isEnabled()
        
        # Uncheck Phase 2
        unified_panel.phase2_enable.setChecked(False)
        
        # All Phase 2 algorithms should be disabled
        assert not unified_panel.fdwra_row['checkbox'].isEnabled()
        assert not unified_panel.hvsr_amp_row['checkbox'].isEnabled()
        assert not unified_panel.flat_peak_row['checkbox'].isEnabled()
        
        # Phase 1 algorithms should still be enabled
        assert unified_panel.amplitude_row['checkbox'].isEnabled()
        
        # Check settings
        settings = unified_panel.get_settings()
        assert settings['phase1_enabled'] == True
        assert settings['phase2_enabled'] == False
    
    def test_individual_algorithm_toggles_independently(self, unified_panel):
        """Individual algorithm checkboxes should toggle independently."""
        # Enable Phase 1 but only check Amplitude
        unified_panel.phase1_enable.setChecked(True)
        unified_panel.amplitude_row['checkbox'].setChecked(True)
        unified_panel.stalta_row['checkbox'].setChecked(False)
        unified_panel.spectral_row['checkbox'].setChecked(False)
        unified_panel.statistical_row['checkbox'].setChecked(False)
        
        settings = unified_panel.get_settings()
        algos = settings['algorithms']
        
        assert algos['amplitude']['enabled'] == True
        assert algos['sta_lta']['enabled'] == False
        assert algos['spectral_spike']['enabled'] == False
        assert algos['statistical_outlier']['enabled'] == False
    
    def test_sesame_preset_matches_hvsrpy_defaults(self, unified_panel):
        """SESAME preset should have same defaults as hvsrpy."""
        # Set to SESAME mode
        unified_panel._sesame_radio.setChecked(True)
        
        settings = unified_panel.get_settings()
        algos = settings['algorithms']
        
        # Phase 1: Amplitude enabled, STA/LTA enabled
        assert algos['amplitude']['enabled'] == True
        assert algos['sta_lta']['enabled'] == True
        
        # STA/LTA params should match hvsrpy
        sta_lta_params = algos['sta_lta']['params']
        assert sta_lta_params['sta_length'] == 1.0
        assert sta_lta_params['lta_length'] == 30.0
        assert sta_lta_params['min_ratio'] == 0.2
        assert sta_lta_params['max_ratio'] == 2.5
        
        # Phase 2: FDWRA enabled
        assert algos['fdwra']['enabled'] == True
        
        # FDWRA params should match hvsrpy
        fdwra_params = algos['fdwra']['params']
        assert fdwra_params['n'] == 2.0
        assert fdwra_params['max_iterations'] == 50
        assert fdwra_params['distribution_fn'] == 'lognormal'
    
    def test_active_count_updates_correctly(self, unified_panel):
        """Active algorithm count should update when checkboxes change."""
        # In SESAME mode: 2 active in Phase 1, 1 in Phase 2
        unified_panel._sesame_radio.setChecked(True)
        
        assert "[2 active]" in unified_panel.phase1_count_label.text()
        assert "[1 active]" in unified_panel.phase2_count_label.text()
        
        # Uncheck STA/LTA -> Phase 1 shows [1 active]
        unified_panel.stalta_row['checkbox'].setChecked(False)
        assert "[1 active]" in unified_panel.phase1_count_label.text()
        
        # Check Flat Peak -> Phase 2 shows [2 active]
        unified_panel.flat_peak_row['checkbox'].setChecked(True)
        assert "[2 active]" in unified_panel.phase2_count_label.text()
    
    def test_mode_switching(self, unified_panel):
        """Switching between SESAME and Custom modes should work correctly."""
        # Start in SESAME
        unified_panel._sesame_radio.setChecked(True)
        assert unified_panel.get_settings()['mode'] == 'sesame'
        assert not unified_panel.save_custom_btn.isEnabled()
        
        # Switch to Custom
        unified_panel._custom_radio.setChecked(True)
        assert unified_panel.get_settings()['mode'] == 'custom'
        assert unified_panel.save_custom_btn.isEnabled()
        
        # Switch back to SESAME
        unified_panel._sesame_radio.setChecked(True)
        assert unified_panel.get_settings()['mode'] == 'sesame'
    
    def test_get_settings_returns_complete_dict(self, unified_panel):
        """get_settings() should return complete settings dictionary."""
        settings = unified_panel.get_settings()
        
        # Check required keys
        assert 'enabled' in settings
        assert 'mode' in settings
        assert 'phase1_enabled' in settings
        assert 'phase2_enabled' in settings
        assert 'algorithms' in settings
        assert 'cox_fdwra' in settings  # FDWRA settings
        
        # Check all algorithms present
        algos = settings['algorithms']
        assert 'amplitude' in algos
        assert 'sta_lta' in algos
        assert 'spectral_spike' in algos
        assert 'statistical_outlier' in algos
        assert 'fdwra' in algos
        assert 'hvsr_amplitude' in algos
        assert 'flat_peak' in algos
    
    def test_is_fdwra_enabled(self, unified_panel):
        """is_fdwra_enabled() should check all required conditions."""
        # In SESAME mode, FDWRA should be enabled
        unified_panel._sesame_radio.setChecked(True)
        assert unified_panel.is_fdwra_enabled() == True
        
        # Disable Phase 2 -> FDWRA disabled
        unified_panel.phase2_enable.setChecked(False)
        assert unified_panel.is_fdwra_enabled() == False
        
        # Re-enable Phase 2 but disable master
        unified_panel.phase2_enable.setChecked(True)
        unified_panel.master_enable.setChecked(False)
        assert unified_panel.is_fdwra_enabled() == False


class TestCustomSettingsPersistence:
    """Tests for custom settings save/load."""
    
    def test_save_creates_config_file(self, temp_config_dir):
        """Saving custom settings should create config file."""
        from hvsr_pro.gui.panels.unified_qc_panel import save_custom_settings, get_custom_settings_path
        
        with patch('hvsr_pro.gui.panels.unified_qc_panel.get_custom_settings_path') as mock_path:
            config_file = temp_config_dir / 'qc_custom_settings.json'
            mock_path.return_value = config_file
            
            settings = {
                'phase1_enabled': True,
                'phase2_enabled': False,
                'algorithms': {'amplitude': {'enabled': True, 'params': {}}}
            }
            
            result = save_custom_settings(settings)
            
            assert result == True
            assert config_file.exists()
            
            # Verify content
            with open(config_file) as f:
                saved = json.load(f)
            assert saved['phase1_enabled'] == True
            assert saved['phase2_enabled'] == False
    
    def test_load_restores_saved_settings(self, temp_config_dir):
        """Loading should restore previously saved settings."""
        from hvsr_pro.gui.panels.unified_qc_panel import load_custom_settings, save_custom_settings
        
        with patch('hvsr_pro.gui.panels.unified_qc_panel.get_custom_settings_path') as mock_path:
            config_file = temp_config_dir / 'qc_custom_settings.json'
            mock_path.return_value = config_file
            
            # Save specific settings
            settings = {
                'phase1_enabled': False,
                'phase2_enabled': True,
                'algorithms': {
                    'amplitude': {'enabled': False, 'params': {}},
                    'fdwra': {'enabled': True, 'params': {'n': 3.0}}
                }
            }
            save_custom_settings(settings)
            
            # Load and verify
            loaded = load_custom_settings()
            assert loaded['phase1_enabled'] == False
            assert loaded['phase2_enabled'] == True
            assert loaded['algorithms']['amplitude']['enabled'] == False
            assert loaded['algorithms']['fdwra']['params']['n'] == 3.0
    
    def test_missing_config_uses_sesame_defaults(self, temp_config_dir):
        """Missing config file should use SESAME defaults."""
        from hvsr_pro.gui.panels.unified_qc_panel import load_custom_settings, SESAME_DEFAULTS
        
        with patch('hvsr_pro.gui.panels.unified_qc_panel.get_custom_settings_path') as mock_path:
            # Point to non-existent file
            config_file = temp_config_dir / 'nonexistent.json'
            mock_path.return_value = config_file
            
            loaded = load_custom_settings()
            
            # Should return SESAME defaults
            assert loaded['phase1_enabled'] == SESAME_DEFAULTS['phase1_enabled']
            assert loaded['phase2_enabled'] == SESAME_DEFAULTS['phase2_enabled']
    
    def test_corrupted_config_uses_sesame_defaults(self, temp_config_dir):
        """Corrupted config file should use SESAME defaults."""
        from hvsr_pro.gui.panels.unified_qc_panel import load_custom_settings, SESAME_DEFAULTS
        
        with patch('hvsr_pro.gui.panels.unified_qc_panel.get_custom_settings_path') as mock_path:
            config_file = temp_config_dir / 'corrupted.json'
            mock_path.return_value = config_file
            
            # Write invalid JSON
            with open(config_file, 'w') as f:
                f.write("{ invalid json }")
            
            loaded = load_custom_settings()
            
            # Should return SESAME defaults
            assert loaded['phase1_enabled'] == SESAME_DEFAULTS['phase1_enabled']


class TestQCProcessing:
    """Tests for QC processing logic."""
    
    def test_qc_settings_object_conversion(self, unified_panel):
        """get_qc_settings_object() should return valid QCSettings."""
        from hvsr_pro.processing.rejection.settings import QCSettings
        
        qc_settings = unified_panel.get_qc_settings_object()
        
        assert isinstance(qc_settings, QCSettings)
        assert qc_settings.enabled == unified_panel.master_enable.isChecked()
        assert qc_settings.cox_fdwra.enabled == unified_panel.fdwra_row['checkbox'].isChecked()
    
    def test_processing_thread_receives_phase_flags(self):
        """ProcessingThread should receive phase1_enabled and phase2_enabled."""
        from hvsr_pro.gui.workers.processing_worker import ProcessingThread
        
        # Create thread with phase flags
        thread = ProcessingThread(
            file_input='test.sac',
            window_length=60.0,
            overlap=0.5,
            smoothing_bandwidth=40.0,
            qc_enabled=True,
            phase1_enabled=True,
            phase2_enabled=False
        )
        
        assert thread.qc_enabled == True
        assert thread.phase1_enabled == True
        assert thread.phase2_enabled == False


class TestAlgorithmSettingsDialogs:
    """Tests for algorithm settings dialogs."""
    
    def test_stalta_dialog_has_correct_fields(self, qapp):
        """STA/LTA dialog should have required fields."""
        from hvsr_pro.gui.dialogs.qc.algorithm_settings_dialogs import STALTASettingsDialog
        
        dialog = STALTASettingsDialog(None, {})
        
        # Check widgets exist
        assert hasattr(dialog, 'sta_spin')
        assert hasattr(dialog, 'lta_spin')
        assert hasattr(dialog, 'min_ratio_spin')
        assert hasattr(dialog, 'max_ratio_spin')
    
    def test_fdwra_dialog_has_correct_fields(self, qapp):
        """FDWRA dialog should have required fields."""
        from hvsr_pro.gui.dialogs.qc.algorithm_settings_dialogs import FDWRASettingsDialog
        
        dialog = FDWRASettingsDialog(None, {})
        
        # Check widgets exist
        assert hasattr(dialog, 'n_spin')
        assert hasattr(dialog, 'max_iter_spin')
        assert hasattr(dialog, 'min_iter_spin')
        assert hasattr(dialog, 'dist_combo')
    
    def test_dialog_reset_restores_defaults(self, qapp):
        """Reset button should restore algorithm defaults."""
        from hvsr_pro.gui.dialogs.qc.algorithm_settings_dialogs import (
            STALTASettingsDialog, ALGORITHM_DEFAULTS
        )
        
        # Start with non-default values
        dialog = STALTASettingsDialog(None, {'sta_length': 5.0, 'lta_length': 60.0})
        
        # Verify non-default values are shown
        assert dialog.sta_spin.value() == 5.0
        assert dialog.lta_spin.value() == 60.0
        
        # Reset
        dialog._on_reset()
        
        # Verify defaults restored
        defaults = ALGORITHM_DEFAULTS['sta_lta']
        assert dialog.sta_spin.value() == defaults['sta_length']
        assert dialog.lta_spin.value() == defaults['lta_length']
    
    def test_dialog_collects_params_correctly(self, qapp):
        """Dialog should collect params correctly on OK."""
        from hvsr_pro.gui.dialogs.qc.algorithm_settings_dialogs import FDWRASettingsDialog
        
        dialog = FDWRASettingsDialog(None, {})
        
        # Set specific values
        dialog.n_spin.setValue(3.5)
        dialog.max_iter_spin.setValue(30)
        
        # Collect params
        params = dialog._collect_params()
        
        assert params['n'] == 3.5
        assert params['max_iterations'] == 30


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
