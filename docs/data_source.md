# Data source

We checked the sources on 2026-10-27 with `council-harvester check` and by hand with curl.

## Dresden (works)

- System: https://oparl.dresden.de/system
- Made by SOMACOS ("Sitzungsmanagementsystem Session"), vendor tag `oparl=v1.5.4`
- OParl version 1.1
- License: Datenlizenz Deutschland Zero 2.0 (`dl-de/zero-2-0`), so the data is free to use
- There is one body called `Instance 0001`. The name does not say Dresden, so we take the
  city name from our config file.
- Paper list: https://oparl.dresden.de/bodies/0001/papers
- 10 papers per page by default. `limit=100` works too.
- The pages have no `totalPages`, only a `links.next` link. So we just follow `next`.
- If you ask for a page after the last one you get http 404.
- `modified_since` works, we use it for incremental runs.
- The links in the answers start with `http://`. The server sends you to `https://` (301),
  requests follows that by itself.
- Papers have no `web` link. There are two kinds of paper ids and each kind has its own
  web page. The number is the last part of the paper id:
  - `.../papers/vo/<number>` (Vorlagen): `https://ratsinfo.dresden.de/vo0050.asp?__kvonr=<number>`
  - `.../papers/ag/<number>` (proposals and questions of the district councils):
    `https://ratsinfo.dresden.de/ag0050.asp?__kagnr=<number>`

  We checked this by hand for papers of both kinds (the reference number is on the page).
- Papers have no `location`. The location list only has empty addresses without geojson.
  So right now we can not make points for dresden papers (see the mapping doc).
- It is slow. A page with 100 papers takes about 30 seconds.

## Leipzig (does not work right now)

- System: https://ratsinformation.leipzig.de/allris_leipzig_public/oparl/system
- This is ALLRIS (made by CC e-gov), not Somacos.
- The server answers http 500 with the text "Oparl-Modul ist deaktiviert"
  (the oparl module is turned off).
- So leipzig has `enabled = false` in the config.
- What we do instead: the tests use OParl fixture files in the same format, so the code
  is ready when the city turns the module back on.
- Other options (not done):
  1. ask the city to turn on oparl again, this is the best one
  2. read the ALLRIS html pages. this is a different pattern, it breaks easy and we would
     have to check the terms of use first

## What we saw in the real Dresden data

First we read the newest 6000 papers (dates 2022-07-25 to 2026-10-22) to tune the keywords.
Then we did a real run with all papers changed since 2024 (5213 papers, see `samples/`).

- every paper had a `date`, none had a `web` link or a `location`
- deleted papers do show up (as `"deleted": true` with no title)
- the real run found 12 papers:
  - 10 `semiconductor_dc_park`: the TSMC / ESMC settlement, trucks to the ESMC building site,
    what TSMC means for flats in Pieschen, the "Halbleiterstandort" cooperation and a tram
    line for Silicon Saxony
  - 2 `mega_substation`: two new 110-kV power lines that SachsenEnergie plans through Rähnitz.
    the Klotzsche district council (same district as the TSMC / ESMC site) wants other routes
- 3 of the 12 are false positives: the city's own IT data center ("Rechenzentrum")
- 61 papers were small grants for clubs ("Kleinprojektförderung") and got skipped
- the word "Umspannwerk" is not in a single title. Big substations are mostly planned by the
  grid companies and approved by the state, so council papers are a weak source for them.
  Better sources would be the state approvals (Landesdirektion Sachsen) and the grid plans
  of the network operators.
- the newest 6000 papers only had `vo` ids, the `ag` ids only showed up in the real run.
  thats why we check the links on real data and not just on the first pages.

## Other places in Saxony

- The OParl endpoint list (https://github.com/OParl/resources/blob/master/endpoints.yml)
  only has Dresden and Leipzig for Saxony.
- A new source is just a new `[[sources]]` block in `config/harvester.toml`, no code change.
