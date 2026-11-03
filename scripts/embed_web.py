"""
embed_web.py -- fold a page under web/ into one self-contained HTML string, so
the notebook can show the live D3 chart without a web server.

A notebook output cannot load web/d3_embed.html by relative path in every
front end (VS Code and exported notebooks have no server behind them). An
iframe whose srcdoc holds the whole page works everywhere a notebook runs
JavaScript: every local <script src> and stylesheet <link> is replaced by the
file's contents, and the result is HTML-escaped into the srcdoc attribute.
Nothing is fetched at view time.

    from embed_web import iframe
    display(HTML(iframe("d3_embed.html", height=820)))
"""
import html
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WEB = os.path.join(ROOT, "web")

SCRIPT = re.compile(r'<script\b[^>]*?\bsrc="([^"]+)"[^>]*>\s*</script>', re.I)
LINK = re.compile(r'<link\b[^>]*?\bhref="([^"]+)"[^>]*>', re.I)
REMOTE = re.compile(r"^(?:[a-z][a-z0-9+.-]*:)?//", re.I)


def _read(base, ref):
    with open(os.path.join(base, ref.split("?")[0].replace("/", os.sep)), encoding="utf-8") as fh:
        return fh.read()


def inline_page(name):
    """The page web/<name> with its local scripts and stylesheets inlined."""
    path = os.path.join(WEB, name)
    base = os.path.dirname(path)
    with open(path, encoding="utf-8") as fh:
        page = fh.read()

    def script(match):
        if REMOTE.match(match.group(1)):
            return match.group(0)
        # A literal "</script" inside the inlined source would close the tag early.
        body = _read(base, match.group(1)).replace("</script", "<\\/script")
        return f"<script>\n{body}\n</script>"

    def link(match):
        if "stylesheet" not in match.group(0).lower() or REMOTE.match(match.group(1)):
            return match.group(0)
        return f"<style>\n{_read(base, match.group(1))}\n</style>"

    return LINK.sub(link, SCRIPT.sub(script, page))


def iframe(name, height=760, title="Interactive chart"):
    """An HTML snippet: one iframe whose srcdoc is the inlined page."""
    page = html.escape(inline_page(name), quote=True)
    return (f'<div class="embedded-page"><iframe srcdoc="{page}" title="{html.escape(title)}" '
            f'width="100%" height="{int(height)}" style="border:0; background:#fcfcfb">'
            f'</iframe></div>')
