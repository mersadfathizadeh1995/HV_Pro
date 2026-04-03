"""
Rejection Pipeline Presets
===========================

Pre-configured QC pipelines for HVSR analysis.

Presets:
    - sesame: SESAME-compliant with FDWRA (default, matches hvsrpy)
    - custom: User-defined settings (persisted across sessions)
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# SESAME Standard configuration (matches hvsrpy defaults)
SESAME_CONFIG = {
    'description': 'SESAME standard with Peak Frequency Consistency (FDWRA)',
    'algorithms': [
        {'type': 'AmplitudeRejection', 'params': {}},
        {'type': 'STALTARejection', 'params': {
            'sta_length': 1.0,
            'lta_length': 30.0,
            'min_ratio': 0.1,
            'max_ratio': 5.0
        }},
    ],
    'post_hvsr': [
        {'type': 'CurveOutlierRejection', 'params': {
            'threshold': 3.0,
            'max_iterations': 5,
            'metric': 'mean',
        }},
    ],
    'use_cox_fdwra': True,
    'fdwra_params': {
        'n': 2.0,
        'max_iterations': 50,
        'min_iterations': 1,
        'distribution_fn': 'lognormal',
        'distribution_mc': 'lognormal'
    }
}

# Preset configurations
PRESET_CONFIGS = {
    'sesame': SESAME_CONFIG,
}


def get_available_presets() -> List[str]:
    """
    Get list of available preset names.
    
    Returns:
        List of preset names
    """
    return list(PRESET_CONFIGS.keys())


def get_preset_description(preset: str) -> str:
    """
    Get description for a preset.
    
    Args:
        preset: Preset name
        
    Returns:
        Description string
    """
    if preset not in PRESET_CONFIGS:
        raise ValueError(f"Unknown preset: {preset}. Available: {get_available_presets()}")
    return PRESET_CONFIGS[preset]['description']


def get_preset_config(preset: str) -> Dict[str, Any]:
    """
    Get full configuration for a preset.
    
    Args:
        preset: Preset name
        
    Returns:
        Configuration dictionary
    """
    if preset not in PRESET_CONFIGS:
        raise ValueError(f"Unknown preset: {preset}. Available: {get_available_presets()}")
    return PRESET_CONFIGS[preset].copy()


def create_preset_pipeline(preset: str, engine=None):
    """
    Create a rejection pipeline from a preset.
    
    Args:
        preset: Preset name ('sesame')
        engine: Optional RejectionEngine instance to configure (creates new if None)
        
    Returns:
        Configured RejectionEngine instance
    """
    from hvsr_pro.processing.rejection.engine import RejectionEngine
    from hvsr_pro.processing.rejection.algorithms import (
        QualityThresholdRejection,
        StatisticalOutlierRejection,
        AmplitudeRejection,
        STALTARejection,
        FrequencyDomainRejection,
        HVSRAmplitudeRejection,
        FlatPeakRejection,
        CurveOutlierRejection,
    )
    
    if preset not in PRESET_CONFIGS:
        raise ValueError(f"Unknown preset: {preset}. Available: {get_available_presets()}")
    
    config = PRESET_CONFIGS[preset]
    
    # Create or clear engine
    if engine is None:
        engine = RejectionEngine(name=f"{preset.title()}Pipeline")
    else:
        engine.clear_algorithms()
    
    # Algorithm type mapping
    algorithm_map = {
        'AmplitudeRejection': AmplitudeRejection,
        'QualityThresholdRejection': QualityThresholdRejection,
        'StatisticalOutlierRejection': StatisticalOutlierRejection,
        'STALTARejection': STALTARejection,
        'FrequencyDomainRejection': FrequencyDomainRejection,
        'HVSRAmplitudeRejection': HVSRAmplitudeRejection,
        'FlatPeakRejection': FlatPeakRejection,
        'CurveOutlierRejection': CurveOutlierRejection,
    }
    
    # Add pre-HVSR algorithms
    for algo_config in config['algorithms']:
        algo_type = algo_config['type']
        algo_params = algo_config['params']
        
        if algo_type in algorithm_map:
            algo = algorithm_map[algo_type](**algo_params)
            engine.add_algorithm(algo)
        else:
            logger.warning(f"Unknown algorithm type: {algo_type}")
    
    # Store post-HVSR algorithms
    engine.post_hvsr_algorithms = []
    for algo_config in config.get('post_hvsr', []):
        algo_type = algo_config['type']
        algo_params = algo_config['params']
        
        if algo_type in algorithm_map:
            algo = algorithm_map[algo_type](**algo_params)
            engine.post_hvsr_algorithms.append(algo)
    
    # Store Cox FDWRA flag
    engine.use_cox_fdwra = config.get('use_cox_fdwra', False)
    
    logger.info(f"Created {preset} rejection pipeline with {len(engine.algorithms)} pre-HVSR algorithms")
    if engine.post_hvsr_algorithms:
        logger.info(f"  Post-HVSR algorithms: {len(engine.post_hvsr_algorithms)}")
    if engine.use_cox_fdwra:
        logger.info("  Cox FDWRA will be applied after HVSR computation")
    
    return engine
