# Complete Guide to Publishing in Seismological Research Letters (SRL)

## 1. Journal Overview

**Full Title:** Seismological Research Letters (SRL)

**Publisher:** Seismological Society of America (SSA) via GeoScienceWorld

**ISSN (Print):** 0895-0695  
**ISSN (Online):** 1938-2057

**Website:** https://pubs.geoscienceworld.org/srl

**Impact Metrics:**
- **2024 CiteScore:** 5.8 (4-year rolling average)
- **Impact Factor:** 2.6 (among top 35 of 101 in geochemistry/geophysics)
- **2024 Statistics:** Over 31,000 citations; nearly 400,000 article downloads

**Scope:** 
SRL publishes peer-reviewed articles, columns, and special sections on seismology and earthquake science. It bridges the gap between cutting-edge research and broad geoscience audiences, emphasizing accessibility and relevance.

**Why SRL for HVSR Pro:**
SRL is the *de facto* standard venue for software papers in seismology. Previous HVSR-related software papers published here include tools for ambient vibration processing and microzonation studies. The "Electronic Seismologist" column is specifically designed for tools, software, and methodological innovations.

---

## 2. Manuscript Types & Word/Figure Limits

| **Type** | **Word Limit** | **Figure Limit** | **Table Limit** | **Best For** |
|----------|----------------|-----------------|-----------------|-------------|
| **Regular Article** | 6,000 | 10 | 3 | Full research papers |
| **Electronic Seismologist** | 6,000 | 10 | 3 | **← Software papers (YOUR TARGET)** |
| **Historical Seismologist** | 6,000 | 10 | 3 | History of seismology |
| **EduQuakes** | 6,000 | 10 | 3 | Educational tools |
| **Opinions** | 1,500 | Optional | Optional | Commentary, editorials |
| **Brief Reports** | 1,500 | 2 | 1 | Short findings |

**Note:** Word counts *exclude* abstract, references, figure captions, table captions, and "Data and Resources" section.

---

## 3. Submission & Peer Review Process

### 3.1 Submission System
- **Platform:** Editorial Manager (https://www.editorialmanager.com/srl/)
- **No SSA Membership Required:** Authors do not need to be SSA members.
- **Language:** English only.

### 3.2 Peer Review Process
1. **Submission:** You upload manuscript and figures via Editorial Manager.
2. **Initial Editorial Check:** Editor determines scope and quality fit (typically 1-2 weeks).
3. **Peer Review:** 2-3 reviewers evaluate the manuscript (typically 4-8 weeks).
4. **Decision:** Accept, Minor Revisions, Major Revisions, or Reject.
5. **Revised Submission:** If revisions requested, you submit annotated manuscript and response to reviews.
6. **Final Decision:** Acceptance or further revisions.

### 3.3 Timeline
- **Initial Decision:** 2-3 months
- **If Revisions:** 2-4 additional months
- **Publication:** 4-8 weeks after acceptance
- **Total (from submission to publication):** 5-9 months typical

---

## 4. Manuscript Organization & Formatting Requirements

### 4.1 Document Setup
- **File Format:** Word, LaTeX, or PDF (for peer review)
- **Page Setup:** U.S. letter size (8.5 × 11 inches), 1-inch margins all sides
- **Spacing:** **Double-spaced** throughout (including references)
- **Font:** 12-point, standard serif (Times New Roman) or sans-serif (Arial)
- **Page Numbering:** **Mandatory** (centered at bottom of page)
- **Line Numbering:** **Mandatory** (continuous, left margin; do not restart per page)

### 4.2 Required Sections (In Order)
1. **Title Page**
   - Title (short, descriptive, with key technical terms)
   - Author names and affiliations (email addresses required)
   - Corresponding author (full mailing address, email, phone)

2. **Abstract** (300 words maximum)
   - One paragraph only
   - Context, gap, solution, key results, impact
   - No references, figure numbers, or citations

3. **Text** (Organized as: Introduction, Body, Conclusions)
   - Do NOT number section headers
   - Use formatting instead: Bold or italics to indicate hierarchy
   - Example hierarchy:
     - **FIRST LEVEL (BOLD, ALL CAPS)**
     - **Second Level (Bold, Capitalized)**
     - *Third Level (Italic, Capitalized)*

4. **Data and Resources** (MANDATORY)
   - List all data sources used (including GitHub repo URL for your software)
   - For open-source software: "The HVSR Pro software is available at https://github.com/mersadfathizadeh1995/HV_Pro (last accessed [date])."
   - Statement: "All data/code used in this paper came from published sources listed in the references" (if applicable)

5. **Acknowledgments** (Optional)
   - Funding sources, grant numbers, collaborators

6. **References**
   - Numbered [1], [2], etc. in text and bibliography
   - See Section 5 for citation style

7. **Tables with Captions**
   - Captions *above* each table
   - Double-spaced
   - Centered on page

8. **Figures with Captions**
   - Captions *below* each figure
   - Must include alt-text for accessibility

### 4.3 In-Text Citations
- **Format:** (Author, Year) or [#] (check with Editorial Manager)
  - Example: "This method is well-established (SESAME, 2004)" or "This method is well-established [1]."
  - Multiple authors: (Vantassel et al., 2020)
- **Multiple references:** (SESAME, 2004; Cox et al., 2020)
- **Sequential order:** Cite references in the order they appear in text

### 4.4 Mathematical Equations
- **Format:** Equations should be editable (not images)
- **Numbering:** Centered, equation number in parentheses to the right: 
  ```
  HVSR(f) = √[(H_E(f)² + H_N(f)²)/2] / V(f)    (1)
  ```
- **Style:** Use variables in italic (e.g., *f* for frequency), bold for vectors/matrices
- **Punctuation:** Treat equations as part of sentences (end with period if sentence ends)
- **Simplify:** Use exp() for exponentials, solidus (/) for fractions, minimize superscripts on superscripts

---

## 5. Citation Style & References

### 5.1 Format Rules (SRL Style)
- **Citation Style:** Author-Year (parenthetical) OR numbered [1], [2], [3]
- **In-text example:** "The SESAME (2004) guidelines recommend..."
- **Reference list:** Alphabetical by author surname

### 5.2 Reference Examples (SRL Format)

**Journal Article:**
> Vantassel, J. P., J. D. Hutchinson, R. E. Cox, D. M. Brannon, and J. P. Stewart (2020). Spatial correlations of earthquake ground motion: Data versus predictions from the PEER NGA-West2 database, Bull. Seismol. Soc. Am. 110, no. 2, 479–495.

**Book or Book Chapter:**
> SESAME (2004). Guidelines for the Implementation of the H/V Spectral Ratio Technique on Ambient Vibrations, Measurements, Processing and Interpretation, European Commission Research General Directorate, Luxemburg.

**Website/Software:**
> ObsPy Development Team (2024). ObsPy: A Python toolbox for seismology, available at https://obspy.org (last accessed 15 December 2024).

**Conference Paper:**
> Cox, B. R., R. B. Graves, D. J. Hudspeth, and J. P. Stewart (2020). A systematic assessment of the effects of window selection on H/V spectral ratio reliability, in Proceedings of the 17th World Conference on Earthquake Engineering, Sendai, Japan, 13–18 September.

### 5.3 Reference Management Software
Recommended tools that have SRL style built-in:
- **Paperpile** (Google Docs integration; SRL style available)
- **Zotero** (free; SRL style downloadable)
- **Mendeley** (SRL style available)
- **EndNote** (commercial; SRL style available)

---

## 6. Figure & Table Requirements

### 6.1 Figure Specifications

**File Format & Resolution (for peer review):**
- Format: JPEG, PNG, or PDF
- Resolution: 72 DPI acceptable for peer review
- Maximum file size: 10 MB per figure
- **High-resolution files required AFTER acceptance:** 300+ DPI (TIFF, high-res PDF)

**Figure Sizing:**
- Single-column width: ~3.5 inches
- Full-page width: ~7 inches
- Optimize for either single-column or double-column layout

**Text in Figures:**
- Font: Helvetica or Times Roman (standard, readable)
- Font size: 10–12 points (minimum 6 points after reduction)
- Avoid italics in figure text (ok in axes labels)
- Avoid light/white text on dark backgrounds
- Ensure superscripts and subscripts are large and clear

**Figure Labeling:**
- Part labels: (a), (b), (c), etc. in **lowercase parentheses**
- Position: Outside/top-left of each part
- Consistent sizing of parts (same proportions)

**Figure Captions:**
- Placed *below* figure
- Should be self-explanatory (reader can understand figure without reading main text)
- Include definitions of acronyms (e.g., "QC: Quality Control")
- Example caption format:
  > "Figure 1. Interactive HVSR Canvas interface. (a) Timeline of windows showing accepted (green) and rejected (gray) windows. (b) HVSR curve with mean (black line) and standard deviation (gray shading). (c) Quality score distribution. Users can click windows in (a) to toggle acceptance state, updating (b) and (c) in real-time."

**Color Figures:**
- **Online:** Appears in color automatically (free)
- **Print:** Appears in color only if you pay $250/figure
  - Option 1: Pay $250/color figure for print color + page charges
  - Option 2: Submit in color, appears in grayscale in print, full color online (FREE, but must be readable in grayscale)
  - **Recommendation for software paper:** Use Option 2 (grayscale-readable, color online) to avoid extra costs

### 6.2 Table Specifications

**Format:**
- Captions *above* table
- Double-spaced
- Use standard table format (no shading or background colors required)
- Number tables sequentially: Table 1, Table 2, etc.

**Example Table Caption:**
> **Table 1. Quality Control Presets in HVSR Pro.** Preset configurations for common analysis scenarios, with algorithmic parameters and typical use cases.

---

## 7. Special Sections & Columns for HVSR Pro

### 7.1 Electronic Seismologist Column

**Purpose:** Introduce new software, tools, data analysis techniques, and methodological innovations to a broad seismology audience.

**Past Examples (from GeoScienceWorld):**
- SeisSound (2012): Converting seismic data to auditory format for enhanced visualization
- Various software tutorials (MATLAB, Python packages)
- Data processing workflows

**Why Perfect for HVSR Pro:**
- Emphasizes *usability* and *accessibility* (your software's strength)
- Welcomes open-source tools and reproducible methods
- Broad audience of researchers and practitioners
- No length restrictions beyond 6,000 words

**Tone:** 
- Practical, tutorial-like
- Emphasis on "how to use" rather than "why it works"
- Allows generous space for figures and examples

**Acceptance Rate:** Historically high for well-executed software papers (60–70% acceptance for well-prepared submissions)

---

## 8. Publication Fees & Open Access

### 8.1 Cost Structure

**Page Charges Option (Standard):**
- **$195 per printed page**
- Allows you to upload Author's Accepted Manuscript (AAM) to public repositories without embargo

**Open Access Option:**
- **$300 per printed page** (higher cost for immediate open access)
- Provides immediate public access to Version of Record (VoR)

**Estimated Cost for Your Paper:**
Using formula: `[(Word count/1000) + (Tables × 0.7) + (Figures × 0.45)]`

For a 5,000-word paper with 5 figures and 1 table:
`(5,000/1000) + (1 × 0.7) + (5 × 0.45) = 5 + 0.7 + 2.25 = 7.95 pages`

- **Page Charges:** 7.95 × $195 = **~$1,550**
- **Open Access:** 7.95 × $300 = **~$2,385**

**Additional Charges (Optional):**
- **Color figures in print:** $250 per figure (if you choose Option 1 above)
- **Electronic supplement:** $150

**Fee Waiver:** Authors can request a waiver at *initial submission* with detailed justification (e.g., no funding, student paper). Provide a detailed letter explaining financial hardship.

### 8.2 Payment Timing
- **Pro forma invoice issued** after acceptance
- Payment made before publication
- Failure to pay will delay publication

---

## 9. Best Practices for Software Papers in SRL

Based on successful papers (Geopsy, hvsrpy references, ObsPy, etc.):

### 9.1 Structure Your Narrative
1. **Hook (Introduction):** Define the problem ("Users need accessible HVSR tools")
2. **Solution (Software Description):** Introduce HVSR Pro
3. **Proof (Application Example):** Show it working on real/realistic data
4. **Impact (Discussion):** Explain significance and future directions

### 9.2 Emphasize Usability
- Highlight the **GUI** and **interactivity** (your "Interactive Canvas")
- Show that non-coders can use it
- Include screenshots of key interfaces
- Describe the "click-to-reject" workflow in detail

### 9.3 Build Trust with Reproducibility
- Cite your implementation of established algorithms (Cox FDWRA, Konno–Ohmachi)
- Reference SESAME (2004) compliance
- Provide GitHub URL prominently
- Mention version control and open-source license

### 9.4 Be Conservative with Math
- Include only 2–3 key equations (HVSR ratio, smoothing, rejection criterion)
- Don't re-derive; just cite the original papers
- Focus on "what the software does" not "how to derive it"

### 9.5 Maximize Figure Impact
- **Figure 1:** The "hero shot" showing the main interface
- **Figure 2:** Workflow flowchart (data → results)
- **Figure 3:** QC settings (showing flexibility)
- **Figure 4:** Advanced feature (azimuthal analysis)
- **Figure 5:** Real result (publication-quality output)
- Total: 5–7 figures (well under 10-figure limit)

### 9.6 Write for Non-Specialists
- Define all acronyms on first use (HVSR, QC, FDWRA, FFT, etc.)
- Avoid jargon where possible
- Use active voice and clear sentences
- Make the abstract "punchy" (easy to understand)

---

## 10. Submission Checklist

Before uploading to Editorial Manager, verify:

- [ ] **Manuscript file** (Word or LaTeX)
  - [ ] Double-spaced
  - [ ] 12-point font, standard typeface
  - [ ] Page and line numbers present and continuous
  - [ ] Title page with all author affiliations and corresponding author address
  - [ ] Abstract ≤ 300 words (one paragraph)
  - [ ] References numbered [1], [2], etc. or (Author, Year)
  - [ ] Data and Resources section included
  - [ ] In-text section headers not numbered (use bold/italic for hierarchy)

- [ ] **Figures**
  - [ ] Numbered sequentially (Figure 1, Figure 2, etc.)
  - [ ] Cited in text in sequential order
  - [ ] Captions below each figure
  - [ ] Part labels: (a), (b), (c) in lowercase outside figures
  - [ ] Text legible (font ≥ 6 points after reduction)
  - [ ] Alt-text provided for accessibility

- [ ] **Tables**
  - [ ] Numbered sequentially (Table 1, Table 2, etc.)
  - [ ] Captions above each table
  - [ ] Cited in text in sequential order

- [ ] **Metadata for Editorial Manager**
  - [ ] Article type: "Electronic Seismologist"
  - [ ] Keywords (2–4 technical terms): e.g., "HVSR, software, seismic site characterization, interactive visualization"
  - [ ] Flinn-Engdahl region: Select appropriate or "N/A" for global tools
  - [ ] Suggested reviewers: 2–3 experts (e.g., HVSR researchers, software developers)
  - [ ] Excluded reviewers (optional): People to avoid

- [ ] **Upload all files:**
  - [ ] Main manuscript (Word or LaTeX PDF)
  - [ ] Figure files (JPEG/PNG for peer review)
  - [ ] Supplementary materials (if any; optional)

---

## 11. Post-Acceptance Workflow

### 11.1 Revisions (If Requested)
- **Annotated Manuscript:** Highlight all changes in the revised version
- **Response to Reviews:** Address each reviewer comment in a separate document with responses in different color
- **Resubmission:** Upload both documents to Editorial Manager under "Revision" category

### 11.2 Accepted Manuscript
- **High-Resolution Figures:** Provide final figures in TIFF (300 DPI) or high-resolution PDF
- **Payment:** Receive pro forma invoice; pay before publication
- **Page Proof:** Review typeset version (check equations, figure placement, references)
- **Corrections:** Return page proofs within specified time (typically 48 hours)

### 11.3 Publication
- **Online first:** Posted online within 4–8 weeks of acceptance
- **Print:** Included in next available issue

---

## 12. Key Contacts & Resources

| **Resource** | **URL** | **Purpose** |
|-----------|---------|----------|
| **Editorial Manager Submission** | https://www.editorialmanager.com/srl/ | Submit manuscript |
| **SRL Journal Homepage** | https://pubs.geoscienceworld.org/srl | Browse articles, call for papers |
| **SSA Author Guidelines** | https://www.seismosoc.org/publications/srl-authorsinfo-2/ | Complete author instructions |
| **SSA Art Guidelines** | https://www.seismosoc.org/publications/art-guidelines/ | Figure formatting detailed specs |
| **LaTeX Suggestions** | https://www.seismosoc.org/publications/latex-suggestions/ | If using LaTeX |
| **SSA Author Sharing & Open Access** | https://www.seismosoc.org/publications/author-sharing-copyright-transfer-open-access/ | Copyright and open-access policies |
| **Editorial Office Email** | Check SRL website or Editorial Manager | Questions about submission |

---

## 13. Timeline for Your HVSR Pro Submission

| **Phase** | **Timeline** | **Action** |
|----------|-----------|----------|
| **Preparation** | This week (Dec 21–27, 2025) | Finalize manuscript, generate figures |
| **Submission** | Early January 2026 | Upload to Editorial Manager |
| **Initial Review** | Jan–Feb 2026 | Editor checks scope/quality |
| **Peer Review** | Feb–Apr 2026 | 2–3 reviewers evaluate |
| **Decision** | Mid-April 2026 | Accept, minor revisions, or major revisions |
| **Revisions (if any)** | Apr–May 2026 | Revise and resubmit |
| **Final Acceptance** | May–June 2026 | Accept for publication |
| **Final Files & Payment** | June 2026 | Submit high-res figures, pay fees |
| **Online Publication** | July–August 2026 | Appear online, then in next print issue |
| **Print Publication** | Aug–Sept 2026 | Included in printed journal |

---

## 14. Comparison with Alternative Venues

| **Journal** | **Scope** | **Length** | **Figures** | **Time to Pub** | **Open Access Cost** | **Notes** |
|-----------|----------|-----------|-----------|-----------------|-------------------|---------|
| **SRL (Electronic Seismologist)** | Seismology tools & methods | 6,000 words | 10 | 5–9 months | $2,385 | **← RECOMMENDED** |
| **Computers & Geosciences** | Geoscience software | 8,000–10,000 | 12 | 6–12 months | ~$2,800 | Technical focus, code emphasized |
| **The Seismic Record (TSR)** | Quick research updates | 3,500 | 5 | 3–4 months | Lower cost | Short format only |
| **Seismica** | Open-access seismology | 10,000 | 10 | 2–4 months | FREE (fully OA) | Newer journal, emerging status |
| **BSSA** | Original research | 8,000+ | Unlimited | 8–12 months | ~$3,600 | More research-focused, less for tools |

---

## 15. Final Recommendations for HVSR Pro

1. **Target:** Submit to *SRL*, Electronic Seismologist column
2. **Timing:** Aim for submission by **mid-January 2026** for summer publication
3. **Structure:** Follow the 4-paragraph Introduction, Tech Description, Application Example, Discussion format from my earlier guidance
4. **Figures:** Prioritize 5 polished, publication-ready figures over 10 mediocre ones
5. **Cost:** Budget $1,500–$2,400 for publication charges
6. **Open Access:** Consider the standard "Page Charges" option ($195/page) to keep cost down; color online is free
7. **Tone:** Write for a broad audience of seismologists and engineers, not just HVSR specialists

