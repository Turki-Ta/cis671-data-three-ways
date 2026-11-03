# SOURCES

Provenance of every file in inputs/ and of every source the Module 2 report cites.
Compiled on 4 October 2026. Web sources were read on that date; the few that are named but could not be opened are marked as such.
Re-checked on the same day by a second, independent pass that opened again every DOI record and web page, and every paper the first pass had read, and recomputed the figures taken from data files. What that pass changed is listed at the end of section 7.

Conventions used in this file

- Plain ASCII only. CO2 is written without a subscript. Accented letters in author names are written without the accent (Le Quere, Landschutzer, Virag, Rodes-Guirao); restore them from the DOI record when the reference list is typeset. Page ranges use a hyphen.
- APA 7 italics cannot be shown in plain text. When typesetting, italicise book and report titles, journal names and volume numbers.
- "Verified" means the detail was read on 4 October 2026 in a source opened that day: the document itself, the publisher's landing page, or the registry record of the DOI (Crossref: https://api.crossref.org/works/DOI ; DataCite: https://api.datacite.org/dois/DOI). Anything not confirmed in that way is marked UNVERIFIED, with what is missing. Section 7 collects every such item.
- SHA-256 values are the ones recorded in scripts/fetch_inputs.py. All seven were recomputed from the files on disk when this file was written, and all seven matched.

Contents

1. Raw downloads in inputs/
2. Derived files
3. The 1991 Kuwait anomaly
4. Verified bibliography (APA 7)
5. Appendix A: the original article, as verified
6. Appendix B: findings recorded from the cited literature, with page numbers
7. Appendix C: what could not be verified, followed by the changes made at the re-check


## 1. Raw downloads in inputs/

Seven files were downloaded and none was edited afterwards. Three are the data; four are the original article's own material. scripts/fetch_inputs.py re-checks their hashes, and with --fetch downloads them again.

### 1.1 inputs/owid-co2-data.csv (the data)

- URL: https://owid-public.owid.io/data/co2/owid-co2-data.csv
- Retrieved: 4 October 2026
- SHA-256: 7ec10de1e9502c20c70bfff54476d7893922f7594aa299d9291d87fe49f3e342
- Size and shape: 33,246,106 bytes; 50,411 rows by 79 columns; 254 entities, 218 of them with a three-letter ISO code; years 1750 to 2024.
- Build: on 4 October 2026 the server reported Last-Modified: Tue, 02 Jun 2026 16:17:17 GMT for this URL, with the same byte length as the local copy. The latest entry in the repository changelog is 2026-06-01 (energy data only). The emissions columns were last rebuilt on 2025-11-13 ("Updated dataset to use the latest version of the Global Carbon Budget (2025)") and the GDP column on 2024-06-20 ("Update data from the Maddison Project Database").
- Publisher: Our World in Data (OWID); repository https://github.com/owid/co2-data . Its README says the data were "collected, aggregated, and documented by Pablo Rosado, Hannah Ritchie, Max Roser, Edouard Mathieu, and Bobbie Macdonald".
- Licence: Creative Commons Attribution 4.0 (CC BY 4.0). README, section License: "All visualizations, data, and code produced by Our World in Data are completely open access under the Creative Commons BY license. You have the permission to use, distribute, and reproduce these in any medium, provided the source and authors are credited." It adds that third-party data "is subject to the license terms from the original third-party authors". Every upstream source used here is itself under a CC BY licence (below). The repository has no separate LICENSE file; the README statement is the licence notice.
- Citation OWID asks for: README, section How to cite this data: "If you are using this dataset, please cite both Our World in Data and the underlying data source(s)." The OWID citation it links to reads: Hannah Ritchie, Pablo Rosado, and Max Roser (2023) - "CO2 and Greenhouse Gas Emissions" Published online at OurWorldinData.org. Retrieved from: 'https://ourworldindata.org/co2-and-greenhouse-gas-emissions' [Online Resource]. In section 4 that is Ritchie, Rosado, and Roser (2023). The underlying sources are Friedlingstein et al. (2026), Andrew and Peters (2025), Bolt and van Zanden (2025) and the population sources.

Upstream sources of the 13 columns that scripts/prepare_data.py reads. The quoted source labels are OWID's own, from the codebook (1.2).

co2 (million tonnes), cumulative_co2 (million tonnes), share_global_cumulative_co2 (%)

- Codebook: "Annual total emissions of carbon dioxide (CO2), excluding land-use change, measured in million tonnes." Source: "Global Carbon Budget (2025)". These are fossil-fuel and industry emissions counted where they are emitted (territorial, also called production-based).
- Upstream: the Global Carbon Project's fossil CO2 emissions dataset, version 2025v15 (Andrew and Peters, 2025; CC BY 4.0), which is the fossil component of the Global Carbon Budget 2025 (Friedlingstein et al., 2026). OWID's pipeline records its snapshot of this file with size 3,147,221 bytes and md5 3008e30d913af5926a83d0d0775fb72e; Zenodo lists the same size and md5 for GCB2025v15_MtCO2_flat.csv, so OWID ingested exactly that file; OWID dates the snapshot 13 November 2025.
- How that dataset is built (Friedlingstein et al., 2026, section 2.1.1): "The CDIAC-FF emissions dataset, derived largely from UN energy data, forms the foundation, and we extend emissions to 2024 using energy growth rates reported by the Energy Institute"; estimates are then replaced with "superior sources, for example Annex 1 countries' official submissions to the UNFCCC". The paper's Table 2 names Erb and Marland (2025) and UNFCCC (2022) as the primary references for national territorial emissions; neither was opened for this file.
- OWID processing: the emissions of the 1991 Kuwaiti oil fires are added to Kuwait (section 3). The cumulative and share columns are OWID's running sums of co2. Emissions from international aviation and shipping are in no country's total.

consumption_co2 (million tonnes)

- Codebook: "Annual consumption-based emissions of carbon dioxide (CO2), measured in million tonnes." Source: "Global Carbon Budget (2025)".
- Upstream: the national emissions workbook of the Global Carbon Budget 2025 data supplement (Global Carbon Project, 2025; CC BY 4.0), which holds territorial emissions, consumption emissions and emissions transfers. Table 2 of the budget paper gives the primary reference for national consumption-based emissions as "Peters et al. (2011a) updated as described in this paper", that is Peters, Minx, Weber, and Edenhofer (2011) as updated in Friedlingstein et al. (2026).
- Which workbook, exactly. OWID's pipeline records its snapshot of the national workbook with size 739,007 bytes and md5 45ffe7018d583fcc896080c299e741cd (snapshots/gcp/2025-11-13/global_carbon_budget_national_emissions.xlsx.dvc in https://github.com/owid/etl , dated 13 November 2025). The file the Global Carbon Budget website serves as "National fossil carbon emissions v2025" (https://globalcarbonbudget.org/download/2345/ , file name National_Fossil_Carbon_Emissions_2025_v0.3.xlsx) was downloaded on 4 October 2026 and has the same size and md5, so that is the workbook OWID ingested. Its sheets are Summary, Territorial Emissions, Consumption Emissions, Emissions Transfers and Regions; the three data sheets are in million tonnes of carbon. Multiplied by 3.664, the Consumption Emissions sheet reproduces consumption_co2 (United Kingdom 1990: 181.7704 MtC = 666.01 Mt CO2; 2022: 137.2190 MtC = 502.77 Mt CO2; for the six focus countries and Kuwait in 1990 and 2022 the two agree to within 0.001 Mt). The sheet's own citation line reads "Updated from Peters, GP, Minx, JC, Weber, CL and Edenhofer, O 2011".
- Coverage in this file: 120 ISO-coded countries, 1990 to 2023. Only World and the two international-transport entities have a 2024 value.
- OWID's definition (indicator metadata): "Consumption-based emissions equals production-based emissions, minus emissions embedded in exports, plus emissions embedded in imports." Also: "Consumption-based emissions are not available for all countries because not all countries have sufficient, high-quality trade data. But those without complete data are a small fraction (3%) of the global total."

How the Global Carbon Budget makes the consumption-based estimates (Friedlingstein et al., 2026, Supplement section S.1.2, "Emissions embodied in goods and services", supplement pp. 1-2)

- Definition: consumption-based inventories "allocate emissions to products that are consumed within a country and are conceptually calculated as the territorial emissions minus the 'embodied' territorial emissions to produce exported products plus the emissions in other countries to produce imported products (Consumption = Territorial - Exports + Imports)". They "have the same global total but reflect the trade-driven movement of emissions between countries".
- Model: "We estimate consumption-based emissions from 1990 by enumerating the global supply chain using a global model of the economic relationships between economic sectors within and between every country (Andrew and Peters, 2013; Peters et al., 2011b)." Here 2011b is Peters, Andrew, and Lennox (2011).
- Data: economic and trade data from the Global Trade Analysis Project (GTAP), with "detailed estimates for the years 1997 (GTAP version 5), 2001 (GTAP6), and 2004, 2007, 2011, 2014, and 2017 (GTAP11.0), covering 57 sectors and 141 countries and regions".
- Years in between and after: "The detailed results are then extended into an annual time series from 1990 to the latest year of the Gross Domestic Product (GDP) data (typically one year less than the territorial emissions data), using GDP data by expenditure in current exchange rate of US dollars ... and time series of trade data from GTAP". Read plainly, the detailed supply-chain estimate exists for seven benchmark years only; the years between them and every year after 2017 are extensions made with GDP and trade series, and no year after 2017 has a benchmark of its own.
- Scaling: sector emissions are estimated with the GTAP data, flaring and cement emissions are added, and the national totals are then scaled "(excluding bunker fuels) to match the emission estimates from the carbon budget".
- Uncertainty: "We do not provide a separate uncertainty estimate for the consumption-based emissions, but based on model comparisons and sensitivity analysis, they are unlikely to be significantly different than for the territorial emission estimates (Peters et al., 2012b)." Here 2012b is Peters, Davis, and Andrew (2012).

trade_co2 (million tonnes), trade_co2_share (%)

- Codebook: "Annual net carbon dioxide (CO2) emissions embedded in trade". Derived by OWID: its pipeline (etl/steps/data/garden/gcp/2025-11-13/global_carbon_budget.py) sets traded emissions = consumption emissions - total emissions, and the share = 100 x traded emissions / total emissions. The Global Carbon Project's national workbook has a sheet of its own, Emissions Transfers, which OWID does not use and which has the opposite sign (territorial minus consumption, so a net exporter is positive): United Kingdom 1990 is -17.4841 MtC = -64.06 Mt CO2 there and +64.06 Mt in trade_co2. OWID's metadata: "A positive value denotes a country or region is a net importer of CO2 emissions; a negative value indicates a country is a net exporter."
- scripts/prepare_data.py recomputes the same difference as net_co2_mt and checks it against trade_co2 (worst gap 0.0005 Mt). Note the sign: Peters, Minx, et al. (2011) use the opposite convention (net exporters positive).

co2_per_capita, consumption_co2_per_capita (tonnes per person)

- Codebook source: "Global Carbon Budget (2025); Population based on various sources (2024)". OWID divides the emissions above by its own population column.

gdp (international-$ in 2011 prices)

- Codebook: "Total economic output of a country or region per year. This data is adjusted for inflation and differences in living costs between countries." Source: "Bolt and van Zanden - Maddison Project Database 2023".
- Upstream: Maddison Project Database 2023 (Bolt and van Zanden, 2025; the database's own page cites the same paper by its online year, 2024, see section 4); dataset https://doi.org/10.34894/INZBF2 (DataverseNL, version 1.0, 26 April 2024); page https://www.rug.nl/ggdc/historicaldevelopment/maddison/releases/maddison-project-database-2023 . It "covers 169 countries and the period up to 2022", which is why this project's window ends in 2022.
- Licence: "Maddison Project Database, version 2023 by Jutta Bolt and Jan Luiten van Zanden is licensed under a Creative Commons Attribution 4.0 International License."
- Attribution requirement on that page. Under the heading "Attribution requirement" it says "All original papers must be cited when:" and lists two cases: "the data is shown in any graphical form" and "subsets of the full dataset that include less than a dozen (12) countries are used for statistical analysis or any other purposes". It goes on: "A list of original papers can be found in the source sheet of the database. When neither a) or b) apply, then the MPD as a whole should be cited." This project plots GDP for six countries, so both cases apply.
- What the source sheet says for this project's years. The Sources sheet of the database workbook (mpd2023_web.xlsx, downloaded from DataverseNL on 4 October 2026) has one general line for recent years: "GDP pc: 2008 - 2022: Total Economy Database the Conference Board for all countries included in TED. Otherwise UN national accounts statistics". Among the six focus countries the only country entry that reaches into 1990-2022 is China, "1952-2008": Wu, Harry X. (2014), "China's growth and productivity performance debate revisited - Accounting for China's sources of growth with a new data set", The Conference Board Economics Program Working Paper Series EWP#14-01. For the United States, United Kingdom, Germany, Sweden and India neither that sheet nor the sheet "Maddison original sources" names a source for 1990 to 2007. Neither The Conference Board database nor Wu (2014) was opened, so they are named here and not listed in section 4.
- OWID processing: the database gives GDP per person (gdppc) and population (pop); OWID multiplies them (etl/steps/data/garden/ggdc/2024-04-26/maddison_project_database.py: gdp = gdppc x pop). Checked on 4 October 2026: OWID's gdp equals gdppc x pop from the workbook for all 3,795 country-years of this project's panel.
- Caveat for this project's gdp_per_capita. scripts/prepare_data.py divides gdp by OWID's population column, which is not the population series the Maddison Project used (its Sources sheet, under "Population sources": "1990 onward Total Economy Database the Conference Board for all countries included in TED. Otherwise UN national accounts statistics"; OWID's column is the UN series). The result is therefore Maddison GDP per person rescaled by the ratio of the two population series, not the Maddison Project's own GDP per person. Across the 3,795 panel country-years the absolute gap is 1.6% at the median, 6.9% at the 90th percentile and 50.9% at most; 16.7% of country-years differ by more than 5%. In 2022, 27 of the 115 countries differ by more than 5% and 10 by more than 10% (largest: Kuwait -33.3%, Georgia +29.4%, Oman -21.9%, Peru -20.0%, Cyprus -18.4%). For the focus countries in 2022 the gap is United States -2.4% (57,075 here, 58,487 in the database), India -5.4% (7,350 and 7,766), China -1.6%, Germany -0.3%, United Kingdom -0.1%, Sweden 0.0%. Growth from 1990 to 2022 is +56.3% here against +58.2% in the database for the United States and +263.1% against +272.1% for India; the other four agree within 0.6 percentage points.
- The original article's chart uses a different GDP series (World Bank, constant 2021 international-$); see 1.4.

population (people)

- Codebook: "Population by country, available from 10,000 BCE to 2100, based on data and estimates from different sources." Source: "Population based on various sources (2024)", https://ourworldindata.org/population-sources (Mathieu and Rodes-Guirao, 2022).
- That page lists the sources by period: 10,000 BCE to 1799 HYDE version 3.3; 1800 to 1949 Gapminder Population version 7; 1950 onwards UN World Population Prospects (2024); former countries from Gapminder Systema Globalis. This project uses 1990 to 2022 only, so its population is the UN series (United Nations, 2024). OWID's request: "If you cite population data for a specific period, please cite the source. For example, for the period 1950 onwards, please cite the UN World Population Prospects. You can add 'via Our World in Data' if you downloaded the data from us."
- Licence: UN World Population Prospects CC BY 3.0 IGO; HYDE and Gapminder CC BY 4.0 (as recorded in OWID's indicator metadata). For the UN series this was confirmed at the source: the footer of the UN's own download page says the data are "made available under a Creative Commons license CC BY 3.0 IGO: http://creativecommons.org/licenses/by/3.0/igo/" and gives "Suggested citation: United Nations, Department of Economic and Social Affairs, Population Division (2024). World Population Prospects 2024, Online Edition." The page is drawn by script; the wording was read in the content file it loads, https://population.un.org/wpp/assets/downloads.json .

country, year, iso_code

- Codebook sources: "Our World in Data - Regions (2024)" for country and year; "International Organization for Standardization - Regions (2023)" for iso_code (ISO 3166-1 alpha-3).

A note on how OWID cites the budget. OWID labels these columns "Global Carbon Budget (2025)", and its indicator metadata still points readers to the 2023 and 2024 budget papers. The paper that describes the 2025 budget was posted as a preprint on 13 November 2025, the day of OWID's snapshot, and published on 13 May 2026; it is Friedlingstein et al. (2026). The DataCite record of the budget's data supplement names that paper as the reference for the 2025 budget.

### 1.2 inputs/owid-co2-codebook.csv (the data dictionary)

- URL: https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-codebook.csv
- Retrieved: 4 October 2026
- SHA-256: 33b4f5e00efd58c7b83863f736beba1af4df946b43642b0400c3ec38648e0e8e
- Size and shape: 24,149 bytes; a header and 79 rows, one per column of the data file, with OWID's title, description, unit and source for each.
- Version: the last commit that changed it is 382ee6c662b0ece26e111f263b44c029afad7787, dated 2 June 2026 ("Update EIA data and change units of carbon intensity of energy (#56)").
- Licence and citation: as 1.1 (same repository, CC BY 4.0).
- Upstream: written by OWID. It is the authority for the source labels quoted in 1.1.

### 1.3 inputs/worldbank_country_classification.json (income groups and regions)

- URL: https://api.worldbank.org/v2/country?format=json&per_page=400
- Retrieved: 4 October 2026
- SHA-256: d29d57f8adf954c5e2a1520a02fb2c7b45575d8db3bd327a9dff47d66914231c
- Size and shape: 113,590 bytes; one page holding 295 entries: 217 economies and 78 aggregates. Each entry gives ISO codes, name, region, income level, lending type, capital city and coordinates. API documentation: Country API Queries, https://datahelpdesk.worldbank.org/knowledgebase/articles/898590-country-api-queries .
- Publisher: World Bank, Development Data Group.
- Licence: CC BY 4.0. World Bank Terms of Use for Datasets (https://www.worldbank.org/ext/en/legal/terms-conditions/datasets): "Unless specifically labeled otherwise, these Datasets are provided to you under a Creative Commons Attribution 4.0 International License (CC BY 4.0), with the additional terms below." The attribution it asks for: "The World Bank: Dataset name: Data source (if known)."
- Which classification is in the file: fiscal year 2027 (FY27), in force from 1 July 2026 to 30 June 2027 and based on 2025 gross national income (GNI) per capita in US dollars, World Bank Atlas method. Thresholds:
  - low income: 1,175 or less
  - lower-middle income: 1,176 to 4,635
  - upper-middle income: 4,636 to 14,375
  - high income: more than 14,375
  - (the year before, FY26, on 2024 incomes: 1,135 or less; 1,136 to 4,495; 4,496 to 13,935; more than 13,935)
- Where the thresholds were read, all four agreeing: the World Bank Data Help Desk page ("For the current 2027 fiscal year, low-income economies are defined as those with a GNI per capita, calculated using the World Bank Atlas method, of $1,175 or less in 2025; lower middle-income economies are those with a GNI per capita between $1,176 and $4,635; upper middle-income economies are those with a GNI per capita between $4,636 and $14,375; high-income economies are those with more than a GNI per capita of $14,375."); the document FY27 Updated Country Income Classification for Analytical Purposes; the notes sheet of the current-classification workbook (https://ddh-openapi.worldbank.org/resources/DR0095333/download); and the Thresholds sheet of the historical workbook (https://ddh-openapi.worldbank.org/resources/DR0095334/download).
- Changes that took effect on 1 July 2026 (FY27 document): Jordan, Micronesia, the Philippines, Sri Lanka and Viet Nam moved from lower-middle to upper-middle income; Togo moved from low to lower-middle income; no country moved down. Ethiopia and Venezuela, which were not classified in FY26, are classified in FY27 as low income and lower-middle income. Argentina and Turkiye "remain classified as upper-middle-income" because of "the limitations of the Atlas method in classifying countries experiencing persistent high inflation".
- Evidence that the downloaded file is the FY27 classification and not an older one: it has all eight of those results (JOR, FSM, PHL, LKA and VNM are UMC; TGO is LMC; ETH is LIC; VEN is LMC); its counts are 86 high, 59 upper-middle, 47 lower-middle and 25 low income, which are the FY27 list counts (87, 59, 47, 25; 218 economies) less one; and a code-by-code comparison with the current-classification workbook found the same income group for all 217 economies in the file.
- Caveat 1, Taiwan. The one economy missing from the API response is "Taiwan, China" (TWN), which the World Bank does classify, as high income: it is in the FY27 list of 87 high-income economies on the Help Desk page and in the workbook. Taiwan is in this project's panel, the join on iso_code finds no match, and it is left out of the income-group views. The accurate wording is "absent from the World Bank API response", not "not classified by the World Bank".
- Caveat 2, one label for all years. The file gives each economy its FY27 class only, and this project applies that class to every year from 1990 to 2022. The historical workbook (sheet Country Analytical History) shows what that hides. China and India were both low income on 1990 incomes (FY92). China was low income up to FY00 (lower-middle in FY99 only), lower-middle income from FY01 to FY11 and upper-middle income from FY12, the classification made on 2010 incomes; India was low income up to FY08 and has been lower-middle income since FY09, made on 2007 incomes. Of the 115 panel countries, 99 have a class for 1990 incomes, and 39 of those 99 fall in a different one of this project's three groups now than they did then (for example China, Indonesia, Vietnam and Sri Lanka from low to upper-middle income; Poland, Romania, Chile and South Korea up to high income; Venezuela down from upper-middle to lower-middle income). The other 16, all successor states of the Soviet Union, Yugoslavia and Czechoslovakia, had no class for 1990. The United States, United Kingdom, Germany, Sweden and Kuwait were high income in every year from FY89 to FY27.
- How to cite: World Bank (n.d.) for the classification and thresholds, World Bank (2026) for the FY27 changes, Metreau, Young, and Eapen (2026) for the explanation; all in section 4.

### 1.4 The original article's own material (four files)

All four come from Our World in Data and belong to the article being remixed (Ritchie, 2021; Appendix A). They are reproduced unaltered. Licence: CC BY 4.0. The two chart exports carry OWID's "CC BY" stamp in their footer, and the grid image says "Licensed under CC-BY by the author Max Roser". OWID's FAQ: "you can use, reproduce, and distribute any chart we made (those with our logo and CC BY copyright stamp), provided that you cite us", and "To cite one of our charts, cite the page that it's found on or that is linked to at the bottom of the chart." So credit the article (Ritchie, 2021) and, for the Grapher chart, the page linked in its footer (Ritchie, Rosado, and Roser, 2023).

OWID redraws Grapher charts whenever its data are updated. These exports show the chart as served on 4 October 2026, with data to 2025; they are not what a reader saw in December 2021, when the same chart ended in 2019.

inputs/original_owid_line_chart_gbr.png

- URL: https://ourworldindata.org/grapher/co2-emissions-and-gdp-per-capita.png?time=1750..latest&country=~GBR&imWidth=1700
- Retrieved: 4 October 2026
- SHA-256: 93025cfef550713a2b836512f03ee34801e9714d1122d709f7aa4c8a456c418f
- 147,318 bytes; PNG, 1700 x 1200 pixels. The article's first chart, "Change in per capita CO2 emissions and GDP", United Kingdom, as OWID's own PNG export.
- Data credit printed on the chart: "Data source: Eurostat, OECD, IMF, and World Bank (2026); Global Carbon Budget (2025); Population based on various sources (2024)"; "Note: GDP per capita is expressed in international-$ at 2021 prices."

inputs/original_owid_line_chart_gbr_chn.png

- URL: https://ourworldindata.org/grapher/co2-emissions-and-gdp-per-capita.png?time=1750..latest&country=GBR~CHN&imWidth=1700
- Retrieved: 4 October 2026
- SHA-256: a1b4e1de50f46cbf8fb4427c784e07067215eed2403fad0cf1777011febf18b1
- 123,173 bytes; PNG, 1700 x 1200 pixels. The same chart with China added through its country selection. It is not a view the article itself embeds; it documents how the chart behaves when a second country is added (one panel per country on a shared percent axis that here runs to +1,500%).

inputs/original_owid_line_chart_gbr.csv

- URL: https://ourworldindata.org/grapher/co2-emissions-and-gdp-per-capita.csv?v=1&csvType=filtered&useColumnShortNames=true&country=~GBR
- Retrieved: 4 October 2026
- SHA-256: 030693a6844f1bb69a9f8712b30794813ebec9c8c0810f5cfa797a7e8b6f8932
- 1,958 bytes; 36 rows (United Kingdom, 1990 to 2025) and three value columns. The data behind the chart, from the same Grapher endpoint.
- Upstream, from the chart's metadata (https://ourworldindata.org/grapher/co2-emissions-and-gdp-per-capita.metadata.json): ny_gdp_pcap_pp_kd is "GDP per capita, PPP (constant 2021 international $)", World Development Indicators, cited as "Eurostat, OECD, IMF, and World Bank (2026) - with minor processing by Our World in Data", 1990 to 2025; emissions_total_per_capita and consumption_emissions_per_capita are the Global Carbon Budget (2025) series divided by OWID population, the same series as co2_per_capita and consumption_co2_per_capita in 1.1 (scripts/original_story.py checks that they agree for the United Kingdom, 1990 to 2022).
- The GDP series is therefore not the one in the CO2 dataset: for the United Kingdom, 1990 to 2022, it rises 61.0% (World Bank, 2021 prices) against 46.1% for the series used in this project (Maddison, 2011 prices).

inputs/original_owid_arrow_grid.png

- URL: https://ourworldindata.org/cdn-cgi/imagedelivery/qLq-8BTgXU8yG0N6HnOy8g/f5db1a91-6bde-4430-3c09-e61fd8df9a00/w=2614
- Retrieved: 4 October 2026
- SHA-256: 361a92ace846b7e41c7351bc399eb0d9b636b4f2e5da985a71eedf9a9a04d6dc
- 410,955 bytes; PNG, 2614 x 2736 pixels. The article's static image, file name decoupling-economic-growth-and-emissions.png in OWID's system: "Decoupling: Countries that achieved economic growth while reducing CO2 emissions, 2005-20". The SHA-256 is identical to the hash OWID's own page metadata records for the image, so this is OWID's original file, not a resized copy.
- Data credit printed on the image: "Data sources: Global Carbon Project & World Bank."


## 2. Derived files

All four are written by scripts/prepare_data.py from inputs/owid-co2-data.csv and inputs/worldbank_country_classification.json. Its checks, and every number it reports, are in screenshots/logs/prepare_data.txt. Nothing is interpolated, imputed or smoothed.

Note added on 5 October 2026, after both passes above. The panel was narrowed from 115 countries to 110 by step 4 below, and this section now describes the 110-country panel. Three statements elsewhere in this file were computed on the 115 complete countries before that step and were not recomputed: the gdp = gdppc x pop check over 3,795 country-years and the population-series gap statistics (both under gdp in 1.1), and the count of countries whose income class changed since 1990 (1.3, caveat 2). The 110 are a subset of the 115, so the first still holds for every panel row; the other two are close but not exact for the smaller panel. None of the three is quoted in the report.

Steps

1. Read 13 columns of the raw file: country, year, iso_code, population, gdp, co2, co2_per_capita, consumption_co2, consumption_co2_per_capita, trade_co2, trade_co2_share, cumulative_co2, share_global_cumulative_co2.
2. Keep rows whose iso_code has three letters, which drops OWID's regional, income-group and other aggregates, and whose year is 1990 to 2022. The data fix the window: consumption-based emissions start in 1990 and the Maddison GDP series ends in 2022.
3. Keep a country only if population, gdp, co2, co2_per_capita, consumption_co2 and consumption_co2_per_capita are all present in all 33 years. 115 of the 218 countries pass; the rest are dropped.
4. Drop a country if, in any year, its consumption_co2 lies within 1 part in 100,000 of its co2. In 39 country-years the file repeats the production-based figure in the consumption-based column to six significant digits, which makes the net balance exactly zero: Belgium 1990-1998, Luxembourg 1990-1998, Botswana 1990-1999, South Africa 1990-1999 and Tunisia 2021. These read as placeholders and not as estimates (Belgium's balance goes from 0 to +56 Mt in 1999, the first year with a distinct figure). In the 110 countries that remain, the two accounts never come closer than 0.010% of production. Why the file holds these values was not traced to the Global Carbon Project's workbook.
5. Derive three variables, here and nowhere else:
   - gdp_per_capita = gdp / population (international-$ at 2011 prices per person; see the caveat under gdp in 1.1)
   - net_co2_per_capita = consumption_co2_per_capita - co2_per_capita (tonnes of CO2 per person)
   - net_co2_mt = consumption_co2 - co2 (million tonnes of CO2)
   A positive net balance means the country consumes more CO2 than it emits on its territory (a net importer of embodied emissions); a negative one means a net exporter.
6. Join the World Bank file on iso_code. region is taken as given. The income level is folded into three groups: HIC to "High income" (46 countries), UMC to "Upper-middle income" (30), LMC and LIC together to "Lower-middle and low income" (33). Taiwan gets no group (1.3, caveat 1).
7. Flag the six focus countries: United States, United Kingdom, Germany, Sweden, China, India.

Files

- inputs/decoupling_panel.csv: 3,630 rows (110 countries x 33 years) and 18 columns: country, iso_code, year, income_group, region, population, gdp, gdp_per_capita, co2, consumption_co2, co2_per_capita, consumption_co2_per_capita, net_co2_per_capita, net_co2_mt, trade_co2_share, cumulative_co2, share_global_cumulative_co2, is_focus.
- inputs/decoupling_focus.csv: 198 rows (6 countries x 33 years); the panel columns plus gdp_pc_change_pct, prod_change_pct and cons_change_pct, each the percent change since 1990 in GDP per person, production-based CO2 per person and consumption-based CO2 per person.
- inputs/decoupling_summary.csv: 6 rows, one per focus country, and 52 columns at the re-check (50 when this file was first written; the script was re-run in between, so count the header if the number matters): the 1990 and 2022 levels, the percent changes over 1990-2022, 1990-2007 and 2007-2022, the peak of consumption-based emissions, and the net balance per person and in million tonnes. These are the figures the report quotes.
- web/data/decoupling_data.js: the six focus series and, as context, the other 104 panel countries, written as one JavaScript assignment (window.DECOUPLING_DATA) for the D3 page.

Checks the script makes on its own arithmetic (all pass in the log): the panel is 110 x 33 = 3,630 rows with no missing value and no placeholder left; co2_per_capita = co2 x 1e6 / population and the same for consumption (worst relative gap about 1e-7); consumption_co2 - co2 equals OWID's trade_co2 (worst gap 0.0005 Mt).

scripts/original_story.py copies the three images of 1.4 into screenshots/ under the names the report uses, without resampling, and compares the chart's data with this project's.


## 3. The 1991 Kuwait anomaly

What the data show. In inputs/owid-co2-data.csv Kuwait's territorial CO2 is 37.86 Mt in 1990, 492.98 Mt in 1991 and 29.68 Mt in 1992 (364.8 tonnes per person in 1991). Its consumption-based CO2 in 1991 is 19.73 Mt, so OWID's trade_co2 for Kuwait in 1991 is -473.25 Mt, or -350.2 tonnes per person, the most negative balance in the panel.

Why. The 1991 figure contains the emissions of the Kuwaiti oil wells set alight in 1991, and it does so because OWID put them there. Three sources, all read on 4 October 2026:

1. Global Carbon Project documentation. Andrew and Peters (2025), section 5.1 "Kuwaiti oil fires", p. 31: "In the dataset there is one region that does not represent a territory, and that is 'Kuwaiti oil fires'. This represents the emissions from the >650 oil wells that were set alight by Iraqi troops as they retreated from Kuwait in 1991. The emissions from combustion of both oil and natural gas were estimated by CDIAC-FF to be 477 Mt CO2 (Andres et al., 1994). This region has non-zero emissions only in the year 1991." (Andres et al., 1994, is cited there and was not opened.)
2. The Global Carbon Project's data file, GCB2025v15_MtCO2_flat.csv in the same Zenodo record: Kuwait (KWT) 1991 total 15.054607 Mt; "Kuwaiti Oil Fires" (no ISO code) 1991 total 477.924832 Mt, of which oil 451.104352 and flaring 26.820480, and zero or blank in every other year. So in the Global Carbon Project's own national series the fires are not part of Kuwait.
3. OWID documentation. Dataset README, changelog entry 2022-11-11: "Added the emissions of the 1991 Kuwaiti oil fires in Kuwait's emissions (while also keeping 'Kuwaiti Oil Fires (GCP)' as a separate entity), to properly account for these emissions in the aggregate of Asia." Indicator metadata for CO2 emissions (for example https://api.ourworldindata.org/v1/indicators/1119914.metadata.json, field descriptionProcessing): "Emissions from the 1991 Kuwaiti oil fires are included in Kuwait's emissions for that year." The pipeline code that does it is etl/steps/data/garden/gcp/2025-11-13/global_carbon_budget.py in https://github.com/owid/etl .

The arithmetic closes: 15.054607 + 477.924832 = 492.979439 Mt, which is the 492.979 Mt in the OWID file. The OWID file also still carries the entity "Kuwaiti Oil Fires (GCP)" with 477.92 Mt in 1991; it has no ISO code, so this project's panel never counts it twice.

What it does to this project. The fires are added to the territorial series only. The consumption-based series comes from the Global Carbon Project's national workbook and does not contain them, and OWID computes trade_co2 as consumption minus territorial. Kuwait therefore appears in 1991 as a net exporter of 473 Mt of embodied CO2. That is an artefact of the merge, not a trade flow: against the Global Carbon Project's own territorial figure the 1991 balance would be 19.73 - 15.05 = +4.68 Mt, a small net import. The national workbook OWID ingested (1.1) says so itself: its Territorial Emissions sheet has Kuwait 1991 at 4.1088 MtC (15.05 Mt CO2), it has no oil-fires column, and its Emissions Transfers sheet gives Kuwait 1991 as -1.2760 MtC, which is -4.68 Mt CO2 in the workbook's sign (net exporter positive), a net import of 4.68 Mt. In this project's income-group totals it is enough to turn the high-income group's balance negative for that one year: -12.2 Mt with Kuwait, +461.0 Mt without (screenshots/logs/prepare_data.txt). Kuwait's 1991 point should be annotated or set aside wherever the net balance is plotted, and described as oil-fire emissions that OWID assigns to Kuwait, not as exports.


## 4. Verified bibliography (APA 7)

Alphabetical. Each entry is followed by one line saying how it was verified. In-text notes: (a) two works shorten to "Peters et al. (2011)", so write "Peters, Minx, et al. (2011)" for the PNAS paper and "Peters, Andrew, and Lennox (2011)" for the method paper; (b) the Global Carbon Budget 2025 is cited as Friedlingstein et al. (2026), because the peer-reviewed paper appeared in May 2026; (c) the Maddison paper is Bolt and van Zanden (2025), the year of the journal volume it sits in, although the database's own page still calls it "Bolt and Van Zanden (2024)" after its online date (see the entry).

Andrew, R. M., & Peters, G. P. (2013). A multi-region input-output table based on the Global Trade Analysis Project database (GTAP-MRIO). Economic Systems Research, 25(1), 99-121. https://doi.org/10.1080/09535314.2012.761953
Verified: Crossref record for the DOI (journal, volume 25, issue 1, pages 99-121, March 2013); cited as the model description in the Global Carbon Budget 2025 supplement, section S.1.2.

Andrew, R. M., & Peters, G. P. (2025). The Global Carbon Project's fossil CO2 emissions dataset (Version 2025v15) [Data set]. Zenodo. https://doi.org/10.5281/zenodo.17417124
Verified: Zenodo record 17417124 (title, authors, version 2025v15, published 22 October 2025, CC BY 4.0) and two of its files, downloaded: the data file, of which the Kuwait rows were read, and the PDF documentation, of which section 5.1 on p. 31 is the Kuwaiti oil fires statement; the DOI for all versions is 10.5281/zenodo.5569234.

Becker, R. A., & Cleveland, W. S. (1987). Brushing scatterplots. Technometrics, 29(2), 127-142. https://doi.org/10.1080/00401706.1987.10488204
Verified: Crossref record for the DOI (volume 29, issue 2, May 1987, pages 127-142) and a scan of the article in the Technometrics archive of Carnegie Mellon University's statistics department (https://www.stat.cmu.edu/technometrics/80-89/VOL-29-02/v2902127.pdf), where every passage in Appendix B was read on the page cited; the publisher and JSTOR pages refused the request.

Bolt, J., & van Zanden, J. L. (2025). Maddison-style estimates of the evolution of the world economy: A new 2023 update. Journal of Economic Surveys, 39(2), 631-671. https://doi.org/10.1111/joes.12618
Verified: Crossref record for the DOI (authors, title, journal; first published online 3 April 2024; volume 39, issue 2, pages 631-671, issue dated April 2025) and the Maddison Project Database 2023 page of the Groningen Growth and Development Centre. Year: corrected at the re-check from 2024 to 2025. APA dates a journal article by the year of its volume, and volume 39 is the 2025 volume, so an entry that gives 39(2), 631-671 takes 2025. The rule was read in a library guide to APA 7 ("For articles, use the year of the volume (also known as the 'publication date')", Red Deer Polytechnic Library, Which date do I use in my citation?, https://answers.rdpolytech.ca/faq/211915 ); the Publication Manual itself was not opened. The year 2024 belongs to the early-view version, which is what the database page asks for ("Bolt, Jutta and Jan Luiten van Zanden (2024), ..., Journal of Economic Surveys, 1-41. DOI: 10.1111/joes.12618") and what the DOI registry's own formatter prints; it is the same paper under the same DOI. Whichever year is used, the in-text citations and the reference list must show the same one.

Bostock, M., Ogievetsky, V., & Heer, J. (2011). D3: Data-driven documents. IEEE Transactions on Visualization and Computer Graphics, 17(12), 2301-2309. https://doi.org/10.1109/TVCG.2011.185
Verified: Crossref record for the DOI (volume 17, issue 12, December 2011, pages 2301-2309) and the Stanford Vis Group paper page (title and full author names); the published title is typeset with a superscript 3.

Cleveland, W. S., & McGill, R. (1984). Graphical perception: Theory, experimentation, and application to the development of graphical methods. Journal of the American Statistical Association, 79(387), 531-554. https://doi.org/10.1080/01621459.1984.10478080
Verified: Crossref record for the DOI and a JSTOR scan of the whole article (stable URL http://www.jstor.org/stable/2288400); every passage in Appendix B was read on the page cited, and those are the printed journal pages.

Davis, S. J., & Caldeira, K. (2010). Consumption-based accounting of CO2 emissions. Proceedings of the National Academy of Sciences, 107(12), 5687-5692. https://doi.org/10.1073/pnas.0906974107
Verified: Crossref record for the DOI (volume 107, issue 12, 23 March 2010, pages 5687-5692); cited in the Global Carbon Budget 2025 supplement, section S.1.2, as an example of consumption-based attribution. The article itself was not read.

Friedlingstein, P., O'Sullivan, M., Jones, M. W., Andrew, R. M., Bakker, D. C. E., Hauck, J., Landschutzer, P., Le Quere, C., Li, H., Luijkx, I. T., Peters, G. P., Peters, W., Pongratz, J., Schwingshackl, C., Sitch, S., Canadell, J. G., Ciais, P., Aas, K., Alin, S. R., ... Zeng, J. (2026). Global Carbon Budget 2025. Earth System Science Data, 18(5), 3211-3288. https://doi.org/10.5194/essd-18-3211-2026
Verified: Crossref record for the DOI (133 authors; volume 18, issue 5, pages 3211-3288; published 13 May 2026) and the Copernicus article page, where section 2.1, Table 2, the data availability section and supplement section S.1.2 were read; the preprint of the same title is https://doi.org/10.5194/essd-2025-659, posted 13 November 2025.

Global Carbon Project. (2025). Supplemental data of Global Carbon Budget 2025 (Version 1.0) [Data set]. https://doi.org/10.18160/GCP-2025
Verified: DataCite record for the DOI (creator and publisher Global Carbon Project; issued 13 November 2025; CC BY 4.0) and the ICOS Carbon Portal page the DOI resolves to. Version: corrected at the re-check from 1.1 to 1.0. Year and version are the ones that page displayed for the release OWID ingested: its Internet Archive captures of 13 November 2025 and 23 January 2026 both read "Citation: Global Carbon Project. (2025). Supplemental data of Global Carbon Budget 2025 (Version 1.0) [Data set]. Global Carbon Project. https://doi.org/10.18160/gcp-2025". "1.1" is only the version field of the DataCite metadata, which also carry an "Updated" date of 15 January 2026 and were last modified on 17 May 2026; neither of the two captures nor the live page carries that label, and no file is named so (between the two captures the one file that changed was the global budget workbook, v0.3 to v0.7; the national workbook was the same ICOS object). The record has moved on since: on 17 May 2026 ICOS replaced the national workbook (v0.1, released 13 November 2025) with v1.0, DataCite now gives publication year 2026, and the page now reads "Global Carbon Project. (2026). Supplemental data of Global Carbon Budget 2025 (Version 1.0) [Data set]. Global Carbon Project." Use that 2026 form only for work based on the May 2026 files. The paper itself cites the supplement as Friedlingstein et al., 2025c. The workbook behind OWID's consumption series is identified by md5 in section 1.1. UNVERIFIED part: the two ICOS copies of the national workbook (v0.1 and v1.0) were not opened, because ICOS serves them only after a licence click-through that was not accepted for this check, so whether their national values equal those of the v0.3 file OWID used is not known.

Haberl, H., Wiedenhofer, D., Virag, D., Kalt, G., Plank, B., Brockway, P., Fishman, T., Hausknost, D., Krausmann, F., Leon-Gruchalski, B., Mayer, A., Pichler, M., Schaffartzik, A., Sousa, T., Streeck, J., & Creutzig, F. (2020). A systematic review of the evidence on decoupling of GDP, resource use and GHG emissions, part II: Synthesizing the insights. Environmental Research Letters, 15(6), Article 065003. https://doi.org/10.1088/1748-9326/ab842a
Verified: Crossref record for the DOI (16 authors; volume 15, issue 6, article 065003, June 2020), including the publisher-deposited abstract quoted in Appendix B; the body of the article was not read. Part I of the review is https://doi.org/10.1088/1748-9326/ab8429 .

Haroz, S., Kosara, R., & Franconeri, S. L. (2016). The connected scatterplot for presenting paired time series. IEEE Transactions on Visualization and Computer Graphics, 22(9), 2174-2186. https://doi.org/10.1109/TVCG.2015.2502587
Verified: Crossref record for the DOI (volume 22, issue 9, September 2016, pages 2174-2186) and the authors' own PDF of the paper (https://media.eagereyes.org/papers/2016/Haroz-TVCG-2016.pdf), where every passage in Appendix B was read. UNVERIFIED part: that PDF has 11 pages and the journal version 13, so Appendix B locates findings by section number and by page of the authors' PDF, not by journal page.

Heer, J., & Shneiderman, B. (2012). Interactive dynamics for visual analysis. Communications of the ACM, 55(4), 45-54. https://doi.org/10.1145/2133806.2133821
Verified: Crossref record for the DOI (volume 55, issue 4, April 2012, pages 45-54) and the article PDF from the University of Washington Interactive Data Lab, where pages 45, 46 and 50 were read; the same article first ran in ACM Queue 10(2), pages 30-55, under https://doi.org/10.1145/2133416.2146416, so keep the DOI and pages given here together.

Hubacek, K., Chen, X., Feng, K., Wiedmann, T., & Shan, Y. (2021). Evidence of decoupling consumption-based CO2 emissions from economic growth. Advances in Applied Energy, 4, Article 100074. https://doi.org/10.1016/j.adapen.2021.100074
Verified: Crossref record for the DOI and the publisher's version of record (open access, CC BY; University of Birmingham repository copy, Advances in Applied Energy 4 (2021) 100074, available online 30 October 2021), where the abstract, introduction, the results on p. 5 and the conclusions were read.

Hunter, J. D. (2007). Matplotlib: A 2D graphics environment. Computing in Science & Engineering, 9(3), 90-95. https://doi.org/10.1109/MCSE.2007.55
Verified: Crossref record for the DOI (volume 9, issue 3, 2007, pages 90-95; author John D. Hunter). The article itself was not read.

Le Quere, C., Korsbakken, J. I., Wilson, C., Tosun, J., Andrew, R., Andres, R. J., Canadell, J. G., Jordan, A., Peters, G. P., & van Vuuren, D. P. (2019). Drivers of declining CO2 emissions in 18 developed economies. Nature Climate Change, 9(3), 213-217. https://doi.org/10.1038/s41558-019-0419-7
Verified: Crossref record for the DOI and the Nature landing page (10 authors; volume 9, issue 3, pages 213-217; online 25 February 2019), including the abstract. The article is paywalled, so the passages in Appendix B come from the authors' accepted manuscript in the IIASA repository (https://pure.iiasa.ac.at/id/eprint/15783/), whose wording may differ slightly from the published text.

Machado, G. M., Oliveira, M. M., & Fernandes, L. A. F. (2009). A physiologically-based model for simulation of color vision deficiency. IEEE Transactions on Visualization and Computer Graphics, 15(6), 1291-1298. https://doi.org/10.1109/TVCG.2009.113
Verified: Crossref record for the DOI (volume 15, issue 6, November 2009, pages 1291-1298) and the authors' project page at UFRGS, which gives the full author names and the same volume, number and pages; Crossref abbreviates the third author to L. Fernandes.

Mathieu, E., & Rodes-Guirao, L. (2022, February 8). What are the sources for Our World in Data's population estimates? Our World in Data. https://ourworldindata.org/population-sources
Verified: the OWID page itself (title, authors, publication date 2022/02/08 in its citation metadata, and its own Cite this work text, which gives 2022). The page's dateline reads "This article was first published in 2022, and last revised in August 2024", which is why a 2022 article lists UN World Population Prospects 2024; the list of sources quoted in 1.1 is the revised text.

Metreau, E., Young, K. E., & Eapen, S. G. (2026, July 1). Who moves up and why? A closer look at the 2026-2027 release of the World Bank Group country income classifications. World Bank Data Blog. https://blogs.worldbank.org/en/opendata/who-moves-up-and-why--a-closer-look-at-the-new-world-bank-group-
Verified: the blog page itself (headline, three authors, dated July 01, 2026).

Munzner, T. (2014). Visualization analysis and design. A K Peters/CRC Press. https://doi.org/10.1201/b17511
Verified: Crossref record for the DOI (book; publisher A K Peters/CRC Press; issued 1 December 2014) and the author's own book page at the University of British Columbia ("A K Peters Visualization Series, CRC Press, 2014"). UNVERIFIED part: the book was not opened, so no page numbers are given for anything taken from it.

Peters, G. P., Andrew, R., & Lennox, J. (2011). Constructing an environmentally-extended multi-regional input-output table using the GTAP database. Economic Systems Research, 23(2), 131-152. https://doi.org/10.1080/09535314.2011.563234
Verified: Crossref record for the DOI (volume 23, issue 2, June 2011, pages 131-152); cited as the method ("Peters et al., 2011b") in the Global Carbon Budget 2025 supplement, section S.1.2. The article itself was not read.

Peters, G. P., Davis, S. J., & Andrew, R. (2012). A synthesis of carbon in international trade. Biogeosciences, 9(8), 3247-3276. https://doi.org/10.5194/bg-9-3247-2012
Verified: Crossref record for the DOI (volume 9, issue 8, 23 August 2012, pages 3247-3276); cited for the uncertainty of consumption-based estimates ("Peters et al., 2012b") in the Global Carbon Budget 2025 supplement, section S.1.2. The article itself was not read.

Peters, G. P., Minx, J. C., Weber, C. L., & Edenhofer, O. (2011). Growth in emission transfers via international trade from 1990 to 2008. Proceedings of the National Academy of Sciences, 108(21), 8903-8908. https://doi.org/10.1073/pnas.1006388108
Verified: Crossref record for the DOI (volume 108, issue 21, 24 May 2011, pages 8903-8908; online 25 April 2011), including the publisher-deposited abstract, and the full text at PubMed Central (PMC3102371). UNVERIFIED part: the PDF could not be downloaded, so only the abstract is tied to a page (p. 8903); other figures in Appendix B are located by section and table.

Ritchie, H. (2021, December 1). Many countries have decoupled economic growth from CO2 emissions, even if we take offshored production into account. Our World in Data. https://ourworldindata.org/co2-gdp-decoupling
Verified: the article page itself (heading, byline, dateline December 1, 2021, citation metadata 2021/12/01, Cite this work text) and the Internet Archive capture of 3 December 2021, which carries the same title; OWID asks that its archived copy be cited, https://archive.ourworldindata.org/20260910-012235/co2-gdp-decoupling.html (archived on September 10, 2026), whose text is identical to the live page read on 4 October 2026.

Ritchie, H., Rosado, P., & Roser, M. (2023). CO2 and greenhouse gas emissions. Our World in Data. https://ourworldindata.org/co2-and-greenhouse-gas-emissions
Verified: the OWID topic page itself (its Cite this work text gives these authors and the year 2023); this is the citation the dataset README and the OWID FAQ ask for when OWID data or charts are reused.

Roberts, J. C. (2007). State of the art: Coordinated & multiple views in exploratory visualization. In G. Andrienko, J. C. Roberts, & C. Weaver (Eds.), Fifth International Conference on Coordinated and Multiple Views in Exploratory Visualization (CMV 2007) (pp. 61-71). IEEE. https://doi.org/10.1109/CMV.2007.20
Verified: Crossref record for the DOI (proceedings article; pages 61-71; publisher IEEE; conference held in Zurich on 2 July 2007) and the Kent Academic Repository record of the paper (https://kar.kent.ac.uk/14569/), which names the three editors and holds a copy where the passages in Appendix B were read. UNVERIFIED part: that copy has no page numbers and its version is not stated, so Appendix B locates passages by section.

Rosado, P., Ritchie, H., Roser, M., Mathieu, E., & Macdonald, B. (2026). Data on CO2 and greenhouse gas emissions by Our World in Data [Data set]. Our World in Data. https://github.com/owid/co2-data
Verified: the repository README (title, the five people it names as having collected, aggregated and documented the data, CC BY licence) and the GitHub API (last commit 382ee6c on 2 June 2026); the repository has no releases, so the year is that of the last change, and OWID's preferred citation for the data is Ritchie, Rosado, and Roser (2023).

Satyanarayan, A., Moritz, D., Wongsuphasawat, K., & Heer, J. (2017). Vega-Lite: A grammar of interactive graphics. IEEE Transactions on Visualization and Computer Graphics, 23(1), 341-350. https://doi.org/10.1109/TVCG.2016.2599030
Verified: Crossref record for the DOI (volume 23, issue 1, January 2017, pages 341-350) and the University of Washington Interactive Data Lab paper page (title, authors, abstract).

Segel, E., & Heer, J. (2010). Narrative visualization: Telling stories with data. IEEE Transactions on Visualization and Computer Graphics, 16(6), 1139-1148. https://doi.org/10.1109/TVCG.2010.179
Verified: Crossref record for the DOI (volume 16, issue 6, November 2010, pages 1139-1148) and the Stanford Vis Group paper page (authors Edward Segel and Jeffrey Heer, abstract); Crossref gives initials only.

Tufte, E. R. (1990). Envisioning information. Graphics Press.
Verified: the publisher's own page (Graphics Press, Cheshire, Connecticut: "Edward R. Tufte | 1990", 126 pages, topics include small multiples) and library catalogue records (Open Library and Internet Archive: Graphics Press, 1990, LCCN 90166920). The small-multiples passage in Appendix B was checked at the re-check against the scanned book, though not by opening it: the Internet Archive's full-text search of its scans (items envisioninginfor00tuft, which is the LCCN 90166920 copy, envisioninginfor0000edwa and envisioninginfor0000edwa_p0q0) returns every phrase of the passage, shows it following directly on the caption of the chapter's opening illustration ("4 Small Multiples 67 ... In this splendid 1659 drawing by Christiaan Huygens ... a superior small multiple design. At the heart of quantitative reasoning ..."), and the contents page reads "Layering and Separation 53 Small Multiples 67 Color and Information 81". So the passage opens the chapter Small Multiples, and the chapter begins on p. 67. UNVERIFIED part: the scans are lending copies and were read only as search snippets (optical character recognition), so punctuation was not checked against the page image, and that the whole passage sits on p. 67 and does not run over to p. 68 is inferred from the snippets, not seen.

United Nations, Department of Economic and Social Affairs, Population Division. (2024). World population prospects 2024, online edition [Data set]. https://population.un.org/wpp/
Verified at the re-check: the UN website draws its pages by script, but the content file its download page loads (https://population.un.org/wpp/assets/downloads.json) is plain text and carries, for the 2024 files, "Suggested citation: United Nations, Department of Economic and Social Affairs, Population Division (2024). World Population Prospects 2024, Online Edition." and the licence line "made available under a Creative Commons license CC BY 3.0 IGO". OWID's population-sources page gives the same citation. The same file announces an interim update of 19 January 2026 that revises the population of Togo only; every other country is unchanged.

VanderPlas, J., Granger, B. E., Heer, J., Moritz, D., Wongsuphasawat, K., Satyanarayan, A., Lees, E., Timofeev, I., Welsh, B., & Sievert, S. (2018). Altair: Interactive statistical visualizations for Python. Journal of Open Source Software, 3(32), Article 1057. https://doi.org/10.21105/joss.01057
Verified: Crossref record for the DOI and the journal's paper page (10 authors, volume 3, issue 32, article 1057, published 10 December 2018).

Waskom, M. L. (2021). seaborn: Statistical data visualization. Journal of Open Source Software, 6(60), Article 3021. https://doi.org/10.21105/joss.03021
Verified: Crossref record for the DOI and the journal's paper page (author Michael L. Waskom, volume 6, issue 60, article 3021, published 6 April 2021); the published title is in lower case throughout.

World Bank. (n.d.). World Bank country and lending groups. World Bank Data Help Desk. Retrieved October 4, 2026, from https://datahelpdesk.worldbank.org/knowledgebase/articles/906519-world-bank-country-and-lending-groups
Verified: the page itself as served on 4 October 2026 ("For the current 2027 fiscal year ...", the four thresholds, and lists of 25, 47, 59 and 87 economies); the page is undated and rewritten every 1 July, hence n.d. with a retrieval date.

World Bank. (2026). FY27 updated country income classification for analytical purposes. https://documents1.worldbank.org/curated/en/099063026190549947/pdf/BOSIB-8ff63426-3c40-412d-bad2-cc20a4ebea81.pdf
Verified: the PDF itself (title, old and new thresholds, the six reclassifications, country notes; file created 1 July 2026); it carries no author, report number or DOI.


## 5. Appendix A: the original article, as verified

Everything here was read from https://ourworldindata.org/co2-gdp-decoupling and the files it loads on 4 October 2026, unless a different source is named.

### A.1 Identity

- Title: Many countries have decoupled economic growth from CO2 emissions, even if we take offshored production into account. (On the page CO2 has a subscript 2.)
- Standfirst: "It is possible to reduce emissions while growing the economy. But this decoupling needs to happen faster."
- Author and date: "By Hannah Ritchie", "December 1, 2021". Page metadata: citation_publication_date 2021/12/01, datePublished 2021-12-01T08:30:00Z. OWID last touched the document on 10 August 2026.
- Topic tags: CO2 & Greenhouse Gas Emissions; Economic Growth.
- The assignment brief's title, "Are countries really decoupling economic growth from emissions?", is not the title of this article. The phrase is not on the page, in the first or the last of OWID's own archived copies, or in the Internet Archive capture made two days after publication (https://web.archive.org/web/20211203070416/https://ourworldindata.org/co2-gdp-decoupling), which already has today's title; a web search for the exact phrase found no OWID page with it. Treat it as a paraphrase of the article's question and cite the article by its real title.
- How OWID asks for it to be cited (its Cite this work box, CO2 written plainly here): Hannah Ritchie (2021) - "Many countries have decoupled economic growth from CO2 emissions, even if we take offshored production into account" Published online at OurWorldinData.org. Retrieved from: 'https://archive.ourworldindata.org/20260910-012235/co2-gdp-decoupling.html' [Online Resource] (archived on September 10, 2026). The box adds: "When citing this article, please also cite the underlying data sources." Its BibTeX entry has author = {Hannah Ritchie}, journal = {Our World in Data}, year = {2021}.
- Licence: "All visualizations, data, and articles produced by Our World in Data are completely open access under the Creative Commons BY license."
- Size: ten paragraphs, 418 words, two embedded interactive charts, one static image, then a "Related charts" block with two links. There are no footnotes and no reference list; data sources are named only in the chart footers.
- The article has changed since 2021. The capture of 3 December 2021 has one chart only (the United Kingdom line chart, then ending in 2019) and no static grid; it told readers to use the "Change country" button and, for the United States, to look at the change since 2000 "by adjusting the time-slider on the bottom of the chart". Today's text says "Edit countries and regions", no longer mentions the time slider, and adds the grid image. OWID's archive lists 29 archived versions between 25 November 2025 and 10 September 2026. The last of them is identical to the live page in title, standfirst and all ten paragraphs. The first has the same ten paragraphs; it differs only outside the article's argument: its title prints CO2 without the subscript, the two "Related charts" links carry a generic caption, and the site's licence wording is older. A critique should say it describes the page as it stood on 4 October 2026.

### A.2 Chart 1: interactive line chart, United Kingdom

- What it is: an embedded OWID Grapher chart, https://ourworldindata.org/grapher/co2-emissions-and-gdp-per-capita, opened with country=~GBR and time=1750..latest. Saved copy: inputs/original_owid_line_chart_gbr.png.
- Title: "Change in per capita CO2 emissions and GDP", with "United Kingdom" beside it. Subtitle: "Consumption-based emissions include those from fossil fuels and industry. Land-use change emissions are not included. GDP per capita is adjusted for inflation and differences in living costs between countries."
- Chart type: line chart of relative change. The chart configuration sets stackMode to "relative", so every line is the percent change from its own value in the first year shown.
- x axis: year, 1990 to 2025, labelled every five years. The configuration sets timelineMinTime to 1990, so 1990 is the earliest year the chart will show.
- y axis: percent change since the first year, from -60% to +60% in steps of 20, with the 0% line drawn solid. The axis carries percent only; no value in tonnes or dollars is plotted (the footer note names the GDP unit).
- Series, three lines on the one axis, labelled directly at their right-hand ends, with a marker at every year: "GDP per capita" (#00295b, navy), "CO2 emissions per capita" (#4c6a9c, slate blue; this is the territorial, production-based series) and "Consumption-based CO2 emissions per capita" (#b13507, orange-red).
- The three lines end in three different years: GDP in 2025, territorial CO2 in 2024, consumption-based CO2 in 2023.
- Values at the ends of the lines, computed from the chart's own data file: GDP per capita +61.0% (1990 to 2025), CO2 per capita -56.9% (1990 to 2024), consumption-based CO2 per capita -38.9% (1990 to 2023). The exported chart prints no values; a reader of it gets them only by reading the line ends against the gridlines.
- Levels behind the index, from the same file: in 1990 the United Kingdom's consumption-based emissions were 11.61 tonnes per person and its territorial emissions 10.49. Both lines nevertheless start at 0%, so the vertical gap between them is not the trade balance, and the chart cannot show that the United Kingdom was already a net importer in 1990.
- Footer: "Data source: Eurostat, OECD, IMF, and World Bank (2026); Global Carbon Budget (2025); Population based on various sources (2024)"; "Note: GDP per capita is expressed in international-$ at 2021 prices."; "OurWorldinData.org/co2-and-greenhouse-gas-emissions | CC BY".

### A.3 Chart 2: the same chart with its default countries

- What it is: the same Grapher chart embedded a second time, without a country parameter, so it shows its default selection.
- Six countries, one panel each, in a grid of three columns by two rows: United Kingdom, France, Germany, Sweden, United States, Finland. The configuration sets selectedFacetStrategy to "entity", which means one panel per country.
- Every panel has the same three lines and the same axes: x from 1990 to 2025, y from -60% to +80% on a scale shared by all six panels. A legend above the grid replaces the direct labels, and the year markers are gone.
- Because the percent scale is shared, one fast-growing country flattens all the others. With China added to the United Kingdom (inputs/original_owid_line_chart_gbr_chn.png) both panels run from 0% to +1,500% and the three United Kingdom lines become nearly indistinguishable from the zero line.

### A.4 Chart 3: static grid of arrows

- What it is: a PNG image, 2614 x 2736 pixels, not interactive. Saved copy: inputs/original_owid_arrow_grid.png.
- Title: "Decoupling: Countries that achieved economic growth while reducing CO2 emissions, 2005-20". Subtitle: "Emissions are adjusted for trade. This means that CO2 emissions caused in the production of imported goods are added to its domestic emissions - and for goods that are exported the emissions are subtracted. Average incomes are measured by GDP per capita (except for Ireland, for which it is measured by GNI per capita)."
- Layout: 30 panels in five rows of six, one country each, in order of the size of the fall in emissions.
- Each panel: two arrows from one starting point. A blue arrow points up to a printed percentage, the "Increase in average incomes per person"; a red arrow points down to a printed percentage, the "Decrease in CO2 emissions per person". The two arrows are explained only in the first panel (Ireland).
- No axes, ticks or gridlines. Measured on the image, the arrow heads do sit on one vertical scale common to all 30 panels (roughly 3 pixels per percentage point: a median of 3.2 for the blue arrows and 3.0 for the red ones when measured again at the re-check) and every arrow spans the same width, but that scale is nowhere drawn, so the values can be read only from the printed labels.
- Only two years are compared, 2005 and 2020. The path between them is not shown. 2020 is the first year of the COVID-19 pandemic.
- Only consumption-based emissions are shown; there is no territorial series in this figure.
- Selection rule, printed on the image: "There are more countries that achieved the same, but only those countries for which data is available and for which each change exceeded 5% are shown." Countries that did not decouple are not shown at all.
- Sources and credit printed on the image: "Data sources: Global Carbon Project & World Bank."; "Licensed under CC-BY by the author Max Roser".
- The 30 panels (income change, emissions change): Ireland +43%, -50%; Finland +5%, -44%; Sweden +12%, -41%; Denmark +8%, -41%; Netherlands +10%, -35%; Estonia +35%, -34%; USA +10%, -32%; Canada +10%, -31%; Germany +17%, -29%; Belgium +5%, -28%; New Zealand +15%, -24%; Israel +30%, -23%; Japan +5%, -22%; Singapore +39%, -21%; Dominican Republic +65%, -20%; Hungary +27%, -20%; Australia +15%, -19%; Zimbabwe +15%, -19%; Ukraine +9%, -19%; Bulgaria +51%, -16%; Switzerland +12%, -16%; Hong Kong +29%, -15%; Slovakia +52%, -14%; Romania +72%, -12%; Czech Republic +27%, -12%; Nicaragua +22%, -8%; Nigeria +23%, -8%; Azerbaijan +93%, -7%; Slovenia +19%, -6%; Croatia +14%, -6%.
- The United Kingdom, the article's lead example, is not among the 30; nor are France and Italy, which the text also names. In the data behind today's line chart the United Kingdom's GDP per capita changes by -0.8% from 2005 to 2020, under the grid's 5% rule, but by +10.5% from 2005 to 2019; its consumption-based emissions per capita change by -44.8% and -38.1%. The grid was drawn from an earlier vintage of the data, so this explains the absence only as far as today's data go.

### A.5 Related links, not charts in the article

The prose carries six text links, all to Our World in Data's own pages, and none of them is embedded. Two of them, and not one as first recorded here, open a view that compares countries on levels:

- Paragraph 1, "strongly correlated with": the scatterplot "CO2 emissions per capita vs. GDP per capita" (https://ourworldindata.org/grapher/co2-emissions-vs-gdp), production-based emissions against GDP, all countries in one coordinate system.
- Paragraph 3, "without per capita adjustments": "Change in CO2 emissions and GDP" for the United Kingdom (https://ourworldindata.org/grapher/co2-emissions-and-gdp?country=~GBR), the same kind of chart for totals.
- Paragraph 7, "have managed to": the article "How much energy do countries consume when we take offshoring into account?" (Ritchie, 7 December 2021, https://ourworldindata.org/energy-offshoring).
- Paragraph 7, "are replacing": the chart "Low-carbon energy as a share of total energy supply" for the United States, United Kingdom, China, World, India, Brazil and South Africa (https://ourworldindata.org/grapher/energy-mix with source=low_carbon_energy and metric=share).
- Paragraph 8, "consumption-based emissions": the CO2 Data Explorer opened on its map tab with Accounting=Consumption-based and Count=Per country (https://ourworldindata.org/explorers/co2?tab=map&...), that is, a world map of consumption-based CO2 in tonnes per country. This is a cross-country view of the trade-adjusted level; the same explorer also offers "Share of emissions embedded in trade", one selection away.
- Paragraph 10, "decline in the cost": the article "Why did renewables become so cheap so fast?" (Roser, 1 December 2020, https://ourworldindata.org/cheap-renewables-growth).
- "Related charts" block: "Change in per capita CO2 emissions and GDP" (long-run version, opened for Germany from 1890) and "Change in CO2 emissions and GDP" (totals, not per capita, opened for the United Kingdom; the same link as in paragraph 3).

The linked pages were identified by their titles and URL parameters; they were not operated.

### A.6 What the reader can and cannot change

- Country: yes. The text says: "Using the 'Edit countries and regions' button on the chart, you can see this for yourself."
- Time window: yes, by configuration. The Grapher schema's default is to show the timeline (hideTimeline is false by default and the chart does not override it), limited to 1990 onwards. Moving the start of the window also moves the base year of the index, which is how the 2021 text told readers to see the change "since 2000".
- Relative or absolute: no, by configuration. The schema's default hides the control that switches relative mode off (hideRelativeToggle is true by default and the chart does not override it), so the chart shows percent change only.
- Map: no (hasMapTab is false by default).
- Linking: none. The two embeds are independent copies of the same chart; a selection in one does nothing to the other, and nothing connects either to the static grid.
- Basis for this list: the published chart configuration (https://ourworldindata.org/grapher/co2-emissions-and-gdp-per-capita.config.json), the schema it names (https://files.ourworldindata.org/schemas/grapher-schema.011.json) and the article's text. The chart was not operated in a browser for this file, and the re-check did not operate it either. The list is therefore not exhaustive: the configuration does not set chartTypes, whose schema default is a line chart plus a discrete bar chart, and Grapher's table view, download and settings controls were not examined.

### A.7 Main claims, in the article's words

1. "Historically, CO2 emissions have been strongly correlated with how much money we have. This is particularly true for low-to-middle incomes. The richer we are, the more CO2 we emit."
2. "But this relationship no longer holds true at higher incomes. Many countries have managed to achieve economic growth while reducing emissions. They have decoupled the two."
3. "We see that the UK's GDP has increased a lot over the last 30 years while its emissions have fallen."
4. "It's not just the UK. Many other countries have achieved this decoupling. ... France, Germany, Sweden, Finland, Denmark, Italy, Czechia, and Romania are examples of countries where we see this."
5. "This decoupling is even more pronounced over the past two decades, since the turn of the millennium. Consumption-based emissions continued to rise in countries such as the US throughout the 1990s. But they have dropped a lot since 2005, alongside a rise in GDP."
6. "There are two key reasons why emissions have fallen in these countries. First, some countries have managed to decouple energy use and economic growth. ... But the second is the most important: countries are replacing fossil fuels with low-carbon energy."
7. "It would be wrong to assume that this reduction in emissions in rich countries was only achieved by offshoring production overseas ... consumption-based emissions - which adjust for emissions from goods that are imported or exported - have also fallen. Some emissions have been exported overseas, but this is not the only driver of this decline."
8. "These countries show that economic growth is not incompatible with reducing emissions."
9. "A key question is whether we can decarbonize fast enough, and across more countries."

The numbers the article gives. The prose states no quantity: no percentage, no tonnes, no dollars. Its only numerals are dates and "the last 30 years". Every number a reader can take away is on a chart: the 60 printed percentages of the arrow grid (A.4), and whatever is read off the line charts (A.2). The article never states how large the "exported" emissions in claim 7 are; that quantity, consumption minus production, is what this project plots.

### A.8 Design facts for a critique, each checkable against A.2 to A.6

1. All three figures show change, never level: percent change since a base year (line charts) or between two years (grid). No figure shows tonnes per person or dollars per person.
2. Production-based and consumption-based CO2 appear together only in the line chart; the grid shows consumption-based only.
3. The difference between the two, the net trade balance, is not plotted in any of the article's three figures, and indexing both series to 0% in 1990 removes it from view. (The explorer linked in paragraph 8 can show it, as a share, if the reader goes looking; A.5.)
4. GDP, a monetary quantity, and CO2, a physical one, share one percent axis; the comparison is of percent changes only.
5. One country per panel. Countries are compared by looking from panel to panel: six panels by default, 30 in the grid. No figure in the article places countries in one coordinate system; the two views that do (a scatterplot and a world map of consumption-based emissions) are text links (A.5).
6. The six-panel view shares one y scale, so adding a fast-growing country flattens the rest.
7. The three lines end in different years (2025, 2024, 2023).
8. Two of the three line colours are blues (GDP navy, territorial CO2 slate blue); consumption-based CO2 is orange-red.
9. The grid encodes each value as the height of an arrow head against an undrawn scale, with the number printed beside it; it shows two end points, not a path, and its end year is 2020.
10. The grid shows only countries that passed a success filter (each change above 5%); the lead example is not in it.
11. The line chart's GDP series is the World Bank's (constant 2021 international-$), not the Maddison series in the CO2 dataset; for the United Kingdom, 1990 to 2022, the two rise 61.0% and 46.1%.
12. What the configuration confirms a reader can change is the countries and the time window within one chart, with no control for leaving relative mode (A.6; not tried in a browser, so do not write "limited to" as if the list were complete). There is no brushing or linking between views.
13. The text gives no numbers and cites no literature outside Our World in Data: it has no footnotes or reference list, and its six text links go to four OWID charts or explorers and two OWID articles (A.5).


## 6. Appendix B: findings recorded from the cited literature, with page numbers

### B.1 Haroz, Kosara, and Franconeri (2016), connected scatterplot

Pages are those of the authors' PDF (11 pages), not the journal's, which was not seen; cite by section number. CS is the connected scatterplot, DALC the dual-axis line chart.

- Time is not on an axis. Section 2.1, p. 2: "Since time is not directly represented in the plot, the points are an important indicator of time steps, as their spacing indicates the rate of change." Section 2.1, p. 2: "Without an indication of the direction of time, a connected scatterplot can be drastically misinterpreted".
- Reading direction, expectation. Section 5, p. 7: the journalists interviewed "generally agreed that the sequence in connected scatterplots should progress from left to right".
- Reading direction, evidence (Study 2; 35 Mechanical Turk participants, 8 excluded; redrawing five-point series from one format in the other). Section 5.2, p. 8: when copying a CS to a CS, "participants reversed the temporal ordering of the points on 5% of trials"; when translating between formats "time was again reversed, but even more frequently (13% in each case)"; and in CS to DALC "participants flipped the horizontal axis 1.6% of the time". Section 5.3, p. 8: "Performance on this difficult translation task was high overall (92%)".
- Understanding (Study 1; 14 undergraduates). Section 3, p. 6: "both DALC and CS formats allowed high performance on objective measures of understanding"; participants "found loops and possible right-to-left ordering to be a surprising and salient feature in the CS format".
- Engagement (Study 3; 25 university students choosing among six thumbnails for five minutes). Section 6.2, p. 8: "In the first half of the experiment, subjects spent more time viewing CSs (57.4%, 95% CI [49.3%, 65.6%])"; "We did not find a viewing bias in the second half of the experiment (49.2%, 95% CI [40.6%, 57.7%])"; "We did not find a reliable difference in total viewing time between the two techniques (CS: 148s, 95% CI [132, 163]; DALC: 130s, 95% CI [114, 146])".
- Guidelines. Section 7, p. 9: "Give salient cues for the flow of time. Viewers occasionally made mistakes in understanding the direction of the flow of time indicated by the connecting lines, even in simple copying tasks. Using a left-to-right global flow of time should minimize this error [29, 20], along with explicit annotation of temporal direction. Although we have primarily seen arrows used to annotate temporal direction, this approach does not appear to be sufficient, as time reversals were the dominant error made by readers." Also "Give explicit reminders of two oriented axes" and "Use for engagement and communication".
- A limit. Section 7, p. 9: "A caveat on correlation. If a major purpose of a graph is to leave the viewer with an understanding of negative or positive correlation in a dataset, a more traditional DALC may make this conclusion far more salient. Our college student participants rarely used correlational language to describe patterns of data in the CS".
- Summary. Section 8, p. 10: participants "are generally able understand this unusual chart, with the notable exception of occasionally mirrored direction", and "chose to look at it first more often than at standard line charts".

### B.2 Cleveland and McGill (1984), elementary perceptual tasks

Pages are the printed journal pages.

- p. 531, abstract: the theory identifies "a set of elementary perceptual tasks that are carried out when people extract quantitative information from graphs" and orders them "on the basis of how accurately people perform them"; "Graphs should employ elementary tasks as high in the ordering as possible."
- p. 532: ten tasks are illustrated (Figure 1). Colour hue and texture are left out "because they do not have an unambiguous single method of ordering from small to large and thus might be regarded as better for encoding categories rather than real variables".
- p. 534: the pattern in a scatterplot is read through direction: "The elementary task that enables us to do this is perception of direction."
- p. 535: the ordering is a hypothesis about accuracy, not a claim that graphs exist to convey decimals: "We are not saying that the primary purpose of a graph is to convey numbers with as many decimal places as possible."
- p. 536, the ranking: "The following are the 10 elementary tasks in Figure 1, ordered from most to least accurate: 1. Position along a common scale 2. Positions along nonaligned scales 3. Length, direction, angle 4. Area 5. Volume, curvature 6. Shading, color saturation".
- p. 541, experiments: "the average errors for length judgments are 40%-250% larger than those for position judgments"; for angle against position the difference is "a factor of ... 1.96, and is statistically significant". Caution on the first figure: the two sentences before it give the underlying factors as 1.4 and 2.5 (a difference of .51 and of 1.32 on the log base 2 scale), and a factor of 2.5 is 150% larger, not 250%. The quotation is exact, but "by a factor of 1.4 to 2.5" is the safer way to report it.
- p. 552: "The outcomes of the two experiments reported here were correctly predicted by the theory; position judgments were more accurate than length judgments and angle judgments."

### B.3 Becker and Cleveland (1987), brushing

Pages are the printed journal pages, read in the scan held by Carnegie Mellon University's Technometrics archive.

- p. 127, abstract: "A dynamic graphical method is one in which a data analyst interacts in real time with a data display on a computer graphics terminal."
- p. 127, abstract, the definition: "Brushing is a collection of dynamic methods for viewing multidimensional data. It is very effective when used on a scatterplot matrix, a rectangular array of all pairwise scatterplots of the variables. Four brushing operations - highlight, shadow highlight, delete, and label - are carried out by moving a mouse-controlled rectangle, called the brush, over one of the scatterplots. The effect of an operation appears simultaneously on all scatterplots."
- p. 128, section 1.3: "The central object in brushing is the brush, a rectangle that is superimposed on the screen".
- p. 129: "There are four basic brushing operations - highlight, shadow highlight, delete, and label. Each operation is carried out in one of three paint modes - transient, lasting, and undo."
- p. 130, section 2.1, what highlighting does across views: "One panel of the scatterplot matrix is selected as the current panel. All points that are both inside the brush and inside the current panel are highlighted, as are the points on other panels that correspond to these points." The same page says the operation "allows us to solve the linking problem".
- p. 131, section 2.2, the transient mode: "As the brush is moved, the new points that come inside the brush are highlighted, but points no longer inside the brush are no longer highlighted."
- p. 131, a brush over a range of one variable: "Conditioning on a single variable is a brush technique that provides a simple, direct way to fix the values of one variable to a certain range and see the behavior of the other variables. This technique is achieved by selecting the highlight operation and the transient paint mode and by making the brush long and narrow."

### B.4 Heer and Shneiderman (2012), interaction taxonomy

Pages are the printed journal pages.

- p. 46: "The taxonomy consists of 12 task types grouped into three high-level categories": data and view specification (visualize, filter, sort, derive); view manipulation (select, navigate, coordinate, organize); process and provenance (record, annotate, share, guide).
- p. 50, coordinate: "Many analysis problems require coordinated multiple views that enable analysts to see their data from different perspectives."
- p. 50, brushing and linking: "Brushing and linking is the process of selecting (brushing) items in one display to highlight (or hide) corresponding data in the other views." The sentence cites Becker and Cleveland (1987).
- p. 50, small multiples: "Edward Tufte advocates the use of small multiples: a collection of visualizations placed in spatial proximity and typically using the same measures and scales. Small multiples enable rapid comparison of different data dimensions or time slices." In the article "Tufte" carries reference number 20, which is The Visual Display of Quantitative Information (1983), not Envisioning Information; so this sentence cannot be cited as Tufte (1990) at second hand.

### B.5 Roberts (2007), coordinated and multiple views

Located by section; the repository copy that was read has no page numbers.

- Section 1, the premise: "users understand their data better if they interact with the presented information and view it through different representations".
- Section 3.2, small multiples: "small-multiples [72] are a matrix of small visualizations that are laid side-by-side".
- Section 4.1, brushing as the link between views: "The technique of brushing is the principle approach, where elements are selected (and highlighted) in one display, concurrently the same information in any other linked display is also highlighted. Much of the original work was done on scatter plot matrices (Carr et al. [15] and Becker and Cleveland [8]). All modern CMV systems provide some brushing capability."
- Section 7, the eight principles of Baldonado et al. as Roberts lists them: diversity, complementarity, decomposition ("partition complex visualizations into smaller manageable views"), parsimony ("use multiple views sparingly"), space/time resource optimization, self evidence ("use perceptual cues to make the relationships more evident"), consistency ("keep the interfaces consistent across views") and attention management. Baldonado et al. was not opened.

### B.6 Tufte (1990), small multiples

First taken from the Wikipedia article "Small multiple", which cites Envisioning Information, p. 67; at the re-check the wording was confirmed in the Internet Archive's searchable text of three scans of the book (see the entry in section 4): "At the heart of quantitative reasoning is a single question: Compared to what? Small multiple designs, multivariate and data bountiful, answer directly by visually enforcing comparisons of changes, of the differences among objects, of the scope of alternatives. For a wide range of problems in data presentation, small multiples are the best design solution." It is the opening paragraph of the chapter "Small Multiples", which the contents page puts at p. 67. The page image was not seen, so a reader with the book should still glance at p. 67 before the quotation goes to print.

### B.7 Peters, Minx, Weber, and Edenhofer (2011), emission transfers

- p. 8903, abstract, size of net transfers: "The net emission transfers via international trade from developing to developed countries increased from 0.4 Gt CO2 in 1990 to 1.6 Gt CO2 in 2008, which exceeds the Kyoto Protocol emission reductions."
- p. 8903, abstract, traded emissions: "the emissions from the production of traded goods and services have increased from 4.3 Gt CO2 in 1990 (20% of global emissions) to 7.8 Gt CO2 in 2008 (26%)".
- p. 8903, abstract: "Most developed countries have increased their consumption-based emissions faster than their territorial emissions".
- Results section: "The net emission transfers from non-Annex B to Annex B has grown from 0.4 Gt CO2 in 1990 to 1.6 Gt CO2 in 2008 (17% per year average growth)". Caution: Table 1 prints this rate as 16.9 %/y. It is not a compound rate: a fourfold rise in 18 years is about 8% a year compounded, while 1.2 Gt over 18 years on a base of 0.4 Gt is 16.7% of the 1990 level a year. That is re-check arithmetic; the main text does not say how the rates were computed. Quote the two levels, or keep the paper's word "average".
- Table 1 (Gt CO2, 1990 and 2008): Annex B production 14.2 and 13.9; Annex B consumption 14.5 and 15.5; non-Annex B production 7.7 and 16.4; non-Annex B consumption 7.4 and 14.8; traded emissions 4.3 and 7.8; trade balance -0.4 and -1.6; global emissions 21.9 and 30.3.
- Results section: "Cumulatively, we find that international trade has relocated 16 Gt CO2 from Annex B to non-Annex B countries from 1990 to 2008."
- Scope and method: "a trade-linked global database for CO2 emissions covering 113 countries and 57 economic sectors from 1990 to 2008" (abstract); the body is more exact: "disaggregated into 113 regions (including 95 individual countries), each with 57 economic sectors". Detailed models for 1997, 2001 and 2004 and an annual series built around them.
- Sign convention, opposite to this project's: "net exporters are positive (surplus) and net imports are negative (deficit)".

### B.8 Does decoupling survive consumption-based accounting?

Le Quere et al. (2019). Passages from the authors' accepted manuscript. The published abstract states the main result (fossil fuels displaced by renewable energy, and lower energy use) but not the selection rule or the trade finding.

- Selection: "We isolate a 'peak-and-decline' group of 18 countries where emissions have significantly decreased over the period 2005-2015 considering both territorial and consumption emissions". The group "represents 28% of global emissions".
- Size: emissions in the group "decreased by -2.4% [-2.9% to -1.4%] per year on average during 2005-2015".
- Drivers: the largest contribution was "from decreases in the fossil share of final energy, accounting for a median of 47% [36 to 73%] of the decrease in emissions", then "decreases in energy use, accounting for 36% [18% to 56%]".
- Trade: "Outsourcing of emissions through trade was small relative to these four physical drivers and does not account for their substantial contribution to CO2 reductions". Earlier: "Since the early 1990s, transfers of emissions through international trade have also contributed to emission reductions in some countries, although this effect stabilized around 2005 in most developed economies."
- A caution, from the published abstract: "the decrease in energy use can be explained at least in part by a lower growth in gross domestic product".

Hubacek, Chen, Feng, Wiedmann, and Shan (2021). Version of record; 116 countries, 1990 to 2018, Global Carbon Budget 2020 data. PBE is production-based and CBE consumption-based emissions.

- p. 1, abstract: "32 out of 116 countries (mainly developed ones) achieved absolute decoupling between GDP and production-based emissions in recent years (2015-2018), and 23 countries achieved absolute decoupling between GDP and consumption-based emissions. 14 countries have decoupled GDP growth from both production- and consumption-based emissions."
- p. 1, abstract: "Even countries that have achieved absolute decoupling are still adding emissions to the atmosphere"; "decoupling can be temporary, and decoupled countries may switch back to increasing emissions".
- p. 5: "Another 67 countries (or 58%) have relatively decoupled, and 19 (or 16%) coupled economic growth with CBE."
- p. 5, persistence: "32 countries achieved absolute decoupling from 2010 to 2015, and only 10 of them remained decoupled over the next three years."

Haberl et al. (2020). From the abstract; a review of 835 peer-reviewed articles.

- "Examples of absolute long-term decoupling are rare, but recently some industrialized countries have decoupled GDP from both production- and, weaklier, consumption-based CO2 emissions."
- "We conclude that large rapid absolute reductions of resource use and GHG emissions cannot be achieved through observed decoupling rates, hence decoupling needs to be complemented by sufficiency-oriented strategies and strict enforcement of absolute reduction targets."


## 7. Appendix C: what could not be verified

1. Tufte (1990): the book was not opened. The wording of the small-multiples passage is now confirmed in the Internet Archive's searchable text of the scanned book, and the chapter it opens begins on p. 67 by the book's contents page; the page image itself was not seen (section 4, B.6).
2. Munzner (2014): the book was not opened. Any page number attached to a concept from it must be checked against the book.
3. Haroz, Kosara, and Franconeri (2016): read in the authors' 11-page PDF. Journal page numbers within 2174-2186 were not mapped; cite findings by section.
4. Peters, Minx, Weber, and Edenhofer (2011): the full text was read as a web page, so only the abstract is tied to a page (p. 8903).
5. Le Quere et al. (2019): the passages on country selection, drivers and trade are from the accepted manuscript, not the published article. The manuscript is titled "Drivers of declining CO2 emissions in industrial countries" and says "18 industrial countries" where the published abstract says "18 developed economies", so wording did change in production; quote the published abstract where it suffices.
6. Haberl et al. (2020): abstract only. Roberts (2007): read in a repository copy without page numbers, version not stated; cite by section.
7. Davis and Caldeira (2010); Hunter (2007); Peters, Andrew, and Lennox (2011); Peters, Davis, and Andrew (2012); Andrew and Peters (2013): bibliographic details verified, articles not read. They are cited here only for what the Global Carbon Budget says it took from them, or as the standard reference for a tool. The same holds for the tool and method papers whose bibliographic details alone were checked: Bostock et al. (2011), Machado et al. (2009), Satyanarayan et al. (2017), Segel and Heer (2010), VanderPlas et al. (2018) and Waskom (2021).
8. United Nations (2024): resolved at the re-check. Citation and licence were read in the content file of the UN's own download page (section 4); the data files themselves were not opened.
9. Sources named inside other sources and not opened: Erb and Marland (2025) and UNFCCC (2022), the Global Carbon Budget's references for national territorial emissions; Andres et al. (1994), the source of the 477 Mt estimate for the Kuwaiti oil fires; The Conference Board Total Economy Database and Wu (2014), the Maddison Project's sources for recent GDP. They are not in section 4.
10. Global Carbon Project (2025): largely resolved at the re-check. The national workbook OWID ingested is now identified by md5 (National_Fossil_Carbon_Emissions_2025_v0.3.xlsx from globalcarbonbudget.org) and its Consumption Emissions sheet reproduces OWID's consumption_co2 (section 1.1), so the consumption-based series no longer rests on OWID's documentation alone. Still open: the copies held by the ICOS Carbon Portal under the DOI (v0.1 of 13 November 2025, replaced by v1.0 on 17 May 2026) were not opened, so whether their national values equal those of the v0.3 file is not known. The link between the OWID file and the Global Carbon Project's fossil CO2 file was checked before (same md5; Kuwait arithmetic in section 3).
11. The Grapher chart was not operated in a browser. What a reader can change (A.6) is inferred from the chart's published configuration, the schema defaults and the article's text.
12. The static grid's data vintage is unknown. The explanation in A.4 of why the United Kingdom is absent uses today's data.
13. Assignment brief: its title for the article could not be matched to any version of the page (A.1).

Changes made by the independent re-check (4 October 2026)

All 34 entries of section 4 were compared again with the registry record of their DOI or with the page or document itself; 32 stood as written. What changed:

1. Bolt and van Zanden: year 2024 corrected to 2025, the year of volume 39 (entry in section 4; in-text mentions in 1.1 and in the notes at the head of section 4). Any text that still cites "Bolt and van Zanden (2024)" must be brought into line with its reference list.
2. Global Carbon Project data supplement: "Version 1.1" corrected to "Version 1.0", the label the DOI's landing page gave the release OWID ingested (entry in section 4, with the history of the record).
3. United Nations (2024): moved from unverified to verified; citation and licence read at the UN source (entry in section 4; population in 1.1; item 8 above).
4. Tufte (1990): the quoted passage and its place at the head of the chapter that begins on p. 67 confirmed in the searchable text of the scanned book (entry in section 4; B.6; item 1 above).
5. consumption_co2: the workbook OWID ingested identified by md5 and its values compared with the OWID file (1.1; section 3; item 10 above).
6. trade_co2: the statement that the Global Carbon Project does not supply this quantity was wrong. Its workbook has an Emissions Transfers sheet with the opposite sign; OWID recomputes its own (1.1).
7. The article, A.5 and A.8: the scatterplot is not the only cross-country view of levels the article links to. Paragraph 8 links to a world map of consumption-based emissions, and the prose has six links in all; A.8 items 3, 5, 12 and 13 were reworded to match. A.1: the first of OWID's archived copies differs from the live page in its title's typography and in site boilerplate, not in the ten paragraphs.
8. Appendix B: the reference markers dropped from one Haroz quotation restored; cautions added on Cleveland and McGill's "40%-250%", on the growth rate in Peters, Minx, et al., and on which Tufte book Heer and Shneiderman cite.
9. Section 2: column count of decoupling_summary.csv updated.

Checked again and found correct, among others: every quotation in Appendix B against the paper or scan named there (Haroz, Cleveland and McGill, Becker and Cleveland, Heer and Shneiderman, Roberts, Hubacek, the Le Quere manuscript and published abstract, Peters, Minx, et al., Haberl's abstract, the Global Carbon Budget paper and supplement, Andrew and Peters section 5.1); the seven SHA-256 values; the Kuwait arithmetic; the Maddison comparison figures in 1.1, recomputed from mpd2023_web.xlsx; the World Bank histories and the count of 39 changed groups, recomputed from the historical workbook; the 30 pairs of the arrow grid; and the chart configuration, data and Internet Archive capture behind Appendix A.
