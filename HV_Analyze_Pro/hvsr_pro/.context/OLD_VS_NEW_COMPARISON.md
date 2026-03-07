# HVSR_old vs batch_processing — Detailed Comparison & Root Cause Analysis

**Date:** 2026-03-06  
**Old System:** `D:\...\HVSR_old\NewTab0_Automatic.py` + `hvsr_making_peak.py`  
**New System:** `D:\...\hvsr_pro\packages\batch_processing\`  
**Test Data:** `D:\...\Files\XX06\XX06.txt` (OSCAR ASCII, 31.25 Hz, 240 min, simulated)

---

## EXECUTIVE SUMMARY

The user reports two main problems with the new `batch_processing`:
1. **No interactive window** — the old system opens a per-station PyQt5 window with click-to-pick peaks, layers panel, and toggle-able windows; the new system never opens this.
2. **Missing 1 Hz peak** — the old system detects a peak near 1 Hz for XX06.txt; the new system does not.

Root causes identified: **7 critical differences** ranging from architectural (subprocess vs in-process) to numerical (FFT frequency resolution, statistics method, peak detection thresholds, and number of output frequency points).

---

## 1. ARCHITECTURE DIFFERENCES

### 1.1 How HVSR computation runs

| Aspect | HVSR_old | batch_processing |
|--------|----------|-----------------|
| **Execution model** | Launches `hvsr_making_peak.py` as a **subprocess** via `ParallelHVSRManager` | Runs **in-process** via `BatchHVSRWorker` QThread calling `HVSRProcessor` directly |
| **Process isolation** | Each station = separate Python process. Has its own GUI event loop. Can open interactive matplotlib windows. | Single Python process. QThread cannot open independent GUI windows. |
| **Interactive window** | When `AUTO_MODE=False` (default): opens a full PyQt5 QMainWindow with matplotlib canvas, WindowLayersPanel, Auto-Detect/Undo/Set-Primary/Finish buttons. | **Never opens an interactive window.** In non-auto mode it says "pick peaks on the canvas" referring to the Results tab's canvas — NOT a per-station interactive window. |
| **Auto mode** | Optional (`HV_AUTO_MODE=1`): skips interactive window, uses `hvsr_pro.processing.windows.peaks.detect_peaks()` automatically | Always automatic (no per-station interactive option) |

### 1.2 Why the interactive window doesn't open

**Root cause:** The old system runs `hvsr_making_peak.py` as a **subprocess** (`subprocess.Popen`). That script creates its own `QApplication`, builds a `QMainWindow` with matplotlib canvas, and calls `qapp.exec_()` to show the interactive peak-picking window. The window stays open until the user clicks "Finish & Save".

The new system runs everything **in the same process** via a `QThread`. QThreads cannot create their own event loops or show independent top-level windows with blocking `exec_()`. The `BatchHVSRWorker` computes HVSR, saves results, and returns — there is no mechanism to pause and wait for user interaction per-station.

**Fix approach:** Either (A) re-introduce subprocess launching for interactive mode, or (B) build an in-process per-station interactive dialog that pauses the workflow, shows the plot, and waits for the user to pick peaks before continuing to the next station.

---

## 2. SIGNAL PROCESSING DIFFERENCES (Why the 1 Hz peak is missed)

### 2.1 FFT & Frequency Resolution

| Parameter | HVSR_old (`hvsr_making_peak.py`) | batch_processing (`HVSRProcessor`) |
|-----------|----------------------------------|-------------------------------------|
| **FFT function** | `np.fft.rfft` → raw FFT bins | `scipy.fft.rfft` → raw FFT bins |
| **FFT normalization** | `(2.0 / n) * abs(rfft)` | `abs(rfft) * 2.0 / n` |
| **Pre-processing** | `signal.detrend()` + tukey(α=0.05) | mean removal + configurable taper (default **hann**) |
| **Frequency points used** | ALL FFT bins in [f_min, f_max] directly. For 120s window at 31.25Hz: 3750 samples → 1876 FFT bins → ~1870 bins in [0.2, 30] Hz. **FULL resolution.** | **Log-spaced target frequencies** (default 100-200 points). Smoothing function maps raw FFT onto these target points. **MUCH lower resolution.** |
| **Smoothing** | KO smoothing applied to raw FFT bins, then H/V ratio computed on those same bins | KO smoothing maps raw FFT directly onto log-spaced target grid. H/V computed on target grid. |

#### ⚠️ CRITICAL: Number of frequency points

**Old system:** Keeps ALL ~1870 FFT frequency bins. Smoothing at each bin. Statistics on all bins. Peak detection on all bins.

**New system (`HVSRProcessor`):** Uses `n_frequencies=100` (default) or 200 (batch_processing default) log-spaced points. The smoothing function (`konno_ohmachi` in `methods.py`) evaluates the weighted average of the raw spectrum at each target point. But with only 100-200 points, the frequency resolution around 1 Hz is very coarse:
- 200 log-spaced points from 0.2 to 30 Hz: spacing near 1 Hz ≈ 0.02 Hz (OK-ish)
- 100 log-spaced points from 0.2 to 20 Hz: spacing near 1 Hz ≈ 0.04 Hz (still OK)

So the number of output points alone may not be the sole issue, but combined with the smoothing behavior it can affect peak shapes.

### 2.2 Taper Function

| | HVSR_old | batch_processing |
|--|---------|-----------------|
| Default taper | `tukey(α=0.05)` — very narrow (5% cosine taper on edges) | `hann` (full cosine bell window) |
| Effect | Preserves most of the signal energy, minimal spectral leakage | **Significantly suppresses edges**, modifies spectral shape. More leakage suppression but more energy loss. |

**Impact:** The Hann window zeros out signal at window edges, which can reduce the effective signal length and alter the spectral shape, especially for low-frequency content near 1 Hz where window length matters most (1 Hz peak needs ≥1s period to be captured; with 120s window this should be fine, but the windowing shape matters).

### 2.3 Smoothing Implementation

| | HVSR_old | batch_processing |
|--|---------|-----------------|
| KO function | `obspy.signal.konnoohmachismoothing` or inline fallback. Smooths at EACH FFT bin frequency. | `hvsr_pro.processing.smoothing.methods.konno_ohmachi()` — smooths raw FFT and evaluates at **target (log-spaced) frequencies**. |
| Window function | `(sin(b*log10(f/fc)) / (b*log10(f/fc)))^4` (standard) | Same formula but with `upper_limit = 10^(3/b)` and `lower_limit = 10^(-3/b)` bandwidth cutoff. |

The old system applies KO smoothing in-place at every FFT frequency bin, preserving maximum resolution. The new system's KO function (`methods.py` L31-106) smooths the raw spectrum onto the target frequency grid, which is a 2-step operation: it windows the raw spectrum around each target frequency and averages. This is mathematically different from smoothing at full resolution then sub-sampling.

### 2.4 Statistics Computation

| Statistic | HVSR_old | batch_processing |
|-----------|---------|-----------------|
| **Mean** | `np.mean(axis=1)` on accepted windows | `np.mean(axis=0)` on active windows |
| **Std** | `np.std(ddof=1)` (sample std) | `np.std()` (**population std**, ddof=0!) |
| **Median** | **Lognormal median**: `zeta = sqrt(log1p(std²/mean²))`, `lambda = log(mean) - 0.5*zeta²`, `median = lognorm.median(s=zeta, scale=exp(lambda))` | **Direct numpy median**: `np.median(axis=0)` |
| **Percentiles** | **Lognormal percentiles**: `lognorm.ppf(0.16, ...)`, `lognorm.ppf(0.84, ...)` | **Direct numpy percentiles**: `np.percentile(16)`, `np.percentile(84)` |

#### ⚠️ CRITICAL: Lognormal vs Direct Statistics

The old system computes the median and percentiles using a **lognormal distribution assumption**, which is the standard approach in HVSR analysis (SESAME 2004 recommendation). This:
- Gives a slightly different (usually lower) median than the arithmetic median
- Gives narrower confidence bands (16th/84th) 
- Makes peaks sharper/more pronounced in the median curve

The new system uses **direct numpy statistics**, which gives broader percentile bands and can smooth out peaks that are prominent in some windows but not others.

**Peak detection runs on `mean_hvsr` in the new system** (L292 of processor.py), while the old system uses the **lognormal median** by default (`PEAK_BASIS = "median"`). For a 1 Hz peak that's moderate in amplitude, the lognormal median can enhance it compared to the arithmetic mean.

### 2.5 Peak Detection Parameters

| Parameter | HVSR_old (auto mode) | batch_processing |
|-----------|---------------------|-----------------|
| **Basis curve** | Median (lognormal) or Mean (configurable via `PEAK_BASIS`) | **Mean** (hardcoded in `_detect_peaks`) |
| **min_prominence** | 0.5 (configurable) | **1.5** (hardcoded) |
| **min_amplitude** | 2.0 (configurable) | **2.0** (hardcoded) |
| **Freq range** | (f_min, f_max) from settings | (f_min, f_max) from processor |
| **Max peaks** | `AUTO_NPEAKS` (default 3) | Unlimited (all found) |

#### ⚠️ CRITICAL: min_prominence = 1.5 vs 0.5

The old system uses `min_prominence=0.5` by default. The new system hardcodes `min_prominence=1.5` in `HVSRProcessor._detect_peaks()` (L371).

A peak at 1 Hz with moderate prominence (say 0.8-1.4) would be detected by the old system but **completely missed** by the new system because it fails the prominence threshold. This is likely the **primary reason** the 1 Hz peak is not found.

### 2.6 Window Overlap

| | HVSR_old | batch_processing |
|--|---------|-----------------|
| Default overlap | **0%** (no overlap, non-overlapping consecutive windows) | **50%** (0.5) |

The old system uses `n_windows = len(Array1Z) // n_per_win` — integer division with no overlap. The new system uses 50% overlap by default, creating roughly twice as many windows. More windows generally improves statistics but doesn't directly affect peak detection.

### 2.7 Detrend Method

| | HVSR_old | batch_processing |
|--|---------|-----------------|
| Detrend | `scipy.signal.detrend()` — removes linear trend | **mean removal only** (`data - np.mean(data)`) |

`signal.detrend()` removes the best-fit line (removes both offset and slope), while `data - np.mean(data)` only removes the DC offset. For real seismic data with instrument drift, detrending can significantly affect low-frequency content.

---

## 3. QC/REJECTION DIFFERENCES

| QC Aspect | HVSR_old | batch_processing |
|-----------|---------|-----------------|
| STA/LTA | Simple STA/LTA on raw Z component before FFT | Uses `hvsr_pro.processing.rejection.STALTARejection` on all components |
| Amplitude | Clipping check (normalized > 0.999, >1%) | Uses `hvsr_pro.processing.rejection.AmplitudeRejection` |
| Statistical | Post-processing MAD/IQR pass on all H/V curves together | Uses `StatisticalOutlierRejection` per-window |
| HVSR amplitude | Post-FFT, checks min/max amplitude of H/V curve | Not used in new batch |
| Flat peak | Post-FFT, checks peak-to-mean ratio | Not used in new batch |
| **Cox FDWRA** | Not used in old `hvsr_making_peak.py` at all | Used in new `hvsr_worker.py` L264 with `evaluate_fdwra()` |

**Note:** The old system's QC is simpler and inline (in `_process_window()`). The new system uses the full `RejectionEngine` pipeline from hvsr_pro, including FDWRA which can reject additional windows and change the result.

---

## 4. OUTPUT FORMAT DIFFERENCES

| Output | HVSR_old | batch_processing |
|--------|---------|-----------------|
| JSON | Saves per-station JSON with `N_FREQUENCIES=300` log-spaced points | Saves with `n_frequencies=200` log-spaced resampled points (from 300 in `_resample_to_log_grid`) |
| MAT file | Saves raw FFT frequency bins | Saves resampled log-spaced frequencies |
| Figures | Standard figure + hvsr_pro-style figures + statistics figure | Single basic figure |
| CSV | Peaks CSV + median data CSV + metadata CSV | Peaks CSV + stats CSV |

---

## 5. COMPLETE SUMMARY OF DIFFERENCES

### 5.1 Why Interactive Window is Missing
**Root cause:** Architecture change from subprocess to in-process QThread. The old system launches `hvsr_making_peak.py` as a subprocess that can run its own `QApplication.exec_()` and open an interactive window. The new system runs inline in a `QThread` and cannot open blocking interactive dialogs.

### 5.2 Why 1 Hz Peak is Missing (Ranked by Impact)

1. **🔴 `min_prominence=1.5` vs `0.5`** — The new system hardcodes 3x stricter prominence threshold. A moderate 1 Hz peak is filtered out.

2. **🔴 Peak detection on `mean` vs `median` (lognormal)** — The old system detects peaks on the lognormal median, which produces sharper peaks. The new system uses arithmetic mean, which tends to broaden peaks and reduce prominence.

3. **🟡 Taper function: `hann` vs `tukey(0.05)`** — Hann window suppresses more signal at window edges, reducing effective data length. For low-frequency peaks (~1 Hz), this reduces amplitude/prominence.

4. **🟡 Population std (ddof=0) vs sample std (ddof=1)** — Slightly affects the shape of mean±std curves, indirectly affecting peak detection.

5. **🟡 Detrend vs mean-removal** — Linear detrend preserves more of the true low-frequency signal shape. Mean-removal alone may leave a slope that affects FFT behavior at low frequencies.

6. **🟡 `n_frequencies` (100 default) and smoothing resampling** — Lower frequency resolution in the output can reduce apparent peak prominence. Combined with the smoothing-at-target-grid vs smooth-then-subsample approach.

7. **🟢 Cox FDWRA in new system** — Additional window rejection in the new system may remove windows that contribute to the 1 Hz peak.

---

## 6. RECOMMENDED FIXES (Priority Order)

### Fix 1: Peak Detection Parameters (Critical)
In `HVSRProcessor._detect_peaks()` (processor.py L369-374):
- Change `min_prominence=1.5` → make it configurable, default `0.5` to match old behavior
- Add `peak_basis` parameter: detect on median_hvsr instead of mean_hvsr
- Make these parameters passable from batch_processing settings

### Fix 2: Implement Lognormal Statistics (Critical)
In `HVSRProcessor.process()` (processor.py L280-285):
- Replace `np.median()` with lognormal median computation
- Replace `np.percentile()` with lognormal percentile computation
- Use `ddof=1` for sample standard deviation
- This matches SESAME 2004 standard practice

### Fix 3: Default Taper (Important)
Change default taper from `hann` to `tukey` with `alpha=0.05` to match old behavior and preserve more signal energy.

### Fix 4: Add Detrend Option (Important)
Add `scipy.signal.detrend()` as preprocessing step before FFT in `compute_fft()`.

### Fix 5: Interactive Window (Architectural)
Either:
- (A) Re-introduce subprocess-based execution for interactive mode (run hvsr_making_peak.py like the old system)
- (B) Build a per-station interactive dialog that shows the HVSR plot, lets the user pick peaks, and returns results (using QDialog.exec_() in the main thread, not in QThread)
- (C) Make the Results tab's canvas support full per-station interactive peak picking (partially implemented already)

### Fix 6: Increase n_frequencies Default (Minor)
Change `n_frequencies` default from 100 to 300 to match old system's output resolution.

---

## 7. FILE-BY-FILE CORRESPONDENCE

| HVSR_old | batch_processing | Notes |
|----------|-----------------|-------|
| `NewTab0_Automatic.py` | `batch_window.py` | Main UI widget (QWidget vs QMainWindow) |
| `hvsr_making_peak.py` | `workers/hvsr_worker.py` | Core computation (subprocess script vs QThread) |
| `automatic_workflow/workers/hvsr_manager.py` | `workers/hvsr_worker.py` | Parallel management (subprocess pool vs sequential QThread) |
| `automatic_workflow/workers/data_worker.py` | `workers/data_worker.py` | Data loading step |
| `automatic_workflow/station_manager.py` | `station_manager.py` | Station file management |
| `automatic_workflow/dialogs/hvsr_settings.py` | `dialogs/hvsr_settings.py` | Settings dialog |
| `automatic_workflow/dialogs/time_windows.py` | `dialogs/time_windows.py` | Time windows dialog |
| `automatic_workflow/report_export.py` | `report_export.py` | Report generation |
| `automatic_workflow/results_handler.py` | `results_handler.py` | Results loading/analysis |
| `dialogs/qc_settings.py` | `dialogs/qc_settings.py` | QC algorithm defaults |
| `dialogs/figure_export_settings.py` | `dialogs/figure_export_settings.py` | Figure export config |
| `widgets/` | `widgets/` | Results table/canvas/tree/histogram |
| `processing/` | `processing/` | Peak/structure definitions |
| N/A (uses ObsPy fallback KO) | hvsr_pro smoothing registry | Smoothing system |
| N/A (inline QC in _process_window) | hvsr_pro RejectionEngine | QC system |

---

## 8. DEFAULT SETTINGS COMPARISON

| Setting | HVSR_old Default | batch_processing Default |
|---------|-----------------|------------------------|
| `freq_min` | 0.2 Hz | 0.2 Hz |
| `freq_max` | 30.0 Hz | 30.0 Hz |
| `window_length` | 120 s | 120 s |
| `overlap` | 0% (none) | **50%** |
| `smoothing_bw` | 40 | 40 |
| `smoothing_method` | Konno-Ohmachi | Konno-Ohmachi |
| `taper` | tukey(0.05) | **hann** |
| `horizontal_method` | geometric_mean ("geo") | geometric_mean |
| `n_frequencies` | 300 (output resampling) | **200** (HVSRProcessor target grid) |
| `peak_basis` | median | **mean** |
| `min_prominence` | 0.5 | **1.5** |
| `min_amplitude` | 2.0 | 2.0 |
| `max_peaks` | 3 | unlimited |
| `statistics` | lognormal median/percentiles | **numpy direct** |
| `std ddof` | 1 (sample) | **0 (population)** |
| `detrend` | linear detrend | **mean removal** |
| `FDWRA` | off by default | **on by default** |

Items in **bold** differ and contribute to the 1 Hz peak discrepancy.
