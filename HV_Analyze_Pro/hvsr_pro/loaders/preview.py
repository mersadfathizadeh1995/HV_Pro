"""
Data Loading Preview Utilities
==============================

Provides preview data extraction and metadata retrieval for all supported formats.
Used by the component mapper dialog to show waveform previews before loading.
"""

import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple, Union
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class ChannelPreview:
    """
    Preview data for a single channel.
    
    Attributes:
        name: Channel identifier (auto-detected or user-provided)
        detected_component: Auto-detected component type (E, N, Z, or None)
        data: Sample waveform data (subset for preview)
        full_length: Total number of samples in file
        sampling_rate: Sampling rate in Hz
        min_val: Minimum amplitude
        max_val: Maximum amplitude
        mean_val: Mean amplitude
        std_val: Standard deviation
        source_file: Source file path (for multi-file formats)
    """
    name: str
    detected_component: Optional[str] = None
    data: np.ndarray = field(default_factory=lambda: np.array([]))
    full_length: int = 0
    sampling_rate: float = 0.0
    min_val: float = 0.0
    max_val: float = 0.0
    mean_val: float = 0.0
    std_val: float = 0.0
    source_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'detected_component': self.detected_component,
            'data': self.data.tolist() if len(self.data) > 0 else [],
            'full_length': self.full_length,
            'sampling_rate': self.sampling_rate,
            'min_val': self.min_val,
            'max_val': self.max_val,
            'mean_val': self.mean_val,
            'std_val': self.std_val,
            'source_file': self.source_file
        }


@dataclass
class PreviewData:
    """
    Complete preview data for a seismic file or file set.
    
    Attributes:
        format: Detected format name
        channels: List of channel previews
        metadata: Additional format-specific metadata
        detected_mapping: Auto-detected component mapping {component: channel_index}
        duration_seconds: Total duration in seconds
        error: Error message if preview failed
    """
    format: str
    channels: List[ChannelPreview] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    detected_mapping: Dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0.0
    error: Optional[str] = None
    
    @property
    def n_channels(self) -> int:
        """Number of channels."""
        return len(self.channels)
    
    @property
    def has_all_components(self) -> bool:
        """Check if all E, N, Z components were detected."""
        detected = set(c.detected_component for c in self.channels if c.detected_component)
        return {'E', 'N', 'Z'}.issubset(detected)
    
    def get_channel_by_component(self, component: str) -> Optional[ChannelPreview]:
        """Get channel preview by detected component."""
        for channel in self.channels:
            if channel.detected_component == component:
                return channel
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'format': self.format,
            'channels': [c.to_dict() for c in self.channels],
            'metadata': self.metadata,
            'detected_mapping': self.detected_mapping,
            'duration_seconds': self.duration_seconds,
            'error': self.error
        }


class PreviewExtractor:
    """
    Unified preview extraction for all supported formats.
    
    Provides methods to extract preview data without fully loading files.
    Used by the component mapper dialog.
    
    Example:
        >>> extractor = PreviewExtractor()
        >>> preview = extractor.get_preview('data.saf', n_samples=1000)
        >>> for channel in preview.channels:
        ...     print(f"{channel.name}: {channel.detected_component}")
    """
    
    def __init__(self):
        """Initialize preview extractor."""
        self._format_handlers = {
            'saf': self._preview_saf,
            'sac': self._preview_sac,
            'gcf': self._preview_gcf,
            'peer': self._preview_peer,
            'miniseed': self._preview_miniseed,
            'mseed': self._preview_miniseed,
            'txt': self._preview_txt,
            'csv': self._preview_txt,
            'dat': self._preview_txt,
            'minishark': self._preview_minishark,
            'srecord3c': self._preview_srecord3c,
            'json': self._preview_srecord3c,
        }
    
    def get_preview(
        self,
        filepath: Union[str, List[str]],
        format: Optional[str] = None,
        n_samples: int = 1000
    ) -> PreviewData:
        """
        Get preview data for a file or file set.
        
        Args:
            filepath: Path to file, or list of paths for multi-file formats
            format: Format name (auto-detected if None)
            n_samples: Number of samples to include in preview
            
        Returns:
            PreviewData with channel information and waveform samples
        """
        # Handle file list
        if isinstance(filepath, list):
            if len(filepath) == 0:
                return PreviewData(format='unknown', error="No files provided")
            primary_file = filepath[0]
        else:
            primary_file = filepath
            filepath = [filepath]
        
        # Auto-detect format if not provided
        if format is None:
            format = self._detect_format(primary_file)
        
        format_lower = format.lower()
        
        # Get appropriate handler
        handler = self._format_handlers.get(format_lower)
        if handler is None:
            return PreviewData(
                format=format,
                error=f"Unsupported format for preview: {format}"
            )
        
        try:
            return handler(filepath, n_samples)
        except Exception as e:
            logger.error(f"Preview extraction failed: {e}")
            return PreviewData(
                format=format,
                error=str(e)
            )
    
    def _detect_format(self, filepath: str) -> str:
        """Auto-detect file format from extension and content."""
        path = Path(filepath)
        ext = path.suffix.lower()
        
        format_map = {
            '.saf': 'saf',
            '.sac': 'sac',
            '.gcf': 'gcf',
            '.vt2': 'peer',
            '.at2': 'peer',
            '.dt2': 'peer',
            '.mseed': 'miniseed',
            '.miniseed': 'miniseed',
            '.txt': 'txt',
            '.csv': 'txt',
            '.dat': 'txt',
        }
        
        return format_map.get(ext, 'unknown')
    
    def _preview_saf(self, filepaths: List[str], n_samples: int) -> PreviewData:
        """Extract preview from SAF file."""
        from hvsr_pro.loaders.patterns import (
            SAF_VERSION, SAF_NPTS, SAF_FS, SAF_V_CH, SAF_N_CH, SAF_E_CH,
            SAF_NORTH_ROT, SAF_DATA_ROW
        )
        
        filepath = filepaths[0]
        
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Check SAF format
        if not SAF_VERSION.search(text):
            return PreviewData(format='saf', error="Not a valid SAF file")
        
        # Extract metadata
        metadata = {}
        
        npts_match = SAF_NPTS.search(text)
        fs_match = SAF_FS.search(text)
        
        if npts_match:
            metadata['npts'] = int(npts_match.group(1))
        if fs_match:
            metadata['sampling_rate'] = float(fs_match.group(1))
        
        # Get channel assignments
        v_ch = 0
        n_ch = 1  
        e_ch = 2
        
        v_match = SAF_V_CH.search(text)
        n_match = SAF_N_CH.search(text)
        e_match = SAF_E_CH.search(text)
        
        if v_match:
            v_ch = int(v_match.group(1))
        if n_match:
            n_ch = int(n_match.group(1))
        if e_match:
            e_ch = int(e_match.group(1))
        
        # Get rotation
        north_rot_match = SAF_NORTH_ROT.search(text)
        if north_rot_match:
            metadata['degrees_from_north'] = float(north_rot_match.group(1))
        
        # Parse some data for preview
        data_samples = []
        for i, match in enumerate(SAF_DATA_ROW.finditer(text)):
            if i >= n_samples:
                break
            channels = match.groups()
            data_samples.append([float(c) for c in channels])
        
        if not data_samples:
            return PreviewData(format='saf', error="No data found in SAF file")
        
        data_array = np.array(data_samples)
        full_length = metadata.get('npts', len(data_samples))
        sampling_rate = metadata.get('sampling_rate', 100.0)
        
        # Create channel previews
        channels = []
        component_map = {v_ch: 'Z', n_ch: 'N', e_ch: 'E'}
        
        for col_idx in range(data_array.shape[1]):
            col_data = data_array[:, col_idx]
            detected = component_map.get(col_idx)
            
            channel = ChannelPreview(
                name=f"Channel {col_idx}",
                detected_component=detected,
                data=col_data,
                full_length=full_length,
                sampling_rate=sampling_rate,
                min_val=float(np.min(col_data)),
                max_val=float(np.max(col_data)),
                mean_val=float(np.mean(col_data)),
                std_val=float(np.std(col_data)),
                source_file=filepath
            )
            channels.append(channel)
        
        # Create detected mapping
        detected_mapping = {}
        for idx, comp in component_map.items():
            if idx < len(channels):
                detected_mapping[comp] = idx
        
        return PreviewData(
            format='SAF',
            channels=channels,
            metadata=metadata,
            detected_mapping=detected_mapping,
            duration_seconds=full_length / sampling_rate if sampling_rate > 0 else 0
        )
    
    def _preview_sac(self, filepaths: List[str], n_samples: int) -> PreviewData:
        """Extract preview from SAC file(s)."""
        try:
            from obspy import read
        except ImportError:
            return PreviewData(format='sac', error="ObsPy required for SAC files")
        
        channels = []
        detected_mapping = {}
        total_duration = 0.0
        
        for filepath in filepaths:
            try:
                st = read(filepath, format='SAC')
                
                for tr in st:
                    data = tr.data[:n_samples]
                    full_data = tr.data
                    
                    # Detect component from channel code
                    detected = None
                    channel_code = tr.stats.channel if hasattr(tr.stats, 'channel') else ''
                    if channel_code:
                        last_char = channel_code[-1].upper()
                        if last_char in ('E', 'N', 'Z', '1', '2'):
                            if last_char == '1':
                                detected = 'N'
                            elif last_char == '2':
                                detected = 'E'
                            else:
                                detected = last_char
                    
                    channel = ChannelPreview(
                        name=channel_code or f"Channel {len(channels)}",
                        detected_component=detected,
                        data=data,
                        full_length=len(full_data),
                        sampling_rate=tr.stats.sampling_rate,
                        min_val=float(np.min(data)),
                        max_val=float(np.max(data)),
                        mean_val=float(np.mean(data)),
                        std_val=float(np.std(data)),
                        source_file=filepath
                    )
                    channels.append(channel)
                    
                    if detected and detected not in detected_mapping:
                        detected_mapping[detected] = len(channels) - 1
                    
                    duration = len(full_data) / tr.stats.sampling_rate
                    total_duration = max(total_duration, duration)
                    
            except Exception as e:
                logger.warning(f"Error reading SAC file {filepath}: {e}")
        
        if not channels:
            return PreviewData(format='SAC', error="No valid SAC data found")
        
        return PreviewData(
            format='SAC',
            channels=channels,
            detected_mapping=detected_mapping,
            duration_seconds=total_duration
        )
    
    def _preview_gcf(self, filepaths: List[str], n_samples: int) -> PreviewData:
        """Extract preview from GCF file."""
        try:
            from obspy import read
        except ImportError:
            return PreviewData(format='gcf', error="ObsPy required for GCF files")
        
        filepath = filepaths[0]
        
        try:
            st = read(filepath, format='GCF')
        except Exception as e:
            return PreviewData(format='GCF', error=f"Error reading GCF: {e}")
        
        if len(st) != 3:
            return PreviewData(
                format='GCF',
                error=f"Expected 3 traces, found {len(st)}"
            )
        
        channels = []
        detected_mapping = {}
        total_duration = 0.0
        
        for i, tr in enumerate(st):
            data = tr.data[:n_samples]
            full_data = tr.data
            
            # Detect component
            detected = None
            channel_code = tr.stats.channel if hasattr(tr.stats, 'channel') else ''
            if channel_code:
                last_char = channel_code[-1].upper()
                if last_char in ('E', 'N', 'Z'):
                    detected = last_char
            
            channel = ChannelPreview(
                name=channel_code or f"Channel {i}",
                detected_component=detected,
                data=data,
                full_length=len(full_data),
                sampling_rate=tr.stats.sampling_rate,
                min_val=float(np.min(data)),
                max_val=float(np.max(data)),
                mean_val=float(np.mean(data)),
                std_val=float(np.std(data)),
                source_file=filepath
            )
            channels.append(channel)
            
            if detected and detected not in detected_mapping:
                detected_mapping[detected] = i
            
            duration = len(full_data) / tr.stats.sampling_rate
            total_duration = max(total_duration, duration)
        
        return PreviewData(
            format='GCF',
            channels=channels,
            detected_mapping=detected_mapping,
            duration_seconds=total_duration
        )
    
    def _preview_peer(self, filepaths: List[str], n_samples: int) -> PreviewData:
        """Extract preview from PEER file(s)."""
        from hvsr_pro.loaders.patterns import (
            PEER_DIRECTION, PEER_NPTS, PEER_DT, PEER_SAMPLE
        )
        
        channels = []
        detected_mapping = {}
        total_duration = 0.0
        
        for filepath in filepaths:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    text = f.read()
                
                # Extract metadata
                direction_match = PEER_DIRECTION.search(text)
                npts_match = PEER_NPTS.search(text)
                dt_match = PEER_DT.search(text)
                
                direction = direction_match.group(1) if direction_match else 'Unknown'
                npts = int(npts_match.group(1)) if npts_match else 0
                dt = float(dt_match.group(1)) if dt_match else 0.02
                sampling_rate = 1.0 / dt if dt > 0 else 50.0
                
                # Parse samples
                samples = []
                for match in PEER_SAMPLE.finditer(text):
                    if len(samples) >= n_samples:
                        break
                    samples.append(float(match.group(1)))
                
                if not samples:
                    continue
                
                data = np.array(samples)
                
                # Detect component from direction
                detected = None
                direction_upper = direction.upper()
                if direction_upper in ('UP', 'VER'):
                    detected = 'Z'
                elif direction_upper.endswith('N'):
                    detected = 'N'
                elif direction_upper.endswith('E'):
                    detected = 'E'
                else:
                    # Try to parse as azimuth
                    try:
                        azimuth = int(direction)
                        if azimuth % 90 == 0:
                            if azimuth in (0, 360):
                                detected = 'N'
                            elif azimuth == 90:
                                detected = 'E'
                    except ValueError:
                        pass
                
                channel = ChannelPreview(
                    name=f"PEER ({direction})",
                    detected_component=detected,
                    data=data,
                    full_length=npts if npts > 0 else len(samples),
                    sampling_rate=sampling_rate,
                    min_val=float(np.min(data)),
                    max_val=float(np.max(data)),
                    mean_val=float(np.mean(data)),
                    std_val=float(np.std(data)),
                    source_file=filepath
                )
                channels.append(channel)
                
                if detected and detected not in detected_mapping:
                    detected_mapping[detected] = len(channels) - 1
                
                duration = npts * dt if npts > 0 else len(samples) * dt
                total_duration = max(total_duration, duration)
                
            except Exception as e:
                logger.warning(f"Error reading PEER file {filepath}: {e}")
        
        if not channels:
            return PreviewData(format='PEER', error="No valid PEER data found")
        
        return PreviewData(
            format='PEER',
            channels=channels,
            detected_mapping=detected_mapping,
            duration_seconds=total_duration
        )
    
    def _preview_miniseed(self, filepaths: List[str], n_samples: int) -> PreviewData:
        """Extract preview from MiniSEED file(s)."""
        try:
            from obspy import read
        except ImportError:
            return PreviewData(format='miniseed', error="ObsPy required for MiniSEED files")
        
        channels = []
        detected_mapping = {}
        total_duration = 0.0
        
        for filepath in filepaths:
            try:
                st = read(filepath)
                
                for tr in st:
                    data = tr.data[:n_samples]
                    full_data = tr.data
                    
                    # Detect component from channel code
                    detected = None
                    channel_code = tr.stats.channel if hasattr(tr.stats, 'channel') else ''
                    if channel_code:
                        last_char = channel_code[-1].upper()
                        if last_char in ('E', 'N', 'Z', '1', '2'):
                            if last_char == '1':
                                detected = 'N'
                            elif last_char == '2':
                                detected = 'E'
                            else:
                                detected = last_char
                    
                    channel = ChannelPreview(
                        name=f"{tr.stats.station}.{channel_code}",
                        detected_component=detected,
                        data=data,
                        full_length=len(full_data),
                        sampling_rate=tr.stats.sampling_rate,
                        min_val=float(np.min(data)),
                        max_val=float(np.max(data)),
                        mean_val=float(np.mean(data)),
                        std_val=float(np.std(data)),
                        source_file=filepath
                    )
                    channels.append(channel)
                    
                    if detected and detected not in detected_mapping:
                        detected_mapping[detected] = len(channels) - 1
                    
                    duration = len(full_data) / tr.stats.sampling_rate
                    total_duration = max(total_duration, duration)
                    
            except Exception as e:
                logger.warning(f"Error reading MiniSEED file {filepath}: {e}")
        
        if not channels:
            return PreviewData(format='MiniSEED', error="No valid MiniSEED data found")
        
        return PreviewData(
            format='MiniSEED',
            channels=channels,
            detected_mapping=detected_mapping,
            duration_seconds=total_duration
        )
    
    def _preview_txt(self, filepaths: List[str], n_samples: int) -> PreviewData:
        """Extract preview from TXT/CSV file."""
        filepath = filepaths[0]
        
        try:
            # Try to read with numpy
            data = np.loadtxt(filepath, max_rows=n_samples)
            
            # Get full row count
            with open(filepath, 'r') as f:
                full_length = sum(1 for line in f if line.strip() and not line.startswith('#'))
            
            if data.ndim == 1:
                data = data.reshape(-1, 1)
            
            channels = []
            detected_mapping = {}
            
            # Simple heuristic: first 3 numeric columns are E, N, Z
            for i in range(min(data.shape[1], 3)):
                col_data = data[:, i]
                
                # Detect component by column position
                component_map = {0: 'E', 1: 'N', 2: 'Z'}
                detected = component_map.get(i)
                
                channel = ChannelPreview(
                    name=f"Column {i + 1}",
                    detected_component=detected,
                    data=col_data,
                    full_length=full_length,
                    sampling_rate=100.0,  # Default, needs mapping
                    min_val=float(np.min(col_data)),
                    max_val=float(np.max(col_data)),
                    mean_val=float(np.mean(col_data)),
                    std_val=float(np.std(col_data)),
                    source_file=filepath
                )
                channels.append(channel)
                
                if detected:
                    detected_mapping[detected] = i
            
            return PreviewData(
                format='TXT',
                channels=channels,
                detected_mapping=detected_mapping,
                duration_seconds=full_length / 100.0  # Default
            )
            
        except Exception as e:
            return PreviewData(format='TXT', error=f"Error reading TXT: {e}")
    
    def _preview_minishark(self, filepaths: List[str], n_samples: int) -> PreviewData:
        """Extract preview from MiniShark file."""
        from hvsr_pro.loaders.patterns import (
            MSHARK_NPTS, MSHARK_FS, MSHARK_GAIN, MSHARK_CONVERSION, MSHARK_DATA_ROW
        )
        
        filepath = filepaths[0]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
            
            # Extract header
            npts_match = MSHARK_NPTS.search(text)
            fs_match = MSHARK_FS.search(text)
            gain_match = MSHARK_GAIN.search(text)
            conversion_match = MSHARK_CONVERSION.search(text)
            
            if not npts_match or not fs_match:
                return PreviewData(format='MiniShark', error="Invalid MiniShark file: missing required headers")
            
            npts_header = int(npts_match.group(1))
            sampling_rate = float(fs_match.group(1))
            gain = int(gain_match.group(1)) if gain_match else 1
            conversion = int(conversion_match.group(1)) if conversion_match else 1
            
            # Parse first n_samples data rows
            data_array = []
            for match in MSHARK_DATA_ROW.finditer(text):
                if len(data_array) >= n_samples:
                    break
                vt, ns, ew = match.groups()
                data_array.append([float(vt), float(ns), float(ew)])
            
            if not data_array:
                return PreviewData(format='MiniShark', error="No data rows found")
            
            data_array = np.array(data_array, dtype=np.float32)
            data_array = data_array / gain / conversion
            
            duration = npts_header / sampling_rate
            
            channels = []
            detected_mapping = {}
            
            # Columns are: VT (Z), NS (N), EW (E)
            component_map = [(0, 'Z', 'Vertical'), (1, 'N', 'North-South'), (2, 'E', 'East-West')]
            
            for idx, (col_idx, comp, name) in enumerate(component_map):
                col_data = data_array[:, col_idx]
                
                channel = ChannelPreview(
                    name=name,
                    detected_component=comp,
                    data=col_data,
                    full_length=npts_header,
                    sampling_rate=sampling_rate,
                    min_val=float(np.min(col_data)),
                    max_val=float(np.max(col_data)),
                    mean_val=float(np.mean(col_data)),
                    std_val=float(np.std(col_data)),
                    source_file=filepath
                )
                channels.append(channel)
                detected_mapping[comp] = idx
            
            return PreviewData(
                format='MiniShark',
                channels=channels,
                detected_mapping=detected_mapping,
                duration_seconds=duration,
                metadata={
                    'npts': npts_header,
                    'sampling_rate': sampling_rate,
                    'gain': gain,
                    'conversion': conversion
                }
            )
            
        except Exception as e:
            return PreviewData(format='MiniShark', error=f"Error reading MiniShark: {e}")
    
    def _preview_srecord3c(self, filepaths: List[str], n_samples: int) -> PreviewData:
        """Extract preview from SeismicRecording3C JSON file."""
        import json
        
        filepath = filepaths[0]
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Validate structure
            required_keys = ['dt_in_seconds', 'ns_amplitude', 'ew_amplitude', 'vt_amplitude']
            missing = [k for k in required_keys if k not in json_data]
            if missing:
                return PreviewData(format='SeismicRecording3C', error=f"Missing keys: {missing}")
            
            dt = json_data['dt_in_seconds']
            sampling_rate = 1.0 / dt
            
            # Get data
            ns_data = np.array(json_data['ns_amplitude'])
            ew_data = np.array(json_data['ew_amplitude'])
            vt_data = np.array(json_data['vt_amplitude'])
            
            full_length = len(ns_data)
            duration = full_length * dt
            degrees_from_north = json_data.get('degrees_from_north', 0.0)
            meta = json_data.get('meta', {})
            
            # Subsample for preview
            step = max(1, full_length // n_samples)
            ns_preview = ns_data[::step][:n_samples]
            ew_preview = ew_data[::step][:n_samples]
            vt_preview = vt_data[::step][:n_samples]
            
            channels = []
            detected_mapping = {}
            
            # Create channel previews: NS -> N, EW -> E, VT -> Z
            for idx, (data, preview_data, comp, name) in enumerate([
                (ns_data, ns_preview, 'N', 'North-South'),
                (ew_data, ew_preview, 'E', 'East-West'),
                (vt_data, vt_preview, 'Z', 'Vertical')
            ]):
                channel = ChannelPreview(
                    name=name,
                    detected_component=comp,
                    data=preview_data,
                    full_length=full_length,
                    sampling_rate=sampling_rate,
                    min_val=float(np.min(data)),
                    max_val=float(np.max(data)),
                    mean_val=float(np.mean(data)),
                    std_val=float(np.std(data)),
                    source_file=filepath
                )
                channels.append(channel)
                detected_mapping[comp] = idx
            
            return PreviewData(
                format='SeismicRecording3C',
                channels=channels,
                detected_mapping=detected_mapping,
                duration_seconds=duration,
                metadata={
                    'npts': full_length,
                    'sampling_rate': sampling_rate,
                    'degrees_from_north': degrees_from_north,
                    'original_meta': meta
                }
            )
            
        except json.JSONDecodeError as e:
            return PreviewData(format='SeismicRecording3C', error=f"Invalid JSON: {e}")
        except Exception as e:
            return PreviewData(format='SeismicRecording3C', error=f"Error reading JSON: {e}")


# Convenience function
def get_preview(filepath: Union[str, List[str]], format: Optional[str] = None, n_samples: int = 1000) -> PreviewData:
    """
    Get preview data for a file or file set.
    
    Args:
        filepath: Path to file, or list of paths for multi-file formats
        format: Format name (auto-detected if None)
        n_samples: Number of samples to include in preview
        
    Returns:
        PreviewData with channel information and waveform samples
    """
    extractor = PreviewExtractor()
    return extractor.get_preview(filepath, format, n_samples)
