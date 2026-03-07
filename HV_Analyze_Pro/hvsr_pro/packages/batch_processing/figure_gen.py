"""
HVSR Figure Generation Module (Batch Processing)
=================================================

Generates all configured figures for HVSR analysis results.
Ported from HVSR_old/hvsr_figure_gen.py with full feature parity.

Uses matplotlib Agg backend internally so it works regardless of
the active GUI backend.
"""

import logging
import numpy as np
from pathlib import Path

from matplotlib.figure import Figure as _Fig
from matplotlib.backends.backend_agg import FigureCanvasAgg as _AggCanvas
import matplotlib.lines as _mlines


_SIZE_MAP = {
    'Standard (10x7)': (10, 7),
    'Large (14x10)': (14, 10),
    'Publication (12x8)': (12, 8),
    'Wide (16x6)': (16, 6),
}


def _compute_smart_ylim(fig_config, hv_mean, hv_std, hv_16, hv_84,
                         combined_hv_accepted):
    """Compute a robust Y-axis upper limit."""
    if not fig_config.get('auto_ylim', True):
        return None
    method = fig_config.get('ylim_method', '95th Percentile')
    if 'Mean + 3' in method:
        ylim = float(np.max(hv_mean) + 3.0 * np.max(hv_std))
    elif 'Mean + 2' in method:
        ylim = float(np.max(hv_84) + 2.0 * np.max(hv_84 - hv_16))
    else:
        ylim = float(np.percentile(combined_hv_accepted, 95))
    ylim = max(ylim * 1.1, float(np.max(hv_mean)) * 1.5)
    logging.info("Smart Y-limit: %.1f (method=%s)", ylim, method)
    return ylim


def _default_palette(n):
    """Generate a simple color palette."""
    import matplotlib.cm as cm
    return [cm.tab20(i / max(n, 1)) for i in range(n)]


def generate_hvsr_figures(
    hvsr_result_obj,
    window_collection,
    seismic_data,
    peaks,
    freq_ref,
    hv_mean,
    hv_std,
    hv_mean_plus_std,
    hv_mean_minus_std,
    hv_16,
    hv_84,
    combined_hv,
    rejected_mask,
    accepted_indices,
    n_windows,
    output_dir,
    fig_label,
    fig_title,
    fig_config,
    fig_standard=True,
    fig_hvsr_pro=True,
    fig_statistics=True,
    save_png=True,
    save_pdf=False,
    dpi=300,
    ann_font_pt=10,
    annot_alpha=0.85,
    palette=None,
    skip_standard_figure=False,
):
    """Generate all configured HVSR figures.

    Parameters
    ----------
    hvsr_result_obj : HVSRResult or None
        hvsr_pro HVSRResult object (None if hvsr_pro unavailable).
    window_collection : WindowCollection or None
    seismic_data : SeismicData or None
    peaks : list
        Peak-like objects with ``.frequency`` and ``.amplitude`` attributes.
    freq_ref : np.ndarray
    hv_mean, hv_std, hv_mean_plus_std, hv_mean_minus_std : np.ndarray
    hv_16, hv_84 : np.ndarray
    combined_hv : np.ndarray
        Shape ``(n_freq, n_windows)``.
    rejected_mask : array-like of bool
    accepted_indices : list[int]
    n_windows : int
    output_dir : Path or str
    fig_label, fig_title : str
    fig_config : dict
    fig_standard, fig_hvsr_pro, fig_statistics : bool
    save_png, save_pdf : bool
    dpi : int
    ann_font_pt : int
    annot_alpha : float
    palette : list or None
    skip_standard_figure : bool

    Returns
    -------
    int
        Number of figures saved.
    """
    output_dir = Path(output_dir)
    _hvsr_pro_ok = hvsr_result_obj is not None
    combined_accepted = combined_hv[:, accepted_indices] if len(accepted_indices) > 0 else combined_hv
    n_accepted = len(accepted_indices)

    smart_ylim = _compute_smart_ylim(
        fig_config, hv_mean, hv_std, hv_16, hv_84, combined_accepted)

    total_saved = 0

    # ── Figure 1: Standard window-curves ─────────────────────────────────
    if fig_standard and not skip_standard_figure:
        logging.info("Generating standard window-curves figure...")
        _pal = palette or _default_palette(n_windows)
        fig1 = _Fig(figsize=(10, 7))
        _AggCanvas(fig1)
        ax1 = fig1.add_subplot(111)

        n_plotted = 0
        for i, curve in enumerate(combined_hv.T, 1):
            if not rejected_mask[i - 1]:
                ax1.plot(freq_ref, curve,
                         color=_pal[i % len(_pal)], lw=0.8, alpha=0.7)
                n_plotted += 1

        ax1.plot(freq_ref, hv_mean, 'k', lw=2, label='Mean')
        ax1.plot(freq_ref, hv_mean_plus_std, '--k', lw=1, label='+Std')
        ax1.plot(freq_ref, hv_mean_minus_std, '--k', lw=1, label='-Std')

        for pk in peaks:
            _f = pk.frequency if hasattr(pk, 'frequency') else pk[0]
            _a = pk.amplitude if hasattr(pk, 'amplitude') else pk[1]
            ax1.plot(_f, _a, 'or', markersize=8,
                     markeredgecolor='black', markeredgewidth=1, zorder=5)
            ax1.annotate(
                f"{_f:.2f} Hz", xy=(_f, _a),
                xytext=(15, 15), textcoords='offset points',
                fontsize=ann_font_pt,
                arrowprops=dict(arrowstyle='->'),
                bbox=dict(boxstyle='round,pad=0.3',
                          fc='yellow', alpha=annot_alpha, lw=0))

        ax1.set_xscale('log')
        ax1.set_xlabel('Frequency [Hz]')
        ax1.set_ylabel('HVSR')
        ax1.set_title(fig_title)
        ax1.grid(True, which='both', ls=':')
        if smart_ylim is not None:
            ax1.set_ylim(0, smart_ylim)

        legend_handles = [
            _mlines.Line2D([], [], color='gray', lw=0.8, alpha=0.7,
                           label=f'Individual curves (n={n_plotted})'),
            _mlines.Line2D([], [], color='k', lw=2, label='Mean'),
            _mlines.Line2D([], [], color='k', lw=1, ls='--', label='\u00b11 Std'),
        ]
        ax1.legend(handles=legend_handles, fontsize=9,
                   loc='upper right', frameon=True, framealpha=0.8)
        ax1.text(0.02, 0.98,
                 f'Windows: {n_plotted}/{n_windows} accepted',
                 transform=ax1.transAxes, verticalalignment='top',
                 fontsize=9,
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        fig1.tight_layout()

        if save_png:
            _p = output_dir / f"HVSR_{fig_label}.png"
            fig1.savefig(str(_p), dpi=dpi, bbox_inches='tight')
            logging.info("Saved %s", _p.name)
            total_saved += 1
        if save_pdf:
            _p = output_dir / f"HVSR_{fig_label}.pdf"
            fig1.savefig(str(_p), bbox_inches='tight')
            logging.info("Saved %s", _p.name)
            total_saved += 1

    # ── Figure 2: hvsr_pro clean HVSR curve ──────────────────────────────
    if fig_hvsr_pro and _hvsr_pro_ok:
        logging.info("Generating hvsr_pro HVSR curve...")
        try:
            from hvsr_pro.visualization.hvsr_plots import save_hvsr_plot
            save_hvsr_plot(hvsr_result_obj,
                           str(output_dir / f"HVSR_{fig_label}_hvsr_pro.png"),
                           plot_type='standard', dpi=dpi,
                           show_peaks=True, show_uncertainty=True,
                           title=fig_title)
            logging.info("Saved HVSR_%s_hvsr_pro.png", fig_label)
            total_saved += 1
        except Exception as _e:
            logging.warning("Could not save hvsr_pro standard figure: %s", _e)

    # ── Figure 3: hvsr_pro statistics 4-panel ────────────────────────────
    if fig_statistics and _hvsr_pro_ok:
        logging.info("Generating statistics 4-panel figure...")
        try:
            from hvsr_pro.visualization.hvsr_plots import save_hvsr_plot
            save_hvsr_plot(hvsr_result_obj,
                           str(output_dir / f"HVSR_{fig_label}_statistics.png"),
                           plot_type='statistics', dpi=dpi)
            logging.info("Saved HVSR_%s_statistics.png", fig_label)
            total_saved += 1
        except Exception as _e:
            logging.warning("Could not save statistics figure: %s", _e)

        if save_pdf:
            try:
                from hvsr_pro.visualization.hvsr_plots import save_hvsr_plot
                save_hvsr_plot(hvsr_result_obj,
                               str(output_dir / f"HVSR_{fig_label}_statistics.pdf"),
                               plot_type='statistics', dpi=dpi)
                logging.info("Saved HVSR_%s_statistics.pdf", fig_label)
                total_saved += 1
            except Exception as _e:
                logging.warning("Could not save statistics PDF: %s", _e)

    # ── Additional figures from FigureExportDialog config ────────────────
    if fig_config and _hvsr_pro_ok:
        total_saved += _generate_detailed_figures(
            hvsr_result_obj, window_collection, seismic_data,
            peaks, freq_ref, hv_mean,
            combined_hv, accepted_indices, n_windows,
            output_dir, fig_label, fig_config,
            dpi, smart_ylim)

    logging.info("Figure generation complete: %d figures saved", total_saved)
    return total_saved


def _generate_detailed_figures(
    hvsr_result_obj, window_collection, seismic_data,
    peaks, freq_ref, hv_mean,
    combined_hv, accepted_indices, n_windows,
    output_dir, fig_label, fig_config,
    default_dpi, smart_ylim,
):
    """Generate all figures enabled in the FigureExportDialog config."""
    cfg_dpi = int(fig_config.get('dpi', default_dpi))
    cfg_fmt = fig_config.get('format', 'png')
    cfg_sz = fig_config.get('figsize', 'Standard (10x7)')
    figsize = _SIZE_MAP.get(cfg_sz, (10, 7))
    saved = 0

    def _save(fig_obj, name):
        nonlocal saved
        out = output_dir / f"HVSR_{fig_label}_{name}.{cfg_fmt}"
        fig_obj.savefig(str(out), dpi=cfg_dpi, bbox_inches='tight')
        logging.info("Saved %s", out.name)
        saved += 1

    def _make_fig():
        f = _Fig(figsize=figsize)
        _AggCanvas(f)
        return f

    # ── HVSR Curve with uncertainty
    if fig_config.get('fig_hvsr_curve', False):
        try:
            from hvsr_pro.visualization.hvsr_plots import plot_hvsr_curve
            _fig = _make_fig()
            _ax = _fig.add_subplot(111)
            plot_hvsr_curve(hvsr_result_obj, ax=_ax,
                            show_uncertainty=True, show_peaks=True)
            _save(_fig, 'hvsr_curve')
        except Exception as _e:
            logging.warning("fig_hvsr_curve failed: %s", _e)

    # ── Mean vs Median
    if fig_config.get('fig_mean_vs_median', False):
        try:
            from hvsr_pro.visualization.plotter import HVSRPlotter
            _fig = HVSRPlotter().plot_mean_vs_median(hvsr_result_obj)
            if _fig:
                _save(_fig, 'mean_vs_median')
        except Exception as _e:
            logging.warning("fig_mean_vs_median failed: %s", _e)

    # ── Component Spectra
    if fig_config.get('fig_components', False):
        try:
            from hvsr_pro.visualization.hvsr_plots import plot_hvsr_components
            _fig = _make_fig()
            _fig = plot_hvsr_components(hvsr_result_obj, fig=_fig)
            if _fig:
                _save(_fig, 'components')
        except Exception as _e:
            logging.warning("fig_components failed: %s", _e)

    # ── Peak Analysis
    if fig_config.get('fig_peak_analysis', False):
        try:
            from hvsr_pro.visualization.hvsr_plots import plot_peak_analysis
            if peaks:
                n_pk = len(peaks)
                _fig = _Fig(figsize=(figsize[0], figsize[1] // max(1, n_pk) + 3))
                _AggCanvas(_fig)
                axes = _fig.subplots(1, n_pk, squeeze=False)[0]
                for pi, pk in enumerate(peaks):
                    plot_peak_analysis(pk, freq_ref, hv_mean, ax=axes[pi])
                _fig.tight_layout()
                _save(_fig, 'peak_analysis')
            else:
                logging.info("fig_peak_analysis skipped: no peaks")
        except Exception as _e:
            logging.warning("fig_peak_analysis failed: %s", _e)

    # ── Window Collection Overview
    if fig_config.get('fig_window_overview', False):
        if window_collection is not None:
            try:
                from hvsr_pro.visualization.window_plots import (
                    plot_window_collection_overview)
                _fig = plot_window_collection_overview(window_collection)
                if _fig:
                    _save(_fig, 'window_overview')
            except Exception as _e:
                logging.warning("fig_window_overview failed: %s", _e)
        else:
            logging.info("fig_window_overview skipped: no WindowCollection")

    # ── Quality Metrics Grid
    if fig_config.get('fig_quality_grid', False):
        if window_collection is not None:
            try:
                from hvsr_pro.visualization.window_plots import (
                    plot_quality_metrics_grid)
                _fig = plot_quality_metrics_grid(window_collection)
                if _fig:
                    _save(_fig, 'quality_grid')
            except Exception as _e:
                logging.warning("fig_quality_grid failed: %s", _e)
        else:
            logging.info("fig_quality_grid skipped: no WindowCollection")

    # ── Rejection Timeline
    if fig_config.get('fig_rejection_timeline', False):
        if window_collection is not None:
            try:
                from hvsr_pro.visualization.window_plots import (
                    plot_rejection_timeline)
                _fig = _make_fig()
                _ax = _fig.add_subplot(111)
                plot_rejection_timeline(window_collection, ax=_ax)
                _save(_fig, 'rejection_timeline')
            except Exception as _e:
                logging.warning("fig_rejection_timeline failed: %s", _e)
        else:
            logging.info("fig_rejection_timeline skipped: no WindowCollection")

    # ── Raw vs Adjusted HVSR
    if fig_config.get('fig_raw_vs_adjusted', False):
        try:
            from hvsr_pro.visualization.comparison_plot import (
                plot_raw_vs_adjusted_hvsr)
            _all_idx = list(range(n_windows))
            _acc_idx = [int(i) for i in accepted_indices]
            _pk_idx = np.array([np.argmax(combined_hv[:, w])
                                for w in range(n_windows)])
            _pk_hz = freq_ref[_pk_idx]
            _pk_amp = np.array([combined_hv[_pk_idx[w], w]
                                for w in range(n_windows)])
            _fig = plot_raw_vs_adjusted_hvsr(
                frequency=freq_ref,
                hvsr_all_windows=combined_hv,
                hvsr_accepted_windows=combined_hv[:, _acc_idx],
                window_indices_all=_all_idx,
                window_indices_accepted=_acc_idx,
                peak_freq_all=_pk_hz,
                peak_amp_all=_pk_amp,
                station_name=fig_label,
                freq_range=(float(freq_ref[0]), float(freq_ref[-1])),
                figsize=(figsize[0] + 2, figsize[1] + 3),
                dpi=cfg_dpi)
            if _fig:
                if smart_ylim is not None:
                    for _ax in _fig.get_axes():
                        if _ax.get_ylabel() == 'HVSR':
                            _ax.set_ylim(0, smart_ylim)
                _save(_fig, 'raw_vs_adjusted')
        except Exception as _e:
            logging.warning("fig_raw_vs_adjusted failed: %s", _e)

    # ── Pre & Post Rejection
    if fig_config.get('fig_pre_post_rejection', False):
        if seismic_data is not None and window_collection is not None:
            try:
                from hvsr_pro.visualization.waveform_plot import (
                    plot_pre_and_post_rejection)
                _fig = plot_pre_and_post_rejection(
                    seismic_data, hvsr_result_obj, window_collection,
                    station_name=fig_label,
                    figsize=(figsize[0] + 4, figsize[1] + 4),
                    dpi=cfg_dpi)
                if _fig:
                    _save(_fig, 'pre_post_rejection')
            except Exception as _e:
                logging.warning("fig_pre_post_rejection failed: %s", _e)
        else:
            logging.info("fig_pre_post_rejection skipped: missing objects")

    # ── 3-Component Waveform
    if fig_config.get('fig_waveform_3c', False):
        if seismic_data is not None:
            try:
                from hvsr_pro.visualization.waveform_plot import (
                    plot_seismic_recordings_3c)
                _fig = plot_seismic_recordings_3c(
                    seismic_data, windows=window_collection,
                    normalize=True, figsize=figsize, dpi=cfg_dpi)
                if _fig:
                    _save(_fig, 'waveform_3c')
            except Exception as _e:
                logging.warning("fig_waveform_3c failed: %s", _e)
        else:
            logging.info("fig_waveform_3c skipped: no SeismicData")

    # ── Dashboard (composite)
    if fig_config.get('fig_dashboard', False):
        if window_collection is not None:
            try:
                from hvsr_pro.visualization.plotter import HVSRPlotter
                _fig = HVSRPlotter().create_interactive_dashboard(
                    hvsr_result_obj, window_collection,
                    figsize=(figsize[0] + 4, figsize[1] + 3))
                if _fig:
                    _save(_fig, 'dashboard')
            except Exception as _e:
                logging.warning("fig_dashboard failed: %s", _e)
        else:
            logging.info("fig_dashboard skipped: no WindowCollection")

    # ── Peak Details
    if fig_config.get('fig_peak_details', False):
        try:
            from hvsr_pro.visualization.plotter import HVSRPlotter
            _fig = HVSRPlotter().plot_peak_details(hvsr_result_obj)
            if _fig:
                _save(_fig, 'peak_details')
        except Exception as _e:
            logging.warning("fig_peak_details failed: %s", _e)

    # ── HVSR with Individual Windows overlay
    if fig_config.get('fig_with_windows', False):
        try:
            from hvsr_pro.visualization.plotter import HVSRPlotter
            _fig = HVSRPlotter().plot_with_windows(hvsr_result_obj)
            if _fig:
                if smart_ylim is not None:
                    for _ax in _fig.get_axes():
                        _yl = _ax.get_ylabel()
                        if 'H/V' in _yl or 'HVSR' in _yl:
                            _ax.set_ylim(0, smart_ylim)
                _save(_fig, 'with_windows')
        except Exception as _e:
            logging.warning("fig_with_windows failed: %s", _e)

    # ── Quality Score Distribution
    if fig_config.get('fig_quality_histogram', False):
        if window_collection is not None:
            try:
                from hvsr_pro.visualization.plotter import HVSRPlotter
                _fig = HVSRPlotter().plot_quality_histogram(window_collection)
                if _fig:
                    _save(_fig, 'quality_histogram')
            except Exception as _e:
                logging.warning("fig_quality_histogram failed: %s", _e)
        else:
            logging.info("fig_quality_histogram skipped: no WindowCollection")

    # ── Window Timeseries
    if fig_config.get('fig_window_timeseries', False):
        if window_collection is not None and seismic_data is not None:
            try:
                from hvsr_pro.visualization.plotter import HVSRPlotter
                _fig = HVSRPlotter().plot_window_timeseries(
                    window_collection, seismic_data)
                if _fig:
                    _save(_fig, 'window_timeseries')
            except Exception as _e:
                logging.warning("fig_window_timeseries failed: %s", _e)
        else:
            logging.info("fig_window_timeseries skipped: missing objects")

    # ── Window Spectrogram
    if fig_config.get('fig_window_spectrogram', False):
        if window_collection is not None and seismic_data is not None:
            try:
                from hvsr_pro.visualization.plotter import HVSRPlotter
                _fig = HVSRPlotter().plot_window_spectrogram(
                    window_collection, seismic_data)
                if _fig:
                    _save(_fig, 'window_spectrogram')
            except Exception as _e:
                logging.warning("fig_window_spectrogram failed: %s", _e)
        else:
            logging.info("fig_window_spectrogram skipped: missing objects")

    logging.info("Detailed figure generation: %d saved, %d types enabled",
                 saved,
                 sum(1 for k, v in fig_config.items()
                     if k.startswith('fig_') and v))
    return saved


def build_hvsr_pro_objects(freq_ref, hv_mean, hv_median, hv_std,
                           hv_16, hv_84, peaks,
                           combined_hv, accepted_indices, n_windows,
                           rejected_mask, rejected_reasons,
                           array_e, array_n, array_z,
                           sample_rate, n_per_win,
                           fig_label, time_win_sec,
                           all_emag=None, all_nmag=None,
                           all_zmag=None, all_horiz=None):
    """Build hvsr_pro HVSRResult, WindowCollection, SeismicData objects.

    Returns
    -------
    tuple
        (hvsr_result_obj, window_collection, seismic_data)
        Any element may be None if hvsr_pro is not available.
    """
    try:
        from hvsr_pro.processing.hvsr.structures import (
            HVSRResult as HVSRProResult,
            WindowSpectrum as HVSRProWindowSpectrum,
        )
        from hvsr_pro.core.data_structures import ComponentData, SeismicData
        from hvsr_pro.processing.windows.structures import (
            Window as HVSRProWindow,
            WindowCollection as HVSRProWindowCollection,
            WindowState as HVSRProWindowState,
        )
    except ImportError as e:
        logging.warning("hvsr_pro not available (%s), skipping object build", e)
        return None, None, None

    # SeismicData
    seismic_data = SeismicData(
        east=ComponentData("E", array_e, float(sample_rate)),
        north=ComponentData("N", array_n, float(sample_rate)),
        vertical=ComponentData("Z", array_z, float(sample_rate)),
        station_name=fig_label,
    )

    # WindowCollection
    win_list = []
    for wi in range(n_windows):
        i0 = wi * n_per_win
        i1 = (wi + 1) * n_per_win
        win_data = SeismicData(
            east=ComponentData("E", array_e[i0:i1], float(sample_rate)),
            north=ComponentData("N", array_n[i0:i1], float(sample_rate)),
            vertical=ComponentData("Z", array_z[i0:i1], float(sample_rate)),
            station_name=fig_label,
        )
        ws = (HVSRProWindowState.ACTIVE
              if not rejected_mask[wi]
              else HVSRProWindowState.REJECTED_AUTO)
        win = HVSRProWindow(
            index=wi, start_sample=i0, end_sample=i1,
            data=win_data, state=ws,
            rejection_reason=(rejected_reasons[wi]
                              if rejected_mask[wi] else None),
        )
        win_list.append(win)

    window_collection = HVSRProWindowCollection(
        windows=win_list, source_data=seismic_data,
        window_length=float(time_win_sec), overlap=0.0,
    )

    # WindowSpectrum list
    wspectra = []
    if (all_emag is not None and all_nmag is not None
            and all_zmag is not None and all_horiz is not None):
        for wi in range(n_windows):
            wsp = HVSRProWindowSpectrum(
                window_index=wi, frequencies=freq_ref,
                east_spectrum=all_emag[wi],
                north_spectrum=all_nmag[wi],
                vertical_spectrum=all_zmag[wi],
                horizontal_spectrum=all_horiz[wi],
                hvsr=combined_hv[:, wi],
                is_valid=not rejected_mask[wi],
            )
            wspectra.append(wsp)

    # HVSRResult
    hvsr_result_obj = HVSRProResult(
        frequencies=freq_ref,
        mean_hvsr=hv_mean,
        median_hvsr=hv_median,
        std_hvsr=hv_std,
        percentile_16=hv_16,
        percentile_84=hv_84,
        valid_windows=len(accepted_indices),
        total_windows=n_windows,
        peaks=peaks,
        window_spectra=wspectra if wspectra else None,
    )
    logging.info("Built hvsr_pro objects: %d windows (%d active), %d spectra",
                 n_windows, len(accepted_indices), len(wspectra))

    return hvsr_result_obj, window_collection, seismic_data
