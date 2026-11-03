/*
 * d3_vis.js -- Visualization 2: a connected scatterplot (phase-space
 * trajectories). GDP per capita runs along x, consumption-based CO2 per capita
 * up y, and each country is one path ordered by year, so time is carried by
 * the line itself and by the year the reader scrubs to.
 *
 * This file is the chart component only: it draws the title, the legend and
 * the plot into a container element and returns a small API. The slider, the
 * play button, the story steps and the table are page wiring (d3_story.js).
 *
 * The x-axis is linear by default, which gives the four high-income countries
 * room and makes a slope mean something: a ray from the origin is a constant
 * carbon intensity of income (CO2 per dollar), and three such rays are drawn as
 * guides. A path that crosses to a shallower ray has cut its CO2 per dollar;
 * a path that also heads downward has cut its CO2 per person. The log axis is
 * one click away, and there the same guides bend into curves.
 *
 *     var chart = DecouplingChart.create(element, window.DECOUPLING_DATA, {year: 2007});
 *     chart.setYear(2010);              chart.setScale("linear");
 *     chart.setOverlay(true);           chart.setContext(true);
 *     chart.setVisible(["China"]);      chart.toggle("India");
 *     chart.highlight(["China"]);       chart.setHeight(480);
 *     chart.play({from: 1990});         chart.pause();
 *     chart.showDetail("China", 2010);  chart.hideDetail();
 *     chart.getState();                 chart.on("change", function (state) { ... });
 *
 * How it is put together, top to bottom: formatting and geometry helpers; the
 * sizes for a given width; then create(), which builds the DOM once, lays it
 * out for the current width and scale (layout), redraws what depends on the
 * year (frame), places the labels, and handles hover, keyboard and the API.
 *
 * Needs D3 v7 (vendor/d3.v7.min.js) loaded first; nothing else, and no network
 * request. Mark colours come from the data file, which takes them from
 * scripts/common.py. Every other colour is a custom property in styles.css,
 * so the chart chrome is defined in one place.
 */
(function (global) {
  "use strict";

  const d3 = global.d3;

  const DEFAULTS = {
    title: null,          // null = written from the data: how many countries, which years
    subtitle: null,       // null = one line on how to read a connected scatterplot
    note: null,           // null = the source named in the data file
    titleTag: "h3",
    year: null,           // null = the last year in the data
    scale: "linear",      // "linear" or "log" x-axis
    overlay: false,       // production-based paths and the gap at the chosen year
    context: false,       // the other countries as thin grey paths
    visible: null,        // null = every country
    height: null,         // null = chosen from the width
    anchorYears: null,    // null = first year, last year and the decades between
    chevronEvery: 3,      // years between direction chevrons
    msPerYear: 320,       // speed of the play animation
    msPerStep: 700,       // pace of play when motion is reduced
    hoverRadius: 30,      // px: how far the pointer may be from the point it picks
    contextRadius: 10     // px: the same for a grey context path
  };

  const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                 "ten"];
  // Guides of constant carbon intensity, in kg of consumption-based CO2 per
  // international-$ of GDP; each is double the one before. In 1990 five of the six
  // countries lay between the upper two, and in 2022 five lie below the middle one.
  const GUIDES = [0.15, 0.3, 0.6];
  const GUIDE_KEY = "grey rays: 0.15, 0.3 and 0.6 kg CO2 per $ of GDP";
  let instances = 0;
  let canvasContext = null;
  const widthCache = new Map();

  // ------------------------------------------------------------ formatting
  // Signs are written by hand because d3.format prints negative numbers with
  // U+2212, and every string a reader sees on this page is plain ASCII.
  const grouped = d3 ? d3.format(",.0f") : String;

  function money(v) { return "$" + grouped(v); }

  function tonnes(v) { return v.toFixed(2) + " t"; }

  function signedTonnes(v) {
    const r = Math.abs(v) < 0.005 ? 0 : v;
    return (r > 0 ? "+" : r < 0 ? "-" : "") + Math.abs(r).toFixed(2) + " t";
  }

  function tradeRole(v) {
    return Math.abs(v) < 0.005 ? "balanced" : v > 0 ? "net importer" : "net exporter";
  }

  function countWord(n) { return n < WORDS.length ? WORDS[n] : String(n); }

  // The net balance per person, as precisely as the data file allows. The file
  // carries it twice: as netPc, rounded to four decimals, and as netMt (two
  // decimals) beside the population. For a country of more than 100 million
  // people the second is the finer of the two, and it settles the cases where
  // netPc sits on a rounding boundary: the United States in 2022 is 1.4950 in
  // the file and 1.49498 before rounding, which prints as +1.49 t, not +1.50 t.
  function netBalance(d) {
    return d.netMt != null && d.pop > 1e8 ? d.netMt * 1e6 / d.pop : d.netPc;
  }

  // ------------------------------------------------------------ geometry helpers
  function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function distance(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }

  // Distance from point p to the segment a-b.
  function distanceToSegment(p, a, b) {
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const along = clamp(((p.x - a.x) * dx + (p.y - a.y) * dy) / (dx * dx + dy * dy || 1), 0, 1);
    return Math.hypot(p.x - (a.x + along * dx), p.y - (a.y + along * dy));
  }

  function textWidth(text, font) {
    const key = font + "|" + text;
    if (!widthCache.has(key)) {
      if (!canvasContext) { canvasContext = document.createElement("canvas").getContext("2d"); }
      canvasContext.font = font;
      widthCache.set(key, canvasContext.measureText(text).width);
    }
    return widthCache.get(key);
  }

  // The box a label of width w and font size fs covers when its text is
  // anchored at (x, y) and centred vertically on y. HALF_LINE is half the
  // height of a line of text in ems, as the browser boxes it.
  const HALF_LINE = 0.66;

  function labelBox(x, y, w, fs, anchor) {
    const x0 = anchor === "start" ? x : anchor === "end" ? x - w : x - w / 2;
    return { x0: x0, x1: x0 + w, y0: y - fs * HALF_LINE, y1: y + fs * HALF_LINE };
  }

  function grow(box, by) {
    return { x0: box.x0 - by, x1: box.x1 + by, y0: box.y0 - by, y1: box.y1 + by };
  }

  function boxesOverlap(a, b) {
    return a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;
  }

  function boxHitsCircle(box, c) {
    const nx = clamp(c.x, box.x0, box.x1);
    const ny = clamp(c.y, box.y0, box.y1);
    return (nx - c.x) * (nx - c.x) + (ny - c.y) * (ny - c.y) < c.r * c.r;
  }

  function pointsInBox(box, points) {
    let n = 0;
    for (let i = 0; i < points.length; i++) {
      const p = points[i];
      if (p.x > box.x0 && p.x < box.x1 && p.y > box.y0 && p.y < box.y1) { n++; }
    }
    return n;
  }

  // Points every few pixels along a polyline, each tagged with its fractional
  // position in time, so label placement can ask "how much line is under here".
  function samplePolyline(points, spacing) {
    const out = [];
    for (let i = 0; i < points.length - 1; i++) {
      const a = points[i];
      const b = points[i + 1];
      const n = Math.max(1, Math.ceil(distance(a, b) / spacing));
      for (let j = 0; j < n; j++) {
        const f = j / n;
        out.push({ x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, i: i + f });
      }
    }
    const last = points[points.length - 1];
    out.push({ x: last.x, y: last.y, i: points.length - 1 });
    return out;
  }

  // Slots for a label of font size fs around a mark of radius r, in the order
  // E, NE, SE, W, NW, SW, N, S. In every slot the nearest edge or corner of the
  // text box is 4 px (plus extra) clear of the mark.
  function slotsAround(p, r, fs, extra) {
    const g = r + 4 + extra;
    const d = g * Math.SQRT1_2;
    const half = fs * HALF_LINE;
    return [
      { x: p.x + g, y: p.y, anchor: "start" },
      { x: p.x + d, y: p.y - d - half, anchor: "start" },
      { x: p.x + d, y: p.y + d + half, anchor: "start" },
      { x: p.x - g, y: p.y, anchor: "end" },
      { x: p.x - d, y: p.y - d - half, anchor: "end" },
      { x: p.x - d, y: p.y + d + half, anchor: "end" },
      { x: p.x, y: p.y - g - half, anchor: "middle" },
      { x: p.x, y: p.y + g + half, anchor: "middle" }
    ];
  }

  // Type and mark sizes for a chart W px wide. The viewBox always equals the
  // rendered size, so these are real CSS pixels at every width.
  function sizesFor(W, heightOverride) {
    const tier = W < 520 ? 0 : W < 860 ? 1 : 2;
    const pick = function (values) { return values[tier]; };
    const natural = [clamp(W * 1.15, 380, 480), clamp(W * 0.72, 420, 540),
                     clamp(W * 0.56, 520, 660)][tier];
    const axisTitle = pick([11.5, 12.5, 13.5]);
    const tick = pick([11, 12, 13]);
    return {
      W: W,
      H: Math.round(heightOverride ? Math.max(300, heightOverride) : natural),
      narrow: tier === 0,
      // The right margin is wider on small charts: on the log scale the four
      // high-income paths end near the right edge and their names go beside them.
      margin: { top: axisTitle + 22, right: pick([46, 36, 30]),
                bottom: tick + axisTitle + pick([30, 30, 32]), left: pick([30, 38, 44]) },
      tick: tick,
      axisTitle: axisTitle,
      name: pick([12, 13.5, 14.5]),
      yearLabel: pick([10.5, 11.5, 12]),
      note: pick([11, 12, 13]),
      range: pick([19, 26, 32]),
      stroke: pick([2, 2.25, 2.5]),
      thin: pick([1.1, 1.25, 1.4]),
      marker: pick([4.5, 5.25, 6]),         // radius of the filled disc
      waypoint: pick([3.5, 3.75, 4]),       // radius of the hollow year marks
      chevron: pick([4.2, 5, 5.5]),
      chevronGap: pick([32, 42, 50]),
      arrow: pick([22, 28, 32])
    };
  }

  // ------------------------------------------------------------ the component
  function create(container, data, options) {
    if (!d3) { throw new Error("d3_vis.js needs D3 v7 to be loaded first"); }
    const opts = Object.assign({}, DEFAULTS, options || {});
    const uid = "dc" + (++instances);
    const meta = data.meta;
    const yearMin = meta.yearMin;
    const yearMax = meta.yearMax;
    const nYears = yearMax - yearMin + 1;
    const motionQuery = global.matchMedia ? global.matchMedia("(prefers-reduced-motion: reduce)")
                                          : { matches: false };
    const dispatch = d3.dispatch("change", "hover");

    const countries = data.countries.map(function (c) {
      return { name: c.name, short: c.short || c.name, iso: c.iso, color: c.color,
               incomeGroup: c.incomeGroup, series: c.series };
    });
    const byName = new Map(countries.map(function (c) { return [c.name, c]; }));
    const context = data.context || [];

    const anchorYears = opts.anchorYears || d3.range(yearMin, yearMax + 1).filter(function (y) {
      return y === yearMin || y === yearMax || (y % 10 === 0 && y - yearMin > 4 && yearMax - y > 4);
    });

    // Axis domains are fixed for the life of the chart. Hiding a country must
    // not move the others, and a path has to mean the same thing in every state.
    const gdpExtent = d3.extent(d3.merge(countries.map(function (c) {
      return c.series.map(function (d) { return d.gdpPc; });
    })));
    const co2Max = d3.max(countries, function (c) {
      return d3.max(c.series, function (d) { return Math.max(d.consPc, d.prodPc); });
    });
    const domain = {
      log: [gdpExtent[0] / 1.35, gdpExtent[1] * 1.4],
      linear: d3.nice(0, gdpExtent[1] * 1.03, 6),
      y: d3.nice(0, co2Max, 5)
    };

    function clampYear(y) { return clamp(Math.round(+y), yearMin, yearMax); }

    const startYear = opts.year == null || isNaN(+opts.year) ? yearMax : clampYear(opts.year);
    const state = {
      year: startYear,
      t: startYear,             // the drawn position in time; fractional while playing
      scale: opts.scale === "log" ? "log" : "linear",
      blend: opts.scale === "log" ? 0 : 1,      // 0 = log, 1 = linear, between during a change
      overlay: !!opts.overlay,
      context: !!opts.context,
      visible: new Set(countries.map(function (c) { return c.name; })),
      highlight: null,          // names kept at full strength, or null for all
      hover: null,              // the point whose detail is showing
      playing: false
    };
    if (opts.visible) {
      const asked = resolveNames(opts.visible);
      if (asked.size) { state.visible = asked; }    // unknown names leave every country on
    }

    let S = null;               // sizes for the current width
    let inner = null;           // plot area in px
    let xLog = null;
    let xLin = null;
    let yScale = null;
    let heightOverride = opts.height;
    let tweening = false;       // true while the x-scale is changing
    let playTimer = null;
    let scaleTimer = null;
    let transient = null;       // country emphasised from the legend
    let cursor = null;          // keyboard position {name, index}
    let focusIndex = null;      // nearest-point lookup over the focus countries
    let focusPoints = [];
    let contextIndex = null;
    let contextPoints = [];
    let yearLabels = [];        // placed year labels (static between layouts)
    let obstacles = [];         // boxes of the in-plot notes
    let fontFamily = "sans-serif";
    let clippedContext = 0;

    function resolveNames(names) {
      const list = Array.isArray(names) ? names : [names];
      const wanted = new Set();
      list.forEach(function (raw) {
        const key = String(raw).trim().toLowerCase();
        countries.forEach(function (c) {
          if ([c.name, c.short, c.iso].some(function (v) { return v.toLowerCase() === key; })) {
            wanted.add(c.name);
          }
        });
      });
      return wanted;
    }

    // ---------------------------------------------------------- DOM skeleton
    const root = d3.select(container).classed("dc", true);
    root.selectAll("*").remove();

    const head = root.append("div").attr("class", "dc-head");
    head.append(opts.titleTag).attr("class", "dc-title").attr("id", uid + "-title")
        .text(opts.title || "Income against carbon footprint: " + countWord(countries.length) +
              " countries, " + yearMin + "-" + yearMax);
    head.append("p").attr("class", "dc-subtitle").attr("id", uid + "-subtitle")
        .text(opts.subtitle || "Each line is one country's path from " + yearMin + " to " +
              yearMax + ". Down and to the right means richer with a smaller footprint.");

    const legend = root.append("div").attr("class", "dc-legend").attr("role", "group")
        .attr("aria-label", "Countries. Select a name to hide or show its path.");
    const legendItems = legend.selectAll("button.dc-legend-item").data(countries).join("button")
        .attr("type", "button").attr("class", "dc-legend-item")
        .attr("data-name", function (c) { return c.name; })
        .on("click", function (event, c) { toggle(c.name); })
        .on("pointerenter focus", function (event, c) { transient = c.name; updateEmphasis(); })
        .on("pointerleave blur", function () { transient = null; updateEmphasis(); });
    legendItems.each(function (c) {
      const key = d3.select(this).append("svg").attr("class", "dc-legend-key")
          .attr("viewBox", "0 0 30 12").attr("width", 30).attr("height", 12)
          .attr("aria-hidden", "true").attr("focusable", "false");
      key.append("line").attr("x1", 1.5).attr("x2", 28.5).attr("y1", 6).attr("y2", 6)
          .attr("stroke", c.color).attr("stroke-width", 2.5).attr("stroke-linecap", "round");
      key.append("circle").attr("cx", 15).attr("cy", 6).attr("r", 4.5)
          .attr("fill", c.color).attr("class", "dc-ring");
    });
    legendItems.append("span").text(function (c) { return c.name; });
    const resetButton = legend.append("button").attr("type", "button")
        .attr("class", "dc-legend-reset").text("Show all").property("hidden", true)
        .on("click", function () { setVisible(null); });

    // A key for the marks that are not countries. The symbols are drawn in the
    // neutral ink so they read as "any country", never as a seventh series.
    const key = root.append("div").attr("class", "dc-key");
    function keyItem(className, label, draw) {
      const item = key.append("span").attr("class", "dc-key-item " + className);
      const symbol = item.append("svg").attr("viewBox", "0 0 26 12").attr("width", 26)
          .attr("height", 12).attr("aria-hidden", "true").attr("focusable", "false");
      draw(symbol);
      item.append("span").text(label);
      return item;
    }
    keyItem("", "labelled year", function (s) {
      s.append("circle").attr("cx", 13).attr("cy", 6).attr("r", 3.75)
          .attr("class", "dc-key-hollow");
    });
    keyItem("", "selected year", function (s) {
      s.append("circle").attr("cx", 13).attr("cy", 6).attr("r", 5).attr("class", "dc-key-fill");
    });
    keyItem("", "direction of travel", function (s) {
      s.append("line").attr("x1", 2).attr("x2", 24).attr("y1", 6).attr("y2", 6)
          .attr("class", "dc-key-line");
      s.append("path").attr("d", "M10.5,1.8L15,6L10.5,10.2").attr("class", "dc-key-line");
    });
    keyItem("dc-key-guides", GUIDE_KEY, function (s) {
      s.append("line").attr("x1", 2).attr("x2", 24).attr("y1", 11).attr("y2", 1)
          .attr("class", "dc-key-guide");
    });
    const overlayKeys = [
      keyItem("dc-key-overlay", "consumption-based", function (s) {
        s.append("line").attr("x1", 2).attr("x2", 24).attr("y1", 6).attr("y2", 6)
            .attr("class", "dc-key-line");
      }),
      keyItem("dc-key-overlay", "production-based", function (s) {
        s.append("line").attr("x1", 2).attr("x2", 24).attr("y1", 6).attr("y2", 6)
            .attr("class", "dc-key-thin");
      }),
      keyItem("dc-key-overlay", "gap = net balance in the selected year", function (s) {
        s.append("line").attr("x1", 13).attr("x2", 13).attr("y1", 1).attr("y2", 11)
            .attr("class", "dc-key-gap");
      })
    ];

    const stage = root.append("div").attr("class", "dc-stage");
    const svg = stage.append("svg").attr("class", "dc-svg").attr("role", "application")
        .attr("tabindex", 0).attr("aria-labelledby", uid + "-title")
        .attr("aria-describedby", uid + "-subtitle " + uid + "-keys");
    root.append("p").attr("class", "dc-hidden").attr("id", uid + "-keys")
        .text("Keyboard: left and right arrows move along a path one year at a time, up and " +
              "down arrows change country, Home and End jump to the first and last year, " +
              "Escape closes the readout. The table view under the chart lists the same values.");
    const defs = svg.append("defs");
    const clipRect = defs.append("clipPath").attr("id", uid + "-clip").append("rect");
    const gPlot = svg.append("g").attr("class", "dc-plot");
    const gGrid = gPlot.append("g").attr("class", "dc-grid");
    const gGuides = gPlot.append("g").attr("class", "dc-guides")
        .attr("clip-path", "url(#" + uid + "-clip)");
    const gAxis = gPlot.append("g").attr("class", "dc-axis");
    const xTitle = gPlot.append("text").attr("class", "dc-axis-title dc-axis-title-x")
        .attr("text-anchor", "middle");
    const yTitle = gPlot.append("text").attr("class", "dc-axis-title dc-axis-title-y");
    const gContext = gPlot.append("g").attr("class", "dc-context")
        .attr("clip-path", "url(#" + uid + "-clip)");
    const rangeLabel = gPlot.append("text").attr("class", "dc-range").attr("text-anchor", "end");
    const gNotes = gPlot.append("g").attr("class", "dc-notes");
    const gCountries = gPlot.append("g").attr("class", "dc-countries");
    const gMarkers = gPlot.append("g").attr("class", "dc-markers");
    const gYearLabels = gPlot.append("g").attr("class", "dc-year-labels");
    const gLabels = gPlot.append("g").attr("class", "dc-labels");
    const gHover = gPlot.append("g").attr("class", "dc-hover").attr("display", "none");
    const emptyNote = gPlot.append("text").attr("class", "dc-empty").attr("text-anchor", "middle")
        .text("All countries are hidden. Select a name above to show its path.");
    const hit = svg.append("rect").attr("class", "dc-hit");

    const countryG = gCountries.selectAll("g.dc-country").data(countries).join("g")
        .attr("class", "dc-country").attr("data-name", function (c) { return c.name; });
    countryG.append("path").attr("class", "dc-prod dc-prod-ghost");
    countryG.append("path").attr("class", "dc-prod dc-prod-done");
    countryG.append("path").attr("class", "dc-ghost");
    countryG.append("path").attr("class", "dc-done");
    countryG.append("g").attr("class", "dc-chevrons");
    countryG.append("g").attr("class", "dc-waypoints");
    // append() hands each new path its country's datum, so the colour is one lookup.
    countryG.selectAll("path").attr("stroke", function (c) { return c.color; });

    const markerG = gMarkers.selectAll("g.dc-marker").data(countries).join("g")
        .attr("class", "dc-marker").attr("data-name", function (c) { return c.name; });
    markerG.append("line").attr("class", "dc-gap");
    markerG.append("circle").attr("class", "dc-prod-now dc-ring-fill")
        .attr("stroke", function (c) { return c.color; });
    markerG.append("circle").attr("class", "dc-now dc-ring")
        .attr("fill", function (c) { return c.color; });

    const labelG = gLabels.selectAll("g.dc-label").data(countries).join("g")
        .attr("class", "dc-label").attr("data-name", function (c) { return c.name; });
    labelG.append("line").attr("class", "dc-leader");
    labelG.append("text").attr("class", "dc-gap-label dc-halo");
    // The label beside the filled marker: the country in ink and, where there is
    // room, the scrubbed year after it, so every marked point reads as a year.
    const nameText = labelG.append("text").attr("class", "dc-name dc-halo");
    nameText.append("tspan").attr("class", "dc-name-country");
    nameText.append("tspan").attr("class", "dc-name-year").attr("dx", 5);

    gHover.append("line").attr("class", "dc-hover-gap");
    gHover.append("circle").attr("class", "dc-hover-twin dc-ring-fill");
    gHover.append("circle").attr("class", "dc-hover-dot dc-ring");
    gHover.append("circle").attr("class", "dc-hover-ring");

    // The direction key: two arrows from one origin, in the empty top-left corner.
    const compass = gNotes.append("g").attr("class", "dc-compass");
    compass.append("path").attr("class", "dc-compass-line dc-compass-up");
    compass.append("path").attr("class", "dc-compass-line dc-compass-down");
    compass.append("circle").attr("class", "dc-compass-origin").attr("r", 2);
    compass.append("text").attr("class", "dc-note dc-halo dc-compass-up-text")
        .text("richer, larger footprint");
    compass.append("text").attr("class", "dc-note dc-halo dc-compass-down-text")
        .text("richer, smaller footprint");

    const tooltip = stage.append("div").attr("class", "dc-tooltip").attr("aria-hidden", "true")
        .property("hidden", true);
    const ttHead = tooltip.append("div").attr("class", "dc-tt-head");
    const ttKey = ttHead.append("span").attr("class", "dc-tt-key");
    const ttCountry = ttHead.append("span").attr("class", "dc-tt-country");
    const ttYear = ttHead.append("span").attr("class", "dc-tt-year");
    const ttRows = tooltip.append("div").attr("class", "dc-tt-rows");
    const ttRow = {};
    [["gdp", "GDP per capita"], ["cons", "consumption-based CO2"],
     ["prod", "production-based CO2"], ["net", "net balance"]].forEach(function (pair) {
      const row = ttRows.append("div").attr("class", "dc-tt-row dc-tt-" + pair[0]);
      ttRow[pair[0]] = { value: row.append("span").attr("class", "dc-tt-value"),
                         label: row.append("span").attr("class", "dc-tt-label").text(pair[1]) };
    });

    const note = root.append("p").attr("class", "dc-note-line");
    const live = root.append("div").attr("class", "dc-hidden").attr("aria-live", "polite");

    const line = d3.line().x(function (p) { return p.x; }).y(function (p) { return p.y; });
    if (line.digits) { line.digits(2); }

    // ---------------------------------------------------------- scales
    // One x mapping for both scale types: a weighted mean of the log and the
    // linear position, so a change of scale can be shown as a movement.
    function sx(v) {
      const k = state.blend;
      if (k >= 1) { return xLin(v); }
      const logPos = xLog(v > 0 ? v : domain.log[0]);
      return k <= 0 ? logPos : (1 - k) * logPos + k * xLin(v);
    }

    function xTicks() {
      if (state.scale === "linear") { return xLin.ticks(S.narrow ? 4 : 6); }
      const out = [];
      const p0 = Math.floor(Math.log10(domain.log[0]));
      const p1 = Math.ceil(Math.log10(domain.log[1]));
      for (let p = p0; p <= p1; p++) {
        [1, 2, 5].forEach(function (m) {
          const v = m * Math.pow(10, p);
          if (v >= domain.log[0] && v <= domain.log[1]) { out.push(v); }
        });
      }
      return out;
    }

    function font(weight, size) { return weight + " " + size + "px " + fontFamily; }

    function firstThatFits(variants, fontString, room) {
      for (let i = 0; i < variants.length; i++) {
        if (textWidth(variants[i], fontString) <= room) { return variants[i]; }
      }
      return variants[variants.length - 1];
    }

    // ---------------------------------------------------------- layout
    function layout() {
      const measured = Math.floor(stage.node().clientWidth);
      S = sizesFor(measured > 0 ? Math.max(280, measured) : 640, heightOverride);
      inner = { w: S.W - S.margin.left - S.margin.right, h: S.H - S.margin.top - S.margin.bottom };
      fontFamily = global.getComputedStyle(svg.node()).fontFamily || "sans-serif";
      xLog = d3.scaleLog().domain(domain.log).range([0, inner.w]);
      xLin = d3.scaleLinear().domain(domain.linear).range([0, inner.w]);
      yScale = d3.scaleLinear().domain(domain.y).range([inner.h, 0]);

      svg.attr("viewBox", "0 0 " + S.W + " " + S.H).attr("width", S.W).attr("height", S.H);
      gPlot.attr("transform", "translate(" + S.margin.left + "," + S.margin.top + ")");
      clipRect.attr("width", inner.w).attr("height", inner.h);
      hit.attr("width", S.W).attr("height", S.H);

      countries.forEach(function (c) {
        c.cons = c.series.map(function (d) { return { x: sx(d.gdpPc), y: yScale(d.consPc) }; });
        c.prod = c.series.map(function (d) { return { x: sx(d.gdpPc), y: yScale(d.prodPc) }; });
        c.consSamples = samplePolyline(c.cons, 4);
        c.prodSamples = samplePolyline(c.prod, 4);
      });

      drawAxes();
      drawGuides();
      drawContext();
      drawNotes();
      drawPaths();
      buildIndex();
      updateChrome();
      frame();
      updateEmphasis();
    }

    function drawAxes() {
      const xt = xTicks();
      const yt = yScale.ticks(5);
      const tickFont = font(400, S.tick);
      // Full dollar figures where they fit, thousands where they would touch.
      let gapMin = Infinity;
      for (let i = 1; i < xt.length; i++) { gapMin = Math.min(gapMin, sx(xt[i]) - sx(xt[i - 1])); }
      const widest = d3.max(xt, function (v) { return textWidth(money(v), tickFont); });
      const compact = widest + 14 > gapMin;
      const xText = function (v) { return compact && v >= 1000 ? "$" + v / 1000 + "k" : money(v); };

      gGrid.selectAll("line.dc-grid-x").data(xt).join("line").attr("class", "dc-grid-x")
          .attr("data-value", String)
          .attr("x1", sx).attr("x2", sx).attr("y1", 0).attr("y2", inner.h);
      gGrid.selectAll("line.dc-grid-y").data(yt).join("line")
          .attr("class", function (v) { return "dc-grid-y" + (v === 0 ? " dc-baseline" : ""); })
          .attr("data-value", String)
          .attr("x1", 0).attr("x2", inner.w).attr("y1", yScale).attr("y2", yScale);
      gAxis.selectAll("text.dc-tick-x").data(xt).join("text").attr("class", "dc-tick dc-tick-x")
          .attr("data-value", String).attr("text-anchor", "middle")
          .attr("x", sx).attr("y", inner.h + S.tick + 7).attr("font-size", S.tick).text(xText);
      gAxis.selectAll("text.dc-tick-y").data(yt).join("text").attr("class", "dc-tick dc-tick-y")
          .attr("data-value", String).attr("text-anchor", "end")
          .attr("x", -8).attr("y", yScale).attr("dy", "0.34em").attr("font-size", S.tick)
          // The top tick carries the unit, so the scale reads as tonnes at a glance.
          .text(function (v, i) { return i === yt.length - 1 ? v + " t" : String(v); });

      const titleFont = font(400, S.axisTitle);
      const scaleWord = state.scale === "log" ? "log scale" : "linear scale";
      const xName = firstThatFits([
        "GDP per capita (international-$ at 2011 prices, " + scaleWord + ")",
        "GDP per capita (int-$ at 2011 prices, " + scaleWord + ")",
        "GDP per capita (int-$, " + scaleWord + ")"], titleFont, S.W - 8);
      // Centred under the plot, or as near to that as keeps it inside the drawing.
      const half = textWidth(xName, titleFont) / 2 + 2;
      xTitle.attr("x", clamp(inner.w / 2, half - S.margin.left, inner.w + S.margin.right - half))
          .attr("y", inner.h + S.tick + S.axisTitle + 20)
          .attr("font-size", S.axisTitle).text(xName);
      yTitle.attr("x", -S.margin.left).attr("y", -S.margin.top + S.axisTitle + 2)
          .attr("font-size", S.axisTitle)
          .text(firstThatFits(state.overlay ? [
            "CO2 per capita (tonnes): consumption-based and production-based",
            "CO2 per capita (t): consumption- and production-based",
            "CO2 per capita (t), both accounts"] : [
            "Consumption-based CO2 per capita (tonnes)",
            "Consumption-based CO2 per capita (t)"], titleFont, S.W - 4));
    }

    // Each guide is the set of points with one carbon intensity: tonnes per
    // person = intensity (kg per $) x GDP per person / 1000. It is sampled in even
    // steps of the scale in use, so it is a straight ray on the linear axis and a
    // smooth curve on the log axis and during the change between the two.
    function drawGuides() {
      const lo = domain[state.scale];
      const steps = 48;
      gGuides.selectAll("path").data(GUIDES).join("path").attr("class", "dc-guide")
          .attr("data-intensity", String)
          .attr("d", function (k) {
            const points = [];
            for (let i = 0; i <= steps; i++) {
              const gdp = state.scale === "linear" ? lo[0] + (lo[1] - lo[0]) * i / steps
                : lo[0] * Math.pow(lo[1] / lo[0], i / steps);
              points.push({ x: sx(gdp), y: yScale(k * gdp / 1000) });
            }
            return line(points);
          });
    }

    function drawContext() {
      gContext.attr("display", state.context ? null : "none");
      clippedContext = 0;
      if (!state.context) {
        gContext.selectAll("path").remove();     // keeps the DOM small while it is off
        return;
      }
      const lo = domain[state.scale];
      gContext.selectAll("path").data(context, function (c) { return c.iso; }).join("path")
          .attr("class", "dc-context-path").attr("data-name", function (c) { return c.name; })
          .attr("d", function (c) {
            c.px = c.gdpPc.map(function (g, i) { return { x: sx(g), y: yScale(c.consPc[i]) }; });
            if (c.gdpPc.some(function (g, i) {
              return g < lo[0] || g > lo[1] || c.consPc[i] > domain.y[1];
            })) { clippedContext++; }
            return line(c.px);
          });
    }

    // The direction key and the year range sit in two corners that the six
    // paths never reach on either scale: top-left and bottom-right.
    function drawNotes() {
      const a = S.arrow;
      const angle = 35 * Math.PI / 180;
      const dx = a * Math.cos(angle);
      const dy = a * Math.sin(angle);
      const ox = 12;
      const oy = 12 + dy + S.note * 0.5;
      const head = 4.5;
      function arrow(sign) {
        const tx = ox + dx;
        const ty = oy + sign * dy;
        const back = Math.atan2(sign * dy, dx);
        return "M" + ox + "," + oy + "L" + tx.toFixed(1) + "," + ty.toFixed(1) +
          "M" + (tx - head * Math.cos(back - 0.5)).toFixed(1) + "," +
          (ty - head * Math.sin(back - 0.5)).toFixed(1) + "L" + tx.toFixed(1) + "," +
          ty.toFixed(1) + "L" + (tx - head * Math.cos(back + 0.5)).toFixed(1) + "," +
          (ty - head * Math.sin(back + 0.5)).toFixed(1);
      }
      compass.select(".dc-compass-up").attr("d", arrow(-1));
      compass.select(".dc-compass-down").attr("d", arrow(1));
      compass.select(".dc-compass-origin").attr("cx", ox).attr("cy", oy);
      compass.select(".dc-compass-up-text").attr("x", ox + dx + 6).attr("y", oy - dy)
          .attr("dy", "0.2em").attr("font-size", S.note);
      compass.select(".dc-compass-down-text").attr("x", ox + dx + 6).attr("y", oy + dy)
          .attr("dy", "0.5em").attr("font-size", S.note);
      const noteWidth = textWidth("richer, smaller footprint", font(400, S.note));
      const compassBox = { x0: ox - 4, x1: ox + dx + 6 + noteWidth + 4,
                           y0: oy - dy - S.note, y1: oy + dy + S.note * 1.1 };

      // Bold where it is small, so the muted tone still counts as large text.
      const rangeWeight = S.narrow ? 700 : 600;
      rangeLabel.attr("x", inner.w - 10).attr("y", inner.h - 12).attr("font-size", S.range)
          .attr("font-weight", rangeWeight);
      const rangeWidth = textWidth(yearMin + "-" + yearMax, font(rangeWeight, S.range));
      const rangeBox = { x0: inner.w - 10 - rangeWidth - 4, x1: inner.w - 6,
                         y0: inner.h - 12 - S.range * 0.85, y1: inner.h - 6 };

      // A note that would sit on a visible path is dropped rather than drawn over it.
      const blocked = function (box) {
        return countries.some(function (c) {
          return state.visible.has(c.name) && (pointsInBox(box, c.consSamples) > 0 ||
            (state.overlay && pointsInBox(box, c.prodSamples) > 0));
        });
      };
      const showCompass = !tweening && !blocked(compassBox);
      const showRange = !blocked(rangeBox);
      compass.attr("display", showCompass ? null : "none");
      rangeLabel.attr("display", showRange ? null : "none");
      obstacles = [];
      if (showCompass) { obstacles.push(compassBox); }
      if (showRange) { obstacles.push(rangeBox); }
    }

    // Direction chevrons: one candidate every few years, at the middle of that
    // year's segment and turned to the segment's angle in screen space, so the
    // arrow is right under either scale. A candidate is skipped when its
    // segment is too short to show a direction or when it would crowd a mark.
    function pickChevrons(c, taken) {
      const out = [];
      const pts = c.cons;
      const marks = anchorYears.map(function (y) { return pts[y - yearMin]; });
      const shortest = Math.max(8, S.chevron * 1.6);
      for (let i = 1; i < nYears - 1; i += opts.chevronEvery) {
        const mid = { x: (pts[i].x + pts[i + 1].x) / 2, y: (pts[i].y + pts[i + 1].y) / 2 };
        // The arrow takes the direction of its own year. Where that step is
        // only a few pixels long it takes the three years around it instead.
        let a = pts[i];
        let b = pts[i + 1];
        if (distance(a, b) < shortest) {
          a = pts[i - 1];
          b = pts[Math.min(nYears - 1, i + 2)];
        }
        if (distance(a, b) < shortest) { continue; }
        if (out.some(function (o) { return distance(o, mid) < S.chevronGap; })) { continue; }
        if (marks.some(function (m) { return distance(m, mid) < S.waypoint + S.chevron + 6; })) {
          continue;
        }
        if (taken.some(function (o) { return distance(o, mid) < S.chevron * 2.4; })) { continue; }
        out.push({ x: mid.x, y: mid.y, i: i + 0.5,
                   angle: Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI });
      }
      return out;
    }

    function drawPaths() {
      const shown = function (c) { return state.visible.has(c.name) ? null : "none"; };
      countryG.attr("display", shown);
      markerG.attr("display", shown);
      labelG.attr("display", shown);
      emptyNote.attr("display", state.visible.size ? "none" : null)
          .attr("x", inner.w / 2).attr("y", inner.h / 2).attr("font-size", S.name);

      countryG.select(".dc-ghost").attr("stroke-width", S.stroke)
          .attr("d", function (c) { return line(c.cons); });
      countryG.select(".dc-done").attr("stroke-width", S.stroke);
      countryG.selectAll(".dc-prod").attr("stroke-width", S.thin)
          .attr("display", state.overlay ? null : "none");
      countryG.select(".dc-prod-ghost")
          .attr("d", function (c) { return state.overlay ? line(c.prod) : null; });

      const taken = [];
      const s = S.chevron;
      const chevronPath = "M" + (-s) + "," + (-s) + "L0,0L" + (-s) + "," + s;
      countryG.each(function (c) {
        const g = d3.select(this);
        const visible = state.visible.has(c.name) && !tweening;
        const chevrons = visible ? pickChevrons(c, taken) : [];
        chevrons.forEach(function (o) { taken.push(o); });
        g.select(".dc-chevrons").selectAll("path").data(chevrons).join("path")
            .attr("class", "dc-chevron").attr("d", chevronPath).attr("stroke", c.color)
            .attr("stroke-width", S.stroke)
            .attr("transform", function (o) {
              return "translate(" + o.x.toFixed(2) + "," + o.y.toFixed(2) + ") rotate(" +
                o.angle.toFixed(1) + ")";
            });
        const stops = anchorYears.map(function (y) {
          const p = c.cons[y - yearMin];
          return { year: y, x: p.x, y: p.y };
        });
        const marks = g.select(".dc-waypoints").selectAll("g").data(stops).join(function (enter) {
          const m = enter.append("g").attr("class", "dc-waypoint");
          m.append("circle").attr("class", "dc-waypoint-ring");
          m.append("circle").attr("class", "dc-waypoint-dot");
          return m;
        });
        marks.attr("data-year", function (o) { return o.year; })
            .attr("transform", function (o) {
              return "translate(" + o.x.toFixed(2) + "," + o.y.toFixed(2) + ")";
            });
        marks.select(".dc-waypoint-ring").attr("r", S.waypoint + 3);
        marks.select(".dc-waypoint-dot").attr("r", S.waypoint).attr("stroke", c.color);
      });

      markerG.select(".dc-now").attr("r", S.marker + 1);
      markerG.select(".dc-prod-now").attr("r", S.waypoint);
      placeYearLabels();
    }

    // Year labels are placed once per layout, not once per frame, so they hold
    // still while the year is scrubbed. First and last years go first; a label
    // with no clear slot is left out, and the legend key says what the hollow
    // marks are.
    function placeYearLabels() {
      yearLabels = [];
      countries.forEach(function (c) { c.labelled = new Set(); });
      if (tweening) { gYearLabels.selectAll("text").remove(); return; }
      const fs = S.yearLabel;
      const labelFont = font(400, fs);
      const visible = countries.filter(function (c) { return state.visible.has(c.name); });
      const marks = [];
      visible.forEach(function (c) {
        anchorYears.forEach(function (y) {
          const p = c.cons[y - yearMin];
          marks.push({ c: c, year: y, x: p.x, y: p.y, r: S.waypoint + 3 });
        });
      });
      const order = [6, 7, 1, 4, 2, 5, 0, 3];     // N, S, NE, NW, SE, SW, E, W
      const rank = function (y) { return y === yearMin ? 0 : y === yearMax ? 1 : 2; };
      // A label is read as belonging to the nearest mark on show. `near` says
      // whether mark o is close enough to a label at `centre` to be taken for
      // the label's own mark, which is `own` px away. Start years get less
      // margin: three of the six paths start within 60 px of each other.
      const near = function (centre, own, o, slack) {
        return distance(centre, o) < own * slack + 2;
      };
      marks.slice().sort(function (a, b) { return rank(a.year) - rank(b.year); })
        .forEach(function (m) {
          // Dating this point must not make an earlier label ambiguous.
          if (m.year !== yearMin && yearLabels.some(function (o) {
            return near(o.centre, o.own, m, 1.25);
          })) { return; }
          const text = String(m.year);
          const w = textWidth(text, labelFont);
          const slots = slotsAround(m, S.waypoint + 2, fs, 0);
          let best = null;
          order.forEach(function (slotIndex, preference) {
            const slot = slots[slotIndex];
            const box = labelBox(slot.x, slot.y, w, fs, slot.anchor);
            if (box.x0 < 2 || box.x1 > inner.w + S.margin.right - 2 ||
                box.y0 < 2 || box.y1 > inner.h - 2) { return; }
            const wide = grow(box, 1.5);
            const centre = { x: (box.x0 + box.x1) / 2, y: (box.y0 + box.y1) / 2 };
            const own = distance(centre, m);
            let cost = preference * 2;
            visible.forEach(function (c) {
              cost += 10 * pointsInBox(wide, c.consSamples);
              if (state.overlay) { cost += 6 * pointsInBox(wide, c.prodSamples); }
            });
            marks.forEach(function (o) {
              if (o === m) { return; }
              if (boxHitsCircle(wide, o)) { cost += 200; }
              const drawn = o.year === yearMin || o.c.labelled.has(o.year);
              if (drawn && near(centre, own, o, m.year === yearMin ? 1 : 1.25)) { cost += 300; }
            });
            // Two years side by side read as one number, so along the line a
            // label keeps a wider gap from its neighbours than above or below.
            const reach = { x0: wide.x0 - 8, x1: wide.x1 + 8, y0: wide.y0, y1: wide.y1 };
            yearLabels.forEach(function (o) { if (boxesOverlap(reach, o.box)) { cost += 1000; } });
            obstacles.forEach(function (o) { if (boxesOverlap(wide, o)) { cost += 1000; } });
            if (!best || cost < best.cost) {
              best = { cost: cost, slot: slot, box: box, centre: centre, own: own };
            }
          });
          // A middle year needs a slot with nothing under it; the two ends may
          // touch a line, because a path with no dated end is hard to read.
          if (best && best.cost < (rank(m.year) < 2 ? 50 : S.narrow ? 16 : 24)) {
            m.c.labelled.add(m.year);
            yearLabels.push({ c: m.c, year: m.year, text: text, x: best.slot.x, y: best.slot.y,
                              anchor: best.slot.anchor, box: best.box, centre: best.centre,
                              own: best.own });
          }
        });
      gYearLabels.selectAll("text").data(yearLabels).join("text")
          .attr("class", "dc-year-label dc-halo")
          .attr("data-name", function (o) { return o.c.name; })
          .attr("x", function (o) { return o.x; }).attr("y", function (o) { return o.y; })
          .attr("dy", "0.35em").attr("font-size", fs)
          .attr("text-anchor", function (o) { return o.anchor; })
          .text(function (o) { return o.text; });
    }

    function buildIndex() {
      focusPoints = [];
      countries.forEach(function (c) {
        if (!state.visible.has(c.name)) { return; }
        c.cons.forEach(function (p, i) {
          focusPoints.push({ c: c, index: i, kind: "cons", x: p.x, y: p.y });
        });
        if (state.overlay) {
          c.prod.forEach(function (p, i) {
            focusPoints.push({ c: c, index: i, kind: "prod", x: p.x, y: p.y });
          });
        }
      });
      const px = function (p) { return p.x; };
      const py = function (p) { return p.y; };
      focusIndex = focusPoints.length ? d3.Delaunay.from(focusPoints, px, py) : null;
      contextPoints = [];
      if (state.context) {
        context.forEach(function (c) {
          c.px.forEach(function (p) {
            if (p.x >= 0 && p.x <= inner.w && p.y >= 0 && p.y <= inner.h) {
              contextPoints.push({ context: c, x: p.x, y: p.y });
            }
          });
        });
      }
      contextIndex = contextPoints.length ? d3.Delaunay.from(contextPoints, px, py) : null;
    }

    function updateChrome() {
      legendItems.attr("aria-pressed", function (c) { return String(state.visible.has(c.name)); });
      resetButton.property("hidden", state.visible.size === countries.length);
      overlayKeys.forEach(function (item) { item.property("hidden", !state.overlay); });
      let text = opts.note || "Source: " + meta.source +
                              ". GDP in international-$ at 2011 prices.";
      if (state.context) {
        text += " Grey lines: the other " + context.length + " countries with a complete " +
                yearMin + "-" + yearMax + " series; " + clippedContext +
                " of them leave the plotted range and are cut at the frame.";
      }
      note.text(text);
    }

    // ---------------------------------------------------------- per-frame drawing
    function pointAt(points, fi) {
      const i = Math.min(Math.floor(fi + 1e-9), nYears - 1);
      const f = fi - i;
      if (f < 1e-6 || i >= nYears - 1) { return points[i]; }
      const a = points[i];
      const b = points[i + 1];
      return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f };
    }

    function pathUpTo(points, fi) {
      const i = Math.min(Math.floor(fi + 1e-9), nYears - 1);
      const head = points.slice(0, i + 1);
      if (fi - i > 1e-6 && i < nYears - 1) { head.push(pointAt(points, fi)); }
      return head.length > 1 ? line(head) : null;
    }

    function frame() {
      const fi = state.t - yearMin;
      const visible = countries.filter(function (c) { return state.visible.has(c.name); });
      visible.forEach(function (c) {
        c.now = pointAt(c.cons, fi);
        c.nowProd = pointAt(c.prod, fi);
      });

      countryG.select(".dc-done").attr("d", function (c) { return pathUpTo(c.cons, fi); });
      if (state.overlay) {
        countryG.select(".dc-prod-done").attr("d", function (c) { return pathUpTo(c.prod, fi); });
      }
      countryG.selectAll(".dc-chevron").classed("is-ahead", function (o) { return o.i > fi; });
      // A hollow mark is drawn where its year label found room, and always at
      // the start; an undated dot on the line would only be noise. The mark
      // under the filled marker is hidden rather than left to peek out.
      countryG.each(function (c) {
        d3.select(this).selectAll(".dc-waypoint")
            .classed("is-ahead", function (o) { return o.year - yearMin > fi + 1e-6; })
            .attr("display", function (o) {
              const dated = o.year === yearMin || (c.labelled && c.labelled.has(o.year));
              return !dated || Math.abs(o.year - yearMin - fi) < 0.35 ? "none" : null;
            });
      });

      const ring = S.marker + 2;                 // disc plus its 2 px surface ring
      markerG.filter(function (c) { return state.visible.has(c.name); }).each(function (c) {
        const g = d3.select(this);
        g.select(".dc-now").attr("cx", c.now.x).attr("cy", c.now.y);
        const top = Math.min(c.now.y, c.nowProd.y);
        const bottom = Math.max(c.now.y, c.nowProd.y);
        const consOnTop = c.now.y <= c.nowProd.y;
        const y1 = top + (consOnTop ? ring : S.waypoint + 2);
        const y2 = bottom - (consOnTop ? S.waypoint + 2 : ring);
        g.select(".dc-prod-now").attr("display", state.overlay ? null : "none")
            .attr("cx", c.nowProd.x).attr("cy", c.nowProd.y);
        g.select(".dc-gap").attr("display", state.overlay && y2 - y1 > 1.5 ? null : "none")
            .attr("x1", c.now.x).attr("x2", c.now.x).attr("y1", y1).attr("y2", y2);
      });

      placeLabels(visible, fi);
      rangeLabel.text(state.year === yearMin ? String(yearMin) : yearMin + "-" + state.year);
    }

    // A year label steps aside while the marker is at its year: the marker's
    // own label says the year then, and on a narrow chart the year range in the
    // corner does.
    function stepsAside(label, fi) {
      return label.year === state.year || Math.abs(label.year - yearMin - fi) < 0.35;
    }

    // Country names and gap labels move with the scrubbed year, so they are
    // placed on every frame: each tries the slots around its mark and takes the
    // one that covers the least ink, with a small bonus for the slot it had on
    // the frame before so that it does not flicker between two equal places.
    function placeLabels(visible, fi) {
      const nameFont = font(600, S.name);
      const yearText = S.narrow ? "" : String(state.year);
      const yearRoom = yearText ? 5 + textWidth(yearText, font(400, S.yearLabel)) : 0;
      const gapSize = S.yearLabel + 0.5;
      const gapFont = font(600, gapSize);
      const ring = S.marker + 2;
      // A label may reach into the right margin, and a few pixels past the
      // baseline for a country close to zero; the tick labels start lower down.
      const bounds = { x0: 2, x1: inner.w + S.margin.right - 2, y0: 2, y1: inner.h + 3 };
      const circles = [];
      visible.forEach(function (c) {
        circles.push({ x: c.now.x, y: c.now.y, r: ring, c: c });
        if (state.overlay) {
          circles.push({ x: c.nowProd.x, y: c.nowProd.y, r: S.waypoint + 2, c: c });
        }
      });
      const connectors = !state.overlay ? [] : visible.map(function (c) {
        return { x0: c.now.x - 2, x1: c.now.x + 2, y0: Math.min(c.now.y, c.nowProd.y),
                 y1: Math.max(c.now.y, c.nowProd.y), c: c };
      });
      const placed = [];        // boxes of labels already placed this frame
      const ON_A_LABEL = 1e5;   // the one cost no slot may carry: text on top of text
      const BLOCKED = 1500;     // from here up a slot covers a marker, a connector or a note

      // What it costs to put a label in `box`. `spec` says whose label it is
      // (owner), how far down its list of slots this one is (preference),
      // whether it had this slot on the last frame (kept), where its leader
      // starts if it has one (leaderFrom), and what a crowded neighbourhood
      // costs it per sample of line (crowd).
      function cost(box, spec) {
        if (box.x0 < bounds.x0 || box.x1 > bounds.x1 || box.y0 < bounds.y0 ||
            box.y1 > bounds.y1) { return Infinity; }
        const wide = grow(box, 2);
        // Two labels side by side on one line read as one phrase, so another
        // label has to be clear by more along the line than above or below.
        const reach = { x0: box.x0 - 12, x1: box.x1 + 12, y0: wide.y0, y1: wide.y1 };
        let total = spec.preference * 4 - (spec.kept ? 30 : 0);
        placed.forEach(function (o) {
          if (o.owner !== spec.owner && boxesOverlap(reach, o.box)) { total += ON_A_LABEL; }
        });
        obstacles.forEach(function (o) { if (boxesOverlap(wide, o)) { total += 3000; } });
        circles.forEach(function (o) { if (boxHitsCircle(wide, o)) { total += 2500; } });
        connectors.forEach(function (o) { if (boxesOverlap(wide, o)) { total += 1500; } });
        // A leader that runs through or close past another country's marker
        // would seem to point at that one.
        if (spec.leaderFrom) {
          const from = spec.leaderFrom;
          const to = { x: clamp(from.x, box.x0, box.x1), y: clamp(from.y, box.y0, box.y1) };
          circles.forEach(function (o) {
            if (o.c.name + "name" !== spec.owner && distanceToSegment(o, from, to) < o.r + 8) {
              total += 2000;
            }
          });
        }
        // Ink under the label costs most; ink close around a name costs a little,
        // which steers it out of a tangle and into open space.
        const around = grow(box, 12);
        visible.forEach(function (c) {
          for (let i = 0; i < c.consSamples.length; i++) {
            const p = c.consSamples[i];
            if (p.x > around.x0 && p.x < around.x1 && p.y > around.y0 && p.y < around.y1) {
              total += spec.crowd;
              if (p.x > wide.x0 && p.x < wide.x1 && p.y > wide.y0 && p.y < wide.y1) {
                total += p.i <= fi ? 50 : 14;
              }
            }
          }
          if (state.overlay) { total += 10 * pointsInBox(wide, c.prodSamples); }
        });
        // Landing on or right beside a year label hides that label, which costs a
        // little. Year labels about to step aside for a marker are not in the way.
        yearLabels.forEach(function (o) {
          if (!stepsAside(o, fi) && boxesOverlap(reach, o.box)) { total += 60; }
        });
        return total;
      }

      function choose(c, slots, w, fs, slotKey, kind) {
        let best = null;
        slots.forEach(function (slot, i) {
          const box = labelBox(slot.x, slot.y, w, fs, slot.anchor);
          const total = cost(box, {
            owner: c.name + kind, preference: i, kept: c[slotKey] === i,
            leaderFrom: kind === "name" && i >= 8 ? c.now : null,
            crowd: kind === "name" ? 2 : 0
          });
          if (total < Infinity && (!best || total < best.total)) {
            best = { total: total, slot: slot, box: box, index: i };
          }
        });
        return best;
      }

      // Gap labels go first. With the overlay on they are what the chart is
      // for, and a name has far more places it can go than a gap label has.
      visible.forEach(function (c) {
        c.gapPlace = null;
        if (!state.overlay) { return; }
        const d = c.series[state.year - yearMin];
        const text = signedTonnes(netBalance(d));
        const w = textWidth(text, gapFont);
        const mid = { x: c.now.x, y: (c.now.y + c.nowProd.y) / 2 };
        const slots = slotsAround(mid, 3, gapSize, 0)
            .concat(slotsAround(c.nowProd, S.waypoint + 2, gapSize, 0));
        const best = choose(c, slots, w, gapSize, "gapSlot", "gap");
        // A gap label may touch a line (it has a halo), but one that could only go
        // along a line, or on a marker or another label, is left to the tooltip
        // and the table, which carry the same number.
        if (best && best.total < 320) {
          c.gapPlace = best;
          c.gapSlot = best.index;
          c.gapText = text;
          placed.push({ owner: c.name + "gap", box: best.box });
        }
      });

      // Two passes: the second lets each name move once it knows where the rest went.
      for (let pass = 0; pass < 2; pass++) {
        visible.forEach(function (c) {
          const w = textWidth(S.narrow ? c.short : c.name, nameFont) + yearRoom;
          // Eight slots against the marker, then eight a little further out on a
          // short leader: near enough that the leader cannot cross another path.
          let slots = slotsAround(c.now, ring, S.name, 0)
              .concat(slotsAround(c.now, ring, S.name, 14));
          for (let i = placed.length - 1; i >= 0; i--) {
            if (placed[i].owner === c.name + "name") { placed.splice(i, 1); }
          }
          let best = choose(c, slots, w, S.name, "nameSlot", "name");
          // Where every one of those would cover a marker, a connector or a
          // label (two countries a few pixels apart), two wider rings are tried.
          if (!best || best.total >= BLOCKED) {
            slots = slots.concat(slotsAround(c.now, ring, S.name, 30),
                                 slotsAround(c.now, ring, S.name, 46));
            best = choose(c, slots, w, S.name, "nameSlot", "name");
          }
          // A name that could still only go on top of another is left out; the
          // legend and the tooltip still say it.
          if (best && best.total >= ON_A_LABEL) { best = null; }
          c.namePlace = best;
          if (best) {
            placed.push({ owner: c.name + "name", box: best.box });
            if (pass === 1) { c.nameSlot = best.index; }
          }
        });
      }
      labelG.filter(function (c) { return state.visible.has(c.name); }).each(function (c) {
        const g = d3.select(this);
        const p = c.namePlace;
        g.select(".dc-name").attr("display", p ? null : "none");
        g.select(".dc-leader").attr("display", p && p.index >= 8 ? null : "none");
        if (p) {
          g.select(".dc-name").attr("x", p.slot.x).attr("y", p.slot.y).attr("dy", "0.35em")
              .attr("text-anchor", p.slot.anchor).attr("font-size", S.name);
          g.select(".dc-name-country").text(S.narrow ? c.short : c.name);
          g.select(".dc-name-year").attr("font-size", S.yearLabel).text(yearText);
          if (p.index >= 8) {
            // The leader runs from the edge of the marker to the nearest point of the text.
            const tx = clamp(c.now.x, p.box.x0, p.box.x1);
            const ty = clamp(c.now.y, p.box.y0, p.box.y1);
            const len = Math.hypot(tx - c.now.x, ty - c.now.y) || 1;
            g.select(".dc-leader")
                .attr("x1", c.now.x + (tx - c.now.x) * ring / len)
                .attr("y1", c.now.y + (ty - c.now.y) * ring / len)
                .attr("x2", tx).attr("y2", ty);
          }
        }
        const gap = c.gapPlace;
        g.select(".dc-gap-label").attr("display", gap ? null : "none");
        if (gap) {
          g.select(".dc-gap-label").attr("x", gap.slot.x).attr("y", gap.slot.y)
              .attr("dy", "0.35em").attr("text-anchor", gap.slot.anchor)
              .attr("font-size", gapSize).text(c.gapText);
        }
      });

      // A year label gives way to anything that moves on top of it, and to a
      // name or gap label that lands right beside it on the same line.
      gYearLabels.selectAll("text")
          .classed("is-ahead", function (o) { return o.year - yearMin > fi + 1e-6; })
          .attr("display", function (o) {
            const wide = grow(o.box, 1);
            const beside = { x0: o.box.x0 - 12, x1: o.box.x1 + 12, y0: wide.y0, y1: wide.y1 };
            if (stepsAside(o, fi)) { return "none"; }
            const covered = placed.some(function (p) { return boxesOverlap(beside, p.box); }) ||
              circles.some(function (p) { return boxHitsCircle(wide, p); }) ||
              connectors.some(function (p) { return boxesOverlap(wide, p); });
            return covered ? "none" : null;
          });
    }

    // ---------------------------------------------------------- emphasis, hover, keyboard
    function emphasised() {
      if (state.hover && state.hover.name) { return new Set([state.hover.name]); }
      if (transient && state.visible.has(transient)) { return new Set([transient]); }
      return state.highlight;
    }

    function updateEmphasis() {
      const set = emphasised();
      const dim = function (c) { return !!set && !set.has(c.name); };
      const strong = function (c) { return !!set && set.has(c.name) && set.size === 1; };
      countryG.classed("is-dim", dim).classed("is-emph", strong);
      markerG.classed("is-dim", dim);
      labelG.classed("is-dim", dim);
      gYearLabels.selectAll("text").classed("is-dim", function (o) { return dim(o.c); });
      countryG.select(".dc-done").attr("stroke-width", function (c) {
        return S.stroke + (strong(c) ? 0.75 : 0);
      });
      gContext.classed("is-dim", !!set);
    }

    function nearest(mx, my) {
      let focus = null;
      let grey = null;
      if (focusIndex) {
        const p = focusPoints[focusIndex.find(mx, my)];
        focus = { p: p, d: Math.hypot(p.x - mx, p.y - my) };
      }
      if (contextIndex) {
        const p = contextPoints[contextIndex.find(mx, my)];
        grey = { p: p, d: Math.hypot(p.x - mx, p.y - my) };
      }
      // A focus point wins unless the pointer is clearly on a grey path instead.
      if (focus && focus.d <= opts.hoverRadius * 0.45) { return focus.p; }
      if (grey && grey.d <= opts.contextRadius && (!focus || grey.d < focus.d)) { return grey.p; }
      return focus && focus.d <= opts.hoverRadius ? focus.p : null;
    }

    // The readout goes in whichever corner around the point hides the least:
    // never the point itself, then as little as possible of the path being
    // read and of its labels, then of the other countries' names.
    function placeTooltip(px, py, samples, ownLabels, otherLabels) {
      const node = tooltip.node();
      const k = svg.node().clientWidth / S.W || 1;
      const x = (S.margin.left + px) * k;
      const y = (S.margin.top + py) * k;
      const w = node.offsetWidth;
      const h = node.offsetHeight;
      const roomX = Math.max(4, stage.node().clientWidth - w - 4);
      const roomY = Math.max(4, stage.node().clientHeight - h - 4);
      const pad = 16;
      const lift = 30;          // enough to clear a name label sitting above or below
      let best = null;
      [[x + pad, y - h - pad], [x - pad - w, y - h - pad], [x + pad, y + pad],
       [x - pad - w, y + pad], [x - w / 2, y - h - pad], [x - w / 2, y + pad],
       [x + pad, y - h - pad - lift], [x - pad - w, y - h - pad - lift],
       [x + pad, y + pad + lift], [x - pad - w, y + pad + lift]]
        .forEach(function (corner, i) {
          const left = clamp(corner[0], 4, roomX);
          const top = clamp(corner[1], 4, roomY);
          const onPoint = x > left - 8 && x < left + w + 8 && y > top - 8 && y < top + h + 8;
          const box = { x0: left / k - S.margin.left, x1: (left + w) / k - S.margin.left,
                        y0: top / k - S.margin.top, y1: (top + h) / k - S.margin.top };
          const hits = function (boxes) {
            return (boxes || []).filter(function (b) { return boxesOverlap(box, b); }).length;
          };
          const score = (onPoint ? 1e6 : 0) + 10 * pointsInBox(box, samples || []) +
            200 * hits(ownLabels) + 8 * hits(otherLabels) + i;
          if (!best || score < best.score) { best = { score: score, left: left, top: top }; }
        });
      tooltip.style("left", Math.round(best.left) + "px")
          .style("top", Math.round(best.top) + "px");
    }

    function showDetail(c, index, kind, source) {
      const d = c.series[index];
      const main = (kind === "prod" ? c.prod : c.cons)[index];
      const twin = (kind === "prod" ? c.cons : c.prod)[index];
      state.hover = { name: c.name, index: index, year: d.year, kind: kind || "cons" };
      gContext.selectAll(".is-hover").classed("is-hover", false);

      gHover.attr("display", null);
      gHover.select(".dc-hover-dot").attr("cx", main.x).attr("cy", main.y).attr("r", S.marker)
          .attr("fill", c.color);
      gHover.select(".dc-hover-ring").attr("cx", main.x).attr("cy", main.y).attr("r", S.marker + 4);
      const twinOn = state.overlay;
      gHover.select(".dc-hover-twin").attr("display", twinOn ? null : "none")
          .attr("cx", twin.x).attr("cy", twin.y).attr("r", S.waypoint).attr("stroke", c.color);
      gHover.select(".dc-hover-gap").attr("display", twinOn ? null : "none")
          .attr("x1", main.x).attr("x2", twin.x).attr("y1", main.y).attr("y2", twin.y);

      tooltip.property("hidden", false).classed("is-context", false);
      ttKey.style("background", c.color);
      ttCountry.text(c.name);
      ttYear.text(d.year);
      ttRow.gdp.value.text(money(d.gdpPc));
      ttRow.cons.value.text(tonnes(d.consPc));
      ttRow.prod.value.text(tonnes(d.prodPc));
      ttRow.net.value.text(signedTonnes(netBalance(d)));
      ttRow.net.label.text("net balance (" + tradeRole(netBalance(d)) + ")");
      const boxOf = function (place) { return place.box; };
      placeTooltip(main.x, main.y,
                   state.overlay ? c.consSamples.concat(c.prodSamples) : c.consSamples,
                   [c.namePlace, c.gapPlace].filter(Boolean).map(boxOf),
                   countries.filter(function (o) {
                     return o !== c && state.visible.has(o.name) && o.namePlace;
                   }).map(function (o) { return o.namePlace.box; }));
      updateEmphasis();
      if (source === "keyboard") {
        live.text(c.name + ", " + d.year + ". GDP per capita " + money(d.gdpPc) +
                  ". Consumption-based CO2 " + tonnes(d.consPc) + ". Production-based CO2 " +
                  tonnes(d.prodPc) + ". Net balance " + signedTonnes(netBalance(d)) +
                  ", " + tradeRole(netBalance(d)) + ".");
      }
      dispatch.call("hover", api, state.hover);
    }

    function showContext(p) {
      state.hover = { context: p.context.name };
      gHover.attr("display", "none");
      gContext.selectAll("path").classed("is-hover", function (c) { return c === p.context; });
      tooltip.property("hidden", false).classed("is-context", true);
      ttKey.style("background", null);
      ttCountry.text(p.context.name);
      ttYear.text("");
      placeTooltip(p.x, p.y);
      updateEmphasis();
      dispatch.call("hover", api, state.hover);
    }

    function hideDetail() {
      if (!state.hover) { return; }
      state.hover = null;
      gHover.attr("display", "none");
      gContext.selectAll(".is-hover").classed("is-hover", false);
      tooltip.property("hidden", true);
      updateEmphasis();
      dispatch.call("hover", api, null);
    }

    function onPointer(event) {
      const m = d3.pointer(event, gPlot.node());
      const found = nearest(m[0], m[1]);
      if (!found) { hideDetail(); return; }
      if (found.context) {
        if (!state.hover || state.hover.context !== found.context.name) { showContext(found); }
        return;
      }
      const h = state.hover;
      if (!h || h.name !== found.c.name || h.index !== found.index || h.kind !== found.kind) {
        showDetail(found.c, found.index, found.kind, "pointer");
      }
    }

    function onKey(event) {
      const visible = countries.filter(function (c) { return state.visible.has(c.name); });
      if (!visible.length) { return; }
      if (event.key === "Escape") { hideDetail(); return; }
      if (!cursor || !state.visible.has(cursor.name)) {
        cursor = { name: visible[0].name, index: state.year - yearMin };
      }
      let ci = visible.findIndex(function (c) { return c.name === cursor.name; });
      let i = cursor.index;
      if (event.key === "ArrowRight") { i = Math.min(nYears - 1, i + 1); }
      else if (event.key === "ArrowLeft") { i = Math.max(0, i - 1); }
      else if (event.key === "ArrowDown") { ci = (ci + 1) % visible.length; }
      else if (event.key === "ArrowUp") { ci = (ci - 1 + visible.length) % visible.length; }
      else if (event.key === "Home") { i = 0; }
      else if (event.key === "End") { i = nYears - 1; }
      else { return; }
      event.preventDefault();
      cursor = { name: visible[ci].name, index: i };
      showDetail(visible[ci], i, "cons", "keyboard");
    }

    hit.on("pointermove pointerdown", onPointer)
       .on("pointerleave", function (event) {
         // A finger has no hover: its readout stays until the next tap.
         if (event.pointerType !== "touch") { hideDetail(); }
       });
    svg.on("keydown", onKey)
       .on("focus", function () {
         // Only for keyboard focus: a mouse click also focuses the plot, and the
         // pointer already says which point is wanted.
         if (!svg.node().matches(":focus-visible")) { return; }
         const visible = countries.filter(function (c) { return state.visible.has(c.name); });
         if (!visible.length) { return; }
         // Start at the scrubbed year, on the country the keys were last on.
         const kept = cursor && state.visible.has(cursor.name) ? cursor.name : visible[0].name;
         cursor = { name: kept, index: state.year - yearMin };
         showDetail(byName.get(kept), cursor.index, "cons", "keyboard");
       })
       .on("blur", hideDetail);

    // ---------------------------------------------------------- state changes
    function emit(reason) { dispatch.call("change", api, getState(), reason); }

    function stopPlay() {
      if (playTimer) { playTimer.stop(); playTimer = null; }
      state.playing = false;
    }

    function setYear(year, reason) {
      const y = clampYear(year);
      const wasPlaying = state.playing;
      stopPlay();
      if (y === state.year && state.t === y && !wasPlaying) { return api; }
      state.year = y;
      state.t = y;
      frame();
      emit(reason || "year");
      return api;
    }

    function play(range) {
      const to = clampYear(range && range.to != null ? range.to : yearMax);
      stopPlay();
      if (range && range.from != null) {
        state.year = clampYear(range.from);
      } else if (state.year >= to) {
        state.year = yearMin;
      }
      state.t = state.year;
      if (state.year >= to) { frame(); emit("year"); return api; }
      state.playing = true;
      frame();
      emit("play");
      const finish = function () {
        stopPlay();
        state.year = to;
        state.t = to;
        frame();
        emit("pause");
      };
      if (motionQuery.matches) {
        // Reduced motion: one whole year at a time, at a calm pace, no tweening.
        playTimer = d3.interval(function () {
          if (state.year + 1 >= to) { finish(); return; }
          state.year += 1;
          state.t = state.year;
          frame();
          emit("year");
        }, opts.msPerStep);
        return api;
      }
      const from = state.t;
      playTimer = d3.timer(function (elapsed) {
        const t = from + elapsed / opts.msPerYear;
        if (t >= to) { finish(); return; }
        state.t = t;
        const year = Math.floor(t + 1e-9);
        const stepped = year !== state.year;
        state.year = year;
        frame();
        if (stepped) { emit("year"); }
      });
      return api;
    }

    function pause() {
      if (!state.playing) { return api; }
      stopPlay();
      state.year = clampYear(state.t);
      state.t = state.year;
      frame();
      emit("pause");
      return api;
    }

    function setScale(type, immediate) {
      const next = type === "linear" ? "linear" : "log";
      if (next === state.scale) { return api; }
      state.scale = next;
      hideDetail();
      if (scaleTimer) { scaleTimer.stop(); scaleTimer = null; }
      const target = next === "linear" ? 1 : 0;
      if (immediate || motionQuery.matches) {
        state.blend = target;
        tweening = false;
        layout();
        emit("scale");
        return api;
      }
      // The points travel from one scale to the other so the eye can follow
      // each country; chevrons and year labels are redrawn when they arrive.
      const from = state.blend;
      const ease = d3.easeCubicInOut;
      tweening = true;
      emit("scale");
      scaleTimer = d3.timer(function (elapsed) {
        const u = Math.min(1, elapsed / 650);
        state.blend = from + (target - from) * ease(u);
        if (u >= 1) {
          scaleTimer.stop();
          scaleTimer = null;
          state.blend = target;
          tweening = false;
        }
        layout();
      });
      return api;
    }

    function setOverlay(on) {
      if (!!on === state.overlay) { return api; }
      state.overlay = !!on;
      hideDetail();
      layout();
      emit("overlay");
      return api;
    }

    function setContext(on) {
      if (!!on === state.context) { return api; }
      state.context = !!on;
      hideDetail();
      layout();
      emit("context");
      return api;
    }

    function setVisible(names) {
      state.visible = names == null ? new Set(countries.map(function (c) { return c.name; }))
                                    : resolveNames(names);
      hideDetail();
      layout();
      updateEmphasis();
      emit("visible");
      return api;
    }

    function toggle(name, on) {
      const c = byName.get(name);
      if (!c) { return api; }
      const next = new Set(state.visible);
      const show = on == null ? !next.has(name) : !!on;
      if (show) { next.add(name); } else { next.delete(name); }
      return setVisible(Array.from(next));
    }

    function highlight(names) {
      const set = names == null ? null : resolveNames(names);
      state.highlight = set && set.size ? set : null;
      updateEmphasis();
      emit("highlight");
      return api;
    }

    function setHeight(height) {
      const next = height ? Math.round(height) : null;
      if (next === heightOverride) { return api; }
      heightOverride = next;
      hideDetail();
      layout();
      return api;
    }

    function getState() {
      const inOrder = function (set) {
        return countries.filter(function (c) { return set.has(c.name); })
          .map(function (c) { return c.name; });
      };
      return {
        year: state.year, yearMin: yearMin, yearMax: yearMax, scale: state.scale,
        overlay: state.overlay, context: state.context, playing: state.playing,
        transitioning: tweening, hoverRadius: opts.hoverRadius,
        visible: inOrder(state.visible),
        highlight: state.highlight ? inOrder(state.highlight) : null,
        hover: state.hover ? Object.assign({}, state.hover) : null,
        width: S ? S.W : 0, height: S ? S.H : 0,
        plot: S ? { x: S.margin.left, y: S.margin.top, width: inner.w, height: inner.h } : null,
        domain: { x: domain[state.scale].slice(), y: domain.y.slice() }
      };
    }

    const api = {
      setYear: function (year) { return setYear(year); },
      setScale: setScale,
      setOverlay: setOverlay,
      setContext: setContext,
      setVisible: setVisible,
      toggle: toggle,
      highlight: highlight,
      setHeight: setHeight,
      play: play,
      pause: pause,
      showDetail: function (name, year) {
        const c = byName.get(name);
        if (c && state.visible.has(name)) {
          cursor = { name: name, index: clampYear(year) - yearMin };
          showDetail(c, cursor.index, "cons", "keyboard");
        }
        return api;
      },
      hideDetail: function () { hideDetail(); return api; },
      getState: getState,
      on: function (type, handler) { dispatch.on(type, handler); return api; },
      resize: function () { layout(); return api; },
      destroy: function () {
        stopPlay();
        if (scaleTimer) { scaleTimer.stop(); }
        if (observer) { observer.disconnect(); }
        root.selectAll("*").remove();
      },
      node: svg.node()
    };

    // Re-lay out when the container changes width. The viewBox is reset to the
    // new size, so text and marks stay at their intended pixel sizes instead
    // of shrinking with the drawing.
    let observer = null;
    if (global.ResizeObserver) {
      observer = new global.ResizeObserver(function () {
        const w = Math.floor(stage.node().clientWidth);
        if (w > 0 && S && Math.abs(Math.max(280, w) - S.W) >= 1) { hideDetail(); layout(); }
      });
      observer.observe(stage.node());
    }

    layout();
    updateEmphasis();
    return api;
  }

  global.DecouplingChart = {
    create: create,
    netBalance: netBalance,
    format: { money: money, tonnes: tonnes, signedTonnes: signedTonnes, tradeRole: tradeRole,
              countWord: countWord }
  };
})(window);
