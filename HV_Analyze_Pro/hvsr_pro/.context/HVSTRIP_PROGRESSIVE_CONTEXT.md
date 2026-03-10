# hvstrip-progressive — Package Context

**Version:** 1.0.0 | **Author:** Mersad Fathizadeh | **Updated:** 2026-03-08  
**Location:** `hvsr_pro/packages/hvstrip-progressive/`  
**Repo:** `https://github.com/mersadfathizadeh1995/hvstrip-progressive`

---

## 1. WHAT IT DOES

**Progressive Layer Stripping** is a technique for interpreting HVSR data by systematically
removing layers from a velocity model (deepest → shallowest) and tracking how the HVSR
resonance frequency changes at each step. This reveals which geologic interfaces control
the site's seismic response.

**Pipeline:** Model → Strip layers → Forward-model HVSR for each → Detect peaks → Analyze shifts → Report

**Scientific basis:** Rahimi et al. (2025) — "Progressive Layer Stripping Analysis for HVSR Interpretation"

---

## 2. PACKAGE STRUCTURE

```
hvstrip-progressive/
├── hvstrip_progressive/              # Main Python package
│   ├── __init__.py                   # v1.0.0, exports core modules
│   ├── core/                         # ★ ALGORITHM ENGINE ★
│   │   ├── stripper.py               # Layer stripping (remove deepest → promote to halfspace)
│   │   ├── hv_forward.py             # Forward modeling facade (pluggable engines)
│   │   ├── hv_postprocess.py         # Peak detection + plot generation per step
│   │   ├── batch_workflow.py         # End-to-end orchestrator (strip→forward→postprocess→report)
│   │   ├── report_generator.py       # ProgressiveStrippingReporter — multi-panel figures
│   │   ├── peak_detection.py         # Flexible peak detection (4 presets, 4 strategies)
│   │   ├── soil_profile.py           # Layer & SoilProfile dataclasses
│   │   ├── velocity_utils.py         # VelocityConverter (Vp↔Vs↔ν↔ρ)
│   │   ├── advanced_analysis.py      # StrippingAnalyzer — controlling interface detection
│   │   ├── dual_resonance.py         # f0/f1 two-resonance extraction
│   │   ├── vs_average.py             # Vs30 calculator (time-averaged shear velocity)
│   │   └── engines/                  # Pluggable forward engines
│   │       ├── base.py               # BaseForwardEngine ABC + EngineResult
│   │       ├── diffuse_field.py      # DiffuseFieldEngine (wraps HVf.exe) — DEFAULT
│   │       ├── sh_wave.py            # SHWaveEngine (Kramer 1996 transfer matrix, pure Python)
│   │       ├── ellipticity.py        # EllipticityEngine (wraps Geopsy gpell.exe)
│   │       ├── sh_transfer_function/ # SH-wave propagator matrix implementation
│   │       ├── ellipticity_engine/   # Rayleigh ellipticity implementation
│   │       └── __init__.py           # EngineRegistry singleton
│   ├── gui/                          # ★ PySide6 + qfluentwidgets GUI ★
│   │   ├── main_window.py            # MainWindow(MSFluentWindow) — 4 tabs
│   │   ├── pages/
│   │   │   ├── home_page.py          # Workflow & batch processing
│   │   │   ├── forward_modeling_page.py  # Direct HVf computation
│   │   │   ├── visualization_page.py    # Figure gallery & export
│   │   │   ├── settings_page.py         # Global configuration
│   │   │   └── multi_profile_tab.py     # Multi-profile batch view
│   │   ├── dialogs/
│   │   │   ├── engine_settings_dialog.py     # Per-engine parameters
│   │   │   ├── batch_settings_dialog.py      # Batch job config
│   │   │   ├── dual_resonance_settings_dialog.py
│   │   │   ├── figure_wizard_dialog.py       # Multi-figure generation
│   │   │   ├── interactive_peak_picker.py    # Manual peak selection
│   │   │   ├── multi_profile_dialog.py
│   │   │   ├── output_viewer_dialog.py
│   │   │   └── figure_settings_panels.py
│   │   └── widgets/
│   │       ├── layer_table_widget.py    # Editable layer table
│   │       ├── plot_widget.py           # Matplotlib canvas
│   │       └── profile_preview_widget.py
│   ├── cli/                          # Click CLI
│   │   └── main.py                   # Commands: workflow, strip, forward, postprocess, report
│   ├── config/
│   │   └── default_config.yaml       # All defaults (engine, peak detection, plotting, output)
│   ├── utils/
│   │   ├── config.py                 # load_config, merge_configs, save_config (YAML/JSON)
│   │   └── validation.py             # validate_model_file, validate_hv_csv
│   ├── visualization/
│   │   ├── plotting.py               # HVSRPlotter — overlay, comparison plots
│   │   └── resonance_plots.py        # Dual-resonance separation, frequency distributions
│   ├── bin/                          # Pre-compiled executables
│   │   ├── exe_Win/HVf.exe           # Windows diffuse-field solver
│   │   └── exe_Linux/HVf             # Linux diffuse-field solver
│   └── Example/                      # Example workflows
├── examples/                         # Example model files
├── tests/                            # pytest suite (6 test files)
├── README.md
├── requirements.txt                  # PySide6, numpy, scipy, pandas, matplotlib, seaborn, PyYAML, click
├── CITATION.cff
└── plan.md
```

---

## 3. KEY DATA STRUCTURES

### 3.1 Layer (dataclass)
```python
@dataclass
class Layer:
    thickness: float          # meters (0 = halfspace)
    vs: float                 # m/s shear wave velocity
    vp: Optional[float]       # m/s (auto-computed from Vs+ν if None)
    nu: Optional[float]       # Poisson's ratio (auto-computed if None)
    density: float            # kg/m³
    is_halfspace: bool
```

### 3.2 SoilProfile (dataclass)
```python
@dataclass
class SoilProfile:
    layers: List[Layer]       # top-to-bottom
    name: str
    description: str
    # Methods: add_layer, get_total_thickness, to_hvf_format, to_csv, validate
```

### 3.3 HVf Model Format (text file)
```
N                          # number of layers
thk1 vp1 vs1 rho1        # layer 1 (topmost)
thk2 vp2 vs2 rho2
...
0    vp_hs vs_hs rho_hs  # halfspace (thickness = 0)
```

### 3.4 EngineResult (dataclass)
```python
@dataclass
class EngineResult:
    frequencies: np.ndarray
    amplitudes: np.ndarray
    metadata: Dict
```

### 3.5 DualResonanceResult
```python
profile_name, n_layers, f0, a0, f1, a1, freq_ratio, max_freq_shift, controlling_step
```

---

## 4. ALGORITHM WORKFLOW

### Step-by-step (batch_workflow.run_complete_workflow):

```
1. LAYER STRIPPING (stripper.py)
   Input: N-layer model → Output: sequence of (N, N-1, N-2, ..., 2)-layer models
   Each step: remove deepest finite layer, promote its properties to halfspace

2. HV FORWARD MODELING (hv_forward.py → engines/)
   For each stripped model: compute theoretical HVSR curve
   Engines: diffuse_field (HVf.exe), sh_wave (pure Python), ellipticity (gpell)
   Adaptive frequency scanning: auto-expand fmax or shrink fmin if peak near boundary

3. POST-PROCESSING (hv_postprocess.py)
   For each step: detect peaks, generate HV curve plot + Vs profile plot
   Peak detection: find_peaks with prominence/distance/frequency filters
   Selection strategies: leftmost, sharpest, leftmost_sharpest, max

4. ADVANCED ANALYSIS (advanced_analysis.py)
   Detect controlling interfaces (which layer removal causes biggest frequency shift)
   Compute layer contributions and impedance contrasts

5. DUAL RESONANCE (dual_resonance.py) — optional
   Extract deep (f0) and shallow (f1) fundamental modes
   Compute separation ratios and statistics

6. REPORT GENERATION (report_generator.py)
   Multi-panel figures: overlay, peak evolution, interface analysis, waterfall
   CSV summaries, text reports, JSON metadata
```

### Output Directory Structure
```
output/
├── strip/
│   ├── Step0_7-layer/
│   │   ├── model_Step0_7-layer.txt
│   │   ├── hv_curve.csv
│   │   ├── hv_curve.png
│   │   ├── vs_profile.png
│   │   └── step_summary.csv
│   ├── Step1_6-layer/
│   └── ...
├── reports/
│   ├── hv_curves_overlay.png
│   ├── peak_evolution_analysis.png
│   ├── interface_analysis.png
│   ├── waterfall_plot.png
│   ├── comprehensive_analysis.png/pdf
│   ├── progressive_stripping_summary.csv
│   ├── analysis_report.txt
│   └── analysis_metadata.json
```

---

## 5. ENGINES (Pluggable Architecture)

| Engine | Class | Executable | Method |
|--------|-------|-----------|--------|
| diffuse_field (DEFAULT) | DiffuseFieldEngine | HVf.exe (subprocess) | Diffuse-field wavefield theory |
| sh_wave | SHWaveEngine | None (pure Python) | SH-wave transfer matrix (Kramer 1996) |
| ellipticity | EllipticityEngine | gpell.exe (via Git Bash) | Rayleigh wave ellipticity |

**Engine Registry (Singleton):**
```python
from hvstrip_progressive.core.engines import registry
engine = registry.get("diffuse_field")
result = engine.compute(model_path, config)  # → EngineResult
```

---

## 6. PEAK DETECTION PRESETS

| Preset | Prominence | Distance | Strategy | Freq Min | Use Case |
|--------|-----------|----------|----------|----------|----------|
| default | 0.2 | 3 | leftmost | 0.5 Hz | General use |
| forward_modeling | 0.1 | 2 | leftmost | 0.3 Hz | Forward model curves |
| conservative | higher | wider | sharpest | 0.5 Hz | Noisy data |
| sensitive | 0.05 | 2 | leftmost | 0.2 Hz | Low-amplitude peaks |

---

## 7. DEFAULT CONFIGURATION

```yaml
engine:
  name: "diffuse_field"
solver:
  exe_path: "HVf.exe"    # auto-detected in bin/
  fmin: 0.2
  fmax: 20.0
  nf: 71
  adaptive:
    enable: true
    max_passes: 2
    edge_margin_frac: 0.05
    fmax_expand_factor: 2.0
    fmin_limit: 0.05
    fmax_limit: 60.0
peak_detection:
  method: "find_peaks"
  select: "leftmost"
  find_peaks_params: {prominence: 0.2, distance: 3}
  freq_min: 0.5
  min_rel_height: 0.25
dual_resonance:
  enable: false
  separation_ratio_threshold: 1.2
plotting:
  hv_curve: {x_axis_scale: "log", y_axis_scale: "log"}
  vs_profile: {show: true, annotate_f0: true}
output:
  formats: ["png", "pdf"]
  dpi: 300
```

---

## 8. GUI ARCHITECTURE

### ⚠️ CRITICAL: FRAMEWORK MISMATCH
- **hvstrip-progressive GUI uses:** PySide6 + qfluentwidgets (MSFluentWindow)
- **HV_Pro main app uses:** PyQt5

These are **incompatible** — PySide6 and PyQt5 cannot coexist in the same Python process.
The core algorithms (everything in `core/`) are **framework-agnostic** (pure Python + numpy/scipy).
Only the `gui/` module depends on PySide6.

### GUI Structure (standalone app, 4 tabs)
```
MainWindow(MSFluentWindow)
├── Home (HomePage)              — Workflow runner, batch processing
├── HV Forward (ForwardModelingPage) — Direct forward modeling
├── Figures (VisualizationPage)  — Figure gallery, export
└── Settings (SettingsPage)      — Engine, peak detection, paths
```

**Workers (QThread-based):**
- `WorkflowWorker` — runs batch_workflow.run_complete_workflow in background
- `BatchWorker` — processes multiple profiles

**Settings persistence:** `~/.hvstrip/settings.yaml`

---

## 9. VELOCITY UTILITIES

**VelocityConverter (static methods):**

| Method | Formula | Purpose |
|--------|---------|---------|
| `vp_from_vs_nu(vs, nu)` | Vp = Vs × √[2(1-ν)/(1-2ν)] | Compute Vp from Vs and Poisson's ratio |
| `nu_from_vp_vs(vp, vs)` | ν = (Vp²/Vs² - 2) / [2(Vp²/Vs² - 1)] | Compute Poisson's ratio |
| `suggest_nu(vs)` | Empirical lookup by Vs range | Auto-assign ν based on soil type |
| `suggest_density(vs)` | Empirical lookup (1700–2500 kg/m³) | Auto-assign density |

**Vs → soil type classification:**
- < 150 m/s: Soft clay (ν=0.48)
- 150–250: Medium clay (ν=0.40)
- 250–400: Stiff clay/sand (ν=0.33)
- 400–600: Dense sand (ν=0.28)
- 600–1000: Weathered rock (ν=0.25)
- > 1000: Intact rock (ν=0.22)

---

## 10. CLI COMMANDS

```bash
hvstrip-progressive workflow model.txt output/ [--exe-path HVf.exe] [--config cfg.yaml]
hvstrip-progressive strip model.txt output/
hvstrip-progressive forward model.txt [--exe-path ...] [--output hv.csv]
hvstrip-progressive postprocess hv.csv model.txt output/
hvstrip-progressive report output/strip/ [--output-dir reports/]
```

---

## 11. INTEGRATION WITH HV_PRO — KEY CONSIDERATIONS

### What works directly (core/ is framework-agnostic):
- `stripper.py` — pure Python file I/O + list manipulation
- `hv_forward.py` + `engines/` — subprocess or pure Python computation
- `hv_postprocess.py` — matplotlib-only visualization
- `batch_workflow.py` — orchestration, no GUI dependency
- `report_generator.py` — matplotlib-only
- `soil_profile.py`, `velocity_utils.py`, `peak_detection.py` — pure data structures
- `advanced_analysis.py`, `dual_resonance.py`, `vs_average.py` — pure computation

### What needs adaptation (gui/ uses PySide6):
- The entire `gui/` module uses PySide6 + qfluentwidgets
- HV_Pro uses PyQt5 — these CANNOT coexist
- To integrate as HV_Pro sub-package: need to either:
  1. **Build a new PyQt5 GUI** that wraps the core algorithms (recommended)
  2. **Launch as separate process** (like the old batch_processing subprocess approach)
  3. **Port gui/ from PySide6 to PyQt5** (significant effort, qfluentwidgets not available for PyQt5)

### Recommended integration pattern:
Follow the same pattern as `batch_processing` and `bedrock_mapping`:
```python
# hvsr_pro/packages/hvstrip-progressive/__init__.py
from .new_pyqt5_window import HVStripWindow  # New PyQt5 wrapper
__all__ = ['HVStripWindow']

# main_window.py:
def open_hvstrip(self):
    from hvsr_pro.packages.hvstrip_progressive import HVStripWindow
    ...
```

---

## 12. DEPENDENCIES

| Category | Packages | Notes |
|----------|----------|-------|
| GUI | PySide6 ≥ 6.5.0, PySide6-Fluent-Widgets ≥ 1.4.0 | ⚠️ Conflicts with PyQt5 |
| Scientific | numpy ≥ 1.24, scipy ≥ 1.10, pandas ≥ 2.0 | Already in HV_Pro |
| Plotting | matplotlib ≥ 3.7, seaborn ≥ 0.12 | matplotlib already in HV_Pro |
| Config | PyYAML ≥ 6.0 | New dependency for HV_Pro |
| CLI | click ≥ 8.1 | Only needed for CLI mode |
| Testing | pytest ≥ 7.0 | Already in HV_Pro |
| External | HVf.exe (bundled in bin/) | Pre-compiled solver |
