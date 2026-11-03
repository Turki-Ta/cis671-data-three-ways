## 5.1 The view

[[SHOT:V3a]]

Visualization 3 isolates the exact quantity that the first two visualizations only imply: the net balance of embodied CO2 in international trade, measured in tonnes per person per year from 1990 to 2022 ([[FIG:V3a]]). Arranged as a 2 x 3 grid of small multiples on shared horizontal and vertical scales, each facet plots a country's consumption-minus-production difference directly against a flat zero baseline. Areas above zero are shaded blue to denote net carbon importers, while areas below zero are shaded orange to denote net exporters.

## 5.2 Idiom, marks and channels

Small multiples repeat a single visual encoding across partitioned subsets of the data on shared scales (Heer & Shneiderman, 2012, p. 50; Munzner, 2014), immediately answering Tufte's (1990, p. 67) core comparative question: *"Compared to what?"*

| Element | Encoding |
| :--- | :--- |
| **Item** | One country-year: 33 per facet, 198 in all |
| **Partition** | Country, arranged in the report's fixed order (2 rows x 3 columns) |
| **Mark** | Filled area between zero and the curve, bounded by a 2 px stroke along the series edge |
| **Horizontal position** | Year, 1990 to 2022, shared across all six facets |
| **Vertical position** | Net balance in t CO2 per person, linear, shared across all six facets with a drawn zero baseline |
| **Hue** | Sign of the balance: blue (`#2a78d6`) above zero, orange (`#eb6834`) below zero |
| **Opacity** | Fixed at 0.42 for the area fill so background gridlines remain legible |
| **Text** | Country name and income tier above each facet; direct callouts for 1990, 2022, and the peak year |

Four design choices shape how these channels work together:

**Replacing an unaligned gap judgment with position on a flat baseline.** [[FIG:V3b]] illustrates why plotting the difference directly matters. In the left panel, the United Kingdom's consumption and production series are drawn as two separate downward-sloping curves; judging how the trade gap evolved requires estimating the vertical distance between two moving lines that share no common baseline--a length judgment prone to substantial perceptual error (Cleveland & McGill, 1984, p. 541). In the right panel, subtracting production from consumption places the gap on a flat horizontal zero line, turning the comparison into an immediate positional reading where the tripling of the UK import balance between 1990 (+1.12 t) and 2004 (+3.34 t) is impossible to miss.

[[SHOT:V3b]]

**Redundant sign encoding with diverging hue.** Because zero represents a true structural boundary between importing and exporting carbon, the chart pairs position above or below the baseline with a diverging color scheme: blue (`#2a78d6`) for net imports and orange (`#eb6834`) for net exports, matching the semantic palette used in Visualizations 1 and 2. This redundancy ensures that the sign of the trade balance can be read at a glance, remains legible if printed in greyscale, and stays clearly distinguishable under simulated protanopia and deuteranopia (Machado et al., 2009).

**Enforcing a shared vertical scale across asymmetric economies.** Locking all six facets to a common y-axis lets the reader directly compare Sweden's peak per-capita import balance (+6.61 t) against China's peak per-capita export balance (-1.20 t). The trade-off is that India's per-capita curve (+0.01 t to -0.34 t) appears nearly flat along the zero line. Retaining the shared axis is deliberate because that visual flatness communicates an important substantive finding: divided across 1.4 billion residents, India's per-capita net export balance is less than one-eighth the size of the United Kingdom's per-capita import balance.

**Focused three-point direct labeling.** Rather than cluttering the facets with dense tick labels, each panel annotates three key milestones: the 1990 starting value, the 2022 ending value, and the historical extremum furthest from zero. Where the United States crosses from net exporter to net importer between 1997 and 1998, linear interpolation splits the polygon cleanly at the exact zero crossing.

## 5.3 What it shows

**Four distinct importer trajectories.** Although all four high-income economies finish above zero in 2022, their historical paths differ sharply. The United Kingdom's net import balance tripled from +1.12 t in 1990 to +3.34 t in 2004 before easing to +2.81 t in 2022. The United States began 1990 as a slight net exporter (-0.32 t), crossed into net-importer territory in 1998, peaked at +1.92 t in 2006, and ended 2022 at +1.49 t. Germany's import balance remained remarkably stable across the three decades (+1.82 t in 1990 versus +2.03 t in 2022), whereas Sweden cut its per-capita import balance by more than half, from +6.40 t in 1990 (and a +6.61 t peak in 1992) down to +2.86 t in 2022. Meanwhile, China's per-capita export deficit deepened to -1.20 t in 2008 before narrowing to -0.90 t in 2022, while India's reached its widest point (-0.34 t) at the end of the series.

**Quantifying the reporting bias in territorial reductions.** Because net imports expanded between 1990 and 2022 in the United States, the United Kingdom, and Germany, territorial accounting overstates the reduction in their actual carbon footprints (Table 3).

| Country | Territorial CO2 per person, 1990 to 2022 | Consumption-based CO2 per person | Territorial cut minus consumption cut, points | Consumption over production, 2022 |
| :--- | :--- | :--- | :--- | :--- |
| **United States** | -26.9% | -18.3% | 8.7 | 1.10 |
| **United Kingdom** | -56.5% | -36.5% | 20.0 | 1.62 |
| **Germany** | -40.0% | -33.7% | 6.2 | 1.26 |
| **Sweden** | -48.3% | -51.7% | -3.4 | 1.83 |

The United Kingdom exhibits the largest divergence: its territorial account reports a reduction 20.0 percentage points larger than its consumption account supports, and in 2022 British consumption generated 62% more CO2 than was emitted within UK borders. Sweden illustrates the opposite dynamic: because its net import balance shrank after 1990, its consumption footprint fell faster (-51.7%) than its territorial emissions (-48.3%), even though Sweden still consumes 83% more CO2 than it emits domestically.

**Total tonnage reverses the per-capita ranking.** Evaluating the same trade balance in total million tonnes (Mt) rather than per-capita terms flips the visual hierarchy ([[FIG:V3c]]). Multiplied across its population, China's modest -0.90 t per-capita balance represents 1,285 Mt of net exported CO2 in 2022--exceeding the combined net imports of the United States (+511 Mt), the United Kingdom (+192 Mt), Germany (+171 Mt), and Sweden (+30 Mt) put together (903 Mt). China's aggregate export balance expanded twelvefold between 1990 (-123 Mt) and 2007 (-1,506 Mt), while India's net exports grew from near zero in 1990 to -491 Mt in 2022.

[[SHOT:V3c]]

## 5.4 Implementation

The visualization is built with `seaborn` 0.13 and `matplotlib` 3.11 (Waskom, 2021; Hunter, 2007). `sns.FacetGrid` partitions the 198 focus rows across a 2 x 3 layout with shared axes and maps a custom drawing function (`facet_balance`) to each panel:

```python
# scripts/vis3_seaborn_diverging.py
    for color, name, side, keep in ((IMPORTER, "importer", 1, y >= 0),
                                    (EXPORTER, "exporter", -1, y <= 0)):
        spans = [(a, b) for a, b, s in runs if s == side]
        if not spans:
            continue
        ax.fill_between(x, 0, y, where=keep, interpolate=True, facecolor=color, alpha=FILL_ALPHA,
                        linewidth=0, zorder=2, gid=name)
        line, = ax.plot(x, y, color=color, linewidth=LINE, zorder=4, gid=name)
        line.set_clip_path(span_path(spans), ax.get_xaxis_transform())
# ...
    grid = sns.FacetGrid(data, col="country", col_order=FOCUS, col_wrap=ncol, sharex=True,
                         sharey=True, height=box["height"] / nrow,
                         aspect=(FIG_W / ncol) / (box["height"] / nrow), despine=False)
    grid.map_dataframe(facet_balance, value=VALUE, ticks=ticks, unit="t")
```

Setting `interpolate=True` in `ax.fill_between` computes the exact sub-year intersection where a series crosses zero, and clipping the boundary stroke to those same horizontal spans ensures the line and shaded polygon change color seamlessly at the zero line. The figure is rendered at 13 in width (200 dpi) for crisp typography when scaled down to the 6.5 in page column.

**AI-use disclosure.** This visualization was designed, programmed, and verified independently by me using seaborn and Matplotlib (`scripts/vis3_seaborn_diverging.py`) without AI assistance.

Source files for this section: `scripts/vis3_seaborn_diverging.py`
