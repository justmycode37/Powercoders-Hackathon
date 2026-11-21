# Bern data sources (lead check)

Checked by the lead on **2026-11-21** unless a row says otherwise. "Live" means the URL was fetched and answered;
"scout" means a research agent reported it on 2026-11-20/21 and the lead has not re-fetched it. Nobody has read the
licence texts in full yet: each folder confirms the licence of what it actually uses and records it in its own
manifest. This file is a starting list, not the provenance record.

## Stops, boarding edges, timetable

| Source | Publisher | URL | Format | Key | Licence (as stated) | Status |
|---|---|---|---|---|---|---|
| Traffic point elements (Haltekanten) | SBB / SKI, atlas | https://data.opentransportdata.swiss/dataset/traffic-point-v2/permalink | CSV, `;`, 34 columns, 62,403 rows, LV95 + WGS84 | none | opentransportdata.swiss terms of use, attribution | Live. 22,986,127 bytes, sha256 `47fd152d…2dd297b`. Zytglogge edge `ch:1:sloid:7110:0:17` = designation `K`. |
| Service points (stations) | SBB / SKI, atlas | https://data.opentransportdata.swiss/dataset/service-point-v2/permalink | CSV, `;`, 56 columns, 60,579 rows | none | same | Live. 26,697,417 bytes, sha256 `fa23a23d…65ac7932`. `number` 8507110 = Bern, Zytglogge. |
| Timetable 2026 (GTFS) | SKI | https://data.opentransportdata.swiss/dataset/timetable-2026-gtfs2020/permalink | GTFS zip, about 292 MB | none | same | Live redirect to `gtfs_fp2026_20261118.zip`. Scout: edge-level stops with `platform_code`, referenced by `stop_times`. |
| Stops of public transport | BAV | https://data.geo.admin.ch/api/stac/v0.9/collections/ch.bav.haltestellen-oev | CSV / GPKG / GDB / XTF, LV95 | none | federal open data, attribution | Live. Item dated 2026-11-08. Scout: includes `Haltekante.csv`. |
| Stops with lines per kerb | Geoinformation Stadt Bern | https://map.bern.ch/arcgis/rest/services/Geoportal/Haltestellen/MapServer/0 | ArcGIS REST / WFS, LV95 | none | open (opendata.swiss `terms_open`) | Live (200). Scout: 1,061 kerbs incl. agglomeration, with letter and line/direction text. |
| Stop accessibility (BehiG) | öV-Info | https://data.oev-info.ch/explore/dataset/haltestellen_tagesdaten | REST JSON / CSV | none | open data | Live (200). Scout: 587 Bern rows with kerb height, tactile and wheelchair flags. |
| Journey API (prototype only) | Opendata.ch community | https://transport.opendata.ch/v1/ | JSON | none | fair use | Used by the team app at the repo root. Station-level coordinates; platform letters present. |
| Realtime: GTFS-RT, OJP 2.0, SIRI-SX | SKI | https://data.opentransportdata.swiss/dataset/gtfsrt | Protobuf / XML | **yes** | terms of use | Not used. Needs a personal API key. |
| CKAN metadata API | SKI | https://data.opentransportdata.swiss/api/3/action/package_show | JSON | ? | | Returned 403 to scripted requests. Use the `/permalink` URLs. |

## 3D terrain and buildings

| Source | Publisher | URL | Format | Key | Licence (as stated) | Status |
|---|---|---|---|---|---|---|
| Terrain, hosted | swisstopo | https://3d.geo.admin.ch/ch.swisstopo.terrain.3d/v1/layer.json | quantized mesh | none | swisstopo open data, attribution | Live, 200, CORS `*`. |
| Buildings, hosted | swisstopo | https://3d.geo.admin.ch/ch.swisstopo.swissbuildings3d.3d/v1/tileset.json | 3D Tiles | none | same | Live, 200, CORS `*`. The older `vectortiles.geo.admin.ch/3d-tiles/...` path returns 403. |
| swissALTI3D | swisstopo | https://data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.swissalti3d | COG GeoTIFF 0.5 m and 2 m, LV95 / LN02 | none | same | Live. 50 one-km tiles over lon 7.42-7.47, lat 46.94-46.97; first item dated 2019. |
| swissBUILDINGS3D 3.0 | swisstopo | https://data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.swissbuildings3d_3_0 | FileGDB, DWG | none | same | Live. 8 tiles over the same box; first item dated 2018. |
| swissBUILDINGS3D 2.0 | swisstopo | https://data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.swissbuildings3d_2 | DXF | none | same | Live. 12 tiles. Fallback if FileGDB cannot be read. |
| swissTLM3D | swisstopo | https://data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.swisstlm3d | GDB / SHP | none | same | Live. Country-wide file; roads, paths and bridges with heights. |
| Height service | swisstopo | https://api3.geo.admin.ch/rest/services/height | JSON, LV95 | none | fair use | Scout: live, returns terrain height per point. Fine for a few hundred points. |
| Base map style | swisstopo | https://vectortiles.geo.admin.ch/styles/ch.swisstopo.lightbasemap.vt/style.json | MapLibre style, vector tiles to z14 | none | same | Live. Used by the team app. |
| Address search | swisstopo | https://api3.geo.admin.ch/rest/services/api/SearchServer | JSON | none | fair use | Live. Used by the team app. |

## Station detail

| Source | Publisher | URL | Format | Key | Licence (as stated) | Status |
|---|---|---|---|---|---|---|
| Sector boards | SBB | https://data.sbb.ch/api/explore/v2.1/catalog/datasets/sektortafel | REST JSON / CSV | none | SBB open data terms | Live (200). Scout: 143 boards for Bern (`BN`). |
| Kerb segments and points (BehiG) | SBB | https://data.sbb.ch/api/explore/v2.1/catalog/datasets/21197_behig-haltekantesegment and `21196_behig-haltekantepunkt` | REST JSON / CSV | none | same | Scout: 91 segments and 5,043 points for Bern; rail only. |
| Platforms | SBB | https://data.sbb.ch/api/explore/v2.1/catalog/datasets/perron and `perronoberflache` | REST JSON / CSV | none | same | Scout: 7 platforms for Bern; centroids, no polygons. |
| OpenStreetMap | OSM contributors | Overpass, e.g. https://overpass.kumi.systems/api/interpreter or https://overpass.osm.ch/api/interpreter | JSON | none | ODbL: attribution, share-alike for derived databases | Live. Platforms, entrances, stairs, lifts, indoor levels. `overpass-api.de` was too slow on 2026-11-21; the kumi mirror answered in 7 s but its data was dated 2026-07-28. |
| Cadastral survey, simplified (MOPUBE) | Canton Bern, AGI | https://geofiles.be.ch/geoportal/pub/stac/de/MOPUBE/collection.json | GPKG / GeoParquet | none | open, attribution | Scout: live. Pavement, island and stair polygons. |
| Kerb plans (Kantenpläne) | BERNMOBIL | https://www.bernmobil.ch/de/fahrplan-netz/kantenplaene | PDF | none | not open data | Reference only, to check letters. Link, do not copy into the repo. |

## Attribution lines to carry into anything that shows this data

- © swisstopo (base map, terrain, buildings, address search)
- Source: opentransportdata.swiss, Systemaufgaben Kundeninformation SKI (stops, edges, timetable)
- © OpenStreetMap contributors (ODbL) for anything taken from OSM
- Geoinformation Stadt Bern; SBB open data; öV-Info, where those layers are used
