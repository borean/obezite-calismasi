# Design Specification

The design system has three independent layers:

1. **Mode** — controls structure (corners, edges, font, caption, spacing)
2. **Palette** — controls colors (swappable independently of mode)
3. **Hierarchy** — maps node roles to palette slots (shared across all combinations)

Any mode can be combined with any palette.

---

## Modes

### `journal`

For manuscripts, textbook chapters, LaTeX documents, journal submissions.

```python
graph_attr = {
    'rankdir': 'TB',
    'splines': 'ortho',      # Right-angle edges only
    'nodesep': '0.60',       # Wide enough for ortho bends to route cleanly
    'ranksep': '0.40',
    'bgcolor': 'white',
    'fontname': 'Helvetica',
    'pad': '0.4',
    'dpi': '300',
    'margin': '0.15',
    'labelloc': 'b',         # Figure caption at bottom
    'labeljust': 'l',
    'label': '<figure_caption>',
    'fontsize': '10',
    'fontcolor': '#333333',
}
node_attr = {
    'fontname': 'Helvetica',
    'fontsize': '11',
    'style': 'filled',       # Sharp 90° corners
    'shape': 'box',
    'penwidth': '0.8',
    'color': '#333333',
    'margin': '0.14,0.07',
}
edge_attr = {
    'fontname': 'Helvetica',
    'fontsize': '9',
    'color': '#333333',
    'penwidth': '0.8',
    'arrowsize': '0.6',
}
```

Figure caption format (use the user's language — do NOT assume Turkish):
```
\n{Figure label} {N}.  {Title}.\n{ABBR}: {expansion}; ...
```
Examples: "Figure 1.", "Şekil 1.", "Abbildung 1.", "Figura 1."

### `web`

For slides, websites, educational handouts, patient materials.

```python
graph_attr = {
    'rankdir': 'TB',
    'splines': 'line',       # Straight lines
    'nodesep': '0.35',
    'ranksep': '0.50',
    'bgcolor': 'white',
    'fontname': 'Helvetica Neue',
    'pad': '0.3',
    'dpi': '300',
    'margin': '0.2',
}
node_attr = {
    'fontname': 'Helvetica Neue',
    'fontsize': '13',
    'style': 'filled,rounded',  # Rounded corners
    'shape': 'box',
    'penwidth': '0.6',
    'margin': '0.18,0.10',
}
edge_attr = {
    'fontname': 'Helvetica Neue',
    'fontsize': '10',
    'color': '<EDGE from palette>',
    'penwidth': '1.0',
    'arrowsize': '0.7',
}
```

No figure caption in web mode.

### Mode Comparison

| Property | `journal` | `web` |
|----------|-----------|-------|
| Corners | Sharp 90° | Rounded |
| Edges | Orthogonal | Straight |
| Font | Helvetica | Helvetica Neue |
| Title fontsize | 14pt | 17pt |
| Body fontsize | 10–11pt | 12–13pt |
| Caption | Yes (bottom) | No |
| Criteria border | Dashed | Dashed + rounded |

---

## Palettes

Each palette defines **8 semantic color slots** that map to the hierarchy levels. The slot names are fixed — only the hex values change.

### Slot Definitions

| Slot | Role |
|------|------|
| `TITLE` | L1 title fill (darkest, white text) |
| `BRANCH` | L3 branch headers (dark, white text) |
| `WORKUP` | L2 workup / L4 lab nodes (medium fill) |
| `LIGHT` | L5 result / finding nodes (light fill) |
| `SURFACE` | L6 diagnosis nodes / L0 criteria (lightest fill) |
| `EDGE` | Edge color, border color |
| `TEXT_ON_DARK` | Text on TITLE/BRANCH fills |
| `TEXT_ON_LIGHT` | Primary text on LIGHT/SURFACE fills |

### Built-in Palettes

#### `blue` (default)

The standard academic monochrome blue. Works with both modes.

```python
TITLE         = '#4472C4'
BRANCH        = '#4472C4'
WORKUP        = '#D6E4F0'
LIGHT         = 'white'
SURFACE       = '#F2F2F2'
EDGE          = '#333333'
TEXT_ON_DARK  = 'white'
TEXT_ON_LIGHT = '#1A1A1A'
```

#### `blue-gradient`

9-stop blue gradient, best with `web` mode.

```python
TITLE         = '#1B2A4A'
BRANCH        = '#5A82B4'
WORKUP        = '#D6E8F4'
LIGHT         = '#D6E8F4'
SURFACE       = '#EAF2F8'
EDGE          = '#6B7B8D'
TEXT_ON_DARK  = 'white'
TEXT_ON_LIGHT = '#1B2A4A'
# Additional gradient stops for fine-grained control:
# B1='#1B2A4A' B2='#2C4A7C' B3='#3D6098' B4='#5A82B4'
# B5='#8AACC8' B6='#B8D4E8' B7='#D6E8F4' B8='#EAF2F8' B9='#F4F8FC'
```

#### `teal`

Cool teal/cyan academic palette.

```python
TITLE         = '#00695C'
BRANCH        = '#00897B'
WORKUP        = '#B2DFDB'
LIGHT         = 'white'
SURFACE       = '#E0F2F1'
EDGE          = '#37474F'
TEXT_ON_DARK  = 'white'
TEXT_ON_LIGHT = '#1A1A1A'
```

#### `slate`

Neutral gray with warm undertone. Highly formal.

```python
TITLE         = '#37474F'
BRANCH        = '#546E7A'
WORKUP        = '#CFD8DC'
LIGHT         = 'white'
SURFACE       = '#ECEFF1'
EDGE          = '#455A64'
TEXT_ON_DARK  = 'white'
TEXT_ON_LIGHT = '#1A1A1A'
```

#### `burgundy`

Warm red-brown palette, distinguished textbook feel.

```python
TITLE         = '#6D2B3E'
BRANCH        = '#8B3A4A'
WORKUP        = '#F0D4DC'
LIGHT         = 'white'
SURFACE       = '#F8ECF0'
EDGE          = '#5D4037'
TEXT_ON_DARK  = 'white'
TEXT_ON_LIGHT = '#3E2723'
```

#### `forest`

Dark green, suitable for surgical/oncology contexts.

```python
TITLE         = '#2E4A3E'
BRANCH        = '#3E6B5A'
WORKUP        = '#C8E6C9'
LIGHT         = 'white'
SURFACE       = '#E8F5E9'
EDGE          = '#3E4A42'
TEXT_ON_DARK  = 'white'
TEXT_ON_LIGHT = '#1B5E20'
```

#### `grayscale`

Pure grayscale for black-and-white printing.

```python
TITLE         = '#333333'
BRANCH        = '#555555'
WORKUP        = '#D9D9D9'
LIGHT         = 'white'
SURFACE       = '#F0F0F0'
EDGE          = '#444444'
TEXT_ON_DARK  = 'white'
TEXT_ON_LIGHT = '#1A1A1A'
```

#### `custom`

When the user requests a specific color or theme, build a palette following this structure. Take the user's accent color and derive:
- `TITLE` / `BRANCH`: the accent at full or near-full saturation
- `WORKUP`: 20–30% tint of the accent
- `LIGHT`: white or 5% tint
- `SURFACE`: 10–15% tint
- `EDGE`: desaturated dark version of the accent
- `TEXT_ON_DARK`: white
- `TEXT_ON_LIGHT`: darkened accent or near-black

---

## Hierarchy → Palette Mapping

This table maps each node level to palette slots. It is the same regardless of mode or palette choice. Font sizes differ between journal and web (shown as journal / web).

| Level | Fill | Font Color | Font Size | Font Weight | penwidth | Border |
|-------|------|-----------|-----------|-------------|----------|--------|
| **L1 Title** | `TITLE` | `TEXT_ON_DARK` | 14 / 17 | Bold | 0 | none |
| **L0 Criteria** | `LIGHT` | `TEXT_ON_LIGHT` | 10 / 11 | Regular | 0.8 | `EDGE` (dashed) |
| **L2 Workup** | `WORKUP` | `TEXT_ON_LIGHT` | 11 / 14 | Regular | 0.8 | `EDGE` |
| **L3 Branch** | `BRANCH` | `TEXT_ON_DARK` | 12 / 13 | Bold | 0 | none |
| **L4 Lab/Finding** | `WORKUP` | `TEXT_ON_LIGHT` | 11 / 13 | Regular | 0.8 | `EDGE` |
| **L5 Result** | `LIGHT` | `TEXT_ON_LIGHT` | 12 / 14 | Bold | 0.8 | `EDGE` |
| **L6 Diagnosis** | `SURFACE` | `TEXT_ON_LIGHT` | 10 / 12 | Regular | 0.8 | `EDGE` |

### Special Edges

| Edge | Style | Color |
|------|-------|-------|
| Title → Criteria | dashed, no arrowhead | lighter than `EDGE` (use 60% opacity or `#999999`) |
| All others | solid | `EDGE` |

---

## Common Rules (Both Modes, All Palettes)

### Text Conventions

- **Bullet**: `▪` (small black square) for lists in diagnosis nodes
- **Separator**: `|` with spaces for workup items: `"USG  |  Karyotip  |  17-OHP"`
- **Dot separator**: `·` for compact inline lists: `"21-OHE  ·  11β-OHE"`
- **Arrows in labels**: Unicode `↑` `↓` for lab values
- **Language**: Match the user's language. Preserve all special characters exactly (any script/language).

### Layout

- `engine='dot'` always
- `format='pdf'` always
- `dpi='300'` always
- `cleanup=True` always on `.render()`

### Ortho Routing Quality (journal mode)

Orthogonal edges should always route cleanly: **horizontal first, then vertical down** (L-shaped).

**Mandatory: Junction Node Technique for every fork.**

For every parent → two-children fork, use invisible `point` nodes at the parent's rank as routing anchors. This is the ONLY reliable way to force clean L-shaped ortho routing. Do NOT rely on `nodesep`, `tailport`/`headport`, or `rank=same` alone — they do not fix the routing direction.

Define a helper function and use it for every fork:

```python
def fork(parent, left, right):
    """Route parent→left and parent→right through invisible junction nodes."""
    jL = f'_jL_{parent}_{left}'
    jR = f'_jR_{parent}_{right}'
    g.node(jL, shape='point', width='0.01', color=EDGE)
    g.node(jR, shape='point', width='0.01', color=EDGE)
    # Junctions at same rank as parent → horizontal edges
    with g.subgraph() as s:
        s.attr(rank='same')
        s.node(jL)
        s.node(parent)
        s.node(jR)
    # Children at same rank → symmetric placement
    with g.subgraph() as s:
        s.attr(rank='same')
        s.node(left)
        s.node(right)
    # Horizontal segments (no arrow)
    g.edge(parent, jL, arrowhead='none')
    g.edge(parent, jR, arrowhead='none')
    # Vertical segments (with arrow)
    g.edge(jL, left)
    g.edge(jR, right)
```

Additional best practices:
- **Equal `width` on sibling nodes** — set the same explicit `width` on both so they occupy symmetric space
- **`nodesep` ≥ `0.60`** — gives enough horizontal channel space for the junction nodes

### Edge Labels

- Avoid when possible — use node labels to convey branching logic
- If necessary: fontsize `9` (journal) / `10` (web)
