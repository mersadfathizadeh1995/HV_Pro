"""
Curve Outlier Rejection Algorithm
==================================

Post-HVSR rejection that identifies windows whose H/V curves deviate
strongly from the population using iterative median-MAD sigma clipping.

This is the standard approach for robust outlier removal in geophysics
and astronomy: compute median and MAD (Median Absolute Deviation) at
each frequency, then flag windows whose normalised deviation exceeds a
threshold.  The process iterates until convergence so that a cluster of
outliers cannot inflate the dispersion estimate and hide themselves.
"""

import logging
from typing import Optional, Tuple, List, Dict, Any

import numpy as np

from hvsr_pro.processing.rejection.base import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.windows import Window, WindowCollection

logger = logging.getLogger(__name__)

# Factor to make MAD consistent with standard deviation for normal data
_MAD_SCALE = 1.4826


class CurveOutlierRejection(BaseRejectionAlgorithm):
    """
    Reject windows whose H/V curve deviates from the population median.

    At each frequency the median and MAD are computed across active
    windows.  A per-window *deviation score* is obtained by aggregating
    the normalised distance ``|curve(f) - median(f)| / scaled_MAD(f)``
    over frequency (using either the mean or the max).  Windows whose
    score exceeds *threshold* are rejected.

    The procedure iterates (up to *max_iterations*) so that rejected
    outliers no longer influence the median/MAD of subsequent rounds.
    Iteration stops early when no new rejections occur.

    NOTE: Requires ``window.hvsr_curve`` and ``window.hvsr_frequencies``
    to be populated (post-HVSR algorithm).
    """

    def __init__(
        self,
        threshold: float = 3.0,
        max_iterations: int = 5,
        metric: str = "mean",
        freq_range: Optional[Tuple[float, float]] = None,
        name: str = "CurveOutlier",
    ):
        """
        Parameters
        ----------
        threshold : float
            Number of scaled-MAD units above which a window is flagged.
        max_iterations : int
            Safety limit on sigma-clipping iterations.
        metric : str
            How to aggregate per-frequency deviations into a single
            score per window.  ``'mean'`` (default, more tolerant) or
            ``'max'`` (stricter, any single extreme frequency triggers
            rejection).
        freq_range : tuple[float, float] or None
            Restrict the comparison to a sub-band ``(f_min, f_max)`` in
            Hz.  ``None`` uses the full frequency range.
        name : str
            Algorithm display name.
        """
        super().__init__(name, threshold)
        self.max_iterations = max_iterations
        self.metric = metric
        self.freq_range = freq_range
        self._window_scores: Dict[int, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def evaluate_collection(
        self, collection: WindowCollection
    ) -> List[RejectionResult]:
        """Run iterative median-MAD sigma clipping on per-window H/V curves."""

        curves, indices, freq_mask = self._gather_curves(collection)

        if curves is None or len(curves) < 3:
            return [
                RejectionResult(False, "Too few curves for outlier detection", 0.0, {})
                for _ in collection.windows
            ]

        rejected_set: set = set()

        for iteration in range(1, self.max_iterations + 1):
            active_mask = np.array(
                [i not in rejected_set for i in range(len(curves))]
            )

            if active_mask.sum() < 3:
                break

            active_curves = curves[active_mask]
            median_hv = np.median(active_curves, axis=0)
            mad = np.median(np.abs(active_curves - median_hv), axis=0)
            scaled_mad = _MAD_SCALE * mad
            scaled_mad = np.where(scaled_mad < 1e-10, 1e-10, scaled_mad)

            new_rejects = 0
            for i in range(len(curves)):
                if i in rejected_set:
                    continue
                norm_dev = np.abs(curves[i] - median_hv) / scaled_mad
                score = float(
                    np.mean(norm_dev) if self.metric == "mean" else np.max(norm_dev)
                )
                self._window_scores[indices[i]] = score
                if score > self.threshold:
                    rejected_set.add(i)
                    new_rejects += 1

            logger.info(
                "  CurveOutlier iter %d: %d new rejections (%d total)",
                iteration, new_rejects, len(rejected_set),
            )
            if new_rejects == 0:
                break

        return self._build_results(collection, indices, rejected_set)

    def evaluate_window(self, window: Window) -> RejectionResult:
        """Return cached result for a single window (after evaluate_collection)."""
        idx = getattr(window, "index", None)
        if idx is not None and idx in self._window_scores:
            score = self._window_scores[idx]
            reject = score > self.threshold
            reason = (
                f"Curve deviation {score:.2f} > {self.threshold:.1f}"
                if reject
                else f"Curve deviation {score:.2f} OK"
            )
            return RejectionResult(reject, reason, min(score / self.threshold, 1.0), {
                "deviation_score": score,
                "threshold": self.threshold,
                "metric": self.metric,
            })
        return RejectionResult(False, "No HVSR curve data", 0.0, {})

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _gather_curves(self, collection):
        """Collect per-window H/V arrays and determine the frequency mask."""
        curves_list = []
        index_list = []
        frequencies = None

        for window in collection.windows:
            hv = getattr(window, "hvsr_curve", None)
            freqs = getattr(window, "hvsr_frequencies", None)
            if hv is None or freqs is None:
                continue
            if frequencies is None:
                frequencies = freqs
            curves_list.append(hv)
            index_list.append(window.index)

        if not curves_list:
            return None, None, None

        all_curves = np.array(curves_list)
        freq_mask = np.ones(all_curves.shape[1], dtype=bool)

        if self.freq_range is not None and frequencies is not None:
            f_min, f_max = self.freq_range
            freq_mask = (frequencies >= f_min) & (frequencies <= f_max)
            if not np.any(freq_mask):
                freq_mask = np.ones(all_curves.shape[1], dtype=bool)

        return all_curves[:, freq_mask], index_list, freq_mask

    def _build_results(self, collection, indices, rejected_set):
        """Map per-index rejection decisions back to collection order."""
        index_to_pos = {idx: pos for pos, idx in enumerate(indices)}
        results = []
        for window in collection.windows:
            pos = index_to_pos.get(window.index)
            if pos is None:
                results.append(
                    RejectionResult(False, "No HVSR curve available", 0.0, {})
                )
                continue
            score = self._window_scores.get(window.index, 0.0)
            reject = pos in rejected_set
            if reject:
                reason = f"Curve deviation {score:.2f} > {self.threshold:.1f}"
            else:
                reason = f"Curve deviation {score:.2f} OK"
            results.append(
                RejectionResult(
                    reject,
                    reason,
                    min(score / self.threshold, 1.0) if self.threshold > 0 else 0.0,
                    {
                        "deviation_score": score,
                        "threshold": self.threshold,
                        "metric": self.metric,
                    },
                )
            )
        return results
