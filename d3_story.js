/*
 * d3_story.js -- page wiring for Visualization 2.
 *
 * Finds every element marked data-decoupling-app and builds, around a chart
 * from d3_vis.js: the story-step buttons with their caption, one row of
 * controls (play, year slider, x-scale, two checkboxes) and the table view.
 * Controls drive the chart; the chart's "change" event drives the readouts,
 * the table and the URL, so the pieces cannot disagree.
 *
 * URL parameters set the first state and are rewritten as the state changes,
 * which makes any view shareable and lets the capture script ask for one:
 *
 *     ?year=2007&x=log&overlay=1&context=1&only=United%20Kingdom,China&step=2
 *
 * Every number in a caption, and every element marked data-fact on the page,
 * is computed here from DECOUPLING_DATA when the page loads. Nothing is typed
 * in from memory, so the words cannot drift away from the chart.
 *
 * Load order: vendor/d3.v7.min.js, data/decoupling_data.js, d3_vis.js, then
 * this file. No network request is made.
 */
(function (global) {
  "use strict";

  const document = global.document;

  // The year the story turns on: the last one before the financial crisis.
  // Same value as PIVOT_YEAR in scripts/common.py.
  const PIVOT_YEAR = 2007;
  const HINT = "Pick a step for a guided reading, or use the controls to explore.";
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
                  "September", "October", "November", "December"];
  const PLAY_ICON = "M2,1L11,6L2,11Z";
  const PAUSE_ICON = "M2,1h3v10h-3ZM7,1h3v10h-3Z";
  const FIT_MIN_HEIGHT = 420;     // the plot is never squeezed below this to fit a frame
  const SOURCE_NOTE = "Source: Our World in Data CO2 dataset (Global Carbon Budget 2025; " +
                      "Maddison Project Database 2023). GDP in international-$ at 2011 prices.";
  let counter = 0;

  // ------------------------------------------------------------ small helpers
  // Elements are built node by node and text goes in through textContent, so
  // nothing from the data file is ever parsed as markup.
  function h(tag, attrs, children) {
    const node = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (name) {
      if (name === "text") { node.textContent = attrs[name]; }
      else if (name === "class") { node.className = attrs[name]; }
      else { node.setAttribute(name, attrs[name]); }
    });
    (children || []).forEach(function (child) { node.appendChild(child); });
    return node;
  }

  function percent(v) {
    const r = Math.round(Math.abs(v));
    return (r === 0 ? "" : v > 0 ? "+" : "-") + r + "%";
  }

  function percentAbs(v) { return Math.round(Math.abs(v)) + "%"; }

  function oneDecimal(v) { return v.toFixed(1) + " t"; }

  function listOf(items) {
    if (items.length < 2) { return items.join(""); }
    return items.slice(0, -1).join(", ") + " and " + items[items.length - 1];
  }

  function the(name) { return /^United /.test(name) ? "the " + name : name; }

  function countWord(n) { return global.DecouplingChart.format.countWord(n); }

  function longDate(iso) {
    const parts = String(iso || "").split("-").map(Number);
    return parts.length === 3 && MONTHS[parts[1] - 1]
      ? parts[2] + " " + MONTHS[parts[1] - 1] + " " + parts[0] : String(iso || "");
  }

  // ------------------------------------------------------------ the numbers
  function model(data) {
    const first = data.meta.yearMin;
    const last = data.meta.yearMax;
    const at = function (c, year) { return c.series[year - first]; };
    return {
      first: first,
      last: last,
      pivot: Math.min(Math.max(PIVOT_YEAR, first), last),
      countries: data.countries,
      high: data.countries.filter(function (c) { return c.incomeGroup === "High income"; }),
      rest: data.countries.filter(function (c) { return c.incomeGroup !== "High income"; }),
      at: at,
      // Net balance per person, from the chart's own function so both round alike.
      net: function (c, year) { return global.DecouplingChart.netBalance(at(c, year)); },
      // Percent change of one measure between two years.
      change: function (c, key, y0, y1) { return 100 * (at(c, y1)[key] / at(c, y0)[key] - 1); }
    };
  }

  function buildFacts(m, data) {
    const signed = global.DecouplingChart.format.signedTonnes;
    const facts = {
      n_years: String(m.last - m.first + 1),
      n_focus: String(m.countries.length),
      n_context: String((data.context || []).length),
      year_first: String(m.first),
      year_last: String(m.last),
      retrieved: longDate(data.meta.retrieved)
    };
    m.countries.forEach(function (c) {
      const tag = c.iso.toLowerCase();
      [["gdp", "gdpPc"], ["prod", "prodPc"], ["cons", "consPc"]].forEach(function (pair) {
        const v = m.change(c, pair[1], m.first, m.last);
        facts[tag + "_" + pair[0] + "_change"] = percent(v);
        facts[tag + "_" + pair[0] + "_change_abs"] = percentAbs(v);
      });
      [m.first, m.pivot, m.last].forEach(function (year) {
        facts[tag + "_net_" + year] = signed(m.net(c, year));
      });
      // The share of the fall in production-based CO2 that a wider net balance gave
      // back. It means something for the four importers only, and only they use it.
      const first = c.series[0];
      const last = c.series[c.series.length - 1];
      facts[tag + "_offset_share"] = percentAbs(
        100 * (m.net(c, m.last) - m.net(c, m.first)) / (first.prodPc - last.prodPc));
    });
    return facts;
  }

  // ------------------------------------------------------------ the story steps
  // Each step is a chart state and a caption. A caption only makes a claim
  // after testing it against the data; where the test fails it falls back to
  // the bare numbers.
  function stepGrowth(m) {
    const cons = function (c) { return m.change(c, "consPc", m.first, m.pivot); };
    const tag = function (c) { return the(c.name) + " (" + percent(cons(c)) + ")"; };
    const all = m.countries;
    const up = all.filter(function (c) { return cons(c) > 0; });
    const down = all.filter(function (c) { return cons(c) <= 0; });
    const richer = all.filter(function (c) { return m.change(c, "gdpPc", m.first, m.pivot) > 0; });
    let text = richer.length === all.length
      ? "By " + m.pivot + " all " + countWord(all.length) + " were richer than in " + m.first + "."
      : "By " + m.pivot + ", " + countWord(richer.length) + " of the " + countWord(all.length) +
        " were richer than in " + m.first + ".";
    text += " Consumption-based CO2 per capita was";
    if (up.length) { text += " higher in " + listOf(up.map(tag)); }
    if (up.length && down.length) { text += ", and"; }
    if (down.length) { text += " lower in " + listOf(down.map(tag)); }
    const kind = up.length && down.length ? "mixed" : up.length ? "rising" : "falling";
    return { title: m.first + "-" + m.pivot + ": growth, " + kind + " footprints",
             caption: text + ".", year: m.pivot, from: m.first, overlay: false, highlight: null };
  }

  function stepTurn(m) {
    const cons = function (c) { return m.change(c, "consPc", m.pivot, m.last); };
    const gdp = function (c) { return m.change(c, "gdpPc", m.pivot, m.last); };
    const fell = m.high.length > 0 && m.high.every(function (c) { return cons(c) < 0; });
    const grew = m.high.every(function (c) { return gdp(c) > 0; });
    const span = "From " + m.pivot + " to " + m.last + " consumption-based CO2 per capita ";
    let text;
    if (fell && grew) {
      text = span + "fell in all " + countWord(m.high.length) + " high-income countries: by " +
        listOf(m.high.map(function (c) { return percentAbs(cons(c)) + " in " + the(c.name); })) +
        ". GDP per capita still grew in each (" +
        listOf(m.high.map(function (c) { return percent(gdp(c)); })) + ").";
    } else {
      text = span + "changed by " +
        listOf(m.high.map(function (c) { return percent(cons(c)) + " in " + the(c.name); })) +
        ". GDP per capita changed by " +
        listOf(m.high.map(function (c) { return percent(gdp(c)); })) + ".";
    }
    return { title: m.pivot + "-" + m.last + ": " + (fell ? "the turn down" : "after " + m.pivot),
             caption: text, year: m.last, from: m.pivot, overlay: false,
             highlight: m.high.map(function (c) { return c.name; }) };
  }

  function stepRise(m) {
    const gdp = function (c) { return m.change(c, "gdpPc", m.first, m.last); };
    const cons = function (c) { return m.change(c, "consPc", m.first, m.last); };
    const levels = function (c) {
      return "from " + oneDecimal(m.at(c, m.first).consPc) + " to " +
        oneDecimal(m.at(c, m.last).consPc);
    };
    const rose = m.rest.every(function (c) { return gdp(c) > 0 && cons(c) > 0; });
    const text = m.rest.map(function (c, i) {
      if (rose && i === 0) {
        return c.name + "'s GDP per capita rose " + percentAbs(gdp(c)) + " from " + m.first +
          " to " + m.last + " and its consumption-based CO2 per capita " + percentAbs(cons(c)) +
          ", " + levels(c) + ".";
      }
      if (rose) {
        return c.name + "'s rose " + percentAbs(gdp(c)) + " and " + percentAbs(cons(c)) + ", " +
          levels(c) + ".";
      }
      return c.name + ": GDP per capita " + percent(gdp(c)) + ", consumption-based CO2 per " +
        "capita " + percent(cons(c)) + " (" + levels(c) + ").";
    }).join(" ");
    const names = listOf(m.rest.map(function (c) { return c.name; }));
    return { title: names + ": " + (rose ? "up and to the right" : m.first + "-" + m.last),
             caption: text, year: m.last, from: m.first, overlay: false,
             highlight: m.rest.map(function (c) { return c.name; }) };
  }

  function stepGap(m) {
    const signed = global.DecouplingChart.format.signedTonnes;
    const net = function (c) { return m.net(c, m.last); };
    const group = function (list, role) {
      return listOf(list.map(function (c, i) {
        return signed(net(c)) + (i === 0 ? " per person" : "") + " in " + the(c.name);
      })) + " (net " + role + (list.length > 1 ? "s" : "") + ")";
    };
    const importers = m.countries.filter(function (c) { return net(c) > 0; });
    const exporters = m.countries.filter(function (c) { return net(c) < 0; });
    const groups = [];
    if (importers.length) { groups.push(group(importers, "importer")); }
    if (exporters.length) { groups.push(group(exporters, "exporter")); }
    return { title: "The gap: emitted or consumed",
             caption: "The thin line is production-based CO2, emitted inside the country; its " +
               "gap to the thick line is the net balance. In " + m.last + " that was " +
               groups.join(", and ") + ".",
             year: m.last, from: null, overlay: true, highlight: null };
  }

  // ------------------------------------------------------------ URL state
  function readUrl(m) {
    let params;
    try { params = new URLSearchParams(global.location.search); }
    catch (error) { params = new URLSearchParams(""); }
    const on = function (name) { return /^(1|true|yes|on)$/i.test(params.get(name) || ""); };
    const out = {};
    const year = parseInt(params.get("year"), 10);
    if (year >= m.first && year <= m.last) { out.year = year; }
    const x = (params.get("x") || "").toLowerCase();
    if (x === "linear" || x === "log") { out.scale = x; }
    if (params.has("overlay")) { out.overlay = on("overlay"); }
    if (params.has("context")) { out.context = on("context"); }
    const only = (params.get("only") || "").split(",")
      .map(function (s) { return s.trim(); }).filter(Boolean);
    if (only.length) { out.visible = only; }
    const step = parseInt(params.get("step"), 10);
    if (step >= 1) { out.step = step - 1; }
    return out;
  }

  // ------------------------------------------------------------ one app
  function init(root) {
    const data = global.DECOUPLING_DATA;
    if (!data || !global.DecouplingChart || !global.d3) {
      root.textContent = "The chart could not be drawn: its data or its scripts did not load.";
      return null;
    }
    const format = global.DecouplingChart.format;
    const id = "vis2-" + (++counter);
    const m = model(data);
    const steps = [stepGrowth(m), stepTurn(m), stepRise(m), stepGap(m)];
    const url = readUrl(m);
    const reduced = global.matchMedia ? global.matchMedia("(prefers-reduced-motion: reduce)")
                                      : { matches: false };
    const fitViewport = root.hasAttribute("data-fit-viewport");
    let active = null;          // index of the story step in force, or null
    let applying = false;       // true while a step is setting the chart
    let urlTimer = null;

    // ---- story steps
    const stepButtons = steps.map(function (step, i) {
      const button = h("button", { type: "button", class: "story-step", "aria-pressed": "false" }, [
        h("span", { class: "story-num", text: String(i + 1), "aria-hidden": "true" }),
        h("span", { class: "story-title", text: step.title })
      ]);
      button.addEventListener("click", function () { applyStep(i, true); });
      return button;
    });
    const caption = h("p", { class: "story-caption", "aria-live": "polite", text: HINT });
    const story = h("div", { class: "story" }, [
      h("div", { class: "story-steps", role: "group",
                 "aria-label": "Guided reading, " + countWord(steps.length) + " steps" },
        stepButtons),
      caption
    ]);

    // ---- controls: one row above the chart it scopes
    const playIcon = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    playIcon.setAttribute("viewBox", "0 0 12 12");
    playIcon.setAttribute("aria-hidden", "true");
    playIcon.setAttribute("focusable", "false");
    const playShape = document.createElementNS("http://www.w3.org/2000/svg", "path");
    playIcon.appendChild(playShape);
    const playLabel = h("span", { text: "Play" });
    const playButton = h("button", { type: "button", class: "vc-play" }, [playIcon, playLabel]);

    const slider = h("input", { type: "range", id: id + "-year", min: m.first, max: m.last,
                                step: 1, value: m.last });
    const yearOut = h("output", { class: "vc-year-value", for: id + "-year",
                                  text: String(m.last) });
    const yearBox = h("div", { class: "vc-year" }, [
      h("label", { for: id + "-year", text: "Year" }), slider, yearOut
    ]);

    const radios = ["linear", "log"].map(function (value) {
      return h("input", { type: "radio", name: id + "-scale", value: value });
    });
    const scaleBox = h("div", { class: "vc-scale", role: "radiogroup",
                                "aria-labelledby": id + "-scale-label" }, [
      h("span", { class: "vc-scale-label", id: id + "-scale-label", text: "GDP axis" }),
      h("label", { class: "seg" }, [radios[0], h("span", { text: "Linear" })]),
      h("label", { class: "seg" }, [radios[1], h("span", { text: "Log" })])
    ]);

    const overlayBox = h("input", { type: "checkbox" });
    const contextBox = h("input", { type: "checkbox" });
    const controls = h("div", { class: "vc", role: "group", "aria-label": "Chart controls" }, [
      playButton, yearBox, scaleBox,
      h("label", { class: "vc-check vc-overlay" },
        [overlayBox, h("span", { text: "Show production-based path" })]),
      h("label", { class: "vc-check vc-context" },
        [contextBox, h("span", { text: "Show the other " + data.context.length + " countries" })])
    ]);

    // ---- table view: the same values for the scrubbed year, without the chart
    const tableYear = h("span", { class: "tv-year", text: String(m.last) });
    const tableCaption = h("caption", {});
    const rows = data.countries.map(function (c) {
      const swatch = h("span", { class: "tv-key", "aria-hidden": "true" });
      swatch.style.background = c.color;
      const cells = { gdp: h("td", {}), cons: h("td", {}), prod: h("td", {}), net: h("td", {}),
                      role: h("td", {}) };
      return { c: c, cells: cells,
               row: h("tr", { "data-name": c.name }, [
                 h("th", { scope: "row" }, [swatch, h("span", { text: c.name })]),
                 cells.gdp, cells.cons, cells.prod, cells.net, cells.role]) };
    });
    const table = h("table", {}, [
      tableCaption,
      h("thead", {}, [h("tr", {}, ["Country", "GDP per capita", "Consumption-based CO2",
                                   "Production-based CO2", "Net balance", "Position"]
        .map(function (text) { return h("th", { scope: "col", text: text }); }))]),
      h("tbody", {}, rows.map(function (r) { return r.row; }))
    ]);
    const details = h("details", { class: "tv" }, [
      h("summary", {}, [h("span", { text: "Table view: values for " }), tableYear]),
      h("div", { class: "tv-scroll", tabindex: "0", role: "region",
                 "aria-label": "Table of the values plotted for the selected year" }, [table])
    ]);

    const mount = h("div", { class: "chart-mount" });
    root.textContent = "";
    root.classList.add("app");
    [story, controls, mount, details].forEach(function (node) { root.appendChild(node); });

    // ---- the chart, in the state the URL asks for
    const first = url.step != null && steps[url.step] ? steps[url.step] : null;
    const chart = global.DecouplingChart.create(mount, data, {
      titleTag: root.getAttribute("data-title-tag") || "h3",
      note: SOURCE_NOTE,
      year: url.year != null ? url.year : first ? first.year : m.last,
      scale: url.scale || "linear",
      overlay: url.overlay != null ? url.overlay : first ? first.overlay : false,
      context: !!url.context,
      visible: url.visible || null
    });
    if (first) {
      active = url.step;
      if (first.highlight) { chart.highlight(first.highlight); }
    }

    function renderSteps() {
      stepButtons.forEach(function (button, i) {
        button.setAttribute("aria-pressed", String(i === active));
      });
      caption.textContent = active == null ? HINT : steps[active].caption;
      caption.classList.toggle("is-step", active != null);
    }

    function applyStep(index, animate) {
      const step = steps[index];
      applying = true;
      chart.setVisible(null);
      chart.setOverlay(step.overlay);
      chart.highlight(step.highlight);
      if (animate && step.from != null && !reduced.matches) {
        chart.play({ from: step.from, to: step.year });
      } else {
        chart.setYear(step.year);
      }
      applying = false;
      active = index;
      renderSteps();
    }

    // A manual change means the caption no longer describes the view.
    function clearStep() {
      if (active == null) { return; }
      active = null;
      chart.highlight(null);
      renderSteps();
    }

    function renderTable(year) {
      tableYear.textContent = String(year);
      tableCaption.textContent = "Values for " + year + ". GDP per capita in international-$ " +
        "at 2011 prices; CO2 in tonnes per person; net balance is consumption minus production.";
      rows.forEach(function (r) {
        const d = m.at(r.c, year);
        r.cells.gdp.textContent = format.money(d.gdpPc);
        r.cells.cons.textContent = format.tonnes(d.consPc);
        r.cells.prod.textContent = format.tonnes(d.prodPc);
        r.cells.net.textContent = format.signedTonnes(m.net(r.c, year));
        r.cells.role.textContent = format.tradeRole(m.net(r.c, year));
      });
    }

    function writeUrl() {
      // A srcdoc frame (the notebook embed) has no address of its own to rewrite.
      if (global.location.protocol === "about:") { return; }
      const state = chart.getState();
      const parts = [];
      if (state.year !== state.yearMax) { parts.push("year=" + state.year); }
      if (state.scale !== "linear") { parts.push("x=" + state.scale); }
      if (state.overlay) { parts.push("overlay=1"); }
      if (state.context) { parts.push("context=1"); }
      if (state.visible.length !== m.countries.length) {
        parts.push("only=" + state.visible.map(encodeURIComponent).join(","));
      }
      const next = global.location.pathname + (parts.length ? "?" + parts.join("&") : "") +
        global.location.hash;
      // Some browsers refuse this for a page opened from disk. The view is unaffected.
      try {
        global.history.replaceState(null, "", next);
      } catch (error) { /* the address stays as it was */ }
    }

    function sync(state, reason) {
      slider.value = state.year;
      yearOut.textContent = String(state.year);
      playLabel.textContent = state.playing ? "Pause" : "Play";
      playShape.setAttribute("d", state.playing ? PAUSE_ICON : PLAY_ICON);
      radios.forEach(function (radio) { radio.checked = radio.value === state.scale; });
      overlayBox.checked = state.overlay;
      contextBox.checked = state.context;
      renderTable(state.year);
      if (!applying && reason === "visible") { clearStep(); }
      // Not on every animation step: browsers throttle rapid history updates.
      global.clearTimeout(urlTimer);
      if (!state.playing) { urlTimer = global.setTimeout(writeUrl, 200); }
    }

    slider.addEventListener("input", function () {
      clearStep();
      chart.setYear(+slider.value);
    });
    playButton.addEventListener("click", function () {
      clearStep();
      if (chart.getState().playing) { chart.pause(); } else { chart.play(); }
    });
    radios.forEach(function (radio) {
      radio.addEventListener("change", function () {
        if (radio.checked) { chart.setScale(radio.value); }
      });
    });
    overlayBox.addEventListener("change", function () {
      clearStep();
      chart.setOverlay(overlayBox.checked);
    });
    contextBox.addEventListener("change", function () { chart.setContext(contextBox.checked); });

    // In a frame of fixed height (the notebook embeds this page in one) the
    // plot gives up height before the page grows a second scrollbar. If even
    // the smallest plot worth reading would not fit, it keeps its full height
    // and the frame scrolls.
    let fitQueued = false;
    function fit() {
      fitQueued = false;
      chart.setHeight(null);
      if (global.innerWidth < 700) { return; }
      const over = Math.ceil(document.documentElement.scrollHeight - global.innerHeight);
      const fitted = chart.getState().height - over;
      if (over > 0 && fitted >= FIT_MIN_HEIGHT) { chart.setHeight(fitted); }
    }
    if (fitViewport) {
      global.addEventListener("resize", function () {
        if (!fitQueued) { fitQueued = true; global.requestAnimationFrame(fit); }
      });
    }

    chart.on("change", sync);
    renderSteps();
    sync(chart.getState(), "init");
    if (fitViewport) { fit(); }
    return { root: root, chart: chart, steps: steps, applyStep: applyStep };
  }

  function start() {
    const story = global.DecouplingStory;
    if (global.DECOUPLING_DATA && global.DecouplingChart) {
      const m = model(global.DECOUPLING_DATA);
      story.facts = buildFacts(m, global.DECOUPLING_DATA);
      document.querySelectorAll("[data-fact]").forEach(function (node) {
        const value = story.facts[node.getAttribute("data-fact")];
        if (value != null) { node.textContent = value; }
      });
    }
    document.querySelectorAll("[data-decoupling-app]").forEach(function (root) {
      const app = init(root);
      if (app) { story.apps.push(app); }
    });
  }

  global.DecouplingStory = { apps: [], facts: {}, pivotYear: PIVOT_YEAR, init: init };
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})(window);
