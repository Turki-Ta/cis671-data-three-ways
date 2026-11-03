## 6.1 How the three views work together

Because no single visual encoding can simultaneously display global cross-sectional distributions, bivariate phase-space trajectories, and exact trade-gap magnitudes, each of the three visualizations addresses a distinct dimension of the research question:

- **Visualization 1 (Altair linked views)** establishes the global structure of carbon trade. Across the 110-country panel, 36 of the 46 high-income economies were net importers of embodied CO2 in 2022, with group net imports totaling 1,566 Mt (up from 372 Mt in 1990). At the same time, it refutes the notion that developing countries uniformly act as carbon exporters: 86 of the 110 countries in the panel are net importers, and just three major exporting nations (China, India, and Russia) account for 78% of all net exported CO2.
- **Visualization 2 (D3.js connected scatterplot)** pinpoints when the relationship between growth and emissions changed. Up through the mid-2000s, consumption-based CO2 per person rose alongside GDP in both the United States (+13% to 2005) and the United Kingdom (+11% to 2004). After 2007, however, all four wealthy economies bent downward into absolute decoupling--cutting consumption footprints by 22% to 41% through 2022 while continuing to expand real GDP per capita--whereas China and India climbed continuously upward and to the right across all 33 years.
- **Visualization 3 (Seaborn small multiples)** measures the exact tonnage of the trade gap between territorial and consumption accounts. It shows that the UK import balance tripled from 1.12 t per person in 1990 to 3.34 t in 2004 before stabilizing at 2.81 t in 2022, while the US shifted from a net exporter (-0.32 t) to a net importer (+1.49 t, peaking at +1.92 t in 2006).

## 6.2 The empirical answer

Both economic decoupling and carbon offshoring are real, and because the two accounting systems are linked by an exact additive identity--the reduction in consumption-based CO2 equals the reduction in territorial CO2 minus the increase in the net import balance--we can quantify the exact contribution of each (Table 4).

| Country | GDP per person | Territorial cut, t per person | Change in import balance, t | Consumption cut, t per person | Share of territorial cut offset by imports |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **United States** | +56% | 5.45 | +1.81 | 3.64 | 33% |
| **United Kingdom** | +46% | 5.93 | +1.69 | 4.24 | 29% |
| **Germany** | +84% | 5.29 | +0.21 | 5.08 | 4% |
| **Sweden** | +68% | 3.24 | -3.54 | 6.78 | none: the balance shrank |

Comparing 1990 against 2022 across Table 4 provides a clear quantitative verdict. In the United Kingdom, territorial emissions fell by 5.93 t per person while a widening import balance offset 1.69 t (29%) of that gain--leaving a genuine reduction of 4.24 t per person (71% of the headline cut) in the average resident's consumption footprint. In the United States, increased carbon imports offset 33% of the territorial reduction, leaving 67% (3.64 t) as genuine consumption decoupling. In Germany, trade shifts offset just 4% of the territorial cut, and in Sweden the consumption footprint actually fell by more than twice the territorial reduction because net imports declined substantially after the early 1990s. Wealthy post-industrial economies have achieved genuine absolute decoupling, even after accounting for trade.

Three important qualifications temper this conclusion:

1. **Historical timing matters.** Between 1990 and 2007, the outsourcing critique was entirely accurate for the United Kingdom and the United States: UK territorial CO2 per person fell 13% while consumption-based CO2 rose 7%, and US territorial emissions stood flat (+0.1%) while consumption emissions climbed 8%. Had this analysis stopped in 2007, the data would have supported the outsourcing hypothesis for both Anglo-Saxon economies.
2. **Baseline levels remain understated by territorial accounting.** Even after fifteen years of falling consumption emissions, wealthy countries still consume substantially more carbon than their domestic inventories report--by 83% in Sweden, 62% in the United Kingdom, 26% in Germany, and 10% in the United States in 2022.
3. **Post-2007 UK decoupling occurred alongside weak income growth.** While UK consumption emissions dropped 41% between 2007 and 2022, Maddison real GDP per capita grew by just 4% over that entire fifteen-year span (compared to 12% in the US and 17% in Germany), meaning recent UK emissions reductions coincided with near-stagnant per-capita income.

On the exporting side, China and India achieved substantial *relative* decoupling--cutting carbon intensity per dollar of GDP by 45% and 33%, respectively--while their absolute per-capita footprints continued to grow alongside rapid industrialization and rising domestic living standards. By 2022, China's consumption footprint (7.32 t per person) had converged with the United Kingdom's (7.37 t) at roughly half the UK's per-capita GDP, and net exports accounted for 11% of China's territorial emissions (down from a peak share in 2008) and 17% of India's.

These empirical findings align closely with the broader climate-economics literature. Le Quéré et al. (2019) analyzed 18 developed economies whose emissions declined on both accounts between 2005 and 2015, showing that net emission transfers via trade plateaued around 2005. Similarly, Hubacek et al. (2021) identified 23 of 116 nations achieving absolute consumption-based decoupling between 2015 and 2018 while cautioning that short-term decoupling can reverse, and Haberl et al.'s (2020) systematic review of 835 studies concluded that while high-income nations have begun decoupling GDP from consumption-based CO2, current reduction rates remain far too gradual to meet rapid global decarbonization targets.

## 6.3 Limitations and future directions

This analysis is bounded by fossil-fuel and industrial CO2, modeled MRIO trade allocations, and single-year endpoints in the decomposition table. Extending the work would involve repeating the decomposition across multi-year averages, incorporating land-use change and non-CO2 greenhouse gases, and explicitly encoding model uncertainty bands around the post-2017 consumption estimates.
