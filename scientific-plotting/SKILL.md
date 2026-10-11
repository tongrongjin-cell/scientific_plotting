---
name: scientific-plotting
description: 'Scientific figure production discipline for research-grade charts with Python/Matplotlib. Use when (1) creating figures for papers, reports, or mobile reading, (2) reproducing or refactoring a figure from a reference script or book, (3) exporting figures as a PNG + editable-SVG pair, (4) checking figure readability (font size, occlusion, color accessibility, grayscale robustness, mobile-width legibility), or (5) deciding honest captioning of experimental vs computed vs synthetic data. Trigger phrases: "科研绘图", "科研作图", "论文配图", "复现这张图", "复现书里的图", "出版级图", "导出清晰PNG", "可编辑SVG", "投稿图片检查", "matplotlib绘图", "scientific figure", "publication-ready plot", "reproduce figure", "export SVG".'
name_cn: 科研绘图可视化
description_cn: 面向论文、报告与移动端阅读的科研绘图：根据数据或公式描述自动推断图族，采用色觉安全的冗余编码，一键导出 300dpi PNG 与可编辑 SVG，并自动完成文字可编辑性、分辨率与灰度可辨性核验。
create_source: super-agent-skill-creator
license: Complete terms in LICENSE.txt
metadata:
  version: 1.1.0
---
# Scientific Plotting

Produce research-grade figures that survive grayscale printing, mobile-width reading, and journal reformatting. The skill constrains three things: visual encoding, dual-format export, and post-export checks.

## Time Budget

**Target: 1 model round for the happy path — script runs AND delivery happens in the same response.**

Measured pipeline: import 0.54s + plot 0.02s + export 0.13s + verify 0.11s ≈ **0.8s total script time** — the only real cost is model reasoning, so the budget optimizes rounds, not code speed:
- **Do everything in one response**: infer data source and chart family, pick encoding from the Quick Reference, write the complete script, run it, and deliver — all in a single response.
- **After the script returns `ok: true`, deliver in the SAME response** by reading the printed `deliver` dict — do not spend another round reformatting it. Only a failed run (`ok: false`) uses a second round for the fix.
- **Never stop to think between sub-steps.** The Quick Reference has everything needed; go straight to code.
- **Do not read reference files** unless the Quick Reference is insufficient for an unusual chart type.
- **Do not run `--selftest`** unless on a new machine or after upgrade.

## Scope

**In scope**: data-driven scientific charts rendered with Python/Matplotlib — curves, scatter with distributions, function plots, statistical and polar charts, 2D fields (heatmap/contour).

**Out of scope**: flowcharts/mindmaps/architecture diagrams — use other skills for those.

## Golden Rules

These seven rules run through the entire workflow. All are enforced in the single Execute step below.

| # | Rule |
|---|------|
| 1 | **Classify before pixels** — state data source (experimental / computed / synthetic) in the caption. |
| 2 | **Never reconstruct data from a screenshot** — if only a screenshot is available, state values are approximations. |
| 3 | **Color must not carry all the discrimination** — every categorical distinction needs redundant encoding (color + linestyle or marker). |
| 4 | **Caption honestly** — classify data as computed/synthetic/experimental; never add unrequested statistical conclusions. |
| 5 | **Export in pairs** — PNG + editable SVG, produced by `export_and_verify()`. |
| 6 | **Stay portable** — no external LaTeX (use mathtext); fix every random seed; code runs on an ordinary machine. |
| 7 | **Check after export, not on screen** — `export_and_verify()` runs all checks in-process; trust its `ok` field. |

## Quick Reference

Inline critical style rules — use these directly without reading the references file. Read [references/style-rules.md](references/style-rules.md) only for edge cases or detailed failure-mode tables.

### Chart inference — from the user's words to the chart family

The plot block is NOT one fixed template: infer the family from what the user actually describes. Do it inline in the same response — it is a table lookup, not a pause:

1. **Extract variables**: how many, and each one continuous / categorical / directional / a formula.
2. **Extract the message**: trend · relationship · comparison (± uncertainty) · distribution · composition · direction · 2D field.
3. **Look up the table** — take the chart family, its geometry, and its mandatory design.

| Typical user signals | Variables | Message | Chart family + mandatory design |
|---|---|---|---|
| “随x变化 / 趋势 / 曲线 / 演化”, "trend, over time" | 1 continuous x + 1–N series | trend | **Line** — never smooth unless stated; color + linestyle redundancy |
| “关系 / 相关 / 每点一个样本”, "relationship" | 2 continuous (± groups) | relationship | **Scatter** + marginal rugs |
| “函数 / 方程 / f(x)=”, "plot f(x)" | formula | math result | **Function plot** — SciPy direct; annotate zeros/extrema |
| “对比 / 各组 / 谁更高”, "compare groups" | 1 categorical + value | comparison | **Bar** — zero baseline mandatory |
| “均值±误差 / 标准差”, "mean ± std" | categorical + value + error | comparison + uncertainty | **Bar or point + errorbar** — `yerr=`, `capsize≥3` |
| “分布 / 直方 / 箱线", "distribution" | 1 variable (± groups) | distribution | **Histogram / box / violin** — state N in caption |
| “占比 / 构成 / 比例", "composition" | parts of a whole | composition | **Stacked area/bar** — redundant patterning; grayscale risk |
| “方向 / 角度 / 风向 / 周期计数", "directional" | angular counts | direction | **Polar histogram** — 0° N, clockwise; thin ticks; state bin width |
| “矩阵 / 网格 / 二维场 / 空间分布", "2D field" | 2 continuous + 1 value | field | **Heatmap / contourf** — `viridis`/`cividis`; labeled colorbar; `aspect='equal'` for physical space |
| “两个量都画 / 双轴", "dual axis" | 2 y vs same x | — | Only when the scale relation IS the point; otherwise two panels |
| “既想A也想B / 同时看 / 顺便再画", "also, and then" | 2+ intents in one request | multi-intent | **Panels (`plt.subplots(1, 2)`)** — one family per panel; each panel obeys its own mandatory design |

Geometry follows the family: line/scatter/bar/hist → wide 7.5 × 4.5 in; polar/heatmap → square-ish (≈ 5.5 × 5.5); bar width ∝ category count. Multi-panel: 1×2 keeps ~7.5 in total width; per-panel fonts stay at the minimums below — if ticks no longer fit, split into two figures instead of shrinking fonts.

Families not in the table (radar, sankey, waterfall, 3D): name the closest in-scope family at delivery or decline — never silently force-fit them into a bar/line shell.

Worked inferences (description → verdict):
- “三种合金在5个温度下的抗拉强度，给均值和标准差” → temperature (x) × alloy (groups) × mean±std → grouped **bar + errorbar**, zero baseline.
- “风速按16个方位的频数” → angular counts → **polar histogram**, 22.5° bins, 0° N.
- “势能随x、y变化的场” → 2 continuous + 1 value → **heatmap/contourf + labeled colorbar**.
- “男女两组的身高体重数据” → 2 continuous + group → **scatter + rugs** (not two histograms).
- “对比三组抗拉强度，也想看每组的分散程度” → comparison + distribution → 1×2 **panels**: bar+errorbar (left) + boxplot (right), shared group axis.
- “6个传感器随时间的变化” → 6 series > 4–6 cap → two panels (3 series each) or small multiples, not one crowded line chart.

If two families could tell different stories for the same numbers (e.g. line vs bar), pick the one matching the stated message and say so at delivery; ask the user only when both are defensible and the numbers' meaning depends on the choice.

### Encoding limits

- Hard cap: **3 visual variables per panel** (e.g., color = group, marker = group duplicate, size = age).
- Categorical distinctions: encode at least twice — color + linestyle (curves) or color + marker shape (scatter).
- Continuous variable → size: scale areas, not radii (`s = k * value`).
- Line styles: solid, dashed, dotted, dash-dot; keep ≥ 4 distinguishable; ≥ 1.5 pt for mobile.
- A 4th variable → second panel, never a 4th aesthetic on the same panel.
- Series crowding: >4–6 curves on one panel → split into panels / small multiples; do not lean on the palette alone.

### Palettes

- Colorblind-safe: Okabe-Ito, Matplotlib `tab10` subsets, `viridis`/`cividis` for continuous. Never `jet`/`rainbow`.
- Background: white (`#FFFFFF`) by default; transparent only when user asks and target background is known.

### Font sizes (for 7.5 × 4.5 in mobile-oriented figure)

| Element | Minimum (pt) |
|---|---|
| Title | 13 |
| Axis labels | 11 |
| Tick labels | 9 |
| Legend | 9 |
| Annotations | 9 |
| Line width | 1.5 |
| Marker size | 5 |

Scale up when the figure is physically larger in print.

## Workflow

### Step 1 — Execute (write script + run + deliver in ONE response)

**Goal**: infer data source, choose encoding, write the complete plotting script, and run it — all in a single response. Do NOT pause between thinking and coding.

**1a. Infer data source** (from context, do NOT ask the user) — classify as computed / synthetic / experimental for the caption:
- User gives a formula or says "compute/计算" → **computed**.
- User says "demo/演示/synthetic/模拟" or provides no data source → **synthetic**; fix a seed.
- User provides measured data or says "experimental/实验/测量" → **experimental**.
- Only ask when genuinely ambiguous about which numbers must not change. Do not guess numbers.

**1b. Infer the chart from the description** (Chart inference table above, do NOT read reference files):
- Extract variables → message → table lookup; take the family, figure geometry, and mandatory design.
- Apply encoding limits: ≤ 3 visual variables, categorical distinctions encoded twice.
- Pick a colorblind-safe palette.
- Task matching an exemplar pattern (A–D)? Mirror its spec; read references/exemplars.md only for the exact data spec.

**1c. Write the script** — fill in the template below, write to a `.py` file in the working directory, and run it with a single `python` call:

```python
import sys, json
sys.dont_write_bytecode = True; sys.path.insert(0, r"<skill-dir>/scripts")  # avoid __pycache__/*.pyc
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from export_figure import export_and_verify  # one-call: export + verify in-process

# --- PLOT: infer the family (Chart inference table), then write ONE block ---
np.random.seed(42)  # fix seed for synthetic/computed
fig, ax = plt.subplots(figsize=(7.5, 4.5))  # square families (polar/heatmap): (5.5, 5.5)
# line:     ax.plot(x, y, "-", lw=2, label="...")                # color + linestyle redundancy
# bar:      ax.bar(labels, means, yerr=stds, capsize=4)          # zero baseline mandatory
# scatter:  ax.scatter(x, y, c=..., marker=..., s=...)           # + marginal rugs on both axes
# hist/box: ax.hist(v, bins=30) / ax.boxplot([a, b], patch_artist=True)
# polar:    ax = fig.add_subplot(projection="polar"); ax.set_theta_zero_location("N"); ax.set_theta_direction(-1)
# heatmap:  im = ax.imshow(Z, cmap="viridis", origin="lower"); fig.colorbar(im, ax=ax, label="z (unit)")
# function: x = np.linspace(a, b, 1200); ax.plot(x, f(x))        # SciPy for special functions
ax.set_xlabel("x (rad)"); ax.set_ylabel("amplitude")  # quantity + unit on every axis, every family
ax.legend(fontsize=9)  # ≥ 9pt — the two lines above are the line-family example; adapt per family
# --- END PLOT ---

# data_source: computed | synthetic | experimental — state in caption (Rule 1 & 4)
result = export_and_verify(fig, name="<name>", out_dir="figures",
                           overwrite=True)  # True = task-owned dir, safe to re-run after a fix
plt.close(fig)
print(json.dumps({
    "deliver": {"ok": result["ok"], "files": result["export"]["files"],
                 "data_source": "<computed|synthetic|experimental>", "seed": 42},
    "tech": {"svg_text_elements": result["export"]["svg"]["text_elements"],
              "png_dpi": result["verify"]["checks"]["png_inspect"]["dpi"]},
    "human_checks": ["mobile width ~8 cm readable", "legend/annotation occlusion",
                     "grayscale separable (.gray.png)", "zero baseline (bar/area only)"],
}, ensure_ascii=False, indent=2))
```

**What `export_and_verify` does**: enforces `svg.fonttype = 'none'` (editable text), 300-dpi PNG, writes `<name>.png` + `.svg`, then in-process runs SVG text check + PNG dpi/pHYs inspection + grayscale preview (`<name>.gray.png`) + pHYs repair-if-needed. Returns `{"export": report, "verify": report, "ok": bool}`.

**If `ok: false`**: fix the plot and re-run the same script in the next response — this is the only path that uses a second round. Common fixes: SVG text not editable → ensure no `svg.fonttype='path'`; dpi null → already auto-repaired, but if still null check antivirus/sync interference.

**Prerequisites**: Python 3.8+ with Matplotlib; all local. On a new machine only, run `python export_figure.py --selftest` once first.

**Multi-figure tasks**: write one script with a loop, calling `export_and_verify` per figure with distinct names.

**Standalone CLI** (ad-hoc checks on existing files; not needed in normal workflow):

```powershell
python export_figure.py --verify-all  figures/<name>          # batch all 4 checks
python export_figure.py --check-svg  figures/<name>.svg       # single check
python export_figure.py --inspect   figures/<name>.png
python export_figure.py --grayscale  figures/<name>.png
python export_figure.py --ensure-phys figures/<name>.png --phys-dpi 300
python export_figure.py --selftest                           # new machine only
```

### Step 2 — Deliver (in the SAME response as the script result)

**Goal**: report results immediately after the script succeeds — no extra round.

The printed `deliver` dict already contains the file paths, data-source class, seed, and `ok`. Report them directly, append the honest caption (Rule 1 & 4), and remind the user of the four `human_checks` (they need human eyes, not you):
- **Mobile width**: shrink PNG to ~8 cm; labels, ticks, legend still readable?
- **Occlusion**: legend/annotations cover data?
- **Grayscale**: open `<name>.gray.png`; every series separable by linestyle/marker?
- **Zero baseline** (bar/area only): does the axis start at zero?

One caveat to state explicitly:
- **Journal compliance**: automated export passing ≠ journal format compliance — final submission still needs the target journal's current figure requirements.

## References

| File | Read when |
|------|-----------|
| [references/style-rules.md](references/style-rules.md) | Edge cases: unusual chart types, detailed failure-mode tables, deep styling questions beyond the Quick Reference in SKILL.md |
| [references/exemplars.md](references/exemplars.md) | Task matches one of four patterns (multi-frequency curves, scatter with marginals, Bessel functions, polar histogram), reproducing Rougier's book figures, or you need an exact worked data spec |
