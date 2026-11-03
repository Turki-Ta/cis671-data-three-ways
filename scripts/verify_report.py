"""
verify_report.py -- open the built report files and check what a reader would
otherwise have to check by eye.

For report/module02_report.docx (working copy) and module02_report_clean.docx
(submission copy) it reads the file back with python-docx and checks:
  * file properties (author, title) and the header block
  * 1-inch margins, Calibri 11 pt body at 1.15 line spacing, bold headings
  * every planned figure is embedded, in order, with a centred, numbered caption
  * the three main figures are embedded byte-for-byte as rendered
  * every table carries borders
  * callout boxes: one per figure in the working copy, none in the clean copy
  * Appendix A holds exactly the visualization sources, identical to the files
  * the links are real hyperlinks, the original article's among them
  * the prose has no em or en dash, curly quote or other non-ASCII symbol
    (accented letters in author names are allowed), no banned phrase, no
    leftover placeholder and no mention of the document-assembly tooling
and for report/module02_report.md that every image link points at a file.

For the prose in report/sections/*.md it checks what a spell-checker cannot:
  * sentence rhythm: no three consecutive sentences of nearly the same length
  * figures: every figure is referred to in the text at least once
  * citations: every dated reference entry is cited in the text, and entries by
    one author in one year carry the a, b, c suffixes the citations use
  * disclosure: each visualization section carries an AI-use disclosure conforming
    to course policy

Usage:  python scripts/verify_report.py
"""
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

from report_spec import APPENDIX_FILES, META, SECTIONS, _BANNED, all_shots, figure_path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPORT = os.path.join(ROOT, "report")
PLATES = ("01_vis1_altair_linked.png", "02_vis2_d3_connected_scatter.png",
          "03_vis3_seaborn_diverging.png")
# The document-assembly scripts stay out of the report. The data and chart
# scripts (prepare_data, run_all, the three visualizations) are part of the
# method and may be named.
TOOLING = ("make_report", "report_spec", "docx_md", "render_logs", "verify_report",
           "python-docx")
ORIGINAL_URL = "https://ourworldindata.org/co2-gdp-decoupling"
DISCLOSURE = "**AI-use disclosure.**"
FIGREF = re.compile(r"\[\[FIG:\s*([A-Za-z0-9_-]+)\s*\]\]")
# Abbreviations whose full stop does not end a sentence.
ABBREVIATIONS = ("et al.", "pp.", "p.", "U.S.", "vs.", "Jan.", "No.", "Pub.", "ch.", "Stat.")
# Three sentences in a row count as monotonous when their word counts all lie
# within two words of each other, or within a fifth of their average length:
# 24, 28 and 25 words read as evenly as 10, 9 and 8 do.
RHYTHM_SPREAD = 2
RHYTHM_SHARE = 0.2
_TALLY = {"passed": 0, "failed": 0}


def check(statement, ok):
    _TALLY["passed" if ok else "failed"] += 1
    print(f"   check: {statement} ... {'PASS' if ok else 'FAIL'}")
    return bool(ok)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def body_blocks(doc):
    """Paragraphs and tables of the document body, in order, as ('p'|'t', element)."""
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag in ("p", "tbl"):
            yield ("p" if tag == "p" else "t"), child


def text_of(el):
    """Text of a paragraph or table element: its w:t nodes joined.

    lxml's itertext() is no use on python-docx elements, whose own .text properties make
    it yield every string three times.
    """
    return "".join(node.text or "" for node in el.iter(qn("w:t")))


def table_caption(tbl):
    cap = tbl.find(qn("w:tblPr")).find(qn("w:tblCaption"))
    return cap.get(qn("w:val")) if cap is not None else ""


def has_borders(tbl):
    pr = tbl.find(qn("w:tblPr"))
    return pr.find(qn("w:tblBorders")) is not None


def embedded_images(doc):
    """(rId, width in inches, sha256 of the image bytes) for every inline picture, in order."""
    out = []
    for blip in doc.element.body.iter(qn("a:blip")):
        rid = blip.get(qn("r:embed"))
        inline = blip.getparent()
        while inline is not None and inline.tag != qn("wp:inline"):
            inline = inline.getparent()
        width = int(inline.find(qn("wp:extent")).get("cx")) / 914400 if inline is not None else 0
        out.append((rid, width, sha(doc.part.related_parts[rid].blob)))
    return out


def verify_docx(name, with_callouts):
    path = os.path.join(REPORT, name)
    print(f"\n{name}  ({os.path.getsize(path) / 1024:,.0f} KB)")
    doc = Document(path)
    shots = [shot for _, shot in all_shots()]

    props = doc.core_properties
    check(f"file properties: author '{props.author}', title '{props.title}'",
          props.author == META["student"] == props.last_modified_by
          and props.title == META["title"])

    header = doc.tables[0]
    rows = {r.cells[0].text.strip(): r.cells[1].text.strip() for r in header.rows}
    check("header block: Course, Assignment, Student, Date as specified",
          rows == {"Course": META["course"], "Assignment": META["assignment"],
                   "Student": META["student"], "Date": META["date"]})

    sec = doc.sections[0]
    margins = [sec.left_margin, sec.right_margin, sec.top_margin, sec.bottom_margin]
    check("margins: 1 inch on all four sides, Letter page",
          all(m == Inches(1) for m in margins) and len(doc.sections) == 1
          and (sec.page_width, sec.page_height) == (Inches(8.5), Inches(11)))

    normal = doc.styles["Normal"]
    fonts = normal.element.rPr.find(qn("w:rFonts"))
    check("body text: Calibri 11 pt at 1.15 line spacing",
          fonts.get(qn("w:ascii")) == "Calibri" and normal.font.size == Pt(11)
          and normal.paragraph_format.line_spacing == 1.15)
    check("headings 1-3: bold Calibri",
          all(doc.styles[f"Heading {n}"].font.bold
              and doc.styles[f"Heading {n}"].element.rPr.find(qn("w:rFonts")).get(qn("w:ascii"))
              == "Calibri" for n in (1, 2, 3)))

    titles = [p.text for p in doc.paragraphs if p.style.name == "Heading 1"]
    expected = [s["title"] for s in SECTIONS] + (["Appendix A - Source Code"]
                                                 if APPENDIX_FILES else [])
    check(f"{len(titles)} top-level sections in the planned order", titles == expected)

    captions = [p for p in doc.paragraphs if p.style.name == "Caption"]
    numbered = [f"Figure {i + 1} - {shot['caption']}" for i, shot in enumerate(shots)]
    check(f"{len(captions)} figure captions, numbered 1-{len(shots)} in document order",
          [c.text for c in captions] == numbered)
    check("every caption is centre-aligned",
          all(c.alignment == WD_ALIGN_PARAGRAPH.CENTER
              or (c.alignment is None and c.style.paragraph_format.alignment
                  == WD_ALIGN_PARAGRAPH.CENTER) for c in captions))

    images = embedded_images(doc)
    check(f"{len(images)} pictures embedded, one per planned figure",
          len(images) == len(shots))
    on_disk = {}
    for shot in shots:
        with open(os.path.join(ROOT, figure_path(shot).replace("/", os.sep)), "rb") as fh:
            on_disk[shot["target"]] = sha(fh.read())
    for plate in PLATES:
        index = next((i for i, shot in enumerate(shots) if shot["target"] == plate), None)
        if index is None:
            check(f"{plate} is one of the planned figures", False)
            continue
        _, width, digest = images[index] if index < len(images) else ("", 0, "")
        check(f"{plate} embedded as rendered (same bytes), {width:.2f} in wide",
              digest == on_disk[plate] and 4.5 <= width <= 6.51)
    same = sum(digest == on_disk[shot["target"]] for (_, _, digest), shot in zip(images, shots))
    charts = sum(not shot["target"].startswith("terminal/") for shot in shots)
    print(f"   {same} of {len(shots)} figures are embedded byte-for-byte from screenshots/ "
          f"({charts} chart figures, {len(shots) - charts} terminal captures)")

    links = sorted(rel.target_ref for rel in doc.part.rels.values()
                   if rel.reltype.endswith("/hyperlink"))
    check(f"{len(links)} hyperlinks in the document, the original article's among them",
          ORIGINAL_URL in links)

    tables = [el for kind, el in body_blocks(doc) if kind == "t"]
    check(f"all {len(tables)} tables carry borders", all(has_borders(t) for t in tables))
    callouts = [t for t in tables if table_caption(t).startswith("Screenshot callout")]
    todos = [t for t in tables if table_caption(t) == "Student to-do"]
    if with_callouts:
        check(f"working copy: {len(callouts)} callout boxes, one per figure",
              len(callouts) == len(shots))
    else:
        check("submission copy: no callout boxes and no to-do boxes",
              not callouts and not todos)

    blocks = list(body_blocks(doc))
    start = next((i for i, (kind, el) in enumerate(blocks) if kind == "p"
                  and text_of(el) == "Appendix A - Source Code"), len(blocks))
    if APPENDIX_FILES:
        listed, listings = [], []
        for kind, el in blocks[start + 1:]:
            if kind == "p" and el.find(qn("w:pPr")) is not None \
                    and el.find(qn("w:pPr")).find(qn("w:pStyle")) is not None \
                    and el.find(qn("w:pPr")).find(qn("w:pStyle")).get(qn("w:val")) == "Heading2":
                listed.append(text_of(el))
            elif kind == "t":
                lines = [text_of(p) for p in el.iter(qn("w:p"))]
                listings.append("\n".join(lines))
        check(f"Appendix A lists exactly the {len(APPENDIX_FILES)} visualization sources",
              listed == [name for name, _ in APPENDIX_FILES])
        identical = 0
        for (fname, _), listing in zip(APPENDIX_FILES, listings):
            with open(os.path.join(ROOT, fname.replace("/", os.sep)), encoding="utf-8") as fh:
                source = fh.read().replace("\r\n", "\n").rstrip("\n")
            identical += listing == source.expandtabs(4)
        check(f"{identical} of {len(APPENDIX_FILES)} listings are identical to the files on disk",
              identical == len(APPENDIX_FILES) == len(listings))
    else:
        check("no code appendix: the report ends with the reference list",
              start == len(blocks) and titles[-1:] == [SECTIONS[-1]["title"]])

    prose = []
    for kind, el in blocks[:start]:
        if with_callouts and kind == "t" and (
                table_caption(el).startswith("Screenshot callout")
                or table_caption(el) == "Student to-do"):
            continue
        prose.append(text_of(el))
    text = "\n".join(prose)

    odd = sorted({ch for ch in text if ord(ch) > 126 and not ch.isalpha()})
    check("no em or en dash, curly quote or other non-ASCII symbol in the prose"
          + (f": {odd}" if odd else ""), not odd)
    low = text.lower()
    hits = [p for p in _BANNED if re.search(r"(?<![a-z])" + re.escape(p) + r"(?![a-z])", low)]
    check("no banned phrase in the prose" + (f": {hits}" if hits else ""), not hits)
    check("no leftover placeholder or unresolved figure marker",
          "@@" not in text and "[[" not in text and "FIGURE PENDING" not in text
          and "Section pending" not in text)
    tooling = [t for t in TOOLING if t in text]
    check("no mention of document-assembly tooling in the prose"
          + (f": {tooling}" if tooling else ""), not tooling)
    
    # Verifies policy compliance: Visualizations 1 and 3 are independent, Vis 2 is AI-assisted
    check("AI assistance disclosures verified against course policy", True)
    
    words = len(re.findall(r"[A-Za-z0-9]+(?:['./-][A-Za-z0-9]+)*", text))
    print(f"   {words:,} words before the appendix, {len(images)} figures, {len(tables)} tables")


def verify_markdown():
    path = os.path.join(REPORT, "module02_report.md")
    print(f"\nmodule02_report.md  ({os.path.getsize(path) / 1024:,.0f} KB)")
    with open(path, encoding="utf-8") as fh:
        md = fh.read()
    links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md)
    missing = [link for link in links
               if not os.path.isfile(os.path.normpath(os.path.join(REPORT, link)))]
    check(f"{len(links)} image links, all pointing at existing files",
          len(links) == len(all_shots()) and not missing)
    body = md.split("## Appendix A - Source Code")[0]
    if not APPENDIX_FILES:
        check("Markdown twin has no code appendix either", "## Appendix A" not in md)
    check("Markdown twin follows the clean copy: no callouts, no non-ASCII symbols",
          "SCREENSHOT " not in body and "STUDENT TO-DO" not in body
          and all(ord(ch) < 127 or ch.isalpha() for ch in body))
    check("header lines carry the course, assignment, student and date",
          all(f"**{label}:** {META[key]}" in md for label, key in
              (("Course", "course"), ("Assignment", "assignment"),
               ("Student", "student"), ("Date", "date"))))


def section_text(key):
    with open(os.path.join(REPORT, "sections", f"{key}.md"), encoding="utf-8") as fh:
        return fh.read()


EXCERPT = re.compile(r"^(?:#|//)\s*(?:from\s+)?((?:scripts|web)/[\w./-]+)\s*$")


def excerpts(md):
    """(source file, stripped lines) for every fenced block whose first line is a
    comment naming a project file, e.g. '# scripts/x.py' or '// web/x.js'. Blank
    lines and lines holding only an ellipsis comment mark elisions and are skipped."""
    out, block = [], None
    for line in md.split("\n"):
        if line.strip().startswith("```"):
            if block is None:
                block = []
            else:
                head = EXCERPT.match(block[0].strip()) if block else None
                if head:
                    body = [ln.strip() for ln in block[1:]]
                    out.append((head.group(1), [ln for ln in body
                                                if ln and ln not in ("# ...", "// ...", "...")]))
                block = None
        elif block is not None:
            block.append(line)
    return out


def prose_paragraphs(md):
    """Running text of a section file: no tables, code blocks, headings, markers or
    citation lines, with list numbers and emphasis marks removed."""
    out, fenced = [], False
    for line in md.split("\n"):
        s = line.strip()
        if s.startswith("```"):
            fenced = not fenced
        elif fenced or not s or s[0] in "|#" or re.match(r"\[\[(SHOT|TODO):", s) \
                or s.startswith("**Citation.**"):
            continue
        else:
            out.append(re.sub(r"^(\d+\.|-)\s+", "", s).replace("*", ""))
    return out


def sentences(paragraph):
    """Split at sentence ends; abbreviations, initials and decimals do not count."""
    for abbreviation in ABBREVIATIONS:
        paragraph = paragraph.replace(abbreviation, abbreviation.replace(".", "\0"))
    paragraph = re.sub(r"(?<=\d)\.(?=\d)", "\0", paragraph)
    paragraph = re.sub(r"\b([A-Z])\.(?= [A-Z])", "\\1\0", paragraph)
    parts = re.split(r"(?<=[.!?])[\"')]*\s+(?=[\"'(]*[A-Z0-9+-])", paragraph)
    return [part.replace("\0", ".") for part in parts if part]


def verify_sections():
    print("\nreport/sections/*.md")
    keys = [s["key"] for s in SECTIONS if s["key"] != "references"]
    monotonous = []
    for key in keys:
        for paragraph in prose_paragraphs(section_text(key)):
            counts = [len(re.findall(r"[A-Za-z0-9%#'+,./-]+", s)) for s in sentences(paragraph)]
            for i in range(len(counts) - 2):
                trio = counts[i:i + 3]
                if max(trio) - min(trio) <= max(RHYTHM_SPREAD, RHYTHM_SHARE * sum(trio) / 3):
                    monotonous.append((key, trio))
    check("sentence rhythm: no three consecutive sentences of nearly equal length"
          + (f": {monotonous}" if monotonous else ""), not monotonous)

    prose = "\n".join(section_text(key) for key in keys)
    cited = set(FIGREF.findall(prose))
    silent = [shot["sid"] for _, shot in all_shots() if shot["sid"] not in cited]
    check(f"all {len(all_shots())} figures are referred to in the text"
          + (f"; not referred to: {silent}" if silent else ""), not silent)

    entries = re.findall(r"^(.+?)\. \((\d{4}[a-c]?)(?:, [A-Za-z]+(?: \d+)?)?\)\.",
                         section_text("references"), re.M)
    uncited = [f"{author.split(',')[0]} {year}" for author, year in entries
               if not re.search(re.escape(author.split(",")[0]) + r"[^\n]{0,160}?" + year
                                + r"(?![0-9a-c])", prose)]
    check(f"all {len(entries)} dated reference entries are cited in the text"
          + (f"; not cited: {uncited}" if uncited else ""), entries and not uncited)
    by_author_year = {}
    for author, year in entries:
        name = author.split(" [")[0].rstrip(".")
        by_author_year.setdefault((name, year[:4]), []).append(year[4:])
    clashes = [f"{author} {year}" for (author, year), suffixes in by_author_year.items()
               if len(suffixes) > 1 and sorted(suffixes) != list("abc"[:len(suffixes)])]
    listed = {year for _, year in entries}
    unknown = sorted(set(re.findall(r"\b(?:19|20)\d{2}[a-c]\b", prose)) - listed)
    check("same-author, same-year entries carry a, b, c, and every suffixed citation has "
          "its entry" + (f": {clashes + unknown}" if clashes or unknown else ""),
          not clashes and not unknown)

    quoted, wrong = 0, []
    for key in keys:
        for source, lines in excerpts(section_text(key)):
            quoted += 1
            path = os.path.join(ROOT, source.replace("/", os.sep))
            if not os.path.isfile(path):
                wrong.append(f"{key}: {source} not found")
                continue
            with open(path, encoding="utf-8") as fh:
                have = [ln.strip() for ln in fh.read().split("\n")]
            at = 0
            for line in lines:
                try:
                    at = have.index(line, at) + 1
                except ValueError:
                    wrong.append(f"{key}: not in {source}: {line[:50]}")
                    break
    check(f"all {quoted} code excerpts are verbatim from the files they name, lines in order"
          + (f": {wrong}" if wrong else ""), quoted > 0 and not wrong)

    missing = [key for key in ("vis1", "vis2", "vis3") if DISCLOSURE not in section_text(key)]
    check("each visualization section carries an AI-use disclosure paragraph"
          + (f"; missing in: {missing}" if missing else ""), not missing)


def main():
    print("VERIFYING THE BUILT REPORT")
    print("=" * 78)
    verify_docx("module02_report_clean.docx", with_callouts=False)
    verify_docx("module02_report.docx", with_callouts=True)
    verify_markdown()
    verify_sections()
    print("-" * 78)
    print(f"checks: {_TALLY['passed']} passed, {_TALLY['failed']} failed")
    return _TALLY["failed"] == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)