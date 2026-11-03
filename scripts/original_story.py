"""
original_story.py -- put the two charts of the article being remixed into
screenshots/, and compare the numbers behind its line chart with this project's.

The article is Hannah Ritchie's "Many countries have decoupled economic growth
from CO2 emissions, even if we take offshored production into account" (Our
World in Data, 1 December 2021). It carries two charts:

  inputs/original_owid_line_chart_gbr.png   the article's interactive Grapher
        chart ("Change in per capita CO2 emissions and GDP", United Kingdom),
        as OWID's own PNG export served it on 4 October 2026. The embedded
        chart is redrawn whenever OWID updates its data, so this export runs
        to 2025 and is not pixel-identical to what a reader saw in 2021.
  inputs/original_owid_line_chart_gbr_chn.png   the same chart after adding
        China with its "Edit countries and regions" control: the chart splits
        into one panel per country on a shared percent axis.
  inputs/original_owid_line_chart_gbr.csv   the data behind that chart, from
        the same Grapher endpoint on the same day.
  inputs/original_owid_arrow_grid.png       the article's static grid of 30
        small panels, "Decoupling: Countries that achieved economic growth
        while reducing CO2 emissions, 2005-20" (credited on the image to Max
        Roser).

All of them are licensed CC BY by Our World in Data and are reproduced
unaltered. The script re-saves the three images, without resampling, under the
names the report uses (dropping the unused alpha channel), then checks two
things about the chart's data: its two CO2 series are the same numbers this
project plots, and its GDP series is a different one (World Bank, 2021 prices)
that grows faster than the Maddison series shipped in the CO2 dataset.

Run:  python scripts/original_story.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from PIL import Image

from common import BASE_YEAR, INPUTS, ROOT, SHOTS, YEAR_MAX, Log, load_focus

# (file in inputs/, file in screenshots/, tag used in the result names)
ORIGINALS = [
    ("original_owid_line_chart_gbr.png", "00a_original_owid_line_chart.png", "line_chart"),
    ("original_owid_line_chart_gbr_chn.png", "00b_original_owid_two_countries.png",
     "two_countries"),
    ("original_owid_arrow_grid.png", "00c_original_owid_arrow_grid.png", "arrow_grid"),
]
CHART_DATA = "original_owid_line_chart_gbr.csv"
# Column names as the Grapher CSV gives them (useColumnShortNames=true).
GDP, PROD, CONS = ("ny_gdp_pcap_pp_kd", "emissions_total_per_capita",
                   "consumption_emissions_per_capita")


def resave(log):
    log.section("1. Originals re-saved as PNG, no resampling")
    for source, target, tag in ORIGINALS:
        src = os.path.join(INPUTS, source)
        dst = os.path.join(SHOTS, target)
        if not log.check(f"{source} is present in inputs/", os.path.isfile(src)):
            continue
        with Image.open(src) as im:
            im.load()
            size = im.size
            im.convert("RGB").save(dst, optimize=True)
        with Image.open(dst) as back:
            same = back.size == size
        print(f"   {os.path.relpath(src, ROOT)}  {size[0]} x {size[1]} px  ->  "
              f"{os.path.relpath(dst, ROOT)}")
        log.check(f"{target} has the original's pixel dimensions ({size[0]} x {size[1]})", same)
        log.result(f"original_{tag}_width_px", size[0], 0)
        log.result(f"original_{tag}_height_px", size[1], 0)


def compare(log):
    log.section("2. The data behind the original line chart (United Kingdom)")
    path = os.path.join(INPUTS, CHART_DATA)
    if not log.check(f"{CHART_DATA} is present in inputs/", os.path.isfile(path)):
        return
    theirs = pd.read_csv(path).set_index("year")
    mine = load_focus()
    mine = mine[mine["country"] == "United Kingdom"].set_index("year")
    years = range(BASE_YEAR, YEAR_MAX + 1)

    def change(series):
        return 100.0 * (series.loc[YEAR_MAX] / series.loc[BASE_YEAR] - 1.0)

    gap_prod = (theirs.loc[years, PROD] - mine.loc[years, "co2_per_capita"]).abs().max()
    gap_cons = (theirs.loc[years, CONS] - mine.loc[years, "consumption_co2_per_capita"]).abs().max()
    log.check(f"the chart's production-based CO2 per person is this project's series, "
              f"{BASE_YEAR}-{YEAR_MAX} (worst gap {gap_prod:.5f} t)", gap_prod < 1e-3)
    log.check(f"the chart's consumption-based CO2 per person is this project's series "
              f"(worst gap {gap_cons:.5f} t)", gap_cons < 1e-3)

    wb, maddison = change(theirs[GDP]), change(mine["gdp_per_capita"])
    print(f"   GDP per person, {BASE_YEAR} to {YEAR_MAX}")
    print(f"      original chart, World Bank, international-$ at 2021 prices: "
          f"{theirs.loc[BASE_YEAR, GDP]:>9,.0f} -> {theirs.loc[YEAR_MAX, GDP]:>9,.0f}  ({wb:+.1f}%)")
    print(f"      this project, Maddison 2023, international-$ at 2011 prices: "
          f"{mine.loc[BASE_YEAR, 'gdp_per_capita']:>8,.0f} -> "
          f"{mine.loc[YEAR_MAX, 'gdp_per_capita']:>9,.0f}  ({maddison:+.1f}%)")
    log.result("original_gbr_gdp_pc_change_pct", wb)
    log.result("maddison_gbr_gdp_pc_change_pct", maddison)
    log.result("original_gbr_prod_change_pct", change(theirs[PROD]))
    log.result("original_gbr_cons_change_pct", change(theirs[CONS]))
    log.result("original_chart_last_year_gdp", theirs[GDP].dropna().index.max(), 0)
    log.result("original_chart_last_year_cons", theirs[CONS].dropna().index.max(), 0)
    log.check("the two GDP series agree on direction and differ in size by more than "
              "10 percentage points", wb > 0 and maddison > 0 and abs(wb - maddison) > 10)

    # The static grid compares 2005 with 2020 and shows only countries where each
    # change exceeded 5%. The article's lead example is not among its 30 panels;
    # these numbers show why, and how much the answer leans on the end year.
    def between(series, first, last):
        return 100.0 * (series.loc[last] / series.loc[first] - 1.0)

    print()
    print("   end-year sensitivity of a two-point comparison (the chart's own series)")
    for first, last in ((2005, 2020), (2005, 2019)):
        gdp, cons = between(theirs[GDP], first, last), between(theirs[CONS], first, last)
        print(f"      {first} to {last}: GDP per person {gdp:+.1f}%, "
              f"consumption-based CO2 per person {cons:+.1f}%")
        log.result(f"original_gbr_gdp_pc_change_{first}_{last}_pct", gdp)
        log.result(f"original_gbr_cons_change_{first}_{last}_pct", cons)
    log.result("original_gbr_cons_change_2019_2020_pct", between(theirs[CONS], 2019, 2020))
    log.result("original_gbr_cons_change_2020_2021_pct", between(theirs[CONS], 2020, 2021))
    log.check("on 2005-2020 the United Kingdom's GDP change is under the grid's 5% threshold, "
              "on 2005-2019 it is over it",
              between(theirs[GDP], 2005, 2020) < 5 < between(theirs[GDP], 2005, 2019))


def main():
    log = Log()
    log.banner("MODULE TWO - THE ORIGINAL STORY'S CHARTS")
    resave(log)
    compare(log)
    ok = log.tally()
    return {"results": log.results, "passed": log.passed, "failed": log.failed, "ok": ok}


if __name__ == "__main__":
    sys.exit(0 if main()["ok"] else 1)
