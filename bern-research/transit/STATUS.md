# transit/ status

Updated 2026-11-21 02:10 Europe/Zurich. Owner thread: Bern Transit GTFS and DiDok Data.

## Ready to commit

Everything below is stable, rebuilt from the downloads by `python scripts/run_all.py`, and passes
`scripts/validate.py --online --node` (75 checks: 71 pass, 4 warnings, 0 failed) and the join section of
`bern-research/lead/validate/validate.py`. No file is above 25 MB (largest 19.4 MB).

| Path | Content | Records | Bytes |
|---|---|---|---|
| `SOURCES.json` | Input manifest: url, publisher, licence, retrieved, bytes, sha256, used_for | 16 sources | |
| `data/MANIFEST.json` | Output manifest: bytes, sha256, records, script, inputs | 24 outputs | |
| `data/stations.geojson` | Stations with atlas `sloid` and `number`, `tier`, WGS84 + LV95, height | 1,123 (208 bern, 386 ring, 529 connected) | 1.1 MB |
| `data/edges.geojson` | Boarding edges and areas: `sloid`, `designation`, `designation_operational`, `station_sloid`, WGS84 + LV95, `height_m`, `type`, `compass_direction_deg`, `coord_rounded` | 3,483 (bern: 598 edges + 21 areas) | 3.0 MB |
| `data/edge_lookup.json` | `number -> designation -> [edge sloid]` | 1,117 stations | 0.3 MB |
| `data/gtfs_stop_map_fp2026.json`, `data/gtfs_stop_map_fp2027.json` | GTFS `stop_id -> edge_sloid / station_sloid`, `kind`, `stop_times_rows`, shares | 3,415 / 3,084 | 1.5 / 1.4 MB |
| `data/coverage_stops.json` | Coverage logic, counts, `known_gaps` | | |
| `data/accessibility_edges.json` | atlas platform-v2 + BfR wheelchair class per edge SLOID | 2,902 edges (bern 575) | 2.1 MB |
| `data/accessibility_stations.json` | atlas stop-point-v2, reference points, toilets, parking, contact points, relations per station SLOID | 1,112 stations | 1.2 MB |
| `data/sectors.geojson` | Platform sectors with atlas coordinates, `edge_sloid` | 1,803 (bern 117 on 20 edges) | 1.3 MB |
| `data/coverage_accessibility.json` | Counts for the three files above | | |
| `data/fp2026/gtfs_bern_fp2026.zip` | Lossless GTFS subset, source rows verbatim | 140,500 trips, 2,066,447 stop_times | 17.8 MB |
| `data/fp2026/timetable.json` | Compact timetable; decodes to exactly the subset | 166 routes, 11,941 patterns, 8,839 services | 19.4 MB |
| `data/fp2026/edge_directions.json` | Derived: lines and next stops per edge (bern + ring) | 1,294 stops | 1.1 MB |
| `data/fp2026/segments.geojson` | Derived: every stop-to-stop hop, lines, trip-days, run time | 5,961 | 5.0 MB |
| `data/fp2026/lines.geojson` | Derived: representative stop sequence per line and direction | 266 | 0.4 MB |
| `data/fp2026/transfers.json` | Minimum transfer times and in-seat transfers | 48,383 | 7.2 MB |
| `data/fp2027/*` | The same six files for the 2027 timetable | 32,473 trips, 444,996 stop_times | 13.4 MB total |
| `validation/report.md`, `report.json` | Validation run | 75 checks | |
| `validation/sample_departures.md`, `.json` | Bern, Bern Bahnhof, Zytglogge, Wankdorf on five date/time cases | 25 boards | |
| `web/bern-transit.js` | Thin reader for `timetable.json` (departures, vehicles); same results as `scripts/timetable.py` | | 7 KB |
| `scripts/*.py` | Pipeline, standard library only | 11 files | |

## Feeds and service days

| Feed | Source file | Valid (service days covered) | Use it for |
|---|---|---|---|
| fp2026 | `gtfs_fp2026_20261118.zip` | 2025-12-14 to 2026-12-12, all 364 days | any date up to and including Saturday 2026-12-12 |
| fp2027 | `gtfs_fp2027_20261118.zip` | 2026-12-13 to 2027-12-11, all 364 days | any date from Sunday 2026-12-13 |

Both compact timetables carry every service day of their feed as an explicit bitmask per service (no weekday
shortcuts). Today, 2026-11-21, is in fp2026. A trip that starts on 2026-12-12 and runs past midnight belongs to
fp2026 (times above 24:00:00). Atlas files are the state of 2026-11-20 (published daily).

## Shares (lead join test)

Share of stop_times that reference an edge SLOID, trips serving Bern:

| | fp2026 all stops | fp2026 at bern stops | fp2027 all stops | fp2027 at bern stops |
|---|---|---|---|---|
| edge SLOID | 95.95 % | 97.87 % | 94.29 % | 95.41 % |
| station SLOID only | 4.02 % | 2.13 % | 5.69 % | 4.59 % |
| no Swiss SLOID (foreign) | 0.03 % | 0 % | 0.02 % | 0 % |

## Known gaps (also machine readable in `data/coverage_stops.json` under `known_gaps`)

- 2 tier-bern stations have no boarding edge in atlas: Bern Matte and Bern Münsterplattform (the two ends of the Matte lift).
- 34 tier-bern edges or areas have no coordinates in atlas (19 boarding platforms, 15 boarding areas); `geometry` is null.
- 141 of 598 tier-bern edges have coordinates rounded to whole metres (`coord_rounded`).
- 170 tier-bern edges have no compass direction, 375 no public designation (kerbs without a letter).
- 4 foreign stations have no Swiss SLOID (Berlin Ostbahnhof, Freiburg (Breisgau) Hbf, Domodossola, Pontarlier).
- fp2027 has no trips at Bern, Kunstmuseum and Bern, Waisenhausplatz (and at the two temporary stops of March 2026).

## Blocked

- GTFS-RT: needs a personal opentransportdata.swiss API key. None is configured here, so it was not fetched.
  `scripts/gtfs_rt.py` documents the plug-in point and has never been run against the live endpoint.

## In progress

- `README.md`, `docs/SCHEMA.md`, `HANDOFF.md` (schemas, coverage, how to load). No data changes planned.

## Rebuild

```
python scripts/run_all.py              # downloads about 560 MB into .cache/, then builds and validates (about 5 min)
python scripts/run_all.py --skip-fetch # reuse .cache/
```

Python 3.11, standard library only. `node` is optional (one cross-check of the JS reader).
