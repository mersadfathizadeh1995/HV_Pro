"""
QC Wiring Helpers
=================

Pure functions that translate ``QCConfig`` settings into
rejection-engine algorithm instances.  Used by ``HVSRAnalysis.process()``.
"""
from __future__ import annotations

import logging
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


def apply_custom_qc_phase1(engine, qc_cfg) -> None:
    """Wire pre-HVSR (Phase 1) algorithms from *qc_cfg*."""
    from hvsr_pro.processing.rejection import (
        AmplitudeRejection,
        QualityThresholdRejection,
        STALTARejection,
        FrequencyDomainRejection,
        StatisticalOutlierRejection,
    )

    a = qc_cfg.amplitude
    if a.enabled:
        engine.add_algorithm(AmplitudeRejection(
            max_amplitude=a.max_amplitude,
            min_rms=a.min_rms,
            clipping_threshold=a.clipping_threshold,
        ))

    qt = qc_cfg.quality_threshold
    if qt.enabled:
        engine.add_algorithm(QualityThresholdRejection(threshold=qt.threshold))

    sl = qc_cfg.sta_lta
    if sl.enabled:
        engine.add_algorithm(STALTARejection(
            sta_length=sl.sta_length,
            lta_length=sl.lta_length,
            min_ratio=sl.min_ratio,
            max_ratio=sl.max_ratio,
        ))

    fd = qc_cfg.frequency_domain
    if fd.enabled:
        engine.add_algorithm(FrequencyDomainRejection(spike_threshold=fd.spike_threshold))

    so = qc_cfg.statistical_outlier
    if so.enabled:
        engine.add_algorithm(StatisticalOutlierRejection(
            method=so.method, threshold=so.threshold,
        ))


def should_apply_fdwra(qc_cfg) -> bool:
    """Decide whether Cox FDWRA should run."""
    if not qc_cfg.enabled or not qc_cfg.phase2_enabled:
        return False
    # Explicit enabled flag always wins
    if not qc_cfg.cox_fdwra.enabled:
        return False
    # SESAME mode enables FDWRA by default (config default is enabled=True)
    return True


def build_post_hvsr_algos(qc_cfg) -> List:
    """Instantiate post-HVSR rejection algorithms from *qc_cfg*."""
    from hvsr_pro.processing.rejection import (
        HVSRAmplitudeRejection,
        FlatPeakRejection,
        CurveOutlierRejection,
    )

    algos: List = []
    ha = qc_cfg.hvsr_amplitude
    if ha.enabled:
        algos.append(HVSRAmplitudeRejection(min_amplitude=ha.min_amplitude))

    fp = qc_cfg.flat_peak
    if fp.enabled:
        algos.append(FlatPeakRejection(flatness_threshold=fp.flatness_threshold))

    co = qc_cfg.curve_outlier
    if co.enabled:
        algos.append(CurveOutlierRejection(
            threshold=co.threshold,
            max_iterations=co.max_iterations,
            metric=co.metric,
        ))

    return algos


def make_dummy_result(processing_cfg, windows, message: str):
    """Create a flat-line ``HVSRResult`` when QC leaves zero windows."""
    from hvsr_pro.processing.hvsr import HVSRResult

    p = processing_cfg
    freqs = np.logspace(np.log10(p.freq_min), np.log10(p.freq_max), p.n_frequencies)
    ones = np.ones_like(freqs)
    return HVSRResult(
        frequencies=freqs,
        mean_hvsr=ones,
        median_hvsr=ones,
        std_hvsr=np.zeros_like(freqs),
        percentile_16=ones * 0.9,
        percentile_84=ones * 1.1,
        window_spectra=[],
        peaks=[],
        total_windows=windows.n_windows,
        valid_windows=0,
        metadata={"qc_failure": True, "message": message},
    )
