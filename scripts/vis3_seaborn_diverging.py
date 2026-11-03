"""
vis3_seaborn_diverging.py -- Visualization 3: the net carbon trade balance of
the six focus countries as small multiples of a diverging area chart, drawn
with Seaborn and Matplotlib.

Input   inputs/decoupling_focus.csv      six countries x 33 years
        inputs/decoupling_summary.csv    one row per country; the labels are checked against it

Output  screenshots/03_vis3_seaborn_diverging.png   six facets, t CO2 per person, shared axes
        screenshots/03a_vis3_derivation_plate.png   how one facet is derived (United Kingdom)
        screenshots/03b_vis3_absolute_balance.png   the same balance in Mt CO2 for three years

The balance is consumption-based minus production-based CO2. Above zero a
country consumes more CO2 than it emits (a net importer, blue); below zero it
emits more than it consumes (a net exporter, orange).

Every figure is 13 in wide and saved at 200 dpi (2600 px) for a 6.5 in slot in
the report, so sizes are written as they print and scaled by two: px() takes a
length in CSS pixels at the printed size, pt() a type size in points.

A notebook can import this file and call load_data(), main_figure(),
derivation_plate() or absolute_figure(). Each figure function returns the
Matplotlib Figure and saves it only when asked. main() draws and saves all
three, reads the plotted artists and the saved PNGs back, and prints
'check: ... PASS' lines on them and 'result: name = value' lines for the
numbers the report quotes; it exits non-zero if a check fails.

Run:  python scripts/vis3_seaborn_diverging.py
      (run_all.py runs it as well and keeps the output in
      screenshots/logs/vis3_seaborn_diverging.txt)
"""
import functools
import io
import math
import os
import re
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matplotlib
if __name__ == "__main__":      # leave a notebook's inline backend alone
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib import font_manager
from matplotlib.collections import PolyCollection
from matplotlib.colors import to_hex, to_rgb
from matplotlib.legend_handler import HandlerBase
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, HPacker, TextArea, VPacker
from matplotlib.patches import Patch, Rectangle
from matplotlib.path import Path
from matplotlib.text import Text
from matplotlib.transforms import Affine2D, Bbox
from PIL import Image

from common import (AXIS, BASE_YEAR, CONSUMPTION, EXPORTER, FOCUS, FOCUS_CSV, FONT_STACK, GRID,
                    IMPORTER, INK, INK_2, MUTED, PIVOT_YEAR, PRODUCTION, ROOT, SHOTS, SURFACE,
                    YEAR_MAX, YEAR_MIN, Log, load_focus, load_summary)

MAIN_PNG = "03_vis3_seaborn_diverging.png"
PLATE_PNG = "03a_vis3_derivation_plate.png"
BARS_PNG = "03b_vis3_absolute_balance.png"

VALUE = "net_co2_per_capita"        # t CO2 per person, consumption minus production
TOTAL = "net_co2_mt"                # Mt CO2, the same balance for the whole country
PROD, CONS = "co2_per_capita", "consumption_co2_per_capita"
PLATE_COUNTRY = "United Kingdom"
BAR_YEARS = (BASE_YEAR, PIVOT_YEAR, YEAR_MAX)
BAR_NOTES = ("first year", "before the financial crisis", "latest year")
X_TICKS = (YEAR_MIN, 2000, 2010, YEAR_MAX)      # both ends and the round decades between
SOURCE = ("Source: Our World in Data, CO2 and Greenhouse Gas Emissions dataset "
          "(Global Carbon Budget 2025).")

# ---------------------------------------------------------------- sizes
DPI = 200
FIG_W = 13.0            # in; FIG_W x DPI = 2600 px
PRINT_W = 6.5           # in; the width the report gives each figure
SCALE = FIG_W / PRINT_W


def px(n):
    """n CSS pixels at the printed size (1 px = 0.75 pt), in points on the canvas."""
    return n * 0.75 * SCALE


def pt(n):
    """A type size of n points at the printed size, in points on the canvas."""
    return n * SCALE


# Type at the printed size: title 12 pt, subtitle 8, facet title 9, labels and
# legend 7.5, tick labels 7, source note 6.5.
T_TITLE, T_SUB, T_FACET, T_LABEL, T_TICK, T_NOTE = pt(12), pt(8), pt(9), pt(7.5), pt(7), pt(6.5)

LINE = px(2)                        # data lines
HAIR = px(1)                        # gridlines
BASE = px(1.5)                      # zero baseline: one step heavier than the grid
DOT = px(8)                         # visible diameter of a labelled point
RING = px(2)                        # surface-colour ring that lifts a point off the line
REACH = DOT / 2 + RING              # centre of a point to the outside of its ring
GAP = REACH + px(3)                 # centre of a point to a label beside it
LIFT = REACH + px(1)                # centre of a point to a label above or below it
ROOM = LIFT + T_LABEL * 1.2 + px(2)     # what such a label needs beyond its point
FILL_ALPHA = 0.42                   # a medium wash: the hue reads, the gridlines show through
BAR = px(13)                        # bar thickness, well under the 24 px cap
BAR_RADIUS = px(4)                  # rounded data end of a bar
AIR = px(10)                        # between the y tick labels and a label left of a line
MARGIN = 0.30                       # in; left edge shared by title, subtitle, legend, source

# Layout boxes in inches on the canvas: the figure height, the margins around
# the block of axes and the gaps inside it.
MAIN = dict(height=9.9, left=0.98, right=0.34, top=2.42, bottom=1.24, wgap=0.12, hgap=0.72)
PLATE = dict(height=6.6, left=0.80, right=0.34, top=2.42, bottom=1.24, gutter=0.80)
BARS = dict(height=6.2, left=1.86, right=0.30, top=2.42, bottom=0.98, wgap=0.20)


# ---------------------------------------------------------------- style
@functools.lru_cache(maxsize=None)
def font_family():
    """The first family of the shared stack that is installed on this machine.

    One concrete name is handed to Matplotlib instead of the whole stack, so
    text created here keeps its font when the figure is drawn later under
    someone else's rcParams (a notebook draws after the function has returned).
    """
    for name in FONT_STACK:
        try:
            font_manager.findfont(font_manager.FontProperties(family=name),
                                  fallback_to_default=False)
            return name
        except ValueError:
            continue
    return "sans-serif"


def house_style():
    """The rcParams of the three figures, as a context manager."""
    return matplotlib.rc_context({
        "font.family": [font_family()], "font.size": T_LABEL, "text.color": INK,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "axes.grid": False,
        "lines.linewidth": LINE, "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
        "legend.frameon": False,
    })


def styled(build):
    """Run a figure builder under house_style(), leaving the caller's rcParams as they were."""
    @functools.wraps(build)
    def wrapper(*args, **kwargs):
        with house_style():
            return build(*args, **kwargs)
    return wrapper


def signed(value, places=2):
    """'+1.49', '-0.90', '-1,285': the sign always shown, and never a '-0.00'."""
    return f"{round(float(value), places) + 0.0:+,.{places}f}"


def signed_tick(value):
    """Tick label of a balance axis: '+2', '-2', and a bare '0' for the baseline."""
    return "0" if value == 0 else signed(value, 0)


def frac(fig, x_in, top_in):
    """Figure fractions of a point given in inches from the left and from the top."""
    width, height = fig.get_size_inches()
    return x_in / width, 1 - top_in / height


# ---------------------------------------------------------------- data
def load_data():
    """The focus table (six countries x 33 years) and the one-row-per-country summary."""
    return load_focus(), load_summary()


def series(table, country, column):
    """One country's column as (years, values), in year order."""
    d = table[table["country"] == country].sort_values("year")
    return d["year"].to_numpy(), d[column].to_numpy(float)


def sign_runs(years, values):
    """Split a series into runs of one sign: [(first x, last x, sign), ...].

    The series is read as straight segments between years, so a run ends where
    a segment crosses zero, not at the nearest whole year.
    """
    x, y = np.asarray(years, float), np.asarray(values, float)
    sign = np.sign(y)
    for i in range(1, len(sign)):           # a point exactly on zero stays in the run it is in
        if sign[i] == 0:
            sign[i] = sign[i - 1]
    for i in range(len(sign) - 2, -1, -1):
        if sign[i] == 0:
            sign[i] = sign[i + 1]
    turn = np.flatnonzero(sign[:-1] != sign[1:])
    cross = x[turn] + (x[turn + 1] - x[turn]) * y[turn] / (y[turn] - y[turn + 1])
    edges = np.concatenate([x[:1], cross, x[-1:]])
    signs = sign[np.concatenate([[0], turn + 1])]
    return [(float(a), float(b), int(s)) for a, b, s in zip(edges[:-1], edges[1:], signs)]


def labelled_points(years, values):
    """The points a facet labels: the first year, the last year and, when it is
    neither of those, the year furthest from zero."""
    last = len(values) - 1
    extreme = int(np.argmax(np.abs(values)))
    picks = [("start", 0), ("end", last)] + ([("extreme", extreme)] if 0 < extreme < last else [])
    return [(kind, int(years[i]), float(values[i])) for kind, i in picks]


def nice_ticks(values, step):
    """Multiples of step inside the range the data spans, zero included: a
    gridline beyond the data would only run into the labels placed there."""
    low, high = min(float(np.min(values)), 0.0), max(float(np.max(values)), 0.0)
    return [float(t) for t in np.arange(step * math.ceil(low / step), high + 1e-9, step)]


def balance_limits(values, height_pt, room_pt=ROOM):
    """y-limits that leave room_pt points beyond the largest and the smallest
    value (or beyond zero), for the label above a peak or below a trough."""
    low, high = min(float(np.min(values)), 0.0), max(float(np.max(values)), 0.0)
    span = (high - low) / (1 - 2 * room_pt / height_pt)
    room = room_pt * span / height_pt
    return low - room, high + room


# ---------------------------------------------------------------- marks
def span_path(spans):
    """Clip path for one sign of a line: a tall rectangle over each run of years.

    x is in data units and y in axes fractions.
    """
    boxes = [Path.unit_rectangle().transformed(Affine2D().scale(b - a, 3).translate(a, -1))
             for a, b in spans]
    return Path.make_compound_path(*boxes)


def draw_frame(ax, ticks):
    """Hairline gridlines over the data years only, and a heavier zero baseline.

    The lines stop at the first and last year so that the labels beside the
    series sit on clean surface with nothing struck through them.
    """
    ax.hlines([t for t in ticks if t != 0], YEAR_MIN, YEAR_MAX, colors=GRID, linewidth=HAIR,
              zorder=1, gid="grid")
    ax.hlines(0, YEAR_MIN, YEAR_MAX, colors=AXIS, linewidth=BASE, zorder=3, gid="zero")


def draw_balance(ax, years, values):
    """The diverging area of one series: a wash between zero and the line, blue
    above zero and orange below, with a 2 px line on top in the same hue.

    fill_between(where=, interpolate=True) ends each polygon where the series
    crosses zero. The line keeps all its points in each colour and is clipped
    to the runs of years in which the balance has that colour's sign, so its
    y-data can be read back whole.
    """
    x, y = np.asarray(years, float), np.asarray(values, float)
    runs = sign_runs(x, y)
    # Only the two ends of the series are widened, so the round caps at the first and
    # the last year survive the clip; a run that ends at a crossing stops there.
    runs[0] = (runs[0][0] - 1.0,) + runs[0][1:]
    runs[-1] = runs[-1][:1] + (runs[-1][1] + 1.0,) + runs[-1][2:]
    for color, name, side, keep in ((IMPORTER, "importer", 1, y >= 0),
                                    (EXPORTER, "exporter", -1, y <= 0)):
        spans = [(a, b) for a, b, s in runs if s == side]
        if not spans:
            continue
        ax.fill_between(x, 0, y, where=keep, interpolate=True, facecolor=color, alpha=FILL_ALPHA,
                        linewidth=0, zorder=2, gid=name)
        line, = ax.plot(x, y, color=color, linewidth=LINE, zorder=4, gid=name)
        line.set_clip_path(span_path(spans), ax.get_xaxis_transform())


def draw_dot(ax, x, y, color):
    """A labelled point: 8 px across with a 2 px ring in the surface colour."""
    ax.plot([x], [y], linestyle="none", marker="o", markersize=DOT + RING, markerfacecolor=color,
            markeredgecolor=SURFACE, markeredgewidth=RING, zorder=5, gid="dot")


def words(*parts):
    """Text areas for (text, weight, colour) triples."""
    return [TextArea(text, textprops=dict(fontsize=T_LABEL, fontweight=weight, color=color))
            for text, weight, color in parts]


def side_label(ax, x, y, text, gid, nudge=0.0):
    """A value to the left of a line's first point, at the height of the point."""
    return ax.annotate(text, (x, y), xytext=(-GAP, nudge), textcoords="offset points", ha="right",
                       va="center_baseline", fontsize=T_LABEL, fontweight="semibold", color=INK,
                       zorder=6, annotation_clip=False, gid=gid)


def point_label(ax, x, y, parts, gid, anchor=0.5):
    """A label above a point of an importer or below a point of an exporter:
    always on the side away from the wash.

    anchor is where the point sits along the label: 0.5 centres the label on
    it, 1.0 ends the label at the right edge of the point. These labels lie
    over the gridlines; clear_gridlines() blanks the hairlines behind them.
    """
    up = 1 if y >= 0 else -1
    row = HPacker(children=words(*parts), align="baseline", pad=0, sep=px(3))
    box = AnnotationBbox(row, (x, y), xybox=((2 * anchor - 1) * REACH, up * LIFT),
                         xycoords="data", boxcoords="offset points",
                         box_alignment=(anchor, 0 if up > 0 else 1), frameon=False, pad=0,
                         annotation_clip=False, zorder=6)
    box.set_gid(gid)
    return ax.add_artist(box)


def label_balance(ax, years, values, unit):
    """Dots and direct labels for the first year, the last year and the extreme.

    The first value hangs to the left of the series, where no line can reach
    it; the last value and the extreme sit above or below their points. The
    unit is given once, on the last value.
    """
    for kind, year, value in labelled_points(years, values):
        draw_dot(ax, year, value, IMPORTER if value >= 0 else EXPORTER)
        if kind == "start":
            side_label(ax, year, value, signed(value), "start")
        elif kind == "end":
            point_label(ax, year, value, [(f"{signed(value)} {unit}", "semibold", INK)], "end",
                        anchor=1.0)
        else:
            point_label(ax, year, value, [(signed(value), "semibold", INK),
                                          (f"in {year}", "normal", MUTED)], "extreme")


class WashKey(HandlerBase):
    """Legend key that mirrors the area mark: the wash with its line on the edge
    away from zero (the top for an importer, the bottom for an exporter)."""

    def __init__(self, edge):
        super().__init__()
        self.edge = edge

    def create_artists(self, legend, handle, xdescent, ydescent, width, height, fontsize, trans):
        color = handle.get_facecolor()[:3]
        wash = Rectangle((-xdescent, -ydescent), width, height, facecolor=color, alpha=FILL_ALPHA,
                         edgecolor="none", transform=trans)
        y = -ydescent + (height if self.edge == "top" else 0)
        line = Line2D([-xdescent, width - xdescent], [y, y], color=color, linewidth=LINE,
                      solid_capstyle="butt", transform=trans)
        return [wash, line]


class DataEndBar(Patch):
    """A horizontal bar from zero to its value: square at the baseline, rounded
    at the data end.

    The thickness and the corner radius are lengths on paper while the bar
    lives in data coordinates, so the outline is rebuilt from the axis scales
    in force each time it is drawn.
    """

    def __init__(self, value, row, thickness=BAR, radius=BAR_RADIUS, **kwargs):
        super().__init__(**kwargs)
        self.value, self.row, self.thickness, self.radius = float(value), row, thickness, radius

    def get_path(self):
        to_px = self.axes.transData.transform
        origin = to_px((0.0, self.row))
        per_x = abs(to_px((1.0, self.row))[0] - origin[0])          # pixels per data unit
        per_y = abs(to_px((0.0, self.row + 1.0))[1] - origin[1])    # pixels per row
        per_pt = self.get_figure(root=True).dpi / 72.0
        half = self.thickness * per_pt / 2 / per_y
        ry = min(self.radius * per_pt / per_y, half)
        rx = math.copysign(min(self.radius * per_pt / per_x, abs(self.value)), self.value)
        v, lo, hi, k = self.value, self.row - half, self.row + half, 0.5523      # k: circular arc
        verts = [(0, lo), (v - rx, lo), (v - rx + k * rx, lo), (v, lo + ry - k * ry), (v, lo + ry),
                 (v, hi - ry), (v, hi - ry + k * ry), (v - rx + k * rx, hi), (v - rx, hi),
                 (0, hi), (0, lo)]
        codes = [Path.MOVETO, Path.LINETO, Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO,
                 Path.CURVE4, Path.CURVE4, Path.CURVE4, Path.LINETO, Path.CLOSEPOLY]
        return Path(verts, codes)


# ---------------------------------------------------------------- figure furniture
def place(fig, box, ncol, nrow):
    """Put a facet grid inside margins given in inches, replacing seaborn's tight
    layout; returns the width and height of one facet in inches."""
    width, height = fig.get_size_inches()
    ax_w = (width - box["left"] - box["right"] - (ncol - 1) * box["wgap"]) / ncol
    ax_h = (height - box["top"] - box["bottom"] - (nrow - 1) * box.get("hgap", 0)) / nrow
    fig.subplots_adjust(left=box["left"] / width, right=1 - box["right"] / width,
                        bottom=box["bottom"] / height, top=1 - box["top"] / height,
                        wspace=box["wgap"] / ax_w, hspace=box.get("hgap", 0) / ax_h)
    return ax_w, ax_h


def heading(fig, title, subtitle):
    """Title and subtitle, left-aligned at the figure margin."""
    x, y = frac(fig, MARGIN, 0.26)
    fig.suptitle(title, x=x, y=y, ha="left", va="top", fontsize=T_TITLE, fontweight="bold",
                 color=INK)
    x, y = frac(fig, MARGIN, 0.86)
    fig.text(x, y, subtitle, ha="left", va="top", fontsize=T_SUB, color=INK_2, linespacing=1.35,
             gid="subtitle")


def legend_row(fig, handles, handler_map=None, top_in=1.60):
    """One-row legend under the subtitle; its labels are in ink, never in a data colour."""
    x, y = frac(fig, MARGIN, top_in)
    return fig.legend(handles=handles, handler_map=handler_map, loc="upper left",
                      bbox_to_anchor=(x, y), ncols=len(handles), frameon=False, borderpad=0,
                      borderaxespad=0, handlelength=1.5, handleheight=0.8, handletextpad=0.55,
                      columnspacing=2.2, fontsize=T_LABEL, labelcolor=INK_2)


def sign_legend(fig, wash=True):
    """The two-entry sign legend: a wash with its line for the areas, solid for the bars."""
    importer = Patch(facecolor=IMPORTER, edgecolor="none",
                     label="Net importer - consumes more CO2 than it emits")
    exporter = Patch(facecolor=EXPORTER, edgecolor="none",
                     label="Net exporter - emits more than it consumes")
    handlers = {importer: WashKey("top"), exporter: WashKey("bottom")} if wash else None
    return legend_row(fig, [importer, exporter], handlers)


def source_note(fig, text):
    """Source and definitions in small muted type at the foot of the figure."""
    fig.text(MARGIN / fig.get_figwidth(), 0.20 / fig.get_figheight(), text, ha="left", va="bottom",
             fontsize=T_NOTE, color=MUTED, linespacing=1.35, gid="source")


def quiet_ticks(ax, left, bottom):
    """Tick labels in muted type and no tick marks; the gridlines do the pointing."""
    ax.tick_params(axis="both", length=0, labelsize=T_TICK, labelcolor=MUTED,
                   labelfontfamily=font_family(), labelleft=left, labelbottom=bottom)
    ax.tick_params(axis="x", pad=px(6))
    ax.tick_params(axis="y", pad=px(4))


def facet_header(ax, name, note):
    """Facet title in bold ink at the left; its muted note is added by header_notes()."""
    title = ax.set_title(name, loc="left", pad=px(6), fontsize=T_FACET, fontweight="bold",
                         color=INK)
    return ax, title, note


def header_notes(fig, headers):
    """Write each facet's muted note beside its title, on the same baseline.

    The note starts where the title ends, which is known only once the title
    has been laid out, so this runs after a draw.
    """
    fig.draw_without_rendering()
    for ax, title, note in headers:
        end = ax.transAxes.inverted().transform((title.get_window_extent().x1, 0))[0]
        gap = px(6) / 72 / (ax.get_position().width * fig.get_figwidth())
        ax.text(end + gap, 1.0, note, transform=title.get_transform(), ha="left", va="baseline",
                fontsize=T_LABEL, color=MUTED, gid="header note")


def tagged(ax, gid):
    """The artists of an Axes that were given this gid."""
    return [a for a in ax.get_children() if a.get_gid() == gid]


def zone(fig, artists, reach=GAP, air=px(3)):
    """Inches a set of labels needs beside the series: the widest of them, its
    distance from the point and some air. Call after a draw."""
    widest = max(a.get_window_extent().width for a in artists) / fig.dpi
    return widest + (reach + air) / 72


def fit_years(ax, width_in, left_in, right_in):
    """x-limits that leave left_in and right_in inches of an Axes width_in wide
    free beside the first and the last year; returns inches per year."""
    per_year = (width_in - left_in - right_in) / (YEAR_MAX - YEAR_MIN)
    ax.set_xlim(YEAR_MIN - left_in / per_year, YEAR_MAX + right_in / per_year)
    return per_year


def keep_inside(fig, ax):
    """Slide the label of an extreme sideways until it lies between the first
    and the last year. Call after a draw."""
    for box in tagged(ax, "extreme"):
        extent = box.get_window_extent()
        low = ax.transData.transform((YEAR_MIN, 0))[0]
        high = ax.transData.transform((YEAR_MAX, 0))[0]
        shift = max(low - extent.x0, 0) + min(high - extent.x1, 0)
        box.xybox = (box.xybox[0] + shift * 72 / fig.dpi, box.xybox[1])
        box.stale = True


def clear_gridlines(fig, axes, pad=px(2), bridge=0.75):
    """Blank the gridlines behind the labels that sit above or below a point.

    Each label gets a patch in the surface colour, drawn over the gridlines
    and under every mark, so it can hide a hairline but never data. Where two
    labels on the same level are less than bridge inches apart, the gap
    between them is blanked as well: the scrap of gridline left there would
    read as a dash. Call after the last change to the layout.
    """
    fig.draw_without_rendering()
    for ax in axes:
        boxes = sorted((a.get_window_extent().padded(pad * fig.dpi / 72)
                        for a in tagged(ax, "extreme") + tagged(ax, "end")), key=lambda b: b.x0)
        gaps = [Bbox.from_extents(a.x1, max(a.y0, b.y0), b.x0, min(a.y1, b.y1))
                for a, b in zip(boxes[:-1], boxes[1:])]
        boxes += [g for g in gaps if 0 < g.width < bridge * fig.dpi and g.height > 0]
        for box in boxes:
            (x0, y0), (x1, y1) = ax.transData.inverted().transform(box.get_points())
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=SURFACE,
                                   edgecolor="none", zorder=1.5, clip_on=False, gid="knockout"))


# ---------------------------------------------------------------- main figure
def facet_balance(data, value, ticks, unit, **_):
    """FacetGrid.map_dataframe target: one country's rows arrive as data."""
    d = data.sort_values("year")
    ax = plt.gca()
    draw_frame(ax, ticks)
    draw_balance(ax, d["year"].to_numpy(), d[value].to_numpy(float))
    label_balance(ax, d["year"].to_numpy(), d[value].to_numpy(float), unit)


@styled
def build_main(focus):
    """The six-facet figure and the FacetGrid that main() reads back: (figure, grid)."""
    box, ncol = MAIN, 3
    nrow = math.ceil(len(FOCUS) / ncol)
    data = focus[["country", "year", "income_group", VALUE]]
    grid = sns.FacetGrid(data, col="country", col_order=FOCUS, col_wrap=ncol, sharex=True,
                         sharey=True, height=box["height"] / nrow,
                         aspect=(FIG_W / ncol) / (box["height"] / nrow), despine=False)
    fig = grid.figure
    ticks = nice_ticks(data[VALUE], 2)
    grid.map_dataframe(facet_balance, value=VALUE, ticks=ticks, unit="t")
    ax_w, ax_h = place(fig, box, ncol, nrow)    # after map_dataframe, which ends in a tight layout
    grid.despine(left=True, bottom=True)
    grid.set_titles(col_template="")            # seaborn's default "country = ..." titles
    axes = [grid.axes_dict[country] for country in FOCUS]
    axes[0].set_ylim(balance_limits(data[VALUE], ax_h * 72))    # the axes are shared: set once
    axes[0].set_yticks(ticks, [signed_tick(t) for t in ticks])
    axes[0].set_xticks(X_TICKS, [str(t) for t in X_TICKS])
    groups = data.drop_duplicates("country").set_index("country")["income_group"]
    headers = []
    for i, (country, ax) in enumerate(zip(FOCUS, axes)):
        quiet_ticks(ax, left=i % ncol == 0, bottom=i >= len(FOCUS) - ncol)
        headers.append(facet_header(ax, country, groups[country]))

    fig.draw_without_rendering()                # the labels can be measured from here on
    fit_years(axes[0], ax_w, zone(fig, [a for ax in axes for a in tagged(ax, "start")], air=AIR),
              (REACH + px(2)) / 72)
    header_notes(fig, headers)
    for ax in axes:
        keep_inside(fig, ax)
    clear_gridlines(fig, axes)

    heading(fig, "Four rich countries are net CO2 importers; China and India are net exporters",
            f"Net balance of CO2 embodied in trade, tonnes per person, {YEAR_MIN}-{YEAR_MAX}: "
            "consumption-based minus production-based emissions.\n"
            "Above zero and blue, a net importer; below zero and orange, a net exporter. "
            "All six panels share one vertical scale.")
    sign_legend(fig)
    middle = 1 - (box["top"] + (box["height"] - box["top"] - box["bottom"]) / 2) / box["height"]
    fig.supylabel("Net balance, t CO2 per person", x=0.33 / FIG_W, y=middle, ha="center",
                  va="center", fontsize=T_LABEL, color=INK_2)
    source_note(fig, f"{SOURCE} Income groups: World Bank, folded to three classes.\n"
                     "Net balance = consumption-based minus production-based CO2 per person. "
                     f"Labels mark {YEAR_MIN}, {YEAR_MAX} and the year furthest from zero.")
    return fig, grid


# ---------------------------------------------------------------- derivation plate
def draw_accounts(ax, years, prod, cons):
    """Both accounts as lines, the gap between them washed in the colour of its sign."""
    x = np.asarray(years, float)
    for color, keep in ((IMPORTER, cons >= prod), (EXPORTER, cons <= prod)):
        if (cons != prod)[keep].any():
            ax.fill_between(x, prod, cons, where=keep, interpolate=True, facecolor=color,
                            alpha=FILL_ALPHA, linewidth=0, zorder=2, gid="gap")
    for values, color, gid in ((prod, PRODUCTION, "production"),
                               (cons, CONSUMPTION, "consumption")):
        ax.plot(x, values, color=color, linewidth=LINE, zorder=4, gid=gid)


def label_accounts(ax, years, prod, cons):
    """Dots at both ends of both lines; values on the left, name and value on the right.

    The name of the upper line goes above its value and the name of the lower
    line below, so the two labels open away from each other.
    """
    for values, other, color, name in ((cons, prod, CONSUMPTION, "Consumption-based"),
                                       (prod, cons, PRODUCTION, "Production-based")):
        for i in (0, -1):
            draw_dot(ax, years[i], values[i], color)
        # The two start values are a line of type apart; a nudge keeps them from touching.
        side_label(ax, years[0], values[0], f"{values[0]:.2f}", "start",
                   nudge=px(1.5) * (1 if values[0] >= other[0] else -1))
        upper = values[-1] >= other[-1]
        parts = [(name, "normal", INK_2), (f"{values[-1]:.2f} t", "semibold", INK)]
        stack = VPacker(children=words(*(parts if upper else parts[::-1])), align="left", pad=0,
                        sep=px(1))
        box = AnnotationBbox(stack, (years[-1], values[-1]), xybox=(GAP, 0), xycoords="data",
                             boxcoords="offset points", box_alignment=(0, 0.25 if upper else 0.75),
                             frameon=False, pad=0, annotation_clip=False, zorder=6)
        box.set_gid("end")
        ax.add_artist(box)


def moved(first, last):
    """'fell by 57%' or 'rose by 12%' for a change between two levels."""
    change = 100.0 * (last / first - 1.0)
    return f"{'fell' if change < 0 else 'rose'} by {abs(change):.0f}%"


def plate_panels(fig, box, years, prod, cons, net):
    """The two Axes of the plate with their marks, labels and ticks; where they
    sit along the page is settled afterwards, by same_year_width()."""
    bottom, height = box["bottom"], box["height"] - box["top"] - box["bottom"]
    accounts = fig.add_axes([0.1, bottom / box["height"], 0.3, height / box["height"]])
    gap = fig.add_axes([0.6, bottom / box["height"], 0.3, height / box["height"]])
    sns.despine(fig=fig, left=True, bottom=True)

    ticks = nice_ticks(np.concatenate([prod, cons]), 2)
    draw_frame(accounts, ticks)
    draw_accounts(accounts, years, prod, cons)
    label_accounts(accounts, years, prod, cons)
    top = max(prod.max(), cons.max())
    accounts.set_ylim(-0.03 * top, 1.07 * top)      # zero-based, with air above the higher line
    accounts.set_yticks(ticks, [f"{t:g}" for t in ticks])

    ticks = nice_ticks(net, 1)
    draw_frame(gap, ticks)
    draw_balance(gap, years, net)
    label_balance(gap, years, net, "t")
    low, high = balance_limits(net, height * 72)
    if float(np.min(net)) >= 0:
        # Nothing to label below zero: keep the span, and so the ratio of the two
        # scales, but put the zero line at the height it has in the left panel.
        span = high - low
        low = -0.03 / 1.10 * span
        high = low + span
    gap.set_ylim(low, high)
    gap.set_yticks(ticks, [signed_tick(t) for t in ticks])

    for ax in (accounts, gap):
        ax.set_xticks(X_TICKS, [str(t) for t in X_TICKS])
        quiet_ticks(ax, left=True, bottom=True)
    return accounts, gap


def same_year_width(fig, box, accounts, gap):
    """Place the two panels so that a year is as wide in one as in the other.

    The gap then keeps its shape from the left panel to the right one. What
    differs between them is the room their labels need: the left panel names
    its lines at the right, the right panel does not.
    """
    fig.draw_without_rendering()
    zones = [(zone(fig, tagged(accounts, "start"), air=AIR), zone(fig, tagged(accounts, "end"))),
             (zone(fig, tagged(gap, "start"), air=AIR), (REACH + px(2)) / 72)]
    free = FIG_W - box["left"] - box["right"] - box["gutter"]
    years_w = (free - sum(left + right for left, right in zones)) / 2
    x0 = box["left"]
    for ax, (left, right) in zip((accounts, gap), zones):
        old = ax.get_position()
        width = years_w + left + right
        ax.set_position([x0 / FIG_W, old.y0, width / FIG_W, old.height])
        fit_years(ax, width, left, right)
        x0 += width + box["gutter"]


def plate_words(fig, country, prod, cons, net):
    """Title, subtitle, legend and source of the plate; the subtitle's numbers
    and its verbs come from the data."""
    wider = "widened" if abs(net[-1]) > abs(net[0]) else "narrowed"
    heading(fig, f"From two CO2 accounts to one balance: the {country}",
            f"Between {YEAR_MIN} and {YEAR_MAX} production-based CO2 per person "
            f"{moved(prod[0], prod[-1])} and consumption-based CO2 {moved(cons[0], cons[-1])}.\n"
            f"The gap between them {wider} from {abs(net[0]):.2f} t ({cons[0]:.2f} - {prod[0]:.2f})"
            f" to {abs(net[-1]):.2f} t ({cons[-1]:.2f} - {prod[-1]:.2f}); "
            "the right panel draws that gap from zero.")
    handles = [Line2D([], [], color=CONSUMPTION, linewidth=LINE, label="Consumption-based"),
               Line2D([], [], color=PRODUCTION, linewidth=LINE,
                      label="Production-based (territorial)")]
    if (net > 0).any():
        handles.append(Patch(facecolor=IMPORTER, alpha=FILL_ALPHA, edgecolor="none",
                             label="Gap where consumption is higher: a net importer"))
    if (net < 0).any():
        handles.append(Patch(facecolor=EXPORTER, alpha=FILL_ALPHA, edgecolor="none",
                             label="Gap where production is higher: a net exporter"))
    legend_row(fig, handles)
    source_note(fig, f"{SOURCE}\nProduction-based: emitted on the country's territory. "
                     "Consumption-based: adjusted for the CO2 embodied in imports and exports.")


@styled
def build_plate(focus):
    """Two panels for one country: both accounts with the gap between them
    shaded, then that gap alone as the diverging area of the main figure.
    Returns (figure, (left axes, right axes))."""
    years, prod = series(focus, PLATE_COUNTRY, PROD)
    _, cons = series(focus, PLATE_COUNTRY, CONS)
    _, net = series(focus, PLATE_COUNTRY, VALUE)
    fig = plt.figure(figsize=(FIG_W, PLATE["height"]))
    accounts, gap = plate_panels(fig, PLATE, years, prod, cons, net)
    same_year_width(fig, PLATE, accounts, gap)
    header_notes(fig, [facet_header(accounts, "Two accounts", "t CO2 per person"),
                       facet_header(gap, "The gap between them", "enlarged scale")])
    keep_inside(fig, gap)
    clear_gridlines(fig, [gap])
    plate_words(fig, PLATE_COUNTRY, prod, cons, net)
    return fig, (accounts, gap)


# ---------------------------------------------------------------- absolute balance
def facet_bars(data, value, **_):
    """FacetGrid.map_dataframe target: one year's six balances as horizontal bars.

    Every bar carries its value at the tip, which is why the panel has no
    value axis; the unit is given once, on the top row.
    """
    ax = plt.gca()
    balance = data.assign(country=data["country"].astype(str)).set_index("country")[value]
    for row, country in enumerate(FOCUS):
        amount = float(balance[country])
        side = 1 if amount >= 0 else -1
        ax.add_patch(DataEndBar(amount, row, facecolor=IMPORTER if side > 0 else EXPORTER,
                                edgecolor="none", zorder=3, gid="bar"))
        ax.annotate(signed(amount, 0) + (" Mt" if row == 0 else ""), (amount, row),
                    xytext=(side * px(4), 0), textcoords="offset points",
                    ha="left" if side > 0 else "right", va="center_baseline", fontsize=T_LABEL,
                    fontweight="semibold", color=INK, zorder=6, annotation_clip=False, gid="value")
    # The baseline goes under the bars: drawn over them it would cover the first
    # pixels of every bar and hide the shortest ones altogether.
    ax.vlines(0, -0.5, len(FOCUS) - 0.5, colors=AXIS, linewidth=BASE, zorder=2, gid="zero")


def row_rules(fig, ax, box):
    """Hairlines between the rows, right across the three panels, so that a bar
    in the last panel can be followed back to its country's name."""
    for row in range(len(FOCUS) - 1):
        y = fig.transFigure.inverted().transform(ax.transData.transform((0, row + 0.5)))[1]
        fig.add_artist(Line2D([MARGIN / FIG_W, 1 - box["right"] / FIG_W], [y, y], color=GRID,
                              linewidth=HAIR, zorder=0, gid="row rule"))


def largest_since(focus):
    """(country, year): whose balance in Mt is the largest in the last year, and
    the first year from which it has been the largest in every year."""
    size = focus.assign(country=focus["country"].astype(str)).pivot(
        index="year", columns="country", values=TOTAL).abs()
    leader = size.loc[YEAR_MAX].idxmax()
    behind = size.index[size.idxmax(axis=1) != leader]
    return leader, (int(behind.max()) + 1 if len(behind) else int(size.index.min()))


@styled
def build_bars(focus):
    """Three panels, one per year, of the balance in Mt CO2: (figure, grid)."""
    box, ncol = BARS, len(BAR_YEARS)
    data = focus[focus["year"].isin(BAR_YEARS)][["country", "year", TOTAL]]
    grid = sns.FacetGrid(data, col="year", col_order=list(BAR_YEARS), sharex=True, sharey=True,
                         height=box["height"], aspect=(FIG_W / ncol) / box["height"],
                         despine=False)
    fig = grid.figure
    grid.map_dataframe(facet_bars, value=TOTAL)
    ax_w, _ = place(fig, box, ncol, 1)          # map_dataframe ends with its own tight layout
    grid.despine(left=True, bottom=True)
    grid.set_titles(col_template="")
    axes = [grid.axes_dict[year] for year in BAR_YEARS]
    axes[0].set_ylim(len(FOCUS) - 0.5, -0.5)    # first country on top
    axes[0].set_yticks(range(len(FOCUS)), FOCUS)
    axes[0].set_xticks([])
    for i, ax in enumerate(axes):
        ax.patch.set_visible(False)             # the row rules run behind all three panels
        ax.tick_params(axis="y", length=0, pad=(box["left"] - MARGIN) * 72, labelsize=T_LABEL,
                       labelcolor=INK, labelfontfamily=font_family(), labelleft=i == 0)
    for name in axes[0].get_yticklabels():      # the names start at the margin, like the title
        name.set_horizontalalignment("left")
    row_rules(fig, axes[0], box)

    # One scale for the three panels: the longest bar on each side, plus the
    # room the widest value label on that side needs beyond its tip.
    fig.draw_without_rendering()
    labels = [a for ax in axes for a in tagged(ax, "value")]
    low, high = min(data[TOTAL].min(), 0.0), max(data[TOTAL].max(), 0.0)
    left = zone(fig, [a for a in labels if a.get_ha() == "right"], reach=px(4))
    right = zone(fig, [a for a in labels if a.get_ha() == "left"], reach=px(4))
    per_unit = (ax_w - left - right) / (high - low)
    axes[0].set_xlim(low - left / per_unit, high + right / per_unit)
    header_notes(fig, [facet_header(ax, str(year), note)
                       for ax, year, note in zip(axes, BAR_YEARS, BAR_NOTES)])

    last = focus[focus["year"] == YEAR_MAX].assign(country=lambda d: d["country"].astype(str))
    last = last.set_index("country")
    leader, since = largest_since(focus)
    other = last[VALUE].abs().idxmax()          # the largest balance per person, for contrast
    kind = "import" if last.loc[leader, TOTAL] > 0 else "export"
    heading(fig, f"In tonnes, {leader}'s {kind} balance is the largest flow",
            "Net balance of CO2 embodied in trade in million tonnes (Mt): consumption-based "
            "minus production-based emissions.\n"
            f"{leader}'s balance has been the largest of the six since {since}. Per person "
            f"it is small: {signed(last.loc[leader, VALUE])} t in {YEAR_MAX} against "
            f"{other}'s {signed(last.loc[other, VALUE])} t.")
    sign_legend(fig, wash=False)
    source_note(fig, f"{SOURCE}\nNet balance = consumption-based minus production-based CO2 of "
                     "the whole country; 1 Mt = 1 million tonnes.")
    return fig, grid


# ---------------------------------------------------------------- public figure functions
def save_png(fig, name, out_dir=SHOTS):
    """Write a figure as a PNG at 200 dpi on the surface colour; returns the path.

    The canvas is opaque, so the alpha channel Matplotlib writes is dropped on
    the way: a word processor or a browser then has nothing to composite.
    """
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, name)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=DPI, facecolor=SURFACE)
    Image.open(buffer).convert("RGB").save(path, optimize=True, dpi=(DPI, DPI))
    return path


def finish(fig, name, save_as):
    """Save when asked: True for the standard file in screenshots/, or a path of the caller's."""
    if save_as is True:
        save_png(fig, name)
    elif save_as:
        save_png(fig, os.path.basename(save_as), os.path.dirname(os.path.abspath(save_as)))
    return fig


def main_figure(focus=None, save=False):
    """Six facets of the net balance per person on shared axes. Returns the Figure."""
    fig, _ = build_main(load_focus() if focus is None else focus)
    return finish(fig, MAIN_PNG, save)


def derivation_plate(focus=None, save=False):
    """How one facet is derived, for the United Kingdom. Returns the Figure."""
    fig, _ = build_plate(load_focus() if focus is None else focus)
    return finish(fig, PLATE_PNG, save)


def absolute_figure(focus=None, save=False):
    """The balance in Mt CO2 for 1990, 2007 and 2022 as diverging bars. Returns the Figure."""
    fig, _ = build_bars(load_focus() if focus is None else focus)
    return finish(fig, BARS_PNG, save)


# ---------------------------------------------------------------- reading back
# What follows only reads: main() uses it to compare the artists and the saved
# PNGs with the data files and with the design rules. Where a rule is a number
# (a 2 px line, a wash of 0.35-0.5 opacity) the number is written out here
# rather than taken from the constants above, so a wrong constant is caught.
LABEL = re.compile(r"^([+-]\d+\.\d\d)(?: (t)| in (\d{4}))?$")
# Words and phrases the writing brief bars from any text a reader sees.
BARRED = ("delve", "tapestry", "testament", "crucial", "moreover", "furthermore", "in conclusion",
          "it is important to note", "serves as a bridge", "rich visual representation",
          "multifaceted", "leverage", "robust", "seamless", "comprehensive", "underscores",
          "pivotal", "nuanced", "holistic", "realm", "landscape", "navigate", "foster",
          "as we can see", "this demonstrates that", "in summary", "overall")


def rel(path):
    """A path as the log prints it: relative to the project folder."""
    return os.path.relpath(path, ROOT)


def result_prefix(summary, country):
    """The prefix of a country's result names: its ISO code in lower case,
    as prepare_data.py forms them."""
    return summary.loc[country, "iso_code"].lower()


def label_text(artist):
    """The words of a label, whether it is a plain annotation or a packed box."""
    if isinstance(artist, Text):
        return artist.get_text()
    return " ".join(t.get_text() for t in artist.findobj(Text))


def shown_text(fig):
    """Every text a reader can see, with its box on the canvas. Call after a draw."""
    return [(t, t.get_window_extent()) for t in fig.findobj(Text)
            if t.get_visible() and t.get_text().strip()]


def core(box):
    """A text box without the empty band a line of type keeps above and below its letters."""
    trim = 0.15 * min(box.width, box.height)
    return Bbox.from_extents(box.x0 + 1, box.y0 + trim, box.x1 - 1, box.y1 - trim)


def layout_problems(fig):
    """What a reader would see as a fault: text over other text, text over a
    mark, text running off the canvas. Returns (problems, texts tested)."""
    fig.draw_without_rendering()
    texts = shown_text(fig)
    canvas = fig.bbox
    problems = [f"'{t.get_text()[:28]}' leaves the canvas" for t, box in texts
                if box.x0 < 0 or box.y0 < 0 or box.x1 > canvas.width or box.y1 > canvas.height]
    for i, (a, box_a) in enumerate(texts):
        for b, box_b in texts[i + 1:]:
            if core(box_a).overlaps(core(box_b)):
                problems.append(f"'{a.get_text()[:28]}' overlaps '{b.get_text()[:28]}'")
    per_pt = fig.dpi / 72
    for ax in fig.axes:
        marks = []                               # (what, path on the canvas, filled, half width)
        for line in ax.lines:
            path = line.get_path().transformed(line.get_transform())
            if line.get_gid() == "dot":
                (x, y), r = path.vertices[0], line.get_markersize() / 2 * per_pt
                marks.append(("a point", Path.unit_rectangle().transformed(
                    Affine2D().scale(2 * r).translate(x - r, y - r)), True, 0))
            elif line.get_gid():
                marks.append(("a line", path, False, line.get_linewidth() / 2 * per_pt))
        for wash in (c for c in ax.collections if isinstance(c, PolyCollection)):
            marks += [("a wash", p.transformed(wash.get_transform()), True, 0)
                      for p in wash.get_paths()]
        marks += [("a bar", bar.get_path().transformed(bar.get_transform()), True, 0)
                  for bar in tagged(ax, "bar")]
        for text, box in texts:
            hit = {what for what, path, filled, half in marks
                   if path.intersects_bbox(core(box).padded(half), filled=filled)}
            problems += [f"'{text.get_text()[:28]}' sits on {what}" for what in sorted(hit)]
    return problems, len(texts)


def solid(stroke):
    """True for an undashed Line2D or line collection."""
    style = stroke.get_linestyle()
    return style == "-" if isinstance(style, str) else all(dash is None for _, dash in style)


def printed(points):
    """A set of lengths in canvas points as CSS pixels at the printed size."""
    return {round(float(p) / px(1), 3) for p in points}


def spread(values):
    """'2' for a set with one value, '2/3' when the marks do not all agree."""
    return "/".join(f"{v:g}" for v in sorted(values))


def marks_as_built(fig):
    """What the marks of a figure measure at the printed size, and whether that
    is what the design system asks for: 2 px lines; points of at least 8 px
    with a 2 px ring in the surface colour; solid 1 px gridlines; a baseline no
    thinner than the grid; washes of 0.35-0.5 opacity."""
    lines = [ln for ax in fig.axes for ln in ax.lines if ln.get_gid() not in (None, "dot")]
    dots = [ln for ax in fig.axes for ln in ax.lines if ln.get_gid() == "dot"]
    rules = {gid: [c for ax in fig.axes for c in ax.collections if c.get_gid() == gid]
             for gid in ("grid", "zero")}
    rules["grid"] += fig.findobj(lambda a: a.get_gid() == "row rule")
    washes = [c for ax in fig.axes for c in ax.collections if isinstance(c, PolyCollection)]
    said, ok = [], True
    if lines:
        widths = printed(ln.get_linewidth() for ln in lines)
        said.append(f"{len(lines)} lines {spread(widths)} px")
        ok &= widths == {2} and all(solid(ln) for ln in lines)
    if dots:
        rings = printed(d.get_markeredgewidth() for d in dots)
        cores = printed(d.get_markersize() - d.get_markeredgewidth() for d in dots)
        said.append(f"{len(dots)} points {spread(cores)} px + {spread(rings)} px ring")
        ok &= (min(cores) >= 8 and rings == {2}
               and all(to_hex(d.get_markeredgecolor()) == SURFACE for d in dots))
    for gid, name in (("grid", "gridlines"), ("zero", "baselines")):
        if rules[gid]:
            widths = printed(np.ravel(r.get_linewidth())[0] for r in rules[gid])
            said.append(f"{name} {spread(widths)} px")
            ok &= all(solid(r) for r in rules[gid])
            ok &= (widths == {1}) if gid == "grid" else (min(widths) >= 1)
    if washes:
        opacity = {w.get_alpha() for w in washes}
        said.append(f"wash opacity {spread(opacity)}")
        ok &= all(0.35 <= a <= 0.5 for a in opacity)
    return ", ".join(said), bool(ok)


def check_page(log, fig, path, what):
    """The checks every figure shares: the saved file, the furniture, the
    marks, the type and the layout."""
    with Image.open(path) as im:
        size, corner = im.size, im.convert("RGB").getpixel((2, 2))
    said, sized = marks_as_built(fig)
    problems, n = layout_problems(fig)
    texts = [t for t, _ in shown_text(fig)]
    inks = {to_hex(t.get_color()) for t in texts}
    notes = {gid: " ".join(a.get_text() for a in fig.findobj(lambda a, g=gid: a.get_gid() == g))
             for gid in ("subtitle", "source")}
    entries = [t.get_text() for legend in fig.legends for t in legend.get_texts()]
    print(f"   {rel(path)}   {size[0]} x {size[1]} px, {os.path.getsize(path) / 1024:.0f} KB")
    print(textwrap.fill(said, 92, initial_indent="   as printed: ", subsequent_indent=" " * 15))
    print(f"   text: {n} pieces, set in {', '.join(sorted(inks))}")
    for problem in problems:
        print(f"      {problem}")
    log.check(f"{what}: the PNG is {FIG_W * DPI:.0f} px wide, on the surface colour {SURFACE}",
              size[0] == round(FIG_W * DPI) and to_hex([c / 255 for c in corner]) == SURFACE)
    log.check(f"{what}: title, subtitle, legend of {len(entries)} entries and source note are "
              "there", bool(fig.get_suptitle()) and bool(notes["subtitle"]) and len(entries) >= 2
              and "Our World in Data" in notes["source"]
              and "Global Carbon Budget 2025" in notes["source"])
    log.check(f"{what}: every stroke is solid and every mark has its specified size", sized)
    log.check(f"{what}: no text overlaps other text, sits on a mark or leaves the canvas",
              not problems)
    log.check(f"{what}: all text is plain ASCII and in ink, none in a data colour",
              all(t.get_text().isascii() for t in texts) and inks <= {INK, INK_2, MUTED})
    words_shown = " ".join(t.get_text() for t in texts).lower()
    log.check(f"{what}: none of the {len(BARRED)} barred words or phrases appears",
              not any(re.search(r"\b" + re.escape(word), words_shown) for word in BARRED))


def pixel(image, ax, x, y, dx=0, dy=0):
    """RGB of the saved PNG at a data point of an Axes, moved by (dx, dy) pixels.
    main() has set the figure to the PNG's resolution, so a canvas pixel is a
    PNG pixel."""
    col, row = ax.transData.transform((x, y)) + (dx, dy)
    return image[int(image.shape[0] - row), int(col)]


def hue(rgb):
    """'blue' or 'orange' for a pixel or a colour, judged from its channels
    alone, so that the test does not lean on the colour constants."""
    red, _, blue = (int(v) for v in rgb[:3])
    return "blue" if blue - red > 40 else "orange" if red - blue > 40 else "neither"


def rgb255(color, alpha=1.0):
    """RGB that a colour leaves on the surface when it is laid on at this opacity."""
    mix = alpha * np.array(to_rgb(color)) + (1 - alpha) * np.array(to_rgb(SURFACE))
    return np.round(255 * mix).astype(int)


def clear_of_points(fig, ax, years, values):
    """True for the years whose marks are not under a labelled point or its ring."""
    reach = (REACH + px(2)) * fig.dpi / 72
    column = [ax.transData.transform((year, 0))[0] for year in years]
    dots = [ax.transData.transform((year, 0))[0] for _, year, _ in labelled_points(years, values)]
    return np.array([min(abs(x - d) for d in dots) >= reach for x in column])


def wash_sample(fig, ax, years, values, ticks, side, min_clear=4.0):
    """Where to test one wash of a facet: (year, y) in the middle of the widest
    band between the baseline, the gridlines and the line that no stroke touches.

    None when no band is min_clear PNG pixels deep, as with a balance that
    stays within the width of the line from zero.
    """
    per_pt, to_px = fig.dpi / 72, ax.transData.transform
    free = clear_of_points(fig, ax, years, values)
    best = None
    for i in np.flatnonzero((np.sign(values) == side) & free):
        here = to_px((years[i], values[i]))
        # A sloping stroke reaches further up and down than half its width.
        steps = [np.abs(to_px((years[j], values[j])) - here) for j in (i - 1, i + 1)
                 if 0 <= j < len(values)]
        reach = LINE / 2 * math.hypot(1, max(dy / dx for dx, dy in steps))
        levels = sorted([(0.0, BASE / 2), (values[i], reach)]
                        + [(t, HAIR / 2) for t in ticks if 0 < side * t < side * values[i]])
        for (low, half_low), (high, half_high) in zip(levels[:-1], levels[1:]):
            y0 = to_px((years[i], low))[1] + half_low * per_pt
            y1 = to_px((years[i], high))[1] - half_high * per_pt
            if best is None or y1 - y0 > best[0]:
                middle = ax.transData.inverted().transform((here[0], (y0 + y1) / 2))[1]
                best = (y1 - y0, int(years[i]), float(middle))
    return best[1:] if best and best[0] >= min_clear else None


def line_sample(fig, ax, years, values, side):
    """Where to test the colour of the line for one sign: the year furthest from
    zero whose two neighbours have the same sign, away from the labelled points."""
    free = clear_of_points(fig, ax, years, values)
    inside = [i for i in range(1, len(values) - 1)
              if free[i] and (np.sign(values[i - 1:i + 2]) == side).all()]
    if not inside:
        return None
    i = max(inside, key=lambda j: abs(values[j]))
    return int(years[i]), float(values[i])


# ---------------------------------------------------------------- checks
def check_data(log):
    """Section 1: the file the three figures are drawn from."""
    log.section("1. Data")
    table = pd.read_csv(FOCUS_CSV)
    n_years = YEAR_MAX - YEAR_MIN + 1
    print(f"   {rel(FOCUS_CSV)}: {len(table)} rows, {table['country'].nunique()} countries, "
          f"{table['year'].min()}-{table['year'].max()}")
    log.check(f"{len(FOCUS)} focus countries x {n_years} years, nothing missing in the plotted "
              "columns",
              len(table) == len(FOCUS) * n_years and set(table["country"]) == set(FOCUS)
              and not table[[VALUE, TOTAL, PROD, CONS]].isna().any().any())
    gap = (table[CONS] - table[PROD] - table[VALUE]).abs().max()
    log.check(f"net balance = consumption - production per person (worst gap {gap:.1e} t)",
              gap < 1e-6)
    return table


def furthest(row):
    """(value, year, 'max' or 'min') of the balance furthest from zero, from the summary."""
    which = "max" if abs(row["net_pc_max"]) >= abs(row["net_pc_min"]) else "min"
    return row[f"net_pc_{which}"], int(row[f"net_pc_{which}_year"]), which


def check_furniture(log, fig, grid):
    """The parts of the main figure that say how to read it."""
    subtitle = fig.findobj(lambda a: a.get_gid() == "subtitle")[0].get_text()
    legend = fig.legends[0]
    entries = [t.get_text() for t in legend.get_texts()]
    keys = [hue(255 * np.array(h.get_facecolor()[:3])) for h in legend.legend_handles]
    log.check("subtitle: says how to read the sign and names both colours",
              all(word in subtitle for word in ("Above zero", "below zero", "blue", "orange",
                                                "importer", "exporter")))
    log.check("legend: two entries, blue for the net importer, orange for the net exporter",
              keys == ["blue", "orange"] and entries[0].startswith("Net importer - ")
              and entries[1].startswith("Net exporter - "))
    log.check(f"y-axis label carries the unit: '{fig.get_supylabel()}'",
              "t CO2 per person" in fig.get_supylabel())
    heads = [(ax.get_title(loc="left"), label_text(tagged(ax, "header note")[0]))
             for ax in grid.axes.flat]
    corners = [ax.get_position() for ax in grid.axes.flat]
    log.check("the facets are the focus countries in their fixed order, 2 rows x 3 columns",
              [name for name, _ in heads] == FOCUS
              and len({round(c.y0, 6) for c in corners}) == 2
              and len({round(c.x0, 6) for c in corners}) == 3)
    return dict(heads)


def check_lines(log, axes, table):
    """The plotted series against the file, and the shared axes."""
    worst, whole, coloured, n_dots = 0.0, True, True, 0
    for country in FOCUS:
        years, values = series(table, country, VALUE)
        lines = [ln for ln in axes[country].lines if ln.get_gid() in ("importer", "exporter")]
        whole &= bool(lines) and all(np.array_equal(ln.get_xdata(), years) for ln in lines)
        worst = max([worst] + [np.abs(ln.get_ydata() - values).max() for ln in lines
                               if len(ln.get_ydata()) == len(values)])
        for dot in tagged(axes[country], "dot"):
            above = dot.get_ydata()[0] >= 0
            coloured &= hue(255 * np.array(to_rgb(dot.get_markerfacecolor()))) == (
                "blue" if above else "orange")
            n_dots += 1
    log.check(f"each facet's line holds the {YEAR_MAX - YEAR_MIN + 1} values of the file "
              f"(worst gap {worst:.1e} t)", whole and worst == 0)
    log.check(f"the {n_dots} labelled points are blue above zero and orange below", coloured)
    ylims = {tuple(np.round(ax.get_ylim(), 9)) for ax in axes.values()}
    xlims = {tuple(np.round(ax.get_xlim(), 9)) for ax in axes.values()}
    low, high = sorted(ylims)[0]
    log.check(f"all six facets share one y-axis ({low:+.2f} to {high:+.2f} t) and one x-axis",
              len(ylims) == 1 and len(xlims) == 1)


def check_washes(log, axes, table):
    """The washes as polygons: each on its own side of zero, cut at the crossings."""
    sided, cuts = True, {}
    for country in FOCUS:
        years, values = series(table, country, VALUE)
        cuts[country] = [end for _, end, _ in sign_runs(years, values)[:-1]]
        for wash in (c for c in axes[country].collections if isinstance(c, PolyCollection)):
            side = 1 if hue(255 * wash.get_facecolor()[0][:3]) == "blue" else -1
            corners = np.concatenate([p.vertices for p in wash.get_paths()])
            on_zero = corners[np.abs(corners[:, 1]) < 1e-12, 0]
            sided &= bool((side * corners[:, 1] >= -1e-12).all())
            sided &= all(np.abs(on_zero - cut).min() < 1e-9 for cut in cuts[country])
    for country, where in cuts.items():
        if where:
            print(f"   {country} crosses zero at {', '.join(f'{x:.2f}' for x in where)}")
    log.check("each wash stays on its side of zero and ends at the crossing "
              f"({sum(map(len, cuts.values()))} crossings)", sided)


def check_pixels(log, fig, axes, path, table):
    """The same split read from the saved PNG, for the wash and for the line."""
    image = np.asarray(Image.open(path).convert("RGB")).astype(int)
    ticks = list(axes[FOCUS[0]].get_yticks())
    seen = {(kind, side): [] for kind in ("wash", "line") for side in (1, -1)}
    print("   colours in the PNG, in the wash between baseline and line and on the line itself")
    for country in FOCUS:
        ax = axes[country]
        years, values = series(table, country, VALUE)
        for side, color, where in ((1, IMPORTER, "above"), (-1, EXPORTER, "below")):
            for kind, spot, want in (
                    ("wash", wash_sample(fig, ax, years, values, ticks, side),
                     rgb255(color, FILL_ALPHA)),
                    ("line", line_sample(fig, ax, years, values, side), rgb255(color))):
                if spot is None:
                    continue
                got = pixel(image, ax, *spot)
                same = (hue(got) == ("blue" if side > 0 else "orange")
                        and bool(np.abs(got - want).max() <= 3))
                seen[kind, side].append(same)
                print(f"      {country:<15}{kind} {where} zero  {spot[0]}  {spot[1]:+.2f} t  "
                      f"rgb{tuple(int(v) for v in got)}  {hue(got)}"
                      f"{'' if same else '  UNEXPECTED'}")
    for kind in ("wash", "line"):
        up, down = seen[kind, 1], seen[kind, -1]
        log.check(f"PNG: the {kind} is blue above zero in {len(up)} facets and orange below "
                  f"zero in {len(down)}", all(up + down) and len(up) >= 2 and len(down) >= 2)


def check_labels(log, axes, table, summary, heads):
    """The direct labels and the facet headers against the summary table."""
    print("   labels read back from the facets, t CO2 per person")
    print(f"   {'country':<17}{YEAR_MIN:>8}{YEAR_MAX:>11}   furthest from zero")
    worded, valued, results, count = True, True, [], 0
    for country in FOCUS:
        ax, row, prefix = axes[country], summary.loc[country], result_prefix(summary, country)
        years, _ = series(table, country, VALUE)
        line = next(ln for ln in ax.lines if ln.get_gid() in ("importer", "exporter"))
        drawn = dict(zip(years, line.get_ydata()))
        _, year, which = furthest(row)
        labels = {gid: [label_text(a) for a in tagged(ax, gid)]
                  for gid in ("start", "end", "extreme")}
        count += sum(map(len, labels.values()))
        # (label, the value it must show, the unit it must carry, the year it must name)
        wanted = [(labels["start"], drawn[YEAR_MIN], None, None),
                  (labels["end"], drawn[YEAR_MAX], "t", None)]
        if year not in (YEAR_MIN, YEAR_MAX):
            wanted.append((labels["extreme"], drawn[year], None, str(year)))
        worded &= len(labels["extreme"]) == len(wanted) - 2
        for found, value, unit, named in wanted:
            match = LABEL.match(found[0]) if len(found) == 1 else None
            worded &= bool(match) and abs(float(match.group(1)) - value) <= 0.005 + 1e-9
            worded &= bool(match) and match.group(2) == unit and match.group(3) == named
        print(f"   {country:<17}{labels['start'][0]:>8}{labels['end'][0]:>11}   "
              f"{labels['extreme'][0] if labels['extreme'] else '(the ' + str(year) + ' value)'}")
        for name, at in ((f"net_pc_{YEAR_MIN}", YEAR_MIN), (f"net_pc_{YEAR_MAX}", YEAR_MAX),
                         (f"net_pc_{which}", year)):
            results.append((f"{prefix}_{name}", drawn[at], 4))
            valued &= abs(drawn[at] - row[name]) < 1e-8
        results.append((f"{prefix}_net_pc_{which}_year", year, 0))
        valued &= max(drawn, key=lambda y: abs(drawn[y])) == year
    for name, value, places in results:
        log.result(name, value, places)
    log.check(f"{count} labels: {YEAR_MIN}, {YEAR_MAX}, the year furthest from zero; signed, "
              "2 dp, unit once", worded)
    log.check("the labelled values equal those in decoupling_summary.csv", valued)
    log.check("each facet header gives the country's income group from the summary",
              all(heads[c] == summary.loc[c, "income_group"] for c in FOCUS))


def check_main(log, fig, grid, path, table, summary):
    """Section 2: the six-facet figure, read back from its artists and its PNG."""
    log.section("2. Main figure: net balance per person, six facets")
    check_page(log, fig, path, "main figure")
    axes = grid.axes_dict
    heads = check_furniture(log, fig, grid)
    check_lines(log, axes, table)
    check_washes(log, axes, table)
    check_pixels(log, fig, axes, path, table)
    check_labels(log, axes, table, summary, heads)

    years, values = series(table, FOCUS[0], VALUE)
    since = int(years[values <= 0].max()) + 1
    log.result(f"{result_prefix(summary, FOCUS[0])}_net_importer_since_year", since, 0)
    log.check(f"the {FOCUS[0]} is a net importer from {since} on, a net exporter in "
              f"{since - 1}",
              bool((values[years >= since] > 0).all()) and values[years == since - 1][0] < 0)
    rich = summary.index[summary["income_group"] == "High income"]
    log.check("title: the four high-income countries end above zero, China and India below",
              len(rich) == 4 and bool((summary.loc[rich, f"net_pc_{YEAR_MAX}"] > 0).all())
              and bool((summary.drop(rich)[f"net_pc_{YEAR_MAX}"] < 0).all()))


def check_plate(log, fig, axes, path, table, summary):
    """Section 3: the derivation plate for one country."""
    log.section(f"3. Derivation plate: {PLATE_COUNTRY}")
    check_page(log, fig, path, "plate")
    accounts, gap = axes
    row, prefix = summary.loc[PLATE_COUNTRY], result_prefix(summary, PLATE_COUNTRY)
    _, prod = series(table, PLATE_COUNTRY, PROD)
    _, cons = series(table, PLATE_COUNTRY, CONS)
    _, net = series(table, PLATE_COUNTRY, VALUE)
    lines = {ln.get_gid(): ln for ln in accounts.lines + gap.lines if ln.get_gid() != "dot"}
    drawn = {gid: line.get_ydata() for gid, line in lines.items()}
    log.check("left panel: each line holds the 33 values of its account in the file",
              np.array_equal(drawn["production"], prod)
              and np.array_equal(drawn["consumption"], cons))
    log.check("left panel: the consumption line is blue and the production line orange",
              hue(255 * np.array(to_rgb(lines["consumption"].get_color()))) == "blue"
              and hue(255 * np.array(to_rgb(lines["production"].get_color()))) == "orange")
    worst = np.abs(drawn["importer"] - (drawn["consumption"] - drawn["production"])).max()
    log.check(f"right panel: line = consumption line - production line (gap {worst:.1e} t)",
              worst < 1e-6)
    extreme, year, _ = furthest(row)
    log.check("right panel: its three labels match the country's facet in the main figure",
              [label_text(a) for gid in ("start", "extreme", "end") for a in tagged(gap, gid)]
              == [signed(net[0]), f"{signed(extreme)} in {year}", f"{signed(net[-1])} t"])
    scale = ((accounts.get_ylim()[1] - accounts.get_ylim()[0])
             / (gap.get_ylim()[1] - gap.get_ylim()[0]))
    same_years = abs(accounts.get_window_extent().width / np.ptp(accounts.get_xlim())
                     - gap.get_window_extent().width / np.ptp(gap.get_xlim())) < 1e-6
    print(f"   {'t CO2 per person':<22}{YEAR_MIN:>8}{YEAR_MAX:>8}{'change':>9}")
    results = []
    for name, short, values in (("production-based", "prod", drawn["production"]),
                                ("consumption-based", "cons", drawn["consumption"])):
        change = 100.0 * (values[-1] / values[0] - 1.0)
        print(f"   {name:<22}{values[0]:>8.2f}{values[-1]:>8.2f}{change:>+8.0f}%")
        results += [(f"{short}_pc_{YEAR_MIN}", values[0]), (f"{short}_pc_{YEAR_MAX}", values[-1]),
                    (f"{short}_change_pct", change)]
    print(f"   {'gap (net balance)':<22}{net[0]:>+8.2f}{net[-1]:>+8.2f}")
    print(f"   the right panel's vertical scale is {scale:.1f} times the left panel's")
    for name, value in results:
        log.result(f"{prefix}_{name}", value)
    log.result("plate_scale_ratio", scale, 2)
    log.check("both panels give a year the same width, so the gap keeps its shape", same_years)
    log.check("the plotted levels and changes equal decoupling_summary.csv",
              all(abs(value - row[name]) < 1e-6 for name, value in results))
    said = fig.findobj(lambda a: a.get_gid() == "subtitle")[0].get_text()
    log.check("subtitle: both accounts fell, production-based further, and the gap widened",
              prod[-1] < prod[0] and cons[-1] < cons[0] and prod[0] - prod[-1] > cons[0] - cons[-1]
              and net[-1] > net[0] > 0 and said.count("fell by") == 2 and "widened" in said)
    log.check("subtitle: the rounded numbers it prints still subtract to the rounded gap",
              all(abs(round(cons[i], 2) - round(prod[i], 2) - round(net[i], 2)) < 1e-9
                  for i in (0, -1)))


def check_bars(log, fig, grid, path, table, summary):
    """Section 4: the balance in Mt CO2 as diverging bars."""
    log.section("4. Absolute balance: Mt CO2 in " + ", ".join(map(str, BAR_YEARS)))
    check_page(log, fig, path, "bars")
    image = np.asarray(Image.open(path).convert("RGB")).astype(int)
    worst, coloured, middles, ends, thickness = 0.0, True, [], [], set()
    rows = {country: [] for country in FOCUS}
    for year in BAR_YEARS:
        ax = grid.axes_dict[year]
        want = table[table["year"] == year].set_index("country")[TOTAL]
        for country, bar in zip(FOCUS, sorted(tagged(ax, "bar"), key=lambda b: b.row)):
            extent = bar.get_path().get_extents()
            length = extent.x0 + extent.x1          # one end of every bar is zero
            side = "blue" if want[country] >= 0 else "orange"
            worst = max(worst, abs(length - want[country]))
            coloured &= hue(255 * np.array(bar.get_facecolor()[:3])) == side
            rows[country].append(length)
            box = bar.get_window_extent()
            thickness.add(round(box.height))
            if box.width >= 12:                     # long enough to hold a clean pixel
                middles.append(hue(pixel(image, ax, length / 2, bar.row)) == side)
            if box.width >= 60:                     # long enough to show both of its ends
                out = 1 if length > 0 else -1       # pixels step away from the baseline
                up = box.height / 2 - 2             # just inside the long edge of the bar
                ends.append(hue(pixel(image, ax, length, bar.row, -2 * out, up)) == "neither"
                            and hue(pixel(image, ax, 0, bar.row, 8 * out, up)) == side)
    print(f"   {'Mt CO2':<17}" + "".join(f"{year:>10}" for year in BAR_YEARS))
    for country in FOCUS:
        print(f"   {country:<17}" + "".join(f"{v:>+10,.0f}" for v in rows[country]))
    for country in FOCUS:
        for year, value in zip(BAR_YEARS, rows[country]):
            log.result(f"{result_prefix(summary, country)}_net_mt_{year}", value)
    n = len(FOCUS) * len(BAR_YEARS)
    log.check(f"the {n} bars run from zero to the file's net_co2_mt (worst gap {worst:.1e} Mt)",
              sum(map(len, rows.values())) == n and worst < 1e-9)
    log.check("bars are blue for a net importer and orange for a net exporter", coloured)
    log.check(f"PNG: the same colours at the middle of the {len(middles)} bars long enough to "
              "sample", all(middles) and len(middles) >= 6)
    log.check(f"PNG: {len(ends)} long bars are square at the baseline and rounded at the data "
              "end", all(ends) and len(ends) >= 3)
    as_printed = {round(v) for v in printed(t * 72 / DPI for t in thickness)}
    log.check(f"every bar is {spread(thickness)} px thick in the PNG: {spread(as_printed)} px as "
              "printed, cap 24 px", len(thickness) == 1 and max(as_printed) <= 24)
    first = grid.axes_dict[BAR_YEARS[0]]
    log.check("the rows are the focus countries in their fixed order, the first on top",
              [t.get_text() for t in first.get_yticklabels()] == FOCUS and first.yaxis_inverted())
    log.check("the 1990 and 2022 bars equal net_mt_1990 and net_mt_2022 in the summary",
              all(abs(rows[c][i] - summary.loc[c, f"net_mt_{year}"]) < 1e-6 for c in FOCUS
                  for i, year in enumerate(BAR_YEARS) if year != PIVOT_YEAR))
    leader, since = largest_since(table)
    size = table.pivot(index="year", columns="country", values=TOTAL).abs()
    log.result(f"{result_prefix(summary, leader)}_net_mt_largest_since_year", since, 0)
    log.check(f"title: {leader}'s balance in Mt is the largest of the six from {since}, "
              f"not {since - 1}",
              bool((size.loc[since:].idxmax(axis=1) == leader).all())
              and size.loc[since - 1].idxmax() != leader)
    last = summary[f"net_pc_{YEAR_MAX}"].abs()
    log.check(f"subtitle: per person {leader}'s {YEAR_MAX} balance is smaller than "
              f"{last.idxmax()}'s", last[leader] < last.max() and last.idxmax() != leader)


def check_importers(log, table, summary):
    """Section 5: what the two accounts say about the cut in each net importer."""
    log.section("5. Territorial against consumption-based change in the net importers")
    last = table[table["year"] == YEAR_MAX].set_index("country")
    importers = [c for c in FOCUS if last.loc[c, VALUE] > 0]
    print(f"   change in CO2 per person, {YEAR_MIN}-{YEAR_MAX}, and consumption over production "
          f"in {YEAR_MAX}")
    print(f"   {'country':<17}{'production':>11}{'consumption':>13}{'gap, points':>13}"
          f"{'cons / prod':>13}")
    agree, results = True, []
    for country in importers:
        row, s, prefix = last.loc[country], summary.loc[country], result_prefix(summary, country)
        gap = row["prod_change_pct"] - row["cons_change_pct"]
        ratio = row[CONS] / row[PROD]
        print(f"   {country:<17}{row['prod_change_pct']:>+10.1f}%{row['cons_change_pct']:>+12.1f}%"
              f"{gap:>+13.1f}{ratio:>13.3f}")
        results += [(f"{prefix}_change_gap_points", gap),
                    (f"{prefix}_cons_over_prod_{YEAR_MAX}", ratio)]
        agree &= (abs(gap - (s["prod_change_pct"] - s["cons_change_pct"])) < 1e-6
                  and abs(ratio - s[f"cons_pc_{YEAR_MAX}"] / s[f"prod_pc_{YEAR_MAX}"]) < 1e-6)
    deeper = [c for c in importers
              if last.loc[c, "prod_change_pct"] < last.loc[c, "cons_change_pct"]]
    print(f"   production-based CO2 fell further than consumption-based in {len(deeper)} of the "
          f"{len(importers)}:")
    print(f"   {', '.join(deeper)}")
    for name, value in results:
        log.result(name, value)
    log.result("importers_with_larger_territorial_cut", len(deeper), 0)
    log.check(f"the net importers of {YEAR_MAX} are the four high-income countries",
              importers == list(summary.index[summary["income_group"] == "High income"])
              and len(importers) == 4)
    log.check("these gaps and ratios equal decoupling_summary.csv", agree)


def main(show_results=True, out_dir=SHOTS):
    """Draw, save and check the three figures; returns the results and the tally."""
    log = Log(show_results=show_results)
    log.banner("MODULE TWO - VISUALIZATION 3: DIVERGING SMALL MULTIPLES IN SEABORN")
    print(f"   seaborn {sns.__version__}, matplotlib {matplotlib.__version__}, "
          f"font {font_family()}")
    print(f"   figures {FIG_W:g} in wide at {DPI} dpi = {FIG_W * DPI:.0f} px, for a "
          f"{PRINT_W:g} in slot in the report")
    focus, summary = load_data()
    table = check_data(log)
    for build, name, check in ((build_main, MAIN_PNG, check_main),
                               (build_plate, PLATE_PNG, check_plate),
                               (build_bars, BARS_PNG, check_bars)):
        fig, parts = build(focus)
        path = save_png(fig, name, out_dir)
        fig.set_dpi(DPI)        # from here on a canvas pixel is a pixel of the saved PNG
        check(log, fig, parts, path, table, summary)
        plt.close(fig)          # a notebook cell that calls main() shows no stray figures
    check_importers(log, table, summary)
    ok = log.tally()
    return {"results": log.results, "passed": log.passed, "failed": log.failed, "ok": ok}


if __name__ == "__main__":
    sys.exit(0 if main()["ok"] else 1)
