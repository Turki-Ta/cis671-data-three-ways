"""
common.py -- paths, the country sets, the colour tokens and the tidy-data
loaders shared by the Module Two scripts.

Everything a chart needs to agree with the other two lives here: which years,
which six focus countries, which hex goes with which entity. The colour sets
were chosen with a validator, not by eye; the numbers it reported are in the
comments beside each set so a later change can be checked against them.

    Delta E = Euclidean distance in OKLab x 100. "CVD" is the worse of
    protanopia and deuteranopia (Machado et al. 2009, severity 1.0).
    Targets: CVD >= 8 (6-8 allowed only with direct labels), normal >= 15.
"""
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INPUTS = os.path.join(ROOT, "inputs")
SHOTS = os.path.join(ROOT, "screenshots")
LOGS = os.path.join(SHOTS, "logs")
WEB = os.path.join(ROOT, "web")

RAW_CSV = os.path.join(INPUTS, "owid-co2-data.csv")
RAW_CODEBOOK = os.path.join(INPUTS, "owid-co2-codebook.csv")
RAW_WORLD_BANK = os.path.join(INPUTS, "worldbank_country_classification.json")
PANEL_CSV = os.path.join(INPUTS, "decoupling_panel.csv")
FOCUS_CSV = os.path.join(INPUTS, "decoupling_focus.csv")
SUMMARY_CSV = os.path.join(INPUTS, "decoupling_summary.csv")
WEB_DATA_JS = os.path.join(WEB, "data", "decoupling_data.js")

# Consumption-based emissions start in 1990 and the Maddison GDP series stops in
# 2022, so this window is the longest one in which every variable exists.
YEAR_MIN, YEAR_MAX = 1990, 2022
BASE_YEAR = 1990
# The year before the financial crisis: the last year in which consumption-based
# emissions per person were still at or near their peak in the importers.
PIVOT_YEAR = 2007
# The two brush positions the report compares in Visualization 1.
EARLY = (1990, 1999)
LATE = (2013, 2022)

# The six countries that carry the story, in the order every chart lists them:
# four post-industrial importers, then the two largest developing economies.
FOCUS = ["United States", "United Kingdom", "Germany", "Sweden", "China", "India"]
FOCUS_SHORT = {"United States": "US", "United Kingdom": "UK", "Germany": "Germany",
               "Sweden": "Sweden", "China": "China", "India": "India"}

# ---------------------------------------------------------------- colour tokens
# Chart chrome: one near-white surface, three inks, hairline grid.
SURFACE = "#fcfcfb"
PAGE = "#f9f9f7"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
ZERO = "#f0efec"            # neutral midpoint of the diverging pair

# Held constant across all three visualizations: blue is the consumption side
# (consumption-based series; consumption above production, a net importer) and
# orange is the production side. Pair: CVD 24.7, normal 33.6.
CONSUMPTION = "#2a78d6"
PRODUCTION = "#eb6834"
IMPORTER = CONSUMPTION
EXPORTER = PRODUCTION

# Visualization 1, top panel: GDP per capita is the reference series, in ink.
MEASURES = {
    "GDP per capita": INK_2,
    "Production-based CO2 per capita": PRODUCTION,
    "Consumption-based CO2 per capita": CONSUMPTION,
}

# Visualization 1, scatter: World Bank income groups folded to three classes.
# A scatter can put any two marks side by side, so all three pairs were checked:
# worst CVD 17.6, worst normal 33.9. Magenta sits at 2.62:1 against the surface,
# so the focus bubbles carry direct labels and every bubble has a tooltip.
INCOME_ORDER = ["High income", "Upper-middle income", "Lower-middle and low income"]
INCOME_COLORS = {
    "High income": "#4a3aa7",
    "Upper-middle income": "#e87ba4",
    "Lower-middle and low income": "#008300",
}
WB_INCOME = {"HIC": "High income", "UMC": "Upper-middle income",
             "LMC": "Lower-middle and low income", "LIC": "Lower-middle and low income"}

# Visualization 2, trajectories: one hue per focus country. Six hues, all 15
# pairs checked: worst CVD 6.9 (red-aqua), worst normal 15.6 (aqua-green), which
# is legal only with direct labels, so every trajectory is labelled at its end.
# The weak pairs are given to countries that sit in opposite corners of the plot
# (red-aqua: United States and India; red-green: United States and United
# Kingdom, at least 4 t apart on the y-axis). The three European paths overlap,
# so they take the three best-separated hues (green, yellow, blue: CVD >= 16).
COUNTRY_COLORS = {
    "United States": "#e34948",
    "United Kingdom": "#008300",
    "Germany": "#eda100",
    "Sweden": "#2a78d6",
    "China": "#4a3aa7",
    "India": "#1baf7a",
}

FONT_STACK = ["Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"]


# ---------------------------------------------------------------- loaders
def _need(path):
    if not os.path.isfile(path):
        raise SystemExit(f"{os.path.relpath(path, ROOT)} is missing - run "
                         f"python scripts/prepare_data.py first")
    return path


def load_panel():
    """Every country with a complete 1990-2022 series: one row per country-year."""
    return pd.read_csv(_need(PANEL_CSV))


def load_focus():
    """The six focus countries, with the change-since-1990 columns added."""
    df = pd.read_csv(_need(FOCUS_CSV))
    df["country"] = pd.Categorical(df["country"], categories=FOCUS, ordered=True)
    return df.sort_values(["country", "year"]).reset_index(drop=True)


def load_summary():
    """One row per focus country: 1990 and 2022 levels, changes and the balance."""
    return pd.read_csv(_need(SUMMARY_CSV)).set_index("country").loc[FOCUS]


class Log:
    """The print conventions every script shares: banners, checks and results.

    'check: ... PASS' lines are counted, and 'result: name = value' lines are
    what run_all.py reads back to compare with its own recomputation. With
    show_results=False the results are still collected but not printed, which
    keeps a notebook cell to the tables and the checks.
    """

    def __init__(self, show_results=True):
        self.passed = self.failed = 0
        self.results = {}
        self.show_results = show_results

    def banner(self, title):
        print("=" * 78)
        print(title)
        print("=" * 78)

    def section(self, title):
        print(f"\n{title}")
        print("-" * len(title))

    def check(self, statement, ok):
        if ok:
            self.passed += 1
        else:
            self.failed += 1
        print(f"   check: {statement} ... {'PASS' if ok else 'FAIL'}")
        return bool(ok)

    def result(self, name, value, places=4):
        self.results[name] = float(value)
        if self.show_results:
            print(f"   result: {name} = {value:.{places}f}")
        return value

    def tally(self):
        print(f"\nchecks: {self.passed} passed, {self.failed} failed")
        return self.failed == 0
