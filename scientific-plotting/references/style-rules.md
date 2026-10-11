# Style Rules — Encoding, Palettes, Captions, Sizes

Detailed rules behind the Golden Rules in SKILL.md. Load this file when choosing chart types/encodings or answering styling questions.

## Table of Contents

1. Chart-type selection
2. Visual encoding limits
3. Palettes and color safety
4. Baseline and axis rules
5. Caption wording
6. Font sizes and mobile legibility
7. Common failure modes

## 1. Chart-type selection

| Data shape | Recommended type | Notes |
|---|---|---|
| One or more series over a continuous variable | Line plot | Curves: never smooth plotted data unless smoothing is the stated transform |
| Two continuous variables, groups optional | Scatter | Add marginal rugs/lines for distribution hints |
| Mathematical functions of one variable | Function plot (line) | Compute with SciPy directly; annotate special points (zeros, extrema) |
| Directional / angular / periodic counts | Polar histogram | 0° at north, clockwise; state bin width |
| Totals per category (few categories) | Bar | Zero baseline mandatory |
| Composition over time (many periods) | Stacked area | Only with redundant patterning; risky in grayscale |
| Distribution comparison | Box/violin or histogram | State sample size in caption |

Avoid dual-axis charts unless the relationship between the two scales is the point; if used, label both axes explicitly and say why.

## 2. Visual encoding limits

- Hard cap: **3 visual variables per panel** (e.g., color = group, marker shape = group duplicate, size = age). A fourth variable demands a second panel or facet, not more encoding.
- Categorical distinctions: encode at least twice — color + linestyle (curves) or color + marker shape (points/scatter).
- Continuous variable → size: scale areas, not radii (`s = k * value`, not `s = k * value**2` misapplied), and keep the mapping linear and stated in the caption.
- Do not encode the same variable twice with two different aesthetics "for beauty" (e.g., color + size for the same age) — it reads as two variables.
- Line styles for discrimination: solid, dashed, dotted, dash-dot; keep ≥ 4 distinguishable; prefer thicker lines (≥ 1.5 pt) for mobile.

## 3. Palettes and color safety

- Use colorblind-safe sets: Okabe-Ito, Matplotlib `tab10` subsets, or `viridis`/`cividis` for continuous maps. Never `jet`/`rainbow`.
- Test: run `python export_figure.py --grayscale <figure>.png` to write a luminance preview beside the figure. Every series must remain separable by its non-color encoding in that preview.
- Background: white (`#FFFFFF`) by default for print and mobile; transparent PNG only when the user asks and the target background is known.
- Contrast: tick labels and axis labels dark gray-to-black on white; never light gray on white for mobile.

## 4. Baseline and axis rules

- Bar and area charts include zero. If a non-zero baseline is requested (e.g., detailed differences), mark it clearly in the caption and axis.
- Every axis label: quantity + unit — "Time (s)", "Normalized amplitude", "Frequency (rad/s)". Units in parentheses, not appended to every tick.
- Ticks: do not overcrowd. For polar charts, thin out angular ticks rather than labeling every bin.
- Limits: start axes at natural data bounds; avoid truncated y-axes on bar charts.
- Marginal distributions (rugs): short perpendicular lines at the axis edges; they do not replace a distribution plot, they hint at it.

## 5. Caption wording

Classify every figure in exactly one of three ways and say so in the caption:

- **experimental** — "Measured …; N = …; acquisition conditions …".
- **computed** — "Computed from … (e.g., SciPy `jv`); mathematical result, not a measurement."
- **synthetic** — "Synthetic demo with fixed seed …; parameters …; does not represent real measurements/populations."

Caption must explain every encoding: "Color and linestyle encode frequency; marker size encodes age (25–50)."

Forbidden in captions for synthetic/computed data: significance levels, p-values, correlation coefficients, "we found", population conclusions, real-world claims (e.g., real wind directions). If the user requests statistics, first check the data can support them.

## 6. Font sizes and mobile legibility

Target: readable when the figure is displayed ~8 cm wide on a phone.

- Default figure size: 7.5 × 4.5 in (16:9.6, ~19:11) for single-panel mobile-oriented figures.
- Font sizes (points): title ≥ 13, axis labels ≥ 11, ticks ≥ 9, legend ≥ 9, annotations ≥ 9. These values assume the 7.5-in width; scale up when the figure is physically larger in print.
- Line width ≥ 1.5, marker size ≥ 5 for scatter.
- Legend: place outside the data area (e.g., `bbox_to_anchor`) or in confirmed-empty space; never over dense data.
- After export, open the PNG at phone width; if any text is below ~9 pt effective, increase and re-export.

## 7. Common failure modes

| Symptom | Cause | Fix |
|---|---|---|
| PNG blurry when zoomed | dpi too low or figure too small | 300 dpi at intended physical size; enlarge fonts |
| SVG text not editable | `svg.fonttype = 'path'` (default in some setups) | `plt.rcParams['svg.fonttype'] = 'none'` (bundled script enforces) |
| Legend covers data | Default legend inside axes | Move outside or use empty corner; verify on export |
| Curves indistinguishable in grayscale | Color-only encoding | Add linestyle/marker redundancy; verify with `--grayscale` preview |
| Script fails on other machines | External LaTeX (`text.usetex`) or custom font family | Use `mathtext`, default font stack |
| Non-reproducible synthetic data | Unfixed RNG | Fix seeds, state in caption |
| Axis unreadable on phone | Fonts sized for a monitor | Apply Section 6 minimums, re-check |
| Overcrowded polar chart | Every bin labeled, dense grid | Thin angular ticks, keep radial gridlines minimal |
| Toolchain output uncertain on a new machine | Unverified environment | Run `export_figure.py --selftest` before plotting |

> AI生成