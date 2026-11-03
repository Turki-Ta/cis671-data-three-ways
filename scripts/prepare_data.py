"""
prepare_data.py -- turn the raw Our World in Data download into the tidy tables
the three visualizations read.

Input   inputs/owid-co2-data.csv                    50,411 rows, 79 columns, 1750-2024
        inputs/worldbank_country_classification.json

Output  inputs/decoupling_panel.csv     every country with a complete, real 1990-2022 series
        inputs/decoupling_focus.csv     the six focus countries, plus change since 1990
        inputs/decoupling_summary.csv   one row per focus country
        web/data/decoupling_data.js     the same focus series for the D3 page

Three variables are derived here and nowhere else:

    gdp_per_capita     = gdp / population                    international-$ (2011 prices)
    net_co2_per_capita = consumption_co2_per_capita - co2_per_capita       t CO2 per person
    net_co2_mt         = consumption_co2 - co2                             Mt CO2

The net balance is positive when a country consumes more CO2 than it emits on
its own territory (a net importer of embodied emissions) and negative when it
emits more than it consumes (a net exporter).

One trap in the raw file is handled here. For a few countries the
consumption-based figure of some years is not an estimate at all: it repeats
the production-based figure to six or more significant digits (Belgium and
Luxembourg up to 1998, South Africa and Botswana up to 1999, one year of
Tunisia), which makes the net balance exactly zero and then jump when the real
estimates begin. Those years are placeholders. They are treated as missing, and
a country that has any of them fails the completeness test like any other
country with a gap.

The script prints 'check: ... PASS' lines on its own arithmetic and
'result: name = value' lines for every number the report quotes; run_all.py
recomputes those from the raw file by a separate route.

Run:  python scripts/prepare_data.py
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd

from common import (BASE_YEAR, CONSUMPTION, COUNTRY_COLORS, EARLY, FOCUS, FOCUS_CSV,
                    FOCUS_SHORT, INCOME_COLORS, INCOME_ORDER, LATE, PANEL_CSV, PIVOT_YEAR,
                    PRODUCTION, RAW_CSV, RAW_WORLD_BANK, ROOT, SUMMARY_CSV, WB_INCOME,
                    WEB_DATA_JS, YEAR_MAX, YEAR_MIN, Log)

USECOLS = ["country", "year", "iso_code", "population", "gdp", "co2", "co2_per_capita",
           "consumption_co2", "consumption_co2_per_capita", "trade_co2", "trade_co2_share",
           "cumulative_co2", "share_global_cumulative_co2"]
# A country stays in the panel only if all six of these exist in all 33 years.
NEEDED = ["population", "gdp", "co2", "co2_per_capita", "consumption_co2",
          "consumption_co2_per_capita"]
# A consumption figure within one part in 100,000 of the production figure is a
# placeholder. Real balances never come that close: the smallest one in the file
# is 0.01% of production (Turkey, 2002), ten times this threshold.
PLACEHOLDER = 1e-5
PANEL_COLS = ["country", "iso_code", "year", "income_group", "region", "population", "gdp",
              "gdp_per_capita", "co2", "consumption_co2", "co2_per_capita",
              "consumption_co2_per_capita", "net_co2_per_capita", "net_co2_mt",
              "trade_co2_share", "cumulative_co2", "share_global_cumulative_co2", "is_focus"]
CHANGE_COLS = {"gdp_per_capita": "gdp_pc_change_pct", "co2_per_capita": "prod_change_pct",
               "consumption_co2_per_capita": "cons_change_pct"}
RETRIEVED = "2026-10-04"


def pct(new, old):
    return 100.0 * (new / old - 1.0)


# ---------------------------------------------------------------- panel
def build_panel(log):
    log.section("1. Raw file")
    raw = pd.read_csv(RAW_CSV, usecols=USECOLS)
    print(f"   {os.path.basename(RAW_CSV)}: {len(raw):,} rows, "
          f"{raw['country'].nunique()} entities, years {raw['year'].min()}-{raw['year'].max()}")
    for col in ("gdp", "consumption_co2_per_capita", "co2_per_capita"):
        years = raw.loc[raw[col].notna(), "year"]
        print(f"   {col:<28} available {years.min()}-{years.max()}")

    log.section("2. Panel")
    # Countries carry a three-letter ISO code; OWID's regional and income
    # aggregates carry none or an OWID_ code, and are left out.
    iso = raw["iso_code"].astype("string")
    window = raw[iso.str.len().eq(3).fillna(False)
                 & raw["year"].between(YEAR_MIN, YEAR_MAX)].copy()
    n_years = YEAR_MAX - YEAR_MIN + 1
    complete = window.dropna(subset=NEEDED).groupby("country")["year"].nunique()
    full = complete[complete == n_years].index
    print(f"   {window['country'].nunique()} countries have an ISO code and at least one row "
          f"in {YEAR_MIN}-{YEAR_MAX}")
    print(f"   {len(full)} of them have all of {', '.join(NEEDED)}")
    print(f"   in every one of the {n_years} years; the rest are dropped, not interpolated")

    # Placeholder years: consumption repeats production (see the module docstring).
    filled = window[window["country"].isin(full)]
    same = ((filled["consumption_co2"] - filled["co2"]).abs() / filled["co2"]) < PLACEHOLDER
    stand_ins = filled[same].groupby("country")["year"].agg(["count", "min", "max"])
    print(f"   {len(stand_ins)} of those carry placeholder consumption figures (equal to the "
          f"production figure")
    print(f"   to within 1 part in {1 / PLACEHOLDER:,.0f}) in {int(same.sum())} country-years "
          f"and are dropped as incomplete:")
    for country, row in stand_ins.iterrows():
        years = str(row["min"]) if row["count"] == 1 else f"{row['min']}-{row['max']}"
        print(f"      {country:<14}{years:>10}   ({row['count']} years)")
    keep = full.difference(stand_ins.index)
    panel = (window[window["country"].isin(keep)]
             .sort_values(["country", "year"]).reset_index(drop=True))
    real = ((panel["consumption_co2"] - panel["co2"]).abs() / panel["co2"]).min()
    print(f"   {len(keep)} countries remain; the closest the two accounts come in any of their "
          f"years is {100 * real:.3f}% of production")
    log.result("complete_countries", len(full), 0)
    log.result("placeholder_countries", len(stand_ins), 0)
    log.result("placeholder_country_years", same.sum(), 0)

    panel["gdp_per_capita"] = panel["gdp"] / panel["population"]
    panel["net_co2_per_capita"] = panel["consumption_co2_per_capita"] - panel["co2_per_capita"]
    panel["net_co2_mt"] = panel["consumption_co2"] - panel["co2"]

    with open(RAW_WORLD_BANK, encoding="utf-8") as fh:
        _, wb_rows = json.load(fh)
    wb = pd.DataFrame([{"iso_code": r["id"], "wb_income": r["incomeLevel"]["id"],
                        "region": r["region"]["value"].strip()} for r in wb_rows])
    panel = panel.merge(wb, on="iso_code", how="left")
    panel["income_group"] = panel["wb_income"].map(WB_INCOME)
    panel["is_focus"] = panel["country"].isin(FOCUS).astype(int)
    panel["population"] = panel["population"].round().astype("int64")

    log.check(f"panel is {len(keep)} countries x {n_years} years = {len(keep) * n_years:,} rows",
              len(panel) == len(keep) * n_years)
    log.check("no missing value in any needed or derived column",
              not panel[NEEDED + ["gdp_per_capita", "net_co2_per_capita"]].isna().any().any())
    log.check("all six focus countries are in the panel",
              set(FOCUS) <= set(panel["country"]))
    log.check("no placeholder is left: the two CO2 accounts differ by more than 1 part in "
              f"{1 / PLACEHOLDER:,.0f} in every row", real > PLACEHOLDER)
    return panel


def check_units(panel, log):
    log.section("3. Units and identities")
    # Per-capita columns are tonnes per person: Mt x 1e6 / people.
    rel_prod = ((panel["co2"] * 1e6 / panel["population"]) / panel["co2_per_capita"] - 1).abs().max()
    rel_cons = ((panel["consumption_co2"] * 1e6 / panel["population"])
                / panel["consumption_co2_per_capita"] - 1).abs().max()
    log.check(f"co2_per_capita = co2 x 1e6 / population (worst relative gap {rel_prod:.1e})",
              rel_prod < 1e-3)
    log.check(f"consumption_co2_per_capita = consumption_co2 x 1e6 / population "
              f"(worst relative gap {rel_cons:.1e})", rel_cons < 1e-3)
    # OWID's own trade_co2 column is consumption minus production; mine must match.
    gap = (panel["net_co2_mt"] - panel["trade_co2"]).abs().max()
    log.check(f"consumption_co2 - co2 equals OWID's trade_co2 (worst gap {gap:.4f} Mt)",
              gap < 0.01)
    rel_net = ((panel["net_co2_mt"] * 1e6 / panel["population"]) - panel["net_co2_per_capita"]).abs().max()
    log.check(f"net balance per person agrees with net balance in Mt (worst gap {rel_net:.4f} t)",
              rel_net < 0.01)
    lo, hi = panel["gdp_per_capita"].min(), panel["gdp_per_capita"].max()
    print(f"   GDP per capita in the panel runs from ${lo:,.0f} to ${hi:,.0f} (2011 international-$)")
    lo, hi = panel["net_co2_per_capita"].min(), panel["net_co2_per_capita"].max()
    print(f"   net balance per person runs from {lo:+.2f} t to {hi:+.2f} t")


# ---------------------------------------------------------------- focus countries
def build_focus(panel):
    focus = panel[panel["is_focus"] == 1].copy()
    base = focus[focus["year"] == BASE_YEAR].set_index("country")
    for col, new in CHANGE_COLS.items():
        focus[new] = pct(focus[col], focus["country"].map(base[col]))
    focus["country"] = pd.Categorical(focus["country"], categories=FOCUS, ordered=True)
    return focus.sort_values(["country", "year"]).reset_index(drop=True)


def summarise(focus, log):
    log.section("4. Focus countries")
    rows = []
    for country in FOCUS:
        d = focus[focus["country"] == country].set_index("year")
        first, pivot, last = d.loc[BASE_YEAR], d.loc[PIVOT_YEAR], d.loc[YEAR_MAX]
        net = d["net_co2_per_capita"]
        cons = d["consumption_co2_per_capita"]
        # How much of the territorial cut a wider import balance gave back. The
        # three terms are an identity: cons_cut = prod_cut - net_change.
        prod_cut = first["co2_per_capita"] - last["co2_per_capita"]
        cons_cut = first["consumption_co2_per_capita"] - last["consumption_co2_per_capita"]
        net_change = last["net_co2_per_capita"] - first["net_co2_per_capita"]
        growth = math.log(last["gdp_per_capita"] / first["gdp_per_capita"])
        rows.append({
            "country": country, "iso_code": first["iso_code"],
            "income_group": first["income_group"],
            "gdp_pc_1990": first["gdp_per_capita"], "gdp_pc_2022": last["gdp_per_capita"],
            "gdp_pc_change_pct": pct(last["gdp_per_capita"], first["gdp_per_capita"]),
            "prod_pc_1990": first["co2_per_capita"], "prod_pc_2022": last["co2_per_capita"],
            "prod_change_pct": pct(last["co2_per_capita"], first["co2_per_capita"]),
            "cons_pc_1990": first["consumption_co2_per_capita"],
            "cons_pc_2022": last["consumption_co2_per_capita"],
            "cons_change_pct": pct(last["consumption_co2_per_capita"],
                                   first["consumption_co2_per_capita"]),
            "cons_peak": cons.max(), "cons_peak_year": int(cons.idxmax()),
            "cons_change_to_peak_pct": pct(cons.max(), first["consumption_co2_per_capita"]),
            "gdp_pc_change_to_cons_peak_pct": pct(d.loc[int(cons.idxmax()), "gdp_per_capita"],
                                                  first["gdp_per_capita"]),
            "cons_change_from_peak_pct": pct(last["consumption_co2_per_capita"], cons.max()),
            "gdp_pc_change_1990_2007_pct": pct(pivot["gdp_per_capita"], first["gdp_per_capita"]),
            "prod_change_1990_2007_pct": pct(pivot["co2_per_capita"], first["co2_per_capita"]),
            "cons_change_1990_2007_pct": pct(pivot["consumption_co2_per_capita"],
                                             first["consumption_co2_per_capita"]),
            "gdp_pc_change_2007_2022_pct": pct(last["gdp_per_capita"], pivot["gdp_per_capita"]),
            "prod_change_2007_2022_pct": pct(last["co2_per_capita"], pivot["co2_per_capita"]),
            "cons_change_2007_2022_pct": pct(last["consumption_co2_per_capita"],
                                             pivot["consumption_co2_per_capita"]),
            "net_pc_1990": first["net_co2_per_capita"], "net_pc_2007": pivot["net_co2_per_capita"],
            "net_pc_2022": last["net_co2_per_capita"],
            "net_pc_max": net.max(), "net_pc_max_year": int(net.idxmax()),
            "net_pc_min": net.min(), "net_pc_min_year": int(net.idxmin()),
            "net_pc_mean_early": net.loc[EARLY[0]:EARLY[1]].mean(),
            "net_pc_mean_late": net.loc[LATE[0]:LATE[1]].mean(),
            "gdp_pc_mean_early": d["gdp_per_capita"].loc[EARLY[0]:EARLY[1]].mean(),
            "gdp_pc_mean_late": d["gdp_per_capita"].loc[LATE[0]:LATE[1]].mean(),
            "prod_cut_t": prod_cut, "cons_cut_t": cons_cut, "net_change_t": net_change,
            "offset_share_pct": 100.0 * net_change / prod_cut,
            "change_gap_points": pct(last["co2_per_capita"], first["co2_per_capita"])
                                 - pct(last["consumption_co2_per_capita"],
                                       first["consumption_co2_per_capita"]),
            "cons_over_prod_2022": last["consumption_co2_per_capita"] / last["co2_per_capita"],
            # Carbon intensity of income on the consumption account, kg CO2 per
            # international-$: the slope of the ray from the origin to a point of
            # the connected scatterplot. Falling intensity is relative decoupling;
            # a falling footprint is absolute decoupling.
            "cons_intensity_1990": 1000.0 * first["consumption_co2_per_capita"]
                                   / first["gdp_per_capita"],
            "cons_intensity_2022": 1000.0 * last["consumption_co2_per_capita"]
                                   / last["gdp_per_capita"],
            # Slope of the 1990-2022 chord in log-log space: the percent change in
            # CO2 per person that went with each one percent of GDP per person.
            "income_elasticity_cons": math.log(last["consumption_co2_per_capita"]
                                               / first["consumption_co2_per_capita"]) / growth,
            "income_elasticity_prod": math.log(last["co2_per_capita"]
                                               / first["co2_per_capita"]) / growth,
            "net_mt_1990": first["net_co2_mt"], "net_mt_2022": last["net_co2_mt"],
            "trade_share_2022_pct": last["trade_co2_share"],
            "prod_mt_2022": last["co2"], "cons_mt_2022": last["consumption_co2"],
            "population_2022": int(last["population"]),
            "cumulative_co2_2022_mt": last["cumulative_co2"],
            "share_global_cumulative_2022_pct": last["share_global_cumulative_co2"],
        })
    summary = pd.DataFrame(rows)

    print(f"   {'':<15}{'GDP/person':>22}{'production t/person':>24}{'consumption t/person':>24}")
    print(f"   {'country':<15}{'1990':>8}{'2022':>8}{'chg':>6}{'1990':>10}{'2022':>8}{'chg':>6}"
          f"{'1990':>10}{'2022':>8}{'chg':>6}")
    for r in rows:
        print(f"   {r['country']:<15}{r['gdp_pc_1990']:>8,.0f}{r['gdp_pc_2022']:>8,.0f}"
              f"{r['gdp_pc_change_pct']:>+5.0f}%{r['prod_pc_1990']:>10.2f}{r['prod_pc_2022']:>8.2f}"
              f"{r['prod_change_pct']:>+5.0f}%{r['cons_pc_1990']:>10.2f}{r['cons_pc_2022']:>8.2f}"
              f"{r['cons_change_pct']:>+5.0f}%")
    print()
    print(f"   net balance = consumption - production, t CO2 per person (+ importer, - exporter)")
    print(f"   {'country':<15}{'1990':>8}{'2007':>8}{'2022':>8}{'max (year)':>15}{'min (year)':>15}"
          f"{'2022 Mt':>10}{'% of prod.':>11}")
    for r in rows:
        print(f"   {r['country']:<15}{r['net_pc_1990']:>+8.2f}{r['net_pc_2007']:>+8.2f}"
              f"{r['net_pc_2022']:>+8.2f}{r['net_pc_max']:>+8.2f} ({r['net_pc_max_year']})"
              f"{r['net_pc_min']:>+8.2f} ({r['net_pc_min_year']}){r['net_mt_2022']:>+10.0f}"
              f"{r['trade_share_2022_pct']:>+10.1f}%")
    print()
    print(f"   how much of the territorial cut a wider import balance gave back, 1990-2022")
    print(f"   {'country':<15}{'prod. cut t':>12}{'cons. cut t':>12}{'net change t':>14}"
          f"{'offset share':>14}{'cons / prod 2022':>18}{'elasticity (cons)':>19}")
    for r in rows:
        print(f"   {r['country']:<15}{r['prod_cut_t']:>12.2f}{r['cons_cut_t']:>12.2f}"
              f"{r['net_change_t']:>+14.2f}{r['offset_share_pct']:>13.1f}%"
              f"{r['cons_over_prod_2022']:>18.3f}{r['income_elasticity_cons']:>+19.2f}")
    print(f"   carbon intensity of income on the consumption account, kg CO2 per international-$")
    print(f"   {'country':<15}{'1990':>8}{'2022':>8}{'change':>9}")
    for r in rows:
        print(f"   {r['country']:<15}{r['cons_intensity_1990']:>8.3f}{r['cons_intensity_2022']:>8.3f}"
              f"{pct(r['cons_intensity_2022'], r['cons_intensity_1990']):>+8.0f}%")
    print()
    published = ("gdp_pc_1990", "gdp_pc_2022", "gdp_pc_change_pct", "prod_pc_1990", "prod_pc_2022",
                 "prod_change_pct", "cons_pc_1990", "cons_pc_2022", "cons_change_pct",
                 "cons_peak", "cons_peak_year", "cons_change_to_peak_pct",
                 "gdp_pc_change_to_cons_peak_pct", "cons_change_from_peak_pct",
                 "gdp_pc_change_1990_2007_pct", "prod_change_1990_2007_pct",
                 "cons_change_1990_2007_pct",
                 "gdp_pc_change_2007_2022_pct", "prod_change_2007_2022_pct",
                 "cons_change_2007_2022_pct", "prod_cut_t", "cons_cut_t", "net_change_t",
                 "offset_share_pct", "change_gap_points", "cons_over_prod_2022",
                 "cons_intensity_1990", "cons_intensity_2022",
                 "income_elasticity_cons", "income_elasticity_prod",
                 "net_pc_1990", "net_pc_2007", "net_pc_2022",
                 "net_pc_max", "net_pc_max_year", "net_pc_min", "net_pc_min_year",
                 "net_pc_mean_early", "net_pc_mean_late", "gdp_pc_mean_early",
                 "gdp_pc_mean_late", "net_mt_1990", "net_mt_2022",
                 "trade_share_2022_pct", "cumulative_co2_2022_mt",
                 "share_global_cumulative_2022_pct")
    for r in rows:
        tag = r["iso_code"].lower()
        for key in published:
            log.result(f"{tag}_{key}", r[key])

    by = summary.set_index("country")
    importers = ["United States", "United Kingdom", "Germany", "Sweden"]
    log.check("the four high-income focus countries grew GDP per person and cut "
              "consumption-based CO2 per person, 1990-2022",
              all(by.loc[c, "gdp_pc_change_pct"] > 0 and by.loc[c, "cons_change_pct"] < 0
                  for c in importers))
    log.check("all four were net importers of embodied CO2 in 2022",
              all(by.loc[c, "net_pc_2022"] > 0 for c in importers))
    log.check("China and India were net exporters of embodied CO2 in 2022",
              all(by.loc[c, "net_pc_2022"] < 0 for c in ("China", "India")))
    log.check("carbon intensity of income fell in all six countries (relative decoupling)",
              (summary["cons_intensity_2022"] < summary["cons_intensity_1990"]).all())
    log.check("consumption cut = production cut - change in the net balance, for all six",
              ((summary["cons_cut_t"] - (summary["prod_cut_t"] - summary["net_change_t"])).abs()
               < 1e-9).all())
    return summary


# ---------------------------------------------------------------- income groups
def income_groups(panel, log):
    log.section("5. Income groups (World Bank classification for fiscal year 2027)")
    classed = panel.dropna(subset=["income_group"])
    unclassed = sorted(set(panel["country"]) - set(classed["country"]))
    counts = classed.groupby("income_group")["country"].nunique().reindex(INCOME_ORDER)
    for group, n in counts.items():
        print(f"   {group:<30}{n:>4} countries")
    # The World Bank does classify Taiwan (high income); its API response has no
    # entry for it, so the join on the ISO code finds nothing.
    print(f"   absent from the World Bank API response, left out of the scatter: "
          f"{', '.join(unclassed) or 'none'}")
    log.result("panel_countries", panel["country"].nunique(), 0)
    log.result("classified_countries", classed["country"].nunique(), 0)

    # Aggregate balance of a group: its countries' net Mt over their population.
    agg = classed.groupby(["income_group", "year"]).agg(net_mt=("net_co2_mt", "sum"),
                                                        pop=("population", "sum"))
    agg["net_pc"] = agg["net_mt"] * 1e6 / agg["pop"]
    tags = {"High income": "high", "Upper-middle income": "upper_middle",
            "Lower-middle and low income": "lower"}
    print()
    print(f"   group balance, t CO2 per person       {BASE_YEAR:>8}{PIVOT_YEAR:>8}{YEAR_MAX:>8}"
          f"{'  importers in 2022':>20}")
    for group in INCOME_ORDER:
        series = agg.loc[group]
        year_max = classed[(classed["income_group"] == group) & (classed["year"] == YEAR_MAX)]
        n_imp = int((year_max["net_co2_per_capita"] > 0).sum())
        print(f"   {group:<38}{series.loc[BASE_YEAR, 'net_pc']:>+8.2f}"
              f"{series.loc[PIVOT_YEAR, 'net_pc']:>+8.2f}{series.loc[YEAR_MAX, 'net_pc']:>+8.2f}"
              f"{n_imp:>10} of {len(year_max)}")
    print()
    for group in INCOME_ORDER:
        tag, series = tags[group], agg.loc[group]
        for year in (BASE_YEAR, PIVOT_YEAR, YEAR_MAX):
            log.result(f"group_{tag}_net_pc_{year}", series.loc[year, "net_pc"])
            log.result(f"group_{tag}_net_mt_{year}", series.loc[year, "net_mt"], 1)
        # 2008 is the last year of the Peters, Minx, et al. (2011) study of the
        # same transfer, so the group totals can be set beside its 0.4 and 1.6 Gt.
        log.result(f"group_{tag}_net_mt_2008", series.loc[2008, "net_mt"], 1)
        in_group = classed[classed["income_group"] == group]
        for year in (BASE_YEAR, YEAR_MAX):
            at = in_group[in_group["year"] == year]
            log.result(f"group_{tag}_importers_{year}", (at["net_co2_per_capita"] > 0).sum(), 0)
        log.result(f"group_{tag}_countries", in_group["country"].nunique(), 0)
        peak = series["net_mt"].abs().idxmax()
        log.result(f"group_{tag}_net_mt_extreme_year", peak, 0)
        log.result(f"group_{tag}_net_mt_extreme", series.loc[peak, "net_mt"], 1)

    # How tightly wealth and the balance go together, across countries. Spearman's
    # rho is Pearson's r on the ranks, which keeps the dependency list to pandas.
    def spearman(table):
        return table["gdp_per_capita"].rank().corr(table["net_co2_per_capita"].rank())

    for year in (BASE_YEAR, PIVOT_YEAR, YEAR_MAX):
        log.result(f"spearman_gdp_net_{year}", spearman(classed[classed["year"] == year]))
    # What the scatter shows under each of the two brush positions: every
    # country's mean over the window.
    for name, (y0, y1) in (("early", EARLY), ("late", LATE)):
        win = (classed[classed["year"].between(y0, y1)]
               .groupby("country")[["gdp_per_capita", "net_co2_per_capita"]].mean())
        log.result(f"spearman_gdp_net_window_{name}", spearman(win))
        groups = classed.drop_duplicates("country").set_index("country")["income_group"]
        high = win[groups.reindex(win.index) == "High income"]
        log.result(f"high_income_importers_window_{name}", (high["net_co2_per_capita"] > 0).sum(), 0)

    # Who is on each side of the trade in the last year, in tonnes: the exporting
    # side is a short list of large economies, not a class of countries.
    at = panel[panel["year"] == YEAR_MAX].sort_values("net_co2_mt")
    exporters, importers = at[at["net_co2_mt"] < 0], at[at["net_co2_mt"] > 0]
    print()
    print(f"   largest net exporters of embodied CO2 in {YEAR_MAX}, Mt: "
          + ", ".join(f"{r.country} {r.net_co2_mt:+.0f}" for r in exporters.head(5).itertuples()))
    print(f"   largest net importers of embodied CO2 in {YEAR_MAX}, Mt: "
          + ", ".join(f"{r.country} {r.net_co2_mt:+.0f}"
                      for r in importers.tail(5).iloc[::-1].itertuples()))
    log.result("exporters_2022", len(exporters), 0)
    log.result("importers_2022", len(importers), 0)
    log.result("exporters_net_mt_2022", exporters["net_co2_mt"].sum(), 1)
    log.result("importers_net_mt_2022", importers["net_co2_mt"].sum(), 1)
    log.result("exporters_top3_share_pct",
               100.0 * exporters["net_co2_mt"].head(3).sum() / exporters["net_co2_mt"].sum())
    for rank, r in enumerate(exporters.head(3).itertuples(), 1):
        log.result(f"exporter_{rank}_net_mt_2022", r.net_co2_mt, 1)
    log.check("the three largest exporters in 2022 are China, India and Russia",
              list(exporters["country"].head(3)) == ["China", "India", "Russia"])

    # 1991 is the one exception, and it is an artefact worth knowing about: the
    # Kuwait oil fires sit in Kuwait's territorial emissions for that year.
    high = agg.loc["High income", "net_mt"]
    kuwait = classed[(classed["country"] == "Kuwait") & (classed["year"] == 1991)]["net_co2_mt"].iloc[0]
    log.result("kuwait_net_mt_1991", kuwait, 1)
    log.result("group_high_net_mt_1991", high.loc[1991], 1)
    log.result("group_high_net_mt_1991_without_kuwait", high.loc[1991] - kuwait, 1)
    log.check("high-income countries as a group were net importers in every year but 1991 "
              "(Kuwait oil fires), and in 1991 too once Kuwait is set aside",
              list(high.index[high <= 0]) == [1991] and high.loc[1991] - kuwait > 0)
    log.check("upper-middle-income countries as a group were net exporters in every year",
              (agg.loc["Upper-middle income", "net_pc"] < 0).all())
    return agg


# ---------------------------------------------------------------- files
def write_files(panel, focus, summary, log):
    log.section("6. Files written")
    os.makedirs(os.path.dirname(WEB_DATA_JS), exist_ok=True)
    panel[PANEL_COLS].to_csv(PANEL_CSV, index=False, float_format="%.10g", lineterminator="\n")
    focus[PANEL_COLS + list(CHANGE_COLS.values())].to_csv(FOCUS_CSV, index=False,
                                                         float_format="%.10g", lineterminator="\n")
    summary.to_csv(SUMMARY_CSV, index=False, float_format="%.10g", lineterminator="\n")

    def series(d):
        return [{"year": int(r.year), "gdpPc": round(r.gdp_per_capita, 1),
                 "consPc": round(r.consumption_co2_per_capita, 4),
                 "prodPc": round(r.co2_per_capita, 4),
                 "netPc": round(r.net_co2_per_capita, 4),
                 "netMt": round(r.net_co2_mt, 2), "pop": int(r.population)}
                for r in d.itertuples()]

    countries = []
    for country in FOCUS:
        d = focus[focus["country"] == country]
        countries.append({"name": country, "short": FOCUS_SHORT[country],
                          "iso": d["iso_code"].iloc[0], "color": COUNTRY_COLORS[country],
                          "incomeGroup": d["income_group"].iloc[0], "series": series(d)})
    # The other countries, as bare arrays, for the optional grey context layer.
    context = []
    for country, d in panel[panel["is_focus"] == 0].groupby("country"):
        group = d["income_group"].iloc[0]
        context.append({"name": country, "iso": d["iso_code"].iloc[0],
                        "incomeGroup": None if pd.isna(group) else group,
                        "gdpPc": [round(v, 1) for v in d["gdp_per_capita"]],
                        "consPc": [round(v, 3) for v in d["consumption_co2_per_capita"]],
                        "prodPc": [round(v, 3) for v in d["co2_per_capita"]]})
    meta = {
        "yearMin": YEAR_MIN, "yearMax": YEAR_MAX, "baseYear": BASE_YEAR,
        "retrieved": RETRIEVED,
        "source": ("Our World in Data CO2 and Greenhouse Gas Emissions dataset: Global Carbon "
                   "Budget (2025), Maddison Project Database 2023, OWID population (2024)"),
        "units": {"gdpPc": "international-$ at 2011 prices, per person",
                  "consPc": "t CO2 per person, consumption-based",
                  "prodPc": "t CO2 per person, production-based (territorial)",
                  "netPc": "t CO2 per person, consumption minus production",
                  "netMt": "Mt CO2, consumption minus production", "pop": "people"},
        "colors": {"consumption": CONSUMPTION, "production": PRODUCTION,
                   "income": INCOME_COLORS},
    }

    def dump(obj):
        return json.dumps(obj, separators=(",", ":"), ensure_ascii=True)

    lines = ["// Written by scripts/prepare_data.py from inputs/decoupling_focus.csv and",
             "// inputs/decoupling_panel.csv. Loaded with a <script> tag, so the page also",
             "// works when index.html is opened straight from disk.",
             "window.DECOUPLING_DATA = {",
             f'"meta":{dump(meta)},',
             '"countries":[']
    for i, c in enumerate(countries):
        head = {k: v for k, v in c.items() if k != "series"}
        lines.append(dump(head)[:-1] + ',"series":[')
        lines += [dump(row) + ("," if j < len(c["series"]) - 1 else "")
                  for j, row in enumerate(c["series"])]
        lines.append("]}" + ("," if i < len(countries) - 1 else ""))
    lines.append('],')
    lines.append('"context":[')
    lines += [dump(c) + ("," if i < len(context) - 1 else "") for i, c in enumerate(context)]
    lines.append("]")
    lines.append("};")
    with open(WEB_DATA_JS, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")

    for path, what in ((PANEL_CSV, f"{panel['country'].nunique()} countries x "
                                   f"{panel['year'].nunique()} years"),
                       (FOCUS_CSV, f"{len(FOCUS)} countries x {focus['year'].nunique()} years"),
                       (SUMMARY_CSV, f"{len(summary)} rows"),
                       (WEB_DATA_JS, f"{len(countries)} focus series, {len(context)} context")):
        print(f"   {os.path.relpath(path, ROOT):<34}{os.path.getsize(path) / 1024:>8.1f} KB   {what}")

    back = pd.read_csv(FOCUS_CSV)
    log.check("decoupling_focus.csv reads back as 198 rows with no missing value in the plotted columns",
              len(back) == len(FOCUS) * (YEAR_MAX - YEAR_MIN + 1)
              and not back[["gdp_per_capita", "co2_per_capita", "consumption_co2_per_capita",
                            "net_co2_per_capita"] + list(CHANGE_COLS.values())].isna().any().any())
    with open(WEB_DATA_JS, encoding="utf-8") as fh:
        text = fh.read()
    body = text[text.index("{"):text.rindex("}") + 1]
    parsed = json.loads(body)
    log.check("decoupling_data.js parses as JSON and holds the six focus series of 33 years each",
              [c["name"] for c in parsed["countries"]] == FOCUS
              and all(len(c["series"]) == 33 for c in parsed["countries"]))


def main(show_results=True):
    log = Log(show_results=show_results)
    log.banner("MODULE TWO - DATA PREPARATION")
    print(f"   window {YEAR_MIN}-{YEAR_MAX}, base year {BASE_YEAR}, focus: {', '.join(FOCUS)}")
    panel = build_panel(log)
    check_units(panel, log)
    focus = build_focus(panel)
    summary = summarise(focus, log)
    income_groups(panel, log)
    write_files(panel, focus, summary, log)
    ok = log.tally()
    return {"results": log.results, "passed": log.passed, "failed": log.failed, "ok": ok}


if __name__ == "__main__":
    sys.exit(0 if main()["ok"] else 1)
