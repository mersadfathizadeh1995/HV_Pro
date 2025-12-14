import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Sequence

import numpy as np

try:
    from obspy import read  # type: ignore
    from obspy.core.stream import Stream
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "ObsPy is required for rdmseed_py to function. Install with 'pip install obspy'."
    ) from e

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
except ImportError:  # pragma: no cover
    plt = None  # plotting optional
    mdates = None

# -----------------------------------------------------------------------------
# Data-classes that replicate the MATLAB structure arrays
# -----------------------------------------------------------------------------


@dataclass
class Blockettes:
    """Placeholder for possible blockette meta-data.

    ObsPy already parses most of the fixed header information but does not expose
    blockettes in the public API.  If you absolutely need them you will need to
    dig into `Trace.stats.mseed` which contains the raw bytes.  For the majority
    of HVSR and surface-wave processing these details are not necessary, so we
    keep a minimal stub here so that attribute access does not fail when
    porting old MATLAB code.
    """

    # We purposely leave this empty – you can extend it later if needed.


@dataclass
class MiniSeedBlock:
    """Container corresponding to one *data record* in MATLABʼs rdmseed."""

    ChannelFullName: str
    StationIdentifierCode: str
    LocationIdentifier: str
    ChannelIdentifier: str
    NetworkCode: str

    # Timing and sampling information
    RecordStartTimeISO: str
    RecordStartTimeMATLAB: float  # MATLAB datenumber equivalent
    SampleRate: float
    NumberSamples: int

    # Actual data and time vector
    d: np.ndarray
    t: np.ndarray

    # Additional metadata – optional, retained for compatibility
    DataRecordSize: Optional[int] = None
    EncodingFormatName: Optional[str] = None
    BLOCKETTES: Blockettes = field(default_factory=Blockettes)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChannelInfo:
    """Information collected over all blocks that belong to the same channel."""

    ChannelFullName: str
    XBlockIndex: Sequence[int]
    ClockDrift: np.ndarray
    OverlapBlockIndex: Sequence[int]
    OverlapTime: np.ndarray
    GapBlockIndex: Sequence[int]
    GapTime: np.ndarray

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# -----------------------------------------------------------------------------
# Convenience helpers
# -----------------------------------------------------------------------------

def _datetime_to_matlabdn(dt: datetime) -> float:
    """Convert Python datetime to MATLABʼs datenum (days since 0000-01-00)."""

    # MATLAB datenum epoch offset from the Python/UTC ordinal is 366 days
    mdn = dt.toordinal() + 366 + (dt - datetime(dt.year, dt.month, dt.day)).total_seconds() / 86400.0
    return mdn


def _matlabdn_array(start: datetime, npts: int, fs: float) -> np.ndarray:
    """Generate MATLAB date-numbers for an equally spaced time vector."""

    start_dn = _datetime_to_matlabdn(start)
    dt = 1.0 / fs / 86400.0
    return start_dn + np.arange(npts) * dt


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def rdmseed(
    file_path: str,
    *,
    plot: bool = False,
    verbose: bool = False,
) -> (List[MiniSeedBlock], List[ChannelInfo]):
    """Read a miniSEED file and return pythonic equivalents to MATLABʼs rdmseed.

    Parameters
    ----------
    file_path
        Path to the miniSEED file on disk.
    plot
        If *True*, reproduce MATLABʼs built-in visualisation. Requires matplotlib.
    verbose
        If *True*, print extra diagnostic information.

    Notes
    -----
    This implementation relies on *ObsPy* for all low-level decoding so it
    automatically supports Steim-1/2, INT16/32, FLOAT32/64 and many other
    formats – far more than manually feasible in pure Python.
    """

    # ------------------------------------------------------------------
    # Stage 1 – Read with ObsPy
    # ------------------------------------------------------------------
    try:
        st: Stream = read(file_path, format="MSEED")
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(f"Failed to read {file_path} as MiniSEED: {exc}")

    if not st:
        raise ValueError(f"File {file_path} contained no trace data")

    # ------------------------------------------------------------------
    # Stage 2 – Build list of MiniSeedBlock objects (XX in MATLAB)
    # ------------------------------------------------------------------
    XX: List[MiniSeedBlock] = []

    for tr in st:
        stats = tr.stats
        start: datetime = stats.starttime.datetime.replace(tzinfo=None)
        sample_rate = float(stats.sampling_rate)
        npts = int(stats.npts)

        XX.append(
            MiniSeedBlock(
                ChannelFullName=f"{stats.network}:{stats.station}:{stats.location}:{stats.channel}",
                StationIdentifierCode=stats.station,
                LocationIdentifier=stats.location or "--",
                ChannelIdentifier=stats.channel,
                NetworkCode=stats.network,
                RecordStartTimeISO=start.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                RecordStartTimeMATLAB=_datetime_to_matlabdn(start),
                SampleRate=sample_rate,
                NumberSamples=npts,
                d=tr.data.astype(np.float64, copy=False),
                t=_matlabdn_array(start, npts, sample_rate),
                DataRecordSize=stats.mseed.record_length if hasattr(stats, "mseed") else None,
                EncodingFormatName=str(stats.mseed.encoding) if hasattr(stats, "mseed") else None,
            )
        )

    # ------------------------------------------------------------------
    # Stage 3 – Build channel-level info (I in MATLAB)
    # ------------------------------------------------------------------
    channel_names = {blk.ChannelFullName for blk in XX}
    I: List[ChannelInfo] = []

    for ch in sorted(channel_names):
        indices = [idx for idx, blk in enumerate(XX) if blk.ChannelFullName == ch]
        sample_rates = {XX[idx].SampleRate for idx in indices}
        if len(sample_rates) > 1:
            warnings.warn(
                f"Channel {ch} has multiple sample rates {sample_rates}; clock drift analysis may be invalid.",
                RuntimeWarning,
            )
        # Compute ideal delta in seconds
        fs = sample_rates.pop()  # pick one arbitrarily
        ideal_delta = 1.0 / fs

        # Concatenate time vectors and check drift
        diffs = []
        gaps, overlaps = [], []
        gap_times, overlap_times = [], []

        for a, b in zip(indices[:-1], indices[1:]):
            prev_end = XX[a].t[-1]
            this_start = XX[b].t[0]
            drift = (this_start - prev_end) * 86400.0 - ideal_delta  # seconds
            diffs.append(drift)
            if drift > 0.5 * ideal_delta:
                gaps.append(b)
                gap_times.append(XX[b].t[0])
            elif drift < -0.5 * ideal_delta:
                overlaps.append(b)
                overlap_times.append(XX[b].t[0])
            else:
                # within tolerance – fine
                pass

        # Pad with NaN so length matches MATLABʼs behaviour
        clock_drift_vec = np.append(diffs, np.nan)
        I.append(
            ChannelInfo(
                ChannelFullName=ch,
                XBlockIndex=indices,
                ClockDrift=clock_drift_vec,
                OverlapBlockIndex=overlaps,
                OverlapTime=np.array(overlap_times),
                GapBlockIndex=gaps,
                GapTime=np.array(gap_times),
            )
        )

    # ------------------------------------------------------------------
    # Stage 4 – Plotting (optional)
    # ------------------------------------------------------------------
    if plot:
        if plt is None or mdates is None:
            raise RuntimeError("Plotting requested but matplotlib is not available.")

        n_channels = len(channel_names)
        fig, axes = plt.subplots(n_channels, 1, sharex=True, figsize=(12, 2 * n_channels))
        if n_channels == 1:
            axes = [axes]

        for ax, ch in zip(axes, sorted(channel_names)):
            ch_blocks = [blk for blk in XX if blk.ChannelFullName == ch]
            for blk in ch_blocks:
                ax.plot_date(mdates.num2date(blk.t), blk.d, "-", linewidth=0.5)
            ax.set_ylabel(ch, rotation=0, ha="right", va="center")
            ax.grid(True)

        axes[-1].set_xlabel("Time")
        fig.autofmt_xdate()
        plt.tight_layout()
        plt.show()

    if verbose:
        print(f"Loaded {len(XX)} data blocks from {file_path}")
        for ch in I:
            print(ch.ChannelFullName)

    return XX, I


__all__ = ["rdmseed", "MiniSeedBlock", "ChannelInfo"] 