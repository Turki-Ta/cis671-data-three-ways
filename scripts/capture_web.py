"""
capture_web.py -- open the web page in a real browser, test Visualization 2 with
real input events, compare what it draws with the data, and take the captures.

Input   web/index.html, web/d3_embed.html and everything they load
        inputs/decoupling_focus.csv                 the numbers the chart must show
        screenshots/03_vis3_seaborn_diverging.png   copied to web/img/ when it exists

Output  screenshots/02_vis2_d3_connected_scatter.png   the chart at 2022 with its controls
        screenshots/02_vis2_scrub_comparison.png       2007, 2022, and 2022 with the overlay
        screenshots/02a_vis2_hover_tooltip.png         the tooltip after a real mouse hover
        screenshots/02b_web_page_full.png              index.html from top to bottom
        web/img/vis3_seaborn_diverging.png             the copy of Visualization 3 the page shows

The browser is the installed Microsoft Edge, driven through Playwright. web/ is
served from a local http.server on a free port, and index.html is opened once
more straight from disk, because the page promises to work that way too.

Nothing here trusts the chart's report of itself where the page can be read
instead. Positions are read back from the SVG and turned into dollars and tonnes
with a scale fitted to the gridlines as drawn; the point a tooltip should pick is
found by brute force over every plotted vertex; the numbers on the page are
compared with the CSV through pandas. The checks print as 'check: ... PASS' and
the values the chart shows for 2022 as 'result: name = value', under the names
prepare_data.py uses, so run_all.py recomputes them from the raw file as well.

The Altair export and the Seaborn figure are written by other scripts. Until
they exist the page shows a note in their place, and this script checks that
note instead of failing; once they exist it checks the real thing.

Run:  python scripts/capture_web.py
"""
import asyncio
import functools
import html
import http.server
import math
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont

from common import (FOCUS, INK, INK_2, MUTED, PAGE, PIVOT_YEAR, ROOT, SHOTS, SURFACE, WEB,
                    YEAR_MAX, YEAR_MIN, Log, load_focus)

EMBED = "d3_embed.html"
INDEX = "index.html"
ALTAIR = os.path.join(WEB, "altair_export.html")
VIS3_SOURCE = os.path.join(SHOTS, "03_vis3_seaborn_diverging.png")
VIS3_COPY = os.path.join(WEB, "img", "vis3_seaborn_diverging.png")
PNG_MAIN = os.path.join(SHOTS, "02_vis2_d3_connected_scatter.png")
PNG_PLATE = os.path.join(SHOTS, "02_vis2_scrub_comparison.png")
PNG_HOVER = os.path.join(SHOTS, "02a_vis2_hover_tooltip.png")
PNG_PAGE = os.path.join(SHOTS, "02b_web_page_full.png")
PNG_OVERVIEW = os.path.join(SHOTS, "02c_web_page_overview.png")

VIEW = (1300, 1500)                 # CSS px; at twice the density a capture is 2600 px wide
DENSITY = 2
PLATE_WIDTH = 2600
WIDTHS = (360, 390, 768, 1024, 1400)    # the layout has to hold at each of these
NOTEBOOK_FRAME = (1000, 860)        # the iframe the notebook puts d3_embed.html in
N_YEARS = YEAR_MAX - YEAR_MIN + 1
OWNED = ("index.html", "d3_embed.html", "styles.css", "d3_vis.js", "d3_story.js", "README.md")
D3_COPY = os.path.join(WEB, "vendor", "d3.v7.min.js")
ARTICLE = ("https://ourworldindata.org/co2-gdp-decoupling",
           "Hannah Ritchie (2021), Many countries have decoupled economic growth from CO2 "
           "emissions, even if we take offshored production into account, Our World in Data")
# Carbon intensities of the three grey guides, kg CO2 per international-$ (d3_vis.js).
GUIDES = (0.15, 0.3, 0.6)
BYLINE = "Module Two - Data Three Ways | Taher Turki | October 2026"
COPY_IDS = ("copy-intro", "copy-vis1", "copy-vis2", "copy-vis3", "copy-synthesis")
BANNED = ("delve", "tapestry", "testament", "crucial", "moreover", "furthermore",
          "in conclusion", "it is important to note", "serves as a bridge",
          "rich visual representation", "multifaceted", "leverage", "robust", "seamless",
          "comprehensive", "underscores", "pivotal", "nuanced", "holistic", "realm",
          "landscape", "navigate", "foster", "as we can see", "this demonstrates that",
          "in summary", "overall")
CONS, PROD, GDP, NET = ("consumption_co2_per_capita", "co2_per_capita", "gdp_per_capita",
                        "net_co2_per_capita")
# A printed value is the CSV value rounded once more after the data file rounded
# it, so it may sit a hair beyond half a unit of its last digit.
TOL_GDP = 0.6
TOL_CO2 = 0.006

# Functions the checks call inside the page. They only read the DOM.
HELPERS = r"""
() => {
  const app = window.DecouplingStory.apps[0];
  const all = (selector, root) => Array.from((root || document).querySelectorAll(selector));
  const one = (selector, root) => (root || document).querySelector(selector);
  const attr = (el, name) => el.getAttribute(name);
  const text = (selector) => one(selector).textContent;
  const shown = (el) => {
    for (let n = el; n && n.nodeType === 1; n = n.parentNode) {
      if (n.hidden || attr(n, "display") === "none") { return false; }
    }
    return true;
  };
  const points = (el) => (attr(el, "d") || "").split(/[ML]/).filter(Boolean)
    .map((pair) => pair.split(",").map(Number));
  const group = (kind, name) => one(".dc-" + kind + '[data-name="' + name + '"]');
  const box = (el) => {
    const b = el.getBoundingClientRect();
    return [b.left, b.top, b.right, b.bottom];
  };
  const screen = (x, y) => {
    const m = one(".dc-plot").getScreenCTM();
    return [m.a * x + m.e, m.d * y + m.f];
  };
  const tick = (selector, position) => all(selector).map((el) => (
    { value: +attr(el, "data-value"), px: +attr(el, position), text: el.textContent }));
  const chevron = /translate\(([-\d.]+),([-\d.]+)\) rotate\(([-\d.]+)\)/;
  window.T = {
    state: () => app.chart.getState(),
    screen: screen,
    path: (name, cls) => {
      const el = one("." + cls, group("country", name));
      return el && shown(el) ? points(el) : null;
    },
    marker: (name, cls) => {
      const el = one("." + (cls || "dc-now"), group("marker", name));
      return shown(el) ? [+attr(el, "cx"), +attr(el, "cy")] : null;
    },
    gap: (name) => {
      const line = one(".dc-gap", group("marker", name));
      const label = one(".dc-gap-label", group("label", name));
      return { line: shown(line) ? [+attr(line, "y1"), +attr(line, "y2")] : null,
               label: shown(label) ? label.textContent : null };
    },
    groups: () => all(".dc-country").map((g) => (
      { name: attr(g, "data-name"), shown: shown(g), cls: attr(g, "class"),
        stroke: attr(one(".dc-done", g), "stroke"), opacity: +getComputedStyle(g).opacity })),
    ticks: () => (
      { x: tick("line.dc-grid-x", "x1"), y: tick("line.dc-grid-y", "y1"),
        labels: tick("text.dc-tick-x", "x").concat(tick("text.dc-tick-y", "y")) }),
    chevrons: (name) => all(".dc-chevron", group("country", name)).map((el) => {
      const m = chevron.exec(attr(el, "transform"));
      return [+m[1], +m[2], +m[3]];
    }),
    grey: () => all(".dc-context-path").map((p) => (
      { name: attr(p, "data-name"), points: points(p).map((xy) => screen(xy[0], xy[1])) })),
    tooltip: () => {
      const tip = one(".dc-tooltip");
      return { hidden: tip.hidden, context: tip.classList.contains("is-context"),
               country: text(".dc-tt-country"), year: text(".dc-tt-year"),
               gdp: text(".dc-tt-gdp .dc-tt-value"), cons: text(".dc-tt-cons .dc-tt-value"),
               prod: text(".dc-tt-prod .dc-tt-value"), net: text(".dc-tt-net .dc-tt-value"),
               netLabel: text(".dc-tt-net .dc-tt-label"),
               rows: getComputedStyle(one(".dc-tt-rows")).display,
               valueFirst: all(".dc-tt-row").every((row) =>
                 row.firstElementChild.classList.contains("dc-tt-value")) };
    },
    labels: () => all(".dc-label").filter(shown).map((g) => {
      const name = one(".dc-name", g);
      return { name: attr(g, "data-name"), text: shown(name) ? name.textContent : null,
               box: shown(name) ? box(name) : null, fill: getComputedStyle(name).fill };
    }),
    yearLabels: () => all(".dc-year-label").filter(shown).map((t) => (
      { text: t.textContent + " " + attr(t, "data-name"), box: box(t) })),
    table: () => {
      const rows = {};
      all(".tv tbody tr").forEach((tr) => {
        rows[attr(tr, "data-name")] = all("td", tr).map((td) => td.textContent);
      });
      return { year: text(".tv-year"), rows: rows, open: one(".tv").open };
    },
    controls: () => (
      { slider: one(".vc-year input").value, readout: text(".vc-year-value"),
        play: text(".vc-play span"), scale: one(".vc-scale input:checked").value,
        overlay: one(".vc-overlay input").checked, context: one(".vc-context input").checked,
        steps: all(".story-step").map((b) => attr(b, "aria-pressed") === "true"),
        caption: text(".story-caption"), range: text(".dc-range"),
        xTitle: text(".dc-axis-title-x"), yTitle: text(".dc-axis-title-y"),
        note: text(".dc-note-line"), live: all(".dc-hidden").pop().textContent,
        overlayKeys: all(".dc-key-overlay").filter((el) => !el.hidden).length,
        focusOnPlot: document.activeElement === one(".dc-svg"),
        outline: getComputedStyle(one(".dc-svg")).outlineStyle }),
    legend: () => all(".dc-legend-item").map((b) => (
      { name: attr(b, "data-name"), pressed: attr(b, "aria-pressed"),
        key: attr(one("line", b), "stroke") })),
    counts: () => (
      { context: all(".dc-context-path").length,
        hovered: all(".dc-context-path.is-hover").map((p) => attr(p, "data-name")),
        underneath:
          (one(".dc-context").compareDocumentPosition(one(".dc-countries")) & 4) === 4 }),
    layout: () => {
      const svg = one(".dc-svg");
      const frame = svg.getBoundingClientRect();
      const outside = all(".dc-svg text").filter(shown).filter((t) => {
        const b = t.getBoundingClientRect();
        return t.textContent && b.width > 0 && (
          b.left < frame.left - 1 || b.right > frame.right + 1 ||
          b.top < frame.top - 1 || b.bottom > frame.bottom + 1);
      }).map((t) => t.textContent);
      const row = one(".vc").getBoundingClientRect();
      return { scrollWidth: document.documentElement.scrollWidth, innerWidth: window.innerWidth,
               viewBox: attr(svg, "viewBox"), svgWidth: frame.width, svgHeight: frame.height,
               outside: outside, controlsHeight: row.height, controlsBottom: row.bottom,
               chartTop: one(".dc").getBoundingClientRect().top,
               content: Math.ceil(document.body.getBoundingClientRect().height) };
    },
    // Every string a reader can meet: text nodes, and the attributes that are read out.
    words: () => {
      const out = [document.title];
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      for (let n = walker.nextNode(); n; n = walker.nextNode()) {
        if (!n.parentNode.closest("script, style, template")) { out.push(n.nodeValue); }
      }
      all("[aria-label], [alt], [title], [placeholder]").forEach((el) => {
        ["aria-label", "alt", "title", "placeholder"].forEach((name) => {
          if (el.hasAttribute(name)) { out.push(attr(el, name)); }
        });
      });
      return out.join("\n");
    },
    facts: () => all("[data-fact]").map((el) => [attr(el, "data-fact"), el.textContent]),
    unnamed: () => all("button, input, select, textarea, iframe, img, svg[tabindex]")
      .filter((el) => !el.closest("[hidden]"))
      .filter((el) => !(attr(el, "aria-label") || attr(el, "aria-labelledby") ||
                        attr(el, "alt") || attr(el, "title") || el.textContent.trim() ||
                        (el.labels && el.labels.length) || el.closest("label")))
      .map((el) => el.outerHTML.slice(0, 80)),
    clip: () => {
      const top = one(".vc").getBoundingClientRect().top + window.scrollY;
      const bottom = one(".dc").getBoundingClientRect().bottom + window.scrollY;
      return { x: 0, y: Math.max(0, top - 12), width: document.documentElement.clientWidth,
               height: bottom - top + 20 };
    }
  };
  return true;
}
"""

PAGE_FACTS = """([ids, href]) => {
  const id = (name) => document.getElementById(name);
  return {
    title: document.querySelector("h1").textContent,
    byline: document.querySelector(".byline").textContent,
    missing: ids.filter((name) => !id(name)),
    link: Array.from(document.querySelectorAll("a")).filter((a) => a.href === href)
      .map((a) => a.textContent),
    landmarks: ["header", "nav", "main", "footer"].filter((t) => !document.querySelector(t)),
    unnamed: T.unnamed(), lang: document.documentElement.lang,
    scheme: getComputedStyle(document.documentElement).colorScheme };
}"""

OPTIONAL_PARTS = """() => {
  const id = (name) => document.getElementById(name);
  return { frame: !id("vis1-frame").hidden, frameNote: !id("vis1-pending").hidden,
           frameTitle: id("vis1-frame").title.length,
           image: !id("vis3-img").hidden && id("vis3-img").naturalWidth > 0,
           imageNote: !id("vis3-pending").hidden, alt: id("vis3-img").alt.length };
}"""


# ---------------------------------------------------------------- formatting, as the page does it
def js_round(x):
    """Math.round for a magnitude: halves go up, unlike Python's round()."""
    return int(math.floor(abs(x) + 0.5))


def percent(v):
    r = js_round(v)
    return ("" if r == 0 else "+" if v > 0 else "-") + f"{r}%"


def percent_abs(v):
    return f"{js_round(v)}%"


def signed_tonnes(v):
    r = 0.0 if abs(v) < 0.005 else v
    return ("+" if r > 0 else "-" if r < 0 else "") + f"{abs(r):.2f} t"


def number(text):
    """'$36,851' -> 36851.0, '12.43 t' -> 12.43, '+3.34 t' -> 3.34, '$10k' -> 10000.0."""
    t = text.replace("$", "").replace(",", "").replace(" t", "").strip()
    return float(t[:-1]) * 1000 if t.endswith("k") else float(t)


def change(focus, country, column, first, last):
    return 100.0 * (focus.loc[(country, last), column] / focus.loc[(country, first), column] - 1)


# ---------------------------------------------------------------- browser plumbing
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):       # the request log would drown the checks
        pass


class QuietServer(http.server.ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # A page that is closed while a large file is still on its way resets the
        # connection. That is the browser leaving, not a fault to print a traceback for.
        if not isinstance(sys.exc_info()[1], ConnectionError):
            super().handle_error(request, client_address)


def serve(directory):
    """web/ on a free local port, in a daemon thread. Returns (server, base URL)."""
    handler = functools.partial(QuietHandler, directory=directory)
    server = QuietServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/"


class Watch:
    """What a page logs and requests, kept so that a check can assert on it.

    `pending` names the files other scripts write; while one is missing, the
    browser's complaint about that one address is expected and left out.
    """

    def __init__(self, page, home, pending):
        self.errors, self.failed, self.outside = [], [], []
        self.home = (home, "data:", "about:", "blob:")
        self.pending = tuple(pending)
        page.on("console", self._console)
        page.on("pageerror", lambda error: self.errors.append(f"uncaught: {error}"))
        page.on("requestfailed", self._failed)
        page.on("response", self._response)
        page.on("request", self._request)

    def _expected(self, url):
        return url.split("?")[0].endswith(self.pending)

    def _console(self, message):
        where = (message.location or {}).get("url", "")
        if message.type == "error" and not self._expected(where):
            self.errors.append(f"console: {message.text} [{where}]")

    def _failed(self, request):
        if not self._expected(request.url):
            self.failed.append(f"{request.url} ({request.failure})")

    def _response(self, response):
        if response.status >= 400 and not self._expected(response.url):
            self.failed.append(f"{response.url} (HTTP {response.status})")

    def _request(self, request):
        if not request.url.startswith(self.home):
            self.outside.append(request.url)

    def report(self):
        """True when nothing went wrong; otherwise prints what did."""
        for line in self.errors + self.failed + self.outside:
            print(f"          {line[:160]}")
        return not (self.errors or self.failed or self.outside)


class Session:
    """One browser, one local server, and the table the page is checked against."""

    def __init__(self, playwright, log):
        self.log = log
        self.browser = playwright.chromium.launch(channel="msedge", headless=True)
        self.server, self.base = serve(WEB)
        self.focus = load_focus().astype({"country": str}).set_index(["country", "year"])
        self.tags = {c: self.focus.loc[(c, YEAR_MIN), "iso_code"].lower() for c in FOCUS}
        self.high = [c for c in FOCUS
                     if self.focus.loc[(c, YEAR_MIN), "income_group"] == "High income"]
        optional = (("altair_export.html", ALTAIR), ("img/vis3_seaborn_diverging.png", VIS3_COPY))
        self.pending = tuple(name for name, path in optional if not os.path.isfile(path))

    def context(self, width=VIEW[0], height=VIEW[1], density=1, motion="reduce"):
        return self.browser.new_context(viewport={"width": width, "height": height},
                                        device_scale_factor=density, reduced_motion=motion)

    def open(self, target, from_disk=False, **view):
        """A fresh page on `target`, waited on until the chart has drawn."""
        page = self.context(**view).new_page()
        page.set_default_timeout(15000)
        if from_disk:
            name, _, query = target.partition("?")
            url = pathlib.Path(WEB, name).as_uri() + ("?" + query if query else "")
            home = pathlib.Path(WEB).as_uri()
        else:
            url, home = self.base + target, self.base
        page.watch = Watch(page, home, self.pending)
        page.goto(url)
        chart_ready(page)
        return page

    def close(self):
        self.browser.close()
        self.server.shutdown()


def chart_ready(frame):
    """Wait until the chart in a page (or in a frame) has drawn, then install the helpers."""
    frame.wait_for_function("window.DecouplingStory && DecouplingStory.apps.length > 0 "
                            "&& document.querySelector('.dc-done')")
    frame.evaluate("document.fonts.ready.then(() => true)")
    frame.evaluate(HELPERS)
    settle(frame)


def settle(page, frames=2):
    """Wait for the next animation frames, so a redraw has reached the DOM."""
    page.evaluate("(n) => new Promise((done) => { const step = () => "
                  "(n-- > 0 ? requestAnimationFrame(step) : done(true)); step(); })", frames)


def idle(page):
    """Wait until no play animation and no change of scale is running."""
    page.wait_for_function("!T.state().playing && !T.state().transitioning")
    settle(page)


def vertex(page, name, year, cls="dc-ghost"):
    """Screen position of one plotted point, read from the path it belongs to."""
    x, y = page.evaluate("([name, cls]) => T.path(name, cls)", [name, cls])[year - YEAR_MIN]
    return page.evaluate("([x, y]) => T.screen(x, y)", [x, y])


def every_vertex(page, state):
    """(country, year, screen x, screen y) for each plotted point of each visible country."""
    out = []
    on_screen = "([name, cls]) => T.path(name, cls).map((p) => T.screen(p[0], p[1]))"
    for name in state["visible"]:
        for cls in ("dc-ghost", "dc-prod-ghost") if state["overlay"] else ("dc-ghost",):
            pts = page.evaluate(on_screen, [name, cls])
            out += [(name, YEAR_MIN + i, x, y) for i, (x, y) in enumerate(pts)]
    return out


def tooltip_agrees(tip, focus, country, year):
    """The four numbers in the tooltip against the CSV row for that country and year."""
    row = focus.loc[(country, year)]
    return (not tip["hidden"] and tip["country"] == country and tip["year"] == str(year)
            and abs(number(tip["gdp"]) - row[GDP]) <= TOL_GDP
            and abs(number(tip["cons"]) - row[CONS]) <= TOL_CO2
            and abs(number(tip["prod"]) - row[PROD]) <= TOL_CO2
            and abs(number(tip["net"]) - row[NET]) <= TOL_CO2
            and ("importer" if row[NET] > 0 else "exporter") in tip["netLabel"])


# ---------------------------------------------------------------- 1. files
def check_files(log):
    log.section("1. Files")
    missing = [name for name in OWNED + ("data/decoupling_data.js",)
               if not os.path.isfile(os.path.join(WEB, name))]
    log.check("the page, the embed, the stylesheet, both scripts and the data file are in web/"
              + (f" (missing: {', '.join(missing)})" if missing else ""), not missing)

    with open(D3_COPY, encoding="utf-8") as fh:
        head = fh.readline().strip()
    version = re.search(r"v(\d+)\.(\d+)\.(\d+)", head)
    log.check(f"vendor/d3.v7.min.js is a local copy of D3 7 with its licence line "
              f"({head[3:60]})", bool(version) and version.group(1) == "7" and "Copyright" in head)
    if version:
        log.result("d3_version_major", int(version.group(1)), 0)
        log.result("d3_version_minor", int(version.group(2)), 0)

    remote, not_ascii, markup = [], [], []
    loads = re.compile(r"""(?:src|href)\s*=\s*["'](?:https?:)?//|url\(\s*["']?(?:https?:)?//"""
                       r"""|@import""")
    writes = re.compile(r"innerHTML|outerHTML|insertAdjacentHTML|\.html\(|document\.write")
    for name in OWNED:
        with open(os.path.join(WEB, name), "rb") as fh:
            raw = fh.read()
        if any(byte > 127 for byte in raw):
            not_ascii.append(name)
        # A link the reader may follow is not a request; anything the page loads is.
        text = re.sub(r"<a\b[^>]*>", "", raw.decode("utf-8", "replace"))
        if name != "README.md" and loads.search(text):
            remote.append(name)
        if name.endswith(".js") and writes.search(text):
            markup.append(name)
    log.check("no page, stylesheet or script loads anything from another site "
              "(no CDN, no web font, no remote image)", not remote)
    log.check("every source file in web/ is plain ASCII", not not_ascii)
    log.check("d3_vis.js and d3_story.js put text into the page as text (textContent, never "
              "innerHTML or .html())", not markup)
    for name in remote + not_ascii + markup:
        print(f"          {name}")

    if os.path.isfile(VIS3_SOURCE):
        os.makedirs(os.path.dirname(VIS3_COPY), exist_ok=True)
        shutil.copyfile(VIS3_SOURCE, VIS3_COPY)
        with Image.open(VIS3_COPY) as im:
            print(f"   copied screenshots/03_vis3_seaborn_diverging.png to web/img/ "
                  f"({im.width} x {im.height} px)")
    else:
        print("   pending: screenshots/03_vis3_seaborn_diverging.png does not exist yet, so the "
              "page shows its note for Visualization 3")
    if not os.path.isfile(ALTAIR):
        print("   pending: web/altair_export.html does not exist yet, so the page shows its "
              "note for Visualization 1")


# ---------------------------------------------------------------- 2. the pages load
def show_optional_parts(page):
    """Scroll through index.html so its lazy frame and image are asked for, and wait for them."""
    page.wait_for_function("!document.getElementById('vis1-pending').hidden "
                           "|| !document.getElementById('vis1-frame').hidden")
    for selector in ("#vis1", "#vis3", "#made"):
        page.locator(selector).scroll_into_view_if_needed()
        page.wait_for_timeout(250)
    page.wait_for_function("(() => { const im = document.getElementById('vis3-img'); "
                           "return im.hidden || (im.complete && im.naturalWidth > 0); })()")
    if not page.evaluate("document.getElementById('vis1-frame').hidden"):
        page.frame_locator("#vis1-frame").locator("canvas, svg").first.wait_for(state="attached")
        page.wait_for_timeout(600)
    page.evaluate("window.scrollTo(0, 0)")
    settle(page)


def check_optional_parts(page, log, how):
    part = page.evaluate(OPTIONAL_PARTS)
    if os.path.isfile(ALTAIR):
        log.check(f"index.html {how}: Visualization 1 is shown in its frame, which has a title "
                  f"for screen readers",
                  part["frame"] and not part["frameNote"] and part["frameTitle"] > 10)
    else:
        log.check(f"index.html {how}: with altair_export.html absent, the page shows its note "
                  f"and no broken frame", part["frameNote"] and not part["frame"])
    if os.path.isfile(VIS3_COPY):
        log.check(f"index.html {how}: Visualization 3 is shown as an image with alt text",
                  part["image"] and not part["imageNote"] and part["alt"] > 40)
    else:
        log.check(f"index.html {how}: with the Seaborn figure absent, the page shows its note "
                  f"and no broken image", part["imageNote"] and not part["image"])


def inlined_embed():
    """d3_embed.html with its stylesheet and scripts folded in, as the notebook embeds it."""
    def read(name):
        with open(os.path.join(WEB, name), encoding="utf-8") as fh:
            return fh.read()

    def script(match):
        body = read(match.group(1)).replace("</script", "<\\/script")
        return f"<script>\n{body}\n</script>"

    page = re.sub(r'<script src="([^"]+)"></script>', script, read(EMBED))
    return re.sub(r'<link rel="stylesheet" href="([^"]+)">',
                  lambda match: f"<style>\n{read(match.group(1))}\n</style>", page)


def check_notebook_frame(s):
    """The notebook shows the embed as one srcdoc iframe with everything inlined. The page
    is tried in a frame of the notebook's size, then in one tall enough to show it whole."""
    width, height = NOTEBOOK_FRAME
    markup = html.escape(inlined_embed(), quote=True)
    ok, needs = True, None
    for tall in (height, 1200):
        page = s.context(width=width + 40, height=tall + 40).new_page()
        watch = Watch(page, "about:", ())
        page.set_content(f'<iframe srcdoc="{markup}" width="{width}" height="{tall}" '
                         f'style="border:0"></iframe>')
        frame = page.frames[1]
        chart_ready(frame)
        ok &= watch.report() and len(frame.evaluate("T.groups()")) == len(FOCUS)
        if tall == height:
            needs = frame.evaluate("document.documentElement.scrollHeight")
        else:
            content = frame.evaluate("T.layout().content")
            ok &= frame.evaluate("document.documentElement.scrollHeight") <= tall
        page.context.close()
    s.log.check(f"inlined into a srcdoc iframe {width} px wide, as the notebook embeds it, the "
                f"chart draws with no error and no request of any kind", ok)
    print(f"   in a frame {width} x {height} px the page is {needs} px tall, so that frame "
          f"scrolls by {max(0, needs - height)} px; {content} px shows it whole")
    s.log.result("vis2_embed_height_px_at_1000_wide", content, 0)


def check_loads(s):
    log = s.log
    log.section("2. The pages load")
    waiting = f" apart from the {len(s.pending)} file(s) still pending" if s.pending else ""

    page = s.open(EMBED)
    log.check("d3_embed.html over http: no console error, no failed request, no request "
              "outside the local server", page.watch.report())
    log.check("the browser runs D3 7 from the local copy",
              page.evaluate("d3.version").startswith("7."))
    drawn = page.evaluate("T.groups()")
    log.check("the chart draws one path per focus country, in the order and colours of "
              "DECOUPLING_DATA", [g["name"] for g in drawn] == FOCUS
              and all(g["shown"] for g in drawn) and [g["stroke"] for g in drawn]
              == page.evaluate("DECOUPLING_DATA.countries.map((c) => c.color)"))
    page.context.close()
    check_notebook_frame(s)

    for from_disk, how in ((False, "over http"), (True, "opened from disk (file://)")):
        page = s.open(INDEX, from_disk=from_disk, height=900)
        show_optional_parts(page)
        log.check(f"index.html {how}: no console error, no failed request, no request outside "
                  f"its own folder{waiting}", page.watch.report())
        log.check(f"index.html {how}: the D3 chart is drawn",
                  len(page.evaluate("T.groups()")) == len(FOCUS))
        check_optional_parts(page, log, how)
        page.context.close()


# ---------------------------------------------------------------- 3. real input events
def check_slider(page, log):
    before = page.evaluate("T.marker('United Kingdom')")
    box = page.locator(".vc-year input").bounding_box()
    page.mouse.click(box["x"] + box["width"] * 0.5, box["y"] + box["height"] / 2)
    settle(page)
    c = page.evaluate("T.controls()")
    moved = page.evaluate("T.marker('United Kingdom')")
    log.check(f"a mouse click on the slider track moves the year (2022 -> {c['readout']}), the "
              f"readout and the marker", c["readout"] != "2022" and c["readout"] == c["slider"]
              and math.dist(before, moved) > 5)
    # Arrow keys on the focused slider, one year a press, until it reads the pivot year.
    for _ in range(40):
        year = int(page.evaluate("T.controls().slider"))
        if year == PIVOT_YEAR:
            break
        page.keyboard.press("ArrowLeft" if year > PIVOT_YEAR else "ArrowRight")
    settle(page)
    c = page.evaluate("T.controls()")
    at = page.evaluate("T.marker('United Kingdom')")
    want = page.evaluate("T.path('United Kingdom', 'dc-ghost')")[PIVOT_YEAR - YEAR_MIN]
    done = page.evaluate("T.path('United Kingdom', 'dc-done')")
    log.check(f"arrow keys step the slider to {PIVOT_YEAR}: readout, year range and table "
              f"heading all say so", c["readout"] == str(PIVOT_YEAR)
              and c["range"] == f"{YEAR_MIN}-{PIVOT_YEAR}"
              and page.evaluate("T.table().year") == str(PIVOT_YEAR))
    log.check(f"the marker sits on the {PIVOT_YEAR} vertex and the full-strength path stops "
              f"there ({len(done)} of {N_YEARS} points)",
              math.dist(at, want) < 0.02 and len(done) == PIVOT_YEAR - YEAR_MIN + 1)


def check_play(page, log):
    start = int(page.evaluate("T.controls().slider"))
    page.locator(".vc-play").click()
    page.wait_for_function(f"T.state().year >= {start + 2}")
    mid = page.evaluate("T.controls()")
    log.check(f"Play advances the year by itself ({start} -> {mid['readout']} and counting) and "
              f"the button turns to Pause",
              int(mid["readout"]) >= start + 2 and mid["play"] == "Pause")
    page.locator(".vc-play").click()
    settle(page)
    stopped = page.evaluate("T.controls()")
    page.wait_for_timeout(700)
    later = page.evaluate("T.controls()")
    log.check(f"Pause holds it at a whole year ({stopped['readout']})",
              stopped["play"] == "Play" and later["readout"] == stopped["readout"]
              and not page.evaluate("T.state().playing"))


def check_nearest(page, log, focus):
    """Nearest-point lookup against a brute-force search over every plotted vertex."""
    state = page.evaluate("T.state()")
    pts = every_vertex(page, state)
    frame = page.locator(".dc-svg").bounding_box()
    reach = state["hoverRadius"]
    rng = random.Random(2022)
    hits = misses = wrong = 0
    for _ in range(120):
        # A pointer position up to 75 px from a plotted point, in a random direction. On
        # the linear axis the points lie close together, so it takes this many tries and
        # this much reach to land often enough where no point is within range.
        _, _, vx, vy = rng.choice(pts)
        r, angle = rng.uniform(0, 75), rng.uniform(0, 2 * math.pi)
        x, y = vx + r * math.cos(angle), vy + r * math.sin(angle)
        if not (frame["x"] + 2 < x < frame["x"] + frame["width"] - 2
                and frame["y"] + 2 < y < frame["y"] + frame["height"] - 2):
            continue
        ranked = sorted((math.hypot(px - x, py - y), name, year) for name, year, px, py in pts)
        (d1, name, year), d2 = ranked[0], ranked[1][0]
        # Positions where two points tie, or the limit is a pixel away, prove nothing.
        if d2 - d1 < 1.5 or abs(d1 - reach) < 1.5:
            continue
        page.mouse.move(x, y)
        settle(page, 1)
        tip = page.evaluate("T.tooltip()")
        if d1 <= reach:
            hits += 1
            wrong += not tooltip_agrees(tip, focus, name, year)
        else:
            misses += 1
            wrong += not tip["hidden"]
    log.check(f"at {hits + misses} pointer positions the tooltip is for the nearest plotted "
              f"point when one is within {reach} px ({hits} cases) and hidden when none is "
              f"({misses} cases)", wrong == 0 and hits >= 10 and misses >= 5)


def check_hover(page, log, focus):
    x, y = vertex(page, "United Kingdom", PIVOT_YEAR)
    page.mouse.move(x - 60, y - 90)
    page.mouse.move(x + 3, y + 2, steps=6)
    page.wait_for_timeout(300)          # the dimming is a short CSS transition
    tip = page.evaluate("T.tooltip()")
    row = focus.loc[("United Kingdom", PIVOT_YEAR)]
    log.check(f"hovering the United Kingdom's {PIVOT_YEAR} point shows {tip['gdp']}, "
              f"{tip['cons']}, {tip['prod']} and {tip['net']}, which is the CSV row "
              f"({row[GDP]:,.1f}, {row[CONS]:.4f}, {row[PROD]:.4f}, {row[NET]:+.4f})",
              tooltip_agrees(tip, focus, "United Kingdom", PIVOT_YEAR))
    log.check("in the tooltip each value comes before its label, and the net balance carries "
              "its sign and says importer or exporter",
              tip["valueFirst"] and tip["net"][0] in "+-" and "net importer" in tip["netLabel"])
    groups = {g["name"]: g for g in page.evaluate("T.groups()")}
    log.check("the hovered path is emphasised and the other five are dimmed",
              "is-emph" in groups["United Kingdom"]["cls"]
              and groups["United Kingdom"]["opacity"] == 1
              and all(g["opacity"] < 0.5 for n, g in groups.items() if n != "United Kingdom"))
    frame = page.locator(".dc-svg").bounding_box()
    page.mouse.move(frame["x"] + 90, frame["y"] + frame["height"] * 0.45)
    page.wait_for_timeout(300)
    log.check("moving the pointer away from every point hides the tooltip and restores the "
              "other paths", page.evaluate("T.tooltip().hidden")
              and all(g["opacity"] == 1 for g in page.evaluate("T.groups()")))
    return number(tip["net"])


def check_legend(page, log):
    before = {g["name"]: g["stroke"] for g in page.evaluate("T.groups()")}
    page.locator(".dc-legend-item", has_text="Germany").click()
    settle(page)
    groups = page.evaluate("T.groups()")
    legend = {e["name"]: e for e in page.evaluate("T.legend()")}
    log.check("a click on Germany in the legend removes its path, marker and label, and "
              "nothing else",
              [g["name"] for g in groups if g["shown"]] == [c for c in FOCUS if c != "Germany"]
              and page.evaluate("T.marker('Germany')") is None
              and "Germany" not in [e["name"] for e in page.evaluate("T.labels()")]
              and legend["Germany"]["pressed"] == "false")
    log.check("the five countries left keep their own colours, on the paths and in the legend",
              all(g["stroke"] == before[g["name"]] for g in groups)
              and all(e["key"] == before[n] for n, e in legend.items()))
    page.locator(".dc-legend-item", has_text="Germany").click()
    page.mouse.move(5, 5)               # off the legend, which emphasises what it points at
    settle(page)
    log.check("a second click brings Germany back",
              all(g["shown"] for g in page.evaluate("T.groups()")))


def check_scale(page, log):
    start = page.evaluate("T.controls()")
    lowest = min(t["value"] for t in page.evaluate("T.ticks()")["x"])
    log.check("the page opens on the linear GDP axis, which starts at $0",
              start["scale"] == "linear" and "linear scale" in start["xTitle"] and lowest == 0)
    before = page.evaluate("T.marker('China')")
    page.locator("label.seg", has_text="Log").click()
    page.wait_for_function("T.state().scale === 'log'")
    idle(page)
    after = page.evaluate("T.marker('China')")
    c = page.evaluate("T.controls()")
    lowest = min(t["value"] for t in page.evaluate("T.ticks()")["x"])
    log.check(f"the Log button moves the points (China's marker travels "
              f"{math.dist(before, after):.0f} px) and relabels the axis, which no longer "
              f"starts at $0",
              math.dist(before, after) > 50 and c["scale"] == "log"
              and "log scale" in c["xTitle"] and lowest > 0)
    page.locator("label.seg", has_text="Linear").click()
    page.wait_for_function("T.state().scale === 'linear'")
    idle(page)
    log.check("the Linear button puts them back where they were",
              math.dist(before, page.evaluate("T.marker('China')")) < 0.02
              and "linear scale" in page.evaluate("T.controls().xTitle"))


def check_overlay(page, log, focus):
    page.locator(".vc-overlay").click()
    settle(page)
    year = page.evaluate("T.state().year")
    paths = [page.evaluate("(name) => T.path(name, 'dc-prod-ghost')", c) for c in FOCUS]
    log.check(f"the overlay checkbox adds a production-based path of {N_YEARS} points for each "
              f"country", all(p and len(p) == N_YEARS for p in paths))
    ok, labels = True, 0
    for country in FOCUS:
        gap = page.evaluate("(name) => T.gap(name)", country)
        cons = page.evaluate("(name) => T.marker(name)", country)
        prod = page.evaluate("(name) => T.marker(name, 'dc-prod-now')", country)
        net = focus.loc[(country, year), NET]
        ok &= abs(cons[0] - prod[0]) < 0.01 and (cons[1] < prod[1]) == (net > 0)
        if gap["line"]:                 # the connector spans the two markers, less their radii
            ok &= min(cons[1], prod[1]) < gap["line"][0] < gap["line"][1] < max(cons[1], prod[1])
        if gap["label"]:
            labels += 1
            ok &= abs(number(gap["label"]) - net) <= TOL_CO2 and gap["label"][0] in "+-"
    log.check(f"at {year} each country has a consumption and a production marker on one "
              f"vertical, consumption on top where the balance is positive, and the {labels} "
              f"gap labels shown equal the net balance in the CSV", ok and labels >= 4)
    c = page.evaluate("T.controls()")
    log.check("the y-axis title and the key now name both accounts",
              "production-based" in c["yTitle"] and c["overlayKeys"] == 3)
    x, y = vertex(page, "Sweden", 1995, "dc-prod-ghost")
    page.mouse.move(x + 2, y + 2)
    settle(page)
    log.check("a point on a production-based path can be hovered too (Sweden, 1995)",
              tooltip_agrees(page.evaluate("T.tooltip()"), focus, "Sweden", 1995))
    page.mouse.move(5, 5)


def lone_grey_vertex(page):
    """(name, screen x, screen y) of a context-path vertex inside the plot that is well away
    from the six focus paths and from every other grey path."""
    state = page.evaluate("T.state()")
    frame = page.locator(".dc-svg").bounding_box()
    left, top = frame["x"] + state["plot"]["x"], frame["y"] + state["plot"]["y"]
    right, bottom = left + state["plot"]["width"], top + state["plot"]["height"]
    six = [(x, y) for _, _, x, y in every_vertex(page, state)]
    grey = page.evaluate("T.grey()")
    for path in grey:
        others = [p for other in grey if other is not path for p in other["points"]]
        for x, y in path["points"]:
            if (left + 20 < x < right - 20 and top + 20 < y < bottom - 20
                    and min(math.hypot(x - a, y - b) for a, b in six) > 60
                    and min(math.hypot(x - a, y - b) for a, b in others) > 8):
                return path["name"], x, y
    return None


def check_context(page, log):
    page.locator(".vc-context").click()
    settle(page)
    n = page.evaluate("DECOUPLING_DATA.context.length")
    counts = page.evaluate("T.counts()")
    log.check(f"the context checkbox draws the other {n} countries as paths under the six, and "
              f"the note under the chart says how many leave the frame",
              counts["context"] == n and counts["underneath"]
              and str(n) in page.evaluate("T.controls().note"))
    name, x, y = lone_grey_vertex(page)
    page.mouse.move(x + 1, y + 1)
    settle(page)
    tip = page.evaluate("T.tooltip()")
    log.check(f"hovering a grey path shows its name and nothing else ({name})",
              not tip["hidden"] and tip["context"] and tip["country"] == name
              and tip["rows"] == "none" and page.evaluate("T.counts().hovered") == [name])
    page.mouse.move(5, 5)
    page.locator(".vc-context").click()
    page.locator(".vc-overlay").click()
    settle(page)


def check_keyboard(page, log, focus):
    page.locator(".dc-legend-item").last.focus()
    page.keyboard.press("Tab")
    settle(page)
    year = page.evaluate("T.state().year")
    tip = page.evaluate("T.tooltip()")
    log.check(f"Tab from the legend reaches the plot and opens the readout for the first "
              f"country at the scrubbed year ({tip['country']}, {tip['year']})",
              page.evaluate("T.controls().focusOnPlot")
              and tooltip_agrees(tip, focus, FOCUS[0], year))
    for key in ("ArrowLeft", "ArrowLeft", "ArrowDown"):
        page.keyboard.press(key)
    settle(page)
    tip = page.evaluate("T.tooltip()")
    said = page.evaluate("T.controls().live")
    log.check(f"arrow keys move it along and across the paths (two years back, one country "
              f"down: {tip['country']}, {tip['year']}) and the same values are announced",
              tooltip_agrees(tip, focus, FOCUS[1], year - 2)
              and all(tip[part] in said for part in ("country", "year", "gdp", "net")))
    page.keyboard.press("Home")
    settle(page)
    first = page.evaluate("T.tooltip()")
    page.keyboard.press("End")
    settle(page)
    last = page.evaluate("T.tooltip()")
    page.keyboard.press("Escape")
    settle(page)
    log.check(f"Home and End jump to {YEAR_MIN} and {YEAR_MAX}, and Escape closes the readout",
              first["year"] == str(YEAR_MIN) and last["year"] == str(YEAR_MAX)
              and page.evaluate("T.tooltip().hidden"))
    log.check("keyboard focus on the plot is visible (it draws an outline)",
              page.evaluate("T.controls().outline") == "solid")


def check_interaction(s):
    log = s.log
    log.section("3. Visualization 2 under real mouse and keyboard input")
    page = s.open(EMBED, motion="no-preference")
    layout = page.evaluate("T.layout()")
    log.check(f"at {VIEW[0]} px the controls sit in one row above the chart "
              f"({layout['controlsHeight']:.0f} px high)", layout["controlsHeight"] < 70
              and layout["controlsBottom"] <= layout["chartTop"])
    check_slider(page, log)
    check_play(page, log)
    check_nearest(page, log, s.focus)
    net = check_hover(page, log, s.focus)
    check_legend(page, log)
    check_scale(page, log)
    check_overlay(page, log, s.focus)
    check_context(page, log)
    check_keyboard(page, log, s.focus)
    log.check("none of that raised an error or a failed request", page.watch.report())
    log.result(f"gbr_net_pc_{PIVOT_YEAR}", net)
    page.context.close()


# ---------------------------------------------------------------- 4. story steps and URL state
def step_expectations(s):
    """For each story step: the numbers its caption must quote (from the CSV), then the
    year, the overlay and the highlight it must set."""
    focus = s.focus
    rest = [c for c in FOCUS if c not in s.high]
    one = [percent(change(focus, c, CONS, YEAR_MIN, PIVOT_YEAR)) for c in FOCUS]
    two = ([percent_abs(change(focus, c, CONS, PIVOT_YEAR, YEAR_MAX)) for c in s.high]
           + [percent(change(focus, c, GDP, PIVOT_YEAR, YEAR_MAX)) for c in s.high])
    three = []
    for c in rest:
        three += [percent_abs(change(focus, c, GDP, YEAR_MIN, YEAR_MAX)),
                  percent_abs(change(focus, c, CONS, YEAR_MIN, YEAR_MAX)),
                  f"{focus.loc[(c, YEAR_MIN), CONS]:.1f} t",
                  f"{focus.loc[(c, YEAR_MAX), CONS]:.1f} t"]
    four = [signed_tonnes(focus.loc[(c, YEAR_MAX), NET]) for c in FOCUS]
    return [(one, PIVOT_YEAR, False, None), (two, YEAR_MAX, False, s.high),
            (three, YEAR_MAX, False, rest), (four, YEAR_MAX, True, None)]


def check_story(s):
    log = s.log
    log.section("4. Story steps and state in the URL")
    page = s.open(EMBED)
    log.check(f"the page wiring uses the same pivot year as scripts/common.py ({PIVOT_YEAR})",
              page.evaluate("DecouplingStory.pivotYear") == PIVOT_YEAR)
    for i, (tokens, year, overlay, highlight) in enumerate(step_expectations(s)):
        page.locator(".story-step").nth(i).click()
        idle(page)
        c = page.evaluate("T.controls()")
        state = page.evaluate("T.state()")
        absent = [t for t in tokens if t not in c["caption"]]
        title = page.locator(".story-step").nth(i).inner_text().replace("\n", " ")
        log.check(f"step {title!r} sets year {year}, overlay {'on' if overlay else 'off'}, and "
                  f"its caption quotes {len(tokens)} numbers that match the CSV"
                  + (f" (not found: {', '.join(absent)})" if absent else ""),
                  not absent and state["year"] == year and state["overlay"] == overlay
                  and state["highlight"] == highlight
                  and c["steps"] == [j == i for j in range(4)])
        print(f"      {c['caption']}")
    page.wait_for_timeout(450)
    log.check("the address bar follows the state (overlay=1 after the last step)",
              "overlay=1" in page.url and "year=" not in page.url)
    page.locator(".vc-year input").focus()
    page.keyboard.press("ArrowLeft")
    settle(page)
    c = page.evaluate("T.controls()")
    log.check("changing the year by hand clears the step and its caption",
              not any(c["steps"]) and "Pick a step" in c["caption"]
              and page.evaluate("T.state().highlight") is None)
    page.context.close()

    page = s.open(EMBED, motion="no-preference")
    page.locator(".story-step").first.click()
    page.wait_for_function("T.state().playing")
    page.wait_for_function(f"!T.state().playing && T.state().year === {PIVOT_YEAR}")
    log.check(f"with motion allowed, the first step plays the paths from {YEAR_MIN} and stops "
              f"at {PIVOT_YEAR}", page.evaluate("T.controls().readout") == str(PIVOT_YEAR))
    page.context.close()

    page = s.open(EMBED + f"?year={YEAR_MIN}")
    page.locator(".vc-play").click()
    page.wait_for_timeout(1700)
    year = page.evaluate("T.state().year")
    at = page.evaluate("T.marker('China')")
    want = page.evaluate("T.path('China', 'dc-ghost')")[year - YEAR_MIN]
    log.check(f"with prefers-reduced-motion, Play steps a whole year at a time (at {year} after "
              f"1.7 s, marker exactly on a vertex)",
              YEAR_MIN < year <= YEAR_MIN + 3 and math.dist(at, want) < 0.02)
    page.context.close()

    query = "?year=2007&x=log&overlay=1&context=1&only=United%20Kingdom,China"
    page = s.open(EMBED + query)
    state, c = page.evaluate("T.state()"), page.evaluate("T.controls()")
    two = ["United Kingdom", "China"]
    log.check(f"{query} sets the first state: 2007, log, overlay and context on, two "
              f"countries", state["year"] == 2007 and state["scale"] == "log"
              and state["overlay"] and state["context"] and state["visible"] == two
              and c["readout"] == "2007" and c["scale"] == "log" and c["overlay"]
              and c["context"]
              and [g["name"] for g in page.evaluate("T.groups()") if g["shown"]] == two)
    page.context.close()


# ---------------------------------------------------------------- 5. geometry against the data
def fit_axis(ticks, log_scale):
    """Least-squares line through the gridlines as drawn: pixel = a + b * value (or log10 of
    it). Returns the function from a pixel back to a value, and the worst residual in px."""
    xs = [math.log10(t["value"]) if log_scale else t["value"] for t in ticks]
    ys = [t["px"] for t in ticks]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
    a = my - b * mx
    worst = max(abs(a + b * x - y) for x, y in zip(xs, ys))
    return (lambda px: 10 ** ((px - a) / b)) if log_scale else (lambda px: (px - a) / b), worst


def measure_geometry(page, focus, log_scale):
    """Worst disagreement between the plotted vertices and the CSV, read off the drawn axes."""
    ticks = page.evaluate("T.ticks()")
    to_gdp, rx = fit_axis(ticks["x"], log_scale)
    to_co2, ry = fit_axis(ticks["y"], False)
    worst_gdp = worst_co2 = 0.0
    points = 0
    for cls, column in (("dc-ghost", CONS), ("dc-prod-ghost", PROD)):
        for country in FOCUS:
            path = page.evaluate("([name, cls]) => T.path(name, cls)", [country, cls])
            if not path or len(path) != N_YEARS:
                return None
            for i, (px, py) in enumerate(path):
                row = focus.loc[(country, YEAR_MIN + i)]
                worst_gdp = max(worst_gdp, abs(to_gdp(px) / row[GDP] - 1) * 100)
                worst_co2 = max(worst_co2, abs(to_co2(py) - row[column]))
                points += 1
    return {"gdp": worst_gdp, "co2": worst_co2, "points": points, "residual": max(rx, ry),
            "labelled": all(abs(number(t["text"]) - t["value"]) < 1e-9 for t in ticks["labels"]),
            "ticks": len(ticks["x"]) + len(ticks["y"])}


def guides_follow(page, log_scale):
    """How far the grey guides stray from tonnes = intensity x GDP / 1000, read off the
    drawn axes like the paths. Returns (how many guides, worst gap in t over their points
    inside the plot)."""
    ticks = page.evaluate("T.ticks()")
    to_gdp, _ = fit_axis(ticks["x"], log_scale)
    to_co2, _ = fit_axis(ticks["y"], False)
    top = max(t["value"] for t in ticks["y"])
    drawn = page.evaluate(
        "Array.from(document.querySelectorAll('.dc-guide'), "
        "(p) => [Number(p.getAttribute('data-intensity')), p.getAttribute('d')])")
    worst = 0.0
    for intensity, d in drawn:
        if intensity not in GUIDES:
            return len(drawn), float("inf")
        pairs = re.findall(r"(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)", d)
        for px, py in pairs:
            gdp, co2 = to_gdp(float(px)), to_co2(float(py))
            if 0 <= co2 <= top:
                worst = max(worst, abs(co2 - intensity * gdp / 1000))
    return len(drawn), worst


def chevrons_follow(page):
    """Each chevron sits on the middle of a year's segment and points the way that segment
    goes on screen (or, where the step is tiny, the way of the three years around it).
    Returns (how many chevrons, how many do not)."""
    total = off = 0
    for country in FOCUS:
        pts = page.evaluate("(name) => T.path(name, 'dc-ghost')", country)
        for x, y, angle in page.evaluate("(name) => T.chevrons(name)", country):
            total += 1
            fits = False
            for i in range(len(pts) - 1):
                (ax, ay), (bx, by) = pts[i], pts[i + 1]
                if math.hypot((ax + bx) / 2 - x, (ay + by) / 2 - y) > 0.02:
                    continue
                cx, cy = pts[max(0, i - 1)]
                dx, dy = pts[min(len(pts) - 1, i + 2)]
                for want in (math.degrees(math.atan2(by - ay, bx - ax)),
                             math.degrees(math.atan2(dy - cy, dx - cx))):
                    fits |= abs((angle - want + 180) % 360 - 180) < 0.2
            off += not fits
    return total, off


def check_geometry(s):
    log = s.log
    log.section("5. What is drawn against what is in the CSV")
    page = s.open(EMBED + "?overlay=1")
    for scale in ("linear", "log"):
        if scale == "log":
            page.locator("label.seg", has_text="Log").click()
            idle(page)
        m = measure_geometry(page, s.focus, scale == "log")
        n_guides, worst_guide = guides_follow(page, scale == "log")
        log.check(f"{scale} scale: the {n_guides} grey guides are the lines of "
                  f"{', '.join(f'{k:g}' for k in GUIDES)} kg CO2 per $ of GDP "
                  f"(worst gap {worst_guide:.4f} t over the points inside the plot)",
                  n_guides == len(GUIDES) and worst_guide < 0.01)
        print(f"   {scale} x-axis: scale fitted to the {m['ticks']} gridlines as drawn "
              f"(worst residual {m['residual']:.4f} px), then {m['points']} vertices read back")
        log.check(f"{scale} scale: the tick labels say what the gridlines are, and the gridlines "
                  f"are {'logarithmic' if scale == 'log' else 'linear'} in pixels",
                  m["labelled"] and m["residual"] < 0.02)
        log.check(f"{scale} scale: all six consumption-based and production-based paths, "
                  f"{N_YEARS} points each, read back to the CSV within {m['gdp']:.4f}% of GDP "
                  f"per capita and {m['co2']:.4f} t of CO2 per capita",
                  m["gdp"] < 0.05 and m["co2"] < 0.005)
        log.result(f"vis2_{scale}_worst_gdp_error_pct", m["gdp"])
        log.result(f"vis2_{scale}_worst_co2_error_t", m["co2"])
        total, off = chevrons_follow(page)
        log.check(f"{scale} scale: each of the {total} direction chevrons lies on its path and "
                  f"points along it in screen space", total >= 12 and off == 0)
    page.context.close()


# ---------------------------------------------------------------- 6. the numbers shown
def check_table(page, s):
    """The table view for the last year, cell by cell, and its values as results."""
    page.locator(".tv summary").click()
    table = page.evaluate("T.table()")
    columns = (("gdp_pc", GDP, TOL_GDP), ("cons_pc", CONS, TOL_CO2), ("prod_pc", PROD, TOL_CO2),
               ("net_pc", NET, TOL_CO2))
    ok = table["year"] == str(YEAR_MAX) and table["open"]
    print(f"   {'table view, ' + table['year']:<18}{'GDP':>10}{'consumption':>14}"
          f"{'production':>13}{'net':>10}   position")
    for country in FOCUS:
        cells = table["rows"][country]
        row = s.focus.loc[(country, YEAR_MAX)]
        print(f"   {country:<18}{cells[0]:>10}{cells[1]:>14}{cells[2]:>13}{cells[3]:>10}"
              f"   {cells[4]}")
        for cell, (short, column, tolerance) in zip(cells, columns):
            ok &= abs(number(cell) - row[column]) <= tolerance
        ok &= cells[4] == ("net importer" if row[NET] > 0 else "net exporter")
    s.log.check(f"the table view lists all six countries for {YEAR_MAX} and every cell agrees "
                f"with the CSV", ok)
    for country in FOCUS:               # after the table, so the table stays readable
        for cell, (short, _, _) in zip(table["rows"][country][:3], columns[:3]):
            s.log.result(f"{s.tags[country]}_{short}_{YEAR_MAX}", number(cell), 2)


def check_every_tooltip(page, s):
    """All 198 country-years through the chart's own readout, against the CSV."""
    worst = {"gdp": 0.0, "co2": 0.0}
    last_digit = []
    show = "([name, year]) => DecouplingStory.apps[0].chart.showDetail(name, year)"
    for country in FOCUS:
        for year in range(YEAR_MIN, YEAR_MAX + 1):
            page.evaluate(show, [country, year])
            tip = page.evaluate("T.tooltip()")
            row = s.focus.loc[(country, year)]
            if tip["country"] != country or tip["year"] != str(year):
                worst["gdp"] = float("inf")
            for key, column in (("gdp", GDP), ("cons", CONS), ("prod", PROD), ("net", NET)):
                shown, true = tip[key], row[column]
                kind = "gdp" if key == "gdp" else "co2"
                worst[kind] = max(worst[kind], abs(number(shown) - true))
                once = (f"${true:,.0f}" if key == "gdp" else
                        signed_tonnes(true) if key == "net" else f"{true:.2f} t")
                if shown != once:
                    last_digit.append(f"{country} {year}: shows {shown}, CSV rounds to {once}")
    page.evaluate("DecouplingStory.apps[0].chart.hideDetail()")
    n = len(FOCUS) * N_YEARS
    s.log.check(f"all {n} tooltips ({4 * n} values) agree with the CSV within ${TOL_GDP} and "
                f"{TOL_CO2} t (worst ${worst['gdp']:.2f} and {worst['co2']:.4f} t)",
                worst["gdp"] <= TOL_GDP and worst["co2"] <= TOL_CO2)
    # Not a fault of the chart: decoupling_data.js carries GDP to one decimal and CO2 to four,
    # so 39,107.495 is already 39,107.5 there before the page rounds it to a whole dollar.
    print(f"   note: {len(last_digit)} of {4 * n} values differ in their last digit from the CSV "
          f"rounded once, because the data file rounds first:")
    for line in last_digit:
        print(f"          {line}")
    s.log.result("vis2_last_digit_differences", len(last_digit), 0)


def check_values(s):
    log = s.log
    log.section(f"6. Numbers shown for {YEAR_MAX}, and every value a tooltip can show")
    page = s.open(EMBED + "?overlay=1")
    check_table(page, s)
    ok = True
    for country in FOCUS:
        label = page.evaluate("(name) => T.gap(name).label", country)
        ok &= label == signed_tonnes(s.focus.loc[(country, YEAR_MAX), NET])
        if label:
            log.result(f"{s.tags[country]}_net_pc_{YEAR_MAX}", number(label), 2)
    log.check(f"the six gap labels at {YEAR_MAX} are the net balance, rounded once from the CSV "
              f"(United States +1.49 t, not +1.50 t)", ok)
    check_every_tooltip(page, s)
    page.context.close()


# ---------------------------------------------------------------- 7. words on the page
def expected_fact(s, key):
    """The text a data-fact element must hold, recomputed from the CSV. None if unknown."""
    columns = {"gdp": GDP, "prod": PROD, "cons": CONS}
    iso = {tag: country for country, tag in s.tags.items()}
    fixed = {"n_years": str(N_YEARS), "n_focus": str(len(FOCUS)),
             "year_first": str(YEAR_MIN), "year_last": str(YEAR_MAX)}
    if key in fixed:
        return fixed[key]
    m = re.fullmatch(r"([a-z]{3})_(gdp|prod|cons)_change(_abs)?", key)
    if m and m.group(1) in iso:
        v = change(s.focus, iso[m.group(1)], columns[m.group(2)], YEAR_MIN, YEAR_MAX)
        return percent_abs(v) if m.group(3) else percent(v)
    m = re.fullmatch(r"([a-z]{3})_net_(\d{4})", key)
    if m and m.group(1) in iso:
        return signed_tonnes(s.focus.loc[(iso[m.group(1)], int(m.group(2))), NET])
    m = re.fullmatch(r"([a-z]{3})_offset_share", key)
    if m and m.group(1) in iso:
        country = iso[m.group(1)]
        wider = s.focus.loc[(country, YEAR_MAX), NET] - s.focus.loc[(country, YEAR_MIN), NET]
        cut = s.focus.loc[(country, YEAR_MIN), PROD] - s.focus.loc[(country, YEAR_MAX), PROD]
        return percent_abs(100 * wider / cut)
    return None


def check_claims(s):
    """The sentences of the synthesis, tested against the CSV as plain statements."""
    log, focus, high = s.log, s.focus, s.high
    gdp = {c: change(focus, c, GDP, YEAR_MIN, YEAR_MAX) for c in FOCUS}
    prod = {c: change(focus, c, PROD, YEAR_MIN, YEAR_MAX) for c in FOCUS}
    cons = {c: change(focus, c, CONS, YEAR_MIN, YEAR_MAX) for c in FOCUS}
    net = {c: focus.loc[(c, YEAR_MAX), NET] for c in FOCUS}
    log.check("claim: GDP per capita rose and CO2 per capita fell on both accounts in all four "
              "high-income countries", len(high) == 4
              and all(gdp[c] > 0 and prod[c] < 0 and cons[c] < 0 for c in high))
    log.check("claim: the production-based fall is the larger one in the United Kingdom, the "
              "United States and Germany, and the smaller one in Sweden",
              sorted(c for c in high if prod[c] < cons[c])
              == ["Germany", "United Kingdom", "United States"])
    log.check("claim: the four were net importers in 2022, China and India net exporters",
              all(net[c] > 0 for c in high) and all(net[c] < 0 for c in FOCUS if c not in high))


def check_page_copy(page, s):
    log = s.log
    with open(os.path.join(WEB, INDEX), encoding="utf-8") as fh:
        source = fh.read()
    facts = page.evaluate("T.facts()")
    wrong, typed = [], []
    for key, shown in facts:
        want = shown if key == "retrieved" else expected_fact(s, key)
        if want != shown:
            wrong.append(f"{key}: page {shown!r}, CSV {want!r}")
        static = re.search(r'data-fact="' + key + r'">([^<]*)<', source)
        if not static or static.group(1) != shown:
            typed.append(key)
    log.check(f"the {len(facts)} numbers in the page copy (data-fact) equal the CSV"
              + (": " + "; ".join(wrong) if wrong else ""), not wrong and len(facts) >= 15)
    log.check("the same numbers are typed into the HTML, for a reader without JavaScript"
              + (f" (differs: {', '.join(typed)})" if typed else ""), not typed)
    check_claims(s)
    info = page.evaluate(PAGE_FACTS, [list(COPY_IDS), ARTICLE[0]])
    log.check("the page carries its title, its byline and the five copy blocks by id",
              info["title"] == "Decoupling or outsourcing?" and info["byline"] == BYLINE
              and not info["missing"])
    log.check(f"the article is linked as {ARTICLE[1]!r}", info["link"] == [ARTICLE[1]])
    log.check("accessibility basics: header, nav, main and footer landmarks, a page language, "
              "a name on every control, frame and image, and a light colour scheme",
              not info["landmarks"] and not info["unnamed"] and info["lang"] == "en"
              and info["scheme"] == "light")
    for line in info["unnamed"]:
        print(f"          unnamed: {line}")


def contrast(a, b):
    """WCAG contrast ratio of two #rrggbb colours."""
    def luminance(colour):
        parts = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        parts = [p / 12.92 if p <= 0.03928 else ((p + 0.055) / 1.055) ** 2.4 for p in parts]
        return 0.2126 * parts[0] + 0.7152 * parts[1] + 0.0722 * parts[2]
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def check_words(s):
    log = s.log
    log.section("7. Words and numbers on the page")
    for target, height in ((INDEX, 900), (EMBED, VIEW[1])):
        page = s.open(target, height=height)
        odd, found = set(), set()
        for i in range(4):                      # every caption is page text as well
            page.locator(".story-step").nth(i).click()
            words = page.evaluate("T.words()")
            odd |= {ch for ch in words if ord(ch) > 126 or (ord(ch) < 32 and ch not in "\n\t\r")}
            found |= {w for w in BANNED if re.search(r"\b" + re.escape(w) + r"\b", words, re.I)}
        log.check(f"{target}: every string a reader can meet is plain ASCII"
                  + (f" (found {sorted(odd)!r})" if odd else ""), not odd)
        log.check(f"{target}: none of the {len(BANNED)} banned words or phrases appears"
                  + (f" (found {', '.join(sorted(found))})" if found else ""), not found)
        if target == INDEX:
            check_page_copy(page, s)
        page.context.close()

    ratio = {name: contrast(colour, SURFACE) for name, colour in
             (("ink", INK), ("ink_2", INK_2), ("muted", MUTED))}
    log.check(f"text contrast on the chart surface: ink {ratio['ink']:.1f}:1 and secondary ink "
              f"{ratio['ink_2']:.1f}:1 (body text, axes, labels; 4.5 needed), muted "
              f"{ratio['muted']:.1f}:1 (only the large year range and years not yet reached; "
              f"3 needed)", ratio["ink"] >= 4.5 and ratio["ink_2"] >= 4.5 and ratio["muted"] >= 3
              and contrast(INK_2, PAGE) >= 4.5)
    for name, value in ratio.items():
        log.result(f"contrast_{name}_on_surface", value, 2)


# ---------------------------------------------------------------- 8. layout at every width
def overlaps(boxes):
    """Pairs of (label, box) whose boxes share more than a sliver."""
    out = []
    for i, (a, (ax0, ay0, ax1, ay1)) in enumerate(boxes):
        for b, (bx0, by0, bx1, by1) in boxes[i + 1:]:
            if min(ax1, bx1) - max(ax0, bx0) > 1 and min(ay1, by1) - max(ay0, by0) > 1:
                out.append(f"{a} / {b}")
    return out


def check_layout(s):
    log = s.log
    log.section("8. Layout from 360 px to 1400 px")
    print(f"   {'width':>8}{'chart':>14}{'content':>10}{'names':>8}{'years':>8}   state")
    for width in WIDTHS:
        for query in ("", "?year=2007&overlay=1", "?x=log"):
            page = s.open(EMBED + query, width=width, height=2400)
            m = page.evaluate("T.layout()")
            names = [(e["text"], e["box"]) for e in page.evaluate("T.labels()") if e["box"]]
            years = [(e["text"], e["box"]) for e in page.evaluate("T.yearLabels()")]
            clash = overlaps(names + years)
            drawn_width = float(m["viewBox"].split()[2])
            state = query[1:] or "default"
            print(f"   {width:>8}{m['svgWidth']:>8.0f} x {m['svgHeight']:<4.0f}{m['content']:>9}"
                  f"{len(names):>8}{len(years):>8}   {state}")
            log.check(f"{width} px, {state}: no sideways scroll, the viewBox matches the drawn "
                      f"size, every country is named, no label leaves the chart or overlaps "
                      f"another", m["scrollWidth"] <= m["innerWidth"] and not m["outside"]
                      and not clash and abs(drawn_width - m["svgWidth"]) < 1
                      and len(names) == len(FOCUS))
            for line in m["outside"] + clash:
                print(f"          {line}")
            if width == VIEW[0] and not query:
                colours = {e["fill"] for e in page.evaluate("T.labels()")}
                log.check("country names are drawn in ink, never in a data colour",
                          colours == {"rgb(11, 11, 11)"})
            page.context.close()
    for width in (360, 390, 1400):
        page = s.open(INDEX, width=width, height=900)
        m = page.evaluate("T.layout()")
        log.check(f"index.html at {width} px has no sideways scroll "
                  f"({m['scrollWidth']} px of content in {m['innerWidth']} px)",
                  m["scrollWidth"] <= m["innerWidth"])
        page.context.close()


# ---------------------------------------------------------------- 9. captures
def font(size):
    """Segoe UI Semibold for the labels drawn on the comparison plate, with fallbacks."""
    for name in ("seguisb.ttf", "segoeuib.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def piece(page, selector):
    """One element of the page as a PIL image."""
    path = PNG_PLATE + ".part.png"
    page.locator(selector).screenshot(path=path)
    with Image.open(path) as im:
        out = im.convert("RGB")
    os.remove(path)
    return out


def stage_at(s, query, stage_width):
    """The plot alone, drawn `stage_width` CSS px wide."""
    page = s.open(EMBED + query, width=stage_width + 60, height=1600, density=DENSITY)
    spare = "window.innerWidth - document.querySelector('.dc-stage').clientWidth"
    for _ in range(3):                  # the page padding changes with the width, so approach it
        page.set_viewport_size({"width": stage_width + page.evaluate(spare), "height": 1600})
        settle(page, 4)
    out = piece(page, ".dc-stage")
    page.context.close()
    return out


def capture_plate(s):
    """Three states of the chart side by side, under one legend and one key."""
    pad, gap, label_height = 44, 40, 56
    width = (PLATE_WIDTH - 2 * pad - 2 * gap) // 3
    states = ((f"?year={PIVOT_YEAR}", f"Year {PIVOT_YEAR}"), ("", f"Year {YEAR_MAX}"),
              ("?overlay=1", f"Year {YEAR_MAX}, production-based path on"))
    panels = [stage_at(s, query, width // DENSITY) for query, _ in states]
    page = s.open(EMBED + "?overlay=1", density=DENSITY)
    strips = [piece(page, ".dc-legend"), piece(page, ".dc-key")]
    page.context.close()

    height = (pad + strips[0].height + 10 + strips[1].height + 34 + label_height + 12
              + max(p.height for p in panels) + pad)
    plate = Image.new("RGB", (PLATE_WIDTH, height), SURFACE)
    draw = ImageDraw.Draw(plate)
    y = pad
    for strip, space in zip(strips, (10, 34)):
        plate.paste(strip.crop((0, 0, min(strip.width, PLATE_WIDTH - 2 * pad), strip.height)),
                    (pad, y))
        y += strip.height + space
    for i, (panel, (_, label)) in enumerate(zip(panels, states)):
        x = pad + i * (width + gap)
        draw.text((x, y), label, font=font(40), fill=INK)
        plate.paste(panel, (x, y + label_height + 12))
    plate.save(PNG_PLATE, optimize=True)
    return panels[0].width // DENSITY


def page_overview(columns=3, pad=60, gap=110):
    """The full-page capture is many times taller than a report page, so it is also laid
    out as a sheet of columns, read top to bottom and then left to right, and scaled to
    PLATE_WIDTH. Returns the sheet's (width, height)."""
    with Image.open(PNG_PAGE) as im:
        page = im.convert("RGB")
    rows = -(-page.height // columns)
    sheet = Image.new("RGB", (columns * page.width + (columns - 1) * gap + 2 * pad,
                              rows + 2 * pad), SURFACE)
    for i in range(columns):
        part = page.crop((0, i * rows, page.width, min(page.height, (i + 1) * rows)))
        sheet.paste(part, (pad + i * (page.width + gap), pad))
    size = (PLATE_WIDTH, round(sheet.height * PLATE_WIDTH / sheet.width))
    sheet.resize(size, Image.LANCZOS).save(PNG_OVERVIEW, optimize=True)
    return size


def capture(s):
    log = s.log
    log.section("9. Captures")
    page = s.open(EMBED, density=DENSITY)
    page.screenshot(path=PNG_MAIN, clip=page.evaluate("T.clip()"), full_page=True)
    state = page.evaluate("T.state()")
    page.context.close()

    # The year is scrubbed to the pivot and the overlay is on, so the marker under the
    # pointer, the gap beside it and the tooltip all describe the same country and year.
    page = s.open(EMBED + f"?overlay=1&year={PIVOT_YEAR}", density=DENSITY)
    x, y = vertex(page, "United Kingdom", PIVOT_YEAR)
    page.mouse.move(x - 80, y - 120)
    page.mouse.move(x + 3, y + 2, steps=8)
    settle(page, 3)
    tip = page.evaluate("T.tooltip()")
    page.screenshot(path=PNG_HOVER, clip=page.evaluate("T.clip()"), full_page=True)
    log.check(f"the hover capture was taken with the tooltip open on the United Kingdom, "
              f"{PIVOT_YEAR}, after a real mouse move",
              tooltip_agrees(tip, s.focus, "United Kingdom", PIVOT_YEAR))
    page.context.close()

    panel = capture_plate(s)

    page = s.open(INDEX, height=1000, density=DENSITY)
    show_optional_parts(page)
    tall = page.evaluate("document.documentElement.scrollHeight")
    page.screenshot(path=PNG_PAGE, full_page=True)
    log.check("the full-page capture was taken with nothing failing to load", page.watch.report())
    page.context.close()

    print(f"   chart in the main capture: {state['width']} x {state['height']} CSS px, plot area "
          f"{state['plot']['width']:.0f} x {state['plot']['height']:.0f}; plate panels {panel} "
          f"CSS px wide; page {tall} CSS px tall")
    sizes = {}
    for name, path in (("main", PNG_MAIN), ("plate", PNG_PLATE), ("hover", PNG_HOVER),
                       ("page", PNG_PAGE)):
        with Image.open(path) as im:
            sizes[name] = im.size
        print(f"   {os.path.relpath(path, ROOT):<50}{sizes[name][0]:>6} x {sizes[name][1]:<6}"
              f"{os.path.getsize(path) / 1024:>8.0f} KB")
    log.check(f"the chart capture, the hover capture, the plate and the page capture are each "
              f"{PLATE_WIDTH} px wide", all(size[0] == PLATE_WIDTH for size in sizes.values()))
    sheet = page_overview()
    print(f"   {os.path.relpath(PNG_OVERVIEW, ROOT):<50}{sheet[0]:>6} x {sheet[1]:<6}"
          f"{os.path.getsize(PNG_OVERVIEW) / 1024:>8.0f} KB   the page in three columns")
    log.check("the overview sheet holds the whole page capture in three columns",
              sheet[0] == PLATE_WIDTH and os.path.getsize(PNG_OVERVIEW) > 0)
    for name, size in sizes.items():
        log.result(f"vis2_capture_{name}_width_px", size[0], 0)
        log.result(f"vis2_capture_{name}_height_px", size[1], 0)
    log.result("vis2_chart_width_css_px", state["width"], 0)
    log.result("vis2_chart_height_css_px", state["height"], 0)


# ---------------------------------------------------------------- main
def run(show_results=True):
    from playwright.sync_api import sync_playwright

    log = Log(show_results=show_results)
    log.banner("MODULE TWO - VISUALIZATION 2: WEB PAGE SELF-TEST AND CAPTURES")
    print("   web/ served from a local port and from disk; browser: Microsoft Edge, headless")
    check_files(log)
    with sync_playwright() as playwright:
        session = Session(playwright, log)
        try:
            print(f"   Edge {session.browser.version}, {len(session.focus)} rows of "
                  f"inputs/decoupling_focus.csv to check against")
            check_loads(session)
            check_interaction(session)
            check_story(session)
            check_geometry(session)
            check_values(session)
            check_words(session)
            check_layout(session)
            capture(session)
        finally:
            session.close()
    ok = log.tally()
    return {"results": log.results, "passed": log.passed, "failed": log.failed, "ok": ok}


def run_in_child(show_results=True):
    """The same run in a child process, for a caller that already has an event loop
    (a notebook): Playwright's synchronous API cannot start inside one."""
    reply = subprocess.run([sys.executable, "-u", os.path.abspath(__file__)], cwd=ROOT,
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    for line in reply.stdout.splitlines():
        if show_results or not line.lstrip().startswith("result:"):
            print(line)
    if reply.returncode and reply.stderr:
        print(reply.stderr[-2000:])
    results = {m.group(1): float(m.group(2)) for m in
               re.finditer(r"^\s*result:\s*(\w+)\s*=\s*([-+0-9.eE]+)\s*$", reply.stdout, re.M)}
    passed = len(re.findall(r"^\s*check: .* PASS$", reply.stdout, re.M))
    failed = len(re.findall(r"^\s*check: .* FAIL$", reply.stdout, re.M))
    return {"results": results, "passed": passed, "failed": failed,
            "ok": reply.returncode == 0 and failed == 0}


def main(show_results=True):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return run(show_results)
    return run_in_child(show_results)


if __name__ == "__main__":
    sys.exit(0 if main()["ok"] else 1)
