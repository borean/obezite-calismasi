---
name: dataviz-principles
description: "Audit and design charts using Tufte's Visual Display of Quantitative Information (9 criteria + 7 remedies) and Knaflic's Storytelling with Data (6 lessons). Use whenever the user asks to review a chart, declutter a figure, choose a chart type, write an active title, or add storytelling to a visualization. Triggers: 'review this chart', 'is this chart honest', 'how should I title this', 'declutter', 'lie factor', 'tufte', 'storytelling with data', 'swd'."
allowed-tools: [Read, Write, Edit, Bash, Grep, Glob]
license: MIT License
metadata:
    skill-author: Bora Ulukapı
    version: "1.0.0"
    sources:
      - "Edward Tufte — The Visual Display of Quantitative Information (Graphics Press, 1983/2001)"
      - "Cole Nussbaumer Knaflic — Storytelling with Data (Wiley, 2015)"
      - "Encoding adapted from gnurio/tufte-vdqi-plugin (MIT)"
---

# Data Visualization Principles — Tufte VDQI + Storytelling with Data

Two complementary frameworks for honest, persuasive charts. Use them as a layered audit:

- **Part I — Tufte (VDQI, 1983)** sets the mechanical floor: data integrity, ink economy, perceptual encoding. *Without it, the chart misleads. Apply first.*
- **Part II — Knaflic (Storytelling with Data, 2015)** sets the rhetorical ceiling: audience, attention, narrative, active titles. *Without it, the chart is honest but mute.*

A chart that fails Part I is wrong. A chart that passes Part I but fails Part II is correct but ineffective.

When you diagnose a chart, name the violation with its code (`T-B1`, `T-B5`, `S-L3.2`, …) so the reader knows exactly what to change.

---

## Part I — Tufte: Visual Display of Quantitative Information

### A. The nine criteria for graphical excellence

Score each 0–10; weight as below. Honesty matters more than elegance.

| # | Criterion | Weight | What a low score looks like | Remedy |
|---|-----------|:------:|-----------------------------|--------|
| T-1 | Integrity | 3× | Truncated axis, distorted areas, missing baseline, cherry-picked range | T-B1 |
| T-2 | Proportionality | 2× | Visual magnitude ≠ data magnitude; 2-D or 3-D area distortion | T-B1 |
| T-3 | Data-ink ratio | 2× | Heavy grids, backgrounds, borders, 3-D, shadows dominate the data marks | T-B5 |
| T-4 | Minimal/redundant ink | 1× | Same datum encoded several ways (height + color + label + border) | T-B6 |
| T-5 | Data density | 1× | One sparse chart where small multiples would pack more comparison | T-B3 |
| T-6 | Integration | 1× | Detached legend, labels far from their marks | T-B4 |
| T-7 | Context | 1× | No baseline, no comparison, no time frame; monetary series left nominal | T-B2, T-B7 |
| T-8 | Clarity | 1× | Ambiguous, congested, or unlabeled; reader cannot tell what they see | T-B4 |
| T-9 | Typography | 0.5× | Decorative or illegible type; labels stranded in a key | T-B4 |

Overall = weighted average. Prioritise: fix integrity and proportionality first, then data-ink, then the rest.

**Common grading mistake**: do not confuse a *design flaw* (ugly but honest) with an *integrity violation* (the graphic misleads). Reserve the lowest integrity scores for graphics that cause the reader to misread the numbers.

### B. The remedies

#### T-B1 — Lie factor

`lie_factor = (% change shown in the graphic) / (% change in the data)`

- Acceptable range **0.95 to 1.05**. Outside it, the graphic distorts.
- Dimensional trap: if a quantity is encoded by an *area*, doubling the data must double the area, not the side length (2× length = 4× area). For *volume*, 2× length = 8× volume. Encoding 1-D quantity with 2-D or 3-D objects is a classic proportionality violation.
- **Bar charts must have a zero baseline** (bar length encodes magnitude from zero). Non-zero bar baselines are an automatic integrity failure.
- **Line charts may use a non-zero range** — they encode change, not magnitude.

#### T-B2 — Range frames

Trim each axis line so it spans exactly the data's min to max; the axis endpoints state those values. Turns dead structural ink into data-carrying ink and stops the data from being squashed into a corner.

- Scatter/line: set axis bounds to the exact data range. **Do not add padding or round outward.**
- Mark min and max at the ends of the axis; interior ticks only if they earn their place.
- **Exception**: bar/column charts keep a zero baseline (T-B1) — do not range-frame the value axis of bars.
- Single point (min == max): keep conventional axes; a range frame needs a range.

#### T-B3 — Small multiples

To compare many series, repeat one small graphic with an **invariant design** so the only thing that changes between frames is the data.

- Identical scales, colors, line weight, markers, and size across every frame. Shared axes are non-negotiable; per-frame auto-scaling destroys comparability.
- Shrink each frame to raise data density; verify legibility at target size.
- Order frames logically: by a meaningful rank (descending total) or by geography/time, never alphabetically by accident.
- Grid sizing: 2–4 frames → 1 row/column; 5–9 → 2–3 rows; 10+ → 3+ rows, consider pagination.
- Label each frame directly (T-B4); do not add a shared legend.

#### T-B4 — Integrate text and graphic

Put labels on the data, not in a remote key, so the eye never darts away and back.

- **Line charts**: label each line at its right-hand endpoint, in the line's color; stagger or use a short leader if endpoints collide.
- **Bar charts**: category names beside/under the bars; a value on a bar only if the exact figure matters and cannot be read from the axis.
- **Scatter**: label notable points/clusters directly; annotate outliers in place.
- **Delete the legend box, its border, and its swatches once labels are direct.**
- Only when direct labeling is truly impossible (very dense scatter) fall back to a compact marginal key, kept as close to the data as possible.

#### T-B5 — Erase non-data-ink

Everything that doesn't carry information goes.

- Gridlines: remove or fade to very-light-gray; never let them compete with the data.
- Chart frames / borders: remove the box around the plot area.
- Backgrounds / fills: white.
- 3-D effects, drop shadows, bevels, gradients: out.
- Tick marks: only on axis labels you actually need; minor ticks rarely earn their place.
- **Decorative color**: if your chart has N categories and you used N colors but color encodes nothing additional, **the color is non-data-ink**. Use one color (or one accent + gray rest).

#### T-B6 — Erase redundant data-ink

A datum encoded once is enough. If a bar's height already says "12," don't also use color, a value label, and a border-thickness all encoding the same thing.

- Pick the strongest single encoding (usually position).
- If you keep redundant labels, drop the axis. If you keep the axis, drop the labels (unless exact values matter).
- **Cleveland dot plots > bars** when values cluster near the floor — bars overemphasize small differences via solid fill.
- **Pie/donut charts are flat-out discouraged** — angular comparison is hard; substitute a bar.

#### T-B7 — Standardize monetary units

For multi-year currency series, deflate to a single base-year value (e.g., 2020 USD). Otherwise rising nominal values can hide real-terms declines.

- Use a published CPI series; never estimate.
- State the base year in the axis label ("Revenue, real 2020 USD").
- Not relevant for: most clinical data, lab values, counts, percentages.

---

## Part II — Knaflic: Storytelling with Data (the six lessons)

Tufte tells you how to encode data honestly. Knaflic tells you how to make the encoded data persuade a specific audience to take a specific action.

### S-L1 — Understand the context

Before drawing anything, answer three questions:

1. **Who is the audience?** Specific person or small group beats "general." A clinician committee reads charts differently than a granting agency.
2. **What do you need them to know or do?** The "action" question is non-negotiable. If you can't name an action, you're decorating, not communicating.
3. **What data supports that?** Filter ruthlessly. Data that doesn't change the action is decoration.

**Tools**:
- **The 3-minute story**: if you had 3 minutes in an elevator, what would you say? Write it out *in prose* before drawing.
- **The Big Idea**: distill the 3-minute story into one sentence stating (a) the unique POV, (b) what's at stake, (c) a complete sentence.
- **Storyboard**: sketch the sequence of slides/charts on paper before opening a tool. Cheap to revise on paper, expensive to revise in code.

### S-L2 — Choose an appropriate visual

Match the chart type to the data and message. Knaflic's preferred forms:

| Use | When |
|---|---|
| **Simple text** | One or two numbers — don't chart them, write them big |
| **Table** | Multiple disparate units of measure, or readers will look up specific values |
| **Heatmap** | Tables where the *pattern* matters more than the values |
| **Line chart** | Continuous data over time |
| **Slopegraph** | Comparing two points in time across many categories |
| **Vertical bar** | A few categories, one metric |
| **Vertical stacked bar** | Parts of a whole, time on x |
| **Horizontal bar** | Long category labels, or many categories |
| **Horizontal stacked bar** | Parts of a whole across categories |
| **Waterfall** | Decomposing a total into contributions |
| **Square area** | Single proportion in context |

**Avoid**:
- **Pie / donut** — angular comparison is hard; bar always wins.
- **3-D anything** — distorts perception, hides data behind data.
- **Secondary y-axis** — readers can't tell which series belongs to which axis; use separate panels or compute a ratio instead.

### S-L3 — Eliminate clutter

Every element on the chart has a cognitive cost. If it doesn't earn its place, remove it.

**S-L3.1 — Cognitive load is real**. The brain has limited working memory; junk on a chart eats it.

**S-L3.2 — Gestalt principles** govern what the eye groups together; use them deliberately:
- **Proximity** — things near each other are read as a group.
- **Similarity** — same color/shape/size → same category.
- **Enclosure** — things in a box are a group.
- **Closure** — the brain completes shapes; you don't need full borders.
- **Continuity** — the eye follows lines and aligned edges.
- **Connection** — connected things are related more strongly than just-proximate ones.

**S-L3.3 — Concrete declutter list** (apply in order):
1. Remove chart border.
2. Remove gridlines, or fade them very light.
3. Remove data markers (dots on lines) unless each datum matters individually.
4. Clean up axis labels: remove `$` on every tick if `$` is in the axis title; remove decimals if data is in millions.
5. Use consistent color for series across charts on the same page.
6. Diagonal text → never. Rotate the chart (vertical bar → horizontal bar) instead.

### S-L4 — Focus your audience's attention

Use **preattentive attributes** — properties the brain processes pre-consciously (in <250 ms), before reading. These are the levers for directing the eye:

- **Color** — by far the strongest. Reserve it for the one element you want seen first.
- **Size** — bigger = more important.
- **Position** — top-left and the center of the page get attention first (Western reading order).
- Plus: orientation, length, width, shape, enclosure, hue, intensity.

**S-L4.1 — Strategic color**:
- Default everything to **gray**. Gray is the "rest" state.
- Use **one accent color** for the element that matters.
- For a comparison ("our group vs. everyone else"), the accent is the comparison subject; everyone else stays gray.
- Two accents max. Three becomes ambiguous.
- Accessibility: design for color-blindness — use orange/blue rather than red/green; never encode information by color *alone* (also encode by position, label, or shape).

**S-L4.2 — Hierarchy of attention** — the reader's eye should follow a deliberate path:
1. Active title (sentence stating the message).
2. The colored element (preattentive draw).
3. Annotation explaining the colored element.
4. Axis labels and supporting data.

If the reader's eye lands anywhere else first, the chart fails this test.

### S-L5 — Think like a designer

Designers obsess over four things, in order:

- **Affordance** — what does the chart invite the reader to do? Labels say "read me;" colors say "look here;" a clear comparison says "notice this."
- **Accessibility** — readable type size, color-blind safe, alt text, descriptive captions; "design as if the reader is tired and skimming."
- **Aesthetics** — alignment, white space, consistent fonts, no diagonal text.
- **Acceptance** — anticipate pushback. Articulate why you made each choice. Show iterations.

### S-L7 — Tell a story

A story has three acts: **setup → conflict → resolution**.

- **Setup** — the situation as it was. Baseline. Status quo.
- **Conflict** — what changed; what's at stake; the tension the audience must resolve.
- **Resolution** — your recommendation; the action you want them to take.

**Active titles** are the headline of each act:
- ❌ "Treatment Modalities" (descriptive — tells the reader *what they're looking at*).
- ✅ "ATD was first-line in 73%; surgery deferred to 45%" (active — tells the reader *what to take away*).

Every chart, every panel, every slide gets an active title. If you can't write one in a single sentence, the chart doesn't have a message yet.

**Build with text**:
- Active title at top.
- Annotation on the chart pointing at the colored element.
- Caption below stating sample size, source, definitions.
- Footnote for caveats.

### S-L8 — Pulling it together — the iteration loop

1. Draft the chart per Tufte (Part I).
2. Write the Big Idea + 3-minute story.
3. Pick the chart type per S-L2.
4. Declutter per S-L3.
5. Apply strategic color + active title per S-L4 + S-L7.
6. Read it again as if you were the audience. Does the eye land where you want it to?

---

## Combined audit checklist (use as a one-pass review)

For any chart, score each of these:

**Tufte (mechanical)**:
- [ ] Lie factor between 0.95 and 1.05 (T-B1)
- [ ] Bar charts have zero baseline (T-B1)
- [ ] Pie / donut / 3-D absent (T-B6)
- [ ] Axis ranges either zero-anchored (bars) or range-framed (line/scatter) (T-B2)
- [ ] Number of distinct colors ≤ number of categorical dimensions encoded (T-B5)
- [ ] Gridlines, chart border, background fill, drop shadows absent or near-invisible (T-B5)
- [ ] Labels on the data, not in a remote legend (T-B4)
- [ ] Multiple series of the same data type shown as small multiples with shared axes (T-B3)
- [ ] Multi-year currency data deflated to a base year (T-B7)

**Storytelling with Data (rhetorical)**:
- [ ] Audience and desired action named (S-L1)
- [ ] Chart type matches Knaflic's table; no pie/donut/3-D/secondary-y (S-L2)
- [ ] Decluttered per the concrete list (S-L3.3)
- [ ] One accent color, rest in gray (S-L4.1)
- [ ] Active title carries the message in one sentence (S-L7)
- [ ] Annotation on the chart points at the accent (S-L7)
- [ ] Reader's eye lands on title → accent → annotation in that order (S-L4.2)
- [ ] Caption states n, source, definitions (S-L7)

Anything unchecked is a finding. Prioritise: Tufte fails first (they're integrity / honesty), then SwD fails (they're effectiveness).

---

## Sources & attribution

- Edward Tufte, *The Visual Display of Quantitative Information* (Graphics Press, 2001 / 1983 1st ed.) — Part A criteria and Part B remedies B1–B7.
- The Part I encoding is adapted from gnurio/tufte-vdqi-plugin (MIT), which distilled Tufte's principles into the criteria-plus-remedies form.
- Cole Nussbaumer Knaflic, *Storytelling with Data* (Wiley, 2015) — six lessons (chapters 1–5 + 7), active titles, preattentive attributes, strategic color.

When citing a violation in an audit, use the code: `T-B1` (Tufte remedy 1), `S-L4.2` (SwD lesson 4.2), etc.
