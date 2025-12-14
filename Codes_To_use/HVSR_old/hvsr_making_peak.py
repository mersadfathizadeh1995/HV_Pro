#!/usr/bin/env python
# coding: utf-8
"""
Parallel + interactive HVSR peak-picking script
(complete replacement for the previous version)
"""
import os
# ─────────────────────────────────────────────────────────────────────────────
# STEP 0 ·  force a GUI backend early so plt.ginput() works
#           we try Qt first because PyQt5 wheels are easy to install; if that
#           fails we fall back to Tk.  Any failure → clear message & exit.
# ─────────────────────────────────────────────────────────────────────────────
import sys, importlib, matplotlib

for backend, mod in (("QtAgg", "PyQt5"), ("TkAgg", "tkinter")):
    if importlib.util.find_spec(mod) is not None:
        try:
            matplotlib.use(backend, force=True)
            break
        except Exception:
            continue
else:
    sys.exit(
        "ERROR: No GUI backend found (PyQt5 or Tk).\n"
        "    Install one of them *inside the environment that runs this script*."
    )

import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# PARALLEL SETTINGS
# ---------------------------------------------------------------------------
MAX_WORKERS   = 24                       # threads for your Core-i9
FORCE_1_BLAS  = True                     # stop BLAS from oversubscribing
if FORCE_1_BLAS:
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(var, "1")

import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import cycle
from typing import Literal, List, Tuple, Optional
import math

import numpy as np
from scipy import signal
from scipy.io import loadmat, savemat
from scipy.stats import lognorm

# ---------------------------------------------------------------------------
# Konno-Ohmachi smoothing
# ---------------------------------------------------------------------------
try:
    from obspy.signal.konnoohmachismoothing import konno_ohmachi_smoothing
except Exception:
    def konno_ohmachi_smoothing(a: np.ndarray, f: np.ndarray, b: int = 40):
        out = np.empty_like(a)
        for i, fc in enumerate(f):
            if fc == 0:
                out[i] = a[i]
                continue
            x = np.log10(f / fc) * b
            w = np.sin(x) / np.where(x == 0, 1.0, x)
            w **= 4
            w /= w.sum()
            out[i] = np.dot(w, a)
        return out

# ---------------------------------------------------------------------------
# ███████████ USER SETTINGS ███████████
# ---------------------------------------------------------------------------
ARRAY_MAT   = Path(r"D:\Research\Softwars\HVSR\Test_station1\array\ArrayData_HV1.mat")
OUTPUT_DIR  = Path(r"D:\Research\Softwars\HVSR\Test_station1\results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
STATION_ID  = 1
TIME_WIN_SEC = 120         # seconds per window
SMRT        = 200.0        # sampling rate [Hz]
KO_BANDWIDTH = 40
FREQ_MIN    = 0.2          # ← ignore everything below this frequency
FREQ_MIN = float(os.getenv("HV_FMIN", FREQ_MIN))
NUM_PEAKS: Optional[int] = None  # number of peaks to click; None → unlimited
AVERAGING: Literal["geo", "quad", "energy", "N", "E"] = "geo"
SAVE_FIG    = True
SAVE_PDF    = False  # new flag to control PDF export
LEGEND_FONT = 8
START_SKIP_MIN = 10
PROCESS_MIN = 20
FIG_LABEL = "HV_1"  # Added for the new save logic
ANNOT_ALPHA = 0.8  # Added for the new annotation transparency
FIG_TITLE = "HV_1"  # Added for the new plot title
ANN_FONT_PT  = 9      # default label font size (points)
DRAG_LABEL   = True   # enable click-drag-release labelling


# --- ENV overrides so GUI can launch with custom settings -------------
def _env_float(var, default):
    try: return float(os.getenv(var, default))
    except ValueError: return default

ARRAY_MAT   = Path(os.getenv("HV_ARRAY", ARRAY_MAT))
OUTPUT_DIR  = Path(os.getenv("HV_OUTDIR", OUTPUT_DIR)); OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
# FIG_LABEL   = os.getenv("HV_LABEL", FIG_LABEL)
FIG_LABEL   = os.getenv("HV_FIG", FIG_LABEL)   # GUI passes HV_FIG
FIG_TITLE   = os.getenv("HV_TITLE", FIG_TITLE)
TIME_WIN_SEC= int(os.getenv("HV_TW", TIME_WIN_SEC))
KO_BANDWIDTH= int(os.getenv("HV_KO", KO_BANDWIDTH))
ANNOT_ALPHA = _env_float("HV_ALPHA", ANNOT_ALPHA)
ANN_FONT_PT = int(os.getenv("HV_PFONT", ANN_FONT_PT))
PROCESS_MIN = int(os.getenv("HV_PROC", PROCESS_MIN))
DRAG_LABEL  = bool(int(os.getenv("HV_DRAG", int(DRAG_LABEL))))
SAVE_PDF   = bool(int(os.getenv("HV_PDF", int(SAVE_PDF))))
SMRT       = float(os.getenv("HV_FS", SMRT))
START_SKIP_MIN = int(os.getenv("HV_SKIP", START_SKIP_MIN))
SAVE_FIG   = bool(int(os.getenv("HV_SAVE", int(SAVE_FIG))))
AVERAGING  = os.getenv("HV_AVG", AVERAGING)
_env_npk = os.getenv("HV_NUMPK", "").strip()
if _env_npk == "":
    NUM_PEAKS = None
else:
    try:
        _npk_val = int(_env_npk)
        NUM_PEAKS = _npk_val if _npk_val > 0 else None
    except Exception:
        NUM_PEAKS = None

# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logging.info("Sampling rate (Fs) in use: %.3f Hz", SMRT)

# helpers ────────────────────────────────────────────────────────────────────
def _fft_mag(arr: np.ndarray, fs: float) -> Tuple[np.ndarray, np.ndarray]:
    n = len(arr)
    freq = np.fft.rfftfreq(n, d=1/fs)
    mag  = (2.0 / n) * np.abs(np.fft.rfft(arr))
    return freq, mag

def _prep(arr: np.ndarray) -> np.ndarray:
    arr = signal.detrend(arr)
    arr *= signal.windows.tukey(len(arr), 0.05)
    return arr.astype(float)

# palette loader (Step 1 helper)
from palette import load_palette

# load input arrays ─────────────────────────────────────────────────────────
mat = loadmat(ARRAY_MAT, squeeze_me=True)
Array1Z = mat["Array1Z"].astype(float)
Array1N = mat["Array1N"].astype(float)
Array1E = mat["Array1E"].astype(float)

# apply start/length trimming ----------------------------------------
start_samp = int(START_SKIP_MIN * 60 * SMRT)

if PROCESS_MIN is None:
    end_samp = None
else:
    end_samp = start_samp + int(PROCESS_MIN * 60 * SMRT)

Array1Z = Array1Z[start_samp:end_samp]
Array1N = Array1N[start_samp:end_samp]
Array1E = Array1E[start_samp:end_samp]

n_per_win = int(TIME_WIN_SEC * SMRT)
n_windows = len(Array1Z) // n_per_win
if n_windows == 0:
    sys.exit("ERROR: Record shorter than one full window.")

logging.info("%d samples / window, %d full windows", n_per_win, n_windows)

# per-window worker ─────────────────────────────────────────────────────────
def _process_window(w: int) -> Tuple[int, np.ndarray, np.ndarray]:
    i0, i1 = w * n_per_win, (w + 1) * n_per_win
    Zwin, Nwin, Ewin = map(_prep, (Array1Z[i0:i1], Array1N[i0:i1], Array1E[i0:i1]))

    freq, Zmag = _fft_mag(Zwin, SMRT)
    _,    Nmag = _fft_mag(Nwin, SMRT)
    _,    Emag = _fft_mag(Ewin, SMRT)

    valid = (freq >= FREQ_MIN) & (freq > 0)
    freq, Zmag, Nmag, Emag = freq[valid], Zmag[valid], Nmag[valid], Emag[valid]

    Zmag = konno_ohmachi_smoothing(Zmag, freq, KO_BANDWIDTH)
    Nmag = konno_ohmachi_smoothing(Nmag, freq, KO_BANDWIDTH)
    Emag = konno_ohmachi_smoothing(Emag, freq, KO_BANDWIDTH)

    if AVERAGING == "geo":
        horiz = np.sqrt(Nmag * Emag)
    elif AVERAGING == "quad":
        horiz = np.sqrt((Nmag**2 + Emag**2) / 2)
    elif AVERAGING == "energy":
        horiz = np.sqrt(Nmag**2 + Emag**2)
    elif AVERAGING == "N":
        horiz = Nmag
    else:
        horiz = Emag

    Zsafe = np.where(Zmag == 0, np.finfo(float).eps, Zmag)
    hv = horiz / Zsafe
    return w, freq, hv

# run in parallel ───────────────────────────────────────────────────────────
Combined: List[Tuple[int, np.ndarray]] = []
freq_ref = None

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
    futs = [ex.submit(_process_window, w) for w in range(n_windows)]
    for fut in as_completed(futs):
        w, freq, hv = fut.result()
        if freq_ref is None:
            freq_ref = freq
        Combined.append((w, hv))

Combined.sort(key=lambda t: t[0])
CombinedHV = np.column_stack([hv for _, hv in Combined])

# statistics ────────────────────────────────────────────────────────────────
HVmean = CombinedHV.mean(axis=1)
HVStd  = CombinedHV.std(axis=1, ddof=1)
HVmeanPlusStd, HVmeanMinusStd = HVmean + HVStd, HVmean - HVStd

zeta   = np.sqrt(np.log1p((HVStd**2)/(HVmean**2)))
lam    = np.log(HVmean) - 0.5*zeta**2
HVMedian = lognorm.median(s=zeta, scale=np.exp(lam))
HV16, HV84 = (lognorm.ppf(p, s=zeta, scale=np.exp(lam)) for p in (0.16, 0.84))

suffix = FIG_LABEL
# build label with minutes window for CSV naming
total_minutes = len(Array1Z)/SMRT/60
end_min_total = end_min_total = START_SKIP_MIN + len(Array1Z) / SMRT / 60

# Save MAT ---------------------------------------------------------
# out_mat = OUTPUT_DIR / f"HVSR_Median_{TIME_WIN_SEC}Sec_Station{STATION_ID}{suffix}.mat"
out_mat = OUTPUT_DIR / f"HVSR_Median_{TIME_WIN_SEC}Sec_{FIG_LABEL}.mat"
savemat(out_mat, {
    "VelFreqHV": CombinedHV, "HVmean": HVmean, "HVStd": HVStd,
    "HVlambda": lam, "HVMedian": HVMedian,
    "HVPer16th": HV16, "HVPer84th": HV84,
    "Frequency": freq_ref, "HVmeanPlusStd": HVmeanPlusStd,
    "HVmeanMinusStd": HVmeanMinusStd,
    "Fs_Hz": float(SMRT),
})
logging.info("Saved statistics MAT file")

# plotting & interactive UI ───────────────────────────────────────────────

# ----------  layout with GridSpec (main plot 4/5, controls 1/5)  ---------
from matplotlib.gridspec import GridSpec
from matplotlib.widgets import CheckButtons, Button

palette = load_palette(ARRAY_MAT.parent / "Colors.mat")

fig = plt.figure(figsize=(8, 6))
gs  = GridSpec(1, 2, width_ratios=[4, 1], wspace=0.04)

ax      = fig.add_subplot(gs[0])                         # main plot
ctrl_gs = gs[1].subgridspec(4, 1, height_ratios=[6, 1, 1, 6], hspace=0.15)

ax_checks   = fig.add_subplot(ctrl_gs[0]); ax_checks.set_xticks([]); ax_checks.set_yticks([])
btn_ax_undo = fig.add_subplot(ctrl_gs[1]); btn_ax_undo.set_xticks([]); btn_ax_undo.set_yticks([])
btn_ax_fin  = fig.add_subplot(ctrl_gs[2]); btn_ax_fin.set_xticks([]);  btn_ax_fin.set_yticks([])
fig.add_subplot(ctrl_gs[3]).set_visible(False)  # spacer

# (ui_axes will be defined below after multi-column axes are created)

# 1. plot each window once and keep handles
window_lines: List[plt.Line2D] = []
window_labels: List[str] = []

for i, curve in enumerate(CombinedHV.T, 1):
    lbl = f"T{i}"
    ln, = ax.plot(freq_ref, curve, color=palette[i % len(palette)], lw=1, label=lbl)
    window_lines.append(ln)
    window_labels.append(lbl)

# 2. mean / std lines
avg_line,  = ax.plot(freq_ref, HVmean,          "k",  lw=2, label="Mean")
std_plus,  = ax.plot(freq_ref, HVmeanPlusStd, "--k", lw=1, label="+Std")
std_minus, = ax.plot(freq_ref, HVmeanMinusStd,"--k", lw=1, label="-Std")

# cosmetics
ax.set_xscale("log"); ax.set_xlabel("Frequency [Hz]"); ax.set_ylabel("HVSR")
# title_txt = FIG_TITLE if FIG_TITLE else f"HVSR – Station {STATION_ID}"
title_txt = FIG_TITLE
ax.set_title(title_txt)
ax.grid(True, which="both", ls=":")

# 3. CheckButtons (2 columns) -----------------------------------------
extra_labels = ["Mean", "+Std", "-Std"]
label_to_artists = {lbl: [ln] for lbl, ln in zip(window_labels, window_lines)}
label_to_artists.update({"Mean": [avg_line], "+Std": [std_plus], "-Std": [std_minus]})

labels_all = window_labels + extra_labels

# -------------------------------------------------------------
# Build a TRUE multi-column CheckButtons layout so long lists
# remain readable and easy to toggle.  We split the labels into
# ≤ max_rows per column and create one CheckButtons widget per
# column inside a sub-gridspec.
# -------------------------------------------------------------

# Callback (kept identical):
def _cb(label):
    artists = label_to_artists[label]
    vis_new = not artists[0].get_visible()
    for art in artists:
        art.set_visible(vis_new)
    if label in window_labels:
        visible_cols = [col for col, ln in zip(CombinedHV.T, window_lines) if ln.get_visible()]
        if visible_cols:
            mat = np.column_stack(visible_cols)
            m = mat.mean(axis=1)
            s = mat.std(axis=1, ddof=1)
            avg_line.set_ydata(m)
            std_plus.set_ydata(m + s)
            std_minus.set_ydata(m - s)

    fig.canvas.draw_idle()

# ---------------- multi-column creation ----------------------
MAX_ROWS = 15  # max rows per column to keep height reasonable
n_cols = int(math.ceil(len(labels_all) / MAX_ROWS))

check_axes = []
check_buttons = []

cols_spec = ctrl_gs[0].subgridspec(1, n_cols, wspace=0.05)

# Hide the original placeholder axis to prevent overlap with new ones
ax_checks.set_visible(False)

for i in range(n_cols):
    axc = fig.add_subplot(cols_spec[0, i])
    axc.set_xticks([]); axc.set_yticks([])
    check_axes.append(axc)

    subset = labels_all[i * MAX_ROWS:(i + 1) * MAX_ROWS]
    if not subset:
        continue

    chk = CheckButtons(axc, subset, [True] * len(subset))
    for txt in chk.labels:
        txt.set_fontsize(7)
    chk.on_clicked(_cb)
    check_buttons.append(chk)

# make list of all UI axes so we can hide them when saving
ui_axes = check_axes + [btn_ax_undo, btn_ax_fin]

# legend inside main axes
leg = ax.legend(fontsize=8, ncol=3, loc="upper right", frameon=True)

# # 4. Buttons -----------------------------------------------------------
# btn_undo   = Button(btn_ax_undo, "Undo",   hovercolor="#ffcccc")
# btn_finish = Button(btn_ax_fin,  "Finish", hovercolor="#ccffcc")
#
# peak_coords: List[Tuple[float, float]] = []
# peak_scatter: List[plt.Line2D] = []
# peak_annots:  List[plt.Annotation] = []
#
# def add_peak(xdata):
#     idx = np.abs(freq_ref - xdata).argmin()
#     fpk, apk = float(freq_ref[idx]), float(avg_line.get_ydata()[idx])
#     peak_coords.append((fpk, apk))
#     scat, = ax.plot(fpk, apk, "or")
#     ann  = ax.annotate(
#         f"{fpk:.2f} Hz", (fpk, apk), textcoords="offset points", xytext=(5, 5),
#         bbox=dict(boxstyle="round,pad=0.3", fc="yellow", alpha=ANNOT_ALPHA, lw=0),
#     )
#     peak_scatter.append(scat); peak_annots.append(ann)
#     fig.canvas.draw_idle()
#
# def undo_peak(event=None):
#     if not peak_coords:
#         return
#     peak_coords.pop(); peak_scatter.pop().remove(); peak_annots.pop().remove()
#     fig.canvas.draw_idle()
#
# btn_undo.on_clicked(undo_peak)
#
# def on_click(event):
#     if event.inaxes != ax:
#         return
#     if event.button == 1:
#         add_peak(event.xdata)
#     elif event.button == 3:
#         undo_peak()
#
# cid = fig.canvas.mpl_connect("button_press_event", on_click)


# 4. Buttons ────────────────────────────────────────────────────────────────
btn_undo   = Button(btn_ax_undo, "Undo",   hovercolor="#ffcccc")
btn_finish = Button(btn_ax_fin,  "Finish", hovercolor="#ccffcc")

# ── data containers
peak_coords, peak_scatter, peak_annots = [], [], []
_drag_start = None           # stores (fpk, apk) while mouse button held

# ── helpers ────────────────────────────────────────────────────────────────
def _nearest_peak(xdata: float) -> tuple[float, float]:
    """Return (freq, amp) of the mean curve at the frequency nearest xdata."""
    idx = np.abs(freq_ref - xdata).argmin()
    return float(freq_ref[idx]), float(avg_line.get_ydata()[idx])

def undo_peak(event=None):
    if peak_coords:
        peak_coords.pop()
        peak_scatter.pop().remove()
        peak_annots.pop().remove()
        fig.canvas.draw_idle()
btn_undo.on_clicked(undo_peak)

# ── mouse callbacks ────────────────────────────────────────────────────────
def on_press(event):
    global _drag_start
    if event.inaxes is not ax or event.button != 1:   # left-click only
        return
    # enforce maximum number of peaks
    if NUM_PEAKS is not None and len(peak_coords) >= NUM_PEAKS:
        return
    fpk, apk = _nearest_peak(event.xdata)
    _drag_start = (fpk, apk)
    scat, = ax.plot(fpk, apk, "or")                  # red dot immediately
    peak_scatter.append(scat)
    fig.canvas.draw_idle()

def on_release(event):
    global _drag_start
    if _drag_start is None or event.button != 1:
        return
    fpk, apk = _drag_start
    _drag_start = None
    # label at release location with arrow to the peak
    ann = ax.annotate(f"{fpk:.2f} Hz",
                      xy=(fpk, apk), xycoords="data",
                      xytext=(event.xdata, event.ydata), textcoords="data",
                      fontsize=ANN_FONT_PT,
                      arrowprops=dict(arrowstyle="->"),
                      bbox=dict(boxstyle="round,pad=0.3",
                                fc="yellow", alpha=ANNOT_ALPHA, lw=0))
    ann.set_annotation_clip(False)
    peak_annots.append(ann)
    peak_coords.append((fpk, apk))
    fig.canvas.draw_idle()

def on_key(event):
    if event.key == "backspace":
        undo_peak()

# ── wire up the new handlers ───────────────────────────────────────────────
fig.canvas.mpl_connect("button_press_event",   on_press)
fig.canvas.mpl_connect("button_release_event", on_release)
fig.canvas.mpl_connect("key_press_event",      on_key)



# 4. Finish callback --------------------------------------------------------
def finish(event=None):
    # mask for visible windows
    vis_idx = [i for i, ln in enumerate(window_lines) if ln.get_visible()]
    if not vis_idx:
        print("Nothing visible – aborting save.")
        return

    Combined_vis = CombinedHV[:, vis_idx]
    # recompute stats on visible only (already done live but redo for save)
    mean_vis = Combined_vis.mean(axis=1)
    std_vis  = Combined_vis.std(axis=1, ddof=1)

    zeta_v   = np.sqrt(np.log1p((std_vis**2)/(mean_vis**2)))
    lam_v    = np.log(mean_vis) - 0.5*zeta_v**2
    med_v    = lognorm.median(s=zeta_v, scale=np.exp(lam_v))
    p16, p84 = (lognorm.ppf(p, s=zeta_v, scale=np.exp(lam_v)) for p in (0.16, 0.84))

    # Save MAT ---------------------------------------------------------
    # out_mat = OUTPUT_DIR / f"HVSR_Median_{TIME_WIN_SEC}Sec_Station{STATION_ID}{suffix}.mat"
    out_mat = OUTPUT_DIR / f"HVSR_Median_{TIME_WIN_SEC}Sec_{FIG_LABEL}.mat"
    savemat(out_mat, {
        "VelFreqHV": Combined_vis,
        "HVmean": mean_vis,
        "HVStd": std_vis,
        "HVlambda": lam_v,
        "HVMedian": med_v,
        "HVPer16th": p16,
        "HVPer84th": p84,
        "Frequency": freq_ref,
        "HVmeanPlusStd": mean_vis + std_vis,
        "HVmeanMinusStd": mean_vis - std_vis,
        "Fs_Hz": float(SMRT),
    })
    logging.info("Saved %s", out_mat.name)

    # temporarily hide UI axes before saving figure
    for uiax in ui_axes:
        uiax.set_visible(False)
    leg.set_visible(True)  # ensure legend remains

    # Save PNG ---------------------------------------------------------
    if SAVE_FIG:
        # out_png = OUTPUT_DIR / f"HVSR_Station_{STATION_ID:02d}{suffix}.png"
        out_png = OUTPUT_DIR / f"HVSR_{FIG_LABEL}.png"
        fig.savefig(out_png, dpi=300, bbox_inches="tight")
        logging.info("Saved %s", out_png.name)

    # Save PDF ---------------------------------------------------------
    if SAVE_PDF:
        out_pdf = OUTPUT_DIR / f"HVSR_{FIG_LABEL}.pdf"
        fig.savefig(out_pdf, bbox_inches="tight")  # vector output
        logging.info("Saved %s", out_pdf.name)

    # Save peaks -------------------------------------------------------
    if peak_coords:
        pk_array = np.array(peak_coords).T
        # out_pk = OUTPUT_DIR / f"Peaks&Median_HVSR_{TIME_WIN_SEC}Sec_Station_{STATION_ID}{suffix}.mat"
        out_pk = OUTPUT_DIR / f"Peaks&Median_HVSR_{TIME_WIN_SEC}Sec_{FIG_LABEL}.mat"
        savemat(out_pk, {"HVmean": mean_vis, "Frequency": freq_ref, "HVSRPeaks": pk_array})
        logging.info("Saved %s", out_pk.name)

        # CSV save --------------------------------------------------
        # csv_name = (
        #     f"Peaks&Median_HVSR_{TIME_WIN_SEC}Sec_Station_{STATION_ID}{suffix}_"
        #     f"{int(START_SKIP_MIN)}-{int(end_min_total)}min.csv"
        # )

        csv_name = (
            f"Peaks&Median_HVSR_{TIME_WIN_SEC}Sec_{FIG_LABEL}_{int(START_SKIP_MIN)}-{int(end_min_total)}min.csv"
        )

        csv_path = OUTPUT_DIR / csv_name
        np.savetxt(
            csv_path,
            np.column_stack((pk_array[0], pk_array[1])),
            delimiter=",",
            header="Frequency_Hz,HV_Amplitude",
            comments="",
            fmt="%.5f",
        )
        logging.info("Saved %s", csv_path.name)

    plt.close(fig)

btn_finish.on_clicked(finish)

print("Left-click to add peaks, right-click/Undo to remove, Finish to save/close.")

plt.tight_layout()
plt.show(block=True)



