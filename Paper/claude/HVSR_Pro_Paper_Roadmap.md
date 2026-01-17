# HVSR Pro Journal Paper: Comprehensive Roadmap

## Executive Summary

This document provides a detailed roadmap for writing the journal paper for **HVSR Pro**, an open-source graphical environment for HVSR analysis. The paper targets **Seismological Research Letters (SRL)**, specifically the *Electronic Seismologist* column.

---

## Part 1: Target Journal and Core Narrative

### Target: Seismological Research Letters (SRL) - Electronic Seismologist

**Why this journal:**
- Industry standard for seismic software papers (ObsPy, Geopsy, hvsrpy)
- Values "utility" and "usability" over novel mathematical theory
- Open to software-focused papers with practical impact
- Audience: seismic engineers, researchers, practitioners

**Alternative:** Computers & Geosciences (if focusing on Python/PyQt5 architecture)

### Core Narrative ("The Story")

> *"While the science of HVSR is mature, the tools available to practitioners are polarized: either expensive black-box commercial software or complex command-line open-source libraries. **HVSR Pro** bridges this gap by providing a transparent, open-source graphical environment that makes advanced processing (like the Cox et al. 2020 algorithm) accessible to non-coders, while ensuring reproducibility and scientific rigor."*

### Key Selling Points
1. **Bridges the GUI gap**: First open-source GUI with modern UX for HVSR
2. **Implements Cox FDWRA**: Industry-standard algorithm now accessible to all
3. **Interactive QC**: Click-to-toggle window management (unique innovation)
4. **Azimuthal analysis**: Beyond basic HVSR to directional site characterization
5. **SESAME compliant**: Follows international guidelines
6. **Reproducible**: All parameters exposed and exportable

---

## Part 2: Complete Paper Outline

### Working Title
*HVSR Pro: An Open-Source Graphical Environment for Robust Horizontal-to-Vertical Spectral Ratio Analysis*

---

### Abstract (200-250 words)

**Structure:**
1. **Context** (1-2 sentences): Define HVSR as standard non-invasive site characterization method
2. **Problem** (2-3 sentences): Current tools are bifurcated—opaque commercial vs. code-heavy libraries
3. **Solution** (2-3 sentences): Introduce HVSR Pro as Python/PyQt5 GUI application
4. **Key Features** (3-4 sentences): 
   - Interactive window management ("click-to-reject")
   - Cox et al. (2020) FDWRA implementation
   - Azimuthal analysis capabilities
   - Multi-format data support (MiniSEED, CSV, ASCII)
5. **Impact** (1-2 sentences): Enables reproducible, publication-quality analysis

**Content to include:**
- Target audience (researchers AND practitioners)
- Cross-platform availability
- Open-source nature
- SESAME compliance

---

### 1. Introduction

**Paragraph 1: The HVSR Method** (~100 words)
- Define HVSR: compares horizontal and vertical components of ambient seismic noise
- Purpose: identifies fundamental resonance frequency (f₀) of near-surface layers
- Applications: seismic microzonation, site characterization, foundation design
- Cite: SESAME (2004), Nakamura (1989)

**Paragraph 2: The Software Landscape** (~150 words)
- **Commercial tools**: Robust GUIs but expensive ($1,000-10,000+), closed-source, "black box"
- **Open-source libraries**: 
  - Geopsy: gold standard but aging interface
  - hvsrpy (Vantassel, 2021): excellent algorithms but command-line only
- Table reference: Feature comparison (see Figure 7/Table 1)

**Paragraph 3: The Gap** (~100 words)
- Need for modern, open-source GUI
- Must integrate recent algorithmic advances (Cox FDWRA)
- Must be accessible to non-programmers
- Transparency for reproducibility

**Paragraph 4: Our Contribution** (~100 words)
- Introduce HVSR Pro
- Python/PyQt5, cross-platform
- Key innovations: interactive window management, Cox FDWRA, azimuthal analysis
- Available on GitHub, free license

---

### 2. Software Architecture

**2.1 Technology Stack** (~100 words)
- Python 3.8+
- PyQt5 (GUI framework)
- ObsPy (seismic data I/O)
- NumPy/SciPy (signal processing)
- Matplotlib (visualization)

**2.2 Design Pattern** (~100 words)
- Model-View-Controller (MVC) approach
- Separation of processing logic (API) from interface (GUI)
- Modular package structure:
  - `api/`: High-level analysis interface
  - `processing/`: Signal processing algorithms
  - `gui/`: User interface components
  - `loaders/`: Multi-format data import

**2.3 Data Handling** (~150 words)
- Multi-format support: MiniSEED, CSV, ASCII
- Three import modes:
  1. Single file (with column mapping for text files)
  2. Multi-file Type 1 (multiple MiniSEED, auto-channel detection)
  3. Multi-file Type 2 (component-separated files)
- Channel mapping dialog with validation
- Time-range selection with window preview
- Reference: Figure 5 (Data Import Dialog)

---

### 3. Methodology and Algorithms

**3.1 HVSR Computation** (~150 words)
- Follow SESAME (2004) guidelines
- **Equation 1**: HVSR ratio formula
  ```
  HVSR(f) = √[S_E(f)·S_N(f)] / S_Z(f)
  ```
  where S_E, S_N, S_Z are smoothed Fourier amplitude spectra

- **Equation 2**: Konno-Ohmachi smoothing function
  ```
  W(f, fc) = [sin(b·log₁₀(f/fc)) / (b·log₁₀(f/fc))]⁴
  ```
  with bandwidth parameter b (default: 40)

- Processing parameters:
  - Window length: configurable (default 30s)
  - Overlap: configurable (default 50%)
  - Frequency range: 0.2-20 Hz (adjustable)

**3.2 Quality Control System** (~200 words)
- Two-tier approach:
  
  **Tier 1: Time-domain (Pre-HVSR)**
  - Amplitude rejection (clipping, saturation)
  - STA/LTA transient detection
  - Quality threshold (SNR)
  
  **Tier 2: Frequency-domain (Post-HVSR)**
  - Spectral spike detection
  - Statistical outlier removal
  - HVSR peak amplitude check (A₀ < 1)
  - Flat/wide peak detection

- **Five QC Presets**:
  | Preset | Description |
  |--------|-------------|
  | Conservative | Only obvious problems (lenient) |
  | Balanced | Amplitude check only (recommended) |
  | Aggressive | STA/LTA + frequency + statistical |
  | SESAME | SESAME-compliant + Cox FDWRA |
  | Publication | 4-condition rejection workflow |

- Reference: Figure 2 (QC Panel)

**3.3 Cox FDWRA Algorithm** (~250 words)
- Full name: Frequency-Domain Window Rejection Algorithm
- Reference: Cox et al. (2020), GJI 221(3), 2170-2183

- **Purpose**: Remove windows with inconsistent peak frequencies

- **Equation 3**: Rejection criterion
  ```
  μ - n·σ ≤ f_peak ≤ μ + n·σ
  ```
  where:
  - μ = mean peak frequency across windows
  - σ = standard deviation of peak frequencies
  - n = user-defined multiplier (default: 2.0)

- **Algorithm Steps**:
  1. Compute peak frequency (f_n) for each window's HVSR curve
  2. Calculate mean (μ) and standard deviation (σ) of peak frequencies
  3. Remove windows with f_peak outside μ ± n·σ
  4. Recalculate statistics using remaining windows
  5. Repeat until convergence or maximum iterations

- **Parameters exposed in GUI**:
  - n-value (0.5-10.0, default 2.0)
  - Max iterations (1-50, default 20)
  - Min iterations (1-20, default 1)
  - Distribution assumption (lognormal/normal)

- Reference: Figure 6 (Cox FDWRA Convergence)

---

### 4. Key Features and Workflow

**4.1 Interactive Window Management** (~200 words)
- **The Innovation**: Real-time click-to-toggle window rejection
- Three-panel Interactive Canvas:
  1. **Timeline** (top): Windows as colored bars (green=active, gray=rejected)
  2. **HVSR Curve** (middle): Mean curve with 16-84% uncertainty band
  3. **Quality Statistics** (bottom): Scatter plot of window quality scores

- **Interactivity**:
  - Click any window to toggle acceptance state
  - Curve recalculates instantly
  - Hover for window info (quality score, state)
  - Real-time statistics update

- **Benefits**:
  - Human-in-the-loop quality control
  - Visual inspection of problematic windows
  - Immediate feedback on QC decisions

- Reference: Figure 1 (Interactive Canvas) - THE HERO SHOT

**4.2 Azimuthal Analysis** (~150 words)
- Rotates horizontal components from 0-180° (configurable step)
- Computes HVSR at each azimuth angle
- Detects directional resonance patterns
- Use cases:
  - Valley-aligned site effects
  - Topographic effects
  - Subsurface anisotropy

- **Visualization options**:
  1. 3D surface plot
  2. 2D contour plot
  3. Polar plot
  4. Individual curves overlay

- **Export capabilities**:
  - Data: CSV, JSON
  - Figures: PNG, PDF, SVG (adjustable DPI)

- Reference: Figure 4 (Azimuthal Analysis)

**4.3 Result Export and Reproducibility** (~100 words)
- Export formats: JSON, CSV, MATLAB (.mat)
- All processing parameters saved with results
- Publication-quality plots (configurable DPI)
- Session save/load for workflow preservation

---

### 5. Application Example (Validation)

**5.1 Dataset Description** (~100 words)
- Source: [Standard open dataset - SESAME project or similar]
- Site characteristics: Soft soil over bedrock
- Recording duration: 30-60 minutes
- Expected f₀: ~1-2 Hz

**5.2 Processing Workflow** (~150 words)
1. Import data (MiniSEED format)
2. Configure: 30s windows, 50% overlap
3. Apply "Balanced" QC preset
4. Run Cox FDWRA (n=2.0)
5. Interactive refinement of window selection

**5.3 Results** (~100 words)
- f₀ = X.XX ± 0.XX Hz
- A₀ = X.XX
- Windows retained: XX/XX (XX%)
- Peak frequency matches known site value

**5.4 Before/After Cox FDWRA Comparison**
- Show improvement in peak frequency consistency
- Reference: Figure 6 (Cox FDWRA Convergence)

---

### 6. Discussion

**6.1 Strengths** (~150 words)
- Modern, intuitive GUI
- Transparent algorithms (open-source)
- Cox FDWRA implementation (industry standard)
- Interactive QC (unique innovation)
- Azimuthal analysis capability
- Multi-format data support
- SESAME compliance

**6.2 Comparison with Existing Software** (~100 words)
- Table: Feature comparison matrix
- Advantages over:
  - Commercial: Cost, transparency
  - Geopsy: Modern interface, Cox FDWRA
  - hvsrpy: GUI accessibility, interactivity

**6.3 Limitations and Future Work** (~100 words)
- Currently single-station analysis (future: array processing)
- Batch processing for large networks
- Database integration for project management
- Machine learning for automated QC
- Web interface for remote analysis

---

### 7. Conclusions

**Summary** (~150 words)
- HVSR Pro fills the gap between commercial and code-only tools
- Combines transparency of open-source with usability of commercial GUI
- Implements industry-standard algorithms (Cox FDWRA)
- Enables reproducible, publication-quality HVSR analysis
- Accessible to practitioners without programming experience

**Availability** (~50 words)
- GitHub: https://github.com/mersadfathizadeh1995/HV_Pro
- License: [Open-source license type]
- Installation: pip install / conda
- Documentation: [Link]

---

### Acknowledgments
[Funding sources, collaborators, etc.]

### References
Key references to include:
1. SESAME (2004) - Guidelines
2. Cox et al. (2020) - FDWRA algorithm
3. Nakamura (1989) - HVSR method
4. Wathelet et al. (2020) - Geopsy
5. Vantassel (2021) - hvsrpy
6. Beyreuther et al. (2010) - ObsPy

---

## Part 3: Figure Specifications

### Figure 1: Interactive HVSR Canvas (THE HERO SHOT)

**Purpose:** Showcase the primary innovation - interactive window management

**Layout:** Composite figure with 3 panels

**Panel A (Top): Window Timeline**
- Horizontal timeline showing all windows as colored bars
- Green bars = Active windows (passing QC)
- Gray bars = Rejected windows (failing QC)
- X-axis: Time (seconds)
- Annotation: "Click windows to toggle"

**Panel B (Middle): HVSR Curve**
- Semilog plot (x-axis log scale)
- Blue line: Mean HVSR curve
- Blue shaded region: 16-84th percentile uncertainty band
- Red dot: Peak marker with annotation
- Annotation box: "f₀ = X.XX Hz, A₀ = X.XX"
- X-axis: Frequency (Hz), log scale
- Y-axis: H/V Spectral Ratio
- Grid: Both major and minor

**Panel C (Bottom): Quality Statistics**
- Scatter plot
- Green dots: Active windows (quality score vs. index)
- Red X markers: Rejected windows
- X-axis: Window Index
- Y-axis: Quality Score (0-1)
- Legend: "Active (N)", "Rejected (M)"

**Annotations:**
- Arrow pointing to timeline: "Click to toggle window"
- Arrow pointing to peak: "Auto-detected peak"
- Stats box: "Windows: X/Y active (XX%)"

**Size:** Full width, approximately 12 × 10 inches

**Caption:** "The primary interface of HVSR Pro. The **Interactive Canvas** allows users to visually inspect and toggle individual time windows (top panel), with immediate updates to the HVSR curve (middle panel) and statistical quality metrics (bottom panel). Green indicates active windows; gray indicates rejected windows. The peak frequency (f₀) and amplitude (A₀) are automatically detected and annotated."

---

### Figure 2: Quality Control Settings Panel

**Purpose:** Demonstrate the transparency and configurability of QC

**Layout:** Screenshot or annotated diagram

**Components to show:**
1. **Mode selector**: Radio buttons for "Preset" vs "Custom"
2. **Preset dropdown**: Showing 5 options (Conservative, Balanced, Aggressive, SESAME, Publication)
3. **Preset description**: Explanatory text below dropdown
4. **Custom mode checkboxes** (if expanded):
   - Amplitude Rejection ☑
   - Quality Threshold ☐
   - STA/LTA Rejection ☐
   - Frequency Domain ☐
   - Statistical Outliers ☐
   - HVSR Peak Amplitude ☐
   - Flat Peak Detection ☐
   - Cox FDWRA ☐
5. **Cox FDWRA group box**:
   - Enable checkbox
   - n-value spinner (2.0)
   - Max iterations (20)
   - Min iterations (1)
   - Distribution dropdown (lognormal/normal)
6. **Advanced Settings button**

**Annotations:**
- Label sections: "Pre-HVSR (Time Domain)" and "Post-HVSR (Frequency Domain)"
- Highlight Cox FDWRA section

**Size:** Half width, approximately 6 × 8 inches

**Caption:** "Quality Control (QC) settings panel in HVSR Pro. Users can select predefined presets (conservative through publication-quality) or customize individual rejection algorithms. The Cox FDWRA parameters (n-value, iterations, distribution) are configurable through a dedicated interface. All parameters are exposed for transparency and reproducibility."

---

### Figure 3: Software Workflow Diagram

**Purpose:** Show complete data flow from input to output

**Layout:** Flowchart (vertical or horizontal)

**Nodes (boxes):**
```
[Raw Data Input]
    ↓
[Data Validation & Channel Mapping]
    ↓
[Time-Range Selection]
    ↓
[Window Segmentation]
    ↓
[FFT & Spectral Computation]
    ↓
[Konno-Ohmachi Smoothing]
    ↓
[HVSR Ratio Calculation]
    ↓
[QC Rejection Pipeline] ←→ [Interactive Toggle]
    ├─ Amplitude
    ├─ STA/LTA
    ├─ Frequency Spike
    └─ Statistical Outlier
    ↓
[Post-HVSR QC]
    ├─ HVSR Amplitude < 1
    └─ Flat Peak Detection
    ↓
[Cox FDWRA] (dashed box - optional)
    ↓
[Mean/Median/Percentile Curves]
    ↓
[Peak Detection]
    ↓
[Visualization & Export]
```

**Styling:**
- Use color coding:
  - Blue: Data input/output
  - Green: Processing steps
  - Orange: QC steps
  - Yellow: Optional steps (Cox FDWRA)
  - Purple: Interactive components
- Dashed border around Cox FDWRA to show it's optional
- Bidirectional arrow for Interactive Toggle

**Size:** Full width, approximately 8 × 6 inches

**Caption:** "Complete HVSR Pro processing workflow. Data flows from input through validation, windowing, spectral computation, and quality control. The Cox FDWRA module (dashed box) is optional but recommended for publication-quality results. Interactive window management allows real-time refinement at the QC stage."

---

### Figure 4: Azimuthal Analysis Visualizations

**Purpose:** Showcase azimuthal analysis capabilities

**Layout:** 2×2 grid of subplots OR 4-panel horizontal layout

**Panel A: 3D Surface Plot**
- X-axis: Frequency (Hz), log scale
- Y-axis: Azimuth (degrees, 0-180)
- Z-axis (color): HVSR amplitude
- Colorbar with label
- View angle: ~30° elevation, ~45° azimuth

**Panel B: 2D Contour Plot**
- X-axis: Frequency (Hz)
- Y-axis: Azimuth (degrees)
- Color: HVSR amplitude
- Contour lines with labels
- Colorbar

**Panel C: Polar Plot**
- Radial axis: Frequency (Hz)
- Angular axis: Azimuth (0-180°)
- Color: HVSR amplitude
- Or: Radial = amplitude, show at peak frequency

**Panel D: Individual Curves Overlay**
- X-axis: Frequency (Hz), log scale
- Y-axis: HVSR amplitude
- Multiple colored lines (one per azimuth)
- Color gradient from 0° to 180°
- Optional legend (showing azimuth values)

**Panel Labels:** (a), (b), (c), (d) in top-left corners

**Size:** Full width, approximately 10 × 8 inches

**Caption:** "Azimuthal HVSR analysis results displaying frequency-azimuth dependence. (a) 3D surface showing HVSR amplitude variation with frequency and azimuth. (b) 2D contour plot with color-coded amplitudes. (c) Polar representation of peak frequency and amplitude. (d) Individual HVSR curves for each azimuth angle, color-coded from 0° (blue) to 175° (red). These visualizations enable identification of directional site effects such as valley-aligned resonance or topographic amplification."

---

### Figure 5: Data Import Interface

**Purpose:** Demonstrate multi-format support and ease of use

**Layout:** Composite showing 3 import modes

**Option A: Three-tab screenshot**
- Show tabs: "Single File" | "Multi-File (Type 1)" | "Multi-File (Type 2)"
- Highlight active tab with content visible

**Option B: Three separate panels**
- Panel A: Single File tab with column mapping dialog
- Panel B: Multi-File Type 1 with channel detection table
- Panel C: Multi-File Type 2 with file grouping

**Components to show:**
1. File browser/list
2. Channel mapping table (E, N, Z dropdowns)
3. Time-range selection widgets
4. Preview button
5. Window count preview
6. Color indicators (green=complete, red=incomplete)

**Annotations:**
- "Automatic column detection"
- "Flexible channel mapping"
- "Time-range selection"

**Size:** Full width, approximately 10 × 6 inches

**Caption:** "Data import interface with three specialized modes. (a) Single File tab for loading individual recordings with optional column mapping for CSV/ASCII files. (b) Multi-File Type 1 tab for combining multiple MiniSEED files with automatic channel detection. (c) Multi-File Type 2 tab for grouping component-separated files. Color indicators show mapping completeness, and time-range selection allows extraction of specific segments."

---

### Figure 6: Cox FDWRA Convergence

**Purpose:** Illustrate the FDWRA algorithm's effect

**Layout:** 2-panel or 3-panel figure

**Panel A: Peak Frequency Distribution (Before FDWRA)**
- Histogram of peak frequencies from all windows
- X-axis: Peak frequency (Hz)
- Y-axis: Count
- Show outliers in red
- Vertical lines: μ and μ ± nσ bounds
- Annotation: "N windows, σ = X.XX Hz"

**Panel B: Peak Frequency Distribution (After FDWRA)**
- Same histogram style
- Show tighter distribution
- Fewer/no outliers
- Annotation: "N-M windows remaining, σ = X.XX Hz"

**Panel C (Optional): HVSR Curves Comparison**
- Overlay of HVSR curves
- Gray/faded: Rejected windows
- Black/bold: Accepted windows
- Show how rejected windows have different peaks

**Alternative Layout: Box plots**
- Side-by-side box plots of peak frequencies
- Before vs. After FDWRA
- Show reduction in outliers and variance

**Size:** Full width, approximately 10 × 4 inches

**Caption:** "Cox Frequency-Domain Window Rejection Algorithm (FDWRA) convergence. (a) Peak frequency distribution before rejection showing outliers. (b) After iterative rejection with n=2.0 standard deviations, the distribution is more tightly clustered with reduced variance. Windows with inconsistent peak frequencies (gray, faded in inset) are removed, ensuring robust estimation of the fundamental frequency."

---

### Figure 7: Software Comparison Matrix

**Purpose:** Position HVSR Pro relative to alternatives

**Layout:** Table format (can be included as figure or standalone table)

**Columns:**
- Feature
- HVSR Pro
- hvsrpy
- Geopsy
- Commercial (generic)

**Rows:**
| Feature | HVSR Pro | hvsrpy | Geopsy | Commercial |
|---------|----------|--------|--------|------------|
| GUI | ✓ Full PyQt5 | ✗ CLI | ✓ Limited | ✓ |
| Open Source | ✓ | ✓ | ✓ | ✗ |
| Transparent Parameters | ✓ | ✓ | ~ Partial | ✗ |
| Interactive Window QC | ✓ **Unique** | ✗ | ✗ | ✓ |
| Cox FDWRA | ✓ | ✓ | ✗ | ~ Some |
| Azimuthal Analysis | ✓ | ✗ | ✗ | ~ Some |
| Preset QC Modes | ✓ 5 presets | ✗ | ✗ | ~ Limited |
| Multi-format Import | ✓ | ✓ | ✓ | ✓ |
| Export (JSON/CSV/MAT) | ✓ | ✓ | ✓ | ✓ |
| Cost | Free | Free | Free | $1,000-10,000+ |
| Learning Curve | Low | High | Medium | Medium |

**Legend:**
- ✓ = Fully supported
- ~ = Partially supported
- ✗ = Not supported

**Size:** Full width, approximately 8 × 4 inches

**Caption:** "Feature comparison of HVSR analysis software. HVSR Pro combines the transparency of open-source tools with the usability of commercial GUI software. Key innovations include interactive window management (click-to-toggle QC), built-in Cox FDWRA implementation, and azimuthal analysis capabilities. Unlike commercial alternatives, all processing parameters are exposed and exportable for reproducibility."

---

### Figure 8: Validation Case Study Results

**Purpose:** Demonstrate real-world application

**Layout:** 4-panel composite figure

**Panel A: Input Waveforms**
- 3-component seismogram (E, N, Z)
- X-axis: Time
- Y-axis: Amplitude
- Show ~60 seconds of representative data

**Panel B: Window Spectra**
- All individual window HVSR curves (gray, transparent)
- Mean curve (black, bold)
- X-axis: Frequency (Hz), log scale
- Y-axis: H/V ratio

**Panel C: QC Statistics**
- Before/after bar chart showing:
  - Total windows
  - After time-domain QC
  - After frequency-domain QC
  - After Cox FDWRA

**Panel D: Final HVSR Result**
- Publication-ready plot
- Mean curve with uncertainty band
- Peak marker and annotation
- Statistics box: f₀ = X.XX Hz, A₀ = X.XX

**Size:** Full width, approximately 12 × 10 inches

**Caption:** "Example HVSR analysis of a soft-soil site using HVSR Pro. (a) Input three-component recording showing 30 minutes of ambient noise. (b) Individual window HVSR curves (gray) with mean curve (black), illustrating data variability. (c) Quality control progression showing window counts at each stage. (d) Final publication-ready HVSR curve with 16-84th percentile uncertainty band and detected fundamental frequency (f₀ = X.XX Hz, A₀ = X.XX)."

---

## Part 4: Tables

### Table 1: HVSR Pro Key Features

| Feature | Description |
|---------|-------------|
| **Multi-format input** | MiniSEED, ASCII, CSV with automatic column/channel mapping |
| **Window management** | Configurable length/overlap with interactive timeline |
| **Quality control** | 5 presets + custom mode with 8+ algorithms |
| **Cox FDWRA** | Full implementation with configurable parameters |
| **Azimuthal analysis** | 4 visualization types, data/figure export |
| **Interactive visualization** | Click-to-toggle windows with real-time updates |
| **Result export** | JSON, CSV, MATLAB formats; PNG/PDF/SVG plots |
| **Open source** | Transparent code, reproducible workflows |

### Table 2: QC Preset Descriptions

| Preset | Algorithms | Use Case |
|--------|------------|----------|
| Conservative | Amplitude only | Noisy field data |
| Balanced | Amplitude check | Most datasets (default) |
| Aggressive | +STA/LTA +Frequency +Statistical | Clean data, strict QC |
| SESAME | Pre-HVSR + Cox FDWRA | SESAME-compliant analysis |
| Publication | +HVSR amplitude +Flat peak | Peer-reviewed papers |

---

## Part 5: Equations to Include

### Equation 1: HVSR Ratio
```
HVSR(f) = √[S_E(f) · S_N(f)] / S_Z(f)
```
or equivalently using geometric mean of horizontals.

### Equation 2: Konno-Ohmachi Smoothing
```
W(f, fc) = [sin(b · log₁₀(f/fc)) / (b · log₁₀(f/fc))]⁴
```
where b is the bandwidth parameter (typically 40).

### Equation 3: Cox FDWRA Rejection Criterion
```
μ - n·σ ≤ f_peak ≤ μ + n·σ
```
where μ is mean peak frequency, σ is standard deviation, n is multiplier.

### Equation 4 (Optional): Bedrock Depth Estimation
```
H = Vs,avg / (4 · f₀)
```
where H is depth, Vs,avg is average shear wave velocity, f₀ is fundamental frequency.

---

## Part 6: Figure Creation Guide

### Required Screenshots from HVSR Pro

1. **Interactive Canvas** (Figure 1)
   - Load representative dataset
   - Process with Balanced preset
   - Manually toggle 2-3 windows to show interaction
   - Capture full canvas with all 3 panels visible

2. **QC Panel** (Figure 2)
   - Show both Preset and Custom modes
   - Expand Cox FDWRA section
   - Consider side-by-side or overlay

3. **Data Import Dialog** (Figure 5)
   - Capture each tab separately
   - Show column mapping dialog popup
   - Include file list with files loaded

4. **Azimuthal Results** (Figure 4)
   - Generate 3D surface, contour, polar, and curves views
   - Use vibrant colormap (plasma or viridis)
   - Capture from export at high DPI

### Diagrams to Create

1. **Workflow Diagram** (Figure 3)
   - Use: PowerPoint, Draw.io, or Lucidchart
   - Style: Clean boxes with arrows
   - Color code by category

### Data Plots to Generate

1. **Cox FDWRA Convergence** (Figure 6)
   - Run FDWRA on dataset
   - Export histogram data before/after
   - Create using Matplotlib or export from app

2. **Validation Results** (Figure 8)
   - Process complete example dataset
   - Export all component plots
   - Assemble in graphics software

### Recommended Tools for Figure Assembly
- **Adobe Illustrator** or **Inkscape**: Vector assembly
- **PowerPoint**: Quick composite figures
- **Matplotlib**: Publication-quality plots
- **HVSR Pro Export**: Native high-DPI export (300+ DPI)

---

## Part 7: Writing Schedule

### Phase 1: Figure Generation (1-2 weeks)
- [ ] Create all screenshots from HVSR Pro
- [ ] Design workflow diagram
- [ ] Generate Cox FDWRA demonstration plots
- [ ] Process validation dataset
- [ ] Assemble composite figures

### Phase 2: First Draft (2-3 weeks)
- [ ] Write Abstract
- [ ] Write Introduction
- [ ] Write Software Architecture
- [ ] Write Methodology/Algorithms
- [ ] Write Key Features (with figure references)
- [ ] Write Validation Example
- [ ] Write Discussion and Conclusions

### Phase 3: Revision (1-2 weeks)
- [ ] Internal review
- [ ] Revise based on feedback
- [ ] Polish figures
- [ ] Format for journal

### Phase 4: Submission (1 week)
- [ ] Final proofread
- [ ] Check journal requirements
- [ ] Prepare supplementary materials
- [ ] Submit to SRL

---

## Part 8: References to Cite

### Essential References

1. **SESAME (2004)** - HVSR Guidelines
   > SESAME Project (2004). Guidelines for the implementation of the H/V spectral ratio technique on ambient vibrations. SESAME European Research Project, Deliverable D23.12.

2. **Cox et al. (2020)** - FDWRA Algorithm
   > Cox, B.R., Cheng, T., Vantassel, J.P., & Manuel, L. (2020). A statistical representation and frequency-domain window-rejection algorithm for single-station HVSR measurements. Geophysical Journal International, 221(3), 2170-2183.

3. **Nakamura (1989)** - Original HVSR Method
   > Nakamura, Y. (1989). A method for dynamic characteristics estimation of subsurface using microtremor on the ground surface. Quarterly Report of Railway Technical Research Institute, 30(1), 25-33.

4. **Geopsy Reference**
   > Wathelet, M., et al. (2020). Geopsy: A user-friendly open-source tool set for ambient vibration processing. Seismological Research Letters, 91(3), 1878-1889.

5. **hvsrpy Reference**
   > Vantassel, J.P. (2021). hvsrpy: An open-source Python package for microtremor HVSR analysis. https://github.com/jpvantassel/hvsrpy

6. **ObsPy Reference**
   > Beyreuther, M., et al. (2010). ObsPy: A Python toolbox for seismology. Seismological Research Letters, 81(3), 530-533.

---

## Part 9: Supplementary Materials (Optional)

Consider including:
1. **User Manual PDF**: Basic usage guide
2. **Example Dataset**: MiniSEED file used in validation
3. **Configuration Files**: JSON/YAML with processing parameters
4. **Video Tutorial**: Screen recording of typical workflow

---

## Summary Checklist

### Before You Start
- [x] Understand software architecture (from code review)
- [x] Identify target journal (SRL - Electronic Seismologist)
- [x] Define core narrative (bridging the GUI gap)
- [x] Plan all figures (8 figures detailed)

### During Writing
- [ ] Follow outline structure
- [ ] Reference figures appropriately
- [ ] Use consistent terminology
- [ ] Include all equations
- [ ] Cite key references

### Before Submission
- [ ] All figures at 300+ DPI
- [ ] Word count within journal limits
- [ ] Supplementary materials prepared
- [ ] Co-author approvals obtained
- [ ] Journal formatting applied

---

*Document created: December 2024*
*For HVSR Pro Journal Paper - Seismological Research Letters*
