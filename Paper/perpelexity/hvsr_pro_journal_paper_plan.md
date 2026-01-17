# Comprehensive Journal Paper Plan for HVSR Pro

## 1. Strategy & Target Journal

**Recommended Target:** **Seismological Research Letters (SRL)**
*   **Specific Section:** *Electronic Seismologist*
*   **Why:** This column is the industry standard for introducing new software. It favors "utility" and "usability" over novel theoretical math. It is where tools like *ObsPy*, *Geopsy*, and *hvsrpy* are discussed.
*   **Alternative:** *Computers & Geosciences* (if you want to focus more on the Python/PyQt5 architecture than the seismic application).

**Core Narrative ("The Story"):**
"While the science of HVSR is mature, the *tools* available to practitioners are polarized: either expensive black-box commercial software or complex command-line open-source libraries. **HVSR Pro** bridges this gap by providing a transparent, open-source graphical environment that makes advanced processing (like the Cox et al. 2020 algorithm) accessible to non-coders."

---

## 2. Detailed Manuscript Outline

### **Title (Working)**
*HVSR Pro: An Open-Source Graphical Environment for Robust Horizontal-to-Vertical Spectral Ratio Analysis*

### **Abstract (200-250 words)**
*   **Context:** Ambient noise HVSR is a standard non-invasive site characterization method.
*   **Problem:** Current workflows are bifurcated: opaque commercial tools vs. code-heavy libraries (e.g., *hvsrpy*) that hinder reproducibility and ease of use.
*   **Solution:** Introduce **HVSR Pro**, a Python-based GUI application.
*   **Key Features:** Highlight (1) Interactive window management (the "Click-to-Reject" canvas), (2) Implementation of the Cox et al. (2020) frequency-domain rejection algorithm (FDWRA), and (3) Azimuthal analysis capabilities.
*   **Impact:** Enables reproducible, publication-quality analysis for both researchers and engineering practitioners.

### **1. Introduction**
*   **Paragraph 1: The Method.** Briefly define HVSR. It's cost-effective and essential for seismic microzonation and site fundamental frequency ($f_0$) estimation. Cite SESAME (2004).
*   **Paragraph 2: The Software Landscape.**
    *   *Commercial:* Robust GUIs but expensive, closed-source, and "black box" (hard to verify results).
    *   *Open Source:* *Geopsy* (the gold standard, but aging interface), *hvsrpy* (excellent math, but command-line only).
*   **Paragraph 3: The Gap.** There is a need for a modern, open-source GUI that integrates recent algorithmic advances (like rigorous statistical rejection) without requiring coding skills.
*   **Paragraph 4: Contribution.** Introduce HVSR Pro. State that it is written in Python/PyQt5, is cross-platform, and emphasizes *interactivity* and *transparency*.

### **2. Software Architecture (The "Engine")**
*   *Keep this concise. Focus on modularity.*
*   **Tech Stack:** Python 3, PyQt5 (GUI), ObsPy (I/O), NumPy/SciPy (Math), Matplotlib (Plotting).
*   **Design Pattern:** Model-View-Controller (MVC) approach. Separation of the *processing logic* (API) from the *interface* (GUI). This ensures scientific accuracy independent of the UI.
*   **Data Handling:** Describe the ability to import MiniSEED (standard seismic) and CSV/ASCII (engineering) formats. Mention the "Channel Mapping" feature that handles inconsistent field file naming.

### **3. Methodology & Algorithms (The "Science")**
*   *Do not derive equations. State the "Rules" the software follows.*
*   **Standard Processing:** "We follow the SESAME (2004) guidelines."
    *   **Equation 1:** The HVSR ratio formula (Geometric mean of horizontals / Vertical).
    *   **Equation 2:** Konno-Ohmachi smoothing function (briefly cited).
*   **Quality Control (QC):** Describe the "Two-Tier" approach:
    *   *Tier 1:* Time-domain thresholds (STA/LTA, saturation checks).
    *   *Tier 2:* Frequency-domain checks.
*   **Advanced Feature: Cox FDWRA:**
    *   Explain *why* it's included: To remove windows that are statistically inconsistent (outliers).
    *   **Equation 3:** The rejection criterion: $\mu - n\sigma \le f_{peak} \le \mu + n\sigma$.
    *   Highlight that HVSR Pro allows users to visualize this convergence iteratively.

### **4. Key Features & Workflow (The "User Experience")**
*   *This is the core of the paper.*
*   **Interactive Window Management:** Describe the "Interactive Canvas." Users can see the timeline, click a window, and see the HVSR curve update *instantly*. This "human-in-the-loop" approach is a major improvement over static batch processing.
*   **Azimuthal Analysis:** Describe the capability to rotate horizontal components from 0–180° to detect directional resonance (e.g., topographic effects or faults).
*   **Reproducibility:** Mention that all settings (presets) can be saved/exported, allowing other researchers to replicate the exact processing steps.

### **5. Application Example (Validation)**
*   *Use a simple dataset to prove it works.*
*   **Dataset:** Use a standard open dataset (e.g., from the SESAME project or a clear 1Hz site).
*   **Workflow:**
    1.  Import data.
    2.  Apply "Balanced" QC preset.
    3.  Run Cox FDWRA (show before/after).
    4.  Result: $f_0 = 1.X$ Hz, matching known values.
*   **Figure Reference:** Link this section to Figure 5 (the "Results" figure).

### **6. Discussion & Conclusions**
*   **Strengths:** Modern UI, transparent code, rigorous algorithms (FDWRA).
*   **Limitations:** Currently focuses on single-station analysis (future work: array processing/SPAC).
*   **Availability:** GitHub link, license (MIT/GPL), and installation via pip/conda.

---

## 3. Detailed Figure Plan (Crucial for Software Papers)

**Figure 1: The "Hero" Shot (Main Interface)**
*   **Content:** The main `InteractiveCanvas`.
*   **Detail:** Show the three-panel layout:
    *   *(Top)* Timeline of windows (Green = Accepted, Grey = Rejected).
    *   *(Middle)* The HVSR curve with uncertainty bounds.
    *   *(Bottom)* Quality Score scatter plot.
*   **Caption:** "The primary interface of HVSR Pro. The **Interactive Canvas** allows users to visually inspect and toggle individual time windows (top), with immediate updates to the HVSR curve (middle) and statistical quality metrics (bottom)."

**Figure 2: Workflow Flowchart**
*   **Content:** A block diagram of the data flow.
*   **Detail:** `Raw Data (MiniSEED/CSV)` $\rightarrow$ `Preprocessing (Windowing)` $\rightarrow$ `QC (STA/LTA, Thresholds)` $\rightarrow$ `Processing (FFT, Smoothing)` $\rightarrow$ `Cox FDWRA (Iterative)` $\rightarrow$ `Final Result`.
*   **Caption:** "Data processing workflow. The software integrates standard SESAME guidelines with optional advanced statistical rejection (Cox FDWRA) and interactive manual review."

**Figure 3: QC Configuration Panel**
*   **Content:** Screenshot of the Settings tab.
*   **Detail:** Highlight the **"Presets"** dropdown (showing "SESAME Standard") and the **"Cox FDWRA"** parameter group (n-sigma, iterations).
*   **Caption:** "Configuration transparency. Users can select rigorous presets or fine-tune individual algorithm parameters, such as the standard deviation multiplier ($n$) for the frequency-domain window rejection algorithm."

**Figure 4: Azimuthal Analysis**
*   **Content:** A 2x2 grid of azimuthal plots.
*   **Detail:**
    *   *Left:* Polar plot (Frequency vs. Azimuth).
    *   *Right:* Contour map (Azimuth vs. Frequency, color = Amplitude).
*   **Caption:** "Azimuthal processing results. Directional variations in the resonance frequency can be analyzed to identify topographic effects or subsurface anisotropy."

**Figure 5: Validation/Result Plot**
*   **Content:** A publication-ready output figure generated by the software.
*   **Detail:** A clean HVSR curve with the peak frequency marked, uncertainty bounds shaded, and a table of statistics (peak freq, amplitude) embedded.
*   **Caption:** "Standard publication-ready output. The figure displays the mean HVSR curve (black), standard deviation (gray shading), and peak frequency statistics, automatically generated by the reporting module."

---

## 4. Reading List & References

I have analyzed the structure of these papers to derive the plan above. You should cite 3-4 of these to establish context.

1.  **Geopsy Reference:**
    *   *Wathelet, M., et al. (2020).* "Geopsy: A User-Friendly Open-Source Tool Set for Ambient Vibration Processing." *Seismological Research Letters*.
    *   *Why read/cite:* This is your main competitor/inspiration. Acknowledge it as the "standard" you are building upon.

2.  **hvsrpy Reference:**
    *   *Vantassel, J. P. (2021).* "hvsrpy: An Open-Source Python Package for Microtremor HVSR Analysis."
    *   *Why read/cite:* This provides the math (Cox FDWRA) you implemented. You bridge their code with a GUI.

3.  **Cox FDWRA Algorithm:**
    *   *Cox, B. R., et al. (2020).* "A Systematic Assessment of the Effects of Window Selection on HVSR Peak Frequency."
    *   *Why read/cite:* This is the *scientific justification* for your "Advanced Feature."

4.  **SESAME Guidelines:**
    *   *SESAME Project (2004).* "Guidelines for the Implementation of the H/V Spectral Ratio Technique."
    *   *Why read/cite:* The "Bible" of HVSR. Your software claims compliance with this.

5.  **General Software Paper Example:**
    *   *Beyreuther, M., et al. (2010).* "ObsPy: A Python Toolbox for Seismology." *SRL*.
    *   *Why read:* Perfect example of how to write a Python software paper for seismologists.

---

## 5. Next Actionable Steps

1.  **Generate Figures 1 & 4:** Open your software, load a sample file, and take high-res screenshots of the "Interactive Canvas" and the "Azimuthal" tab.
2.  **Draw Figure 2:** Use PowerPoint or Draw.io to make the flowchart based on the description above.
3.  **Write "Methodology" Section:** Draft the text surrounding the 3 equations (HVSR formula, Smoothing, Rejection). Use the `hvsr_pro_repository_context.md` I provided earlier for the technical details.
4.  **Submit:** Aim for *Seismological Research Letters* (Electronic Seismologist column).

