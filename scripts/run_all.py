"""
run_all.py -- run the Module Two scripts in order, tee each one's stdout to
screenshots/logs/<name>.txt, then re-derive the published numbers independently.

Order matters: the data tables come first, the two Python visualizations next,
and the web capture last, because the page it photographs embeds the Altair
export and a copy of the Seaborn figure.

The scripts publish their numbers as "result: name = value" lines. After they
have run, this script goes back to the raw downloads (inputs/owid-co2-data.csv,
and the CSV behind the original article's line chart), reads them with the csv
module alone (no pandas, none of the project's own helpers) and recomputes
those numbers from the definitions:

    GDP per person = gdp / population
    net balance    = consumption-based CO2 - production-based CO2
    change         = 100 x (value in the later year / value in the earlier year - 1)

and compares its answers with what the logs say. The point is a second,
separate path through the arithmetic: a slip in prepare_data.py, a wrong
column, a wrong year or a wrong sign shows up here as a mismatch instead of
travelling into the report. Some published values have no second route
because they measure the output and not the data: image sizes, library
versions, contrast ratios, the error of reading a plotted point back. Those
are counted per script and left alone. The verification block is teed to
screenshots/logs/run_all.txt, and render_logs.py runs last so the terminal
PNGs are drawn from the fresh logs.

The run stops at the first failing script: the verification and the terminal
captures would only describe stale files after that.

Usage:  python scripts/run_all.py
        python scripts/run_all.py prepare_data vis3_seaborn_diverging    # a subset, same order
"""
import csv
import json
import math
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INPUTS = os.path.join(ROOT, "inputs")
LOGS = os.path.join(ROOT, "screenshots", "logs")

ORDER = [
    "fetch_inputs.py",              # SHA-256 of the seven raw downloads
    "prepare_data.py",              # raw CSV -> panel, focus table, summary, web data
    "original_story.py",            # the remixed article's two charts and their data
    "vis1_altair_linked.py",        # Visualization 1: Altair linked views + browser check
    "vis3_seaborn_diverging.py",    # Visualization 3: Seaborn small multiples
    "capture_web.py",               # Visualization 2: D3 page self-test and captures
]
RULE = "=" * 78
RESULT = re.compile(r"^\s*result:\s*([A-Za-z0-9_]+)\s*=\s*([-+0-9.eE]+)\s*$")
# The scripts print 4 decimals for most values and 1 for totals in Mt, so
# agreement to 5e-4 relative, or to the last printed digit, means the same number.
TOL = 5e-4

YEARS = range(1990, 2023)
FOCUS = {"usa": "United States", "gbr": "United Kingdom", "deu": "Germany",
         "swe": "Sweden", "chn": "China", "ind": "India"}
NEEDED = ("population", "gdp", "co2", "co2_per_capita", "consumption_co2",
          "consumption_co2_per_capita")
EARLY, LATE, PIVOT = range(1990, 2000), range(2013, 2023), 2007
# The range of the net-balance axis in Visualization 1 (Y_LO, Y_HI there): a
# country whose window mean falls outside it is drawn pinned to the edge.
AXIS_LO, AXIS_HI = -6.0, 8.0
GROUPS = {"HIC": "high", "UMC": "upper_middle", "LMC": "lower", "LIC": "lower"}
# The data behind the original article's line chart, as the Grapher exports it.
CHART = "original_owid_line_chart_gbr.csv"
CHART_GDP, CHART_CONS = "ny_gdp_pcap_pp_kd", "consumption_emissions_per_capita"
# Names other scripts use for numbers that prepare_data.py publishes under a
# different name: {alias pattern: canonical pattern}, with {c} the country tag.
FIXED_ALIASES = {
    "plotted_countries": "classified_countries",
    "high_income_countries": "group_high_countries",
    "upper_middle_countries": "group_upper_middle_countries",
    "lower_countries": "group_lower_countries",
    "maddison_gbr_gdp_pc_change_pct": "gbr_gdp_pc_change_pct",
    "original_gbr_prod_change_pct": "gbr_prod_change_pct",
    "original_gbr_cons_change_pct": "gbr_cons_change_pct",
}
ALIASES = {
    "{c}_net_window_early": "{c}_net_pc_mean_early",
    "{c}_net_window_late": "{c}_net_pc_mean_late",
    "{c}_gdp_window_early": "{c}_gdp_pc_mean_early",
    "{c}_gdp_window_late": "{c}_gdp_pc_mean_late",
    "{c}_net_1990": "{c}_net_pc_1990",
    "{c}_net_2022": "{c}_net_pc_2022",
}


class Tee:
    """print() to the console and to a log file at the same time."""

    def __init__(self, path):
        self.fh = open(path, "w", encoding="utf-8")

    def __call__(self, text=""):
        print(text, flush=True)
        self.fh.write(text + "\n")

    def close(self):
        self.fh.close()


def run(script, py, env):
    print(f"\n{RULE}\nRUNNING {script}\n{RULE}", flush=True)
    log = os.path.join(LOGS, script.replace(".py", ".txt"))
    t0 = time.perf_counter()
    # stderr is merged into stdout so warnings land in the log in the order
    # they happened, next to the line that caused them.
    with open(log, "w", encoding="utf-8") as fh:
        proc = subprocess.Popen([py, "-u", os.path.join(HERE, script)], cwd=ROOT, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            sys.stdout.write(line)
            fh.write(line)
        proc.wait()
    dt = time.perf_counter() - t0
    print(f"-> exit {proc.returncode} after {dt:.1f}s, log at {os.path.relpath(log, ROOT)}",
          flush=True)
    return proc.returncode, dt


# ---------------------------------------------------------------- reading back
def published(script):
    """The 'result:' lines and the PASS / FAIL counts of one script's log."""
    values, passed, failed = {}, 0, 0
    path = os.path.join(LOGS, script.replace(".py", ".txt"))
    if not os.path.isfile(path):
        return None, 0, 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            m = RESULT.match(line)
            if m:
                values[m.group(1)] = float(m.group(2))
            if line.lstrip().startswith("check:"):
                passed += line.rstrip().endswith("PASS")
                failed += line.rstrip().endswith("FAIL")
    return values, passed, failed


def number(text):
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def load_raw():
    """{country: {year: row}} for rows with an ISO-3 code inside the window,
    with the needed columns parsed to float (None where the cell is empty)."""
    table = {}
    with open(os.path.join(INPUTS, "owid-co2-data.csv"), encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            year = int(row["year"])
            if len(row["iso_code"]) != 3 or year not in YEARS:
                continue
            keep = {col: number(row[col]) for col in NEEDED}
            keep["iso"] = row["iso_code"]
            keep["cumulative_co2"] = number(row["cumulative_co2"])
            keep["share_global_cumulative_co2"] = number(row["share_global_cumulative_co2"])
            keep["trade_co2_share"] = number(row["trade_co2_share"])
            table.setdefault(row["country"], {})[year] = keep
    return table


def change(new, old):
    return 100.0 * (new / old - 1.0)


def spearman(xs, ys):
    """Rank correlation with average ranks for ties, written out longhand."""
    def ranks(values):
        order = sorted(range(len(values)), key=lambda i: values[i])
        out, i = [0.0] * len(values), 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
                j += 1
            for k in range(i, j + 1):
                out[order[k]] = (i + j) / 2.0 + 1.0
            i = j + 1
        return out
    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    return cov / (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5


# ---------------------------------------------------------------- re-derivation
def derive():
    raw = load_raw()
    full = {c: rows for c, rows in raw.items()
            if all(y in rows and all(rows[y][col] is not None for col in NEEDED)
                   for y in YEARS)}

    # A consumption figure that repeats the production figure is a placeholder,
    # and a country with any such year is not complete.
    def stand_in(r):
        return abs(r["consumption_co2"] - r["co2"]) / r["co2"] < 1e-5

    flagged = {c: sum(stand_in(rows[y]) for y in YEARS) for c, rows in full.items()}
    panel = {c: rows for c, rows in full.items() if not flagged[c]}
    out = {"complete_countries": len(full), "panel_countries": len(panel),
           "placeholder_countries": sum(n > 0 for n in flagged.values()),
           "placeholder_country_years": sum(flagged.values())}

    def gdp_pc(r):
        return r["gdp"] / r["population"]

    def net_pc(r):
        return r["consumption_co2_per_capita"] - r["co2_per_capita"]

    def net_mt(r):
        return r["consumption_co2"] - r["co2"]

    for tag, country in FOCUS.items():
        rows = panel[country]
        first, pivot, last = rows[1990], rows[PIVOT], rows[2022]
        net = {y: net_pc(rows[y]) for y in YEARS}
        cons = {y: rows[y]["consumption_co2_per_capita"] for y in YEARS}
        year_max, year_min = max(net, key=net.get), min(net, key=net.get)
        peak_year = max(cons, key=cons.get)
        prod_cut = first["co2_per_capita"] - last["co2_per_capita"]
        growth = math.log(gdp_pc(last) / gdp_pc(first))
        out.update({
            f"{tag}_gdp_pc_change_1990_2007_pct": change(gdp_pc(pivot), gdp_pc(first)),
            f"{tag}_prod_change_1990_2007_pct": change(pivot["co2_per_capita"],
                                                       first["co2_per_capita"]),
            f"{tag}_cons_change_1990_2007_pct": change(cons[PIVOT], cons[1990]),
            f"{tag}_prod_cut_t": prod_cut,
            f"{tag}_cons_cut_t": cons[1990] - cons[2022],
            f"{tag}_net_change_t": net[2022] - net[1990],
            f"{tag}_offset_share_pct": 100.0 * (net[2022] - net[1990]) / prod_cut,
            f"{tag}_change_gap_points": change(last["co2_per_capita"], first["co2_per_capita"])
                                        - change(cons[2022], cons[1990]),
            f"{tag}_cons_over_prod_2022": cons[2022] / last["co2_per_capita"],
            f"{tag}_cons_intensity_1990": 1000.0 * cons[1990] / gdp_pc(first),
            f"{tag}_cons_intensity_2022": 1000.0 * cons[2022] / gdp_pc(last),
            f"{tag}_income_elasticity_cons": math.log(cons[2022] / cons[1990]) / growth,
            f"{tag}_income_elasticity_prod": math.log(last["co2_per_capita"]
                                                      / first["co2_per_capita"]) / growth,
            f"{tag}_gdp_pc_1990": gdp_pc(first), f"{tag}_gdp_pc_2022": gdp_pc(last),
            f"{tag}_gdp_pc_change_pct": change(gdp_pc(last), gdp_pc(first)),
            f"{tag}_prod_pc_1990": first["co2_per_capita"],
            f"{tag}_prod_pc_2022": last["co2_per_capita"],
            f"{tag}_prod_change_pct": change(last["co2_per_capita"], first["co2_per_capita"]),
            f"{tag}_cons_pc_1990": cons[1990], f"{tag}_cons_pc_2022": cons[2022],
            f"{tag}_cons_change_pct": change(cons[2022], cons[1990]),
            f"{tag}_cons_peak": cons[peak_year], f"{tag}_cons_peak_year": peak_year,
            f"{tag}_cons_change_to_peak_pct": change(cons[peak_year], cons[1990]),
            f"{tag}_gdp_pc_change_to_cons_peak_pct": change(gdp_pc(rows[peak_year]),
                                                            gdp_pc(first)),
            f"{tag}_cons_change_from_peak_pct": change(cons[2022], cons[peak_year]),
            f"{tag}_gdp_pc_change_2007_2022_pct": change(gdp_pc(last), gdp_pc(pivot)),
            f"{tag}_prod_change_2007_2022_pct": change(last["co2_per_capita"],
                                                       pivot["co2_per_capita"]),
            f"{tag}_cons_change_2007_2022_pct": change(cons[2022], cons[PIVOT]),
            f"{tag}_net_pc_1990": net[1990], f"{tag}_net_pc_2007": net[PIVOT],
            f"{tag}_net_pc_2022": net[2022],
            f"{tag}_net_pc_max": net[year_max], f"{tag}_net_pc_max_year": year_max,
            f"{tag}_net_pc_min": net[year_min], f"{tag}_net_pc_min_year": year_min,
            f"{tag}_net_pc_mean_early": sum(net[y] for y in EARLY) / len(EARLY),
            f"{tag}_net_pc_mean_late": sum(net[y] for y in LATE) / len(LATE),
            f"{tag}_gdp_pc_mean_early": sum(gdp_pc(rows[y]) for y in EARLY) / len(EARLY),
            f"{tag}_gdp_pc_mean_late": sum(gdp_pc(rows[y]) for y in LATE) / len(LATE),
            f"{tag}_net_mt_1990": net_mt(first), f"{tag}_net_mt_2007": net_mt(pivot),
            f"{tag}_net_mt_2022": net_mt(last),
            # the first year from which the country stays a net importer
            f"{tag}_net_importer_since_year": next(
                (y for y in YEARS if all(net[z] > 0 for z in range(y, 2023))), float("nan")),
            f"{tag}_trade_share_2022_pct": last["trade_co2_share"],
            f"{tag}_cumulative_co2_2022_mt": last["cumulative_co2"],
            f"{tag}_share_global_cumulative_2022_pct": last["share_global_cumulative_co2"],
        })

    # The first year from which China's balance in Mt is the largest of the six.
    size = {tag: {y: abs(net_mt(panel[country][y])) for y in YEARS}
            for tag, country in FOCUS.items()}
    out["chn_net_mt_largest_since_year"] = next(
        y for y in YEARS if all(size["chn"][z] >= max(s[z] for s in size.values())
                                for z in range(y, 2023)))
    out["importers_with_larger_territorial_cut"] = sum(
        out[f"{tag}_prod_change_pct"] < out[f"{tag}_cons_change_pct"]
        for tag in ("usa", "gbr", "deu", "swe"))

    # Income groups, from the World Bank file as downloaded.
    with open(os.path.join(INPUTS, "worldbank_country_classification.json"),
              encoding="utf-8") as fh:
        _, wb = json.load(fh)
    income = {r["id"]: GROUPS[r["incomeLevel"]["id"]] for r in wb
              if r["incomeLevel"]["id"] in GROUPS}
    grouped = {}
    for country, rows in panel.items():
        group = income.get(rows[1990]["iso"])
        if group:
            grouped.setdefault(group, []).append(rows)
    out["classified_countries"] = sum(len(v) for v in grouped.values())
    for group, members in grouped.items():
        out[f"group_{group}_countries"] = len(members)
        totals = {y: sum(net_mt(rows[y]) for rows in members) for y in YEARS}
        for year in (1990, PIVOT, 2022):
            people = sum(rows[year]["population"] for rows in members)
            out[f"group_{group}_net_mt_{year}"] = totals[year]
            out[f"group_{group}_net_pc_{year}"] = totals[year] * 1e6 / people
        out[f"group_{group}_net_mt_2008"] = totals[2008]
        for year in (1990, 2022):
            out[f"group_{group}_importers_{year}"] = sum(net_pc(rows[year]) > 0
                                                         for rows in members)
        extreme = max(totals, key=lambda y: abs(totals[y]))
        out[f"group_{group}_net_mt_extreme_year"] = extreme
        out[f"group_{group}_net_mt_extreme"] = totals[extreme]
    balances = sorted(net_mt(rows[2022]) for rows in panel.values())
    negative = [b for b in balances if b < 0]
    positive = [b for b in balances if b > 0]
    out["exporters_2022"], out["importers_2022"] = len(negative), len(positive)
    out["exporters_net_mt_2022"], out["importers_net_mt_2022"] = sum(negative), sum(positive)
    out["exporters_top3_share_pct"] = 100.0 * sum(negative[:3]) / sum(negative)
    for rank in (1, 2, 3):
        out[f"exporter_{rank}_net_mt_2022"] = negative[rank - 1]
    kuwait = net_mt(panel["Kuwait"][1991])
    high_1991 = sum(net_mt(rows[1991]) for rows in grouped["high"])
    out["kuwait_net_mt_1991"] = kuwait
    out["group_high_net_mt_1991"] = high_1991
    out["group_high_net_mt_1991_without_kuwait"] = high_1991 - kuwait

    everyone = [rows for members in grouped.values() for rows in members]
    for year in (1990, PIVOT, 2022):
        out[f"spearman_gdp_net_{year}"] = spearman([gdp_pc(r[year]) for r in everyone],
                                                   [net_pc(r[year]) for r in everyone])
    # What the scatter of Visualization 1 shows: each country's mean over a
    # window of years, counted by side of zero, by income group and by whether
    # it falls outside the axis.
    def window_mean(rows, f, years):
        return sum(f(rows[y]) for y in years) / len(years)

    names = {"high": "high_income", "upper_middle": "upper_middle", "lower": "lower"}
    for name, window in (("early", EARLY), ("late", LATE), ("all", YEARS)):
        means = {g: [window_mean(r, net_pc, window) for r in members]
                 for g, members in grouped.items()}
        flat = [m for group_means in means.values() for m in group_means]
        out[f"importers_window_{name}"] = sum(m > 0 for m in flat)
        for group, label in names.items():
            out[f"{label}_importers_window_{name}"] = sum(m > 0 for m in means[group])
        out[f"offscale_above_window_{name}"] = sum(m > AXIS_HI for m in flat)
        out[f"offscale_below_window_{name}"] = sum(m < AXIS_LO for m in flat)
        out[f"offscale_window_{name}"] = sum(not AXIS_LO <= m <= AXIS_HI for m in flat)
    # Every window an interval brush can select: 33 x 34 / 2 spans of whole years.
    spans = [range(a, b + 1) for a in YEARS for b in range(a, 2023)]
    out["windows_a_brush_can_select"] = len(spans)
    out["offscale_most_in_any_window"] = max(
        sum(not AXIS_LO <= window_mean(r, net_pc, span) <= AXIS_HI for r in everyone)
        for span in spans)

    for name, window in (("early", EARLY), ("late", LATE)):
        def mean(rows, f):
            return sum(f(rows[y]) for y in window) / len(window)
        out[f"spearman_gdp_net_window_{name}"] = spearman(
            [mean(r, gdp_pc) for r in everyone], [mean(r, net_pc) for r in everyone])
        out[f"high_income_importers_window_{name}"] = sum(mean(r, net_pc) > 0
                                                          for r in grouped["high"])
    return out


def derive_chart():
    """What original_story.py reads off the original chart's own data for the United
    Kingdom: World Bank GDP per person and consumption-based CO2 per person."""
    series = {CHART_GDP: {}, CHART_CONS: {}}
    with open(os.path.join(INPUTS, CHART), encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            for col, values in series.items():
                value = number(row[col])
                if value is not None:
                    values[int(row["year"])] = value
    gdp, cons = series[CHART_GDP], series[CHART_CONS]
    out = {"original_gbr_gdp_pc_change_pct": change(gdp[2022], gdp[1990]),
           "original_chart_last_year_gdp": max(gdp),
           "original_chart_last_year_cons": max(cons),
           "original_gbr_cons_change_2019_2020_pct": change(cons[2020], cons[2019]),
           "original_gbr_cons_change_2020_2021_pct": change(cons[2021], cons[2020])}
    for last in (2020, 2019):
        out[f"original_gbr_gdp_pc_change_2005_{last}_pct"] = change(gdp[last], gdp[2005])
        out[f"original_gbr_cons_change_2005_{last}_pct"] = change(cons[last], cons[2005])
    return out


def browser_window(years):
    """The six focus countries' mean net balance over an arbitrary span of years."""
    raw = load_raw()
    out = {}
    for tag, country in FOCUS.items():
        rows = raw[country]
        out[f"{tag}_net_window_browser"] = sum(
            rows[y]["consumption_co2_per_capita"] - rows[y]["co2_per_capita"]
            for y in years) / len(years)
    return out


def canonical(name):
    """The prepare_data.py name for a result another script may publish as an alias."""
    if name in FIXED_ALIASES:
        return FIXED_ALIASES[name]
    for tag in FOCUS:
        for alias, target in ALIASES.items():
            if name == alias.format(c=tag):
                return target.format(c=tag)
    return name


def agrees(script_value, mine):
    return abs(script_value - mine) <= TOL * max(1.0, abs(mine))


def verify(scripts, out):
    out(RULE)
    out("INDEPENDENT VERIFICATION OF THE PUBLISHED NUMBERS")
    out(RULE)
    out("   Recomputed here from the raw files in inputs/ with the csv module and the")
    out("   definitions alone, then compared with the 'result:' lines each script printed.")
    mine = derive()
    mine.update(derive_chart())
    bad = compared = uncompared = 0
    for script in scripts:
        values, passed, failed = published(script)
        out("")
        out(f"{script}")
        if values is None:
            out("   (no log found)   FAIL")
            bad += 1
            continue
        # Visualization 1 drags a brush in a real browser and publishes what the
        # scatter then held; the window is the script's choice, so it is read here.
        first = values.get("browser_window_first_year")
        last = values.get("browser_window_last_year")
        if first is not None and last is not None:
            mine.update(browser_window(range(int(first), int(last) + 1)))
        rows = [(name, value, mine[canonical(name)]) for name, value in values.items()
                if canonical(name) in mine]
        # Values printed with one decimal (totals in Mt) are compared at that precision.
        mismatched = [(n, v, m) for n, v, m in rows
                      if not (agrees(v, m) or abs(v - m) <= 0.051)]
        rest = len(values) - len(rows)
        compared += len(rows)
        uncompared += rest
        bad += len(mismatched) + failed
        if values:
            other = (f", {rest} measure{'s' if rest == 1 else ''} the output, not the data"
                     if rest else "")
            out(f"   {len(values)} values: {len(rows)} recomputed "
                f"({len(rows) - len(mismatched)} agree, {len(mismatched)} disagree){other}")
        else:
            out("   publishes no values")
        for name, value, m in mismatched:
            out(f"   {name:<44}{value:>14.4f}{m:>14.4f}   FAIL")
        out(f"   the script's own checks: {passed} passed, {failed} failed")

    # The headline numbers, shown in full so the comparison can be read, not just counted.
    values, _, _ = published("prepare_data.py")
    if values:
        out("")
        out("headline values (prepare_data.py against the recomputation)")
        out(f"   {'result':<40}{'script':>14}{'recomputed':>14}   agreement")
        for tag in FOCUS:
            for key in ("gdp_pc_change_pct", "prod_change_pct", "cons_change_pct",
                        "net_pc_1990", "net_pc_2022", "net_mt_2022", "offset_share_pct"):
                name = f"{tag}_{key}"
                if name not in values:
                    out(f"   {name:<40}{'(missing)':>14}{mine[name]:>14.4f}   FAIL")
                    bad += 1
                    continue
                ok = agrees(values[name], mine[name])
                out(f"   {name:<40}{values[name]:>14.4f}{mine[name]:>14.4f}   "
                    f"{'PASS' if ok else 'FAIL'}")
        for name in ("complete_countries", "placeholder_country_years", "panel_countries",
                     "classified_countries", "group_high_net_mt_1990",
                     "group_high_net_mt_2022", "group_upper_middle_net_mt_2022",
                     "kuwait_net_mt_1991"):
            if name in values:
                ok = agrees(values[name], mine[name]) or abs(values[name] - mine[name]) <= 0.051
                out(f"   {name:<40}{values[name]:>14.1f}{mine[name]:>14.1f}   "
                    f"{'PASS' if ok else 'FAIL'}")
    out("")
    out("-" * 78)
    out(f"verification: all {compared} recomputed values agree and no script check failed"
        if not bad else f"verification: {bad} problem(s) - see the FAIL lines above")
    return bad == 0, compared, uncompared


def main(argv):
    os.makedirs(LOGS, exist_ok=True)
    wanted = [a if a.endswith(".py") else a + ".py" for a in argv]
    unknown = [w for w in wanted if w not in ORDER]
    if unknown:
        sys.exit(f"unknown script(s): {unknown}; choose from {ORDER}")
    todo = [s for s in ORDER if not wanted or s in wanted]
    # A non-interactive backend in the children means a stray plt.show() can
    # never block the batch run waiting for a window to close.
    env = dict(os.environ, MPLBACKEND="Agg", PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    timings = []
    for script in todo:
        code, dt = run(script, sys.executable, env)
        timings.append((script, dt))
        if code != 0:
            print(f"\nFAILED: {script} exited with {code}; later steps were not run.")
            sys.exit(1)

    print()
    tee = Tee(os.path.join(LOGS, "run_all.txt"))
    ok, compared, uncompared = verify(todo, tee)
    tee.close()

    code, dt = run("render_logs.py", sys.executable, env)
    timings.append(("render_logs.py", dt))

    print(f"\n{RULE}")
    for script, dt in timings:
        print(f"  {script:<30}{dt:8.1f}s")
    if not ok or code != 0:
        print("FINISHED WITH PROBLEMS: see the FAIL lines above.")
        sys.exit(1)
    print(f"All {len(todo)} scripts ran, {compared} of the {compared + uncompared} published "
          f"values were re-derived from the raw files (the other {uncompared} measure the "
          f"output), and the terminal captures were rendered "
          f"({sum(dt for _, dt in timings):.1f}s).")


if __name__ == "__main__":
    main(sys.argv[1:])
