from __future__ import annotations
"""
palette.py
~~~~~~~~~~
Load a MATLAB colour table (Colors.mat / Kcolors) or gracefully fall back
to Matplotlib’s default colour cycle.

Example
-------
>>> from palette import load_palette
>>> palette = load_palette("Colors.mat")
>>> print(palette[0])        # → (R, G, B) floats in 0-1 range
"""

from pathlib import Path
from typing import List, Tuple

import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb
from scipy.io import loadmat


def _fallback_palette() -> List[Tuple[float, float, float]]:
    """Return Matplotlib’s default colour cycle as RGB triples."""
    default_cycle = plt.rcParams["axes.prop_cycle"].by_key()["color"]
    return [to_rgb(c) for c in default_cycle]      # converts hex → floats


def load_palette(mat_file: Path | str) -> List[Tuple[float, float, float]]:
    """
    Parameters
    ----------
    mat_file : str or Path
        .mat file containing an N×3 array named *Colors* or *Kcolors*.

    Returns
    -------
    list[tuple[float, float, float]]
        RGB triples on 0-1 scale.  Falls back to Matplotlib defaults if
        the file/variable is missing or malformed.
    """
    mat_path = Path(mat_file)

    try:
        data = loadmat(mat_path, squeeze_me=True)          # may raise IOError
        rgb = None
        for key in ("Kcolors", "Colors"):
            if key in data and getattr(data[key], "ndim", 0) == 2 and data[key].shape[1] == 3:
                rgb = data[key]
                break
        if rgb is None:
            raise ValueError("RGB array not found or wrong shape")

        return [tuple(map(float, row)) for row in rgb]

    except Exception as exc:
        print(f"[palette] Warning: {exc}.  Using Matplotlib defaults.")
        return _fallback_palette()


# -----------------------------------------------------------------------
# Tiny self-test
# -----------------------------------------------------------------------
if __name__ == "__main__":
    import numpy as np

    palette = load_palette("Colors.mat")       # edit path if needed
    x = np.linspace(0, 10, 200)

    for i, colour in enumerate(palette, start=1):
        plt.plot(x, np.sin(x + i), color=colour, label=f"C{i}")

    plt.legend(ncol=2)
    plt.title("Loaded palette demo")
    plt.show()
