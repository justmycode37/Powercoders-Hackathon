# stations/ STATUS

Updated: 2026-11-21 03:08 Europe/Zurich. Owner thread: Bern Station Geometry and 3D Models.

## Ready to validate and commit

Formats are stable. Later runs may add attributes or stations, not rename things.

```
bern-research/stations/.gitignore
bern-research/stations/README.md             formats and schemas
bern-research/stations/STATUS.md
bern-research/stations/HANDOFF.md            coverage, limits, findings, rebuild, load
bern-research/stations/SOURCES.json          90 inputs: url, publisher, licence, retrieved, bytes, sha256, used_for
bern-research/stations/references.json       operator plans (links only) and what was read off them
bern-research/stations/tools/                10 Python files, standard library only
bern-research/stations/data/boarding_edges.geojson
bern-research/stations/data/station_features.geojson
bern-research/stations/data/stations.geojson
bern-research/stations/data/accessibility.json
bern-research/stations/data/edge_placements.json
bern-research/stations/data/build-report.json
bern-research/stations/data/focus/           59 x .geojson, 59 x .walk_graph.json, index.json
bern-research/stations/models/               59 x .glb + .model.json
bern-research/stations/models/archetypes/    4 x .glb + .model.json
bern-research/stations/validation/report.md
bern-research/stations/validation/report.json
```

Sizes: `data/` 4.7 MB, `data/focus/` 11.9 MB, `models/` 3.2 MB, everything else under 0.6 MB. Largest file
`data/boarding_edges.geojson` 2.4 MB. `.cache/` (about 160 MB) is git-ignored.

Checks at 03:08:
- `python tools/validate.py`: 0 FAIL, 49 WARN, 767 OK (`validation/report.md`). 41 of the WARN are "stairs without a
  level tag in OSM" at single focus stations.
- `python -I ../lead/validate/validate.py`: 0 FAIL. One WARN is mine and intended, see "Wankdorf" below.

## Counts

| Path | What | Count |
|---|---|---|
| `data/boarding_edges.geojson` | one feature per atlas boarding edge, id = edge SLOID | 1,105: 63 surveyed (SBB kerb points), 3 surveyed (cadastral platform outline), 511 OSM platform, 496 constructed (approximate), 9 point only, 23 without atlas coordinates (geometry null). By transit tier: 598 bern, 507 ring (all ring edges inside my box) |
| `data/station_features.geojson` | linked to station SLOID + number and edge SLOID | 1,238: 219 platform surfaces, 240 shelters (140 surveyed footprints), 126 atlas sector markers, 152 SBB sector boards, 103 derived sector spans, 398 surveyed kerb candidates |
| `data/stations.geojson` | atlas stops plus operating points that own edges | 446 |
| `data/accessibility.json` | atlas register: named access points and step-free access per platform | 31 stations, 35 access points, 193 relations |
| `data/focus/*.geojson` | level-aware station geometry | 59 stations, 4,830 features: 450 passages, 246 stairs, 33 escalators, 77 lifts, 23 entrances, 492 access points, 99 surveyed underground outlines, 478 edges, ... |
| `data/focus/*.walk_graph.json` | pedestrian graph with levels, footways plus streets (OSM, ODbL) | 11,520 nodes, 13,971 edges; largest component holds 99 % / 100 % / 96 % of nodes at the three priority stations |
| `models/*.glb` | focus station models | 59, 2.7 MB, 124,164 triangles (Bern Bahnhof 0.9 MB) |
| `data/edge_placements.json` | archetype placement per edge with a line | 1,073 |

Focus stations: 3 priority (Bern Bahnhof with levels -2..5, Zytglogge, Wankdorf) and 56 picked by rule (28 further
rail stations, 28 tram/bus stops with at least 4 lettered kerbs). The list with reasons is in `data/focus/index.json`.

## Lead notes of 02:05, handled

- `ch:1:sloid:7081:0:640619` (Bern Fischermaetteli): the transit file now lists it, so it is in
  `boarding_edges.geojson`. If transit ever lacks an edge of mine, `build_geometry.py` moves it to
  `data/boarding_edges_not_in_transit.geojson` by itself (the file does not exist at the moment).
- Missing tier-bern edges: `build_geometry.py` reads `../transit/data/edges.geojson` read-only when it exists and
  adds every tier-bern edge, and every tier-ring edge inside my box, that my atlas download lacks (20 edges; flagged
  `atlas_record_origin`, `atlas_valid_today`). Bern Europaplatz Sued now has surveyed SBB lines; edges without atlas
  coordinates have `geometry: null`.
- `SOURCES.json` is at the folder root.

## Findings for the other threads

- **Wankdorf, atlas coordinates on the wrong track.** Five rail edges have an atlas coordinate that lies on a
  different track than their track number: Bern Wankdorf 2, 3, 5, 7 (`ch:1:sloid:16161:1:1`, `:1:2`, `:2:3`, `:3:5`) and
  Bern `ch:1:sloid:7000:6:32`. SBB kerb points, SBB sector boards, OSM and atlas's own platform grouping (tracks 5 and 6
  share "Perron 2") agree with each other. My geometry follows the track number and the features carry
  `atlas_position_conflict`. Offsets: 7.9, 10.0, 85.5, 14.4 and 10.1 m. Track 5 at Wankdorf is the one edge beyond
  15 m in the lead check: the atlas coordinate is on the 2/3 island, track 5 is on the 5/6 island.
  Stated tolerance: every edge geometry is within 15 m of its atlas point unless it carries `atlas_position_conflict`.
- atlas heights of the PostAuto deck edges at Bern Bahnhof (OSM level 2) equal the track level (540.0 m). Rejected for
  the level table. Levels 1 and 2 at Bern Bahnhof now take measured heights from the city3d folder's swissTLM3D
  paths (547.8 m and 549.1 m; read-only use of `../city3d/data/network/tlm_paths_3d.geojson`); three underpass
  levels at Worblaufen, Guemligen and Koeniz likewise. 47 of 114 station levels remain nominal.
- SBB kerb points lie on the platform edge, not the track axis: median 0.17 m to OSM platform outlines.
- OSM platform lines in the city agree with the cadastral pavement boundaries: mean offset 0.58 m in the median for
  283 edges.
- Own review at 02:45 changed the matching (data changed, formats did not): tram and bus edges no longer take a
  nearby railway platform (this had hit 'X, Bahnhof' bus stops and the PostAuto kerbs X and Y), a platform line
  contested by two different edges goes to the nearer one (28 claims resolved), and the platform side follows the
  atlas direction of travel. Result: 511 OSM-based and 496 constructed edges (before: 551 and 456).
- BERNMOBIL kerb plans (read from the public PDFs, not copied): all 9 Zytglogge letters, 16 of 17 Bern Bahnhof
  letters (K2 is not on the 2026 plan) and A-F at Wankdorf Bahnhof / Nord (G is not on the 2025 plan) are confirmed.
  The SBB station plans could not be fetched by script (HTTP 403), so named SBB passages are not plan-checked.

## Lead request of 03:05 (Stadt Bern kerb layer as second position source): done

Code `tools/city_kerbs.py`; full lists in `data/build-report.json` under `city_kerb_check`; written up in
`HANDOFF.md` ("Stadt Bern kerb points ..."); checked in `validation/report.md`.

| Question | Result |
|---|---|
| Edges without atlas coordinates filled from a city kerb | **0 of 23.** The city layer has letters on 58 of 873 kerbs and no numbers. 20 of the 23 edges are at stops whose city kerbs are unlabelled, 3 (Bern Bahnhof op. 66 and 80, Thunplatz op. 12) are unlettered edges at lettered stops. All 23 keep `geometry: null` and carry `no_geometry_reason`. One (`ch:1:sloid:82210:0:618032`, Untermattweg) carries a `city_kerb_candidate` property found by elimination, not used as geometry |
| City kerb letters added | **0.** Only 7 located edges without an atlas letter are at stops with city letters; the nearest lettered city kerb is 25 to 141 m away (limit 6 m). `designation` untouched |
| atlas point to city kerb point, 60 pairs matched by station and letter | median 10.2 m, p75 16.5, p90 20.7, p95 23.3, max 34.3 m; 8 within 5 m, 30 within 10 m, 54 within 20 m |
| same, 602 pairs matched by position | median 7.1 m, p75 11.3, p90 16.4, p95 21.5, max 42.2 m |
| City kerb point to my edge line | median 1.2 m, p90 4.4 m (letter pairs): the city points lie on the edge lines |
| Stops where atlas and the city disagree on which letter is where | **none.** Naming only: Bern Bahnhof atlas `K1` = city `K`. Letters only in atlas: Bahnhof K2, N, Q, Z; Zytglogge K; Hauptbahnhof R, W, X, Y; Hirschengraben N; Wankdorf Bahnhof B; Wankdorf Bahnhof Nord G |

Worst ten letter pairs (atlas to city kerb point): Viktoriaplatz B 34.3 m, Bahnhof E 25.6, Buempliz Unterfuehrung D
23.3, Bahnhof E 23.2, Bahnhof C 21.7, Bahnhof G 20.7, Hirschengraben C 19.4, Bahnhof B 19.2, Buempliz Unterfuehrung
B 18.8, Zytglogge F 18.2. In all but two the city point is within 1.3 m of my edge line, so these are offsets along
the kerb, not wrong kerbs. Table with edge SLOIDs in `HANDOFF.md`.

Correction that came out of this: `lines_at_kerb` had been taken from the city kerb nearest to the atlas point,
which picked the kerb across the street for 18 edges. It now uses the position pairing (662 edges, before 470).
No new sources, no model or viewer work.

## Lead note of 02:55, handled

- `ch:1:sloid:16161:2:3` (Bern Wankdorf track 5, 85.5 m from its atlas point) is the track-number rule, not a
  regression. Before 02:22 the edge had wrongly taken the kerb of track 3, because that is where the atlas
  coordinate lies. The feature now says so in `inferred_how` ("linked ... by equal track number within the same
  station, NOT by proximity: the atlas coordinate lies 85.5 m away, on SBB track 3"), carries
  `atlas_position_conflict` and `dist_atlas_to_geometry_m: 85.55`, and is listed with the other four conflicts in
  `data/build-report.json` (`atlas_position_conflicts`), in `validation/report.md` and in `HANDOFF.md`.

## In progress

- Nothing required. Optional extras only; STATUS and HANDOFF are refreshed after any change.

## Blocked

- Nothing.
