## 1.1 The question

**Has economic growth in post-industrial nations genuinely decoupled from carbon emissions, or have wealthy countries merely outsourced their environmental footprint by importing emissions-intensive manufactured goods from developing nations?**

These two explanations predict very different patterns when we compare how emissions are counted. A country's CO2 can be measured where fossil fuels are physically burned--known as production-based or territorial accounting--or where finished goods and services are ultimately consumed, known as consumption-based accounting. If a wealthy economy reduced its domestic emissions simply by shifting heavy manufacturing overseas, its consumption-based emissions would remain flat or continue climbing even as its territorial emissions fell, widening the gap between the two accounts over time. Conversely, if economic growth has genuinely decoupled from carbon, both territorial and consumption-based emissions should decline together. Every visualization in this report examines this relationship across three core quantities for each country and year: real GDP per person, CO2 per person under both accounting methods, and the net trade balance between the two accounts.

Looking across the full 1990-2022 record, the data show that both dynamics occurred in sequence, though on different scales. Between 1990 and 2007, the outsourcing hypothesis holds up well for the United Kingdom and the United States. During that period, the United Kingdom's territorial CO2 per person fell by 13% while its consumption-based footprint rose by 7%, causing the net import gap between the two series to triple from 1.1 t to 3.3 t per person. After 2007, however, both series declined in tandem. Over the entire 33-year window, GDP per person across the four high-income economies tracked in this study grew by 46% to 84%, while their consumption-based CO2 per person fell by 18% to 52%--a sustained reduction that offshoring alone cannot explain. What offshoring leaves behind is a persistent baseline gap and a reporting bias: in 2022, the United Kingdom's consumption footprint was 62% higher than its domestic territorial emissions, and territorial accounting suggests a 57% reduction since 1990 compared to a 36% reduction on the consumption account.

## 1.2 The dataset

All data in this report come from the Our World in Data (OWID) CO2 and Greenhouse Gas Emissions dataset (Ritchie et al., 2023), a CSV of 50,411 rows and 79 columns covering 254 countries and regional aggregates from 1750 to 2024. The snapshot analyzed here was retrieved on 4 October 2026 from `https://owid-public.owid.io/data/co2/owid-co2-data.csv`. To ensure reproducibility, `scripts/fetch_inputs.py` verifies the local file against its stored SHA-256 checksum prior to running the pipeline. Because OWID compiles this file from primary institutional datasets, Table 1 cites each upstream authority alongside its respective coverage and units.

| Variable | What it measures | Unit | Upstream source | In the file for |
| :--- | :--- | :--- | :--- | :--- |
| `gdp` | Real GDP, adjusted for inflation and purchasing power differences across countries | international-$ at 2011 prices | Maddison Project Database 2023 (Bolt & van Zanden, 2025) | 1820-2022 |
| `population` | Resident population | persons | World Population Prospects 2024 (United Nations, 2024), via OWID (Mathieu & Rodés-Guirao, 2022) | 1750-2024 |
| `co2_per_capita` | Production-based (territorial) CO2 from fossil fuels and industry; excludes land-use change | t per person per year | Global Carbon Budget 2025 (Friedlingstein et al., 2026; Andrew & Peters, 2025) | 1750-2024 |
| `consumption_co2_per_capita` | Territorial CO2 minus CO2 embodied in exports, plus CO2 embodied in imports | t per person per year | Global Carbon Budget 2025, method of Peters, Minx, et al. (2011) | 1990-2023 |
| `cumulative_co2` | Territorial CO2 summed continuously from 1750 | Mt | Global Carbon Budget 2025 | 1750-2024 |
| `income group` | World Bank classification by GNI per capita for FY 2027, consolidated into three tiers | category | World Bank (2026) | current year only |

From these raw columns, `scripts/prepare_data.py` derives three analytical variables:

```text
gdp_per_capita     = gdp / population                               international-$ per person
net_co2_per_capita = consumption_co2_per_capita - co2_per_capita    t CO2 per person
net_co2_mt         = consumption_co2 - co2                          Mt CO2
```

The net balance (`net_co2_per_capita`) is the central metric of our analysis. A positive balance means a country consumes more CO2 than it emits domestically, making it a net importer of embodied emissions; a negative balance means it emits more domestically than it consumes, making it a net exporter.

**Sampling and Panel Construction.** All series are annual, covering the 33-year window from 1990 to 2022--the overlapping period where consumption-based CO2 estimates (which begin in 1990) and Maddison real GDP data (which end in 2022) are jointly available. Out of 218 sovereign entities with an ISO code, 115 have complete records for GDP, population, and both CO2 series across all 33 years. Five of those countries contain unmodeled placeholder values in early years (detailed below) and are excluded rather than interpolated, leaving a balanced panel of 110 countries. Six focal economies anchor the narrative and appear in a consistent sequence across every chart: the United States, the United Kingdom, Germany, and Sweden (high income), alongside China (upper-middle income) and India (lower-middle income). The remaining 104 countries provide global context in Visualization 1, where 109 of the 110 countries carry an official World Bank income classification (Taiwan is omitted from the World Bank API response).

| Country | GDP per person, int-$ | Production CO2, t per person | Consumption CO2, t per person | Net balance, t per person | Share of world cumulative CO2 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **United States** | 36,509 to 57,075 (+56%) | 20.25 to 14.80 (-27%) | 19.94 to 16.30 (-18%) | -0.32 to +1.49 | 24.0% |
| **United Kingdom** | 26,246 to 38,358 (+46%) | 10.49 to 4.56 (-57%) | 11.61 to 7.37 (-36%) | +1.12 to +2.81 | 4.5% |
| **Germany** | 25,287 to 46,495 (+84%) | 13.23 to 7.94 (-40%) | 15.06 to 9.98 (-34%) | +1.82 to +2.03 | 5.3% |
| **Sweden** | 28,069 to 47,125 (+68%) | 6.71 to 3.47 (-48%) | 13.11 to 6.33 (-52%) | +6.40 to +2.86 | 0.3% |
| **China** | 2,934 to 18,921 (+545%) | 2.15 to 8.22 (+282%) | 2.05 to 7.32 (+258%) | -0.11 to -0.90 | 14.7% |
| **India** | 2,024 to 7,350 (+263%) | 0.67 to 1.99 (+197%) | 0.67 to 1.64 (+143%) | +0.01 to -0.34 | 3.4% |

Each cell in Table 2 compares 1990 against 2022. The final column lists each nation's share of cumulative global territorial CO2 emitted since 1750 as of 2022, underscoring the historical scale of the United States, which alone accounts for nearly a quarter of all historical industrial emissions.

## 1.3 Data integrity

Interpreting these series accurately requires accounting for eight methodological constraints in the underlying data:

1. **Consumption emissions are modeled estimates.** The Global Carbon Budget estimates consumption-based CO2 using a multi-region input-output (MRIO) trade model anchored to Global Trade Analysis Project (GTAP) benchmark tables for seven reference years (1997, 2001, 2004, 2007, 2011, 2014, and 2017) and extrapolated to intervening and subsequent years using national GDP and trade accounts (Friedlingstein et al., 2026, Supplement S.1.2). Because no benchmark table exists after 2017, the final five years of our panel rely on trade-model extensions, and the Global Carbon Project does not publish separate uncertainty bounds for the consumption series.
2. **Placeholder records in early consumption series.** In 39 country-years, the raw file repeats the territorial figure verbatim in the consumption column to six significant digits: Belgium and Luxembourg through 1998, South Africa and Botswana through 1999, and Tunisia in 2021. This produces an artificial net balance of zero that jumps abruptly once trade modeling begins (for example, Belgium jumps from 0 to +56 Mt in 1999). Because no genuine modeled balance in the dataset falls within 0.00001 of zero, `scripts/prepare_data.py` flags any observation where the two accounts match within one part in 100,000 as missing and excludes those five incomplete countries from the panel.
3. **Emissions scope.** Both series track CO2 from fossil fuel combustion and cement production. Emissions from land-use change, forestry, methane, and nitrous oxide are excluded, as are international aviation and maritime bunker fuels, which are not allocated to national territories.
4. **Differences across GDP series.** The OWID CO2 file bundles Maddison Project GDP measured in 2011 international dollars. By contrast, the interactive chart in the original OWID article plots a World Bank PPP series in 2021 prices, under which UK GDP per person grows by 61% between 1990 and 2022 compared to 46% in the Maddison series. Both charts share identical CO2 series to five decimal places, meaning the emissions side of the decoupling calculation is unchanged while the magnitude of income growth depends on the chosen price benchmark. Additionally, dividing Maddison total GDP by OWID's UN population column yields a US per-capita GDP increase of 56.3% (versus 58.2% in Maddison's internal per-capita series) and 263% for India (versus 272%), while the remaining four focus nations agree within 0.6 percentage points.
5. **Geopolitical accounting anomalies.** Kuwait's territorial emissions spike from 38 Mt in 1990 to 493 Mt in 1991 due to the Gulf War oil-well fires, which OWID merges into Kuwait's territorial total (Andrew & Peters, 2025). Because the trade model does not allocate oil-fire emissions to foreign consumers, Kuwait registers as a net exporter of 473 Mt in 1991, pulling the entire high-income group's aggregate balance down from +461 Mt to -12 Mt for that single year. I retain the observation in the panel and annotate the anomaly where relevant.
6. **Fixed contemporary income classifications.** World Bank income tiers reflect the fiscal year 2027 classification (effective July 2026) applied across the full 1990-2022 timeframe. Although China was classified as a low-income economy in 1990, it is encoded under its current upper-middle-income designation throughout the scatterplots.
7. **Single-year baseline sensitivity.** Using 1990 as an index anchor introduces single-year noise for Germany (which reunified in October 1990) and Sweden (whose 1990 consumption estimate of 13.1 t is nearly double its territorial figure of 6.7 t). To mitigate endpoint sensitivity, I pair single-year comparisons with ten-year window averages in Visualization 1.
8. **Incomplete coverage of lower-income economies.** Because the panel of 110 countries is restricted to nations continuously tracked by the trade model across all 33 years, smaller developing economies are underrepresented; only 7 of the 110 countries fall into the low-income tier.

As an internal consistency check, the net balance derived in `scripts/prepare_data.py` matches OWID's precomputed `trade_co2` column to within 0.0005 Mt across every row of the 3,630 country-year observations, confirming that the difference between consumption and production per-capita series accurately captures embodied trade flows.

## 1.4 Tools and AI use

The project pipeline is implemented in Python 3.12 using `pandas` 3.0, `altair` 6.3, `matplotlib` 3.11, and `seaborn` 0.13 inside a local virtual environment, paired with vanilla JavaScript and D3 v7 for web rendering. Course guidelines permit AI assistance on at most one target visualization. I used that allowance for **Visualization 2**, the D3.js connected scatterplot: AI tooling (Claude, Anthropic) worked there as a coding assistant and nowhere else. Visualization 1 (Altair), Visualization 3 (Seaborn/Matplotlib), the data preparation scripts, and the written analysis in this report were completed independently by me without AI assistance. Specific implementation disclosures appear at the end of Sections 3, 4, and 5.
