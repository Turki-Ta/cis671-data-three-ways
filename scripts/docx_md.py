"""
docx_md.py -- the small Markdown subset renderer used to build the Word report.

Handles headings, paragraphs, bullet and numbered lists, fenced code blocks,
pipe tables, block quotes, inline **bold** / *italic* / `code`, and links. That
covers everything the report sections actually use; anything fancier is
deliberately out of scope.

Carried over from the Module One copy with one addition: a Markdown link
[text](https://...) and a bare https://... URL both become real Word
hyperlinks (a relationship in the document part, not blue underlined text), so
they stay clickable after the file is imported into Google Docs. The
behaviour worth knowing about:
  * set_font() writes an explicit font AND strips the theme-font attributes.
    The default python-docx template puts w:asciiTheme on docDefaults and on
    every heading style, and Word lets the theme attribute win over w:ascii on
    the same element, so without this the headings silently came out in
    Calibri Light instead of the font I asked for.
  * render_markdown() takes min_level (clamps headings so a stray "# " in a
    section file cannot collide with the section title) and code_size.
  * Every numbered list restarts at 1. The template's "List Number" style shares
    one numbering instance across the whole document, so the second list in a
    report used to continue at 4, 5, 6.
  * Block quotes keep their inline **bold** / `code` formatting.
"""
import re

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

MONO = "Consolas"

# ---------------------------------------------------------------- low-level xml
# OOXML property containers are sequences with a fixed child order. Lab 2's
# helpers appended, which Word tolerates most of the time but a validator does
# not; I insert each element in front of the first sibling that must follow it.
_ORDER = {
    "pPr": ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
            "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd", "tabs",
            "suppressAutoHyphens", "kinsoku", "wordWrap", "overflowPunct",
            "topLinePunct", "autoSpaceDE", "autoSpaceDN", "bidi", "adjustRightInd",
            "snapToGrid", "spacing", "ind", "contextualSpacing", "mirrorIndents",
            "suppressOverlap", "jc", "textDirection", "textAlignment",
            "textboxTightWrap", "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr",
            "pPrChange"],
    "tcPr": ["cnfStyle", "tcW", "gridSpan", "hMerge", "vMerge", "tcBorders", "shd",
             "noWrap", "tcMar", "textDirection", "tcFitText", "vAlign", "hideMark"],
    "tblPr": ["tblStyle", "tblpPr", "tblOverlap", "bidiVisual", "tblStyleRowBandSize",
              "tblStyleColBandSize", "tblW", "jc", "tblCellSpacing", "tblInd",
              "tblBorders", "shd", "tblLayout", "tblCellMar", "tblLook",
              "tblCaption", "tblDescription"],
}


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _put(parent, el):
    """Insert el into parent at its schema position, replacing any same-tag child."""
    name = _local(el.tag)
    for old in parent.findall(el.tag):
        parent.remove(old)
    order = _ORDER.get(_local(parent.tag))
    if not order or name not in order:
        parent.append(el)
        return el
    after = set(order[order.index(name) + 1:])
    for i, child in enumerate(parent):
        if _local(child.tag) in after:
            parent.insert(i, el)
            return el
    parent.append(el)
    return el


def shade(cell, hex_fill):
    """Apply a solid background fill to a table cell."""
    el = OxmlElement("w:shd")
    el.set(qn("w:val"), "clear")
    el.set(qn("w:color"), "auto")
    el.set(qn("w:fill"), hex_fill)
    _put(cell._tc.get_or_add_tcPr(), el)


def set_borders(obj, color="000000", sz=6, style="single", edges=None):
    """Set table borders. obj may be a Table or a _Cell."""
    edges = edges or ("top", "left", "bottom", "right", "insideH", "insideV")
    if hasattr(obj, "_tbl"):                       # Table
        pr = obj._tbl.tblPr
        tag = "w:tblBorders"
    else:                                          # _Cell
        pr = obj._tc.get_or_add_tcPr()
        tag = "w:tcBorders"
    borders = OxmlElement(tag)
    for edge in edges:
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), style)
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), color)
        borders.append(e)
    _put(pr, borders)


def cell_margins(cell, top=80, start=110, bottom=80, end=110):
    """Set cell padding in twentieths of a point."""
    pr = cell._tc.get_or_add_tcPr()
    mar = OxmlElement("w:tcMar")
    for name, val in (("top", top), ("start", start),
                      ("bottom", bottom), ("end", end)):
        node = OxmlElement(f"w:{name}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        mar.append(node)
    _put(pr, mar)


def no_space(par, before=0, after=0):
    par.paragraph_format.space_before = Pt(before)
    par.paragraph_format.space_after = Pt(after)
    return par


_THEME_ATTRS = ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme")


def set_font(target, name):
    """
    Force a font on a style, a run, or a bare w:rPr element.

    I write all four slots (ascii, hAnsi, eastAsia, cs) and delete the theme
    attributes, because Word resolves a theme attribute ahead of an explicit
    name sitting on the same w:rFonts element.
    """
    if hasattr(target, "element") and hasattr(target, "font"):     # style
        rpr = target.element.get_or_add_rPr()
    elif hasattr(target, "_r"):                                    # run
        rpr = target._r.get_or_add_rPr()
    else:                                                          # raw rPr
        rpr = target
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        first = rpr[0] if len(rpr) else None
        rpr.insert(1 if first is not None and _local(first.tag) == "rStyle" else 0,
                   fonts)
    for attr in _THEME_ATTRS:
        if fonts.get(qn(attr)) is not None:
            del fonts.attrib[qn(attr)]
    for slot in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fonts.set(qn(slot), name)


def mono(run, size=None):
    """Consolas run, optionally sized."""
    set_font(run, MONO)
    if size:
        run.font.size = Pt(size)
    return run


def para_border(par, color="9AA3AE", sz=8, style="single", fill=None):
    """Box a single paragraph (used for placeholders so they stay paragraphs)."""
    pr = par._p.get_or_add_pPr()
    bdr = OxmlElement("w:pBdr")
    for edge in ("top", "left", "bottom", "right"):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), style)
        e.set(qn("w:sz"), str(sz))
        e.set(qn("w:space"), "6")
        e.set(qn("w:color"), color)
        bdr.append(e)
    _put(pr, bdr)
    if fill:
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), fill)
        _put(pr, shd)


def keep_table_with_next(tbl):
    """Keep every paragraph of a table with what follows (callout -> figure)."""
    for row in tbl.rows:
        for cell in row.cells:
            for par in cell.paragraphs:
                par.paragraph_format.keep_with_next = True


# ---------------------------------------------------------------- inline spans
# Links come first in the alternation so a URL is never half-eaten by the
# emphasis patterns; a URL inside a `code` span stays code because that span
# starts matching earlier in the string.
MD_LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+)\)")
INLINE = re.compile(r"(\[[^\]\n]+\]\(https?://[^\s)]+\)|https?://[^\s<>]+"
                    r"|\*\*.+?\*\*|(?<!\*)\*(?!\*).+?(?<!\*)\*(?!\*)|`[^`]+`)")
LINK_COLOR = "1155CC"


def add_hyperlink(par, text, url, size=None):
    """Append a clickable external link to a paragraph."""
    rid = par.part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rid)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), LINK_COLOR)
    rpr.append(color)
    if size:
        for tag in ("w:sz", "w:szCs"):                 # half-points
            node = OxmlElement(tag)
            node.set(qn("w:val"), str(int(round(size * 2))))
            rpr.append(node)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    rpr.append(underline)
    run.append(rpr)
    node = OxmlElement("w:t")
    node.set(qn("xml:space"), "preserve")
    node.text = text
    run.append(node)
    link.append(run)
    par._p.append(link)
    return link


def add_inline(par, text, base_size=None, base_mono=False):
    """Append text to a paragraph, honouring **bold**, *italic*, `code` and links."""
    for piece in INLINE.split(text):
        if not piece:
            continue
        link = MD_LINK.fullmatch(piece)
        if link:
            add_hyperlink(par, link.group(1), link.group(2), base_size)
            continue
        if piece.startswith(("http://", "https://")):
            # Sentence punctuation right after a bare URL is not part of it.
            url = piece.rstrip(".,;:!?")
            if url.endswith(")") and url.count("(") < url.count(")"):
                url = url[:-1]
            add_hyperlink(par, url, url, base_size)
            piece = piece[len(url):]
            if not piece:
                continue
        if piece.startswith("**") and piece.endswith("**") and len(piece) > 4:
            r = par.add_run(piece[2:-2]); r.bold = True
        elif piece.startswith("`") and piece.endswith("`") and len(piece) > 2:
            r = par.add_run(piece[1:-1])
            set_font(r, MONO)
            r.font.size = Pt((base_size or 11) - 1)
            r.font.color.rgb = RGBColor(0xA3, 0x15, 0x15)
        elif (piece.startswith("*") and piece.endswith("*")
              and len(piece) > 2 and not piece.startswith("**")):
            r = par.add_run(piece[1:-1]); r.italic = True
        else:
            r = par.add_run(piece)
        if base_mono:
            set_font(r, MONO)
        if base_size and not (piece.startswith("`") and piece.endswith("`")):
            r.font.size = Pt(base_size)
    return par


# ---------------------------------------------------------------- block parser
def parse_blocks(md):
    """Turn Markdown text into a list of (kind, payload) blocks."""
    lines = md.replace("\r\n", "\n").split("\n")
    blocks, i = [], 0
    while i < len(lines):
        line = lines[i]

        if line.strip().startswith("```"):
            lang = line.strip().strip("`").strip()
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1
            blocks.append(("code", (lang, "\n".join(buf))))
            continue

        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            blocks.append(("h", (len(m.group(1)), m.group(2).strip())))
            i += 1
            continue

        if re.match(r"^\s*([-*_])\1{2,}\s*$", line):
            blocks.append(("hr", None)); i += 1; continue

        # pipe table: a header row followed by a --- separator row
        if (line.strip().startswith("|") and i + 1 < len(lines)
                and re.match(r"^\s*\|[\s:|-]+\|\s*$", lines[i + 1])):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not re.match(r"^[\s:|-]+$", "|".join(cells)):
                    rows.append(cells)
                i += 1
            blocks.append(("table", rows))
            continue

        if re.match(r"^\s*[-*+]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[-*+]\s+", lines[i]):
                items.append(re.sub(r"^\s*[-*+]\s+", "", lines[i])); i += 1
            blocks.append(("ul", items))
            continue

        if re.match(r"^\s*\d+[.)]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*\d+[.)]\s+", lines[i]):
                items.append(re.sub(r"^\s*\d+[.)]\s+", "", lines[i])); i += 1
            blocks.append(("ol", items))
            continue

        if line.strip().startswith(">"):
            buf = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i])); i += 1
            blocks.append(("quote", " ".join(x for x in buf if x.strip())))
            continue

        if not line.strip():
            i += 1
            continue

        buf = []
        while (i < len(lines) and lines[i].strip()
               and not lines[i].strip().startswith(("```", "#", ">", "|"))
               and not re.match(r"^\s*([-*+]\s+|\d+[.)]\s+)", lines[i])):
            buf.append(lines[i].strip()); i += 1
        if buf:
            blocks.append(("p", " ".join(buf)))
        else:
            # A line starting with "#" or "|" that did not qualify as a heading
            # or a table (e.g. "#hashtag", a lone "| x |"). Emit it as text
            # rather than spinning on it forever.
            blocks.append(("p", line.strip())); i += 1
    return blocks


def _restart_numbering(doc, style_name="List Number"):
    """
    A fresh w:num that points at the style's abstract list with a start
    override of 1. Returns its numId, or None if the style carries no list.
    """
    try:
        numpr = doc.styles[style_name].element.pPr.numPr
        base_id = numpr.numId.val
        numbering = doc.part.numbering_part.element
        abstract_id = numbering.num_having_numId(base_id).abstractNumId.val
    except (AttributeError, KeyError):
        return None
    num = numbering.add_num(abstract_id)
    num.add_lvlOverride(ilvl=0).add_startOverride(1)
    return num.numId


def code_table(doc, body, size=8.5, fill="F4F5F7", border="C9CCD1"):
    """A light-shaded, bordered single-cell table holding monospaced lines."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    shade(cell, fill)
    set_borders(tbl, color=border, sz=4)
    cell_margins(cell, 90, 130, 90, 130)
    cell.text = ""
    for n, ln in enumerate(body.split("\n")):
        par = cell.paragraphs[0] if n == 0 else cell.add_paragraph()
        no_space(par)
        # Code reads better single-spaced than at the 1.15 body spacing.
        par.paragraph_format.line_spacing = 1.0
        r = par.add_run(ln.expandtabs(4))
        set_font(r, MONO)
        r.font.size = Pt(size)
    return tbl


# ---------------------------------------------------------------- renderer
def render_markdown(doc, md, h_offset=0, body_size=11, min_level=1, code_size=8.5):
    """Render a Markdown string into an open python-docx Document."""
    for kind, payload in parse_blocks(md):
        if kind == "h":
            level, text = payload
            level = max(min_level, min(level + h_offset, 9))
            par = doc.add_heading("", level=level)
            add_inline(par, text)

        elif kind == "p":
            par = doc.add_paragraph()
            par.paragraph_format.space_after = Pt(7)
            add_inline(par, payload, base_size=body_size)

        elif kind == "ul":
            for item in payload:
                par = doc.add_paragraph(style="List Bullet")
                no_space(par, 0, 3)
                add_inline(par, item, base_size=body_size)

        elif kind == "ol":
            num_id = _restart_numbering(doc)
            for item in payload:
                par = doc.add_paragraph(style="List Number")
                no_space(par, 0, 3)
                if num_id is not None:
                    numpr = par._p.get_or_add_pPr().get_or_add_numPr()
                    numpr.get_or_add_ilvl().val = 0
                    numpr.get_or_add_numId().val = num_id
                add_inline(par, item, base_size=body_size)

        elif kind == "quote":
            par = doc.add_paragraph()
            par.paragraph_format.left_indent = Pt(24)
            add_inline(par, payload, base_size=body_size - 0.5)
            for r in par.runs:
                r.italic = True

        elif kind == "code":
            _, body = payload
            code_table(doc, body, size=code_size)
            doc.add_paragraph().paragraph_format.space_after = Pt(4)

        elif kind == "table":
            rows = payload
            if not rows:
                continue
            ncol = max(len(r) for r in rows)
            tbl = doc.add_table(rows=len(rows), cols=ncol)
            tbl.style = "Table Grid"
            tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
            set_borders(tbl, color="444444", sz=6)
            for ri, row in enumerate(rows):
                for ci in range(ncol):
                    cell = tbl.cell(ri, ci)
                    cell.text = ""
                    par = cell.paragraphs[0]
                    no_space(par, 1, 1)
                    par.paragraph_format.line_spacing = 1.0
                    txt = row[ci] if ci < len(row) else ""
                    is_mono = bool(re.fullmatch(r"`[^`]+`", txt.strip()))
                    add_inline(par, txt, base_size=9.5, base_mono=is_mono)
                    if ri == 0:
                        for r in par.runs:
                            r.bold = True
                            r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                        shade(cell, "1F3864")
                    elif ri % 2 == 0:
                        shade(cell, "EEF2F8")
                    cell_margins(cell, 40, 80, 40, 80)
            doc.add_paragraph().paragraph_format.space_after = Pt(4)

        elif kind == "hr":
            par = doc.add_paragraph()
            no_space(par, 4, 4)
            pr = par._p.get_or_add_pPr()
            bdr = OxmlElement("w:pBdr")
            bottom = OxmlElement("w:bottom")
            bottom.set(qn("w:val"), "single")
            bottom.set(qn("w:sz"), "6")
            bottom.set(qn("w:space"), "1")
            bottom.set(qn("w:color"), "AAAAAA")
            bdr.append(bottom)
            _put(pr, bdr)
