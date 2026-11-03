"""
vis1_altair_linked.py -- Visualization 1: two coordinated views in Altair, linked
by an interval brush.

Top     one focus country at a time (a dropdown): GDP per capita and CO2 per capita on
        both accounts, as percent change since 1990. The brush is drawn on this panel:
        drag to set a window of years, drag its label to slide it, click to clear it.
Bottom  every country with a World Bank income group, one bubble each, placed at its
        MEAN over the brushed years: GDP per capita (log) against the net balance of
        embodied CO2 (consumption minus production, linear). Area is population, hue
        is the income group. The filter and the averaging run in the browser, so the
        bubbles move while the brush is dragged. A click on one of the six ringed
        bubbles puts that country in the top panel.

Input   inputs/decoupling_focus.csv, inputs/decoupling_panel.csv,
        inputs/decoupling_summary.csv        (written by prepare_data.py)

Output  web/altair_export.html               the interactive page, JavaScript inlined
        web/altair_spec.json                 the Vega-Lite spec of the same chart
        screenshots/01_vis1_altair_linked.png        brush on 2013-2022, United Kingdom
        screenshots/01a_vis1_brush_early.png         the same view, brush on 1990-1999
        screenshots/01b_vis1_brush_late.png          the same view, brush on 2013-2022
        screenshots/01_vis1_brush_comparison.png     the two scatter states side by side
        screenshots/01c_vis1_browser_brushed.png     Edge, after a real mouse drag

The script prints 'check: ... PASS' lines on what it wrote (the numbers the scatter
must show, the structure of the spec, the behaviour of the page in a browser) and
'result: name = value' lines for the numbers the report quotes.

Run:  python scripts/vis1_altair_linked.py
      python scripts/vis1_altair_linked.py --no-browser     # skip the Edge test
"""
import io
import json
import math
import os
import pathlib
import re
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import altair as alt
import pandas as pd

from common import (AXIS, EARLY, FOCUS, FOCUS_SHORT, FONT_STACK, GRID, INCOME_COLORS,
                    INCOME_ORDER, INK, INK_2, LATE, MEASURES, MUTED, ROOT, SHOTS, SURFACE, WEB,
                    YEAR_MAX, YEAR_MIN, ZERO, Log, load_focus, load_panel, load_summary)

HTML_PATH = os.path.join(WEB, "altair_export.html")
SPEC_PATH = os.path.join(WEB, "altair_spec.json")
PNG_MAIN = os.path.join(SHOTS, "01_vis1_altair_linked.png")
PNG_EARLY = os.path.join(SHOTS, "01a_vis1_brush_early.png")
PNG_LATE = os.path.join(SHOTS, "01b_vis1_brush_late.png")
PNG_PLATE = os.path.join(SHOTS, "01_vis1_brush_comparison.png")
PNG_BROWSER = os.path.join(SHOTS, "01c_vis1_browser_brushed.png")
PNG_WIDTH = 2600                      # target width of the static plates, px
LOG_WIDTH = 112                       # longest line printed, so the terminal captures stay legible
ALL_YEARS = (YEAR_MIN, YEAR_MAX)
# The two brush positions the report compares, and the cleared brush.
WINDOWS = {"early": EARLY, "late": LATE, "all": ALL_YEARS}

# ---------------------------------------------------------------- geometry
PLOT_W = 596                          # both panels share one plot width, so their edges align
TOP_H = 236
SCATTER_H = 440
TAB_H = 20                            # strip at the top of the time series kept for the brush tab
LABEL_GAP = 14                        # least distance between two line-end labels, px
PLATE_W, PLATE_H, PLATE_ZOOM = 500, 440, 1.3

# Net balance axis. Whatever window is brushed, all but 8 of the plotted countries at
# most fall inside the labelled range; a band beyond each end is reserved for the rest.
Y_LO, Y_HI = -6.0, 8.0
BAND = 0.7
CAPTION_X = 7                         # left edge of the small print inside the scatter, px
# Inside a band a pinned mark sits further out the more extreme its value, from 30% of
# the band's depth at the axis limit to 70% at PIN_SPAN tonnes beyond it and more. Two
# countries with the same GDP per capita then show as two triangles, not as one.
PIN_NEAR, PIN_FAR, PIN_SPAN = 0.3, 0.7, 30.0
X_DOMAIN = [600, 200000]              # single-year GDP per capita runs from $624 to $163,531
X_TICKS = [1000, 3000, 10000, 30000, 100000]

# Bubble area is proportional to population. A country of 30 million or fewer would be
# a speck at that rate, so it is drawn at the smallest size that stays readable.
# Vega measures a symbol by the square it fits in: a circle of size s is sqrt(s) px
# across. AREA_PER_PERSON is therefore that square's area per person, and a circle
# covers pi / 4 of it, which keeps the disc's own area proportional to population.
POP_FLOOR = 30e6
BUBBLE_RING = 1.2                     # surface-coloured stroke that separates overlapping bubbles
MIN_DIAMETER = 8.0 + BUBBLE_RING      # 8 px of fill inside the ring
DOT_RING = 2.0                        # ring of the line-end and crosshair markers
AREA_PER_PERSON = MIN_DIAMETER ** 2 / POP_FLOOR
POP_TOP = 1.5e9
POP_LEGEND = [30e6, 100e6, 300e6, 1e9]
# A triangle of Vega size s covers sqrt(3) / 4 of the square against pi / 4 for a
# circle; the pinned marks are scaled up by the ratio so that their area follows
# population like the rest.
TRIANGLE_BOOST = math.pi / math.sqrt(3)

FONT = ", ".join(FONT_STACK) + ", sans-serif"
# The three series of the top panel: column in decoupling_focus.csv -> name in the legend
# (the keys of common.MEASURES, which also fix the colours), and a short name for labels.
CHANGE_COLS = dict(zip(("gdp_pc_change_pct", "prod_change_pct", "cons_change_pct"), MEASURES))
SHORT = dict(zip(MEASURES, ("GDP", "Production", "Consumption")))
INCOME_TAGS = {"High income": "high_income", "Upper-middle income": "upper_middle",
               "Lower-middle and low income": "lower"}
# Where each focus label sits relative to its bubble, as (horizontal, vertical) steps of
# -1, 0 or 1. The four rich countries crowd one corner of the plot, so each label takes
# a different side; the sides were chosen by scoring every combination against the
# bubbles of 1990-1999 and of 2013-2022 (overlap with another label or with a bubble).
LABEL_SIDES = {"United States": (1, 1), "United Kingdom": (-1, 0), "Germany": (1, -1),
               "Sweden": (1, 0), "China": (0, 1), "India": (0, 1)}

TITLE = "Decoupled or offshored? GDP, CO2 and the trade in embodied emissions, 1990-2022"
SUBTITLE = ["Drag across the years in the top panel to choose the window the scatter averages "
            "over; drag the window's label",
            "to slide it, or click the panel once to clear it. Pick the top panel's country "
            "from the menu or by clicking a ringed bubble."]
DESCRIPTION = ("Linked views. An interval selection (a brush) on the time series of one country "
               "sets the years over which the scatter below averages GDP per capita and the "
               "net balance of embodied CO2 for every country.")
SOURCE = ("Source: Our World in Data CO2 dataset (Global Carbon Budget 2025, Maddison Project "
          "Database 2023), World Bank income groups.")
BANNED = ("delve", "tapestry", "testament", "crucial", "moreover", "furthermore",
          "in conclusion", "it is important to note", "serves as a bridge",
          "rich visual representation", "multifaceted", "leverage", "robust", "seamless",
          "comprehensive", "underscores", "pivotal", "nuanced", "holistic", "realm",
          "landscape", "navigate", "foster", "as we can see", "this demonstrates that",
          "in summary", "overall")

# Added to the page that chart.save() writes: the page plane, the font, the dropdown in a
# row above the chart it scopes, and a tooltip in which the value leads and the label
# follows. Everything else on the page is Altair's own inline template.
PAGE_STYLE = """
  <title>Visualization 1 - Altair linked views</title>
  <style>
    html, body { margin: 0; background: %(surface)s; }
    body { font-family: "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial,
           sans-serif; color: %(ink)s; }
    #vis.vega-embed { display: flex; flex-direction: column; align-items: flex-start;
                      width: auto; }
    #vis .vega-bindings { order: -1; margin: 14px 0 0 12px; font-size: 13px;
                          color: %(ink2)s; }
    #vis .vega-bind-name { margin-right: 8px; }
    #vis .vega-bind select { font: inherit; color: %(ink)s; background: %(surface)s;
                             border: 1px solid %(axis)s; border-radius: 4px;
                             padding: 3px 8px; }
    #vg-tooltip-element.vg-tooltip { font-family: inherit; font-size: 12px; color: %(ink)s;
                                     background: %(surface)s; border-radius: 4px;
                                     border: 1px solid rgba(11, 11, 11, 0.16);
                                     box-shadow: 0 2px 8px rgba(11, 11, 11, 0.10);
                                     padding: 8px 10px; }
    #vg-tooltip-element.vg-tooltip table tr td.key { color: %(ink2)s; font-weight: 400;
                                                     max-width: 280px; white-space: nowrap; }
    #vg-tooltip-element.vg-tooltip table tr td.value { color: %(ink)s; font-weight: 600; }
  </style>
""" % {"surface": SURFACE, "ink": INK, "ink2": INK_2, "axis": AXIS}
EMBED_CALL = "vegaEmbed('#vis', spec, embedOpt).catch(console.error);"
# The same call, keeping the result so that the browser test can read the Vega view.
EMBED_KEPT = ("vegaEmbed('#vis', spec, embedOpt).then(function (result) "
              "{ window.vis1 = result; }).catch(console.error);")
# The tooltip opens a little further from the pointer than the default 10 px, so that it
# does not sit on the bubble it describes or on that bubble's label.
EMBED_OPTIONS = {"actions": False, "renderer": "svg", "tooltip": {"offsetX": 22, "offsetY": 14}}


# ---------------------------------------------------------------- tables
def scatter_table():
    """One row per country-year for the scatter: the countries with an income group.

    Taiwan is in the panel but missing from the World Bank's API response (the Bank
    does classify it, as high income), so it has no hue to wear and is left out: all
    but one of the panel's countries are plotted.
    """
    panel = load_panel().dropna(subset=["income_group"])
    cols = ["country", "income_group", "is_focus", "year", "gdp_per_capita",
            "net_co2_per_capita", "population"]
    return panel[cols].reset_index(drop=True)


def series_table():
    """The six focus countries, one row per year, with the three change columns."""
    focus = load_focus()
    focus["country"] = focus["country"].astype(str)
    return focus[["country", "year"] + list(CHANGE_COLS)].reset_index(drop=True)


def y_domains(series):
    """Per country, the y-domain of the top panel: the data range plus fixed margins.

    The domain is set here instead of being left to the renderer because the positions
    of the line-end labels are worked out from it, and because the top margin has to
    clear the strip that holds the brush tab.
    """
    out = {}
    for country, d in series.groupby("country"):
        lo, hi = d[list(CHANGE_COLS)].min().min(), d[list(CHANGE_COLS)].max().max()
        span = hi - lo
        out[country] = (round(lo - 0.08 * span, 2), round(hi + 0.15 * span, 2))
    return out


def spread(positions, gap):
    """Move positions apart until neighbours are at least `gap` apart, keeping the order
    and moving each cluster as little as possible (its centre stays where it was)."""
    order = sorted(range(len(positions)), key=lambda i: positions[i])
    clusters = [[i] for i in order]
    centre = [positions[i] for i in order]
    merged = True
    while merged:
        merged = False
        for k in range(len(clusters) - 1):
            reach = (len(clusters[k]) + len(clusters[k + 1])) * gap / 2
            if centre[k + 1] - centre[k] < reach - 1e-9:
                members = clusters[k] + clusters[k + 1]
                clusters[k:k + 2] = [members]
                centre[k:k + 2] = [sum(positions[i] for i in members) / len(members)]
                merged = True
                break
    out = list(positions)
    for members, mid in zip(clusters, centre):
        for j, i in enumerate(members):
            out[i] = mid + (j - (len(members) - 1) / 2) * gap
    return out


def end_labels(series, domains):
    """The label at the end of each line: a short name and the 2022 value.

    Two lines can end within a few pixels of each other (Sweden, Germany, China), so the
    labels are spread to LABEL_GAP apart; label_y is the value the label is drawn at.
    """
    rows = []
    last = series[series["year"] == YEAR_MAX].set_index("country")
    for country in FOCUS:
        lo, hi = domains[country]
        per_px = (hi - lo) / TOP_H
        values = [last.loc[country, col] for col in CHANGE_COLS]
        pixels = spread([(hi - v) / per_px for v in values], LABEL_GAP)
        for (col, measure), value, px in zip(CHANGE_COLS.items(), values, pixels):
            rows.append({"country": country, "measure": measure, "year": YEAR_MAX,
                         "value": value, "label_y": hi - px * per_px,
                         "text": f"{SHORT[measure]} {value:+.0f}%"})
    return pd.DataFrame(rows)


def window_means(table, window):
    """The pandas twin of the scatter's Vega pipeline: filter to the window, then one
    row per country with the mean of each plotted variable."""
    rows = table[table["year"].between(window[0], window[1])]
    means = rows.groupby("country").agg(
        income_group=("income_group", "first"), mean_gdp=("gdp_per_capita", "mean"),
        mean_net=("net_co2_per_capita", "mean"), mean_pop=("population", "mean"),
        n_years=("year", "size"))
    means["pin"] = "inside"
    means.loc[means["mean_net"] > Y_HI, "pin"] = "above"
    means.loc[means["mean_net"] < Y_LO, "pin"] = "below"
    return means


# ---------------------------------------------------------------- expressions
def lookup(mapping, key):
    """A Vega expression that reads `mapping` at `key`."""
    return f"({json.dumps(mapping)})[{key}]"


def window_filter(window):
    """What the scatter filters on: the brush itself, or a fixed span of years."""
    if isinstance(window, alt.Parameter):
        return window
    return alt.FieldRangePredicate(field="year", range=[window[0], window[1]])


def brush_params():
    """Readouts of the brush: the first and last whole year inside it, and a label.

    The selection test is inclusive at both ends, so the years that pass are the whole
    numbers from ceil(low edge) to floor(high edge); a brush narrower than a year can
    hold none.
    """
    active = "isDefined(brush.year)"
    low = "min(brush.year[0], brush.year[1])"
    high = "max(brush.year[0], brush.year[1])"
    return [
        alt.param(name="win_x0", expr=f"{active} ? {low} : {YEAR_MIN - 0.5}"),
        alt.param(name="win_x1", expr=f"{active} ? {high} : {YEAR_MIN - 0.5}"),
        alt.param(name="win_lo", expr=f"{active} ? ceil({low}) : {YEAR_MIN}"),
        alt.param(name="win_hi", expr=f"{active} ? floor({high}) : {YEAR_MAX}"),
        alt.param(name="win_label", expr="win_hi < win_lo ? 'no whole year' : win_lo == win_hi "
                                         "? toString(win_lo) : win_lo + '-' + win_hi"),
    ]


TITLE_LEAD = "Bubbles show each country's mean over "
EMPTY_TITLE = "The brush holds no whole year: drag it wider, or click the top panel to clear it"
SCATTER_TITLE = (
    f"win_hi < win_lo ? {json.dumps(EMPTY_TITLE)} : {json.dumps(TITLE_LEAD)} + win_label + "
    "(isDefined(brush.year) ? (win_lo == win_hi ? ' (one year)' : ' (' + (win_hi - win_lo + 1) "
    f"+ ' years)') : ' (all {YEAR_MAX - YEAR_MIN + 1} years, no window brushed)')")


def window_label(window):
    """What the scatter title says after TITLE_LEAD; None stands for the cleared brush."""
    if window is None:
        return (f"{YEAR_MIN}-{YEAR_MAX} (all {YEAR_MAX - YEAR_MIN + 1} years, "
                f"no window brushed)")
    lo, hi = window
    return f"{lo} (one year)" if lo == hi else f"{lo}-{hi} ({hi - lo + 1} years)"


# ---------------------------------------------------------------- top panel
def panel_title(text, subtitle=alt.Undefined, zoom=1.0):
    return alt.Title(text, subtitle=subtitle, anchor="start", frame="group",
                     fontSize=13.5 * zoom, fontWeight=600, color=INK, subtitleColor=INK_2,
                     subtitleFontSize=11.5 * zoom, subtitlePadding=5, offset=8)


def year_axis(field="year"):
    years = list(range(YEAR_MIN, YEAR_MAX + 1))
    # Vega thins explicit tick values down to tickCount, so the count is given too.
    return alt.X(field, type="quantitative",
                 scale=alt.Scale(domain=[YEAR_MIN - 0.5, YEAR_MAX + 0.5], nice=False),
                 axis=alt.Axis(values=years, format="d", grid=False, title="Year",
                               labelExpr="datum.value % 5 == 0 ? datum.label : ''",
                               labelOverlap=False, tickCount=len(years),
                               tickSize=alt.condition("datum.value % 5 == 0", alt.value(6),
                                                      alt.value(3))))


def change_axis(field):
    return alt.Y(field, type="quantitative",
                 scale=alt.Scale(domainMin=alt.expr("y_lo"), domainMax=alt.expr("y_hi"),
                                 nice=False, zero=False),
                 axis=alt.Axis(title="Change since 1990 (%)", format="+d", tickCount=6,
                               grid=True, labelExpr="datum.value == 0 ? '0' : datum.label"))


def measure_scale():
    return alt.Scale(domain=list(MEASURES), range=list(MEASURES.values()))


def brush_layer(wide, brush):
    """The brush and its tab, in a layer of their own.

    Vega-Lite draws a brush above every mark of the layer that defines it, where it
    would swallow the hover events of the whole brushed span. Nesting it in a layer of
    its own keeps it beneath the lines and the hover bands; the strip at the top of
    the plot, which the bands leave free, is where the brush can be gripped and slid.
    """
    host = (wide.mark_point(opacity=0, size=1).encode(x=year_axis(), y=alt.value(0))
            .properties(name="window_host").add_params(brush))
    one = alt.Chart(alt.InlineData(values=[{"tab": 1}]))
    shown = alt.expr("isDefined(brush.year) ? 1 : 0")
    tab = one.mark_rect(fill=GRID, stroke=AXIS, strokeWidth=1, cornerRadius=3,
                        opacity=shown).encode(
        x=alt.datum(alt.expr("win_x0"), type="quantitative"), x2=alt.datum(alt.expr("win_x1")),
        y=alt.value(2.5), y2=alt.value(TAB_H - 2.5))
    label = one.mark_text(text=alt.expr("win_label"), color=INK, fontSize=10.5, fontWeight=600,
                          baseline="middle", opacity=shown).encode(
        x=alt.datum(alt.expr("(win_x0 + win_x1) / 2"), type="quantitative"),
        y=alt.value(TAB_H / 2))
    return alt.layer(host, tab, label)


def time_series_panel(series, labels, country, brush):
    wide = alt.Chart(series).transform_filter(alt.datum.country == country).transform_calculate(
        year_from="datum.year - 0.5", year_to="datum.year + 0.5",
        **{f"tip_{col}": f"format(datum.{col}, '+.1f') + '%'" for col in CHANGE_COLS})
    long = wide.transform_fold(list(CHANGE_COLS), as_=["column", "value"]).transform_calculate(
        measure=lookup(CHANGE_COLS, "datum.column"))
    hover = alt.selection_point(name="hover_year", fields=["year"], on="pointerover",
                                clear="pointerout", empty=False)
    shown = alt.condition(hover, alt.value(1), alt.value(0))

    zero = alt.Chart(alt.InlineData(values=[{"zero": 0}])).mark_rule(color=AXIS).encode(
        y=alt.Y(datum=0))
    lines = long.mark_line(strokeWidth=2, strokeJoin="round", strokeCap="round").encode(
        x=year_axis(), y=change_axis("value"),
        color=alt.Color("measure:N", scale=measure_scale(), legend=alt.Legend(
            title=None, orient="top", direction="horizontal", symbolType="stroke",
            symbolStrokeWidth=2, symbolSize=260, labelLimit=260, columnPadding=20, offset=6)))
    # The markers are coloured through the fill channel, which has a scale of its own:
    # the legend then describes the lines alone and no layer has to switch it off.
    dot = dict(filled=True, size=78, stroke=SURFACE, strokeWidth=DOT_RING, opacity=1)
    fill = alt.Fill("measure:N", scale=measure_scale(), legend=None)
    ends = long.transform_filter(alt.datum.year == YEAR_MAX).mark_point(**dot).encode(
        x=year_axis(), y=change_axis("value"), fill=fill)
    texts = (alt.Chart(labels).transform_filter(alt.datum.country == country)
             .mark_text(align="left", baseline="middle", dx=10, color=INK, fontSize=11.5)
             .encode(x=year_axis(), y=change_axis("label_y"), text="text:N"))
    cross = wide.mark_rule(color=INK_2, strokeWidth=1).encode(
        x=year_axis(), y=alt.value(TAB_H), y2=alt.value(TOP_H), opacity=shown)
    dots = long.mark_point(**dot).encode(x=year_axis(), y=change_axis("value"), fill=fill,
                                         opacity=shown)
    # One invisible band per year, year - 0.5 to year + 0.5: the pointer only has to be
    # nearest to a year, never on a 2 px line, and the band carries the tooltip.
    bands = wide.mark_rect(opacity=0, cursor="crosshair").encode(
        x=year_axis("year_from"), x2="year_to:Q", y=alt.value(TAB_H), y2=alt.value(TOP_H),
        tooltip=[alt.Tooltip("country:N", title="Country"),
                 alt.Tooltip("year:Q", title="Year", format="d")]
        + [alt.Tooltip(f"tip_{col}:N", title=name) for col, name in CHANGE_COLS.items()],
    ).properties(name="year_bands").add_params(hover)
    # A unit that holds a selection sits in a layer of its own: Altair attaches the
    # selections of a layered chart to every named unit directly inside it, which would
    # put the brush on the hover bands as well.
    return alt.layer(brush_layer(wide, brush), zero, lines, ends, texts, cross, dots,
                     alt.layer(bands)).properties(
        width=PLOT_W, height=TOP_H,
        title=panel_title(alt.expr("country + ': GDP and CO2 per capita, change since 1990'")))


# ---------------------------------------------------------------- bottom panel
def gdp_axis(look):
    title = ("Mean GDP per capita (international-$ at 2011 prices, log scale)" if look["plate"]
             else "Mean GDP per capita over the window (international-$ at 2011 prices, "
                  "log scale)")
    return alt.X("mean_gdp:Q", scale=alt.Scale(type="log", domain=X_DOMAIN, nice=False),
                 axis=alt.Axis(values=X_TICKS, format="$,.0f", grid=True, title=title))


def net_axis(look, field="y_plot"):
    """The y-axis of the scatter. On the plate the second panel shares the first one's
    labels, and the larger type needs the title on two lines to fit the plot height."""
    ticks = list(range(int(Y_LO), int(Y_HI) + 1, 2))
    title = "Mean net CO2 balance, consumption minus production (t CO2 per person)"
    if look["plate"]:
        title = [title[:title.index(" (")], title[title.index("("):]]
    return alt.Y(field, type="quantitative",
                 scale=alt.Scale(type="linear", domain=[Y_LO - BAND, Y_HI + BAND], nice=False,
                                 zero=False),
                 axis=alt.Axis(values=ticks, format="+d", grid=True, labels=look["labelled"],
                               ticks=look["labelled"],
                               title=title if look["labelled"] else None,
                               labelExpr="datum.value == 0 ? '0' : datum.label"))


def population_size():
    labels = ("datum.value <= %d ? 'up to %d million' : datum.value >= 1e9 ? "
              "format(datum.value / 1e9, 'd') + ' billion' : "
              "format(datum.value / 1e6, 'd') + ' million'" % (POP_FLOOR, POP_FLOOR / 1e6))
    key = alt.Legend(title=["Population", "(area to scale)"], values=POP_LEGEND,
                     labelExpr=labels, symbolType="circle", symbolFillColor=AXIS,
                     symbolStrokeColor=SURFACE, symbolStrokeWidth=0, symbolOpacity=1,
                     rowPadding=4)
    return alt.Size("size_pop:Q", legend=key,
                    scale=alt.Scale(type="linear", domain=[0, POP_TOP],
                                    range=[0, AREA_PER_PERSON * POP_TOP]))


def income_colour():
    wrap = ("datum.label == 'Lower-middle and low income' ? ['Lower-middle and', 'low income'] "
            ": datum.label")
    return alt.Color("income_group:N",
                     scale=alt.Scale(domain=INCOME_ORDER,
                                     range=[INCOME_COLORS[g] for g in INCOME_ORDER]),
                     legend=alt.Legend(title=["Income group", "(World Bank)"], labelExpr=wrap,
                                       symbolType="circle", symbolSize=110,
                                       symbolStrokeWidth=0, symbolOpacity=0.75))


# The tooltip of a bubble, as one expression. Vega-Lite 6.4 copies a tooltip encoding
# onto the Voronoi cells without redirecting its text fields to the point under the
# cell (they read as undefined), so the row is looked up here: on a cell the data row
# is datum.datum, on the point itself it is datum.
# A pinned country gets one more row, which says that its mark is not where its value is.
TIP_ROWS = ", ".join(f"'{title}': (datum.datum || datum).{field}" for title, field in (
    ("Country", "country"), ("Income group", "income_group"),
    ("Mean GDP per capita", "tip_gdp"), ("Mean net balance", "tip_net"),
    ("Mean population", "tip_pop"), ("Years averaged", "tip_years")))
PINNED_ROW = "'Drawn': 'at the edge, beyond the axis'"
BUBBLE_TIP = (f"(datum.datum || datum).pin == 'inside' ? {{{TIP_ROWS}}} "
              f": {{{TIP_ROWS}, {PINNED_ROW}}}")


def pinned_at(limit, side):
    """Where in its band a mark beyond `limit` is drawn; `side` is 1 above, -1 below."""
    beyond = f"min(1, {side} * (datum.mean_net - {limit}) / {PIN_SPAN})"
    return f"{limit} + {side * BAND} * ({PIN_NEAR} + {PIN_FAR - PIN_NEAR} * {beyond})"


def scatter_calculations():
    """Fields derived from the window means, in the order they depend on each other."""
    radius = f"sqrt({AREA_PER_PERSON!r} * max(datum.mean_pop, {POP_FLOOR!r})) / 2"
    # A label beside, above or below its bubble clears the edge by 5 px; one on a
    # diagonal starts where the 45-degree radius meets the edge.
    reach = "(datum.side_h != 0 && datum.side_v != 0 ? 0.71 * datum.radius + 3 : datum.radius + 5)"
    return [
        ("pin", f"datum.mean_net > {Y_HI} ? 'above' : datum.mean_net < {Y_LO} ? 'below' "
                f": 'inside'"),
        ("y_plot", f"datum.pin == 'above' ? {pinned_at(Y_HI, 1)} : datum.pin == 'below' "
                   f"? {pinned_at(Y_LO, -1)} : datum.mean_net"),
        ("size_pop", f"max(datum.mean_pop, {POP_FLOOR!r}) * (datum.pin == 'inside' ? 1 "
                     f": {TRIANGLE_BOOST!r})"),
        ("radius", radius),
        ("label", lookup(FOCUS_SHORT, "datum.country")),
        ("side_h", lookup({c: s[0] for c, s in LABEL_SIDES.items()}, "datum.country")),
        ("side_v", lookup({c: s[1] for c, s in LABEL_SIDES.items()}, "datum.country")),
        ("label_dx", f"datum.side_h * {reach}"),
        ("label_dy", f"datum.side_v * {reach}"),
        ("label_align", "datum.side_h > 0 ? 'left' : datum.side_h < 0 ? 'right' : 'center'"),
        ("label_base", "datum.side_v > 0 ? 'top' : datum.side_v < 0 ? 'bottom' : 'middle'"),
        ("tip_gdp", "'$' + format(datum.mean_gdp, ',.0f')"),
        ("tip_net", "format(datum.mean_net, '+.2f') + ' t CO2 per person'"),
        ("tip_pop", "datum.mean_pop >= 1e9 ? format(datum.mean_pop / 1e9, '.2f') + ' billion' "
                    ": format(datum.mean_pop / 1e6, '.1f') + ' million'"),
        ("tip_years", "datum.n_years == 1 ? toString(datum.year_min) : datum.year_min + '-' + "
                      "datum.year_max + ' (' + datum.n_years + ' years)'"),
    ]


def averaged(chart, window):
    """Filter to the window, then one row per country: the means the scatter plots."""
    chart = chart.transform_filter(window_filter(window)).transform_aggregate(
        mean_gdp="mean(gdp_per_capita)", mean_net="mean(net_co2_per_capita)",
        mean_pop="mean(population)", n_years="count()", year_min="min(year)",
        year_max="max(year)", groupby=["country", "income_group", "is_focus"])
    for name, expr in scatter_calculations():
        chart = chart.transform_calculate(**{name: expr})
    return chart


def captions(look):
    """The small print inside the scatter: its type size, and (y in px, text) per line.

    It sits in the two left-hand corners, which stay empty in every window: no country
    poor enough to plot there imports or exports that much CO2 per person.
    """
    height, size = look["height"], 10.5 * look["zoom"]
    band = BAND / (Y_HI - Y_LO + 2 * BAND) * height
    step = 1.3 * size
    return size, [(band / 2, f"Beyond the axis (above {Y_HI:+.0f} t)"),
                  (band + 0.9 * step, "Net importer: consumes"),
                  (band + 1.9 * step, "more CO2 than it emits"),
                  (height - band - 1.9 * step, "Net exporter: emits"),
                  (height - band - 0.9 * step, "more CO2 than it consumes"),
                  (height - band / 2, f"Beyond the axis (below {Y_LO:+.0f} t)")]


def caption_zone(look):
    """The corners the captions occupy, in data terms: GDP per capita below the first
    value together with a balance above the second or below the third. The text is
    taken to be 0.6 em a character wide, which is generous for this typeface."""
    size, rows = captions(look)
    reach = CAPTION_X + 0.6 * size * max(len(text) for _, text in rows)
    gdp = X_DOMAIN[0] * (X_DOMAIN[1] / X_DOMAIN[0]) ** (reach / look["width"])
    per_px = (Y_HI - Y_LO + 2 * BAND) / look["height"]
    return (gdp, Y_HI + BAND - (rows[2][0] + size / 2) * per_px,
            Y_HI + BAND - (rows[3][0] - size / 2) * per_px)


def scatter_furniture(look):
    """What sits behind the bubbles: the off-scale bands, the zero line, the captions."""
    size, rows = captions(look)
    lines = pd.DataFrame(rows, columns=["y", "text"])
    bands = pd.DataFrame({"y0": [Y_HI, Y_LO - BAND], "y1": [Y_HI + BAND, Y_LO]})
    shade = alt.Chart(bands).mark_rect(color=ZERO).encode(y=net_axis(look, "y0"), y2="y1:Q")
    zero = alt.Chart(alt.InlineData(values=[{"zero": 0}])).mark_rule(
        color=MUTED, strokeWidth=1.2).encode(y=alt.Y(datum=0))
    text = alt.Chart(lines).mark_text(align="left", baseline="middle", color=MUTED,
                                      fontSize=size).encode(
        x=alt.value(CAPTION_X), y=alt.Y("y:Q", scale=None), text="text:N")
    return [shade, zero, text]


def scatter_marks(look, picked, selections):
    """The bubbles, the rings and labels of the six focus countries, and the hover layer.

    `selections` are the hover selection, which lights the bubble under the pointer,
    and the selection a click sets; `picked` tests for the country shown in the top
    panel. The static plate has none of the three.
    """
    nobody = alt.datum.country == "__nobody__"
    lit = selections[0] if selections else nobody
    position = dict(x=gdp_axis(look), y=net_axis(look))
    # opacity=1 switches off Vega-Lite's default of 0.7 for point marks, which would
    # multiply with the fill opacity below and wash the three hues out.
    bubbles = alt.Chart().mark_point(filled=True, opacity=1, strokeWidth=BUBBLE_RING,
                                     strokeOpacity=1).encode(
        size=population_size(), color=income_colour(),
        shape=alt.Shape("pin:N", legend=None,
                        scale=alt.Scale(domain=["inside", "above", "below"],
                                        range=["circle", "triangle-up", "triangle-down"])),
        stroke=alt.condition(lit, alt.value(INK), alt.value(SURFACE)),
        fillOpacity=alt.condition(lit, alt.value(1.0), alt.value(0.75)),
        # Largest first, so that a small country is never hidden under a large one.
        order=alt.Order("mean_pop:Q", sort="descending"), **position)
    focus = alt.Chart().transform_filter(alt.datum.is_focus == 1)
    # The ring takes its area from the same rule as the bubble, written as an expression:
    # a second size encoding would add its unfilled symbol to the population legend.
    rings = focus.mark_point(filled=False, stroke=INK, opacity=1,
                             size=alt.expr(f"{AREA_PER_PERSON!r} * datum.size_pop")).encode(
        strokeWidth=alt.condition(picked if picked is not None else nobody, alt.value(3.2),
                                  alt.value(1.5)), **position)
    placed = dict(dx=alt.expr("datum.label_dx"), dy=alt.expr("datum.label_dy"),
                  align=alt.expr("datum.label_align"), baseline=alt.expr("datum.label_base"),
                  fontSize=12 * look["zoom"], fontWeight=600)
    halo = focus.mark_text(stroke=SURFACE, strokeWidth=3, strokeJoin="round", fill=SURFACE,
                           strokeOpacity=0.85, **placed).encode(text="label:N", **position)
    names = focus.mark_text(fill=INK, **placed).encode(text="label:N", **position)
    layers = [bubbles, rings, halo, names]
    if selections:
        # An invisible copy of the points holds the selections, which use nearest=True:
        # Vega-Lite lays a Voronoi cell over each point, so the pointer only has to be
        # closest to a bubble, never dead centre on an 8 px dot.
        targets = alt.Chart().mark_point(opacity=0, size=1, tooltip=alt.expr(BUBBLE_TIP)).encode(
            **position).properties(name="bubble_targets").add_params(*selections)
        layers.append(targets)
    return layers


def footer(look, lines):
    """Lines of small print under the x-axis; each line is (text or chart, colour)."""
    layers = []
    for i, (line, colour) in enumerate(lines):
        chart = line if isinstance(line, alt.Chart) else alt.Chart(
            alt.InlineData(values=[{"note": line}]))
        layers.append(chart.mark_text(align="left", baseline="top", color=colour,
                                      fontSize=11 * look["zoom"]).encode(
            x=alt.value(0), y=alt.value(look["height"] + (50 + 16 * i) * look["zoom"]),
            text="note:N"))
    return layers


def pinned_note(table, window):
    """A one-row chart whose `note` counts the pinned countries in the current window."""
    text = ("datum.n_off == 0 ? 'No country lies beyond the axis in this window.' : "
            "(datum.n_off == 1 ? '1 country lies' : datum.n_off + ' countries lie') + "
            "' beyond the axis in this window: triangles in the shaded bands, further out "
            "the more extreme; true value in the tooltip.'")
    return (alt.Chart(table).transform_filter(window_filter(window))
            .transform_aggregate(mean_net="mean(net_co2_per_capita)", groupby=["country"])
            .transform_calculate(off=f"datum.mean_net > {Y_HI} || datum.mean_net < {Y_LO} "
                                     f"? 1 : 0")
            .transform_aggregate(n_off="sum(off)")
            .transform_calculate(note=text))


# What differs between the scatter of the linked view and a panel of the plate: the plot
# size, the type scale, and whether the panel draws its own y-axis labels.
VIEW_LOOK = dict(width=PLOT_W, height=SCATTER_H, zoom=1.0, plate=False, labelled=True)
PLATE_LOOK = dict(width=PLATE_W, height=PLATE_H, zoom=PLATE_ZOOM, plate=True, labelled=True)


def scatter_panel(table, window, title, notes, picked=None, selections=(), look=VIEW_LOOK):
    means = averaged(alt.layer(*scatter_marks(look, picked, selections), data=table), window)
    layers = scatter_furniture(look) + [means] + footer(look, notes)
    return alt.layer(*layers).properties(width=look["width"], height=look["height"],
                                         title=title)


# ---------------------------------------------------------------- the charts
def themed(chart, zoom=1.0):
    """The chrome every view shares: one surface, three inks, hairline grid.

    The number locale replaces the typographic minus of d3-format with a plain hyphen.
    """
    return (chart
            .configure(background=SURFACE, font=FONT, padding=12,
                       locale=alt.Locale(number=alt.NumberLocale(
                           decimal=".", thousands=",", grouping=[3], currency=["$", ""],
                           minus="-")))
            .configure_view(stroke=None)
            .configure_axis(labelColor=INK_2, labelFontSize=11 * zoom, titleColor=INK_2,
                            titleFontSize=11.5 * zoom, titleFontWeight="normal",
                            titlePadding=8, gridColor=GRID, gridWidth=1, domainColor=AXIS,
                            tickColor=AXIS, labelPadding=5)
            .configure_legend(labelColor=INK_2, labelFontSize=11.5 * zoom, titleColor=INK_2,
                              titleFontSize=11.5 * zoom, titleFontWeight=600, titlePadding=6,
                              labelLimit=240, offset=14))


def main_title(text, subtitle, zoom=1.0):
    return alt.Title(text, subtitle=subtitle, anchor="start", fontSize=17 * zoom,
                     fontWeight=600, color=INK, subtitleColor=INK_2,
                     subtitleFontSize=12.5 * zoom, subtitlePadding=6, offset=16)


def build_chart(window=LATE, country="United Kingdom"):
    """The linked view. `window` is the span of years the brush starts on (None for no
    brush, which averages over all years); `country` is what the dropdown starts on."""
    series, table = series_table(), scatter_table()
    domains = y_domains(series)
    # The dropdown is a point selection bound to a select element, not a plain
    # parameter, so that a click on one of the six ringed bubbles can set it too. The
    # event filter lets through clicks on the Voronoi cell of a focus country only (a
    # click that ends a drag lands on no mark at all, hence the first test), and
    # nothing clears the selection.
    pick = alt.selection_point(
        name="pick", fields=["country"], value=[{"country": country}], nearest=True,
        bind=alt.binding_select(options=FOCUS, name="Country in the top panel "),
        on="click[event.item && event.item.isVoronoi && event.item.datum.datum.is_focus === 1]",
        clear=False, toggle=False)
    # Vega-Lite keeps the value of a selection bound to an input element in a signal
    # named <selection>_<field>. Everything that follows the dropdown reads `country`,
    # which falls back to the starting country if that signal is ever anything but one
    # of the six: the top panel cannot go empty or show all countries at once.
    shown = alt.param(name="country", expr=f"indexof({json.dumps(FOCUS)}, pick_country) >= 0 "
                                           f"? pick_country : {json.dumps(country)}")
    # Half a year of padding at each end of the x-domain lets the brush take in the
    # whole of 1990 and the whole of 2022. A single click empties the brush; the default
    # double-click clear is switched off because it would fire from the scatter as well.
    start = {"value": {"x": [window[0] - 0.5, window[1] + 0.5]}} if window else {}
    brush = alt.selection_interval(
        name="brush", encodings=["x"], zoom=False, clear=False,
        mark=alt.BrushConfig(fill=INK, fillOpacity=0.07, stroke=INK_2, strokeOpacity=0.55,
                             strokeWidth=1, cursor="ew-resize"), **start)
    hover = alt.selection_point(name="hover_country", fields=["country"], nearest=True,
                                on="pointerover", clear="pointerout", empty=False)
    limits = [alt.param(name="y_lo", expr=lookup({c: d[0] for c, d in domains.items()},
                                                 "country")),
              alt.param(name="y_hi", expr=lookup({c: d[1] for c, d in domains.items()},
                                                 "country"))]
    top = time_series_panel(series, end_labels(series, domains), shown, brush)
    title = panel_title(alt.expr(SCATTER_TITLE), subtitle=(
        f"{table['country'].nunique()} countries; the six focus countries are ringed and "
        f"named, with a heavier ring on the one shown above."))
    notes = [(pinned_note(table, brush), INK_2), (SOURCE, MUTED)]
    bottom = scatter_panel(table, brush, title, notes, picked=alt.datum.country == shown,
                           selections=(hover, pick))
    chart = alt.vconcat(top, bottom, spacing=26).add_params(shown, *limits, *brush_params())
    # Each panel has its own colour scale: measures on top, income groups below.
    chart = chart.resolve_scale(color="independent", size="independent", shape="independent")
    chart = chart.properties(title=main_title(TITLE, SUBTITLE), description=DESCRIPTION,
                             usermeta={"embedOptions": EMBED_OPTIONS})
    return themed(chart)


def pinned_lines(means):
    """For the static plate, where no tooltip can give them: the pinned countries and
    their true means, most extreme first, in lines short enough for one panel."""
    off = means[means["pin"] != "inside"].sort_values("mean_net", ascending=False)
    if off.empty:
        return ["No country lies beyond the axis in this window."]
    items = [f"{name} {row.mean_net:+.1f}" for name, row in off.iterrows()]
    lines, line = [], "Beyond the axis (t CO2 per person): "
    for i, item in enumerate(items):
        piece = item + (", " if i < len(items) - 1 else "")
        if len(line) + len(piece) > 76:
            lines.append(line.rstrip())
            line = ""
        line += piece
    return lines + [line]


def comparison_chart():
    """The scatter under the two brush positions the report compares, side by side on
    one shared y-axis. Static: the windows are fixed filters, not a brush."""
    table = scatter_table()
    panels = []
    for i, window in enumerate((EARLY, LATE)):
        means = window_means(table, window)
        name = "First ten years" if window == EARLY else "Last ten years"
        title = panel_title(f"{name}: mean over {window[0]}-{window[1]}", zoom=PLATE_ZOOM)
        notes = [(line, INK_2) for line in pinned_lines(means)]
        if i == 0:
            # A line wider than the plot would push the second panel away, so the
            # source is wrapped to the width of the first.
            notes += [("", MUTED)] + [(line, MUTED) for line in textwrap.wrap(SOURCE, 70)]
        panels.append(scatter_panel(table, window, title, notes,
                                    look=dict(PLATE_LOOK, labelled=(i == 0))))
    chart = alt.hconcat(*panels, spacing=22).properties(title=main_title(
        "The same scatter under two brush positions: 1990-1999 and 2013-2022",
        [f"Each bubble is one of {table['country'].nunique()} countries at its mean over "
         "the window; the six focus countries are ringed and named.",
         "Triangles in the shaded bands mark countries whose mean lies beyond the axis, "
         "further out the more extreme; their values are listed under each panel."],
        PLATE_ZOOM))
    return themed(chart, PLATE_ZOOM)


# ---------------------------------------------------------------- files
def svg_of(chart):
    buffer = io.StringIO()
    chart.save(buffer, format="svg")
    return buffer.getvalue()


def svg_size(svg):
    head = svg[:svg.index(">")]
    return (float(re.search(r'\swidth="([\d.]+)"', head).group(1)),
            float(re.search(r'\sheight="([\d.]+)"', head).group(1)))


def svg_texts(svg):
    """Every piece of text a reader can see in a rendered chart."""
    found = re.findall(r"<text[^>]*>(.*?)</text>", svg, flags=re.S)
    plain = [re.sub(r"<[^>]+>", " ", t) for t in found]
    return [t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
            .replace("&#39;", "'").replace("&quot;", '"').strip() for t in plain if t.strip()]


def write_png(chart, path):
    """Render through vl-convert at the scale that makes the image PNG_WIDTH wide."""
    svg = svg_of(chart)
    width, height = svg_size(svg)
    chart.save(path, format="png", scale_factor=PNG_WIDTH / width)
    return svg, (width, height)


def write_html(chart):
    """chart.save(inline=True) bundles Vega, Vega-Lite and vega-embed into the page through
    vl-convert, so the page runs from disk and inside an iframe with no network."""
    chart.save(HTML_PATH, inline=True, embed_options=EMBED_OPTIONS)
    with open(HTML_PATH, encoding="utf-8") as fh:
        html = fh.read()
    # The three places Altair's template is touched; if it ever changes shape the page
    # is left as written and the caller is told.
    patched = (html.count("</style>") == 1 and html.count(EMBED_CALL) == 1
               and html.count("<html>\n<head>") == 1)
    if patched:
        html = (html.replace("<html>\n<head>", '<html lang="en">\n<head>')
                .replace("</style>", "</style>" + PAGE_STYLE).replace(EMBED_CALL, EMBED_KEPT))
        with open(HTML_PATH, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html)
    return patched


def write_spec(spec):
    """The spec as JSON: the structure indented, each data row on a line of its own."""
    body = {k: v for k, v in spec.items() if k != "datasets"}
    text = json.dumps(body, indent=2, ensure_ascii=True)
    blocks = []
    for name, rows in spec["datasets"].items():
        lines = ",\n".join("      " + json.dumps(r, separators=(",", ":"), ensure_ascii=True)
                           for r in rows)
        blocks.append(f"    {json.dumps(name)}: [\n{lines}\n    ]")
    text = text[:text.rindex("}")].rstrip() + ',\n  "datasets": {\n' + ",\n".join(blocks)
    with open(SPEC_PATH, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n  }\n}\n")
    with open(SPEC_PATH, encoding="utf-8") as fh:
        return json.load(fh) == spec


def png_size(path):
    from PIL import Image
    with Image.open(path) as image:
        return image.size


def relative(path):
    return os.path.relpath(path, ROOT)


def note(text):
    """Print a line of detail, wrapped to LOG_WIDTH."""
    print(textwrap.fill(text, width=LOG_WIDTH, initial_indent="   ", subsequent_indent="   "))


# ---------------------------------------------------------------- checks
def check_tables(log, table, series):
    log.section("1. Tables")
    panel = load_panel()
    left_out = sorted(set(panel["country"]) - set(table["country"]))
    n_years = YEAR_MAX - YEAR_MIN + 1
    print(f"   scatter: {table['country'].nunique()} countries x {table['year'].nunique()} years"
          f" = {len(table):,} rows (decoupling_panel.csv, countries with an income group)")
    print(f"   left out, no World Bank income group: {', '.join(left_out) or 'none'}")
    print(f"   time series: {series['country'].nunique()} countries x "
          f"{series['year'].nunique()} years = {len(series)} rows (decoupling_focus.csv)")
    log.result("plotted_countries", table["country"].nunique(), 0)
    log.check("the scatter holds every panel country except Taiwan, 33 years each",
              left_out == ["Taiwan"] and len(table) == table["country"].nunique() * n_years)
    log.check("the time series holds the six focus countries, 33 years each, starting at 0",
              sorted(series["country"].unique()) == sorted(FOCUS)
              and len(series) == len(FOCUS) * n_years
              and (series[series["year"] == YEAR_MIN][list(CHANGE_COLS)].abs() < 1e-9).all().all())
    counts = table.drop_duplicates("country")["income_group"].value_counts()
    for group in INCOME_ORDER:
        log.result(f"{INCOME_TAGS[group]}_countries", counts[group], 0)
    check_end_labels(log, series)


def check_end_labels(log, series):
    """The numbers written on the top panel: one label at the end of each line."""
    summary, domains = load_summary(), y_domains(series)
    labels = end_labels(series, domains)
    gap = min(abs(a - b) / ((domains[c][1] - domains[c][0]) / TOP_H)
              for c, d in labels.groupby("country")
              for i, a in enumerate(d["label_y"]) for b in list(d["label_y"])[i + 1:])
    by = labels.set_index(["country", "measure"])["value"]
    log.check("the 18 line-end labels carry the 2022 changes in decoupling_summary.csv",
              all(abs(by[(c, CHANGE_COLS[col])] - summary.loc[c, col]) < 1e-9
                  for c in FOCUS for col in CHANGE_COLS))
    log.check(f"the labels of one country sit at least {LABEL_GAP} px apart (closest pair "
              f"{gap:.1f} px)", gap >= LABEL_GAP - 1e-6)


def check_means(log, table):
    """What the scatter must show under the two brush positions, from pandas alone."""
    log.section("2. Window means the scatter must show")
    summary = load_summary()
    means = {name: window_means(table, w) for name, w in WINDOWS.items()}
    print(f"   {'':<16}{'net balance, t CO2 per person':>33}{'GDP per capita, int-$':>30}")
    print(f"   {'country':<16}{'1990-1999':>11}{'2013-2022':>11}{'1990-2022':>11}"
          f"{'1990-1999':>12}{'2013-2022':>10}{'1990-2022':>10}")
    for country in FOCUS:
        row = [means[n].loc[country] for n in WINDOWS]
        print(f"   {country:<16}" + "".join(f"{r.mean_net:>+11.2f}" for r in row)
              + f"{row[0].mean_gdp:>12,.0f}{row[1].mean_gdp:>10,.0f}{row[2].mean_gdp:>10,.0f}")
    print()
    worst = 0.0
    for country in FOCUS:
        tag = summary.loc[country, "iso_code"].lower()
        for name in ("early", "late"):
            mine = means[name].loc[country]
            log.result(f"{tag}_net_window_{name}", mine.mean_net)
            log.result(f"{tag}_gdp_window_{name}", mine.mean_gdp, 1)
            worst = max(worst,
                        abs(mine.mean_net - summary.loc[country, f"net_pc_mean_{name}"]),
                        abs(mine.mean_gdp / summary.loc[country, f"gdp_pc_mean_{name}"] - 1))
    log.check("the focus means of both windows equal those in decoupling_summary.csv "
              f"(worst gap {worst:.1e})", worst < 1e-9)
    log.check("no focus country is ever pinned: its 198 single-year balances lie inside "
              f"{Y_LO:+.0f} to {Y_HI:+.0f} t",
              table[table["is_focus"] == 1]["net_co2_per_capita"].between(Y_LO, Y_HI).all())
    return means


def check_counts(log, table, means):
    """How many countries are pinned in each window, and how many sit above zero."""
    log.section("3. Countries beyond the axis, and on each side of zero")
    for name, window in WINDOWS.items():
        m = means[name]
        off = m[m["pin"] != "inside"].sort_values("mean_net", ascending=False)
        listed = ", ".join(f"{c} {r.mean_net:+.1f}" for c, r in off.iterrows())
        note(f"{window[0]}-{window[1]}: {len(off)} beyond the axis ({listed})")
        log.result(f"offscale_window_{name}", len(off), 0)
        log.result(f"offscale_above_window_{name}", (off["pin"] == "above").sum(), 0)
        log.result(f"offscale_below_window_{name}", (off["pin"] == "below").sum(), 0)
    print()
    print(f"   net importers (mean balance above zero)   {'1990-1999':>11}{'2013-2022':>11}"
          f"{'1990-2022':>11}{'of':>6}")
    for group in INCOME_ORDER:
        counts = [int((m[m["income_group"] == group]["mean_net"] > 0).sum())
                  for m in means.values()]
        size = int((means["all"]["income_group"] == group).sum())
        print(f"   {group:<42}" + "".join(f"{c:>11}" for c in counts) + f"{size:>6}")
        for name, count in zip(WINDOWS, counts):
            log.result(f"{INCOME_TAGS[group]}_importers_window_{name}", count, 0)
    for name, m in means.items():
        log.result(f"importers_window_{name}", (m["mean_net"] > 0).sum(), 0)
    log.check(f"all {table['country'].nunique()} countries are plotted in each of the three "
              f"windows, pinned or not",
              all(len(m) == table["country"].nunique() for m in means.values()))
    check_every_window(log, table, means)


def under_captions(gdp, net, look):
    """How many countries, placed at these means, would sit under the corner captions."""
    limit, top, bottom = caption_zone(look)
    return int(((gdp < limit) & ((net > top) | (net < bottom))).sum())


def check_every_window(log, table, means):
    """The brush can select 561 windows, from one year to all 33. Two things the layout
    counts on are checked in each: few countries leave the axis, none hides a caption."""
    net = table.pivot(index="year", columns="country", values="net_co2_per_capita")
    gdp = table.pivot(index="year", columns="country", values="gdp_per_capita")
    windows = [(lo, hi) for lo in range(YEAR_MIN, YEAR_MAX + 1)
               for hi in range(lo, YEAR_MAX + 1)]
    pinned, hidden = [], 0
    for lo, hi in windows:
        mean_net, mean_gdp = net.loc[lo:hi].mean(), gdp.loc[lo:hi].mean()
        pinned.append(int(((mean_net > Y_HI) | (mean_net < Y_LO)).sum()))
        hidden += under_captions(mean_gdp, mean_net, VIEW_LOOK)
    log.result("windows_a_brush_can_select", len(windows), 0)
    log.result("offscale_most_in_any_window", max(pinned), 0)
    log.check(f"in each of the {len(windows)} windows a brush can select, at most "
              f"{max(pinned)} of {net.shape[1]} countries leave the axis", max(pinned) <= 8)
    limit, top, bottom = caption_zone(VIEW_LOOK)
    on_plate = sum(under_captions(means[name]["mean_gdp"], means[name]["mean_net"], PLATE_LOOK)
                   for name in ("early", "late"))
    note(f"the corner captions cover GDP per capita below ${limit:,.0f} with a balance above "
         f"{top:+.1f} t or below {bottom:+.1f} t")
    log.check("no bubble or triangle sits under those captions in any window, nor on the plate",
              hidden == 0 and on_plate == 0)


def walk(node):
    """Every dict inside a spec, depth first."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def check_spec(log, spec):
    log.section("5. Structure of the Vega-Lite spec")
    check_spec_controls(log, spec)
    check_spec_scatter(log, spec)
    texts = [v for n in walk({k: v for k, v in spec.items() if k != "datasets"})
             for v in n.values() if isinstance(v, str)]
    log.check("no string in the spec outside the data holds a non-ASCII character",
              all(t.isascii() for t in texts))


def check_spec_controls(log, spec):
    """The brush and the dropdown: where they are defined and what they start on."""
    params = {p["name"]: p for p in spec.get("params", [])}
    brush = params.get("brush", {})
    log.check("the spec holds an interval selection named brush, projected on x, that starts "
              f"on {LATE[0]}-{LATE[1]}",
              brush.get("select", {}).get("type") == "interval"
              and brush["select"].get("encodings") == ["x"]
              and brush.get("value") == {"x": [LATE[0] - 0.5, LATE[1] + 0.5]})
    top = spec["vconcat"][0]
    host = [n for n in walk(top) if n.get("name") in brush.get("views", [])]
    log.check("the brush is defined on the time series, whose x-domain is padded by half a "
              "year each side",
              len(host) == 1 and host[0]["encoding"]["x"]["field"] == "year"
              and host[0]["encoding"]["x"]["scale"]["domain"] == [YEAR_MIN - 0.5, YEAR_MAX + 0.5])
    pick = params.get("pick", {})
    log.check("a dropdown bound to a parameter filters the top panel (six countries, United "
              "Kingdom first)",
              pick.get("bind", {}).get("input") == "select" and pick["bind"]["options"] == FOCUS
              and pick.get("value") == [{"country": "United Kingdom"}]
              and "pick_country" in params.get("country", {}).get("expr", "")
              and any(t.get("filter") == "(datum.country === country)"
                      for n in walk(top) for t in n.get("transform", [])))
    log.check("a click sets that parameter on a focus country only; nothing else clears it "
              "or the brush",
              "is_focus === 1" in pick.get("select", {}).get("on", "")
              and pick["select"].get("clear") is False and brush["select"].get("clear") is False)


def check_spec_scatter(log, spec):
    """The pipeline behind the bubbles and the scales they are drawn with."""
    piped = [n for n in walk(spec["vconcat"][1]) if isinstance(n.get("transform"), list)
             and any(t.get("filter") == {"param": "brush"} for t in n["transform"])]
    bubbles = [n for n in piped if "layer" in n]
    steps = bubbles[0]["transform"] if bubbles else []
    kinds = ["filter" if "filter" in t else "aggregate" if "aggregate" in t else "calculate"
             for t in steps]
    log.check("the scatter is transform_filter(brush) -> transform_aggregate(mean ..., "
              "groupby country)",
              len(bubbles) == 1 and kinds[:2] == ["filter", "aggregate"]
              and "country" in steps[1]["groupby"]
              and {(a["op"], a.get("field")) for a in steps[1]["aggregate"]} >= {
                  ("mean", "gdp_per_capita"), ("mean", "net_co2_per_capita"),
                  ("mean", "population")})
    marks = bubbles[0]["layer"][0]["encoding"] if bubbles else {}
    log.check("x is a log scale and y a linear one",
              marks.get("x", {}).get("scale", {}).get("type") == "log"
              and marks.get("y", {}).get("scale", {}).get("type") == "linear")
    colour = marks.get("color", {}).get("scale", {})
    log.check("the colour scale maps INCOME_ORDER to INCOME_COLORS, in that order",
              colour.get("domain") == INCOME_ORDER
              and colour.get("range") == [INCOME_COLORS[g] for g in INCOME_ORDER])
    size = marks.get("size", {}).get("scale", {})
    log.check("bubble area is proportional to population: a linear size scale through zero",
              size.get("type") == "linear" and size.get("domain", [1])[0] == 0
              and size.get("range", [1])[0] == 0)


def check_text(log, renders):
    """`renders` maps a label to the SVG of a chart as vl-convert drew it."""
    log.section("6. Text a reader can see")
    texts = {name: svg_texts(svg) for name, svg in renders.items()}
    everything = [t for found in texts.values() for t in found]
    print(f"   {len(everything)} text marks read back from {len(renders)} rendered charts")
    odd = sorted({ch for t in everything for ch in t if not ch.isascii()})
    log.check("every text mark is plain ASCII (hyphen for the minus sign and for ranges)",
              not odd)
    hits = sorted({w for w in BANNED for t in everything
                   if re.search(rf"\b{re.escape(w)}\b", t, flags=re.I)})
    log.check(f"none of the {len(BANNED)} barred words or phrases appears"
              + (f" (found: {', '.join(hits)})" if hits else ""), not hits)
    with open(os.path.abspath(__file__), "rb") as fh:
        log.check("this source file is ASCII and no line is longer than 100 characters",
                  all(line.isascii() and len(line.rstrip(b"\r\n")) <= 100 for line in fh))
    return texts


# ---------------------------------------------------------------- browser
# Reads the page the way a reader meets it: titles and labels from the SVG text, the
# plotted rows from the scenegraph items Vega binds to each mark element, the tooltip
# from its own element. A mark is found by its place in the layer stack.
PAGE_STATE = r"""
() => {
  const all = sel => [...document.querySelectorAll(sel)];
  const one = sel => { const e = document.querySelector(sel); return e ? e.textContent : null; };
  const box = sel => { const e = document.querySelector(sel); if (!e) return null;
                       const r = e.getBoundingClientRect();
                       return [r.left, r.top, r.width, r.height]; };
  const group = (kind, pattern) => all('g.mark-' + kind + '.role-mark').find(
      g => pattern.test(g.getAttribute('class')));
  const items = g => g ? [...g.children].map(e => [e, e.__data__]).filter(
      p => p[1] && p[1].datum) : [];
  const bubbles = items(group('symbol', /concat_1_layer_\d+_layer_0_marks/)).map(([e, d]) => {
      const r = e.getBoundingClientRect();
      return {country: d.datum.country, net: d.datum.mean_net, gdp: d.datum.mean_gdp,
              pop: d.datum.mean_pop, pin: d.datum.pin, shape: d.shape, lit: d.fillOpacity,
              cx: r.left + r.width / 2, cy: r.top + r.height / 2, r: r.width / 2}; });
  const rings = items(group('symbol', /concat_1_layer_\d+_layer_1_marks/)).map(
      ([e, d]) => ({country: d.datum.country, width: d.strokeWidth}));
  const lines = all('g.concat_0_group g.mark-line.role-mark path').map(
      p => p.__data__.mark.items.map(i => ({country: i.datum.country, measure: i.datum.measure,
                                            year: i.datum.year, value: i.datum.value})));
  const cross = items(group('rule', /concat_0_layer_5_marks/)).filter(
      ([e, d]) => d.opacity > 0).map(([e, d]) => d.datum.year);
  const text0 = all('g.concat_0_group g.mark-text.role-mark text').map(t => t.textContent);
  const text1 = all('g.concat_1_group g.mark-text.role-mark text').map(t => t.textContent);
  const tip = document.querySelector('#vg-tooltip-element');
  const menu = document.querySelector('#vis .vega-bindings select');
  return {
    top_title: one('g.concat_0_group g.role-title-text text'),
    scatter_title: one('g.concat_1_group g.role-title-text text'),
    bubbles, rings, lines, cross,
    end_labels: text0.filter(t => /%$/.test(t)),
    note: text1.find(t => /beyond the axis in this window/.test(t)) || null,
    tooltip: tip && tip.classList.contains('visible') ? all('#vg-tooltip-element tr').map(
        tr => [...tr.querySelectorAll('td')].map(td => td.textContent.trim())) : null,
    top: box('g.concat_0_group > g > path.background'),
    bottom: box('g.concat_1_group > g > path.background'),
    brush: box('g.brush_brush path'),
    menu: menu ? menu.value : null,
    menu_above: menu ? menu.getBoundingClientRect().bottom
                       <= document.querySelector('#vis svg').getBoundingClientRect().top : null,
    extent: window.vis1 ? (window.vis1.view.signal('brush').year || null) : null,
    cursor: document.querySelector('#vis').style.cursor,
  };
}
"""
SETTLE = ("async () => { if (window.vis1) await window.vis1.view.runAsync(); await new Promise("
          "done => requestAnimationFrame(() => requestAnimationFrame(done))); }")


class PageTest:
    """The exported page in Edge: real pointer events in, plotted rows out, pandas beside."""

    def __init__(self, page, log, table, series):
        self.page, self.log, self.table, self.series = page, log, table, series
        self.country, self.window = "United Kingdom", LATE

    def state(self):
        """Wait for Vega to finish the run the last event started, then read the page."""
        self.page.evaluate(SETTLE)
        return self.page.evaluate(PAGE_STATE)

    def x_of(self, state, year):
        left, _, width, _ = state["top"]
        return left + (year - (YEAR_MIN - 0.5)) / (YEAR_MAX - YEAR_MIN + 1) * width

    def drag(self, x0, x1, y, steps=12):
        """A mouse drag as a hand makes it: press, move in small steps, release."""
        self.page.mouse.move(x0, y)
        self.page.mouse.down()
        for i in range(1, steps + 1):
            self.page.mouse.move(x0 + (x1 - x0) * i / steps, y)
        self.page.mouse.up()

    def gap(self, state, means):
        """Largest difference between the rows the page plots and the pandas means:
        absolute for the balance in tonnes, relative for GDP per capita and population."""
        rows = state["bubbles"]
        if sorted(b["country"] for b in rows) != sorted(means.index):
            return float("inf")
        return max(max(abs(b["net"] - means.loc[b["country"], "mean_net"]),
                       abs(b["gdp"] / means.loc[b["country"], "mean_gdp"] - 1),
                       abs(b["pop"] / means.loc[b["country"], "mean_pop"] - 1)) for b in rows)

    def shows(self, state, window, lead):
        """One check: the title names the window and the bubbles sit at its means."""
        means = window_means(self.table, window or ALL_YEARS)
        gap = self.gap(state, means)
        pinned = int((means["pin"] != "inside").sum())
        triangles = sum(1 for b in state["bubbles"] if b["shape"] != "circle")
        counted = (state["note"] or "").split(" ")[0]
        self.window = window
        years = "-".join(str(year) for year in (window or ALL_YEARS))
        note(f"title '... {window_label(window)}'; {len(state['bubbles'])} bubbles, {triangles} "
             f"triangles; worst gap to pandas {gap:.1e}")
        return self.log.check(
            f"{lead}: the scatter shows the means of {years}" + ("" if window else ", all years"),
            state["scatter_title"] == TITLE_LEAD + window_label(window) and gap < 1e-9
            and triangles == pinned and counted == ("No" if pinned == 0 else str(pinned)))

    def top_shows(self, state, country):
        """True if the top panel draws `country` and nothing else, at the file's values."""
        points = [p for line in state["lines"] for p in line]
        want = self.series[self.series["country"] == country].set_index("year")
        column = {name: col for col, name in CHANGE_COLS.items()}
        n_years = YEAR_MAX - YEAR_MIN + 1
        return (len(state["lines"]) == len(CHANGE_COLS) and len(points) == 3 * n_years
                and all(p["country"] == country for p in points)
                and max(abs(p["value"] - want.loc[p["year"], column[p["measure"]]])
                        for p in points) < 1e-9
                and state["top_title"].startswith(country + ":") and state["menu"] == country
                and {r["country"] for r in state["rings"] if r["width"] > 2} == {country})

    def load(self, problems):
        state = self.state()
        self.log.check("both panels render, with the dropdown above them on United Kingdom and "
                       "a clean console",
                       bool(state["top"] and state["bottom"]) and state["menu_above"] is True
                       and self.top_shows(state, "United Kingdom") and not problems)
        self.shows(state, LATE, "on load")

    def hover_year(self, year):
        """Point at a year inside the brushed span, where a brush drawn above the marks
        would have swallowed the event."""
        state = self.state()
        self.page.mouse.move(self.x_of(state, year), state["top"][1] + TAB_H + 96)
        state = self.state()
        tip = dict(state["tooltip"] or [])
        row = self.series[(self.series["country"] == self.country)
                          & (self.series["year"] == year)].iloc[0]
        want = {name: f"{row[col]:+.1f}%" for col, name in CHANGE_COLS.items()}
        self.log.check(f"hovering {year}, inside the window, sets the crosshair there; tooltip "
                       + ", ".join(want.values()),
                       state["cross"] == [year] and tip.get("Year") == str(year)
                       and all(tip.get(name) == value for name, value in want.items())
                       and state["cursor"] == "crosshair")

    def brush(self, lo, hi, backwards=False):
        """Draw a new window with the mouse, from inside `lo` to inside `hi` or back."""
        state = self.state()
        before = {b["country"]: b["net"] for b in state["bubbles"]}
        y = state["top"][1] + TAB_H + 130
        ends = [self.x_of(state, lo - 0.4), self.x_of(state, hi + 0.4)]
        self.drag(*(reversed(ends) if backwards else ends), y)
        state = self.state()
        moved = sum(1 for b in state["bubbles"] if abs(b["net"] - before[b["country"]]) > 1e-6)
        way = "right to left " if backwards else ""
        ok = self.shows(state, (lo, hi), f"after a mouse drag {way}across {lo}-{hi}")
        self.log.check(f"the drag moved {moved} of the {len(before)} bubbles",
                       ok and moved > 100)

    def slide(self, years):
        """Grip the tab of the window and slide it."""
        state = self.state()
        left, top, width, _ = state["brush"]
        step = years * state["top"][2] / (YEAR_MAX - YEAR_MIN + 1)
        self.page.mouse.move(left + width / 2, top + TAB_H / 2)
        grip = self.state()["cursor"]
        self.drag(left + width / 2, left + width / 2 + step, top + TAB_H / 2)
        state = self.state()
        lo, hi = self.window[0] + years, self.window[1] + years
        ok = self.shows(state, (lo, hi), f"after sliding the window {years} years by its label")
        self.log.check(f"the slide kept the window {width:.1f} px wide; over its label the "
                       "pointer is the east-west arrow",
                       ok and abs(state["brush"][2] - width) < 0.5 and grip == "ew-resize")

    def click_bubble(self, country, changes):
        state = self.state()
        spot = next(b for b in state["bubbles"] if b["country"] == country)
        self.page.mouse.click(spot["cx"], spot["cy"])
        state = self.state()
        if changes:
            self.country = country
            self.log.check(f"clicking the ringed bubble of {country} switches the top panel "
                           "and the dropdown to it", self.top_shows(state, country))
        else:
            self.log.check(f"clicking {country}, which is not a focus country, changes nothing",
                           self.top_shows(state, self.country))

    def choose(self, country):
        self.page.select_option("#vis .vega-bindings select", country)
        state = self.state()
        last = self.series[(self.series["country"] == country)
                           & (self.series["year"] == YEAR_MAX)].iloc[0]
        labels = sorted(f"{SHORT[name]} {last[col]:+.0f}%" for col, name in CHANGE_COLS.items())
        self.country = country
        note(f"line ends after the change: {', '.join(state['end_labels'])}")
        self.log.check(f"picking {country} in the dropdown redraws the top panel for it and "
                       "leaves the window alone",
                       self.top_shows(state, country) and sorted(state["end_labels"]) == labels
                       and state["scatter_title"] == TITLE_LEAD + window_label(self.window))

    def hover_pinned(self, country):
        """A country beyond the axis: its mark is in the band, its tooltip tells the truth."""
        state = self.state()
        spot = next(b for b in state["bubbles"] if b["country"] == country)
        self.page.mouse.move(spot["cx"], spot["cy"])
        state = self.state()
        tip = dict(state["tooltip"] or [])
        mean = window_means(self.table, self.window).loc[country]
        self.log.check(f"the tooltip of {country}, a triangle in the upper band, gives its "
                       f"true mean, {mean.mean_net:+.2f} t",
                       spot["shape"] == "triangle-up" and tip.get("Country") == country
                       and tip.get("Mean net balance") == f"{mean.mean_net:+.2f} t CO2 per person"
                       and tip.get("Drawn") == "at the edge, beyond the axis")

    def hover_bubble(self, country):
        state = self.state()
        spot = next(b for b in state["bubbles"] if b["country"] == country)
        self.page.mouse.move(spot["cx"], spot["cy"])
        state = self.state()
        tip = dict(state["tooltip"] or [])
        mean = window_means(self.table, self.window).loc[country]
        lo, hi = self.window
        lit = [b["country"] for b in state["bubbles"] if b["lit"] == 1]
        self.log.check(f"hovering {country} lights its bubble; tooltip: mean net balance "
                       f"{mean.mean_net:+.2f} t over {lo}-{hi}",
                       tip.get("Country") == country and lit == [country]
                       and tip.get("Mean net balance") == f"{mean.mean_net:+.2f} t CO2 per person"
                       and tip.get("Years averaged") == f"{lo}-{hi} ({hi - lo + 1} years)")

    def capture(self):
        self.page.screenshot(path=PNG_BROWSER, full_page=True)
        size = png_size(PNG_BROWSER)
        lo, hi = self.window
        note(f"{relative(PNG_BROWSER)}: {size[0]} x {size[1]} px, taken with the brush on "
             f"{lo}-{hi}, {self.country} in the dropdown and the pointer on its bubble")
        state = self.state()
        self.log.result("browser_window_first_year", lo, 0)
        self.log.result("browser_window_last_year", hi, 0)
        summary = load_summary()
        for b in state["bubbles"]:
            if b["country"] in FOCUS:
                tag = summary.loc[b["country"], "iso_code"].lower()
                self.log.result(f"{tag}_net_window_browser", b["net"])

    def arrow_key(self, country):
        """The dropdown is a native select element, so it also answers to the keyboard."""
        self.page.focus("#vis .vega-bindings select")
        self.page.keyboard.press("ArrowDown")
        self.country = country
        self.log.check(f"with the dropdown focused, the down-arrow key moves it on to {country}",
                       self.top_shows(self.state(), country))

    def double_click(self):
        state = self.state()
        left, top, width, height = state["bottom"]
        self.page.mouse.dblclick(left + 0.12 * width, top + 0.3 * height)
        state = self.state()
        self.log.check("a double click in the scatter changes neither the window nor the country",
                       state["scatter_title"] == TITLE_LEAD + window_label(self.window)
                       and self.top_shows(state, self.country))

    def clear(self):
        state = self.state()
        self.page.mouse.click(self.x_of(state, self.window[1] + 6), state["top"][1] + TAB_H + 130)
        self.shows(self.state(), None, "after one click on the top panel")

    def narrow(self, year):
        """A brush that lies between two years holds none: the page has to say so."""
        state = self.state()
        y = state["top"][1] + TAB_H + 130
        self.drag(self.x_of(state, year + 0.6), self.x_of(state, year + 0.9), y, steps=3)
        state = self.state()
        self.log.check(f"a brush from {year + 0.6:.1f} to {year + 0.9:.1f} holds no year: the "
                       "scatter is empty and its title says why",
                       state["scatter_title"] == EMPTY_TITLE and not state["bubbles"])


def browser_session(play, log, table, series):
    """One sitting at the page, in the order a reader might try things."""
    problems = []
    browser = play.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 860, "height": 1060}, device_scale_factor=2)
    page.on("console", lambda m: m.type in ("error", "warning")
            and problems.append(f"{m.type}: {m.text}"))
    page.on("pageerror", lambda error: problems.append(f"page error: {error}"))
    page.goto(pathlib.Path(HTML_PATH).as_uri())
    page.wait_for_selector("#vis svg.marks")
    note(f"Microsoft Edge {browser.version}, headless, 860 x 1060 viewport at device scale 2; "
         "the file is opened from disk and the network is not used")
    test = PageTest(page, log, table, series)
    test.load(problems)
    test.hover_pinned("Singapore")
    test.hover_year(2016)
    test.brush(1997, 2003)
    test.slide(5)
    test.click_bubble("Germany", changes=True)
    test.click_bubble("Japan", changes=False)
    test.choose("China")
    test.hover_bubble("China")
    test.capture()
    test.arrow_key("India")
    test.double_click()
    test.clear()
    test.brush(2010, 2019, backwards=True)
    test.narrow(2004)
    for problem in problems:
        note(problem)
    log.check("no error or warning reached the console during the whole session", not problems)
    browser.close()


def browser_check(log, table, series):
    """Open web/altair_export.html in Edge through playwright, drive it with real mouse
    events and compare what it then shows with pandas. Writes the browser capture."""
    log.section("7. The page in a browser")
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as play:
            browser_session(play, log, table, series)
    except Exception as error:      # whatever stopped the browser, the log has to say so
        note(f"stopped by {type(error).__name__}: {(str(error).splitlines() or [''])[0]}")
        log.check("the browser session ran to its end", False)
        return
    print("   Verified above with real pointer events and key presses: drawing, sliding and")
    print("   clearing the brush, both hover layers, the dropdown and the click on a bubble,")
    print("   each compared with pandas. Not verified: touch input, and any browser other")
    print("   than Edge.")


# ---------------------------------------------------------------- run
def main(show_results=True, browser=True):
    """Write every output and check it. `browser=False` leaves out the session in Edge
    (and the capture it takes); `show_results=False` keeps the result lines off the screen."""
    log = Log(show_results=show_results)
    log.banner("VISUALIZATION 1 - ALTAIR LINKED VIEWS (INTERVAL BRUSH)")
    table, series = scatter_table(), series_table()
    check_tables(log, table, series)
    check_counts(log, table, check_means(log, table))

    log.section("4. Files written")
    chart = build_chart()
    spec = chart.to_dict()
    renders = {}
    for path, built in ((PNG_MAIN, chart), (PNG_EARLY, build_chart(EARLY)),
                        (PNG_LATE, build_chart(LATE)), (PNG_PLATE, comparison_chart())):
        renders[relative(path)], logical = write_png(built, path)
        size = png_size(path)
        print(f"   {relative(path):<46}{size[0]:>5} x {size[1]:<5} px"
              f"   (chart {logical[0]:.0f} x {logical[1]:.0f} px)")
    patched = write_html(chart)
    same = write_spec(spec)
    for path in (HTML_PATH, SPEC_PATH):
        print(f"   {relative(path):<46}{os.path.getsize(path) / 1024:>9.0f} KB")
    log.check("the four static plates are 2600 px wide to within 2 px",
              all(abs(png_size(p)[0] - PNG_WIDTH) <= 2
                  for p in (PNG_MAIN, PNG_EARLY, PNG_LATE, PNG_PLATE)))
    log.check("altair_spec.json parses back to the spec the chart was built from", same)
    with open(HTML_PATH, encoding="utf-8") as fh:
        html = fh.read()
    log.check("altair_export.html is self-contained: no script, stylesheet or font is loaded "
              "from a URL",
              patched and not re.search(r"<link\b|<script[^>]+\bsrc=|@import|@font-face", html))

    check_spec(log, spec)
    check_text(log, renders)
    if browser:
        browser_check(log, table, series)
    else:
        log.section("7. The page in a browser")
        print("   skipped on request: nothing about the page was verified in a browser, and")
        print(f"   {relative(PNG_BROWSER)} was not rewritten")
    ok = log.tally()
    return {"results": log.results, "passed": log.passed, "failed": log.failed, "ok": ok}


if __name__ == "__main__":
    sys.exit(0 if main(browser="--no-browser" not in sys.argv[1:])["ok"] else 1)
