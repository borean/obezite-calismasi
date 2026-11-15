---
name: clinical-algorithm-figures
description: "Generate publication-quality clinical algorithm flowcharts as PDF using Python graphviz. Two modes: 'journal' (grayscale, Helvetica, ready for LaTeX) and 'web' (colorful, modern). Use whenever the user needs a diagnostic algorithm, treatment flowchart, clinical pathway diagram, or decision tree figure for a manuscript or presentation."
allowed-tools: [Read, Write, Edit, Bash, Glob, Grep]
license: MIT License
metadata:
    skill-author: Bora
---

# Clinical Algorithm Figures

Generate publication-quality clinical diagnostic and treatment algorithm flowcharts as vector PDF files using Python's `graphviz` library.

## When to Use

- Converting hand-drawn or slide-based clinical algorithms into structured figures
- Creating diagnostic workup flowcharts for journal manuscripts or textbook chapters
- Building treatment decision trees for clinical guidelines
- Generating algorithm figures for presentations, websites, or educational materials

## Design System

The design has three independent layers that can be mixed and matched:

1. **Mode** — controls structure (corners, edges, font, caption, spacing)
2. **Palette** — controls colors (swappable independently of mode)
3. **Hierarchy** — maps node roles to palette slots (shared across all combinations)

### Modes

| Mode | Use case | Corners | Edges | Font | Caption |
|------|----------|---------|-------|------|---------|
| `journal` | Manuscript, LaTeX, textbook, journal | Sharp 90° | Orthogonal | Helvetica | Yes (bottom, with abbreviations) |
| `web` | Slides, website, educational handouts | Rounded | Straight | Helvetica Neue | No |

### Palettes

Any palette works with any mode. Built-in options:

| Palette | Description |
|---------|-------------|
| `blue` | Default. White + gray + muted accent blue (#4472C4). Best for journal. |
| `blue-gradient` | 9-stop navy-to-ice gradient. Best for web. |
| `teal` | Cool teal/cyan. |
| `slate` | Neutral warm gray. Highly formal. |
| `burgundy` | Warm red-brown. Distinguished textbook feel. |
| `forest` | Dark green. Surgical/oncology contexts. |
| `grayscale` | Pure B&W for print. |
| `custom` | Derive from user's accent color — see design-spec.md for the derivation formula. |

See [references/design-spec.md](references/design-spec.md) for exact hex values and the palette slot system.

## Workflow

1. **Understand the algorithm** — Read the source material (image, text description, or existing diagram). Identify every node, branch, and terminal diagnosis.
2. **Ask the user for mode + palette** — e.g. `journal` + `blue`, or `web` + `teal` (if not already specified). Default: `journal` + `blue`.
3. **Ask for figure number and caption** — e.g. "Figure 1. Evaluation of micropenis." or "Şekil 1. Mikropenis değerlendirme algoritması." (journal mode only). Use the same language as the user's content — do NOT assume Turkish or any other language.
4. **Generate the Python script** — Using the design spec for the chosen mode + palette. One script per figure.
5. **Run the script** — Ensure `graphviz` system package and Python package are available. Use a venv if needed.
6. **Open the PDF** — Use `open` (macOS) or `xdg-open` (Linux) so the user can inspect.
7. **Iterate** — Ask if adjustments are needed (including palette changes).

## Prerequisites

```bash
# System package
brew install graphviz        # macOS
sudo apt install graphviz    # Debian/Ubuntu

# Python package (in venv)
pip install graphviz
```

## Script Structure

Every generated script must follow this template:

```python
#!/usr/bin/env python3
"""<Figure title and description>"""

import graphviz

def create_algorithm():
    g = graphviz.Digraph(
        '<name>',
        format='pdf',
        engine='dot',
        graph_attr={...},   # From design spec
        node_attr={...},    # From design spec
        edge_attr={...},    # From design spec
    )

    # Define palette from design spec
    # Build nodes by hierarchy level (title → workup → branch → lab → diagnosis)
    # Build edges

    return g

if __name__ == '__main__':
    g = create_algorithm()
    output = g.render('<output_path>', cleanup=True)
    print(f'Generated: {output}')
```

## Node Hierarchy

Every clinical algorithm has a visual hierarchy. Map each element to the correct level:

| Level | Role | Examples |
|-------|------|---------|
| **L1 — Title** | Algorithm name | "PRİMER AMENORE", "GONAD PALPABL" |
| **L2 — Workup** | Initial tests / evaluation steps | "Anamnez + FM \| USG \| β-hCG, TSH, PRL, FSH" |
| **L3 — Branch** | Major decision forks | "UTERUS VAR", "SRY (+)", "Müllerian yapılar YOK" |
| **L4 — Lab / Finding** | Lab values, imaging findings | "FSH > 20", "T ↓ AMH ↓", "17-OH Progesteron" |
| **L5 — Result** | Intermediate results | "46,XX", "45,X", "Yüksek", "Normal" |
| **L6 — Diagnosis** | Terminal diagnoses / differentials | "Turner sendromu", "KAH", "Gonadal disgenezi" |
| **L0 — Criteria** | Definition / inclusion criteria (optional, dashed border) | Diagnostic criteria box |

## Key Rules

- **Sharp 90° corners** (`shape='box'`) in journal mode. Rounded corners (`style='filled,rounded'`) in web mode.
- **Orthogonal edges** (`splines='ortho'`) in journal mode. Straight lines (`splines='line'`) in web mode.
- **Figure caption** always at bottom (`labelloc='b'`) in journal mode, with abbreviation legend.
- **Bullet character** — use `▪` for lists inside diagnosis nodes (not `•` or `-`).
- **Separator character** — use `|` between items in workup nodes (e.g., "USG | Karyotip | 17-OHP").
- **`cleanup=True`** — always pass to `.render()` to remove intermediate `.gv` source file.
- **One script per figure** — do not combine multiple algorithms into one script.
- **Language** — use the same language as the user's content. Do not assume Turkish or any other language. Preserve all special characters exactly (Turkish İıŞşÇçÖöÜüĞğ, German äöüß, French àéè, etc.).

## Ecosystem Integration

### Figure Pipeline Connection
This skill generates PDF figures that should integrate with the broader figure pipeline:

| Integration Point | Details |
|------------------|---------|
| `figure-pipeline` | After generating algorithm PDFs, invoke figure-pipeline to validate: DPI compliance, file integrity, manuscript cross-references (\includegraphics match) |
| `manuscript-linter` | Algorithm figure captions in LaTeX manuscripts are checked for AI slop and quality |
| `manuscript-from-clinical-data` | Algorithm figures typically appear in Phase 6 (Manuscript Draft) — Figure 4 slot (diagnostic cascade) |
| `data-integrity-check` | If the algorithm references patient counts or statistics, validates they match the data |

### Convention Alignment
- **Format:** PDF (vector) — matches figure-pipeline default
- **DPI:** 300 via Graphviz dot engine — matches pipeline requirement
- **Output directory:** Place in project's `figures/` directory for figure-pipeline discovery
- **Naming:** Use `fig{NN}_algorithm_{name}.pdf` pattern for manuscript cross-referencing

## References

- [Design Specification](references/design-spec.md) — Full color palettes, font sizes, spacing, and node styling for both modes
- [Examples](references/examples.md) — Complete worked examples of journal and web mode scripts
