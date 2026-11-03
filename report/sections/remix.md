## 2.1 The original story

**Citation:** Ritchie, H. (2021, December 1). *Many countries have decoupled economic growth from CO2 emissions, even if we take offshored production into account*. Our World in Data. https://ourworldindata.org/co2-gdp-decoupling

Ritchie addresses the exact question posed in this report and summarizes her argument in 418 words and three charts. She makes a two-part claim: first, that numerous wealthy nations have expanded GDP while reducing domestic CO2 emissions; second, that this decline is not merely an accounting artifact of globalization--stating that *"it would be wrong to assume that this reduction in emissions in rich countries was only achieved by offshoring production overseas"* because consumption-based emissions *"have also fallen"* (Ritchie, 2021). Because the body text of her article cites no specific numbers, the visual encodings carry the entire empirical burden. Below, I evaluate the article as served on 4 October 2026 under its Creative Commons BY license.

**Chart A: The indexed line chart ([[FIG:Ra]]).** The article opens with an interactive Our World in Data Grapher embed titled *"Change in per capita CO2 emissions and GDP"*, defaulting to the United Kingdom. It plots three continuous line series with annual point markers from 1990 onward. Horizontal position encodes the year, while vertical position on a shared scale (-60% to +60%) encodes cumulative percentage change relative to 1990 for GDP per capita, consumption-based CO2 per capita, and territorial CO2 per capita. Color hue distinguishes the three series, which are directly labeled at their right endpoints. Interactive controls allow readers to switch or add countries and adjust the date range. Later in the article, Ritchie embeds the same chart a second time configured as a six-country small-multiple grid sharing a common percentage axis.

[[SHOT:Ra]]

**Chart B: The static arrow grid ([[FIG:Rc]]).** The second idiom is a static graphic credited to Max Roser titled *"Decoupling: Countries that achieved economic growth while reducing CO2 emissions, 2005-20"*. It arranges 30 country panels in a 5 x 6 grid. Within each panel, two straight arrows diverge from a common left-hand origin: a blue arrow pointing upward to represent percentage growth in GDP per capita, and a red arrow pointing downward to represent percentage reduction in consumption-based CO2 per capita between 2005 and 2020.

## 2.2 Critique of the original charts

Both original visualizations are clean, well-labeled, and transparent about their data sources, and Chart A's horizontal zero baseline makes the divergence between positive GDP growth and negative emissions growth immediately legible. However, the two idioms suffer from five analytical limitations when evaluating the trade-outsourcing question:

1. **Absolute emission levels are hidden.** Because every series is indexed to 0% in 1990, physical quantities in tonnes disappear entirely. In [[FIG:Ra]], the United Kingdom's production and consumption lines both start at the exact same 0% origin in 1990, hiding the fact that the UK was already importing a net balance of 1.12 t of CO2 per person in 1990. Readers can only compare differences in relative percentage rates rather than the physical tonnage of offshored carbon, and the embedded chart disables the toggle that would display absolute units.
2. **Indexed percentage scales break down when comparing advanced and developing economies.** When I used Chart A's country selector to add China alongside the United Kingdom ([[FIG:Rb]]), the view split into faceted panels sharing a vertical axis that stretched to +1,500% to accommodate China's tenfold GDP expansion from a low 1990 base. On that shared scale, the United Kingdom's entire 33-year trajectory (-57% to +61%) is compressed into a flat sliver along the zero line. As a result, the idiom cannot legibly compare a wealthy net importer and a rapidly industrializing net exporter on the same axis.

[[SHOT:Rb]]

3. **Income and emissions are never plotted directly against each other.** Because time occupies the horizontal axis in Chart A, evaluating how emissions respond to economic growth requires the viewer to visually estimate and compare the slopes of separate lines over time. In Cleveland and McGill's (1984, p. 536) hierarchy of graphical perception, slope and angle judgments are significantly less accurate than judgments of position along a common scale.
4. **Reliance on two isolated endpoints--ending in a pandemic anomaly.** Chart B ([[FIG:Rc]]) collapses sixteen years of economic history into a single two-point comparison (2005 versus 2020) and filters the dataset to show only countries where both metrics changed by more than 5%. Ironically, the United Kingdom--the flagship example of Ritchie's article--is missing from the 30 panels because UK real GDP per capita in 2020 dipped 0.8% below its 2005 level due to COVID-19 lockdowns (whereas ending in 2019 would show +10.5% growth). Similarly, UK consumption-based CO2 dropped 10.8% in 2020 alone before rebounding 9.6% in 2021. By filtering strictly for decoupling successes, the grid also omits net exporters like China and India and provides no visibility into international trade balances.

[[SHOT:Rc]]

5. **Limited interactive agency.** While Chart A lets readers swap countries or narrow the year range, the views are isolated. A reader cannot brush a specific historical era (such as the pre-2008 globalization boom) to see how global trade balances shifted across income groups, nor can they inspect how territorial and consumption trajectories diverge in phase space.

## 2.3 What the remix adds

| Limit of the original | What this report does about it |
| :--- | :--- |
| **Levels are gone** | Visualization 3 plots the trade gap directly in tonnes per person. Visualization 2 plots consumption footprints in tonnes against real income in dollars. |
| **No importer and exporter in one view** | All three visualizations place the United States, the United Kingdom, Germany, and Sweden alongside China and India on shared or compatible coordinate scales. |
| **GDP and CO2 never meet** | Visualization 2 maps GDP per person to the x-axis and CO2 per person to the y-axis, encoding time along the connected trajectory path. |
| **Two endpoints** | Every visualization incorporates all 33 annual observations (1990-2022), allowing readers to brush custom multi-year windows in Visualization 1 and scrub year-by-year in Visualization 2. |
| **Substitution only; no linked cross-country view** | Visualization 1 links the national time series to a 109-country scatterplot so brushing any time interval dynamically recomputes the global cross-section. |

Extending the panel through 2022 also incorporates two post-pandemic recovery years that were unavailable when the 2005-2020 arrow grid was published. As noted in Section 1.3, whereas OWID's Chart A uses World Bank GDP at 2021 prices, this remix uses the Maddison Project GDP series (at 2011 prices) bundled directly inside the OWID CO2 dataset.
