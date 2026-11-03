"""
make_report.py -- assemble the Module Two report from the section text in
report/sections/, the figures in screenshots/ and the plan in report_spec.py.

One plan, four outputs:
  report/module02_report.docx        the working copy, with a shaded instruction
                                     callout above every figure
  report/module02_report_clean.docx  identical minus the callouts (submission copy)
  report/module02_report.md          Markdown twin of the submission copy
  screenshots/SCREENSHOT_INSTRUCTIONS.md

The section-file conventions (heading levels, [[SHOT:...]] placement markers
and [[FIG:...]] figure references) are documented in report_spec.py. Nothing
here crashes on a missing input: the sections and figures come from other
scripts that may not have run yet, so a missing section or figure becomes a
visible placeholder in the document and a line in the build summary.

Carried over from the Module One builder. What changed for this module:
Appendix A takes project-relative paths, because one of the three
visualizations is JavaScript under web/ and not a script under scripts/; the
title block carries a subtitle; a section flagged "hanging" in the spec (the
reference list) is set with a hanging indent; and links in the section text
become real hyperlinks (see docx_md.py). Appendix A is now optional: it is
built only when report_spec.APPENDIX_FILES lists files, and with an empty list
each section names its source files instead (the visualization sources of this
module run to several thousand lines, so the report quotes short excerpts and
leaves the full files to the project folder). As before the builder keeps
every trace of itself out of the submission, and the Markdown twin follows the
clean copy (the callouts live in the working .docx and in
SCREENSHOT_INSTRUCTIONS.md).

Run:  python scripts/make_report.py
"""
import datetime
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image

from docx_md import (MONO, _put, add_inline, cell_margins, code_table,
                     keep_table_with_next, no_space, para_border, render_markdown,
                     set_borders, set_font, shade)
from report_spec import APPENDIX_FILES, META, SECTIONS, figure_path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPORT = os.path.join(ROOT, "report")
SECDIR = os.path.join(REPORT, "sections")
SHOTS = os.path.join(ROOT, "screenshots")
CACHE = os.path.join(REPORT, ".embed_cache")

OUT_FULL = os.path.join(REPORT, "module02_report.docx")
OUT_CLEAN = os.path.join(REPORT, "module02_report_clean.docx")
OUT_MD = os.path.join(REPORT, "module02_report.md")
OUT_GUIDE = os.path.join(SHOTS, "SCREENSHOT_INSTRUCTIONS.md")

ACCENT = RGBColor(0x1F, 0x38, 0x64)
MUTED = RGBColor(0x55, 0x5F, 0x6D)
AMBER = RGBColor(0x8A, 0x60, 0x00)
ALERT = RGBColor(0xB0, 0x3A, 0x2E)

# 300 DPI at the embedded width keeps the small type on a two-panel comparison
# plate sharp. The plates are saved 2600 px wide for a 6.5 in slot (400 px/in),
# inside the 1.5x band, so they are embedded untouched.
TARGET_DPI = 300
# A Letter page with 1-inch margins has 9 in of body height. I keep a figure at
# or under 7.9 in so its caption fits beneath it on the same page.
MAX_FIG_H = 7.9
# Tall terminal captures are sliced at blank rows between text lines instead of
# being shrunk until the text is unreadable. The tallest capture this report
# embeds (the run_all excerpt, 42 lines) is 7.1 in at its embedded width, so
# with a first slice of 7.2 in none of them is cut; render_logs.py clips that
# excerpt to stay under the limit.
FIRST_SLICE_H = 7.2
NEXT_SLICE_H = 8.3
TERM_DPI = 170        # the savefig DPI in render_logs.py
TERM_SCALE = 0.75     # 10 pt rendered text -> ~7.5 pt on the page
TERM_MIN_W = 4.5

MARKER = re.compile(r"^\s*\[\[SHOT:\s*([A-Za-z0-9_-]+)\s*\]\]\s*$")
# A line holding only [[TODO: ...]] is a note to the student, such as a step only
# they can complete: a boxed to-do in the working copy, left out of the clean
# submission copy and its Markdown twin, and listed in the build summary.
TODO = re.compile(r"^\s*\[\[TODO:\s*(.+?)\s*\]\]\s*$")
FIGREF = re.compile(r"\[\[FIG:\s*([A-Za-z0-9_-]+)\s*\]\]")
FENCE = re.compile(r"^\s*```")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")

SHOT_BY_ID = {shot["sid"]: (sec, shot) for sec in SECTIONS for shot in sec["shots"]}


# ================================================================ planning
def norm(text):
    return re.sub(r"[^a-z0-9]", "", text.lower())


def strip_title(text, title):
    """
    Drop a leading heading that repeats the section title.

    The builder writes the title itself, so a file that opens with "# Title" or
    "## Title" (the Lab 2 habit) would otherwise print it twice. A level-1
    heading at the very top is always treated as the title; a level-2 one only
    when its text matches.
    """
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        if not ln.strip():
            continue
        m = HEADING.match(ln)
        if m:
            level, nh, nt = len(m.group(1)), norm(m.group(2)), norm(title)
            if level == 1 or (level == 2 and nh and (nt in nh or nh in nt)):
                return "\n".join(lines[:i] + lines[i + 1:]).strip("\n"), True
        break
    return text, False


def load_sections():
    texts, missing, stripped = {}, [], []
    for sec in SECTIONS:
        path = os.path.join(SECDIR, f"{sec['key']}.md")
        if not os.path.isfile(path):
            missing.append(sec["key"])
            continue
        with open(path, encoding="utf-8-sig") as fh:
            raw = fh.read().replace("\r\n", "\n").strip()
        if not raw:                     # an empty placeholder file is still pending
            missing.append(sec["key"])
            continue
        text, cut = strip_title(raw, sec["title"])
        if cut:
            stripped.append(sec["key"])
        texts[sec["key"]] = text
    return texts, missing, stripped


def split_items(text, key, warnings):
    """Split a section into Markdown chunks and [[SHOT:...]] markers, skipping fences."""
    items, buf, fenced = [], [], False
    for ln in text.split("\n"):
        if FENCE.match(ln):
            fenced = not fenced
        m = None if fenced else MARKER.match(ln)
        t = None if fenced else TODO.match(ln)
        if m or t:
            if "".join(buf).strip():
                items.append(("md", "\n".join(buf)))
            buf = []
            items.append(("marker", m.group(1)) if m else ("todo", t.group(1)))
            continue
        if not fenced and "[[SHOT:" in ln:
            warnings.append(f"{key}.md: a [[SHOT:...]] marker must sit on its own "
                            f"line; this one is left as text: {ln.strip()[:60]}")
        buf.append(ln)
    if "".join(buf).strip():
        items.append(("md", "\n".join(buf)))
    return items


def build_plan(texts):
    """
    Decide where every shot lands and number the figures in document order.

    Returns (plan, numbers, warnings): plan[key] is an ordered list of
    ("md", text) / ("shot", sid) / ("unknown", sid) / ("pending", key) items.
    """
    warnings = []
    split = {k: split_items(t, k, warnings) for k, t in texts.items()}

    # A marker anywhere claims its shot, so a shot pulled into a later section
    # is not also appended at the end of its own section.
    claimed = {v for items in split.values() for kind, v in items
               if kind == "marker" and v in SHOT_BY_ID}

    plan, placed = {}, set()
    for sec in SECTIONS:
        key, items = sec["key"], []
        if key not in texts:
            items.append(("pending", key))
        for kind, val in split.get(key, []):
            if kind in ("md", "todo"):
                items.append((kind, val))
            elif val not in SHOT_BY_ID:
                warnings.append(f"{key}.md: unknown marker [[SHOT:{val}]]")
                items.append(("unknown", val))
            elif val in placed:
                warnings.append(f"{key}.md: [[SHOT:{val}]] repeated - second one ignored")
            else:
                home = SHOT_BY_ID[val][0]["key"]
                if home != key:
                    warnings.append(f"{key}.md: shot {val} belongs to '{home}' but is "
                                    f"placed here, as marked")
                placed.add(val)
                items.append(("shot", val))
        for shot in sec["shots"]:
            if shot["sid"] not in claimed:
                placed.add(shot["sid"])
                items.append(("shot", shot["sid"]))
        plan[key] = items

    numbers = {}
    for sec in SECTIONS:
        for kind, val in plan[sec["key"]]:
            if kind == "shot":
                numbers[val] = len(numbers) + 1

    # [[FIG:S1b]] -> "Figure N", resolved once so warnings are not repeated.
    for key, items in plan.items():
        def sub(m, key=key):
            sid = m.group(1)
            if sid in numbers:
                return f"Figure {numbers[sid]}"
            warnings.append(f"{key}.md: [[FIG:{sid}]] matches no shot")
            return f"Figure [{sid}?]"
        plan[key] = [(k, FIGREF.sub(sub, v)) if k == "md" else (k, v)
                     for k, v in items]
    return plan, numbers, warnings


def word_count(text):
    """Prose words only: fenced code and marker lines do not count."""
    prose, fenced = [], False
    for ln in text.split("\n"):
        if FENCE.match(ln):
            fenced = not fenced
            continue
        if fenced or MARKER.match(ln) or TODO.match(ln):
            continue
        prose.append(re.sub(r"^#+\s*", "", ln))
    body = FIGREF.sub("Figure", "\n".join(prose))
    return len(re.findall(r"[A-Za-z0-9]+(?:['./-][A-Za-z0-9]+)*", body))


# ================================================================ images
_PREPARED = {}


def _save_scaled(img, width_in, name, src=None, palette=False):
    """
    Return a path to embed: the untouched original when it is already close to
    TARGET_DPI at the embedded width, otherwise a downscaled copy in the cache.

    I only resample past 1.5x the target density. Shaving 5-20 % off a figure's
    width with LANCZOS roughly doubled its PNG size (the filter invents new
    in-between colours) with no visible gain. Terminal slices are quantised to a
    256-colour palette without dithering: the text is a few hundred
    anti-aliasing shades of two colours, so nothing visible is lost and each
    slice shrinks by more than half.
    """
    max_px = int(round(width_in * TARGET_DPI))
    if img.width > 1.5 * max_px:
        h = max(1, int(round(img.height * max_px / img.width)))
        img = img.resize((max_px, h), Image.LANCZOS)
    elif src is not None:
        return src
    if palette:
        img = img.quantize(256, method=Image.Quantize.MEDIANCUT,
                           dither=Image.Dither.NONE)
    os.makedirs(CACHE, exist_ok=True)
    out = os.path.join(CACHE, name)
    img.save(out, optimize=True)
    return out


def _slice_rows(arr, first_px, next_px):
    """
    Row ranges that cut a tall terminal PNG between text lines.

    A row is a safe cut if every pixel equals the background colour (sampled at
    the top-left corner). Within each window I cut in the middle of the last
    blank run, so no glyph is ever split across two pictures.
    """
    height = arr.shape[0]
    blank = np.all(arr == arr[0, 0], axis=(1, 2))
    cuts, start, limit = [], 0, first_px
    while height - start > limit:
        lo, hi = start + limit // 2, start + limit
        idx = np.flatnonzero(blank[lo:hi])
        if idx.size:
            end = beg = int(idx[-1])
            while beg > 0 and blank[lo + beg - 1]:
                beg -= 1
            cut = lo + (beg + end) // 2 + 1
        else:
            cut = hi
        cuts.append((start, cut))
        start = cut
        # Share what is left evenly between the pages it needs, so the last
        # slice is not a four-line stub; 6 % slack absorbs where the blank rows
        # happen to fall.
        rest = height - start
        pages = -(-rest // next_px)
        limit = min(next_px, int(rest / pages * 1.06) + 1)
    cuts.append((start, height))
    return cuts


def prepare_image(shot, path):
    """
    Returns (list of image paths to embed in order, width in inches, note).

    Ordinary figures taller than MAX_FIG_H at their spec width are narrowed;
    terminal captures are sliced so their text stays at a readable size.
    """
    if path in _PREPARED:
        return _PREPARED[path]
    with Image.open(path) as im:
        im.load()
        img = im.convert("RGB")
    w_px, h_px = img.size
    width = float(shot["width"])
    stem = shot["target"].replace("/", "__").rsplit(".", 1)[0]
    note = ""

    if shot["target"].startswith("terminal/"):
        # render_logs.py draws 10 pt text at 170 DPI, so embedding at TERM_SCALE
        # of the native width puts every capture's text near 7.5 pt: wide logs
        # are not shrunk to 6 pt while short, narrow ones are not blown up past
        # the body text. The spec width is the ceiling.
        width = min(width, max(TERM_MIN_W, TERM_SCALE * w_px / TERM_DPI))
        px_per_in = w_px / width
        cuts = _slice_rows(np.asarray(img), int(FIRST_SLICE_H * px_per_in),
                           int(NEXT_SLICE_H * px_per_in))
        if len(cuts) > 1:
            note = f"split into {len(cuts)} page-sized slices"
            paths = [_save_scaled(img.crop((0, a, w_px, b)), width,
                                  f"{stem}_part{i + 1}.png", palette=True)
                     for i, (a, b) in enumerate(cuts)]
        else:
            paths = [_save_scaled(img, width, f"{stem}.png", src=path)]
    else:
        if h_px / w_px * width > MAX_FIG_H:
            new_w = MAX_FIG_H * w_px / h_px
            note = f"narrowed {width:.2f} -> {new_w:.2f} in to fit the page height"
            width = new_w
        paths = [_save_scaled(img, width, f"{stem}.png", src=path)]

    _PREPARED[path] = (paths, width, note)
    return _PREPARED[path]


# ================================================================ doc styling
def setup(doc):
    for s in doc.sections:
        s.left_margin = s.right_margin = Inches(1.0)
        s.top_margin = s.bottom_margin = Inches(1.0)

    # The stock template carries the library's name as author and a 2013
    # creation date; the file properties should describe this report instead.
    props = doc.core_properties
    props.author = props.last_modified_by = META["student"]
    props.title = META["title"]
    props.subject = META["course"]
    props.keywords = props.comments = props.category = ""
    # The file format stores these as UTC, so a local clock time would read as
    # several hours off when Word converts it back.
    now = datetime.datetime.now(datetime.timezone.utc)
    props.created = props.modified = now.replace(microsecond=0, tzinfo=None)
    props.revision = 1

    # docDefaults carries theme fonts in the stock template; make Calibri
    # explicit there too so every style that does not name a font agrees.
    defaults = doc.styles.element.find(qn("w:docDefaults"))
    rpr = defaults.find(qn("w:rPrDefault")).find(qn("w:rPr"))
    set_font(rpr, "Calibri")

    normal = doc.styles["Normal"]
    set_font(normal, "Calibri")
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.15

    for name, size, before in (("Heading 1", 16, 16), ("Heading 2", 13, 11),
                               ("Heading 3", 11.5, 9), ("Heading 4", 11, 8)):
        st = doc.styles[name]
        set_font(st, "Calibri")
        st.font.size = Pt(size)
        st.font.bold = True
        st.font.italic = False
        st.font.color.rgb = ACCENT
        st.paragraph_format.space_before = Pt(before)
        st.paragraph_format.space_after = Pt(5)
        st.paragraph_format.keep_with_next = True

    cap = doc.styles["Caption"]
    set_font(cap, "Calibri")
    cap.font.size = Pt(9.5)
    cap.font.bold = False
    cap.font.italic = True
    cap.font.color.rgb = MUTED
    cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(3)
    cap.paragraph_format.space_after = Pt(12)


def footer(doc):
    """Centered footer: student, assignment and a live PAGE field."""
    par = doc.sections[0].footer.paragraphs[0]
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = par.add_run(f"{META['student']}  |  {META['footer']}  |  Page ")
    r.font.size = Pt(8.5); r.font.color.rgb = MUTED
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE")
    num = par.add_run("1")
    num.font.size = Pt(8.5); num.font.color.rgb = MUTED
    par._p.remove(num._r)
    fld.append(num._r)
    par._p.append(fld)


def title_block(doc):
    p = doc.add_paragraph(); no_space(p, 0, 2)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(META["course"])
    r.bold = True; r.font.size = Pt(12); r.font.color.rgb = MUTED

    p = doc.add_paragraph(); no_space(p, 2, 3 if META.get("subtitle") else 10)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(META["title"])
    r.bold = True; r.font.size = Pt(20); r.font.color.rgb = ACCENT

    if META.get("subtitle"):
        p = doc.add_paragraph(); no_space(p, 0, 10)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(META["subtitle"])
        r.italic = True; r.font.size = Pt(12); r.font.color.rgb = MUTED

    rows = [("Course", META["course"]), ("Assignment", META["assignment"]),
            ("Student", META["student"]), ("Date", META["date"])]
    tbl = doc.add_table(rows=len(rows), cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tbl.autofit = False
    set_borders(tbl, color="1F3864", sz=6)
    # Word reads the per-cell widths, Google Docs the grid columns; set both.
    for col, width in zip(tbl.columns, (1.3, 3.9)):
        col.width = Inches(width)
    for i, (label, value) in enumerate(rows):
        for j, (text, width) in enumerate(((label, 1.3), (value, 3.9))):
            cell = tbl.cell(i, j)
            cell.width = Inches(width)
            cell.text = ""
            par = cell.paragraphs[0]; no_space(par, 1, 1)
            par.paragraph_format.line_spacing = 1.0
            r = par.add_run(text); r.font.size = Pt(10.5)
            if j == 0:
                r.bold = True; r.font.color.rgb = ACCENT
                shade(cell, "E9EEF6")
            cell_margins(cell, 60, 110, 60, 110)

    spacer = doc.add_paragraph(); no_space(spacer, 0, 6)


def _alert_par(doc, bold_text, rest, fill="FDF3F2", color="B03A2E"):
    """A visible, boxed paragraph for anything still missing at build time."""
    p = doc.add_paragraph()
    no_space(p, 4, 8)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    para_border(p, color=color, sz=8, style="dashed", fill=fill)
    r = p.add_run(bold_text); r.bold = True; r.font.color.rgb = ALERT
    if rest:
        r = p.add_run("  " + rest); r.italic = True
        r.font.size = Pt(9.5); r.font.color.rgb = MUTED
    return p


def todo_box(doc, text):
    """A boxed note for a step only the student can complete (working copy only)."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    shade(cell, "FDF3F2")
    set_borders(tbl, color="B03A2E", sz=10)
    cell_margins(cell, 110, 150, 110, 150)
    cap = OxmlElement("w:tblCaption")        # how tests tell it from a code block
    cap.set(qn("w:val"), "Student to-do")
    _put(tbl._tbl.tblPr, cap)
    cell.text = ""
    par = cell.paragraphs[0]
    no_space(par, 0, 0)
    par.paragraph_format.line_spacing = 1.05
    r = par.add_run("STUDENT TO-DO (instructions copy only)   ")
    r.bold = True; r.font.size = Pt(10); r.font.color.rgb = ALERT
    r = par.add_run(text)
    r.font.size = Pt(9.5)
    spacer = doc.add_paragraph(); no_space(spacer, 0, 0)
    spacer.paragraph_format.line_spacing = Pt(6)


# ================================================================ shots
def callout(doc, shot, number, have):
    """A bordered, shaded instruction box for one screenshot (working copy only)."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    shade(cell, "FFF8E5")
    set_borders(tbl, color="D9A400", sz=10)
    cell_margins(cell, 110, 150, 110, 150)
    cap = OxmlElement("w:tblCaption")        # alt text; also how tests find callouts
    cap.set(qn("w:val"), f"Screenshot callout {shot['sid']}")
    _put(tbl._tbl.tblPr, cap)
    cell.text = ""
    target = f"screenshots/{shot['target']}"

    def line(before=0, after=2, indent=0):
        par = cell.paragraphs[0] if not line.used else cell.add_paragraph()
        line.used = True
        no_space(par, before, after)
        par.paragraph_format.line_spacing = 1.05
        if indent:
            par.paragraph_format.left_indent = Pt(indent)
        return par
    line.used = False

    def run(par, text, size=9.5, bold=False, italic=False, mono=False, color=None):
        r = par.add_run(text)
        r.font.size = Pt(size); r.bold = bold; r.italic = italic
        if mono:
            set_font(r, MONO)
        if color is not None:
            r.font.color.rgb = color
        return r

    par = line(after=5)
    run(par, f"SCREENSHOT {shot['sid']}", 10.5, bold=True, color=AMBER)
    run(par, f"   Figure {number}   ", 10, color=AMBER)
    run(par, "save as  ", 10, bold=True, color=AMBER)
    run(par, target, 10, bold=True, mono=True, color=AMBER)

    par = line()
    run(par, "1.  Run this command", bold=True)
    run(par, "   from the module02_data_three_ways/ folder with .venv active", 9,
        italic=True, color=MUTED)
    run(line(after=5, indent=16), shot["command"], 9, mono=True)

    run(line(), "2.  Crop exactly this", bold=True)
    run(line(after=5, indent=16), shot["crop"])

    run(line(), "3.  Save to", bold=True)
    run(line(after=5, indent=16), target, 9, mono=True)

    if shot.get("note"):
        par = line(after=5, indent=16)
        run(par, "Note:  ", 9, bold=True, color=MUTED)
        run(par, shot["note"], 9, italic=True, color=MUTED)

    par = line(after=0)
    run(par, "4.  Place the image   ", bold=True)
    if have:
        msg = (f"Figure {number} below is the pre-rendered copy, read from that same "
               f"path. Save your own capture there and re-run python "
               f"scripts/make_report.py to embed it instead.")
    else:
        msg = (f"Nothing was at that path when this report was built. Save the "
               f"capture there and re-run python scripts/make_report.py to embed it "
               f"as Figure {number}.")
    run(par, msg, italic=True)

    keep_table_with_next(tbl)
    spacer = doc.add_paragraph(); no_space(spacer, 0, 0)
    spacer.paragraph_format.line_spacing = Pt(6)
    spacer.paragraph_format.keep_with_next = True


def embed(doc, shot, path, number):
    paths, width, note = prepare_image(shot, path)
    for i, img in enumerate(paths):
        par = doc.add_paragraph()
        par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        no_space(par, 2 if i == 0 else 0, 0)
        # Multiple line spacing scales an inline picture's line too, which
        # would add 15 % of the image height as dead space; pin it to single.
        par.paragraph_format.line_spacing = 1.0
        if i == len(paths) - 1:
            par.paragraph_format.keep_with_next = True       # stay with caption
        inline = par.add_run().add_picture(img, width=Inches(width))
        inline._inline.docPr.set("descr", f"Figure {number} - {shot['caption']}")
    return note


def caption(doc, shot, number):
    par = doc.add_paragraph(style="Caption")
    par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = par.add_run(f"Figure {number}"); r.bold = True
    par.add_run(f" - {shot['caption']}")


def place_shot(doc, sid, number, with_callouts, stats):
    _, shot = SHOT_BY_ID[sid]
    path = os.path.join(ROOT, figure_path(shot).replace("/", os.sep))
    have = os.path.isfile(path)
    if with_callouts:
        callout(doc, shot, number, have)
    reason = "not found when this report was built"
    if have:
        try:
            note = embed(doc, shot, path, number)
            stats["embedded"].add(sid)
            if note:
                stats["adjusted"][sid] = note
            caption(doc, shot, number)
            return
        except Exception as exc:          # half-written PNG from a parallel run
            reason = f"could not be read ({type(exc).__name__})"
            stats["unreadable"][sid] = f"{type(exc).__name__}: {exc}"
    stats["missing"].add(sid)
    _alert_par(doc, f"[ FIGURE PENDING - screenshots/{shot['target']} ]",
               f"{reason}. Run {shot['command']}, then python scripts/make_report.py.")
    caption(doc, shot, number)


def code_reference(doc, sec):
    files = sec.get("code") or []
    if not files:
        return
    par = doc.add_paragraph()
    par.paragraph_format.space_before = Pt(2)
    par.paragraph_format.space_after = Pt(12)
    r = par.add_run("Code for this section: " if APPENDIX_FILES
                    else "Source files for this section: ")
    r.bold = True; r.font.size = Pt(9.5); r.font.color.rgb = ACCENT
    if APPENDIX_FILES:
        r = par.add_run("Appendix A, ")
        r.font.size = Pt(9.5); r.font.color.rgb = MUTED
    for i, f in enumerate(files):
        r = par.add_run(f)
        set_font(r, MONO); r.font.size = Pt(9); r.font.color.rgb = MUTED
        if i < len(files) - 1:
            r = par.add_run(" and ")
            r.font.size = Pt(9.5); r.font.color.rgb = MUTED


# ================================================================ appendices
def read_source(fname):
    """fname is project-relative, for example scripts/x.py or web/x.js."""
    path = os.path.join(ROOT, fname.replace("/", os.sep))
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        return fh.read().replace("\r\n", "\n").rstrip("\n")


def appendix_docx(doc, stats):
    if not APPENDIX_FILES:
        return
    doc.add_page_break()
    doc.add_heading("Appendix A - Source Code", level=1)
    add_inline(doc.add_paragraph(), META["appendix_intro"])

    for fname, blurb in APPENDIX_FILES:
        doc.add_heading(fname, level=2)
        code = read_source(fname)
        p = doc.add_paragraph(); no_space(p, 0, 4)
        extra = f"  ({code.count(chr(10)) + 1} lines)" if code is not None else ""
        r = p.add_run(blurb + extra); r.italic = True
        r.font.size = Pt(9.5); r.font.color.rgb = MUTED
        if code is None:
            stats["appendix_missing"].append(fname)
            _alert_par(doc, f"[ Source pending: {fname} ]",
                       "the file was not found when this report was built.")
            continue
        # 7.5 pt Consolas with 4.5 pt side padding fits 111 characters in the
        # 6.5 in text block, so no source line (at most 100) wraps and breaks
        # its indentation; the terminal captures are sized to ~7.5 pt text too.
        tbl = code_table(doc, code, size=7.5, fill="F7F8FA")
        cell_margins(tbl.cell(0, 0), 90, 90, 90, 90)
        no_space(doc.add_paragraph(), 0, 6)


# ================================================================ build: docx
def build_doc(plan, with_callouts, stats):
    doc = Document()
    setup(doc)
    footer(doc)
    title_block(doc)
    for sec in SECTIONS:
        # Each case study opens on a fresh page so its original image, the
        # citation and the first heading stay together.
        if sec.get("page_break"):
            doc.add_page_break()
        doc.add_heading(sec["title"], level=1)
        for kind, val in plan[sec["key"]]:
            if kind == "md":
                # Formula and console blocks in the text are at most 96
                # characters wide; 8.5 pt Consolas fits 97 in the 6.5 in column.
                before = len(doc.paragraphs)
                render_markdown(doc, val, h_offset=0, min_level=2, code_size=8.5)
                if sec.get("hanging"):
                    # APA reference list: first line flush, the rest indented.
                    for par in doc.paragraphs[before:]:
                        if par.style.name == "Normal":
                            par.paragraph_format.left_indent = Inches(0.5)
                            par.paragraph_format.first_line_indent = Inches(-0.5)
            elif kind == "shot":
                place_shot(doc, val, stats["numbers"][val], with_callouts, stats)
            elif kind == "todo":
                if with_callouts:
                    todo_box(doc, val)
            elif kind == "unknown":
                _alert_par(doc, f"[Unknown screenshot marker: {val}]",
                           "no shot with this id exists in scripts/report_spec.py.")
            elif kind == "pending":
                _alert_par(doc, f"[Section pending: {val}]",
                           f"report/sections/{val}.md was not found when this "
                           f"report was built.")
        code_reference(doc, sec)
    appendix_docx(doc, stats)
    return doc


# ================================================================ build: markdown
def shift_headings(md):
    """Section files use ## and deeper; in the .md twin the section title is ##."""
    out, fenced = [], False
    for ln in md.split("\n"):
        if FENCE.match(ln):
            fenced = not fenced
        m = None if fenced else HEADING.match(ln)
        if m:
            level = min(6, max(2, len(m.group(1))) + 1)
            ln = "#" * level + " " + m.group(2)
        out.append(ln)
    return "\n".join(out)


def fence_for(code):
    longest = max((len(m) for m in re.findall(r"`+", code)), default=0)
    return "`" * max(3, longest + 1)


def md_shot(sid, number):
    """Image and caption only: the Markdown twin follows the submission copy."""
    _, shot = SHOT_BY_ID[sid]
    rel = figure_path(shot)
    have = os.path.isfile(os.path.join(ROOT, rel.replace("/", os.sep)))
    out = []
    if have:
        out += [f"![Figure {number}](../{rel})", ""]
    else:
        out += [f"**[ FIGURE PENDING - `screenshots/{shot['target']}` ]** - not found "
                f"when this report was built.", ""]
    out += [f"*Figure {number} - {shot['caption']}*", ""]
    return out


def build_markdown(plan, numbers):
    out = [f"# {META['title']}", ""]
    if META.get("subtitle"):
        out += [f"*{META['subtitle']}*", ""]
    out += [f"**Course:** {META['course']}  ",
            f"**Assignment:** {META['assignment']}  ",
            f"**Student:** {META['student']}  ",
            f"**Date:** {META['date']}", "", "---", ""]
    for sec in SECTIONS:
        out += [f"## {sec['title']}", ""]
        for kind, val in plan[sec["key"]]:
            if kind == "md":
                out += [shift_headings(val).strip("\n"), ""]
            elif kind == "shot":
                out += md_shot(val, numbers[val])
            elif kind == "unknown":
                out += [f"**[Unknown screenshot marker: {val}]**", ""]
            elif kind == "pending":
                out += [f"**[Section pending: {val}]** - `report/sections/{val}.md` "
                        f"was not found when this report was built.", ""]
        files = sec.get("code") or []
        if files:
            refs = " and ".join(f"`{f}`" for f in files)
            lead = ("**Code for this section:** Appendix A, " if APPENDIX_FILES
                    else "**Source files for this section:** ")
            out += [lead + refs, ""]

    if APPENDIX_FILES:
        out += ["---", "", "## Appendix A - Source Code", "", META["appendix_intro"], ""]
    for fname, blurb in APPENDIX_FILES:
        code = read_source(fname)
        out += [f"### {fname}", "", f"*{blurb}*", ""]
        if code is None:
            out += [f"**[ Source pending: {fname} ]** - the file was not "
                    f"found when this report was built.", ""]
            continue
        fence = fence_for(code)
        language = "javascript" if fname.endswith(".js") else "python"
        out += [fence + language, code, fence, ""]
    return "\n".join(out)


# ================================================================ screenshot guide
def build_guide(plan, numbers):
    lines = [
        "# Screenshot Instructions - Module Two",
        "",
        "Generated by `scripts/make_report.py` from `scripts/report_spec.py`; edit "
        "the spec, not this file, so the filenames here and in the report can "
        "never disagree.",
        "",
        "Every figure the report uses is listed below in document order. A "
        "pre-rendered PNG is embedded in `report/module02_report.docx` and "
        "`report/module02_report_clean.docx` for each one that existed at build "
        "time, read from the exact target path shown. To use your own capture, "
        "save it at that path and re-run `python scripts/make_report.py`. Note "
        "that `python scripts/run_all.py` rewrites every PNG it produces, so run "
        "it before swapping in manual captures, not after.",
        "",
        "Regenerate everything first (from the `module02_data_three_ways/` folder):",
        "",
        "```powershell",
        r".\.venv\Scripts\Activate.ps1",
        "python scripts/run_all.py",
        "```",
        "",
        "The run needs no network: every script reads the raw downloads already "
        "saved in `inputs/` (their source URLs and SHA-256 hashes are in "
        "`inputs/SOURCES.md`). It does need Microsoft Edge, which the browser "
        "captures drive headlessly through Playwright.",
        "",
        "| Figure | Shot | Target in `screenshots/` | Pre-rendered copy |",
        "|---|---|---|---|",
    ]
    order = [(sec, sid) for sec in SECTIONS
             for kind, sid in plan[sec["key"]] if kind == "shot"]
    for _, sid in order:
        shot = SHOT_BY_ID[sid][1]
        have = os.path.isfile(os.path.join(ROOT, figure_path(shot).replace("/", os.sep)))
        lines.append(f"| {numbers[sid]} | {sid} | `{shot['target']}` | "
                     f"{'present' if have else '**missing**'} |")
    lines += ["", "---", ""]

    current = None
    for sec, sid in order:
        if sec["key"] != current:
            current = sec["key"]
            lines += [f"## {sec['title']}", ""]
        shot = SHOT_BY_ID[sid][1]
        have = os.path.isfile(os.path.join(ROOT, figure_path(shot).replace("/", os.sep)))
        lines += [
            f"### {sid} - Figure {numbers[sid]} - `{shot['target']}`",
            "",
            f"1. **Run:** `{shot['command']}`",
            f"2. **Crop:** {shot['crop']}",
            f"3. **Save as:** `screenshots/{shot['target']}`",
            "",
            f"- **Caption:** Figure {numbers[sid]} - {shot['caption']}",
        ]
        if shot.get("note"):
            lines.append(f"- **Note:** {shot['note']}")
        status = ("pre-rendered copy present and embedded" if have else
                  "MISSING - the report shows a placeholder")
        lines += [f"- **Status at build time:** {status}", ""]
    lines += ["---", "", f"**Total screenshots: {len(order)}**", ""]
    return "\n".join(lines)


# ================================================================ main
def _write_docx(doc, path, label):
    try:
        doc.save(path)
    except PermissionError:
        print(f"  ! could not write {os.path.relpath(path, ROOT)} - is it open in Word?")
        return False
    print(f"  wrote {os.path.relpath(path, ROOT):38s} {os.path.getsize(path) / 1024:7.0f} KB"
          f"   {label}")
    return True


def _write_text(text, path, label):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print(f"  wrote {os.path.relpath(path, ROOT):38s} {os.path.getsize(path) / 1024:7.0f} KB"
          f"   {label}")


def main():
    print("BUILDING MODULE TWO REPORT")
    print("=" * 72)
    os.makedirs(REPORT, exist_ok=True)
    shutil.rmtree(CACHE, ignore_errors=True)

    texts, missing_secs, stripped = load_sections()
    plan, numbers, warnings = build_plan(texts)
    stats = {"numbers": numbers, "embedded": set(), "missing": set(),
             "unreadable": {}, "adjusted": {}, "appendix_missing": []}

    print("\nOUTPUTS")
    ok = _write_docx(build_doc(plan, True, stats), OUT_FULL,
                     f"working copy, {len(numbers)} callouts")
    # The second build re-uses the prepared images; its stats would only repeat
    # the first build's, so it gets a scratch copy.
    scratch = {**stats, "embedded": set(), "missing": set(), "unreadable": {},
               "adjusted": {}, "appendix_missing": []}
    ok &= _write_docx(build_doc(plan, False, scratch), OUT_CLEAN,
                      "clean submission copy, no callouts")
    _write_text(build_markdown(plan, numbers), OUT_MD, "Markdown twin of the clean copy")
    _write_text(build_guide(plan, numbers), OUT_GUIDE, f"{len(numbers)} screenshots")

    print("\nSECTIONS")
    print(f"  {'key':15s} {'status':9s} {'words':>6s}  {'shots (marker / appended)':s}")
    print("  " + "-" * 60)
    total = 0
    for sec in SECTIONS:
        key = sec["key"]
        words = word_count(texts[key]) if key in texts else 0
        total += words
        raw = split_items(texts.get(key, ""), key, [])
        placed = [v for k, v in plan[key] if k == "shot"]
        marked = len({v for k, v in raw if k == "marker"} & set(placed))
        shots = len(placed)
        status = "ok" if key in texts else "PENDING"
        print(f"  {key:15s} {status:9s} {words:6d}  {shots} ({marked} / {shots - marked})"
              + ("   [leading title line dropped]" if key in stripped else ""))
    print("  " + "-" * 60)
    print(f"  {'total':15s} {'':9s} {total:6d}")

    print("\nFIGURES")
    print(f"  planned {len(numbers)}, embedded {len(stats['embedded'])}, "
          f"placeholder {len(stats['missing'])}")
    for sid in sorted(stats["missing"], key=lambda s: numbers[s]):
        shot = SHOT_BY_ID[sid][1]
        why = stats["unreadable"].get(sid, "missing")
        print(f"  - Figure {numbers[sid]:2d}  {sid:4s} screenshots/{shot['target']}  ({why})")
    for sid, note in sorted(stats["adjusted"].items(), key=lambda kv: numbers[kv[0]]):
        print(f"  * Figure {numbers[sid]:2d}  {sid:4s} {note}")

    print("\nAPPENDIX A")
    have = len(APPENDIX_FILES) - len(stats["appendix_missing"])
    print(f"  {have} of {len(APPENDIX_FILES)} source files included"
          if APPENDIX_FILES else "  not built: report_spec.APPENDIX_FILES is empty")
    for f in stats["appendix_missing"]:
        print(f"  - pending: {f}")

    todos = [(sec["key"], v) for sec in SECTIONS for k, v in plan[sec["key"]] if k == "todo"]
    if todos:
        print("\nSTUDENT TO-DO  (boxed in the working copy, left out of the clean copy and the .md)")
        for key, text in todos:
            print(f"  - {key}: {text[:90]}{'...' if len(text) > 90 else ''}")

    if missing_secs or warnings:
        print("\nWARNINGS")
        for key in missing_secs:
            print(f"  ! missing section: report/sections/{key}.md")
        for w in warnings:
            print(f"  ! {w}")
    print("\nDone." if ok else "\nDone, but at least one .docx could not be written.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
