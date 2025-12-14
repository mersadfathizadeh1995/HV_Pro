# This file is part of hvsrpy, a Python package for horizontal-to-vertical
# spectral ratio processing.
# Copyright (C) 2025 Joseph P. Vantassel (joseph.p.vantassel@gmail.com)
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <https: //www.gnu.org/licenses/>.

"""Class definition for FrequencyAmplitudeCurve object."""

import logging
from abc import ABC

import numpy as np

logger = logging.getLogger(__name__)

__all__ = ["FrequencyAmplitudeCurve"]


class FrequencyAmplitudeCurve(ABC):
    """Class for creating and manipulating ``FrequencyAmplitudeCurve`` objects.

    Attributes
    ----------
    frequency : ndarray
        Vector of frequencies, must be same length as ``amplitude``.
    amplitude : ndarray
        Vector of PSD amplitude values, one value per ``frequency``.

    """
    @staticmethod
    def _check_input(value, name):
        """Check input values.

        .. warning:: 
            Private methods are subject to change without warning.

        Specifically:
            1. ``value`` must be castable to ``ndarray`` of doubles.
            2. ``value`` must be real; no ``np.nan``.
            3. ``value`` must be >= 0.

        Parameters
        ----------
        value : iterable
            Value to be checked.
        name : str
            Name of ``value`` to be checked, used for meaningful error
            messages.

        Returns
        -------
        ndarray
            ``values`` as ``ndarray`` of doubles.

        Raises
        ------
        TypeError
            If ``value`` is not castable to an ``ndarray`` of doubles.
        ValueError
            If ``value`` contains nan or a value less than or equal to zero.

        """
        try:
            value = np.array(value, dtype=np.double)
        except ValueError as e:
            msg = f"{name} must be castable to array of doubles, "
            msg += f"not {type(value)}."
            raise TypeError(msg) from e

        if np.isnan(value).any():
            raise ValueError(f"{name} may not contain nan.")

        if (value < 0).any():
            raise ValueError(f"{name} must be >= 0.")

        return value

    def __init__(self, frequency, amplitude):
        """Create ``HvsrCurve`` from iterables of frequency and amplitude.

        Parameters
        ----------
        frequency : ndarray
            Vector of frequencies, one per ``amplitude``.
        amplitude : ndarray
            Vector of HVSR amplitudes, one per ``frequency``.

        Returns
        -------
        FrequencyAmplitudeCurve
            Initialized with ``amplitude`` and ``frequency``.

        """
        self.frequency = self._check_input(frequency, "frequency")
        self.amplitude = self._check_input(amplitude, "amplitude")

        if len(self.frequency) != len(self.amplitude):
            msg = f"Length of amplitude {len(self.amplitude)} and length"
            msg += f"of frequency {len(self.amplitude)} must be agree."
            raise ValueError(msg)

    def is_similar(self, other, atol=1E-9, rtol=0.):
        """Check if ``other`` is similar to ``self``."""
        if len(self.frequency) != len(other.frequency):
            return False

        if not np.allclose(self.frequency, other.frequency, atol=atol, rtol=rtol):
            return False

        return True
