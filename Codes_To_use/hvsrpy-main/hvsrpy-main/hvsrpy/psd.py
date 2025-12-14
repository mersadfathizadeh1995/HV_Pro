# This file is part of hvsrpy, a Python package for horizontal-to-vertical
# spectral ratio processing.
# Copyright (C) 2019-2023 Joseph P. Vantassel (joseph.p.vantassel@gmail.com)
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

"""Class definition for Psd object."""

import logging

from .frequency_amplitude_curve import FrequencyAmplitudeCurve

logger = logging.getLogger(__name__)

__all__ = ["Psd"]


class Psd(FrequencyAmplitudeCurve):
    """Class for creating and manipulating ``Psd`` objects.

    Attributes
    ----------
    frequency : ndarray
        Vector of frequencies, must be same length as ``amplitude``.
    amplitude : ndarray
        Vector of PSD amplitude values, one value per ``frequency``.

    """

    def __init__(self, frequency, amplitude, meta=None):
        """Create ``Psd`` from iterables of frequency and amplitude.

        Parameters
        ----------
        frequency : ndarray
            Vector of frequencies, one per ``amplitude``.
        amplitude : ndarray
            Vector of PSD amplitudes, one per ``frequency``.
        meta : dict, optional
            Meta information about the object, default is ``None``.

        Returns
        -------
        Psd
            Initialized with ``amplitude`` and ``frequency``.

        """
        super().__init__(frequency, amplitude)

        self.meta = dict(meta) if isinstance(meta, dict) else {}

    def is_similar(self, other, atol=1E-9, rtol=0.):
        """Check if ``other`` is similar to ``self``."""
        if not isinstance(other, Psd):
            return False
        return super().is_similar(other, atol=atol, rtol=rtol)
