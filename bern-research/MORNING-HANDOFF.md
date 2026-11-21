# Bern research: morning handoff

**Status: in progress, snapshot 2.** Updated 2026-11-21 02:30 Europe/Zurich by the lead. Rewritten at each committed
snapshot; final at 07:00. Numbers are from the committed files at this snapshot and may still grow.

- Checkout: `C:\Users\apfel\Documents\Coding\Powercoders-Hackathon`
- Branch: `bern-transit-3d`, local only, from `origin/main` @ `a4cc40f`. Nothing pushed, no PR.
- The team files at the repo root and the earlier demo in `C:\Users\apfel\Documents\Coding\Hackathon\rightside`
  are untouched. Everything new is under `bern-research/`.
- The deliverable is data: sourced, keyed by stable ids, validated. The two HTML pages are thin sample loaders.

## What is in the tree

| Folder | Content at this snapshot | Detail |
|---|---|---|
| `transit/` | 1,123 stations, 3,483 boarding edges and areas, timetables for two feeds, accessibility, sectors | `transit/STATUS.md`, `transit/validation/report.md` |
| `stations/` | 1,095 boarding-edge geometries, 697 station features, by-level detail and walk graphs for focus stations, glTF models | `stations/STATUS.md`, `stations/validation/report.md` |
| `city3d/` | Terrain tiles, 46,946 buildings with heights, LOD2 roofs for the centre, roads, paths, rail and bridges in 3D | `city3d/HANDOFF.md` |
| `references/` | 359-station list, 233 street-level photo records, 46 operator links, 16 orthophoto crops, 10 furniture assets | `references/STATUS.md` |
| `lead/` | Contract, source list, validation, join checks, smoke test, sample loader | `lead/CONTRACT.md` |

## Coverage

**Stops and boarding edges** (atlas service-point-v2 and traffic-point-v2, retrieved 2026-11-21)
- Stations: 208 in Bern municipality (`tier: bern`), 386 within 5 km of the boundary (`ring`), 529 further out on
  trips that serve Bern (`connected`).
- Bern municipality: 598 boarding edges and 21 boarding areas. 585 have coordinates.
- Lookup `station number -> designation -> edge SLOID` for 1,117 stations (`transit/data/edge_lookup.json`).
- GTFS stop ids map to an edge SLOID for 95.9 % of stop_times on trips serving Bern (97.9 % at Bern stops); the
  rest reference the station.

**Timetable** (Swiss GTFS, feed version 2026-11-18)
- `fp2026`, valid 2025-12-14 to 2026-12-12: 140,500 trips, 2,066,447 stop_times, 166 routes, 19 agencies,
  8,839 services with calendar exceptions expanded, times up to 29:45:00.
- `fp2027`, valid from 2026-12-13: 32,473 trips, 444,996 stop_times, 123 routes.
- Per feed: lossless GTFS subset (zip), compact timetable, per-edge directions, stop-to-stop segments, lines, transfers.
- Timezone Europe/Zurich. No realtime.

**Accessibility and sectors** (atlas PRM data)
- 575 Bern edges with accessibility records; 1,803 platform sectors (117 in Bern, on 20 edges).

**Station geometry**
- Kerb or track line per boarding edge for the study area: 64 from SBB surveyed kerb points, 551 from OSM platforms,
  448 constructed from the atlas point and bearing, 9 point only, 23 without any geometry.
- By-level detail (passages, stairs, lifts, entrances, sector boards, platform surfaces) and walk graphs for
  Bern Bahnhof (1,189 features), Zytglogge (346) and Wankdorf (238), plus further rail stations and larger stops.

**3D** (box LV95 E 2589000-2606000, N 1194000-1205000, contains all of Bern municipality)
- Terrain-RGB tiles from swissALTI3D, 2 m, with 0.5 m in the centre: 725 tiles.
- 46,946 building footprints with EGID and LN02 heights (swissBUILDINGS3D 3.0, 2021 edition); LOD2 roofs for 2,933
  central buildings.
- swissTLM3D roads, paths, stairs, rail and 632 bridge segments in 3D; OSM footways, steps and crossings.

## What is approximate, inferred or missing

- **Timetable is scheduled only.** GTFS-RT, OJP and SIRI need an opentransportdata.swiss API key. None is configured
  on this machine, so no realtime was fetched. `transit/scripts/gtfs_rt.py` marks the plug-in point and has never
  run against the live service.
- **34 Bern edges and areas have no coordinates in atlas**, and 2 Bern stations (Bern Matte, Bern Münsterplattform)
  have no boarding edge. These are listed under `known_gaps` in `transit/data/coverage_stops.json`, not filled in.
- **147 Bern edge coordinates are rounded at the source** (flag `coord_rounded`), and 375 Bern edges have no public
  letter or track, only an operational number.
- **Kerb lines:** 448 are constructed from a point and a bearing with a default length (`geometry_quality:
  approximate`), 551 come from OSM (`community`). Only the 64 SBB lines are surveyed.
- **Four rail edges disagree with their track number:** the atlas point for Bern track 12 and Wankdorf tracks 2, 3
  and 7 sits on the neighbouring track. The geometry follows the track number; see `stations/data/build-report.json`.
- **Station interiors come from OSM.** Many stairs and lifts carry no level tag there. Nothing inside the stations
  has been checked on site.
- **Heights:** atlas edge heights agree with the terrain within 1 m for 92.2 % of 1,112 edges. The outliers are
  mostly underground or elevated platforms (for example the RBS tracks at 517 m under terrain at 540 m); the list is
  in `city3d/data/validation/edge_terrain_heights.json`.
- **Bridge decks** in `city3d/data/network/bridges_deck_approx.geojson` are inferred polygons for display.
- **Buildings missing** in a strip of about 380 m at the far west of the box (mostly forest near Riedbach).
- **Terrain and buildings are older than the station rebuild** (buildings 2021 edition).
- **References:** Mapillary needs a token and KartaView did not answer, so both are links only. The Wikimedia
  Commons subset is still downloading and is not committed yet.

## Validation

| Check | Result at this snapshot | How to run |
|---|---|---|
| Lead validator (sizes, parsing, coordinates, ids, flags, manifests, credentials) and cross-folder joins | 0 FAIL, 17 WARN | `python -I bern-research/lead/validate/validate.py` -> `lead/validate/REPORT.md` |
| Sample loader smoke test in headless Chrome | 10 of 10 pass | `node bern-research/lead/validate/smoke_sample.js` -> `lead/validate/smoke/` |
| Transit worker checks (incl. timetable decode against the GTFS subset) | 75 checks, 0 failed | `python bern-research/transit/scripts/validate.py` |
| Stations worker checks | 0 FAIL, 48 WARN | `python bern-research/stations/tools/validate.py` |

Join results: no edge without a parent station; no lookup or stop-map entry pointing at a missing edge; every
station-geometry edge is known to transit and lies within 15 m of the atlas point; all five focus stations have
edges with coordinates. In the smoke test, 400 of 400 departures at Zytglogge on Monday 2026-11-23 from 08:00
resolve to a boarding edge with coordinates.

Independent data reviews are scheduled for 03:00 and 05:00 and a handoff review for 06:40. Their findings will be
added here.

## How to run the samples

```
cd C:\Users\apfel\Documents\Coding\Powercoders-Hackathon\bern-research
python -m http.server 8140 --bind 127.0.0.1
```
- `http://127.0.0.1:8140/lead/sample/` : boarding edges, kerb lines and station detail on the swisstopo map; click
  an edge for its record and scheduled departures.
- `http://127.0.0.1:8140/city3d/index.html` : terrain, buildings, bridges and edges in 3D.

Both need internet for the swisstopo base map and the map library.

## How to rebuild

Each folder rebuilds from the official downloads with its own scripts (Python 3.11; transit and stations use the
standard library only). Raw downloads go to a git-ignored `.cache/` in each folder.
- transit: `python scripts/run_all.py` (inputs in `transit/SOURCES.json`, outputs in `transit/data/MANIFEST.json`)
- stations: `python tools/fetch_sources.py`, then the build scripts named in `stations/STATUS.md`
- city3d: tools and order in `city3d/HANDOFF.md` (inputs in `city3d/SOURCES.json`, 217 entries)
- references: `tools/01_…` to `09_…` in order

## Licences and attribution

- opentransportdata.swiss (SKI): stops, edges, timetable, accessibility. Terms of use of the platform, attribution.
- swisstopo: base map, terrain, buildings, TLM, orthophotos. Free geodata (OGD), attribution "© swisstopo".
- SBB open data, Geoinformation Stadt Bern, canton Bern cadastral survey: station and kerb data, attribution.
- OpenStreetMap contributors: platforms, footways, indoor detail. ODbL; derived files say so per feature.
- Panoramax photos: CC BY-SA 4.0, linked, not copied.
Per-input licence, URL, date and checksum are in each folder's `SOURCES.json`. Nobody has read the full licence
texts tonight; treat the licence fields as what the publisher states on the dataset page.

## Commits on `bern-transit-3d` (all local, author and committer `ktr0a`)

| Commit | Content |
|---|---|
| `d9c0739`, `c8fa6cf`, `3cee3f6` | Lead contract, source list, validator, join checks |
| `94ace7d`, `dc2b49e` | Transit snapshots 1 and 2 |
| `2487027` | References snapshot 1 |
| `376e88c` | City 3D snapshot 1 (138 MB of data in 755 files) |
| `acb14c1` | Stations snapshot 1 |

The repository is now about 90 MB packed. If that is too large to push, `city3d/HANDOFF.md` names the two files to
drop first.
