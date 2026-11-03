"""
report_spec.py -- the single source of truth for report metadata, section order
and every figure and terminal capture the Module Two report uses.

make_report.py renders this into report/module02_report.docx (the working copy,
with the screenshot callout boxes), report/module02_report_clean.docx (the
submission copy, without them) and report/module02_report.md; the same list also
generates screenshots/SCREENSHOT_INSTRUCTIONS.md, so the document and the
instructions can never disagree about a filename.

Conventions for the section files, report/sections/<key>.md
------------------------------------------------------------
* Headings. make_report.py writes each section's title (the "title" below) as
  Heading 1 itself, so a section file must NOT repeat it. Sub-headings inside a
  file start at "##" (Heading 2), then "###" (Heading 3).
* Shot markers. A line containing only  [[SHOT:V1b]]  places that shot - the
  callout box (working copy only), the embedded figure and its numbered caption -
  exactly there. Every shot of a section that no marker references is appended
  at the end of that section, in the order listed below. A shot is placed once.
* Figure numbers. Captions are written here WITHOUT a number; the builder
  prefixes "Figure N - " in document order. To cite a figure in prose, write
  [[FIG:V1b]] and it becomes "Figure N" in the .docx and the .md.
* To-do notes. A line containing only  [[TODO: text]]  becomes a boxed note to
  the student in the working copy and is left out of the submission copy.
* Links. [text](https://...) and bare https://... URLs become real hyperlinks.
* Terminal captures. Every target "terminal/NAME.png" is drawn by
  scripts/render_logs.py from its entry RENDER["NAME"] (log file, command,
  start and end marker), so each capture is an excerpt of one canonical log.

Shot fields
-----------
  sid      short id used in the callout heading and in [[SHOT:...]] markers:
           section prefix (N, R, V1, V2, V3, E) + one lowercase letter, in
           document order
  target   filename inside screenshots/
  command  exact command to run from the project root with .venv active
  crop     exactly what region to capture, or what to do in the browser first
  caption  caption text, without the "Figure N - " prefix
  width    rendered width in inches (the builder shrinks it if the image would
           be taller than a page allows). For terminal captures it is a maximum:
           make_report.py sizes those so the terminal text lands near 7.5 pt.
  note     optional extra line for the callout (regeneration hints)
"""

META = {
    "course": "Applied Computer Vision / Data Visualization (Module Two)",
    "assignment": "Module Two - Data Three Ways",
    "title": "Module Two - Data Three Ways",
    "subtitle": "Decoupling or outsourcing? Growth, carbon and trade in six economies, 1990-2022",
    "footer": "Module Two - Data Three Ways",
    "student": "Taher Turki",
    "date": "October 2026",
    # The only text Appendix A carries besides the listings, if APPENDIX_FILES
    # is ever filled in.
    "appendix_intro": ("The files below are sources of the three visualizations, reproduced "
                       "exactly as they stood when this report was built. The Python scripts "
                       "import their paths, colour tokens and loaders from `scripts/common.py` "
                       "and read the tables that `scripts/prepare_data.py` writes; both are in "
                       "the project folder."),
}

# Shared wording, so every callout of one kind says the same thing the same way.
_TERM_CROP = ("The terminal window's text area only, showing the output of "
              "'{cmd}' {part}, with every 'check: ... PASS' line of that stretch "
              "in frame. The pre-rendered PNG draws the prompt line above the "
              "excerpt. Leave out the window title bar, tabs and the taskbar. If "
              "the excerpt is taller than the window, enlarge the window or reduce "
              "the font size rather than stitching two captures together.")
_RENDERED = "Captured stdout, rendered as an image."


def _term_note(log):
    return (f"The embedded PNG is drawn by scripts/render_logs.py from "
            f"screenshots/logs/{log}, which scripts/run_all.py writes; its start "
            f"and end markers are listed in the RENDER table of render_logs.py. "
            f"'python scripts/run_all.py' regenerates both the log and the PNG.")


def _fig_crop(what):
    return (f"The complete figure, cropped at its outer border: {what} The "
            f"command writes the PNG straight to the target path, so either open "
            f"that file or the matching cell output in notebooks/module02_story.ipynb "
            f"and crop there - no window chrome, toolbar or notebook margin.")


def _orig_crop(what):
    return (f"Nothing to crop: this is the original image itself, {what}, re-saved "
            f"as PNG without resampling. To replace it, put a newer copy in inputs/ "
            f"under the same name (python scripts/fetch_inputs.py --fetch downloads "
            f"one) and re-run the command.")


def _browser_crop(steps, region):
    return (f"A browser capture of the live page. {steps} Then capture {region}, "
            f"with no browser chrome, bookmarks bar or scrollbar in frame. Use a "
            f"window about 1300 px wide at 200% zoom or a high-DPI display so the "
            f"capture is about 2600 px wide.")


def _terminal(sid, name, script, part, caption):
    """A terminal shot: an excerpt of one script's log."""
    cmd = f"python scripts/{script}.py"
    return {"sid": sid, "target": f"terminal/{name}.png", "command": cmd,
            "crop": _TERM_CROP.format(cmd=cmd, part=part),
            "note": _term_note(f"{script}.txt"),
            "caption": f"{caption} {_RENDERED}", "width": 6.5}


_PREP = "python scripts/prepare_data.py"
_ORIG = "python scripts/original_story.py"
_V1 = "python scripts/vis1_altair_linked.py"
_V2 = "python scripts/capture_web.py"
_V3 = "python scripts/vis3_seaborn_diverging.py"
_ALL = "python scripts/run_all.py"
_OWID = ("Our World in Data, CC BY; reproduced unaltered from "
         "https://ourworldindata.org/co2-gdp-decoupling")


SECTIONS = [
    {
        "key": "narrative",
        "title": "1. Central Narrative and Data Description",
        "code": [],
        "shots": [],
    },
    {
        "key": "remix",
        "title": "2. Story Remix Context",
        "code": [],
        "shots": [
            {
                "sid": "Ra",
                "target": "00a_original_owid_line_chart.png",
                "command": _ORIG,
                "crop": _orig_crop("Our World in Data's own 1700 x 1200 px PNG export of the "
                                   "article's Grapher chart for the United Kingdom"),
                "caption": "The original, Chart A: \"Change in per capita CO2 emissions and "
                           "GDP\", United Kingdom, percent change since 1990. This is the "
                           "export served on 4 October 2026, so it runs past the 2021 article; "
                           "its GDP line is a World Bank series at 2021 prices. Source: "
                           + _OWID + ".",
                "width": 5.4,
            },
            {
                "sid": "Rb",
                "target": "00b_original_owid_two_countries.png",
                "command": _ORIG,
                "crop": _orig_crop("the same Grapher chart exported with the United Kingdom and "
                                   "China selected (1700 x 1200 px)"),
                "caption": "Chart A after adding China with its own country control. The chart "
                           "splits into one panel per country on a shared percent axis that "
                           "runs to +1,500%, and the United Kingdom's three lines collapse onto "
                           "the zero line. Source: " + _OWID + ".",
                "width": 5.4,
            },
            {
                "sid": "Rc",
                "target": "00c_original_owid_arrow_grid.png",
                "command": _ORIG,
                "crop": _orig_crop("the article's static grid image at the 2614 x 2736 px size "
                                   "the page serves"),
                "caption": "The original, Chart B: a static grid of 30 countries, each as two "
                           "arrows for the change in GDP per capita and in consumption-based "
                           "CO2 per capita between 2005 and 2020. The United Kingdom is not "
                           "among them. Image credited to Max Roser. Source: " + _OWID + ".",
                "width": 4.9,
            },
        ],
    },
    {
        "key": "vis1",
        "title": "3. Visualization 1 - Altair Linked Coordinated Views",
        "page_break": True,
        "code": ["scripts/vis1_altair_linked.py"],
        "shots": [
            {
                "sid": "V1a",
                "target": "01_vis1_altair_linked.png",
                "command": _V1,
                "crop": _fig_crop("the title and subtitle, the time series with its brush and "
                                  "line-end labels, the scatter with both legends and the two "
                                  "shaded bands, and the two note lines at the bottom."),
                "caption": "Visualization 1, static export with the brush on 2013-2022 and the "
                           "United Kingdom in the top view. Top: percent change since 1990 in "
                           "GDP per capita and in CO2 per capita on both accounts. Bottom: 109 "
                           "countries at their means over the brushed years; x is GDP per capita "
                           "on a log scale, y the net balance of embodied CO2, area is "
                           "population and hue the World Bank income group. Seven countries lie "
                           "beyond the axis and are drawn as triangles in the shaded bands.",
                "width": 6.5,
            },
            {
                "sid": "V1b",
                "target": "01c_vis1_browser_brushed.png",
                "command": _V1,
                "crop": _browser_crop("Open web/altair_export.html, drag across 2002 to 2008 in "
                                      "the top panel, choose China in the menu above the chart "
                                      "and rest the pointer on China's bubble.",
                                      "the menu, both panels and the tooltip"),
                "caption": "Browser capture of the live chart in Microsoft Edge, taken after the "
                           "brush was dragged with the mouse to 2002-2008 and China was picked "
                           "from the menu. The top view, the panel title, the bubbles and the "
                           "tooltip (China, mean net balance -0.87 t over 2002-2008) all follow "
                           "the selection.",
                "width": 5.4,
                "note": "The script takes this capture itself with Playwright driving Edge; "
                        "run it without --no-browser to regenerate the file.",
            },
            {
                "sid": "V1c",
                "target": "01_vis1_brush_comparison.png",
                "command": _V1,
                "crop": _fig_crop("the title, both scatter panels with their headings, the "
                                  "shared legends on the right and the list of countries beyond "
                                  "the axis under each panel."),
                "caption": "Comparison plate: the scatter under two brush positions. Left, each "
                           "country's mean over 1990-1999; right, its mean over 2013-2022. The "
                           "United Kingdom and the United States move up, Germany and Sweden "
                           "move down, and China and India sink further below zero. Countries "
                           "beyond the axis are listed under each panel with their true values.",
                "width": 6.5,
            },
        ],
    },
    {
        "key": "vis2",
        "title": "4. Visualization 2 - D3.js Connected Scatterplot",
        "page_break": True,
        "code": ["web/d3_vis.js", "web/d3_story.js"],
        "shots": [
            {
                "sid": "V2a",
                "target": "02_vis2_d3_connected_scatter.png",
                "command": _V2,
                "crop": _browser_crop("Open web/d3_embed.html (or the Visualization 2 section "
                                      "of web/index.html) and leave the year slider at 2022.",
                                      "the control row and the chart card, from the Play button "
                                      "to the source line"),
                "caption": "Visualization 2 at 2022, on its default linear axis. Each line is "
                           "one country's path through GDP per capita (x) and consumption-based "
                           "CO2 per capita (y) from 1990 to 2022. Chevrons give the direction "
                           "of travel and hollow markers the years 1990, 2000 and 2010. The "
                           "grey rays are constant carbon intensities of 0.15, 0.3 and 0.6 kg "
                           "CO2 per dollar of GDP.",
                "width": 6.5,
            },
            {
                "sid": "V2b",
                "target": "02_vis2_scrub_comparison.png",
                "command": _V2,
                "crop": _fig_crop("the legend and key rows across the top and the three "
                                  "labelled panels (Year 2007; Year 2022; Year 2022, "
                                  "production-based path on). The script composes this plate "
                                  "from three browser captures."),
                "caption": "Comparison plate: three states of the chart. Left, the slider at "
                           "2007, with the later years faded. Centre, 2022. Right, 2022 with "
                           "the production-based paths overlaid and each country's gap between "
                           "the two accounts labelled, which is its net balance.",
                "width": 6.5,
            },
            {
                "sid": "V2c",
                "target": "02a_vis2_hover_tooltip.png",
                "command": _V2,
                "crop": _browser_crop("Open web/d3_embed.html?overlay=1&year=2007 and move the "
                                      "pointer onto the United Kingdom's marker.",
                                      "the control row and the chart card with the tooltip open"),
                "caption": "Browser capture after a real mouse move onto the United Kingdom's "
                           "2007 point, with the overlay on. The tooltip gives GDP per capita, "
                           "both CO2 accounts and the net balance (+3.34 t), values first, and "
                           "the other five paths dim.",
                "width": 5.8,
            },
        ],
    },
    {
        "key": "vis3",
        "title": "5. Visualization 3 - Seaborn Diverging Trade Balance",
        "page_break": True,
        "code": ["scripts/vis3_seaborn_diverging.py"],
        "shots": [
            {
                "sid": "V3a",
                "target": "03_vis3_seaborn_diverging.png",
                "command": _V3,
                "crop": _fig_crop("the title, subtitle and two-entry legend, all six facets "
                                  "with their headers and value labels, the shared axis labels "
                                  "and the source note."),
                "caption": "Visualization 3: net balance of CO2 embodied in trade, t per person, "
                           "1990-2022, in six facets on shared axes. Blue above zero marks a "
                           "net importer and orange below zero a net exporter. Labels give the "
                           "1990 value, the 2022 value and the year furthest from zero.",
                "width": 6.5,
            },
            {
                "sid": "V3b",
                "target": "03a_vis3_derivation_plate.png",
                "command": _V3,
                "crop": _fig_crop("the title, subtitle and legend, the two-account panel on the "
                                  "left, the gap panel on the right and the source note."),
                "caption": "Derivation plate for the United Kingdom. Left: production-based and "
                           "consumption-based CO2 per person, with the gap between them shaded. "
                           "Right: the gap alone on a zero baseline, at three times the "
                           "vertical scale.",
                "width": 6.5,
            },
            {
                "sid": "V3c",
                "target": "03b_vis3_absolute_balance.png",
                "command": _V3,
                "crop": _fig_crop("the title, subtitle and legend, the three columns of bars "
                                  "for 1990, 2007 and 2022 with their value labels, and the "
                                  "source note."),
                "caption": "The same balance in million tonnes for 1990, 2007 and 2022. China's "
                           "export balance, small per person, is the largest flow of the six in "
                           "tonnes: 1,285 Mt in 2022, against 511 Mt of net imports for the "
                           "United States.",
                "width": 6.5,
            },
        ],
    },
    {
        "key": "synthesis",
        "title": "6. Synthesis and Answer to the Central Question",
        "page_break": True,
        "code": [],
        "shots": [],
    },
    {
        "key": "extra",
        "title": "7. Extra Credit Summary and Web Portfolio Deployment",
        "code": [],
        "shots": [
            {
                "sid": "Ea",
                "target": "02c_web_page_overview.png",
                "command": _V2,
                "crop": _browser_crop("Open web/index.html and capture the whole page from the "
                                      "title to the footer (a full-page capture tool is the "
                                      "easy way).",
                                      "the entire page; the script then lays its capture out in "
                                      "three columns so that it fits a report page"),
                "caption": "The portfolio page web/index.html, captured in full and laid out in "
                           "three columns, with the top of the page at the upper left: the "
                           "question, Visualization 1 embedded from its Altair export, the live "
                           "D3 chart, the Seaborn figure, the synthesis and the sources.",
                "width": 6.5,
                "note": "The uncut capture is screenshots/02b_web_page_full.png (2600 px wide, "
                        "about 12,500 px tall).",
            },
        ],
    },
    {
        "key": "references",
        "title": "8. References",
        "page_break": True,
        "hanging": True,
        "code": [],
        "shots": [],
    },
]

# Appendix A is off for this module. The four visualization sources come to
# several thousand lines, most of them self-checks, so each visualization section
# quotes the lines that matter (verify_report.py confirms every excerpt is
# verbatim) and names its files, which are in the project folder. To append the
# full listings, put (project-relative path, one-line description) pairs here,
# for example ("scripts/vis3_seaborn_diverging.py", "Visualization 3 - ...").
APPENDIX_FILES = []


def figure_path(shot):
    """Project-relative path of the pre-rendered PNG for a shot."""
    return shot.get("figure") or f"screenshots/{shot['target']}"


def all_shots():
    """(section, shot) pairs in spec order."""
    return [(sec, shot) for sec in SECTIONS for shot in sec["shots"]]


_PREFIX = {"narrative": "N", "remix": "R", "vis1": "V1", "vis2": "V2", "vis3": "V3",
           "synthesis": "S", "extra": "E", "references": "X"}

# Phrases the writing brief bans; captions are report text too.
_BANNED = ("delve", "tapestry", "testament", "crucial", "moreover", "furthermore",
           "in conclusion", "it is important to note", "serves as a bridge",
           "rich visual representation", "multifaceted", "leverage", "robust",
           "seamless", "comprehensive", "underscores", "pivotal", "nuanced",
           "holistic", "realm", "landscape", "navigate", "foster", "as we can see",
           "this demonstrates that", "in summary", "overall,")


def _self_check():
    sids = [s["sid"] for _, s in all_shots()]
    targets = [s["target"] for _, s in all_shots()]
    keys = [s["key"] for s in SECTIONS]
    assert len(sids) == len(set(sids)), "duplicate screenshot id"
    assert len(targets) == len(set(targets)), "two shots share a target file"
    assert len(keys) == len(set(keys)), "duplicate section key"
    for sec, s in all_shots():
        for field in ("sid", "target", "command", "crop", "caption", "width"):
            assert field in s, f"{s.get('sid')}: missing {field}"
        assert not s["caption"].lower().startswith("figure"), \
            f"{s['sid']}: captions are numbered by the builder"
        prefix = _PREFIX[sec["key"]]
        assert s["sid"][:-1] == prefix and s["sid"][-1].islower(), \
            f"{s['sid']}: sid must be '{prefix}' + one letter"
        assert s["target"].endswith(".png"), f"{s['sid']}: target must be a PNG"
        if s["target"].startswith("terminal/"):
            assert "note" in s, f"{s['sid']}: terminal shots carry a _term_note"
        for field in ("caption", "crop", "note"):
            text = s.get(field, "")
            assert text.isascii(), f"{s['sid']}: non-ASCII character in {field}"
        low = s["caption"].lower()
        for phrase in _BANNED:
            assert phrase not in low, f"{s['sid']}: banned phrase '{phrase}'"
    for sec in SECTIONS:
        letters = [s["sid"][-1] for s in sec["shots"]]
        assert letters == sorted(letters), f"{sec['key']}: shots are not in letter order"
    names = {fname for fname, _ in APPENDIX_FILES}
    for sec in SECTIONS:
        assert not names or set(sec.get("code") or []) <= names, \
            f"{sec['key']}: a code reference points outside Appendix A"


_self_check()
