## 4.1 The view

[[SHOT:V2a]]

Visualization 2 removes time from the coordinate axes so that economic output and carbon footprints can be compared directly. Real GDP per person is mapped to the horizontal axis and consumption-based CO2 per person is mapped to the vertical axis, turning each country's 33-year history into a continuous trajectory through income-emissions space from 1990 to 2022 ([[FIG:V2a]]). Where the original OWID line chart forced readers to mentally compare slopes across separate curves, this connected scatterplot makes the coupling relationship the geometry of the mark itself: a trajectory moving up and right indicates emissions rising with income, whereas a trajectory bending down and right demonstrates absolute decoupling.

## 4.2 Idiom, marks and channels

As Haroz et al. (2016, Section 2.1) note, the defining characteristic of a connected scatterplot is that time is encoded sequentially along a path rather than on an axis--which creates a risk that viewers will misread the direction of temporal progression if visual cues are weak. The encoding choices summarized below are designed specifically to keep directionality and scale unmistakable.

| Element | Encoding |
| :--- | :--- |
| **Item** | One country-year: 33 per country, 198 in all |
| **Mark** | A connected line per country, 2.5 px wide at desktop width |
| **Horizontal position** | GDP per person, linear from $0 to $60,000 by default; log scale on toggle |
| **Vertical position** | Consumption-based CO2 per person, linear from 0 to 25 t |
| **Order of connection** | Chronological year: vertices connected sequentially from 1990 to 2022 |
| **Direction** | Mid-segment chevrons rotated to match the screen-space angle of each path segment |
| **Time anchors** | Hollow circular markers with text labels at 1990, 2000, and 2010; solid 12 px marker at the selected year |
| **Hue** | Country identity: six distinct hues paired with direct path-end labels and a top legend |
| **Opacity** | Path segments after the selected scrubber year fade to 0.3 opacity |
| **Guides** | Three diagonal grey rays from the origin marking constant carbon intensities (0.15, 0.3, and 0.6 kg CO2 per dollar of GDP) |

**Four redundant cues for temporal direction.** Because Haroz et al. (2016, Section 7) found that single arrows are often insufficient to prevent time-reversal errors, the chart layers four distinct directional signals: mid-segment chevrons, decadal hollow anchor markers (1990, 2000, 2010), a solid terminal marker at the active year, and an interactive year scrubber. Because real GDP per capita rises in almost every year, trajectories naturally progress from left to right; the brief leftward hooks in 2009 and 2020 immediately stand out as the global financial crisis and COVID-19 recessions.

**Keeping the full trajectory visible during playback.** While an interactive play button and year slider encourage step-by-step exploration, Robertson et al. (2008) showed that animated trend displays are slower and more error-prone for analytical comparison than static traces. Accordingly, the full 1990-2022 path remains visible on screen at all times--with future years dimmed to 0.3 opacity when scrubbing--so the viewer never loses sight of the complete trajectory.

**Linear default scale with constant-intensity rays.** On a linear x-axis starting at (0, 0), the four high-income trajectories spread out clearly across the right two-thirds of the canvas, and straight lines radiating from the origin acquire a direct physical meaning: any ray of constant slope k represents a constant carbon intensity of economic output (kg CO2 per dollar of GDP). The chart draws three reference rays at 0.15, 0.30, and 0.60 kg per dollar. A path crossing clockwise into a shallower ray achieves *relative decoupling* (lower carbon intensity per dollar), whereas a path moving downward achieves *absolute decoupling* (lower total emissions per person). Toggling the x-axis to logarithmic mode bends those same constant-intensity lines into smooth curves:

```javascript
// web/d3_vis.js
              const gdp = state.scale === "linear" ? lo[0] + (lo[1] - lo[0]) * i / steps
                : lo[0] * Math.pow(lo[1] / lo[0], i / steps);
              points.push({ x: sx(gdp), y: yScale(k * gdp / 1000) });
```

**Redundant country labeling.** Distinguishing six categorical hues across intersecting lines is challenging under color vision deficiency. Using the simulation matrices of Machado et al. (2009), the three overlapping European paths (United Kingdom, Germany, Sweden) were assigned the most strongly contrasting hues, while the closest pair of hues was assigned to the United States and India at opposite corners of the canvas, reinforced by direct text labels at the end of every path.

## 4.3 What the trajectories show

**A clear mid-2000s turning point for the US and UK.** Both the United States and the United Kingdom initially travel upward and to the right: US consumption-based CO2 per person rose 13% between 1990 and its 2005 peak as GDP per person grew 36%, while UK consumption emissions rose 11% through 2004. After 2005, both trajectories bend sharply downward. Between 2007 and 2022, consumption-based CO2 per person fell by 25% in the United States, 41% in the United Kingdom, 22% in Germany, and 35% in Sweden, while per-capita GDP grew by 12%, 4%, 17%, and 11%, respectively. Unlike the US and UK, Germany and Sweden peaked in 1992 and have trended downward and to the right for three decades.

**Continuous upward coupling in China and India.** Neither China nor India exhibits a downward bend. Over the 33-year window, China's GDP per person expanded by 545% while its consumption-based CO2 per person rose 258%; India's grew by 263% and 143%, respectively. Across both economies, each 1% increase in per-capita income was accompanied by roughly 0.7% growth in per-capita consumption emissions.

**Universal relative decoupling across all six economies.** Despite diverging in absolute terms, all six trajectories cross the grey reference rays clockwise toward lower carbon intensities. In 1990, five of the six countries sat between the 0.3 and 0.6 kg per dollar rays, and China sat above the 0.6 ray at 0.70 kg per dollar. By 2022, five sit below the 0.3 kg per dollar ray and China has dropped to 0.39 kg per dollar. Over the full period, the carbon intensity of consumption fell by 71% in Sweden, 64% in Germany, 57% in the United Kingdom, 48% in the United States, 45% in China, and 33% in India.

**Inspecting the territorial-consumption gap directly on the canvas.** Checking *"Show production-based path"* overlays each country's territorial series as a thinner line and connects same-year points with a vertical gap indicator at the selected year ([[FIG:V2b]], right). At 2022, this vertical gap equals +2.81 t for the United Kingdom, +2.86 t for Sweden, +2.03 t for Germany, +1.49 t for the United States, -0.90 t for China, and -0.34 t for India. Scrubbing back to 2007 highlights the United Kingdom's peak import gap of +3.34 t ([[FIG:V2c]]).

[[SHOT:V2b]]

## 4.4 Interaction

A unified control bar above the canvas provides six interactive affordances: a year slider with an automated Play/Pause toggle, a Linear/Log scale switcher for the GDP axis, a checkbox to overlay production-based paths, a checkbox to render the remaining 104 countries as faint grey background trajectories, clickable legend items to isolate specific countries, and four guided story steps that configure the view to illustrate key findings (Segel & Heer, 2010).

To make hovering effortless without requiring the user to land precisely on a 2.5 px path stroke, mouse position is resolved via a Delaunay triangulation (`d3.Delaunay`) computed over all visible vertices within a 30 px capture radius:

```javascript
// web/d3_vis.js
      focusIndex = focusPoints.length ? d3.Delaunay.from(focusPoints, px, py) : null;
```

Hovering highlights the active country's trajectory, dims the remaining paths, and opens a structured tooltip displaying GDP per capita, both CO2 accounts, and the net trade balance ([[FIG:V2c]]). Full keyboard navigation (Tab and arrow keys) and a synchronized summary table below the chart ensure accessibility.

[[SHOT:V2c]]

## 4.5 Implementation

The visualization is built in vanilla JavaScript on D3 v7.9 (Bostock et al., 2011) with no external framework or build step. `web/d3_vis.js` renders a responsive SVG using a `viewBox`, while `web/d3_story.js` synchronizes the UI controls, guided narrative steps, data table, and URL query parameters (`?year=2007&overlay=1`). Directional chevrons are positioned and rotated in screen coordinates after applying the active axis scales so that arrowheads remain properly tangent to the path under both linear and logarithmic views:

```javascript
// web/d3_vis.js
        const mid = { x: (pts[i].x + pts[i + 1].x) / 2, y: (pts[i].y + pts[i + 1].y) / 2 };
// ...
        out.push({ x: mid.x, y: mid.y, i: i + 0.5,
                   angle: Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI });
```

An automated browser check (`scripts/capture_web.py`) drives the rendered page in Microsoft Edge and verifies that all 396 plotted vertices across the consumption and production paths invert back to the source CSV values within 0.02% for GDP and 0.001 t for CO2.

**AI-use disclosure.** In accordance with the assignment guidelines allowing AI assistance on at most one visualization, this D3.js connected scatterplot was developed with AI coding assistance. I used Claude (Anthropic) as a coding partner to help implement `web/d3_vis.js` and `web/d3_story.js` from my design specification--specifically assisting with the D3 v7 SVG path rendering, screen-space chevron rotation math, Delaunay triangulation hover lookup, and control wiring. I reviewed, tested, and verified the implementation and wrote the analysis in this section independently.

Source files for this section: `web/d3_vis.js` and `web/d3_story.js`
