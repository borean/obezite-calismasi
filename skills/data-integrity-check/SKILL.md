---
name: data-integrity-check
description: "Validates data consistency across the xlsx→py→csv→tex→pdf research pipeline. Checks that manuscript numbers match script outputs, figures are current, cross-references exist, and no stale artifacts remain. Use whenever the user suspects data mismatches, says 'check the numbers', or before manuscript submission to verify nothing is stale or inconsistent."
allowed-tools: [Read, Bash, Grep, Glob, Write, TodoWrite]
license: MIT License
metadata:
    skill-author: Bora Ulukapı
    version: "1.0.0"
---

# Data Integrity Check

Run a full consistency audit of a research data pipeline before committing, submitting, or sharing results. Designed for clinical research projects (OGTT, thyroid studies, etc.) where Excel data flows through Python scripts into CSVs, LaTeX manuscripts, and PDF figures.

## When to Use

- Before every `git commit` on a research project
- After updating any `.xlsx` data file
- After modifying a Python analysis script
- Before manuscript submission or sharing results with collaborators
- Whenever something "feels off" about the numbers

## Procedure

Work through all five checks below sequentially. Use the TodoWrite tool to track progress. Collect all findings into a single report at the end.

### Step 0: Discover the Project

Locate all relevant files in the working directory:

```bash
# Find all pipeline-relevant files
find . -maxdepth 4 \( -name "*.xlsx" -o -name "*.xls" \) -type f | sort
find . -maxdepth 4 -name "*.py" -type f | sort
find . -maxdepth 4 -name "*.csv" -type f | sort
find . -maxdepth 4 -name "*.tex" -type f | sort
find . -maxdepth 4 -name "*.bib" -type f | sort
find . -maxdepth 4 -name "*.pdf" -type f | sort
find . -maxdepth 4 -name "pipeline-state.json" -type f | sort
```

Build an internal map of which scripts read which data files and produce which outputs. Look for clues:
- `pd.read_excel(...)` or `openpyxl.load_workbook(...)` calls in `.py` files to identify data sources
- `to_csv(...)` or `savefig(...)` calls to identify outputs
- `\input{}`, `\includegraphics{}`, `\bibliography{}` in `.tex` files to identify dependencies

Use Grep to trace these relationships:

```bash
# In each .py file, find what it reads and what it writes
grep -n "read_excel\|read_csv\|load_workbook\|open(" *.py
grep -n "to_csv\|savefig\|to_excel\|write" *.py
```

### Step 1: File Freshness Chain

Check modification timestamps along the entire pipeline. A downstream file must never be older than its upstream source.

```bash
# Get modification times for all pipeline files (epoch seconds for comparison, human-readable for reporting)
for f in $(find . -maxdepth 4 \( -name "*.xlsx" -o -name "*.py" -o -name "*.csv" -o -name "*.tex" -o -name "*.pdf" \) -type f); do
    echo "$(stat -f '%m' "$f" 2>/dev/null || stat -c '%Y' "$f" 2>/dev/null) $(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$f" 2>/dev/null || date -r $(stat -c '%Y' "$f" 2>/dev/null) '+%Y-%m-%d %H:%M' 2>/dev/null) $f"
done | sort -k3
```

Check each link in the chain and report violations:

**xlsx -> py**: If any `.xlsx` file is newer than a `.py` script that reads it, the script may be using stale data logic.

**py -> csv**: If any `.py` script is newer than the `.csv` it produces, the CSV was not regenerated after the script changed.

```bash
# For each .py file, find its CSV outputs and compare timestamps
for py_file in $(find . -maxdepth 4 -name "*.py" -type f); do
    csv_outputs=$(grep -oP "to_csv\(['\"]([^'\"]+)['\"]" "$py_file" 2>/dev/null | sed "s/to_csv(['\"]//;s/['\"]//g")
    for csv_file in $csv_outputs; do
        if [ -f "$csv_file" ]; then
            py_time=$(stat -f '%m' "$py_file" 2>/dev/null || stat -c '%Y' "$py_file" 2>/dev/null)
            csv_time=$(stat -f '%m' "$csv_file" 2>/dev/null || stat -c '%Y' "$csv_file" 2>/dev/null)
            if [ "$py_time" -gt "$csv_time" ]; then
                py_date=$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$py_file" 2>/dev/null)
                csv_date=$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$csv_file" 2>/dev/null)
                echo "STALE: $csv_file ($csv_date) is older than $py_file ($py_date)"
            fi
        fi
    done
done
```

**csv -> tex**: If a `.tex` file references data that has changed in the CSV, the manuscript is stale.

**tex -> pdf**: If the `.tex` file is newer than the corresponding `.pdf`, it needs recompilation.

```bash
# Check tex vs pdf freshness
for tex_file in $(find . -maxdepth 4 -name "*.tex" -type f); do
    pdf_file="${tex_file%.tex}.pdf"
    if [ -f "$pdf_file" ]; then
        tex_time=$(stat -f '%m' "$tex_file" 2>/dev/null || stat -c '%Y' "$tex_file" 2>/dev/null)
        pdf_time=$(stat -f '%m' "$pdf_file" 2>/dev/null || stat -c '%Y' "$pdf_file" 2>/dev/null)
        if [ "$tex_time" -gt "$pdf_time" ]; then
            echo "STALE: $pdf_file needs recompilation (tex modified after pdf)"
        fi
    fi
done
```

Also check figure PDFs/PNGs against their generating scripts:

```bash
# Check if figure files are older than the scripts that generate them
for py_file in $(find . -maxdepth 4 -name "*.py" -type f); do
    fig_outputs=$(grep -oP "savefig\(['\"]([^'\"]+)['\"]" "$py_file" 2>/dev/null | sed "s/savefig(['\"]//;s/['\"]//g")
    for fig_file in $fig_outputs; do
        if [ -f "$fig_file" ]; then
            py_time=$(stat -f '%m' "$py_file" 2>/dev/null || stat -c '%Y' "$py_file" 2>/dev/null)
            fig_time=$(stat -f '%m' "$fig_file" 2>/dev/null || stat -c '%Y' "$fig_file" 2>/dev/null)
            if [ "$py_time" -gt "$fig_time" ]; then
                days_diff=$(( (py_time - fig_time) / 86400 ))
                echo "STALE: $fig_file is ${days_diff} days older than $py_file"
            fi
        fi
    done
done
```

Format each violation as:
```
STALE: fig03_bradford.pdf is 3 days older than fig03_bradford.py — needs regeneration
FIX:   cd <dir> && python fig03_bradford.py
```

### Step 2: Number Consistency

Extract all statistical values from the manuscript and verify each one against script outputs.

**Extract numbers from the .tex manuscript:**

Use Grep to find common statistical patterns in `.tex` files:

```
# Sample sizes: n=XX, N=XX, (n=XX)
grep -oP '[nN]\s*=\s*\d+' manuscript.tex

# P-values: p=0.XXX, p<0.XXX, P=0.XXX
grep -oP '[pP]\s*[=<>]\s*0?\.\d+' manuscript.tex

# Percentages: XX%, XX.X%
grep -oP '\d+\.?\d*\s*\\?%' manuscript.tex

# Mean +/- SD patterns: XX.X ± XX.X, XX.X +/- XX.X, XX.X \pm XX.X
grep -oP '\d+\.?\d*\s*(?:\\pm|±|\+/?-)\s*\d+\.?\d*' manuscript.tex

# Confidence intervals: (XX.X-XX.X), (XX.X, XX.X), 95% CI [XX.X-XX.X]
grep -oP '(?:95%?\s*CI\s*)?[\[\(]\s*\d+\.?\d*\s*[-,]\s*\d+\.?\d*\s*[\]\)]' manuscript.tex

# Correlation/test statistics: r=0.XX, R²=0.XX, t=X.XX, F=X.XX, chi²=X.XX
grep -oP '(?:r|R²|t|F|chi2|χ²)\s*=\s*\d+\.?\d*' manuscript.tex
```

**Cross-reference against CSV outputs:**

For each extracted number, search all `.csv` files and any `.log` or `.txt` output files for a match:

```bash
# For a given number, check if it exists in any output file
number="42"  # Replace with each extracted value
grep -r "$number" --include="*.csv" --include="*.log" --include="*.txt" .
```

Use a Python one-liner to do bulk validation:

```python
python3 -c "
import csv, re, sys, glob

# Read all CSV files into a set of values
all_values = set()
for csvf in glob.glob('**/*.csv', recursive=True):
    try:
        with open(csvf) as f:
            reader = csv.reader(f)
            for row in reader:
                for cell in row:
                    cell = cell.strip()
                    if cell:
                        all_values.add(cell)
                        # Also add rounded versions
                        try:
                            v = float(cell)
                            all_values.add(f'{v:.1f}')
                            all_values.add(f'{v:.2f}')
                            all_values.add(f'{v:.3f}')
                            all_values.add(str(int(v)))
                        except ValueError:
                            pass
    except Exception:
        pass

# Read tex file and extract numbers
tex_files = glob.glob('**/*.tex', recursive=True)
for texf in tex_files:
    with open(texf) as f:
        content = f.read()
    # Find all numeric patterns
    numbers = re.findall(r'(?<![a-zA-Z])(\d+\.?\d*)(?![a-zA-Z{])', content)
    for n in numbers:
        if float(n) > 1 or '.' in n:  # Skip trivial numbers like 0, 1
            if n not in all_values:
                # Find the line for context
                for i, line in enumerate(content.split('\n'), 1):
                    if n in line and not line.strip().startswith('%'):
                        print(f'UNVERIFIED: {n} on line {i} of {texf}')
                        print(f'  Context: {line.strip()[:120]}')
                        break
"
```

**Check sample size consistency across manuscript sections:**

```bash
# Extract sample sizes from different sections and compare
python3 -c "
import re
with open('manuscript.tex') as f:
    content = f.read()

# Split by sections
sections = re.split(r'\\\\(?:section|subsection)\{([^}]+)\}', content)
sample_sizes = {}
for i in range(0, len(sections)-1, 2):
    section_name = sections[i+1] if i+1 < len(sections) else 'preamble'
    section_text = sections[i+2] if i+2 < len(sections) else sections[i]
    sizes = re.findall(r'[nN]\s*=\s*(\d+)', section_text)
    if sizes:
        sample_sizes[section_name] = sizes

for section, sizes in sample_sizes.items():
    print(f'{section}: n = {", ".join(sizes)}')

# Check abstract separately
abstract = re.search(r'\\\\begin\{abstract\}(.*?)\\\\end\{abstract\}', content, re.DOTALL)
if abstract:
    abs_sizes = re.findall(r'[nN]\s*=\s*(\d+)', abstract.group(1))
    if abs_sizes:
        print(f'Abstract: n = {\", \".join(abs_sizes)}')
"
```

Flag any discrepancies:
```
MISMATCH: Abstract says n=127 but Methods says n=125
MISMATCH: Table 2 header says n=84 but CSV row count is 82
UNVERIFIED: p=0.023 on line 341 not found in any CSV or log output
```

### Step 3: Cross-Reference Validation

Verify all internal references in the LaTeX manuscript.

**Labels and refs:**

```bash
# Extract all \label{} definitions
grep -oP '\\label\{([^}]+)\}' manuscript.tex | sed 's/\\label{//;s/}//' | sort > /tmp/labels.txt

# Extract all \ref{} and \autoref{} and \cref{} usages
grep -oP '\\(?:auto)?(?:c)?ref\{([^}]+)\}' manuscript.tex | sed 's/\\[a-z]*ref{//;s/}//' | sort > /tmp/refs.txt

# Find refs that have no matching label (broken references)
comm -23 /tmp/refs.txt /tmp/labels.txt

# Find labels that are never referenced (orphaned labels)
comm -23 /tmp/labels.txt /tmp/refs.txt
```

**Citations and bibliography:**

```bash
# Extract all \cite{} keys (handle multi-cite like \cite{a,b,c})
grep -oP '\\cite[tp]?\{([^}]+)\}' manuscript.tex | sed 's/\\cite[tp]\?{//;s/}//' | tr ',' '\n' | sed 's/^ *//;s/ *$//' | sort -u > /tmp/citekeys.txt

# Extract all @type{key, entries from .bib file
grep -oP '@\w+\{([^,]+),' *.bib | sed 's/.*{//;s/,//' | sort -u > /tmp/bibkeys.txt

# Find citations not in bibliography (missing references)
comm -23 /tmp/citekeys.txt /tmp/bibkeys.txt

# Find bib entries never cited (unused references — warning only)
comm -23 /tmp/bibkeys.txt /tmp/citekeys.txt
```

**Figure and table float existence:**

```bash
# Check that every \includegraphics file exists
grep -oP '\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}' manuscript.tex | sed 's/.*{//;s/}//' | while read -r fig; do
    # Try with and without extension
    if [ ! -f "$fig" ] && [ ! -f "${fig}.pdf" ] && [ ! -f "${fig}.png" ] && [ ! -f "${fig}.eps" ]; then
        echo "MISSING FIGURE: $fig referenced in manuscript but file not found"
    fi
done

# Check that every \input{} file exists
grep -oP '\\input\{([^}]+)\}' manuscript.tex | sed 's/.*{//;s/}//' | while read -r inp; do
    if [ ! -f "$inp" ] && [ ! -f "${inp}.tex" ]; then
        echo "MISSING INPUT: $inp referenced in manuscript but file not found"
    fi
done
```

Format each finding:
```
BROKEN REF:    \ref{tab:ogtt_results} — no matching \label found
ORPHAN LABEL:  \label{fig:old_scatter} — defined but never referenced
MISSING CITE:  \cite{Johnson2024} — not in bibliography.bib
MISSING FIG:   figures/fig03_bradford.pdf — referenced but file does not exist
```

### Step 4: Data Source Tracking via pipeline-state.json

If a `pipeline-state.json` exists, use it as the authoritative record of the pipeline.

```bash
# Read and validate pipeline-state.json
python3 -c "
import json, os, sys

try:
    with open('pipeline-state.json') as f:
        state = json.load(f)
except FileNotFoundError:
    print('INFO: No pipeline-state.json found — skipping pipeline state checks')
    sys.exit(0)

issues = []

# Check data_sources exist
for src in state.get('data_sources', []):
    path = src if isinstance(src, str) else src.get('path', '')
    if path and not os.path.exists(path):
        issues.append(f'MISSING SOURCE: {path} listed in pipeline-state.json but not found on disk')

# Check scripts exist
for script in state.get('scripts', []):
    path = script if isinstance(script, str) else script.get('path', '')
    if path and not os.path.exists(path):
        issues.append(f'MISSING SCRIPT: {path} listed in pipeline-state.json but not found on disk')

# Check sample size consistency
pipeline_n = state.get('sample_size') or state.get('n')
if pipeline_n:
    print(f'Pipeline sample size: n={pipeline_n}')
    # This will be cross-checked against manuscript in the report

# Check outputs exist
for out in state.get('outputs', []):
    path = out if isinstance(out, str) else out.get('path', '')
    if path and not os.path.exists(path):
        issues.append(f'MISSING OUTPUT: {path} listed in pipeline-state.json but not found on disk')

if issues:
    for issue in issues:
        print(issue)
else:
    print('OK: All files in pipeline-state.json exist on disk')
"
```

### Step 5: Compile the Report

Aggregate all findings into a traffic-light summary.

**Severity classification:**
- **RED** items: Mismatched numbers in manuscript, broken references, missing files, stale CSVs from modified scripts
- **YELLOW** items: Stale PDFs (just need recompile), orphaned labels, unused bib entries, unverified numbers that might be page numbers or trivial constants
- **GREEN**: Everything checks out

**Report format:**

```
========================================
  DATA INTEGRITY CHECK — 2026-03-12
  Project: <project directory name>
========================================

OVERALL STATUS: RED / YELLOW / GREEN

--- FILE FRESHNESS ---
[RED]    fig03_bradford.pdf is 3 days older than fig03_bradford.py
         FIX: cd figures/ && python fig03_bradford.py
[RED]    results.csv is older than analyze.py
         FIX: python analyze.py
[YELLOW] manuscript.pdf is older than manuscript.tex
         FIX: cd . && pdflatex manuscript.tex && bibtex manuscript && pdflatex manuscript.tex && pdflatex manuscript.tex

--- NUMBER CONSISTENCY ---
[RED]    Abstract says n=127 but Methods section says n=125
[RED]    p=0.023 on line 341 of manuscript.tex not found in any output file
[YELLOW] Value 3.45 on line 89 could not be verified (may be a constant)

--- CROSS-REFERENCES ---
[RED]    \ref{tab:ogtt_results} has no matching \label
[RED]    \cite{Johnson2024} not found in bibliography.bib
[YELLOW] \label{fig:old_scatter} defined but never referenced
[GREEN]  All \includegraphics files exist

--- PIPELINE STATE ---
[RED]    data/raw_ogtt.xlsx listed in pipeline-state.json but not found
[GREEN]  All scripts exist
[GREEN]  Sample size n=125 matches pipeline-state.json

--- SUMMARY ---
RED:    5 issues requiring immediate attention
YELLOW: 3 warnings to review
GREEN:  3 checks passed

========================================
  Fix the RED items before committing.
========================================
```

## Important Notes

- **Adapt file paths**: The commands above use generic names like `manuscript.tex`. Replace with actual file names discovered in Step 0. If there are multiple `.tex` files, check the one that contains `\documentclass` as the main manuscript.
- **Handle multiple classification systems**: In OGTT projects, watch for columns like `classification_v1` vs `classification_v2` or `ADA_criteria` vs `WHO_criteria` in CSVs. Flag if both appear in the same output but the manuscript only references one.
- **Rounding tolerance**: When comparing numbers between CSV and manuscript, allow for rounding. A CSV value of `0.0234` matches a manuscript value of `p=0.023` or `p=0.02`. Flag only when values diverge beyond plausible rounding.
- **Comment lines**: Skip lines beginning with `%` in `.tex` files — those are comments, not live manuscript content.
- **Large projects**: If the project has many CSV files, prioritize those referenced in the `.tex` file or listed in `pipeline-state.json`.
- **No destructive actions**: This skill only reads and reports. It never modifies files. Fix suggestions are printed for the user to execute manually.
