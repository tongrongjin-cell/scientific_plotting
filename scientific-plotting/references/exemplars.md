# Exemplars — Four Worked Patterns

Distilled reproduction patterns based on BSD-licensed code from *Scientific Visualization: Python + Matplotlib* by Nicolas P. Rougier (github.com/rougier/scientific-visualization-book). These are re-derived mathematical/composition patterns, not copies of book artwork. Load this file when a task matches one of the patterns below or the user asks to reproduce book figures.

## Table of Contents

1. Pattern A — Multi-frequency damped oscillation curves (`colors/colored-plot.py`)
2. Pattern B — Scatter with marginal distributions (`ornaments/elegant-scatter.py`)
3. Pattern C — Bessel functions with zeros (`ornaments/bessel-functions.py`)
4. Pattern D — Polar direction histogram (`scales-projections/projection-polar-histogram.py`)

---

## Pattern A — Multi-frequency damped oscillation curves

**Use when**: several similar continuous series must stay individually distinguishable (e.g., frequency response, modes, trials).

**Data spec (deterministic, no external dataset)**:
- Time t ∈ [0, 12] s, 900 points.
- Four series: x(t) = exp(-d·t)·sin(ω·t+φ)
  - ω = 0.8, 1.1, 1.4, 1.8 rad/s
  - d = 0.06, 0.075, 0.09, 0.105
  - φ = 0, 0.25, 0.50, 0.75 rad
- Keep all 900 points; no smoothing.

**Encoding**: colorblind-safe color **and** distinct linestyle per series (solid/dashed/dotted/dash-dot). Axis: "Time (s)", "Normalized amplitude".

**Caption template**: "根据确定性公式计算的演示曲线。颜色与线型同时编码频率，没有实验观测或统计推断。" / "Deterministic demo curves computed from x(t)=exp(−d·t)·sin(ω·t+φ). Color and linestyle jointly encode frequency; no experimental observation or statistical inference."

**Do not**: smooth the series, let color alone distinguish curves, or omit units.

---

## Pattern B — Scatter with marginal distributions

**Use when**: two continuous variables per observation, with groups and one auxiliary variable — without overloading the plot.

**Data spec (synthetic, fixed seed)**:
- Seed = 1, 250 rows per group.
- Group A: height ~ N(1.60, 0.10) m, weight ~ N(50, 10) kg.
- Group B: height ~ N(1.75, 0.10) m, weight ~ N(75, 10) kg.
- Age: uniform 25–50, controls marker size only.

**Encoding (exactly 3 variables)**: color + marker shape = group (redundant pair), marker size = age. Marginal rugs: short perpendicular lines along both axes showing distribution position. This is the encoding cap — a fourth variable goes to a second panel.

**Caption template**: "合成数据演示（seed=1）。颜色和点形状表示组别，点大小表示25至50岁的合成年龄，边缘短线展示两个变量的分布位置。" / "Synthetic demo (seed=1). Color and marker encode group; size encodes synthetic age 25–50; marginal rugs show distribution positions."

**Forbidden**: significance, correlation coefficients, population claims — the data is synthetic. Do not add a 4th aesthetic for beauty.

---

## Pattern C — Bessel functions with zeros

**Use when**: mathematical functions computed directly (no dataset), annotated at special points. Closest to pure math plotting.

**Data spec (computed)**:
- x ∈ [0, 20], 1200 points.
- Curves: `scipy.special.jv(n, x)` for n = 0..4 (J0–J4).
- Zeros: `scipy.special.jn_zeros(n, 8)` per order, keep only zeros < 20.

**Portability (critical)**: the original script uses external LaTeX and a specific font — the most common reproduction failure. Replace with Matplotlib `mathtext` (default `text.usetex=False`); never require a LaTeX install. Label each order directly on/near its curve; mark zeros with open circles (hollow markers).

**Caption template**: "SciPy 计算得到的 J0 至 J4 曲线及零点。图形展示数学计算结果，不是实验测量。" / "J0–J4 curves and zeros computed with SciPy. Mathematical results, not measurements."

---

## Pattern D — Polar direction histogram

**Use when**: directional, angular, or periodic counts — wind directions, orientations, cyclic events. Polar charts fail most often from crowded ticks and unclear radius meaning.

**Data spec (synthetic, fixed seed)**:
- Seed = 123. Sectors: 0°–350° in 10° steps, 36 rows.
- Count(θ) = 24 + 15·cos(θ − 0.7) + 7·cos(2θ + 0.4) + integer noise in [−3, 3], floored at 4. Angles in radians in the formula; report the mapping explicitly.

**Layout conventions**: 0° at north (top), angles increase clockwise (`theta_zero_location='N', theta_direction=-1`). Radius = count per 10° sector. Thin out angular tick labels; keep radial gridlines minimal; reduce decorative rings.

**Caption template**: "确定性合成的方向频数演示。半径表示每10度扇区的频数，不代表真实风场或实验样本。" / "Deterministic synthetic direction counts. Radius = count per 10° sector; not real wind or experimental data."

**Switching to real data**: replace the synthetic array with the user's directional observations, and the caption must state bin width, number of observations, and how missing/unrecorded directions were handled. Pretty alone is not a substitute for these.

---

## Common delivery notes for all four patterns

- Every pattern delivers: PNG (300 dpi) + editable SVG via `scripts/export_figure.py`.
- Attribution: when redistributing adapted code, keep the author and source (Rougier, scientific-visualization-book) and note that book text and code have different licenses — verify per file.

> AI生成