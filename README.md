# Decoupling or outsourcing? - the web page

The story page for Module Two - Data Three Ways: one question, three
visualizations on three platforms. It is plain HTML, CSS and JavaScript with
no build step, no package manager and no request to any other site. D3 v7 is
bundled in `vendor/`, and there are no web fonts.

## Files

| File | What it is |
|---|---|
| `index.html` | The story page: the question, the three visualizations, the synthesis, sources |
| `d3_embed.html` | Visualization 2 on its own, for iframes and screenshots |
| `styles.css` | One stylesheet for both pages (light theme, colour tokens from `scripts/common.py`) |
| `d3_vis.js` | The D3 chart component: a connected scatterplot with a small API |
| `d3_story.js` | Page wiring: story steps, play button, year slider, URL state, table view |
| `data/decoupling_data.js` | The data, written by `scripts/prepare_data.py` and loaded with a script tag |
| `vendor/d3.v7.min.js` | D3 7.9.0, an unmodified local copy (ISC licence, header kept) |
| `altair_export.html` | Visualization 1, written by `scripts/vis1_altair_linked.py` |
| `altair_spec.json` | The Vega-Lite specification of Visualization 1, from the same script |
| `img/vis3_seaborn_diverging.png` | Visualization 3, copied here by `scripts/capture_web.py` |

Until the Altair export and the Seaborn image exist, `index.html` shows a short
note in their place.

## View it locally

Either open `index.html` in a browser straight from this folder, or serve the
folder, which is closer to how it runs once published:

```powershell
cd web
python -m http.server 8000
```

Then open http://localhost:8000/. Both ways work; the data is a script file,
not a fetch, so nothing depends on a server.

## Visualization 2 from the address bar

`d3_embed.html` and `index.html` read the same parameters, and rewrite them as
the chart changes, so any view can be bookmarked or shared:

| Parameter | Values | Default |
|---|---|---|
| `year` | 1990 to 2022 | 2022 |
| `x` | `linear` or `log` | `linear` |
| `overlay` | `1` shows the production-based paths and the gap | off |
| `context` | `1` shows the other 104 countries in grey | off |
| `only` | country names, short names or ISO codes, comma-separated | all six |
| `step` | 1 to 4, one of the story steps | none |

Example: `d3_embed.html?year=2007&x=log&overlay=1&only=United%20Kingdom,China`

The chart can also be driven from the console or from another script:

```js
const chart = DecouplingStory.apps[0].chart;
chart.setYear(2007);
chart.setScale("linear");
chart.setOverlay(true);
chart.highlight(["United Kingdom"]);
chart.getState();
```

## Embedding Visualization 2

`d3_embed.html` is made for an iframe. At 1000 px wide it needs about 1090 px
of height to show whole. In a frame a little shorter than that the plot gives
up height, down to 420 px; in a frame shorter still it keeps its full height
and the frame scrolls. The chart re-lays itself out at any width from 360 px
up, so the frame can be as wide as its column:

```html
<iframe src="d3_embed.html" title="Income against carbon footprint"
        width="100%" height="1090" style="border:0"></iframe>
```

## Editing the copy

Each block of narrative text in `index.html` has an id: `copy-intro`,
`copy-vis1`, `copy-vis2`, `copy-vis3`, `copy-synthesis`. A number inside a
`<span data-fact="...">` is recomputed from the data when the page loads; the
text typed in the span is what a reader without JavaScript sees. Keep the span
when rewording a sentence, and `scripts/capture_web.py` will check both.

## Publish on GitHub Pages

There is nothing to build. GitHub Pages serves a branch from its root or from
a folder named `docs`, so publish the contents of this folder in one of two
ways.

Option 1, a `gh-pages` branch that holds only this folder (run from the
repository root, with the path to this folder as the prefix):

```powershell
git subtree push --prefix module02_data_three_ways/web origin gh-pages
```

Then, on GitHub: Settings, Pages, Build and deployment, Source "Deploy from a
branch", Branch `gh-pages` and folder `/ (root)`.

Option 2, the main branch: copy this folder to `docs/` at the repository root,
commit it, and choose Branch `main` and folder `/docs` on the same settings
page.

Every path in the page is relative, so it works under
`https://<user>.github.io/<repository>/` without changes. After a change,
re-run `python scripts/run_all.py` so the Altair export, the Seaborn image and
the captures are current, then push again.

## Check it

```powershell
python scripts/capture_web.py
```

opens both pages in headless Microsoft Edge, tests the chart with real mouse
and keyboard input, compares what is drawn with `inputs/decoupling_focus.csv`,
and rewrites the four captures of Visualization 2 in `screenshots/`.
