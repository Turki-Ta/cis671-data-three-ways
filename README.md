# Module Two - Data Three Ways

Data Visualization - Taher Turki - October 2026

**Decoupling or outsourcing?** One dataset on growth, carbon and trade, 1990-2022, drawn three
ways on three platforms, as a remix of Hannah Ritchie's Our World in Data article *Many countries
have decoupled economic growth from CO2 emissions, even if we take offshored production into
account* (2021).

| # | Idiom | Platform | Source | Main figure |
|---|---|---|---|---|
| 1 | Linked views: indexed time series + 109-country scatter, joined by an interval brush | Altair 6 (Vega-Lite) | `scripts/vis1_altair_linked.py` | `screenshots/01_vis1_altair_linked.png` |
| 2 | Connected scatterplot (phase-space trajectories) with a year scrubber | D3 v7 | `web/d3_vis.js`, `web/d3_story.js` | `screenshots/02_vis2_d3_connected_scatter.png` |
| 3 | Small multiples of a diverging area chart | Seaborn / Matplotlib | `scripts/vis3_seaborn_diverging.py` | `screenshots/03_vis3_seaborn_diverging.png` |

What the data says, in one paragraph: in the United States, the United Kingdom, Germany and
Sweden, GDP per person rose 46% to 84% between 1990 and 2022 while CO2 per person fell on both
accounts, so the decoupling is real. Outsourcing is real too, and it can be sized: a wider import
balance gave back 33% of the territorial cut in the United States and 29% in the United Kingdom,
4% in Germany and none in Sweden. For the first two countries it happened between 1990 and 2007.

## Deliverables

- **`report/module02_report_clean.docx`** is the submission copy. Upload it to Google Docs
  (File > Open > Upload); margins, tables, links and images carry over. Export the PDF with
  File > Download > PDF Document (.pdf).
- `report/module02_report.docx` is the same report with a shaded callout box above every figure
  (screenshot id, exact command, what to capture, target filename) and four boxed notes to you.
  `report/module02_report.md` is a Markdown twin of the clean copy.
- `notebooks/module02_story.ipynb` is the computational story, executed in place.
- `web/` is the portfolio page: open `web/index.html`, or see `web/README.md` to serve or publish it.
- `screenshots/SCREENSHOT_INSTRUCTIONS.md` lists every figure as a checklist.

## Before you submit

1. **AI-use disclosures match the brief's one-visualization limit.** Visualization 2 (D3) was
   built with AI coding assistance, as allowed. Visualization 1 (Altair), Visualization 3
   (Seaborn/Matplotlib), the data preparation scripts, and the written analysis were completed
   independently, without AI assistance, and the report says so (Section 1.4 and the last
   paragraph of Sections 3, 4 and 5). `web/index.html` and `notebooks/module02_story.ipynb` carry
   the same disclosure.
2. **Live deployment.** The report names a public URL in Sections 7.1 and 7.2,
   https://turki-ta.github.io/cis671-data-three-ways/. Confirm it resolves before you submit, or
   the link in the report will not work for the grader.
3. **Corrections to the brief.** Four details in the brief did not survive checking, and the
   report uses the verified versions:
   - The article's title is "Many countries have decoupled economic growth from CO2 emissions,
     even if we take offshored production into account" (Ritchie, 1 December 2021). No version of
     the page carries the title given in the brief.
   - Its charts are not all static. It has an interactive Grapher line chart (embedded twice)
     and one static grid; the critique in Section 2 describes them as they are.
   - The data do not show that decoupling "merely" masks outsourcing. Consumption-based CO2 fell
     in all four rich countries. The report states the two-sided result and sizes each side.
   - The Global Carbon Budget 2025 is cited as Friedlingstein et al. (2026), the year the paper
     was published, and the Maddison paper as Bolt and van Zanden (2025), the year of its volume.
4. **Header.** The course line reads "Applied Computer Vision / Data Visualization (Module Two)",
   as given in the brief. To change it, edit `META["course"]` in `scripts/report_spec.py` and
   re-run `python scripts/make_report.py`.
5. **No code appendix.** The four visualization sources come to several thousand lines, so the
   report quotes short excerpts (each checked to be verbatim) and names the files. To append full
   listings, fill `APPENDIX_FILES` in `scripts/report_spec.py`.
6. **Know the numbers.** The scripts print the numbers the report quotes as `result:` lines
   (`screenshots/logs/prepare_data.txt` holds most of them). `screenshots/logs/run_all.txt` shows
   488 of the 518 printed values recomputed from the raw files by a separate route; the other 30
   measure the output itself (image sizes, library versions, contrast ratios). `inputs/SOURCES.md`
   records where every source was checked.
7. **Look at the pages once.** This machine has neither Word nor LibreOffice, so the `.docx` was
   checked by reading it back with python-docx (margins, fonts, captions, embedded images, links)
   and never seen as laid-out pages. After uploading, scroll through it once for a heading left
   alone at the foot of a page or a figure parted from its caption.

## Layout

```
inputs/        raw downloads (OWID CO2 dataset, codebook, World Bank classification, the original
               article's charts), SOURCES.md, and the tidy tables prepare_data.py writes
scripts/       data, charts, captures, the notebook and report builders (see below)
web/           index.html, styles.css, d3_vis.js, d3_story.js, d3_embed.html, altair_export.html,
               data/, vendor/d3.v7.min.js, img/
notebooks/     module02_story.ipynb
screenshots/   figures, terminal/ renders of the logs, logs/ (captured stdout), the checklist
report/        both .docx builds, the .md twin, sections/ (the prose, one Markdown file each)
```

## Reproducing everything

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/run_all.py          # hashes, data, original charts, Vis 1, Vis 3, Vis 2 captures,
                                   # independent re-derivation, terminal PNGs
python scripts/build_notebook.py
python -m jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=900 notebooks/module02_story.ipynb
python scripts/build_notebook.py --verify
python scripts/make_report.py      # both .docx builds, the .md twin, the checklist
python scripts/verify_report.py    # reads the built files back and checks them
```

Nothing touches the network except `python scripts/fetch_inputs.py --fetch`. Two steps drive
Microsoft Edge headlessly through Playwright (the browser tests and captures of Visualizations 1
and 2). The `.venv` was created from the Lab 1 runtime of the computer vision course
(`..\..\..\computer vision\lab 1\lab01_environments\python-runtime\python.exe -m venv .venv`).
Beyond the packages named in the brief it holds `vl-convert-python` (Altair's PNG and offline
HTML export) and `playwright` (browser tests; it uses the installed Edge and downloads no
browser). Nothing was installed system-wide; the install log is `screenshots/logs/00_pip_install.txt`.

## Scripts

| Script | What it does |
|---|---|
| `fetch_inputs.py` | checks the seven raw downloads against their recorded SHA-256; `--fetch` downloads them again |
| `common.py` | paths, the six focus countries, colour tokens, loaders, the `check:` / `result:` log helper |
| `prepare_data.py` | raw CSV to the 110-country panel, the six-country table, the summary and the web data file |
| `original_story.py` | the original article's three chart images, and a comparison of its data with this project's |
| `vis1_altair_linked.py` | Visualization 1: chart, HTML and PNG exports, browser test |
| `vis3_seaborn_diverging.py` | Visualization 3: main figure, derivation plate, absolute-balance figure |
| `capture_web.py` | Visualization 2: browser self-test of the D3 page and its captures |
| `run_all.py` | runs the above in order, then recomputes the published numbers from the raw files by a separate route |
| `render_logs.py` | draws excerpts of the logs as terminal-style PNGs |
| `embed_web.py`, `build_notebook.py` | fold the D3 page into the notebook; build and verify the notebook |
| `report_spec.py`, `make_report.py`, `docx_md.py`, `verify_report.py` | the report plan, builder, Markdown-to-Word renderer and checker |

## Known limits

- **The panel is 110 countries, not 115.** Five countries (Belgium, Luxembourg, Botswana, South
  Africa, Tunisia) carry placeholder consumption figures in some years and are left out. Section
  1.3 of the report and `inputs/SOURCES.md` give the rule.
- **Visualization 2 had no second review.** Visualizations 1 and 3 each went through a separate
  review pass and the fixes that came out of it. The same pass for the D3 chart was cut short, so
  its evidence is the browser self-test in `scripts/capture_web.py` (101 checks) and the captures
  themselves.
- **Visualization 1, three things left as they are.** Hover picks the nearest bubble centre, so
  the rim of China's or India's bubble can name a small neighbour. The six name labels are placed
  for the two windows the report shows and can touch in windows in between. A brush that holds no
  whole year empties the scatter; the panel title then says so and how to recover.
- **One browser.** Everything was tested in Microsoft Edge with a mouse and a keyboard. Other
  browsers and touch input were not tried.

## Conventions

- Every script prints `check: ... PASS` lines on its own output and `result: name = value` lines
  for the numbers the report quotes.
- Blue always means the consumption side (consumption-based CO2, a net importer) and orange the
  production side. Every colour set was run through a colour-vision-deficiency validator; the
  measured separations are in the comments of `scripts/common.py`.
- The report's prose follows the brief's writing rules (no em or en dashes, a list of barred
  words, varied sentence length); `verify_report.py` checks them.
