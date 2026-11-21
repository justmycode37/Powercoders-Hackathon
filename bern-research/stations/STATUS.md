# stations/ STATUS

Updated: 2026-11-21 02:25 Europe/Zurich. Owner thread: Bern Station Geometry and 3D Models.

## Ready to validate and commit

Everything below is stable in format. Later runs may add stations or attributes, not rename things.

```
bern-research/stations/.gitignore
bern-research/stations/STATUS.md
bern-research/stations/SOURCES.json
bern-research/stations/tools/            (7 Python files, standard library only)
bern-research/stations/data/boarding_edges.geojson
bern-research/stations/data/boarding_edges_not_in_transit.geojson
bern-research/stations/data/station_features.geojson
bern-research/stations/data/stations.geojson
bern-research/stations/data/edge_placements.json
bern-research/stations/data/build-report.json
bern-research/stations/data/focus/        (3 x .geojson, 3 x .walk_graph.json, index.json)
bern-research/stations/models/            (3 x .glb + .model.json, archetypes/ 4 x .glb + .model.json)
bern-research/stations/validation/report.md
bern-research/stations/validation/report.json
```

Largest file: `data/boarding_edges.geojson` 2.1 MB. Nothing above 25 MB. `.cache/` (about 120 MB) is git-ignored.

Own checks: `python tools/validate.py` -> 0 FAIL, 10 WARN, 72 OK (`validation/report.md`).
Lead checks (`python -I ../lead/validate/validate.py`, 02:20): no FAIL in "stations" or "joins".

## Done

| Path | What | Count |
|---|---|---|
| `data/boarding_edges.geojson` | one feature per atlas boarding edge, id = edge SLOID, best line geometry + provenance | 1,090: 60 surveyed (SBB kerb points), 555 OSM platform, 443 constructed (approximate), 9 point only, 23 without atlas coordinates (geometry null) |
| `data/boarding_edges_not_in_transit.geojson` | same schema, edges in my atlas download that `transit/data/edges.geojson` does not list | 1 (`ch:1:sloid:7081:0:640619`, Bern Fischermaetteli) |
| `data/station_features.geojson` | platform surfaces, shelters, atlas sector markers, SBB sector boards; all carry station SLOID + number and edge SLOID | 181 + 237 + 126 + 152 |
| `data/stations.geojson` | one point per atlas stop (plus operating points that own edges), edge counts, best geometry tier, bbox | 440 |
| `data/focus/bern-bahnhof.geojson` | level-aware geometry: edges, platforms, passages, stairs, escalators, lifts, entrances, access points, surveyed underground outlines, buildings, roofs | 1,188 features, levels -2..5 |
| `data/focus/zytglogge.geojson` | same | 346 features, level 0 |
| `data/focus/wankdorf.geojson` | same | 238 features, levels -1..1 |
| `data/focus/<slug>.walk_graph.json` | pedestrian graph with levels (OSM, ODbL) | 1,224 / 271 / 233 nodes |
| `data/focus/index.json` | stations, level table with elevation and quality, counts per focus | 3 |
| `models/<slug>.glb` + `.model.json` | lightweight 3D, 1.3 MB / 37 kB / 252 kB; sidecar states frame, origin, per-feature index ranges, approximations | 3 |
| `models/archetypes/*.glb` | generic stop pieces for the fallback (CC0) | 4 |
| `data/edge_placements.json` | position, rotation and scale to place an archetype on every edge that has a line | 1,058 |

Rebuild from nothing:
`python tools/fetch_sources.py && python tools/build_geometry.py && python tools/build_focus.py && python tools/build_models.py && python tools/validate.py`

## Lead notes of 02:05, handled

- `ch:1:sloid:7081:0:640619`: kept, but moved to `data/boarding_edges_not_in_transit.geojson` and flagged
  (`in_transit_edges: false`, `atlas_record_origin`). It is in the atlas "actual date" file I downloaded at 01:41
  (validFrom 2026-03-27). Its station `ch:1:sloid:7081` stays in `stations.geojson` (your WARN).
- The eight tier-bern edges: `build_geometry.py` now reads `../transit/data/edges.geojson` read-only when it exists and
  adds every tier-bern BOARDING_PLATFORM my atlas download lacks, flagged `atlas_record_origin` and
  `atlas_valid_today`. Six get a fallback line or point (`inferred: true`); the two Gewerbeschule edges have no atlas
  coordinates, so `geometry: null`. Bern Europaplatz Sued (operating point, not a stop point) is now included natively.
- `SOURCES.json` is at the folder root: 34 inputs with url, publisher, licence, retrieved, bytes, sha256, used_for.

## In progress

- `README.md` (schemas) and `HANDOFF.md` (by 06:15).
- Check of named passages and entrances against the SBB and BERNMOBIL plans (links only) -> `references.json`.
- More stations at focus level of detail (rail stations and tram/bus hubs).

## Findings for the other threads

- atlas coordinates of 4 edges sit on the neighbouring track: Bern Wankdorf designations 2, 3 and 7
  (`ch:1:sloid:16161:1:1`, `:1:2`, `:3:5`) and Bern `ch:1:sloid:7000:6:32`. SBB kerb points, SBB sector boards and OSM
  agree with each other. My geometry follows the track number; the features carry `atlas_position_conflict`, offsets
  7.9 to 14.4 m. This is why the stated tolerance is 15 m; without these four the largest surveyed offset is 3.9 m.
- atlas heights of the PostAuto deck edges at Bern Bahnhof (OSM level 2) equal the track level (540.0 m). Rejected for
  the level table; level 2 elevation is nominal and labelled approximate.
- SBB kerb points lie on the platform edge, not the track axis: median 0.17 m to OSM platform outlines (539 samples).

## Blocked

- Nothing.
