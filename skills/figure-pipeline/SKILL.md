---
name: figure-pipeline
description: "Single-command figure regeneration with quality checks. Runs all figure-generating scripts and validates for overlapping text, clipped labels, empty panels, Turkish characters, DPI compliance, and color consistency. Use whenever the user needs to regenerate figures, says 'update the figures', or before submission to check figure quality."
allowed-tools: [Read, Bash, Grep, Glob, Write, TodoWrite]
license: MIT License
metadata:
    skill-author: Bora Ulukapı
    version: "1.0.0"
---

# Figure Pipeline — Regenerate and Validate All Project Figures

This skill regenerates every figure in the project and runs quality/validation checks tailored to the common issues Bora encounters: overlapping text, clipped labels, empty panels, Turkish character rendering failures, stale figures, and inconsistent color palettes.

It works for both large bibliometric projects (many figures, complex dependency chains) and smaller clinical studies (fewer figures, simpler pipelines).

---

## Procedure

### Step 0: Set Up a Todo List

Create a TodoWrite tracking list with the following items:
- Discover figure-generating scripts and build dependency graph
- Run all scripts in dependency order
- Validate generated figures (existence, size, format, freshness)
- Run quality checks (DPI, Turkish chars, clipping, colors)
- Check manuscript references for missing figures
- Produce final report

Mark each item in_progress as you begin it, and completed when done.

---

### Step 1: Discover Figure-Generating Scripts

Use Glob and Grep to find every script that produces figures.

1. **Find candidate scripts:**

   ```
   Glob: scripts/**/*.py
   Glob: src/**/*.py
   Glob: analysis/**/*.py
   Glob: *.py  (root-level scripts)
   ```

2. **Filter to figure-generating scripts** by grepping each candidate for:
   - `import matplotlib` or `from matplotlib`
   - `import seaborn` or `from seaborn`
   - `savefig`
   - `figures/` or `figs/` or `output/` in a save path
   - `plt.savefig`, `fig.savefig`

3. **Read `pipeline-state.json`** if it exists at the project root. This file may contain:
   ```json
   {
     "figures": [
       {"name": "fig01_flowchart.pdf", "script": "scripts/01_flowchart.py"},
       ...
     ]
   }
   ```
   Use it to cross-reference discovered scripts against the expected figure list.

4. **Build the dependency graph.** For each script:
   - Read the file and extract all `savefig(...)` calls to identify output filenames.
   - Check for imports of other project modules (one script depending on another's output).
   - Check for data file reads that might be produced by earlier scripts.
   - Assign a numeric order: if filenames or script names contain numbers (e.g., `01_`, `02_`), sort by that. Otherwise, use topological order from dependencies. If no ordering signal exists, use alphabetical order.

5. **Identify the figures directory.** Look for:
   - `figures/`, `figs/`, `output/figures/`, `results/figures/`
   - Whatever paths appear in `savefig()` calls.

Store the full mapping: `{script_path -> [output_figure_paths]}` and the execution order.

---

### Step 2: Run All Scripts in Dependency Order

For each script, in the determined order:

1. **Set environment for headless rendering:**

   ```bash
   MPLBACKEND=Agg python <script_path>
   ```

   If scripts accept arguments (check with `--help` or by reading the argparse section), use sensible defaults or read from `pipeline-state.json`.

2. **Capture output and timing:**

   ```bash
   time MPLBACKEND=Agg python <script_path> 2>&1
   ```

3. **Record the result:** PASS if exit code is 0, FAIL otherwise. Store stdout/stderr for the report.

4. **If a script fails:**
   - Log the error.
   - Check if the failure is due to a missing dependency (ModuleNotFoundError) and report it.
   - Continue to the next script (do not abort the pipeline).

5. **Force DPI 300 if possible.** Before running each script, check if it sets DPI. If not, prepend a matplotlib rcParams override:

   ```bash
   MPLBACKEND=Agg python -c "
   import matplotlib
   matplotlib.rcParams['savefig.dpi'] = 300
   matplotlib.rcParams['figure.dpi'] = 300
   " && MPLBACKEND=Agg python <script_path>
   ```

   Note: The above only works if the script itself does not override DPI. A more robust approach: grep the script for `dpi=` settings. If the script already sets DPI >= 300, leave it alone. If it sets DPI < 300 or does not set it at all, create a temporary wrapper:

   ```python
   import matplotlib
   matplotlib.rcParams['savefig.dpi'] = 300
   matplotlib.rcParams['figure.dpi'] = 300
   exec(open('<script_path>').read())
   ```

   Run the wrapper instead. Clean up the temporary file after.

---

### Step 3: Validate Each Generated Figure

For every figure in the expected list (from Step 1):

1. **Existence check:** Does the file exist at the expected path?

2. **Non-zero size:** Is the file size > 0 bytes?
   ```bash
   stat -f%z <figure_path>   # macOS
   ```

3. **PDF validity** (for .pdf figures):
   ```bash
   pdfinfo <figure_path>
   ```
   If pdfinfo is not installed, try:
   ```bash
   python3 -c "
   import subprocess
   try:
       subprocess.run(['pdfinfo', '$FIGURE'], check=True, capture_output=True)
       print('VALID')
   except FileNotFoundError:
       # Fallback: check PDF header
       with open('$FIGURE', 'rb') as f:
           header = f.read(5)
           print('VALID' if header == b'%PDF-' else 'INVALID')
   "
   ```

4. **Image dimensions** (for .png/.jpg/.tiff):
   ```bash
   python3 -c "
   from PIL import Image
   img = Image.open('<figure_path>')
   w, h = img.size
   print(f'{w}x{h}')
   if w == 0 or h == 0:
       print('ERROR: zero dimension')
   elif w > 20000 or h > 20000:
       print('WARNING: unusually large')
   "
   ```

5. **Freshness check:** Compare the figure's modification time against the script's modification time.
   ```bash
   python3 -c "
   import os
   fig_mtime = os.path.getmtime('<figure_path>')
   script_mtime = os.path.getmtime('<script_path>')
   if fig_mtime < script_mtime:
       print('STALE: figure is older than script')
   else:
       print('FRESH')
   "
   ```

---

### Step 4: Quality Checks

Run a comprehensive Python quality check script via Bash:

```python
#!/usr/bin/env python3
"""Figure quality checker for the figure pipeline skill."""

import os
import sys
import json
import struct
import re
from pathlib import Path

results = {
    "dpi_compliance": [],
    "empty_panels": [],
    "turkish_chars": [],
    "clipping_protection": [],
    "color_palettes": [],
    "font_sizes": [],
}

# --- Helpers ---

def check_dpi_png(filepath):
    """Read DPI from PNG pHYs chunk."""
    try:
        from PIL import Image
        img = Image.open(filepath)
        dpi = img.info.get("dpi", (72, 72))
        return dpi[0] >= 299  # allow rounding
    except Exception:
        return None  # cannot determine

def check_dpi_pdf(filepath):
    """Check if PDF contains high-res images by examining embedded image dimensions."""
    try:
        import subprocess
        result = subprocess.run(["pdfinfo", filepath], capture_output=True, text=True)
        # pdfinfo does not directly report image DPI; we rely on script-level DPI setting
        return True if result.returncode == 0 else None
    except FileNotFoundError:
        return None

def check_turkish_in_script(script_path):
    """Check if a script uses Turkish characters and whether it configures fonts properly."""
    turkish_chars = set("şçöüğıİŞÇÖÜĞ")
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
    has_turkish = bool(turkish_chars & set(content))
    has_font_config = (
        "rcParams" in content and "font" in content
    ) or "FontProperties" in content or "DejaVu" in content
    return has_turkish, has_font_config

def check_clipping_protection(script_path):
    """Check if script uses tight_layout or bbox_inches='tight'."""
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
    has_tight_layout = "tight_layout" in content
    has_bbox_tight = "bbox_inches" in content and "tight" in content
    has_constrained = "constrained_layout" in content
    return has_tight_layout or has_bbox_tight or has_constrained

def extract_color_info(script_path):
    """Extract color palette usage from a script."""
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
    palettes = set()
    # Check for named colormaps
    for cmap in ["viridis", "plasma", "inferno", "magma", "cividis",
                 "tab10", "tab20", "Set1", "Set2", "Set3", "Paired",
                 "Pastel1", "Pastel2", "Dark2", "Accent",
                 "Blues", "Reds", "Greens", "Oranges", "Purples",
                 "coolwarm", "RdBu", "RdYlBu", "RdYlGn", "Spectral"]:
        if cmap in content:
            palettes.add(cmap)
    # Check for hex colors
    hex_colors = re.findall(r"['\"]#[0-9a-fA-F]{6}['\"]", content)
    if hex_colors:
        palettes.add(f"custom({len(hex_colors)} hex colors)")
    # Check for named colors
    for color in ["steelblue", "steel blue", "amber", "coral", "teal",
                  "salmon", "forestgreen", "dodgerblue", "crimson"]:
        if color.lower() in content.lower():
            palettes.add(color)
    return palettes

def check_font_sizes(script_path):
    """Check for font size specifications that might be too small."""
    with open(script_path, "r", encoding="utf-8") as f:
        content = f.read()
    issues = []
    # Find fontsize= arguments
    for match in re.finditer(r"fontsize\s*=\s*(\d+)", content):
        size = int(match.group(1))
        if size < 8:
            issues.append(f"fontsize={size} (below 8pt minimum for labels)")
    # Find size= in text/title calls
    for match in re.finditer(r"\.set_.*?size\s*=\s*(\d+)", content):
        size = int(match.group(1))
        if size < 8:
            issues.append(f"element size={size} (below 8pt)")
    return issues

def check_empty_panels_in_figure(filepath):
    """Check if a figure has completely blank/empty panels."""
    try:
        from PIL import Image
        import numpy as np
        img = Image.open(filepath).convert("RGB")
        arr = np.array(img)
        # Check if image is entirely white or entirely one color
        if arr.std() < 1.0:
            return True  # essentially blank
        # Check quadrants for emptiness (multi-panel detection)
        h, w = arr.shape[:2]
        quadrants_blank = 0
        for qy in [0, h // 2]:
            for qx in [0, w // 2]:
                quad = arr[qy:qy + h // 2, qx:qx + w // 2]
                if quad.std() < 2.0:
                    quadrants_blank += 1
        return quadrants_blank  # number of blank quadrants
    except Exception:
        return None

# These functions are called from the main pipeline below.
```

Run this quality check logic for every script+figure pair discovered in Step 1. Aggregate results.

#### 4a. DPI Compliance

For each .png figure, read the DPI metadata. For .pdf figures, check the script for `dpi=` settings. Flag anything below 300 DPI.

#### 4b. Turkish Character Rendering

For each script that contains Turkish characters (ş, ç, ö, ü, ğ, ı, İ, Ş, Ç, Ö, Ü, Ğ):
- Verify the script configures a Unicode-capable font (DejaVu Sans, Arial, etc.).
- If the figure is a PNG, rasterize and attempt OCR or pixel-level check for missing-glyph rectangles (tofu). A simpler heuristic: if the script contains Turkish text but does NOT configure `rcParams['font.family']` or use `FontProperties`, flag a WARNING.

#### 4c. Clipping Protection

For each script, verify at least one of:
- `plt.tight_layout()` is called
- `bbox_inches='tight'` is passed to `savefig()`
- `constrained_layout=True` is set on the figure

If none are present, flag a WARNING — labels and titles may be clipped.

#### 4d. Color Palette Consistency

Collect all palette/colormap references across all scripts. If more than 2 distinct named colormaps are used (e.g., one script uses `viridis`, another uses `tab10`, another uses `Set2`), flag a WARNING for inconsistency. Report what each script uses.

#### 4e. Font Size Check

Flag any `fontsize=` below 8 for labels or below 10 for titles.

#### 4f. Empty Panel Detection

For PNG figures, use PIL to check if any quadrant of the image is blank (std deviation of pixel values < 2.0). This catches cases where a subplot was created but never drawn to.

#### 4g. Tufte + SwD Audit (advisory)

Apply the canonical principles from the `dataviz-principles` skill. **Warnings only — do not fail the pipeline on these.**

Detect and flag (cite the violation code so the reader knows where to read):

- **T-B1 (lie factor)** — bar charts without a zero baseline (grep the script for `ylim`/`set_ylim`/`ax.set_ylim` with a non-zero lower bound on a bar chart context); flag `non-zero bar baseline`.
- **T-B5 (chartjunk-via-color)** — count distinct fill colors per panel via PIL color quantization; if `distinct_colors > number_of_categorical_dimensions_encoded`, warn `decorative color`.
- **T-B6 (pie/donut)** — detect circular plots: grep scripts for `plt.pie`, `ax.pie`, `wedgeprops`, `donut`, `pie chart`. Warn `pie/donut chart — substitute bar`.
- **S-L2 (secondary y-axis)** — grep for `twinx()` or `secondary_y`. Warn `dual axis — separate panels or compute a ratio`.
- **S-L7 (descriptive title)** — extract panel titles via `ax.set_title` / `suptitle`. If the title is a noun phrase with no verb (e.g. "Treatment Modalities", "Age Distribution"), warn `descriptive title — rewrite as active sentence`.

When a script triggers any of these, print:

```
TUFTE/SWD ADVISORY
──────────────────
  fig03_treatment_outcomes.png
    [T-B5] decorative color: 5 distinct fill colors for 5 categorical bars (color encodes nothing).
    [T-B6] pie chart detected in scripts/03_outcomes.py:142 — substitute horizontal bar.
    [S-L7] title "A) Treatment Modalities" is descriptive — rewrite as active sentence stating the takeaway.
```

This is the only step in the pipeline that produces *design* feedback rather than *correctness* feedback. Keep it advisory; the clinician decides what to change.

For the full grading framework (9 Tufte criteria + 7 remedies + 6 SwD lessons), invoke the `dataviz-principles` skill directly.

---

### Step 5: Check Manuscript References

1. **Find .tex files:**
   ```
   Glob: **/*.tex
   ```

2. **Extract figure references:**
   ```
   Grep: \\includegraphics.*?{(.*?)} in all .tex files
   Grep: \\input{.*fig.*} in all .tex files
   ```

3. **Cross-reference** every referenced figure against the actual files in the figures directory. Report:
   - Figures referenced in .tex but not present on disk.
   - Figures present on disk but not referenced in .tex (orphans).

---

### Step 6: Produce the Final Report

Print a structured report to the console:

```
FIGURE PIPELINE REPORT
══════════════════════════════════════════════════════════════

SCRIPT EXECUTION
────────────────
  scripts/01_flowchart.py ................ PASS (2.3s)
  scripts/02_data_overview.py ............ PASS (5.1s)
  scripts/03_temporal_analysis.py ........ PASS (4.7s)
  scripts/04_network_analysis.py ......... FAIL (12.1s)
    → ModuleNotFoundError: No module named 'igraph'
  ...

  Result: 11/12 PASS, 1/12 FAIL

FIGURE VALIDATION
─────────────────
  Generated: 15/16 figures
  Missing: fig14_network_graph.pdf (script 04 failed)

QUALITY CHECKS
──────────────
  DPI compliance ............ 15/15 ✓
  Non-empty panels .......... 14/15 ✓
    ⚠ fig06_subgroup.png — quadrant 3 appears blank
  Freshness ................. 13/15 ✓
    ⚠ fig07_world_map.pdf — older than script (STALE)
    ⚠ fig12_bertopic.pdf — older than script (STALE)
  Turkish characters ........ 15/15 ✓
  Clipping protection ....... 12/15 ✓
    ⚠ fig03_temporal.py — no tight_layout or bbox_inches='tight'
    ⚠ fig09_heatmap.py — no tight_layout or bbox_inches='tight'
    ⚠ fig11_comparison.py — no tight_layout or bbox_inches='tight'
  Font sizes ................ 14/15 ✓
    ⚠ fig05_demographics.py — fontsize=6 (below 8pt minimum)
  Color consistency ......... ✓ primary palette: steelblue + custom hex
    All scripts use compatible palettes.

MANUSCRIPT CROSS-REFERENCE
──────────────────────────
  Figures in .tex: 16
  Figures on disk: 15
  Missing: fig14_network_graph.pdf (referenced in results.tex line 142)
  Orphans: fig_appendix_extra.pdf (on disk but not in manuscript)

RECOMMENDED ACTIONS
───────────────────
  1. Install igraph: pip install python-igraph (for script 04)
  2. Rerun scripts/05_geographic_analysis.py (world map stale)
  3. Rerun scripts/08_bertopic_analysis.py (bertopic stale)
  4. Add tight_layout() to scripts 03, 09, 11
  5. Increase fontsize in scripts/05_demographics.py (currently 6pt)
  6. Check fig06_subgroup.png panel 3 — may have empty subplot

══════════════════════════════════════════════════════════════
Pipeline complete. 3 warnings, 1 error, 2 stale figures.
```

---

## Important Notes

- **Do not modify scripts unless explicitly asked.** This skill is diagnostic. It runs scripts as-is and reports problems. If the user asks for fixes, apply them in a separate step.
- **Handle missing tools gracefully.** If `pdfinfo` is not installed, fall back to PDF header checks. If `PIL` is not available, skip image-level quality checks and note it in the report.
- **Always use `MPLBACKEND=Agg`** to prevent display-related crashes on headless systems or SSH sessions.
- **Respect script arguments.** If a script requires command-line arguments or config files, check for `argparse` usage and read defaults from `pipeline-state.json` or the script's own defaults.
- **For very large projects** (20+ scripts), run scripts in parallel batches where dependencies allow, but always respect the dependency order.
- **If no scripts/ directory exists**, scan the entire project for Python files that generate figures. Adapt the search paths accordingly.
- **If no .tex files exist**, skip the manuscript cross-reference step and note it in the report.
