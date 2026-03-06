"""
Output Organizer
=================

Handles organized folder structure and export to Excel/MAT formats.
Supports Topic/Diameter-based organization (e.g., 200m, 300m, 500m arrays).
"""

import os
import numpy as np
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    from scipy.io import savemat
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


class OutputOrganizer:
    """
    Organizes HVSR output into structured folders by topic/diameter.
    
    Folder Structure:
        output_dir/
        ├── 200/
        │   ├── STN01/
        │   │   ├── ArrayData_STN01.mat
        │   │   └── HVSR_STN01.png
        │   └── STN02/
        ├── 300/
        │   └── ...
        ├── SITE_HVSRData.xlsx
        ├── HV_Peaks_SITE.xlsx
        └── SITE_HVSRData.mat
    """
    
    def __init__(self, output_dir: str, site_name: str = "SITE"):
        """
        Initialize output organizer.
        
        Args:
            output_dir: Root output directory
            site_name: Site name for file naming
        """
        self.output_dir = Path(output_dir)
        self.site_name = site_name
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def create_topic_folder(self, topic: str) -> Path:
        """
        Create folder for a topic/diameter.
        
        Args:
            topic: Topic name (e.g., "200", "300", "500")
            
        Returns:
            Path to the created folder
        """
        topic_dir = self.output_dir / str(topic)
        topic_dir.mkdir(parents=True, exist_ok=True)
        return topic_dir
    
    def create_station_folder(self, topic: str, station_name: str) -> Path:
        """
        Create folder for a station within a topic.
        
        Args:
            topic: Topic name
            station_name: Station name
            
        Returns:
            Path to the created folder
        """
        station_dir = self.output_dir / str(topic) / station_name
        station_dir.mkdir(parents=True, exist_ok=True)
        return station_dir
    
    def get_station_output_path(self, topic: str, station_name: str, 
                                 filename: str) -> Path:
        """
        Get full path for a station output file.
        
        Args:
            topic: Topic name
            station_name: Station name
            filename: File name
            
        Returns:
            Full path to the file
        """
        station_dir = self.create_station_folder(topic, station_name)
        return station_dir / filename
    
    def export_hvsr_excel(self, 
                          station_results: List[Dict[str, Any]],
                          filename: Optional[str] = None) -> str:
        """
        Export all HVSR curves to Excel file.
        
        Creates a file with columns:
        - Frequency
        - Station1_Mean, Station1_Std
        - Station2_Mean, Station2_Std
        - ...
        
        Args:
            station_results: List of station result dictionaries
            filename: Output filename (default: SITE_HVSRData.xlsx)
            
        Returns:
            Path to the created file
        """
        if not HAS_PANDAS:
            raise ImportError("pandas is required for Excel export")
        
        if not station_results:
            raise ValueError("No station results to export")
        
        filename = filename or f"{self.site_name}_HVSRData.xlsx"
        filepath = self.output_dir / filename
        
        # Get frequency array from first station
        frequencies = np.array(station_results[0]['frequencies'])
        
        # Build DataFrame
        data = {'Frequency_Hz': frequencies}
        
        # Group by topic
        topics = sorted(set(s.get('topic', 'Default') for s in station_results))
        
        for topic in topics:
            topic_stations = [s for s in station_results if s.get('topic', 'Default') == topic]
            
            for station in topic_stations:
                name = station['station_name']
                prefix = f"{topic}_{name}" if len(topics) > 1 else name
                
                mean_hvsr = np.array(station['mean_hvsr'])
                std_hvsr = np.array(station.get('std_hvsr', np.zeros_like(mean_hvsr)))
                
                # Ensure same length
                if len(mean_hvsr) == len(frequencies):
                    data[f'{prefix}_Mean'] = mean_hvsr
                    data[f'{prefix}_Std'] = std_hvsr
        
        df = pd.DataFrame(data)
        
        # Write to Excel with formatting
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='HVSR_Data', index=False)
            
            # Add summary sheet
            summary_data = []
            for station in station_results:
                row = {
                    'Station': station['station_name'],
                    'Topic': station.get('topic', 'Default'),
                    'Valid_Windows': station.get('valid_windows', 0),
                    'Total_Windows': station.get('total_windows', 0),
                }
                
                # Add peak info
                peaks = station.get('peaks', [])
                for i, peak in enumerate(peaks[:5], start=1):
                    if isinstance(peak, dict):
                        row[f'Peak{i}_Freq_Hz'] = peak.get('frequency', 0)
                        row[f'Peak{i}_Amp'] = peak.get('amplitude', 0)
                    else:
                        row[f'Peak{i}_Freq_Hz'] = peak.frequency
                        row[f'Peak{i}_Amp'] = peak.amplitude
                
                summary_data.append(row)
            
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
        
        return str(filepath)
    
    def export_peaks_excel(self,
                           station_results: List[Dict[str, Any]],
                           peak_statistics: Optional[List[Dict[str, Any]]] = None,
                           filename: Optional[str] = None) -> str:
        """
        Export peak summary to Excel file.
        
        Args:
            station_results: List of station result dictionaries
            peak_statistics: Optional peak statistics from automatic workflow
            filename: Output filename (default: HV_Peaks_SITE.xlsx)
            
        Returns:
            Path to the created file
        """
        if not HAS_PANDAS:
            raise ImportError("pandas is required for Excel export")
        
        filename = filename or f"HV_Peaks_{self.site_name}.xlsx"
        filepath = self.output_dir / filename
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Station peaks sheet
            station_peaks = []
            for station in station_results:
                base_row = {
                    'Station': station['station_name'],
                    'Topic': station.get('topic', 'Default'),
                }
                
                peaks = station.get('peaks', [])
                for i, peak in enumerate(peaks[:5], start=1):
                    if isinstance(peak, dict):
                        base_row[f'Peak{i}_Freq_Hz'] = peak.get('frequency', '')
                        base_row[f'Peak{i}_Amp'] = peak.get('amplitude', '')
                        base_row[f'Peak{i}_Prom'] = peak.get('prominence', '')
                    else:
                        base_row[f'Peak{i}_Freq_Hz'] = peak.frequency
                        base_row[f'Peak{i}_Amp'] = peak.amplitude
                        base_row[f'Peak{i}_Prom'] = peak.prominence
                
                station_peaks.append(base_row)
            
            peaks_df = pd.DataFrame(station_peaks)
            peaks_df.to_excel(writer, sheet_name='Station_Peaks', index=False)
            
            # Peak statistics sheet (if available)
            if peak_statistics:
                stats_data = []
                for stat in peak_statistics:
                    if isinstance(stat, dict):
                        stats_data.append(stat)
                    else:
                        stats_data.append(stat.to_dict())
                
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Peak_Statistics', index=False)
        
        return str(filepath)
    
    def export_hvsr_mat(self,
                        station_results: List[Dict[str, Any]],
                        combined_result: Optional[Dict[str, Any]] = None,
                        filename: Optional[str] = None) -> str:
        """
        Export HVSR data to MATLAB .mat file.
        
        Args:
            station_results: List of station result dictionaries
            combined_result: Optional combined/median result
            filename: Output filename (default: SITE_HVSRData.mat)
            
        Returns:
            Path to the created file
        """
        if not HAS_SCIPY:
            raise ImportError("scipy is required for MAT export")
        
        filename = filename or f"{self.site_name}_HVSRData.mat"
        filepath = self.output_dir / filename
        
        mat_dict = {
            'site_name': self.site_name,
            'n_stations': len(station_results),
            'export_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        # Get frequency array
        if station_results:
            mat_dict['frequencies'] = np.array(station_results[0]['frequencies'])
        
        # Station data
        station_names = []
        station_topics = []
        hvsr_mean_all = []
        hvsr_std_all = []
        peak_freqs_all = []
        peak_amps_all = []
        
        for station in station_results:
            station_names.append(station['station_name'])
            station_topics.append(station.get('topic', 'Default'))
            
            mean_hvsr = np.array(station['mean_hvsr'])
            std_hvsr = np.array(station.get('std_hvsr', np.zeros_like(mean_hvsr)))
            
            hvsr_mean_all.append(mean_hvsr)
            hvsr_std_all.append(std_hvsr)
            
            # Peak data
            peaks = station.get('peaks', [])
            freqs = []
            amps = []
            for peak in peaks[:5]:
                if isinstance(peak, dict):
                    freqs.append(peak.get('frequency', 0))
                    amps.append(peak.get('amplitude', 0))
                else:
                    freqs.append(peak.frequency)
                    amps.append(peak.amplitude)
            
            # Pad to 5 peaks
            while len(freqs) < 5:
                freqs.append(np.nan)
                amps.append(np.nan)
            
            peak_freqs_all.append(freqs)
            peak_amps_all.append(amps)
        
        mat_dict['station_names'] = np.array(station_names, dtype=object)
        mat_dict['station_topics'] = np.array(station_topics, dtype=object)
        mat_dict['hvsr_mean'] = np.array(hvsr_mean_all)
        mat_dict['hvsr_std'] = np.array(hvsr_std_all)
        mat_dict['peak_frequencies'] = np.array(peak_freqs_all)
        mat_dict['peak_amplitudes'] = np.array(peak_amps_all)
        
        # Combined result
        if combined_result:
            if 'median_hvsr' in combined_result and combined_result['median_hvsr'] is not None:
                mat_dict['median_hvsr'] = np.array(combined_result['median_hvsr'])
            if 'mean_hvsr' in combined_result and combined_result['mean_hvsr'] is not None:
                mat_dict['combined_mean_hvsr'] = np.array(combined_result['mean_hvsr'])
            if 'std_hvsr' in combined_result and combined_result['std_hvsr'] is not None:
                mat_dict['combined_std_hvsr'] = np.array(combined_result['std_hvsr'])
        
        savemat(str(filepath), mat_dict)
        
        return str(filepath)
    
    def export_all(self,
                   station_results: List[Dict[str, Any]],
                   combined_result: Optional[Dict[str, Any]] = None,
                   peak_statistics: Optional[List[Dict[str, Any]]] = None) -> Dict[str, str]:
        """
        Export all output files (Excel and MAT).
        
        Args:
            station_results: List of station result dictionaries
            combined_result: Optional combined/median result
            peak_statistics: Optional peak statistics
            
        Returns:
            Dictionary of exported file paths
        """
        exported = {}
        
        # Export Excel files
        if HAS_PANDAS:
            try:
                exported['hvsr_excel'] = self.export_hvsr_excel(station_results)
            except Exception as e:
                exported['hvsr_excel_error'] = str(e)
            
            try:
                exported['peaks_excel'] = self.export_peaks_excel(
                    station_results, peak_statistics
                )
            except Exception as e:
                exported['peaks_excel_error'] = str(e)
        
        # Export MAT file
        if HAS_SCIPY:
            try:
                exported['hvsr_mat'] = self.export_hvsr_mat(
                    station_results, combined_result
                )
            except Exception as e:
                exported['hvsr_mat_error'] = str(e)
        
        return exported


def organize_by_topic(station_files: Dict[int, List[str]],
                      topics: Dict[int, str],
                      output_dir: str) -> Dict[str, Dict[int, str]]:
    """
    Organize station files by topic into folder structure.
    
    Args:
        station_files: Dict mapping station_id to file list
        topics: Dict mapping station_id to topic string
        output_dir: Root output directory
        
    Returns:
        Dict mapping topic to {station_id: output_dir}
    """
    organizer = OutputOrganizer(output_dir)
    result = {}
    
    for station_id, files in station_files.items():
        topic = topics.get(station_id, 'Default')
        station_name = f"STN{station_id:02d}"
        
        station_dir = organizer.create_station_folder(topic, station_name)
        
        if topic not in result:
            result[topic] = {}
        result[topic][station_id] = str(station_dir)
    
    return result


def create_time_window_table_data(time_windows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Create table data for time windows with topic column.
    
    Args:
        time_windows: List of time window dictionaries with keys:
            - start: Start datetime
            - end: End datetime
            - topic: Topic/diameter string (optional)
            
    Returns:
        List of row dictionaries for table display
    """
    rows = []
    for i, tw in enumerate(time_windows, start=1):
        start = tw['start']
        end = tw['end']
        topic = tw.get('topic', '')
        
        rows.append({
            'Figure': f"HV{i}",
            'Start_Time': start.strftime('%Y-%m-%d %H:%M:%S') if hasattr(start, 'strftime') else str(start),
            'End_Time': end.strftime('%Y-%m-%d %H:%M:%S') if hasattr(end, 'strftime') else str(end),
            'Topic': topic,
        })
    
    return rows
