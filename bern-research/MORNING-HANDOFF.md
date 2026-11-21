# Bern research: morning handoff

**Status: final.** Written 2026-11-21 05:00 Europe/Zurich by the lead, at ktr0a's request to finalise early. The
independent reviews planned for 05:00 and 06:40 had not run when this was written; a read-only checkpoint at 03:00
did. All four worker threads are idle and nothing is uncommitted.

- Checkout: `C:\Users\apfel\Documents\Coding\Powercoders-Hackathon`
- Branch: `bern-transit-3d`, **local only**, from `origin/main` @ `a4cc40f`. Nothing pushed, no PR, no upstream set.
- Every commit has author and committer `ktr0a <107317602+ktr0a@users.noreply.github.com>` (checked with `gh`), with
  no co-author or tool attribution.
- The team files at the repo root and the earlier demo in `C:\Users\apfel\Documents\Coding\Hackathon\rightside` are
  untouched. Everything new is under `bern-research/`.
- The deliverable is data: sourced, keyed by stable ids, validated. The HTML pages are thin sample loaders.

## Start here

| Folder | What it holds | Read first |
|---|---|---|
| `transit/` | Stations, boarding edges, timetables for two feeds, accessibility, sectors | `transit/HANDOFF.md` |
| `stations/` | Kerb and track lines per edge, station features, by-level detail and walk graphs, glTF models | `stations/HANDOFF.md` |
| `city3d/` | Terrain tiles, buildings with heights, roof models, roads, paths, rail and bridges in 3D | `city3d/HANDOFF.md` |
| `references/` | Licensed photos, orthophoto crops, operator plan links, furniture assets | `references/HANDOFF.md`, `references/ATTRIBUTION.md` |
| `lead/` | Contract, source list, validation, sample loader | `lead/CONTRACT.md` |

Ids that join everything: atlas station `sloid` and `number` (the number is the station id used by
`transport.opendata.ch`), and the atlas edge `sloid` with its `designation` (public letter or track).

## Coverage

**Stops and boarding edges** (atlas service-point-v2 and traffic-point-v2, retrieved 2026-11-21)
- 1,123 stations: 208 in Bern municipality (`tier: bern`), 386 within 5 km of the boundary (`ring`), 529 further
  out on trips that serve Bern (`connected`).
- 3,483 boarding edges and areas. In Bern municipality: 598 boarding edges and 21 boarding areas, 585 of them with
  coordinates.
- Lookup `station number -> designation -> edge SLOID` for 1,117 stations (`transit/data/edge_lookup.json`).
- GTFS stop ids resolve to an edge SLOID for 95.9 % of stop_times on trips serving Bern (97.9 % at Bern stops); the
  rest reference the station.

**Timetable** (Swiss GTFS, feed version 2026-11-18)
- `fp2026`, valid 2025-12-14 to 2026-12-12: 140,500 trips, 2,066,447 stop_times, 166 routes, 19 agencies,
  8,839 services with calendar exceptions expanded, times up to 29:45:00.
- `fp2027`, valid from 2026-12-13: 32,473 trips, 444,996 stop_times, 123 routes.
- Per feed: lossless GTFS subset (zip), compact timetable, per-edge lines and directions, stop-to-stop segments,
  lines, transfers. A slice for 2026-11-21 to 2026-12-12 is included for quick loading.
- Timezone Europe/Zurich. Scheduled times only.

**Accessibility and sectors** (atlas PRM data): 575 Bern edges with accessibility records; 1,803 platform sectors
(117 in Bern, on 20 edges).

**Station geometry**
- 1,105 boarding-edge features for 446 stations in the study area. Geometry class: 66 surveyed (SBB kerb survey
  points and cadastral platform outlines), 511 from OSM platforms, 496 constructed from the atlas point and bearing,
  9 point only, 23 without geometry.
- By-level detail (passages, stairs, lifts, entrances, sector boards and spans, platform surfaces) and a walk graph
  for 59 areas: Bern Bahnhof (1,328 features), Zytglogge (352), Wankdorf (268), every rail station in the study
  area and the larger tram and bus stops. One lightweight glTF model per area plus 4 generic archetypes.

**3D** (box LV95 E 2589000-2606000, N 1194000-1205000, contains all of Bern municipality)
- Terrain-RGB tiles from swissALTI3D, 2 m, with 0.5 m in the centre: 725 tiles.
- 46,946 building footprints with EGID and LN02 heights (swissBUILDINGS3D 3.0, 2021 edition); LOD2 roofs for 2,933
  central buildings.
- swissTLM3D roads, paths, stairs, rail and 632 bridge segments in 3D; OSM footways, steps and crossings.

**References**: 2,450 records. 172 are stored in the repo with author, licence, source URL and checksum (144 image
files, 16 orthophoto crops, 12 original parametric assets); the rest are links, including 233 street-level photos
and 46 operator plans and datasets.

## What is approximate, inferred or missing

- **No realtime.** GTFS-RT, OJP and SIRI need a personal opentransportdata.swiss API key (free, by registration).
  None is configured on this machine. `transit/scripts/gtfs_rt.py` marks the plug-in point and has never run
  against the live service.
- **34 Bern edges and areas have no coordinates in atlas**, and 2 Bern stations (Bern Matte, Bern Münsterplattform)
  have no boarding edge. They are listed under `known_gaps` in `transit/data/coverage_stops.json`, not filled in.
  The Stadt Bern kerb layer could not fill them: it has letters on only 58 of 873 kerbs and no operational numbers.
- **147 Bern edge coordinates are rounded at the source** (flag `coord_rounded`), and 375 Bern edges have no public
  letter or track, only an operational number.
- **Atlas edge points are not kerb-exact along the kerb.** Against the Stadt Bern kerb layer (60 edges matched by
  stop and letter) the atlas point is a median 10.2 m from the city's kerb point (90 % within 20.7 m, maximum
  34.3 m). The offsets run along the kerb: the city points lie a median 1.2 m from the drawn edge lines. Atlas and
  the city never disagree on which letter is on which side.
- **Kerb lines are mostly not surveyed.** 496 are constructed from a point and a bearing with a default length
  (`geometry_quality: approximate`) and 511 come from OSM (`community`). Only 66 are surveyed.
- **Four rail edges disagree with their track number:** the atlas point for Bern track 12 and Wankdorf tracks 2, 3
  and 7 sits on the neighbouring track. The geometry follows the track number, which puts one Wankdorf edge
  (`ch:1:sloid:16161:2:3`) 85 m from its atlas point. See `stations/data/build-report.json`.
- **Station interiors come from OSM.** Many stairs and lifts carry no level tag there. Nothing inside any station
  has been checked on site.
- **Heights:** atlas edge heights agree with the terrain within 1 m for 92.2 % of 1,112 edges. The outliers are
  mostly underground or elevated platforms; the list is in `city3d/data/validation/edge_terrain_heights.json`.
- **Bridge decks** in `city3d/data/network/bridges_deck_approx.geojson` are inferred polygons for display.
- **Buildings missing** in a strip of about 380 m at the far west of the box (mostly forest near Riedbach).
- **Terrain and buildings are older than the station rebuild** (buildings 2021 edition).
- **References:** station links and feature tags on photos are inferred from Commons categories, distance or
  keywords. Items found only by keyword search were removed from the stored subset after a false match, and 162
  linked records are flagged `relevance_unverified`. Nobody has looked at every stored photo. Mapillary needs a
  token and KartaView did not answer, so both are links only.
- **Licences were taken from the dataset pages.** Nobody read the full licence texts.

## Validation

| Check | Result (04:55) | How to run |
|---|---|---|
| Lead validator: sizes, parsing, coordinate order and extent, id format, flags, manifests, credential patterns, and cross-folder joins | 0 FAIL, 19 WARN, 104 OK | `python -I bern-research/lead/validate/validate.py` -> `lead/validate/REPORT.md` |
| Timetable against the live Swiss journey API (`transport.opendata.ch` station boards) for Zytglogge, Bern Bahnhof, Bern, Bern Wankdorf and Wankdorf Bahnhof | 605 of 607 departures found at the same minute and line, on Mon 2026-11-23 08:00, Sun 2026-11-22 23:30 (past midnight) and Mon 2026-12-14 17:30 (2027 feed). Platform or kerb equal in all 592 cases where both sides give one. The 2 misses are long-distance trains the API lists by train number. | `node bern-research/lead/validate/crosscheck_stationboard.js 2026-11-23 08:00` |
| Sample loaders in headless Chrome | 10 of 10 pass | `node bern-research/lead/validate/smoke_sample.js` -> `lead/validate/smoke/` |
| Transit worker checks (incl. timetable decode against the GTFS subset) | 75 checks, 0 failed | `python bern-research/transit/scripts/validate.py` |
| Stations worker checks | 0 FAIL | `python bern-research/stations/tools/validate.py` |

Join results: no edge without a parent station; no lookup or stop-map entry pointing at a missing edge; every
station-geometry edge is known to transit; all five focus stations have edges with coordinates; every tier-bern
boarding platform has a feature in the stations folder. In the smoke test, 400 of 400 departures at Zytglogge on
Monday 2026-11-23 from 08:00 resolve to a boarding edge with coordinates.

The 19 warnings are known and explained above or expected: stations on through trips outside Switzerland and
outside the Bern box, four foreign stations without SLOID, the two Bern stations without an edge, the Wankdorf
track conflict, a render-only building copy without per-feature flags, two output manifests that are not input
manifests, and one reference station that transit does not list.

Two errors were caught before they were committed: a photo of a memorial plaque in Germany linked to Bern station by
a keyword match, and a "lines at this kerb" attribute that had picked the kerb across the street for 18 edges.

## How to run the samples

```
cd C:\Users\apfel\Documents\Coding\Powercoders-Hackathon\bern-research
python -m http.server 8140 --bind 127.0.0.1
```
- `http://127.0.0.1:8140/lead/sample/` : boarding edges, kerb lines and station detail on the swisstopo map; click
  an edge for its record and scheduled departures.
- `http://127.0.0.1:8140/city3d/index.html` : terrain, buildings, bridges and edges in 3D.
- `http://127.0.0.1:8140/references/browse.html` : the reference collection by station.

All need internet for the swisstopo base map and the map library. Screenshots of the first two are in
`lead/validate/smoke/`.

## How to rebuild

Each folder rebuilds from the official downloads with its own scripts (Python 3.11; transit and stations use the
standard library only). Raw downloads go to a git-ignored `.cache/` in each folder.
- transit: `python scripts/run_all.py` (inputs in `transit/SOURCES.json`, outputs in `transit/data/MANIFEST.json`)
- stations: `python tools/fetch_sources.py`, then the build scripts in the order given in `stations/HANDOFF.md`
- city3d: tools and order in `city3d/HANDOFF.md` (inputs in `city3d/SOURCES.json`, 217 entries)
- references: `tools/01_…` to `10_…` in order

## Fit with the other branches (read through git on 2026-11-21 04:50, not run)

Two candidates exist as a basis. Both already place each departure on its boarding edge from the same atlas
register, for all of Switzerland, so the station and edge points here duplicate what they have and should not
replace it.

| | `origin/main` @ `c94f756` | `origin/nikitas-implementation` @ `48937e8` (Kante) |
|---|---|---|
| What it is | One static page plus `platforms.js` built by `tools/build_platforms.py` | Rust routing engine plus a Preact web app; no data in the repo, about 900 MB downloaded on first run |
| Journeys | Live from `transport.opendata.ch` | Own search on the national GTFS |
| Edges | Atlas points with bearing and OSM floor level | Atlas points with sectors, accessibility, side of street and a precision class |
| Walking | Public routing services | Own multi-level graph from OpenStreetMap |
| 3D | None | None |

| Output here | Use with `main` | Use with Kante |
|---|---|---|
| `city3d/` terrain and buildings | Direct: same map library family and base style (`raster-dem`, `fill-extrusion`) | Direct: same base style |
| `stations/` kerb and track lines with quality class | New: it has points only | New: it has a point and a side |
| Coordinate caveats (`coord_rounded`, missing, wrong track) | New: it shows the atlas points as published | Refines its `edge` / `edge-at-station` / `station` precision |
| `transit/data/*/edge_directions.json` | Replaces its "traffic keeps right" guess when the live API names no platform | Already computed by its engine |
| Accessibility and sector positions | New | Already ingested nationally |
| Station levels, entrances, walk graphs | New beyond a floor number | A check on its in-station walks, which its README lists as sometimes wrong |
| Timetable files and the cross-check script | Offline fallback or test fixture | Independent test oracle and realistic mock data |
| `references/` | New | New |

The commits here touch only `bern-research/`, which neither branch has, so a merge onto either should not conflict.
No test merge was done.

## Licences and attribution

- opentransportdata.swiss (SKI): stops, edges, timetable, accessibility. Terms of use of the platform, attribution.
- swisstopo: base map, terrain, buildings, TLM, orthophotos. Free geodata (OGD), attribution "© swisstopo".
- SBB open data, Geoinformation Stadt Bern, canton Bern cadastral survey: station and kerb data, attribution.
- OpenStreetMap contributors: platforms, footways, indoor detail. ODbL; derived files say so per feature.
- Wikimedia Commons photos: CC BY, CC BY-SA and CC0, per file in `references/ATTRIBUTION.md`.
- Panoramax photos: CC BY-SA 4.0, linked, not copied.
Per-input licence, URL, date and checksum are in each folder's `SOURCES.json`.

## Open items for ktr0a

1. **Push or not.** The branch is local. It adds about 165 MB of packed history, mostly `city3d/`. If that is too
   much, `city3d/HANDOFF.md` names the two files to drop first; dropping them needs a history rewrite before the
   first push, not after.
2. **Realtime.** Register for an opentransportdata.swiss API key if delays and platform changes are wanted.
3. **Which branch is the basis.** The table above says what plugs in where; nothing has been integrated.
4. **Site check.** The three focus stations have never been compared with reality on the ground.
5. **The Tailscale address from the earlier demo** (`http://ktr0a-desktop.tail112150.ts.net/`) still forwards to a
   local server that is no longer running. `tailscale serve --http=80 off` removes it.

## Commits on `bern-transit-3d`

| Commit | Content |
|---|---|
| `d9c0739`, `c8fa6cf`, `3cee3f6` | Lead contract, source list, validator, join checks |
| `94ace7d`, `dc2b49e`, `ec017da` | Transit snapshots 1 to 3 |
| `2487027`, `17503fd` | References snapshots 1 and 2 |
| `376e88c` | City 3D snapshot 1 (138 MB of data in 755 files) |
| `acb14c1`, `33752f6`, `e9bf38b`, `3766ba6` | Stations snapshots 1 to 4 |
| `e5d9948`, `42a502f` | Sample loader, smoke test, live-API cross-check |
| `930c519`, `d093b85`, `abf846f`, `aa519e5`, and the final commit that adds this text | Handoff and validation report updates |
