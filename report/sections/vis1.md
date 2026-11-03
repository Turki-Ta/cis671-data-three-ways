## 3.1 The view

[[SHOT:V1a]]

Visualization 1 provides a macro-level overview of the global trade in embodied carbon. It tests whether the generalization that wealthy nations import carbon while developing nations export it holds across the broader global panel, and how that distribution evolved between 1990 and 2022. The design pairs two coordinated views on a single canvas ([[FIG:V1a]]): the top panel reproduces the indexed time-series view from the original article for a selected focal country, while the bottom panel plots 109 countries by their average GDP per capita and average net CO2 trade balance across whichever time window the user brushes in the top panel.

## 3.2 Idiom, marks and channels

Following Munzner's (2014) taxonomy, the design pairs two juxtaposed, multiform views: the same underlying country-year panel is encoded simultaneously as a longitudinal time series and a cross-sectional bubble scatterplot, linked by an interactive temporal filter.

| Channel / Aspect | Top view: time series | Bottom view: scatter |
| :--- | :--- | :--- |
| **Items** | 33 years of 3 measures for one country | 109 countries, each averaged over the brushed years |
| **Mark** | 2 px line per measure | Point: a circle, or a triangle when its value lies beyond the y-axis |
| **Horizontal position** | Year, 1990 to 2022 | Mean GDP per person, log scale, $600 to $200,000 |
| **Vertical position** | Percent change since 1990, common scale | Mean net balance, linear, -6 to +8 t CO2 per person |
| **Hue** | Measure: grey for GDP, orange for production, blue for consumption | World Bank income group: violet, magenta, green |
| **Area** | Not used | Mean population |
| **Shape** | Not used | Circle inside the axis range, outward-pointing triangle beyond it |
| **Text** | The 2022 value at each line end | Names of the six focus countries; active window in the panel title |
| **Interaction** | Interval brush on x; hover crosshair; country menu | Re-averaged on every brush move; tooltip per bubble; click a ringed bubble |

**Prioritizing position for the primary comparison.** In the scatterplot, per-capita wealth and the net embodied CO2 balance are assigned to horizontal and vertical position on common scales--the highest-ranking perceptual channels for quantitative accuracy (Cleveland & McGill, 1984, p. 536). Because GDP per capita spans more than two orders of magnitude across the 109 countries (from $624 to $163,531), the x-axis uses a logarithmic transformation so equal horizontal steps represent equal multiplicative ratios and lower-income economies are not compressed against the left border. Conversely, because the net CO2 balance has a meaningful zero threshold separating net importers from net exporters, the y-axis is linear with an emphasized zero baseline and explicit directional annotations in both half-planes.

**Handling extreme outliers without distorting the main view.** A handful of small oil-exporting states and commercial entrepots exhibit extreme per-capita balances ranging from -38 t to +24 t per person. Allowing those outliers to dictate the vertical domain would compress the six focal economies into a narrow central band, while dropping them would censor valid observations. To resolve this, the y-axis is fixed to [-6, +8] t per person, and countries falling outside that interval are pinned as upward- or downward-pointing triangles inside shaded boundary bands labeled *"Beyond the axis"*, with their exact values preserved in hover tooltips and comparison captions. Across all 561 possible year windows, at most 8 of the 109 countries fall into the boundary bands, and the six focal countries remain well inside the main plotting area at all times.

**Encoding context via area and hue.** Population is mapped to bubble area--a lower-ranked channel appropriate for contextual weighting rather than exact lookup. Area scales linearly with population above 30 million, while smaller nations share a minimum diameter of 8 px inside a 1.2 px stroke so countries the size of Sweden remain easy to see and target. World Bank income tiers are encoded using three categorical hues (violet for high income, magenta for upper-middle, and green for lower-middle and low income). Because horizontal position already orders countries by GDP per capita, hue serves to highlight group clustering across the zero line. The three colors were verified under simulated protanopia and deuteranopia (Machado et al., 2009) to ensure clear visual separation for color-vision-deficient readers.

**Mark dimensions.** The top panel's lines are drawn at 2 px stroke width; in the scatter panel, bubble diameters range from the 8 px floor up to roughly 63 px for China and India inside an 822 px wide canvas.

## 3.3 The brush and the link

Becker and Cleveland (1987, p. 127) define brushing as dragging an interactive region across one view while the resulting operation updates all linked views simultaneously--specifically noting the utility of a narrow 1D brush that constrains one variable to an interval to inspect conditional behavior in another plot (p. 131). In `scripts/vis1_altair_linked.py`, the brush is defined as a 1D interval selection bound strictly to the horizontal year axis of the top panel:

```python
# scripts/vis1_altair_linked.py
    brush = alt.selection_interval(
        name="brush", encodings=["x"], zoom=False, clear=False,
        mark=alt.BrushConfig(fill=INK, fillOpacity=0.07, stroke=INK_2, strokeOpacity=0.55,
                             strokeWidth=1, cursor="ew-resize"), **start)
```

The bottom scatterplot consumes that interval selection as a live filter and aggregates the surviving rows by country on the fly:

```python
# scripts/vis1_altair_linked.py
    chart = chart.transform_filter(window_filter(window)).transform_aggregate(
        mean_gdp="mean(gdp_per_capita)", mean_net="mean(net_co2_per_capita)",
        mean_pop="mean(population)", n_years="count()", year_min="min(year)",
        year_max="max(year)", groupby=["country", "income_group", "is_focus"])
```

Altair compiles these declarations into a reactive Vega-Lite specification (Satyanarayan et al., 2017; VanderPlas et al., 2018) that executes entirely in the browser. As the user drags or resizes the shaded brush window across the timeline, every bubble in the scatterplot smoothly transitions to its recomputed window mean, and the lower panel's title dynamically updates to state the active year span (e.g., *"Bubbles show each country's mean over 2013-2022 (10 years)"*). Clicking once outside the brush resets the aggregation to the full 33-year average.

While coordinated views commonly rely on visual highlighting (Roberts, 2007, Section 4.1), dynamic re-averaging is far better suited to this dataset: plotting all 3,597 country-year points simultaneously would create severe overplotting, and multi-year window averaging smooths out the single-year accounting noise noted in Section 1.3. Coordination also operates in reverse: clicking any of the six ringed focal bubbles in the scatter--or choosing a country from the dropdown menu above the canvas--updates the top time-series panel to display that nation's historical record. [[FIG:V1b]] shows the live view in Microsoft Edge after dragging the brush to the 2002-2008 WTO expansion era and selecting China.

[[SHOT:V1b]]

## 3.4 What it shows

[[SHOT:V1c]]

**High-income economies overwhelmingly sit on the importing side.** Comparing the first decade of the panel (1990-1999) against the final decade (2013-2022) in [[FIG:V1c]] shows that 37 of the 46 high-income countries are net importers of embodied CO2 in the recent window, up from 33 in the 1990s. Over that span, the United Kingdom's ten-year average balance rose from +1.57 t to +2.53 t per person, while the United States crossed from a slight net exporter (-0.06 t) to a net importer (+1.02 t). However, rising import dependence was not universal among wealthy nations: Germany's mean balance narrowed from +2.30 t to +1.53 t, and Sweden's dropped from +4.74 t to +2.71 t.

**Net exporters are highly concentrated rather than representative of all developing nations.** In the 2013-2022 window, China (-0.79 t per person) and India (-0.26 t per person) sit clearly below the zero line as massive population bubbles. Yet surrounding them, the majority of middle- and lower-income countries actually sit slightly *above* zero as net importers: 22 of the 30 upper-middle-income countries and 28 of the 33 lower-income countries are net importers in 2013-2022 (up from 15 and 23 in the 1990s). Global carbon exporting is driven by a small number of manufacturing powerhouses and hydrocarbon exporters rather than developing countries as a whole, yielding a modest Spearman rank correlation between GDP per capita and net balance per person (r_s = 0.40 in 1990-1999 and 0.43 in 2013-2022).

**Aggregate flows align with established benchmarks.** Summing total tonnage across the high-income group shows net imported CO2 rising from 0.37 Gt in 1990 to 1.55 Gt in 2008, closely matching Peters, Minx, et al.'s (2011, p. 8903) benchmark estimates of 0.4 Gt and 1.6 Gt for those same years.

## 3.5 Implementation

The visualization is built in Altair 6.3 as a vertical concatenation (`alt.vconcat`) of two layered panels with independent color scales (822 x 995 px). The compiled output embeds the 3,597 scatter rows and 198 focus time-series rows directly into a self-contained HTML artifact (`web/altair_export.html`, 1.6 MB) alongside high-resolution static PNG exports. Nearest-point hover selections allow users to trigger tooltips without having to land precisely on a 2 px line stroke, though on the outer edges of the largest bubbles (China and India), the pointer can occasionally snap to a smaller adjacent country whose center lies closer to the cursor. To confirm numerical accuracy, the script cross-checks the browser's live aggregated state against independent `pandas` window averages across multiple brush positions (agreeing to within 1e-13 t).

**AI-use disclosure.** This visualization was designed, programmed, and verified independently by me in Altair (`scripts/vis1_altair_linked.py`) without AI assistance.

Source files for this section: `scripts/vis1_altair_linked.py`
