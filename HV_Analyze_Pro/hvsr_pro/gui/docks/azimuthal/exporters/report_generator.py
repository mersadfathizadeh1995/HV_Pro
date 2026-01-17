"""
Report Generator
================

Comprehensive report generation for azimuthal HVSR analysis.
"""

import os
from typing import Any, Dict, List, Optional, Callable
import matplotlib.pyplot as plt


class ReportGenerator:
    """
    Generates comprehensive azimuthal HVSR reports.
    
    Creates multiple figure types and data files based on user selections.
    """
    
    def __init__(self, result: Any, options: Dict[str, Any]):
        """
        Initialize report generator.
        
        Args:
            result: AzimuthalHVSRResult object
            options: Plot options dictionary with keys like 'cmap', 'legend_loc', etc.
        """
        self.result = result
        self.options = options
    
    def generate(
        self,
        output_dir: str,
        selections: Dict[str, Any],
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> List[str]:
        """
        Generate report files.
        
        Args:
            output_dir: Directory to save files
            selections: Selection dict from ExportReportDialog.get_selections()
            progress_callback: Optional callback(label: str, step: int) for progress
            
        Returns:
            List of created file paths
        """
        from hvsr_pro.processing.azimuthal import (
            plot_azimuthal_contour_2d,
            plot_azimuthal_contour_3d,
            plot_azimuthal_summary
        )
        from .data_exporter import (
            write_csv, write_json, write_individual_csv, write_peaks_csv
        )
        
        created_files = []
        current_step = 0
        dpi = selections['dpi']
        fmt = selections['format']
        formats = ['png', 'pdf', 'svg'] if fmt == 'all formats' else [fmt]
        opts = self.options
        
        def update_progress(label: str):
            nonlocal current_step
            if progress_callback:
                progress_callback(label, current_step)
            current_step += 1
        
        # === GENERATE FIGURES ===
        figures_sel = selections['figures']
        
        if figures_sel.get('summary'):
            update_progress("Generating summary plot...")
            for ext in formats:
                fig, _ = plot_azimuthal_summary(
                    self.result,
                    figsize=(12, 10),
                    dpi=dpi,
                    cmap=opts.get('cmap', 'plasma'),
                    legend_loc=opts.get('legend_loc', 'outside_right'),
                    plot_mean_curve_peak_by_azimuth=opts.get('show_peaks', True),
                    plot_individual_curves=opts.get('show_individual_curves', True),
                    show_panel_labels=opts.get('show_panel_labels', True),
                    title_fontsize=opts.get('title_fontsize', 14),
                    axis_fontsize=opts.get('axis_fontsize', 10),
                    tick_fontsize=opts.get('tick_fontsize', 8),
                    legend_fontsize=opts.get('legend_fontsize', 8)
                )
                filepath = os.path.join(output_dir, f"azimuthal_summary.{ext}")
                fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
                plt.close(fig)
                created_files.append(filepath)
        
        if figures_sel.get('3d'):
            update_progress("Generating 3D surface plot...")
            for ext in formats:
                fig = plt.figure(figsize=(10, 8), dpi=dpi)
                ax = fig.add_subplot(111, projection='3d')
                plot_azimuthal_contour_3d(
                    self.result,
                    ax=ax,
                    cmap=opts.get('cmap', 'plasma'),
                    plot_mean_curve_peak_by_azimuth=opts.get('show_peaks', True)
                )
                ax.set_xlabel("Frequency (Hz)", fontsize=opts.get('axis_fontsize', 10))
                ax.set_ylabel("Azimuth (deg)", fontsize=opts.get('axis_fontsize', 10))
                ax.set_zlabel("HVSR Amplitude", fontsize=opts.get('axis_fontsize', 10))
                fig.suptitle("3D Azimuthal HVSR", fontsize=opts.get('title_fontsize', 14), fontweight='bold')
                
                filepath = os.path.join(output_dir, f"azimuthal_3d.{ext}")
                fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
                plt.close(fig)
                created_files.append(filepath)
        
        if figures_sel.get('2d'):
            update_progress("Generating 2D contour plot...")
            for ext in formats:
                fig, ax = plt.subplots(figsize=(10, 6), dpi=dpi)
                plot_azimuthal_contour_2d(
                    self.result,
                    ax=ax,
                    cmap=opts.get('cmap', 'plasma'),
                    plot_mean_curve_peak_by_azimuth=opts.get('show_peaks', True)
                )
                ax.set_xlabel("Frequency (Hz)", fontsize=opts.get('axis_fontsize', 10))
                ax.set_ylabel("Azimuth (deg)", fontsize=opts.get('axis_fontsize', 10))
                fig.suptitle("2D Azimuthal HVSR Contour", fontsize=opts.get('title_fontsize', 14), fontweight='bold')
                
                filepath = os.path.join(output_dir, f"azimuthal_2d.{ext}")
                fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
                plt.close(fig)
                created_files.append(filepath)
        
        if figures_sel.get('polar'):
            update_progress("Generating polar plot...")
            try:
                from hvsr_pro.processing.azimuthal import plot_azimuthal_polar
                for ext in formats:
                    fig = plt.figure(figsize=(8, 8), dpi=dpi)
                    ax = fig.add_subplot(111, projection='polar')
                    plot_azimuthal_polar(
                        self.result,
                        ax=ax,
                        cmap=opts.get('cmap', 'plasma'),
                        title_fontsize=opts.get('title_fontsize', 14),
                        axis_fontsize=opts.get('axis_fontsize', 10),
                        tick_fontsize=opts.get('tick_fontsize', 8)
                    )
                    
                    filepath = os.path.join(output_dir, f"azimuthal_polar.{ext}")
                    fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
                    plt.close(fig)
                    created_files.append(filepath)
            except Exception as e:
                print(f"Warning: Could not generate polar plot: {e}")
        
        if figures_sel.get('curves'):
            update_progress("Generating individual curves plot...")
            try:
                from hvsr_pro.processing.azimuthal import plot_azimuthal_curves
                for ext in formats:
                    fig, ax = plt.subplots(figsize=(10, 6), dpi=dpi)
                    plot_azimuthal_curves(
                        self.result,
                        ax=ax,
                        cmap=opts.get('cmap', 'plasma'),
                        title_fontsize=opts.get('title_fontsize', 14),
                        axis_fontsize=opts.get('axis_fontsize', 10),
                        tick_fontsize=opts.get('tick_fontsize', 8),
                        legend_fontsize=opts.get('legend_fontsize', 8)
                    )
                    
                    filepath = os.path.join(output_dir, f"azimuthal_curves.{ext}")
                    fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
                    plt.close(fig)
                    created_files.append(filepath)
            except Exception as e:
                print(f"Warning: Could not generate curves plot: {e}")
        
        # === GENERATE DATA FILES ===
        data_sel = selections['data']
        
        if data_sel.get('csv_mean'):
            update_progress("Exporting mean curves CSV...")
            filepath = os.path.join(output_dir, "azimuthal_mean_curves.csv")
            write_csv(filepath, self.result)
            created_files.append(filepath)
        
        if data_sel.get('csv_individual'):
            update_progress("Exporting individual curves CSV...")
            filepath = os.path.join(output_dir, "azimuthal_individual_curves.csv")
            write_individual_csv(filepath, self.result)
            created_files.append(filepath)
        
        if data_sel.get('json'):
            update_progress("Exporting JSON data...")
            filepath = os.path.join(output_dir, "azimuthal_results.json")
            write_json(filepath, self.result)
            created_files.append(filepath)
        
        if data_sel.get('peaks'):
            update_progress("Exporting peak frequencies...")
            filepath = os.path.join(output_dir, "azimuthal_peak_frequencies.csv")
            write_peaks_csv(filepath, self.result)
            created_files.append(filepath)
        
        return created_files
