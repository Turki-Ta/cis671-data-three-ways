"""
fetch_inputs.py -- check the raw downloads in inputs/ against their recorded
SHA-256, or download them again.

    python scripts/fetch_inputs.py            verify only, no network
    python scripts/fetch_inputs.py --fetch    download again, then verify

Three files are the data (the OWID CO2 dataset, its codebook and the World Bank
classification) and four are the original article's material (its line chart
as a PNG export for the United Kingdom, the same chart with China added, the
data behind the chart, and its static grid image).

Our World in Data rebuilds owid-co2-data.csv and redraws its charts whenever an
upstream source is revised, and the World Bank reclassifies countries every
July, so a fresh download is expected to differ from the copy this project was
built on. A changed hash after --fetch is therefore reported as "changed
upstream", not as an error: re-run prepare_data.py and read its checks before
trusting any number in the report. Without --fetch a changed hash means the
local file was edited, and that is an error.
"""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INPUTS = os.path.join(ROOT, "inputs")
_GRAPHER = "https://ourworldindata.org/grapher/co2-emissions-and-gdp-per-capita"

# File -> (URL, SHA-256 of the copy retrieved on 4 October 2026).
SOURCES = {
    "owid-co2-data.csv": (
        "https://owid-public.owid.io/data/co2/owid-co2-data.csv",
        "7ec10de1e9502c20c70bfff54476d7893922f7594aa299d9291d87fe49f3e342"),
    "owid-co2-codebook.csv": (
        "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-codebook.csv",
        "33b4f5e00efd58c7b83863f736beba1af4df946b43642b0400c3ec38648e0e8e"),
    "worldbank_country_classification.json": (
        "https://api.worldbank.org/v2/country?format=json&per_page=400",
        "d29d57f8adf954c5e2a1520a02fb2c7b45575d8db3bd327a9dff47d66914231c"),
    "original_owid_line_chart_gbr.png": (
        _GRAPHER + ".png?time=1750..latest&country=~GBR&imWidth=1700",
        "93025cfef550713a2b836512f03ee34801e9714d1122d709f7aa4c8a456c418f"),
    "original_owid_line_chart_gbr_chn.png": (
        _GRAPHER + ".png?time=1750..latest&country=GBR~CHN&imWidth=1700",
        "a1b4e1de50f46cbf8fb4427c784e07067215eed2403fad0cf1777011febf18b1"),
    "original_owid_line_chart_gbr.csv": (
        _GRAPHER + ".csv?v=1&csvType=filtered&useColumnShortNames=true&country=~GBR",
        "030693a6844f1bb69a9f8712b30794813ebec9c8c0810f5cfa797a7e8b6f8932"),
    "original_owid_arrow_grid.png": (
        "https://ourworldindata.org/cdn-cgi/imagedelivery/qLq-8BTgXU8yG0N6HnOy8g/"
        "f5db1a91-6bde-4430-3c09-e61fd8df9a00/w=2614",
        "361a92ace846b7e41c7351bc399eb0d9b636b4f2e5da985a71eedf9a9a04d6dc"),
}
# OWID's CDN turns away requests that do not look like a browser.
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(name, url):
    import requests
    print(f"   downloading {url}")
    reply = requests.get(url, timeout=180, headers=HEADERS)
    reply.raise_for_status()
    with open(os.path.join(INPUTS, name), "wb") as fh:
        fh.write(reply.content)


def main(argv):
    refetch = "--fetch" in argv
    print("RAW INPUTS")
    print("=" * 78)
    bad = changed = 0
    for name, (url, recorded) in SOURCES.items():
        path = os.path.join(INPUTS, name)
        if refetch:
            fetch(name, url)
        if not os.path.isfile(path):
            print(f"   check: {name} is present ... FAIL (run with --fetch)")
            bad += 1
            continue
        digest = sha256(path)
        size = os.path.getsize(path)
        same = digest == recorded
        if same:
            verdict = "PASS"
        elif refetch:
            verdict = "CHANGED UPSTREAM"
            changed += 1
        else:
            verdict = "FAIL"
            bad += 1
        print(f"   check: {name} ({size:,} bytes) matches its recorded SHA-256 ... {verdict}")
        if not same:
            print(f"          recorded {recorded}")
            print(f"          on disk  {digest}")
    print("-" * 78)
    if bad:
        print(f"inputs: {bad} problem(s)")
    elif changed:
        print(f"inputs: {changed} of {len(SOURCES)} files changed upstream since 4 October 2026")
    else:
        print(f"inputs: all {len(SOURCES)} files match")
    return bad == 0


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
