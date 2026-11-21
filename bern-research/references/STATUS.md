# references/ STATUS (Bern Station Reference Collection)

Updated 02:10 Europe/Zurich, 2026-11-21.

## Done
- `data/stations.json`: 359 atlas stop points (202 in the City of Bern, plus Ittigen, Ostermundigen, Muri and Köniz) with `number`, `sloid` and coordinates (`tools/01_stations.py`).
- `data/panoramax_items.json`: 233 georeferenced street-level photos (CC BY-SA 4.0) with GPS position, compass azimuth, field of view and capture time, keyed to stations (`tools/03_harvest_panoramax.py`).
- `data/operator_links.json`: 46 operator plans, standards, planning PDFs, datasets and imagery services. All 46 URLs checked live; sbb.ch answers only browser user agents, which is noted per link. They are links only and nothing proprietary is copied (`tools/04_operator_links.py`).
- `orthophoto/`: 16 swisstopo SWISSIMAGE crops of the hubs (0.1 to 0.2 m/px, LV95), each with a `.jgw` world file and a `.json` sidecar, about 14 MB (`tools/05_orthophotos.py`).
- `assets/`: 10 original parametric glTF assets (bench, ticket machine, recycling station, info stele, generic clock, sector sign, departure display, shelter, tram island, Baldachin approximation). Each sidecar gives evidence, units, axes and origin, and sets `approximate: true` (`tools/07_assets.py`).

## In progress
- Wikimedia Commons harvest (seed categories plus GeoData geosearch around rail and tram stops). It is slowed by API rate limits (HTTP 429).
- Then `tools/06_select_download.py` (licence filter, scoring, download of about 125 Commons and 22 Panoramax images), `tools/08_build_manifest.py` and `tools/09_validate.py`.

## Blocked
- Mapillary: the API needs a token (contract rule 9), so it is recorded as a link only.
- KartaView: the API did not answer, so it is recorded as a link only.

## Ready for the lead to commit (provisional, final list in HANDOFF.md)
- `references/.gitignore`, `tools/`, `data/stations.json`, `data/panoramax_items.json`, `data/operator_links.json`, `data/orthophotos.json`, `orthophoto/`, `assets/`, `data/assets.json`
