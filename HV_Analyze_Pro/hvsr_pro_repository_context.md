# HVSR Pro Repository Context and Architecture Documentation

## Executive Summary

**HVSR Pro** (Horizontal-to-Vertical Spectral Ratio Processing) is a comprehensive open-source, cross-platform graphical software application designed for horizontal-to-vertical spectral ratio (HVSR) analysis of ambient seismic noise. Built with Python and PyQt5, HVSR Pro bridges the gap between code-only libraries (such as hvsrpy) and expensive commercial black-box software, providing researchers and practitioners with transparent, reproducible, and user-friendly HVSR processing capabilities.

---

## 1. Repository Overview

### 1.1 Project Location and Structure
- **GitHub URL**: https://github.com/mersadfathizadeh1995/HV_Pro
- **Package Directory**: `HV_Analyze_Pro/hvsr_pro/`
- **Main Components**: GUI, processing algorithms, API, data import/export utilities
- **License**: Open-source (transparent, reproducible research)
- **Target Users**: Seismic engineers, researchers, practitioners without programming experience

### 1.2 Core Purpose
HVSR Pro automates and visualizes the complete HVSR workflow:
1. **Data Import**: Supports MiniSEED, ASCII, and CSV formats with flexible column/channel mapping
2. **Data Preprocessing**: Time-range selection, channel validation, waveform preview
3. **Window Segmentation**: Configurable window length and overlap with interactive management
4. **Quality Control (QC)**: Preset and custom QC modes with multiple rejection algorithms
5. **Frequency-Domain Processing**: Cox et al. (2020) Frequency-Domain Window Rejection Algorithm (FDWRA)
6. **HVSR Computation**: Mean, median, and percentile curves with uncertainty quantification
7. **Azimuthal Analysis**: HVSR as a function of horizontal rotation angle
8. **Interactive Visualization**: Real-time curve updates, window toggling, quality metrics
9. **Result Export**: JSON, CSV, MATLAB, and publication-quality plots

---

## 2. Technical Architecture

### 2.1 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Core Language** | Python 3.8+ | Main development language |
| **GUI Framework** | PyQt5 | Cross-platform graphical user interface |
| **Data Processing** | NumPy, SciPy | Numerical computing, signal processing |
| **Visualization** | Matplotlib | Interactive plotting and figure generation |
| **File Formats** | ObsPy (MiniSEED), Pandas | Seismic data and tabular data handling |
| **Data Structures** | Dataclasses | Configuration and result management |

### 2.2 Package Organization

The `hvsr_pro` folder contains several subpackages:

```
hvsr_pro/
├── gui/                          # Graphical User Interface
│   ├── data_input_dialog.py      # Multi-tab data import dialog
│   ├── interactive_canvas.py     # Interactive HVSR visualization
│   ├── main_window.py            # Main application window
│   ├── panels/
│   │   ├── qc_panel.py          # Quality control settings panel
│   │   └── azimuthal_properties_dock.py  # Azimuthal analysis dock
│   └── ...other UI components
│
├── api/                          # Application Programming Interface
│   ├── analysis.py               # HVSRAnalysis class (main processing)
│   ├── processing_config.py      # ProcessingConfig dataclass
│   └── ...other API modules
│
├── processing/                   # Signal Processing Algorithms
│   ├── hvsr/                     # HVSR computation
│   │   ├── hvsr_processor.py     # Core HVSR algorithm
│   │   └── smoothing.py          # Konno-Ohmachi smoothing
│   │
│   ├── window/                   # Window management
│   │   ├── windower.py           # Window segmentation
│   │   └── window_utils.py       # Utility functions
│   │
│   ├── rejection/                # Quality control algorithms
│   │   ├── qc_engine.py          # Main rejection pipeline
│   │   ├── algorithms/
│   │   │   ├── amplitude.py      # Amplitude-based rejection
│   │   │   ├── sta_lta.py        # STA/LTA transient detection
│   │   │   ├── frequency_spike.py # Frequency spike detection
│   │   │   ├── cox_fdwra.py      # Cox FDWRA algorithm
│   │   │   └── ...other rejection methods
│   │   └── presets.py            # QC preset configurations
│   │
│   ├── azimuthal/                # Azimuthal analysis
│   │   └── azimuthal_processor.py # Rotation and analysis
│   │
│   └── spectral/                 # Spectral computation
│       ├── fft.py                # Fast Fourier Transform
│       └── spectrum.py           # Spectral estimation
│
├── io/                           # Input/Output Operations
│   ├── readers/
│   │   ├── miniseed_reader.py    # MiniSEED file handling
│   │   ├── ascii_reader.py       # ASCII file handling
│   │   └── csv_reader.py         # CSV file handling
│   │
│   └── writers/
│       ├── json_writer.py        # JSON export
│       ├── csv_writer.py         # CSV export
│       └── matlab_writer.py      # MATLAB format export
│
├── models/                       # Data Models
│   ├── hvsr_result.py            # HVSR result dataclass
│   ├── window.py                 # Window dataclass
│   └── ...other data models
│
├── utils/                        # Utility Functions
│   ├── validators.py             # Data validation
│   ├── constants.py              # Global constants
│   ├── exceptions.py             # Custom exceptions
│   └── diagnostics.py            # Diagnostic messages
│
└── version.py                    # Version information
```

---

## 3. Key Features and Detailed Descriptions

### 3.1 Data Import and Pre-Processing

#### Multi-Format Support
HVSR Pro accommodates different data acquisition workflows through three specialized import modes:

**Single File Tab**:
- Load a single MiniSEED, ASCII, or CSV file
- For text/CSV files: Enable **column mapping** to assign columns to E (East), N (North), Z (Vertical) components and time
- **Time-range selection** area with start/end time inputs
- Live preview of the number of windows that will be generated from the selected time range
- Automatic detection of numeric columns in CSV/ASCII files

**Multi-File (Type 1) Tab**:
- Import multiple MiniSEED files, each containing all three components (E, N, Z)
- Automatic channel code detection and display in an interactive table
- User can map detected channels to E, N, Z components via dropdown menus
- **Color indicators** (green for complete mappings, yellow/red for incomplete) provide visual feedback
- Validation ensures all three components are present before proceeding

**Multi-File (Type 2) Tab**:
- Import separate files for each component (one file per channel)
- Program automatically groups files and validates complete triplets (E, N, Z)
- Useful for field data stored in component-separated files
- Error messages if triplets are incomplete

#### Waveform Preview
- Optional **Matplotlib-based visualization** showing all three components
- Allows users to verify signal quality, correct channel mapping, and absence of data corruption
- Helpful for detecting clipped signals, excessive noise, or equipment issues

#### Column Mapping Dialog
- Automatic detection of numeric columns in ASCII/CSV files
- Interactive dialog allowing users to select which columns correspond to E, N, Z, and time
- Unit conversion options (if data are in different units)
- Preview of mapped data

### 3.2 Window Segmentation and Interactive Management

#### Window Configuration
- **Configurable window length**: Default 30 seconds, user-adjustable
- **Configurable overlap**: Default 50%, user-adjustable
- **Automatic window generation**: Divides continuous recording into overlapping segments
- Windows are computed and quality-checked before visualization

#### Interactive Canvas (Key Innovation)
The **Interactive HVSR Canvas** is the central visualization and control hub:

**Components**:
1. **Timeline of Windows** (Top Panel):
   - Horizontal timeline showing all windows as colored bars
   - **Green bars**: Active windows (passing QC)
   - **Gray bars**: Rejected windows (failing QC)
   - **Clickable interface**: Users can click any window to toggle acceptance state
   - **Hover tooltips**: Display quality score, acceptance state, and window index

2. **HVSR Curve** (Middle Panel):
   - **Semilog plot**: Frequency on x-axis (log scale), HVSR amplitude on y-axis
   - **Mean HVSR curve**: Computed from active windows
   - **Uncertainty band**: 16th–84th percentile range (confidence interval)
   - **Peak marker**: Indicates primary resonance frequency and amplitude
   - **Real-time updates**: Curve refreshes instantly when windows are toggled

3. **Window Quality Statistics** (Bottom Panel):
   - **Scatter plot**: Quality score vs. window index
   - **Active windows**: Plotted in green
   - **Rejected windows**: Plotted in red
   - **Summary statistics**: Number of active/rejected windows, mean quality score
   - **Interactive legend**: Click to show/hide accepted or rejected windows

#### Real-Time Interactivity
- **Immediate feedback**: Toggling a window instantly recalculates the HVSR curve
- **Diagnostic messages**: If all windows fail QC, the system displays helpful diagnostic messages suggesting possible causes (e.g., excessive clipping, poor sensor coupling, strong transients) and remediation steps
- **State persistence**: Users can save/load their window acceptance decisions

### 3.3 Quality Control (QC) System

#### Two-Mode Architecture

**Preset Mode**:
- Users select from **five predefined QC presets**:
  1. **Conservative**: Strictest criteria; recommended for high-quality publications
  2. **Balanced**: Medium criteria; good for routine analysis
  3. **Aggressive**: Lenient criteria; useful for difficult or noisy data
  4. **SESAME**: Aligned with SESAME guidelines (Nakamura, 1989; SESAME, 2004)
  5. **Publication**: Equivalent to Conservative; optimized for peer-reviewed papers
- Each preset applies a specific combination of time- and frequency-domain checks
- **Description panel**: Explains the preset's behavior and typical use cases

**Custom Mode**:
- Users enable/disable individual rejection algorithms via checkboxes:
  1. **Amplitude rejection**: Rejects windows exceeding a maximum amplitude threshold (detects clipping)
  2. **Quality threshold**: Rejects windows with low signal-to-noise ratio (SNR < threshold)
  3. **STA/LTA transient detection**: Identifies transient events using Short-Term-Average / Long-Term-Average ratio
  4. **Frequency-domain spike rejection**: Detects narrow spectral peaks indicating instrumental or environmental artifacts
  5. **Statistical outlier detection**: Identifies windows with anomalous spectral characteristics
  6. **Post-HVSR peak amplitude check**: Rejects curves where primary peak amplitude < 1
  7. **Flat/wide peak detection**: Identifies broad or ambiguous peaks
  8. **Cox FDWRA**: Optional frequency-domain window rejection (see Section 3.4)

#### Advanced Settings
- **"Advanced Settings..." button**: Provides fine-tuning interface for all thresholds and parameters
- Allows users to customize algorithm-specific parameters (e.g., STA/LTA window lengths, frequency spike height threshold)

#### Cox FDWRA Configuration Panel
- **Dedicated group box** within the QC panel
- **Parameters**:
  - **Standard-deviation multiplier (n)**: Typical values 2–3; controls rejection sensitivity
  - **Maximum iterations**: Convergence limit (default 50)
  - **Minimum iterations**: Ensures at least a few iterations (default 2)
  - **Statistical distribution**: Choice between lognormal or normal distribution
- **Dynamic parameter adjustment**: Users can modify parameters and immediately see effects in the interactive canvas

### 3.4 Cox Frequency-Domain Window Rejection (FDWRA)

#### Algorithm Overview
Implements the algorithm of Cox et al. (2020) as an optional post-QC step to remove outlier windows based on peak frequency consistency.

#### Procedure
1. **Initial peak frequency computation**: For each window, compute HVSR curve and extract peak frequency (fundamental mode)
2. **Statistical calculation**: Compute mean (μ) and standard deviation (σ) of all peak frequencies
3. **Rejection criterion**: Remove windows whose peak frequency lies outside μ ± n·σ (where n is user-defined)
4. **Iteration**: Recalculate μ, σ using remaining windows and repeat steps 2–3
5. **Convergence**: Stop when no additional windows are rejected or maximum iterations reached

#### Parameters
- **n (standard-deviation multiplier)**: Typically 2–3; lower values are more aggressive
- **Distribution assumption**: Lognormal (recommended for geophysical data) or normal
- **Convergence tolerance**: Number of iterations before stopping

#### Use Cases
- **Robust peak frequency estimation**: Removes windows with anomalous peak frequencies
- **Handling multi-modal data**: Useful when multiple resonance modes are present and interfere with consensus peak identification
- **Publication-ready results**: Aligns analysis with recent best-practice recommendations

### 3.5 HVSR Computation and Spectral Analysis

#### Core Processing Class: HVSRAnalysis
The **HVSRAnalysis** class (in `api/analysis.py`) encapsulates the entire HVSR workflow:

**Configuration**:
- Stored in **ProcessingConfig** dataclass with default parameters:
  - Window length: 30 seconds
  - Overlap: 50%
  - Smoothing bandwidth: 40 (Konno–Ohmachi)
  - Frequency range: 0.1–25 Hz (adjustable)

**Workflow**:
1. **Data validation**: Verify 3-component continuous recording
2. **Window generation**: Divide data into overlapping segments
3. **Spectral computation**: Apply FFT to each window; use Konno–Ohmachi smoothing
4. **Horizontal combination**: Compute geometric mean of E and N components
5. **HVSR ratio**: Divide horizontal amplitude by vertical amplitude at each frequency
6. **QC application**: Apply selected rejection pipeline to discard poor windows
7. **Final HVSR**: Compute mean, median, and percentile (16th, 50th, 84th) curves from accepted windows
8. **Peak detection**: Identify fundamental mode frequency and amplitude

#### Output Statistics
- **Mean curve**: Simple arithmetic average of HVSR curves
- **Median curve**: Robust central tendency (recommended for skewed distributions)
- **Percentile curves**: 16th and 84th percentiles (approximate confidence interval for lognormal distribution)
- **Peak frequency**: Fundamental resonance frequency in Hz
- **Peak amplitude**: HVSR amplitude at peak frequency
- **Number of windows**: Original and accepted window counts

#### Spectral Smoothing
- **Konno–Ohmachi smoothing** (default): Bandwidth parameter (typically 40) controls frequency resolution vs. amplitude stability tradeoff
- **Butterworth smoothing** (alternative): Configurable order and cutoff frequency
- **No smoothing option**: Raw FFT output for comparison

### 3.6 Azimuthal Analysis

#### Purpose
Investigates how HVSR parameters vary with horizontal rotation angle, useful for:
- Detecting directional site effects (e.g., valley-aligned resonance)
- Identifying complex subsurface geometries
- Characterizing anisotropic wave propagation

#### Process
1. **Rotate horizontal components**: Systematically rotate E and N components around vertical axis
2. **Recompute HVSR**: For each rotation angle (0°–180°, default 36 angles)
3. **Track peak frequency**: Extract fundamental mode frequency at each angle
4. **Visualization**: Generate frequency–azimuth plots showing resonance variation

#### Visualization Options
Users can select from four visualization types:
1. **3D surface plot**: Peak frequency and amplitude vs. azimuth (3D landscape)
2. **2D contour plot**: Azimuth vs. frequency with amplitude color-coded
3. **Polar plot**: Azimuth as angle, frequency/amplitude as radius
4. **Individual curves**: Stack of HVSR curves (one per azimuth) with color gradient

#### Export Capabilities
- **Data export**: CSV or JSON files containing frequency and amplitude for each azimuth
- **Figure export**: High-resolution (adjustable DPI) PNG/PDF of selected visualization
- **Batch processing**: Generate and export results for multiple sites in workflow

### 3.7 Result Visualization and Export

#### Built-in Plotting Functions
HVSR Pro generates publication-quality figures automatically:

1. **HVSR Curve Plot**:
   - Semilog axes with frequency range and HVSR amplitude
   - Mean, median, and percentile curves in distinct colors/styles
   - Peak frequency marker with annotation
   - Uncertainty band shaded region

2. **Window Spectra Plot**:
   - Individual window HVSR curves with transparency to show overlap
   - Mean curve overlaid in bold
   - Color gradient indicating window acceptance state (green/gray)

3. **Quality Control Summary**:
   - Time series showing window acceptance states (colored bars)
   - Quality score distribution (histogram or scatter plot)
   - Pre- and post-QC window counts

4. **Statistical Summary Dashboard**:
   - Subplots combining HVSR curve, window spectra, and QC metrics
   - Comprehensive figure suitable for reports/publications

#### Export Formats

**Data Formats**:
- **JSON**: Structured output including metadata, configuration, and all computed curves
- **CSV**: Tabular format with frequency and HVSR amplitude columns for import into external tools
- **MATLAB (.mat)**: Compatibility with MATLAB-based workflows

**Figure Formats**:
- **PNG**: Raster format with adjustable DPI (default 300 DPI for publications)
- **PDF**: Vector format for scalable inclusion in LaTeX/Word documents
- **EPS**: PostScript format for publication submissions

**Customization Options**:
- Figure size, font sizes, color schemes
- Include/exclude uncertainty bands, percentile curves
- Frequency range and HVSR amplitude limits
- Title, axis labels, legend position

---

## 4. GUI Components Overview

### 4.1 Main Application Window
- **Multi-tab interface**: Tabs for Data Input, Processing, Results, Azimuthal Analysis
- **Menu bar**: File (Open/Save), Edit, Tools, Help
- **Status bar**: Current operation status, progress indicators, messages
- **Keyboard shortcuts**: Standard shortcuts (Ctrl+O for Open, Ctrl+S for Save, etc.)

### 4.2 Data Input Dialog (`data_input_dialog.py`)
- **Multi-tab design**: Single File, Multi-File Type 1, Multi-File Type 2, Batch Import
- **File browser**: Navigate and select files with filtering by type
- **Channel mapping table**: Display and edit component assignments
- **Time-range slider**: Interactive selection of data interval
- **Preview button**: Generate waveform plot with Matplotlib
- **Column detection**: Automatic identification of numeric columns in ASCII/CSV

### 4.3 QC Settings Panel (`qc_panel.py`)
- **Preset selector**: Dropdown menu with five preset options
- **Algorithm checkboxes**: Enable/disable individual rejection methods
- **Advanced Settings dialog**: Fine-tune algorithm-specific parameters
- **Cox FDWRA controls**: Dedicated group box for FDWRA configuration
- **Live preview toggle**: Enable/disable QC in real time to compare results

### 4.4 Azimuthal Properties Dock (`azimuthal_properties_dock.py`)
- **Azimuth configuration**: Number of angles, angular step size
- **Visualization selector**: Radio buttons for 3D, 2D contour, polar, or individual curves
- **Colormap selector**: Choose from matplotlib colormaps
- **Export buttons**: Save data and figures

### 4.5 Interactive Canvas (`interactive_canvas.py`)
- **Matplotlib figure canvas**: Embedded in PyQt5 application
- **Responsive layout**: Subplots adjust to window resizing
- **Mouse events**: Click handlers for window toggling, hover for tooltips
- **Real-time updates**: Immediate redraw on data changes

---

## 5. Processing Pipeline Architecture

### 5.1 Data Flow

```
Input Data (MiniSEED/ASCII/CSV)
    ↓
Data Validation & Channel Mapping
    ↓
Time-Range Selection & Extraction
    ↓
Window Segmentation (overlap, length)
    ↓
FFT & Spectral Computation (Konno–Ohmachi smoothing)
    ↓
HVSR Ratio Calculation (H/V per window)
    ↓
QC Rejection Pipeline
    ├── Amplitude check
    ├── Quality threshold
    ├── STA/LTA transient detection
    ├── Frequency-domain spike rejection
    ├── Statistical outlier detection
    ├── Peak amplitude check
    └── Optional: Cox FDWRA
    ↓
Accepted Windows → Mean/Median/Percentile HVSR Curves
    ↓
Peak Detection & Frequency Identification
    ↓
Visualization (Interactive Canvas) & Export (JSON/CSV/MAT/PNG/PDF)
```

### 5.2 Rejection Engine
- **Modular design**: Each rejection algorithm is a separate class
- **Preset configurations**: Predefined combinations of algorithms with tuned parameters
- **Custom pipeline**: Users can compose custom rejection sequences
- **Reporting**: Track which windows were rejected and for what reason

### 5.3 Post-Processing
- **Smoothing options**: Konno–Ohmachi, Butterworth, or raw
- **Uncertainty quantification**: Compute percentile curves
- **Peak fitting**: Optional fine-tuning of peak frequency using parabolic interpolation
- **Resonance identification**: Automated detection of fundamental and higher modes

---

## 6. Key Innovations and Strengths

### 6.1 Transparency and Reproducibility
- **Open-source codebase**: Every processing parameter and algorithm is visible and auditable
- **Preset documentation**: Clear explanations of what each preset does
- **Parameter export**: All configuration settings saved with results for future reference
- **Reproducible results**: Same inputs always produce identical outputs

### 6.2 User-Friendly Interface
- **Graphical design**: Eliminates need for command-line knowledge
- **Interactive feedback**: Real-time updates as users modify parameters
- **Preset modes**: Non-experts can run standard analyses without deep parameter knowledge
- **Helpful diagnostics**: Clear error messages and suggestions for troubleshooting

### 6.3 Advanced Features
- **Cox FDWRA implementation**: Incorporates latest best practices (Cox et al., 2020)
- **Azimuthal analysis**: Goes beyond basic HVSR to explore directional effects
- **Multiple visualization types**: Flexibility to present results in various formats
- **Batch processing**: Capability to process multiple stations in one session

### 6.4 Scientific Rigor
- **SESAME compliance**: Aligns with international guidelines for HVSR analysis
- **Quality metrics**: Multiple statistical checks ensure result reliability
- **Uncertainty quantification**: Reports confidence intervals alongside best estimates
- **Extensive testing**: Validated against reference implementations (e.g., hvsrpy)

---

## 7. Comparison with Related Software

| Feature | HVSR Pro | hvsrpy | Commercial Software | Geopsy |
|---------|----------|--------|-------------------|--------|
| **GUI** | ✓ Full PyQt5 | ✗ Command-line only | ✓ Proprietary | ✓ Limited |
| **Open Source** | ✓ | ✓ | ✗ | ✓ |
| **Transparent Parameters** | ✓ | ✓ | ✗ | ~ Partial |
| **Interactive Window QC** | ✓ Unique | ✗ | ✓ Commercial | ✗ |
| **Cox FDWRA** | ✓ | ✓ | ✓ Some | ✗ |
| **Azimuthal Analysis** | ✓ | ✗ | ✓ Some | ✗ |
| **Preset QC Modes** | ✓ | ✗ | ~ Limited | ✗ |
| **Cost** | Free | Free | $1,000–10,000+ | Free |
| **Learning Curve** | Low | High | Medium | Medium |

---

## 8. Use Cases and Applications

### 8.1 Seismic Microzonation
- Identify areas with high resonance amplification
- Map spatial variation in fundamental frequency
- Plan focused earthquake risk assessment

### 8.2 Site Response and Building Damage Assessment
- Correlate building fundamental frequency with site resonance
- Investigate causes of disproportionate earthquake damage in certain neighborhoods
- Support post-earthquake reconnaissance studies

### 8.3 Engineering Seismology
- Characterize soil deposits for foundation design
- Identify soft-sediment basins with high amplification
- Support seismic code compliance studies

### 8.4 Academic Research
- Investigate relationship between HVSR and earthquake response (eHVSR vs. mHVSR)
- Develop improved peak-identification algorithms
- Study 3D subsurface structure using azimuthal HVSR

### 8.5 Consulting and Practice
- Routine HVSR surveys for professional seismic assessments
- Generate publication-quality figures for reports
- Ensure consistent QC across multiple projects

---

## 9. Project Development and Maintenance

### 9.1 Code Organization
- **Modular design**: Separation of concerns (GUI, processing, I/O, utilities)
- **Configuration management**: ProcessingConfig dataclass centralizes parameter storage
- **Version control**: GitHub repository with commit history and branch management
- **Documentation**: Inline code comments and docstrings

### 9.2 Testing and Validation
- **Unit tests**: Individual components tested independently
- **Integration tests**: Full workflows validated end-to-end
- **Reference data**: Test datasets with known results for validation
- **Community feedback**: Open-source model allows users to report issues and suggest improvements

### 9.3 Future Enhancements
- **Batch processing**: Automated processing of large site networks
- **Database integration**: Store results and metadata in structured database
- **Inversion tools**: Couple with site-response inversion for profile estimation
- **Machine learning**: Automated peak identification and mode detection
- **Web interface**: Browser-based version for remote analysis
- **Distributed processing**: Parallel processing of multiple stations

---

## 10. Dependencies and Requirements

### 10.1 Core Dependencies
- **Python**: 3.8 or higher
- **PyQt5**: GUI framework
- **NumPy**: Numerical arrays and operations
- **SciPy**: Scientific computing (FFT, signal processing, statistics)
- **Matplotlib**: Visualization
- **ObsPy** (optional): MiniSEED file support; fallback to manual parsing if unavailable
- **Pandas** (optional): CSV/ASCII reading convenience

### 10.2 Installation Methods
- **pip**: `pip install hvsr-pro` (if published to PyPI)
- **git clone**: Download from GitHub and install in development mode
- **Conda**: Package in conda-forge (if maintained)
- **Executable**: Windows standalone executable (if distributed)

### 10.3 Compatibility
- **Operating Systems**: Windows, macOS, Linux (PyQt5 cross-platform)
- **Python Versions**: 3.8–3.11 (3.12+ requires testing)
- **Architecture**: 64-bit recommended; 32-bit supported (memory constraints)

---

## 11. Expected Journal Paper Structure

### Suggested Sections
1. **Abstract**: Concise summary of the software, its capabilities, and impact
2. **Introduction**: Context of HVSR analysis, existing solutions, motivation for HVSR Pro
3. **Software Architecture**: Technical design, key components, data flow
4. **Features and Workflows**: Detailed description of each major feature (Data Import, QC, Cox FDWRA, Azimuthal Analysis)
5. **Interactive Visualization**: Emphasis on the interactive canvas innovation
6. **Quality Control Philosophy**: Explanation of preset and custom QC modes, Cox FDWRA, SESAME compliance
7. **Case Studies or Validation**: Example analyses demonstrating the software's capabilities
8. **Comparison with Existing Software**: Feature comparison table and discussion
9. **Discussion**: Strengths, limitations, impact on the field
10. **Conclusion**: Summary and future directions
11. **Availability and Installation**: How users can obtain and use the software
12. **Appendix**: Detailed algorithm descriptions, mathematical formulae, QC preset configurations

### Suggested Figures with Detailed Descriptions

**Figure 1: Overall Workflow Diagram**
- Shows the complete data processing pipeline from input to output
- Highlight key decision points (QC, Cox FDWRA, azimuthal choice)
- Include icons or flowchart notation for clarity
- Caption: "Complete HVSR Pro workflow. Data flow from import through QC, computation, visualization, and export. Dashed box indicates optional Cox FDWRA module."

**Figure 2: Quality Control Settings Panel**
- Screenshot or diagram of the QC panel showing preset selector, algorithm checkboxes, and Cox FDWRA configuration
- Annotate each control with brief explanation
- Caption: "Quality Control panel interface showing (a) preset selector dropdown, (b) custom mode algorithm checkboxes, (c) Advanced Settings button, and (d) Cox FDWRA parameter controls. Color-coded sections indicate functionality grouping."

**Figure 3: Azimuthal Analysis Visualizations**
- Show four example outputs (3D surface, 2D contour, polar plot, individual curves) side-by-side
- Use realistic data (synthetic or example site)
- Caption: "Azimuthal HVSR analysis results displayed in four visualization modes: (a) 3D surface showing frequency and amplitude variation with azimuth; (b) 2D contour plot with frequency on x-axis, azimuth on y-axis, amplitude color-coded; (c) polar plot with azimuth as angle, frequency as radius; (d) stacked individual HVSR curves with color gradient by azimuth."

**Figure 4: Interactive HVSR Canvas**
- Composite figure showing three panels: window timeline, HVSR curve, and quality statistics
- Include annotations showing interactive elements (mouse hover, click to toggle)
- Caption: "Interactive HVSR Canvas with three integrated panels: (top) timeline of processing windows color-coded by acceptance state (green = active, gray = rejected); (middle) HVSR curve with uncertainty band and peak marker; (bottom) quality score scatter plot showing accepted (green) and rejected (red) windows. Users click windows in the timeline to toggle acceptance and trigger real-time HVSR curve recalculation."

**Figure 5: Data Import and Channel Mapping**
- Screenshot showing multi-tab data input dialog
- Highlight three import modes (Single File, Multi-File Type 1, Multi-File Type 2)
- Show column mapping interface for CSV files
- Caption: "Data import interface with three specialized tabs: (a) Single File tab for loading individual records with time-range selection; (b) Multi-File Type 1 tab for combining multiple MiniSEED files with automatic channel detection; (c) Multi-File Type 2 tab for grouping component-separated files. Column mapping dialog automatically detects numeric columns and allows users to assign E, N, Z components."

**Figure 6: Cox FDWRA Convergence**
- Example showing peak frequency distribution before and after Cox FDWRA
- Histogram or box plot showing outlier removal
- Caption: "Cox Frequency-Domain Window Rejection Algorithm convergence. (left) Distribution of peak frequencies before FDWRA showing outliers; (right) after iterative rejection with n=2 standard deviations, distribution is more tightly clustered. Inset shows HVSR curves from rejected windows (gray, faded) vs. accepted windows (black, bold)."

**Figure 7: Feature Comparison Matrix**
- Table comparing HVSR Pro with competing software (hvsrpy, Geopsy, commercial tools)
- Include rows for: GUI, open-source, transparent parameters, interactive QC, Cox FDWRA, azimuthal, presets, cost
- Use checkmarks and X's for clarity
- Caption: "Comparison of HVSR analysis software. HVSR Pro combines the transparency of open-source tools with the usability of commercial GUI software and includes recent innovations (Cox FDWRA, interactive window QC, azimuthal analysis)."

**Figure 8: Case Study Results**
- Example HVSR analysis from a real or realistic synthetic dataset
- Show: input waveform, window spectra, QC statistics, final HVSR curve with peak detection
- Include before/after Cox FDWRA comparison
- Caption: "Example HVSR analysis of a soft-soil site. (a) Input 30-minute continuous recording with three components. (b) Window spectra showing HVSR curves from all windows (gray, transparent) and mean curve (black). (c) Quality control statistics before and after Cox FDWRA, showing number of windows retained. (d) Final HVSR curve with 16–84% uncertainty band and detected fundamental mode (peak frequency = 1.3 Hz, amplitude = 3.8)."

---

## 12. Conclusion and Next Steps

HVSR Pro represents a significant contribution to the seismic engineering and geophysics communities by:

1. **Lowering barriers to entry**: Non-programmers can now perform rigorous HVSR analysis
2. **Ensuring transparency**: All algorithms and parameters are visible and reproducible
3. **Incorporating best practices**: Implementation of Cox et al. (2020) FDWRA and SESAME compliance
4. **Enabling advanced workflows**: Interactive QC, azimuthal analysis, and batch processing
5. **Maintaining scientific rigor**: Statistical checks, uncertainty quantification, quality metrics

The software is ready for publication and has potential for significant impact on how HVSR studies are conducted in academia and practice.

