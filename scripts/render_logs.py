"""
render_logs.py -- turn the captured stdout logs into terminal-styled PNGs.

run_all.py tees every script's output into screenshots/logs/<script>.txt; this
script draws excerpts of those logs as dark terminal windows under
screenshots/terminal/, so the report is complete without any manual capture
(the callout boxes in the working copy still say how to replace any of them
with a real screenshot). The PNGs are renderings of real captured output, not
photographs of a terminal window, and the report's captions say so.

A capture is an EXCERPT: the lines from the first one containing `start` up to
(not including) the first later one containing `end`. An excerpt that is still
too long keeps its head and tail around a visible "... N lines omitted ..."
marker instead of silently dropping lines. Section rules and banners are drawn
in blue, "check: ... PASS" in green, "result:" lines in amber, and anything
that says FAIL, Error or Traceback in red.

Carried over from Module One. What differs: the RENDER table, the prompt, and
wrapping. A log line longer than WRAP characters is broken at a space and its
continuation indented, keeping the colour of the line it belongs to, so that a
long check sentence stays readable at the report's column width.
"""
import os

import matplotlib
if __name__ == "__main__":      # leave the notebook's inline backend alone
    matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOGS = os.path.join(ROOT, "screenshots", "logs")
TERM = os.path.join(ROOT, "screenshots", "terminal")

BG = "#12161c"
FG = "#d7dde5"
DIM = "#8b949e"
PROMPT = "#6ee787"
HEAD = "#79c0ff"
OK = "#56d364"
RES = "#e3b341"
BAD = "#ff7b72"
PS = "(.venv) PS module02_data_three_ways> "

# Output basename -> (log file, command shown at the prompt, start, end, max lines).
# start / end are substrings matched against log lines (None = from the top / to
# the bottom). max lines is a total, or a (head, tail) pair where the split matters.
# The basenames match the terminal targets in report_spec.py, so a callout box and
# the image embedded under it always name the same file.
_MAX = 60
WRAP = 110
RENDER = {
    "01_prepare_data_panel": ("prepare_data.txt", "python scripts/prepare_data.py",
                              None, "4. Focus countries", _MAX),
    "02_prepare_data_focus": ("prepare_data.txt", "python scripts/prepare_data.py",
                              "4. Focus countries", "result: usa_gdp_pc_1990", _MAX),
    "03_prepare_data_groups": ("prepare_data.txt", "python scripts/prepare_data.py",
                               "5. Income groups", "result: group_high_net_pc_1990", _MAX),
    "04_vis1_browser_checks": ("vis1_altair_linked.txt", "python scripts/vis1_altair_linked.py",
                               "7. The page in a browser", None, _MAX),
    "05_vis2_interaction_checks": ("capture_web.txt", "python scripts/capture_web.py",
                                   "3. Visualization 2 under real mouse", "4. Story steps",
                                   _MAX),
    "06_vis3_main_figure_checks": ("vis3_seaborn_diverging.txt",
                                   "python scripts/vis3_seaborn_diverging.py",
                                   "2. Main figure", "labels read back from the facets", _MAX),
    # The head keeps every script's tally and the first rows of the headline table,
    # the tail its last rows and the verdict; 40 lines is what fits one report page.
    "07_run_all_verification": ("run_all.txt", "python scripts/run_all.py",
                                "INDEPENDENT VERIFICATION", None, (34, 5)),
}


def excerpt(lines, start=None, end=None):
    """Lines from the first containing `start` up to the first later one
    containing `end` (exclusive)."""
    i0 = 0
    if start is not None:
        hits = [i for i, ln in enumerate(lines) if start in ln]
        if not hits:
            raise ValueError(f"start marker not found: {start!r}")
        i0 = hits[0]
        # A banner is three lines (rule, title, rule); keep its top rule.
        if i0 > 0 and set(lines[i0 - 1].strip()) == {"="}:
            i0 -= 1
    i1 = len(lines)
    if end is not None:
        hits = [i for i in range(i0 + 1, len(lines)) if end in lines[i]]
        if not hits:
            raise ValueError(f"end marker not found after start: {end!r}")
        i1 = hits[0]
        if i1 > i0 + 1 and set(lines[i1 - 1].strip()) == {"="}:
            i1 -= 1
    out = lines[i0:i1]
    while out and not out[-1].strip():
        out.pop()
    while out and not out[0].strip():
        out.pop(0)
    return out


def clip(lines, max_lines):
    """Keep head and tail with an explicit omission marker in between."""
    if not max_lines:
        return lines
    if isinstance(max_lines, tuple):
        head, tail = max_lines
    else:
        head = (max_lines - 1) * 2 // 3
        tail = max_lines - 1 - head
    if len(lines) <= head + tail + 1:
        return lines
    gap = len(lines) - head - tail
    return lines[:head] + [f"    ... {gap} lines omitted (full log: screenshots/logs/) ..."] + \
        lines[-tail:]


def wrap(ln, width=WRAP):
    """One log line as one or more display lines no longer than `width`."""
    if len(ln) <= width:
        return [ln]
    pad = " " * (len(ln) - len(ln.lstrip()) + 6)
    out, rest = [], ln
    while len(rest) > width:
        cut = rest.rfind(" ", len(pad) + 1, width + 1)
        if cut < 0:
            cut = width
        out.append(rest[:cut].rstrip())
        rest = pad + rest[cut:].lstrip()
    return out + [rest]


def colour(ln):
    s = ln.strip()
    if not s:
        return FG
    if "FAIL" in s or "Traceback" in s or "Error" in s:
        return BAD
    if s.startswith("check:") or s.startswith("checks:") or s.startswith("verification:"):
        return OK
    if s.startswith("result:"):
        return RES
    if s.startswith("...") and "omitted" in s:
        return DIM
    if set(s) <= {"=", "-"}:
        return HEAD
    # A numbered section heading ("3. Units and identities") or an all-caps banner line.
    # The banner test requires no digits, so table rows are never drawn as headings.
    if s[:2] in {f"{n}." for n in range(1, 10)} and not ln.startswith(" "):
        return HEAD
    if s == s.upper() and any(c.isalpha() for c in s) and not any(c.isdigit() for c in s):
        return HEAD
    return FG


def render_terminal(name, log_file, command, start=None, end=None, max_lines=None):
    path = os.path.join(LOGS, log_file)
    with open(path, encoding="utf-8") as fh:
        body = fh.read().rstrip("\n").split("\n")
    body = clip(excerpt([ln.rstrip() for ln in body], start, end), max_lines)

    # Colour is decided on the whole line, then shared by the pieces it wraps into.
    rows = [(piece, colour(ln)) for ln in body for piece in wrap(ln)]
    lines = [PS + command, ""] + [text for text, _ in rows]
    width = max(len(x) for x in lines)
    fs = 10.0 if width <= 96 else (9.0 if width <= 120 else 7.6)

    fig_w = max(7.0, min(16.0, width * fs * 0.0092 + 0.7))
    fig_h = max(1.6, len(lines) * fs * 0.0215 + 0.45)

    fig = plt.figure(figsize=(fig_w, fig_h), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_facecolor(BG); ax.axis("off")

    y, dy = 1.0, 1.0 / (len(lines) + 1.2)
    for i, ln in enumerate(lines):
        y -= dy
        if i == 0:
            ax.text(0.012, y, PS, color=PROMPT, family="monospace", fontsize=fs, va="top")
            ax.text(0.012, y, " " * len(PS) + command, color="#ffffff",
                    family="monospace", fontsize=fs, va="top", weight="bold")
            continue
        ax.text(0.012, y, ln, color=rows[i - 2][1] if i >= 2 else FG, family="monospace",
                fontsize=fs, va="top")

    os.makedirs(TERM, exist_ok=True)
    out = os.path.join(TERM, f"{name}.png")
    fig.savefig(out, dpi=170, facecolor=BG)
    plt.close(fig)
    print(f"  {os.path.relpath(out, ROOT)}  ({len(lines)} lines, {width} cols)")
    return out


def main():
    print("Rendering terminal captures...")
    missing = 0
    for name, (log_file, command, start, end, mx) in RENDER.items():
        if not os.path.exists(os.path.join(LOGS, log_file)):
            print(f"  ! missing log {log_file} - run scripts/run_all.py first")
            missing += 1
            continue
        render_terminal(name, log_file, command, start, end, mx)
    print(f"Done: {len(RENDER) - missing} of {len(RENDER)} captures rendered.")
    return missing == 0


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
