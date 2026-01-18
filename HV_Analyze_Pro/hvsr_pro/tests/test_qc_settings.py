"""
Tests for QC Settings
=====================

Tests for QCSettings dataclass and custom settings persistence.
"""

import pytest
import json
import tempfile
from pathlib import Path


class TestQCSettings:
    """Tests for QCSettings dataclass."""
    
    def test_default_values(self):
        """QCSettings should have sensible defaults."""
        from hvsr_pro.processing.rejection.settings import QCSettings
        
        settings = QCSettings()
        
        assert settings.enabled == True
        assert settings.mode == 'sesame'
        assert settings.preset == 'sesame'
        assert settings.phase1_enabled == True
        assert settings.phase2_enabled == True
    
    def test_to_dict_includes_all_fields(self):
        """to_dict() should include all settings."""
        from hvsr_pro.processing.rejection.settings import QCSettings
        
        settings = QCSettings()
        d = settings.to_dict()
        
        assert 'enabled' in d
        assert 'mode' in d
        assert 'preset' in d
        assert 'phase1_enabled' in d
        assert 'phase2_enabled' in d
        assert 'algorithms' in d
        assert 'cox_fdwra' in d
    
    def test_from_dict_restores_settings(self):
        """from_dict() should restore settings from dictionary."""
        from hvsr_pro.processing.rejection.settings import QCSettings
        
        original = QCSettings()
        original.enabled = False
        original.phase1_enabled = False
        original.mode = 'custom'
        original.sta_lta.enabled = True
        original.sta_lta.params['min_ratio'] = 0.3
        original.cox_fdwra.enabled = True
        original.cox_fdwra.n = 3.0
        
        d = original.to_dict()
        restored = QCSettings.from_dict(d)
        
        assert restored.enabled == False
        assert restored.phase1_enabled == False
        assert restored.mode == 'custom'
        assert restored.sta_lta.enabled == True
        assert restored.sta_lta.params['min_ratio'] == 0.3
        assert restored.cox_fdwra.enabled == True
        assert restored.cox_fdwra.n == 3.0
    
    def test_save_and_load(self, tmp_path):
        """save() and load() should round-trip correctly."""
        from hvsr_pro.processing.rejection.settings import QCSettings
        
        filepath = tmp_path / 'test_settings.json'
        
        # Create and save
        original = QCSettings()
        original.mode = 'custom'
        original.phase2_enabled = False
        original.amplitude.enabled = False
        original.cox_fdwra.n = 2.5
        original.save(str(filepath))
        
        # Load and verify
        loaded = QCSettings.load(str(filepath))
        
        assert loaded.mode == 'custom'
        assert loaded.phase2_enabled == False
        assert loaded.amplitude.enabled == False
        assert loaded.cox_fdwra.n == 2.5
    
    def test_apply_preset_sesame(self):
        """apply_preset('sesame') should configure for SESAME standard."""
        from hvsr_pro.processing.rejection.settings import QCSettings
        
        settings = QCSettings()
        settings.apply_preset('sesame')
        
        # SESAME enables amplitude, quality threshold, and cox_fdwra
        assert settings.amplitude.enabled == True
        assert settings.quality_threshold.enabled == True
        assert settings.cox_fdwra.enabled == True
        assert settings.preset == 'sesame'
    
    def test_get_enabled_pre_hvsr_algorithms(self):
        """get_enabled_pre_hvsr_algorithms() should return correct list."""
        from hvsr_pro.processing.rejection.settings import QCSettings
        
        settings = QCSettings()
        settings.amplitude.enabled = True
        settings.sta_lta.enabled = True
        settings.frequency_domain.enabled = False
        
        enabled = settings.get_enabled_pre_hvsr_algorithms()
        
        assert 'amplitude' in enabled
        assert 'sta_lta' in enabled
        assert 'frequency_domain' not in enabled
    
    def test_get_enabled_post_hvsr_algorithms(self):
        """get_enabled_post_hvsr_algorithms() should return correct list."""
        from hvsr_pro.processing.rejection.settings import QCSettings
        
        settings = QCSettings()
        settings.hvsr_amplitude.enabled = True
        settings.flat_peak.enabled = False
        
        enabled = settings.get_enabled_post_hvsr_algorithms()
        
        assert 'hvsr_amplitude' in enabled
        assert 'flat_peak' not in enabled


class TestPresetConfigurations:
    """Tests for preset configurations."""
    
    def test_sesame_config_matches_hvsrpy(self):
        """SESAME config should match hvsrpy defaults."""
        from hvsr_pro.processing.rejection.presets import SESAME_CONFIG
        
        # Check FDWRA params match hvsrpy
        fdwra = SESAME_CONFIG['fdwra_params']
        assert fdwra['n'] == 2.0
        assert fdwra['max_iterations'] == 50
        assert fdwra['distribution_fn'] == 'lognormal'
        
        # Check STA/LTA params
        stalta = None
        for algo in SESAME_CONFIG['algorithms']:
            if algo['type'] == 'STALTARejection':
                stalta = algo['params']
                break
        
        assert stalta is not None
        assert stalta['sta_length'] == 1.0
        assert stalta['lta_length'] == 30.0
        assert stalta['min_ratio'] == 0.2
        assert stalta['max_ratio'] == 2.5
    
    def test_get_preset_names_returns_primary_presets(self):
        """get_preset_names() should return SESAME and custom only."""
        from hvsr_pro.processing.rejection.settings import get_preset_names
        
        names = get_preset_names()
        
        assert 'sesame' in names
        assert 'custom' in names
        # Legacy presets should not be in primary list
        assert 'balanced' not in names
        assert 'aggressive' not in names


class TestCoxFDWRASettings:
    """Tests for FDWRA settings dataclass."""
    
    def test_default_values_match_hvsrpy(self):
        """Default FDWRA values should match hvsrpy."""
        from hvsr_pro.processing.rejection.settings import CoxFDWRASettings
        
        settings = CoxFDWRASettings()
        
        # Defaults should match hvsrpy frequency_domain_window_rejection
        assert settings.n == 2.0
        assert settings.max_iterations == 50
        assert settings.min_iterations == 1
        assert settings.distribution_fn == 'lognormal'
        assert settings.distribution_mc == 'lognormal'
    
    def test_to_dict_and_from_dict(self):
        """to_dict() and from_dict() should round-trip correctly."""
        from hvsr_pro.processing.rejection.settings import CoxFDWRASettings
        
        original = CoxFDWRASettings(
            enabled=True,
            n=3.0,
            max_iterations=30,
            distribution_fn='normal'
        )
        
        d = original.to_dict()
        restored = CoxFDWRASettings.from_dict(d)
        
        assert restored.enabled == True
        assert restored.n == 3.0
        assert restored.max_iterations == 30
        assert restored.distribution_fn == 'normal'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
