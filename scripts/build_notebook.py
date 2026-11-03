"""
build_notebook.py -- assemble notebooks/module02_story.ipynb from source cells.

The notebook tells the story in report order: the question, the data, the three
visualizations, the synthesis. Every code cell imports a script from ../scripts
and calls its functions, so the notebook draws the same charts and prints the
same checks as the terminal runs, without a second copy of any code:

  * the Altair linked view is displayed as a live chart object (and again as
    its static PNG, for viewers that do not run JavaScript);
  * the D3 connected scatterplot is embedded as an iframe whose srcdoc holds
    the whole of web/d3_embed.html with its scripts inlined (see embed_web.py),
    so it runs inside the notebook with no server, followed by its PNG capture;
  * the Seaborn figures are drawn inline by Matplotlib from the same functions
    that write the PNGs in screenshots/.

Run from the project root:
    python scripts/build_notebook.py
    python -m jupyter nbconvert --to notebook --execute --inplace \
        --ExecutePreprocessor.timeout=600 notebooks/module02_story.ipynb
    python scripts/build_notebook.py --verify   # execution counts, errors, outputs present
"""
import os
import sys

import nbformat as nbf
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
NB_DIR = os.path.join(ROOT, "notebooks")
NB_PATH = os.path.join(NB_DIR, "module02_story.ipynb")

MD = "md"
CODE = "code"

# What verify() expects to find in the executed notebook.
INLINE_FIGURES = 3          # the three Seaborn / Matplotlib figures
STATIC_IMAGES = 6           # three originals, two Altair plates and the D3 capture

# Every cell is a raw string so the source lands in the notebook exactly as typed.
CELLS = [
(MD, r"""# Module Two - Data Three Ways

**Applied Computer Vision / Data Visualization (Module Two)**<br>
Student: Taher Turki<br>
October 2026

## Decoupling or outsourcing?

**Has economic growth in post-industrial nations genuinely decoupled from carbon emissions, or
have wealthy countries merely outsourced their environmental footprint by importing
emissions-intensive manufactured goods from developing nations?**

This notebook answers that with one dataset drawn three ways, on three platforms:

| # | Idiom | Platform | What it is for |
|---|---|---|---|
| 1 | Linked views: indexed time series + bubble scatter, joined by an interval brush | Altair (Vega-Lite) | where 109 countries sit between importing and exporting CO2, for any window of years |
| 2 | Connected scatterplot (phase-space trajectories) with a year scrubber | D3 v7 | the path each of six countries took through income and footprint |
| 3 | Small multiples of a diverging area chart | Seaborn / Matplotlib | the gap between what a country emits and what it consumes, in tonnes |

It remixes Hannah Ritchie's Our World in Data article *Many countries have decoupled economic
growth from CO2 emissions, even if we take offshored production into account* (1 December 2021,
https://ourworldindata.org/co2-gdp-decoupling) with the same publisher's CO2 dataset, updated to
2022.

The code lives in `../scripts/` and `../web/`; each cell imports it and calls it, so the notebook
and the standalone scripts cannot drift apart. Visualization 2 (the D3 chart) was built with AI
coding assistance; Visualizations 1 and 3 and the written analysis were completed independently,
as the report states for each one."""),

(MD, r"""## Setup

Inline figures and `../scripts` on the import path."""),

(CODE, r"""%matplotlib inline
import os, sys, platform
sys.path.insert(0, os.path.abspath(os.path.join("..", "scripts")))

import altair as alt
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from IPython.display import HTML, Image, display

import common

plt.rcParams["figure.dpi"] = 100        # inline preview size; the saved PNGs keep their own dpi
pd.set_option("display.float_format", "{:,.2f}".format)

print("python", platform.python_version(), "| numpy", np.__version__, "| pandas", pd.__version__,
      "| altair", alt.__version__, "| matplotlib", matplotlib.__version__,
      "| seaborn", sns.__version__)"""),

# ------------------------------------------------------------------ original
(MD, r"""## The story being remixed

Ritchie's article makes its case with two chart forms. The first is an interactive line chart,
one country per panel, of the percent change since 1990 in GDP per capita and in CO2 per capita on
both accounts. The second is a static grid of 30 countries, each drawn as two arrows for 2005-20.
They are reproduced unaltered under OWID's CC BY licence. The line chart is OWID's own export as
served on 4 October 2026, so it runs past the 2021 article; the middle image is the same chart
after China is added, which is where an indexed percent axis stops working."""),

(CODE, r"""import original_story
originals = original_story.main()
for name in ("00a_original_owid_line_chart.png", "00b_original_owid_two_countries.png",
             "00c_original_owid_arrow_grid.png"):
    display(Image(filename=os.path.join(common.SHOTS, name), width=640))"""),

# ------------------------------------------------------------------ data
(MD, r"""## 1. The data

One file: the Our World in Data CO2 and Greenhouse Gas Emissions dataset, downloaded on
4 October 2026 (50,411 rows, 79 columns, 1750-2024). `prepare_data.py` keeps the 110 countries
that have GDP, population and a real CO2 estimate on both accounts in every year from 1990 to 2022,
and derives three variables:

```
gdp_per_capita     = gdp / population                             international-$, 2011 prices
net_co2_per_capita = consumption_co2_per_capita - co2_per_capita  t CO2 per person
net_co2_mt         = consumption_co2 - co2                        Mt CO2
```

A positive net balance means the country consumes more CO2 than it emits on its own territory:
it is a net importer of embodied emissions. Running the script here prints its checks on units
and identities."""),

(CODE, r"""import prepare_data
prep = prepare_data.main(show_results=False)"""),

(MD, r"""The six focus countries, 1990 against 2022. GDP is per person in international-$ at 2011
prices; CO2 is in tonnes per person; the last three columns are the net balance."""),

(CODE, r"""summary = common.load_summary()
cols = {"gdp_pc_1990": "GDP 1990", "gdp_pc_2022": "GDP 2022", "gdp_pc_change_pct": "GDP %",
        "prod_pc_1990": "prod 1990", "prod_pc_2022": "prod 2022", "prod_change_pct": "prod %",
        "cons_pc_1990": "cons 1990", "cons_pc_2022": "cons 2022", "cons_change_pct": "cons %",
        "net_pc_1990": "net 1990", "net_pc_2007": "net 2007", "net_pc_2022": "net 2022"}
display(summary[list(cols)].rename(columns=cols))"""),

# ------------------------------------------------------------------ vis 1
(MD, r"""## 2. Visualization 1 - linked views in Altair

Top: one country's GDP per capita and CO2 per capita on both accounts, as percent change since
1990. Bottom: 109 countries, each a bubble at its mean GDP per capita (log scale) and its mean
net balance over the years brushed in the top panel; bubble area is population and hue is the
World Bank income group.

**Try it:** drag across the years in the top panel and watch the bubbles move; drag the brush
from the 1990s to the 2010s; click outside the brush to average over all 33 years; change the
country in the dropdown under the chart."""),

(CODE, r"""import vis1_altair_linked as v1
chart = v1.build_chart()
chart"""),

(MD, r"""The same view as a static image (brush on 2013-2022), for viewers that do not run
JavaScript, and the two brush positions side by side."""),

(CODE, r"""display(Image(filename=os.path.join(common.SHOTS, "01_vis1_altair_linked.png"), width=820))
display(Image(filename=os.path.join(common.SHOTS, "01_vis1_brush_comparison.png"), width=980))"""),

# ------------------------------------------------------------------ vis 2
(MD, r"""## 3. Visualization 2 - connected scatterplot in D3

Time is taken off the x-axis. Each country is one path through GDP per capita (x) and
consumption-based CO2 per capita (y), from 1990 to 2022, with chevrons marking the direction of
travel. A path that heads down and to the right is a country getting richer with a smaller
footprint.

**Try it:** move the year slider or press play; hover a point for the numbers; tick *Show
production-based path* to see the gap between what a country emits and what it consumes; switch
the x-axis between log and linear; click a legend entry to hide a country.

The chart below is the live page `../web/d3_embed.html`, folded into a single iframe so that it
runs inside the notebook with no server."""),

(CODE, r"""from embed_web import iframe
display(HTML(iframe("d3_embed.html", height=860, title="D3 connected scatterplot")))"""),

(MD, r"""Its capture at 2022, for viewers that do not run JavaScript."""),

(CODE, r"""display(Image(filename=os.path.join(common.SHOTS, "02_vis2_d3_connected_scatter.png"),
              width=980))"""),

# ------------------------------------------------------------------ vis 3
(MD, r"""## 4. Visualization 3 - diverging small multiples in Seaborn

The net balance itself, one facet per country on shared axes: blue where the country consumes
more CO2 than it emits (net importer), orange where it emits more than it consumes (net
exporter). Running the script draws the three figures, saves them and prints its checks."""),

(CODE, r"""import vis3_seaborn_diverging as v3
r3 = v3.main(show_results=False)"""),

(CODE, r"""fig = v3.main_figure()
plt.show()"""),

(MD, r"""How the main figure is derived, for the United Kingdom: the two accounts as lines, then
the gap between them on its own."""),

(CODE, r"""fig = v3.derivation_plate()
plt.show()"""),

(MD, r"""The same balance in absolute terms. Per person, China's export balance looks small; in
tonnes it is the largest flow of the six."""),

(CODE, r"""fig = v3.absolute_figure()
plt.show()"""),

# ------------------------------------------------------------------ synthesis
(MD, r"""## 5. What the three views say together

How much of each importer's territorial cut was offset by a larger import balance? The offset
share is the change in the net balance divided by the fall in production-based CO2 per person,
1990 to 2022."""),

(CODE, r"""rows = []
for country in common.FOCUS[:4]:
    s = summary.loc[country]
    prod_cut = s["prod_pc_1990"] - s["prod_pc_2022"]
    cons_cut = s["cons_pc_1990"] - s["cons_pc_2022"]
    balance = s["net_pc_2022"] - s["net_pc_1990"]
    rows.append({"country": country, "GDP per person %": s["gdp_pc_change_pct"],
                 "territorial cut, t": prod_cut, "consumption cut, t": cons_cut,
                 "change in net balance, t": balance, "offset share %": 100 * balance / prod_cut})
display(pd.DataFrame(rows).set_index("country"))"""),

(MD, r"""Emissions fell on both accounts in all four countries while GDP per person rose, so the
decoupling is real. The import balance still matters. It widened until the mid-2000s, it gave back
33% of the territorial cut in the United States and 29% in the United Kingdom, and in 2022 the
United Kingdom consumed 62% more CO2 than it emitted at home. Germany's balance barely moved and
Sweden's shrank. China and India moved the other way on both axes and became the exporters."""),
]


def build():
    nb = new_notebook()
    nb.metadata["kernelspec"] = {"display_name": "Python 3 (module02 .venv)",
                                 "language": "python", "name": "python3"}
    nb.metadata["language_info"] = {"name": "python"}
    nb.cells = [new_markdown_cell(src) if kind == MD else new_code_cell(src)
                for kind, src in CELLS]
    os.makedirs(NB_DIR, exist_ok=True)
    nbf.write(nb, NB_PATH)
    n_code = sum(1 for k, _ in CELLS if k == CODE)
    print(f"wrote {os.path.relpath(NB_PATH, ROOT)}: {len(CELLS)} cells ({n_code} code)")


def verify():
    """After nbconvert --execute: every code cell ran, none raised, the Altair
    chart, the D3 iframe and every figure are in the outputs, and no check
    printed FAIL."""
    nb = nbf.read(NB_PATH, as_version=4)
    code = [c for c in nb.cells if c.cell_type == "code"]
    outputs = [o for c in code for o in c.outputs]
    unexecuted = [i for i, c in enumerate(code) if c.execution_count is None]
    errors = [(i, o.get("ename")) for i, c in enumerate(code) for o in c.outputs
              if o.output_type == "error"]
    data = [o.get("data", {}) for o in outputs
            if o.output_type in ("display_data", "execute_result")]
    inline = sum(1 for d in data if "image/png" in d and "Figure" in d.get("text/plain", ""))
    static = sum(1 for d in data if "image/png" in d and "Figure" not in d.get("text/plain", ""))
    html = ["".join(d["text/html"]) for d in data if "text/html" in d]
    altair = any("vega" in h.lower() and "selection" in h.lower() for h in html) or any(
        key.startswith("application/vnd.vegalite") for d in data for key in d)
    d3 = any("<iframe" in h and "srcdoc" in h and "DECOUPLING_DATA" in h for h in html)
    stream = "".join(o.get("text", "") for o in outputs if o.output_type == "stream")
    passed, failed = stream.count("... PASS"), stream.count("... FAIL")
    print(f"code cells {len(code)}, unexecuted {len(unexecuted)}, errors {errors or 0}, "
          f"inline Matplotlib figures {inline} (expected {INLINE_FIGURES}), "
          f"static images {static} (expected {STATIC_IMAGES}), "
          f"Altair chart output {'present' if altair else 'MISSING'}, "
          f"D3 iframe {'present' if d3 else 'MISSING'}, "
          f"checks {passed} PASS / {failed} FAIL")
    return (not unexecuted and not errors and inline == INLINE_FIGURES
            and static == STATIC_IMAGES and altair and d3 and failed == 0)


if __name__ == "__main__":
    if "--verify" in sys.argv[1:]:
        sys.exit(0 if verify() else 1)
    build()
