# transit/ status

Updated 2026-11-21 02:40 Europe/Zurich. Owner thread: Bern Transit GTFS and DiDok Data.

**Done. Everything in this folder is ready to commit.** `HANDOFF.md` is written. No further data changes are
planned; if one becomes necessary it will be listed here first.

## Ready to commit

Everything below is rebuilt from the downloads by `python scripts/run_all.py` (checked: two consecutive rebuilds
from `.cache/` give 25 byte-identical outputs), passes `scripts/validate.py --online --node` (79 checks: 75 pass, 4 warnings,
0 failed) and has no failure in the join section of `bern-research/lead/validate/validate.py`. No file is above
25 MB (largest 19.4 MB, 81 MB in total).

| Path | Content | Records | Size |
|---|---|---|---|
| `README.md`, `HANDOFF.md`, `docs/SCHEMA.md` | overview, handoff, field-level schemas | | |
| `SOURCES.json` | input manifest: url, publisher, licence, retrieved, bytes, sha256, used_for | 16 sources | |
| `data/MANIFEST.json` | output manifest: bytes, sha256, records, script, inputs | 25 outputs | |
| `data/stations.geojson` | stations with atlas `sloid` and `number`, `tier`, WGS84 + LV95, height | 1,123 (208 bern, 386 ring, 529 connected) | 1.1 MB |
| `data/edges.geojson` | boarding edges and areas: `sloid`, `designation`, `designation_operational`, `station_sloid`, WGS84 + LV95, `height_m`, `type`, `compass_direction_deg`, `coord_rounded` | 3,483 (bern: 598 edges + 21 areas) | 3.0 MB |
| `data/edge_lookup.json` | `number -> designation -> [edge sloid]` | 1,117 stations | 0.3 MB |
| `data/gtfs_stop_map_fp2026.json`, `data/gtfs_stop_map_fp2027.json` | GTFS `stop_id -> edge_sloid / station_sloid`, `kind`, `stop_times_rows`, shares | 3,415 / 3,084 | 1.5 / 1.4 MB |
| `data/coverage_stops.json` | coverage logic, counts, `known_gaps` | | |
| `data/accessibility_edges.json` | atlas platform-v2 + BfR wheelchair class per edge SLOID | 2,902 edges (bern 575) | 2.1 MB |
| `data/accessibility_stations.json` | atlas stop-point-v2, reference points, toilets, parking, contact points, relations per station SLOID | 1,112 stations (bern 205) | 1.2 MB |
| `data/sectors.geojson` | platform sectors with atlas coordinates, `edge_sloid` | 1,803 (bern 117 on 20 edges) | 1.3 MB |
| `data/coverage_accessibility.json` | counts for the three files above | | |
| `data/fp2026/gtfs_bern_fp2026.zip` | lossless GTFS subset, source rows verbatim | 140,500 trips, 2,066,447 stop_times | 17.8 MB |
| `data/fp2026/timetable.json` | compact timetable; decodes to exactly the subset | 166 routes, 11,941 patterns, 8,839 services | 19.4 MB |
| `data/fp2026/timetable_2026-11-21_2026-12-12.json` | the same schema, only trips running on the remaining days of the 2026 timetable year (lighter to load) | 35,443 trips, 501,227 stop_times | 4.8 MB |
| `data/fp2026/edge_directions.json` | derived: lines and next stops per edge (bern + ring) | 1,294 stops | 1.1 MB |
| `data/fp2026/segments.geojson` | derived: every stop-to-stop hop, lines, trip-days, run time | 5,961 | 5.0 MB |
| `data/fp2026/lines.geojson` | derived: representative stop sequence per line and direction | 266 | 0.4 MB |
| `data/fp2026/transfers.json` | minimum transfer times and in-seat transfers | 48,383 | 7.2 MB |
| `data/fp2026/timetable_stats.json`, `data/fp2027/timetable_stats.json` | record counts | | |
| `data/fp2027/*` | the same files for the 2027 timetable | 32,473 trips, 444,996 stop_times, 123 routes | 13.4 MB total |
| `validation/report.md`, `report.json` | validation run | 79 checks | |
| `validation/sample_departures.md`, `.json` | Bern, Bern Bahnhof, Zytglogge, Wankdorf on five date/time cases | 25 boards | |
| `web/bern-transit.js` | thin reader for `timetable.json` (departures, vehicles); same results as `scripts/timetable.py` | | 7 KB |
| `scripts/*.py` | pipeline, standard library only | 12 files | |
| `.gitignore` | ignores `.cache/` and `__pycache__/` | | |

Not yet in lead snapshot 2 (`dc2b49e`), all additive, no existing data file changed:

- new `data/fp2026/timetable_2026-11-21_2026-12-12.json` and `scripts/slice_timetable.py` (built by `run_all.py`);
- `scripts/validate.py` (one more check for that file), `scripts/run_all.py`, `scripts/write_manifest.py`,
  `data/MANIFEST.json` (one more entry), `validation/report.*`;
- `scripts/build_timetable.py`: `timetable_stats.json` lists a fixed set of files, so a rebuild is byte-identical
  whether or not the window file already exists (the committed stats files are unchanged);
- `STATUS.md`, `HANDOFF.md`, `README.md`, `docs/SCHEMA.md` (text).

Late changes that snapshot 2 already contains, no data file affected:

- `scripts/timetable.py`, `web/bern-transit.js`: `departures()` also looks into later service days when the
  window reaches past the end of the day (found by the wider cross-check; quiet stops returned too few rows).
- `scripts/validate.py`: stationboard cross-check widened to 105 boards (40 random Bern stops, both feeds).
- `scripts/fetch_sources.py`: atlas download links change every night; the current link is looked up on the
  dataset page by file name.

Changes between snapshot 1 (`94ace7d`) and snapshot 2: `stations.geojson` went from 1,116 to 1,123 and
`edges.geojson` from 3,411 to 3,483 (stops and edges valid earlier or later in the timetable year, operating
points that own an edge such as Bern Fischermätteli, edges whose parent link atlas had dropped). New properties:
`valid_today`, `stop_point`; `gtfs_stop_map_*` gained `edge_station_sloid`. No property was renamed or removed.

## Feeds and service days

| Feed | Source file | Valid (service days covered) | Use it for |
|---|---|---|---|
| fp2026 | `gtfs_fp2026_20261118.zip` | 2025-12-14 to 2026-12-12, all 364 days | any date up to and including Saturday 2026-12-12 |
| fp2027 | `gtfs_fp2027_20261118.zip` | 2026-12-13 to 2027-12-11, all 364 days | any date from Sunday 2026-12-13 |

Both compact timetables carry every service day of their feed as an explicit bitmask per service (no weekday
shortcuts). Today, 2026-11-21, is in fp2026. A trip that starts on 2026-12-12 and runs past midnight belongs to
fp2026 (times above 24:00:00). Atlas files are the state published on 2026-11-20.

## Shares (lead join test)

Share of stop_times that reference an edge SLOID, trips serving Bern:

| | fp2026 all stops | fp2026 at bern stops | fp2027 all stops | fp2027 at bern stops |
|---|---|---|---|---|
| edge SLOID | 95.95 % | 97.87 % | 94.29 % | 95.41 % |
| station SLOID only | 4.02 % | 2.13 % | 5.69 % | 4.59 % |
| no Swiss SLOID (foreign) | 0.03 % | 0 % | 0.02 % | 0 % |

## Validation in one line each

- Compact timetable decodes to the GTFS subset exactly (2,066,447 and 444,996 stop_times, all columns).
- Service-day bitmasks equal calendar plus exceptions for all 8,839 and 1,858 services.
- 123,886 stop_times at or after 24:00:00 kept (latest 29:45:00).
- Live stationboard cross-check, 105 boards in both feeds: 3,898 of 3,898 departures matched, 1,562 of 1,562
  platform strings equal.
- GTFS and atlas edge coordinates agree to 0.5 m at most.

## Known gaps (machine readable in `data/coverage_stops.json` under `known_gaps`)

- 2 tier-bern stations have no boarding edge in atlas: Bern Matte and Bern Münsterplattform (the Matte lift).
- 34 tier-bern edges or areas have no coordinates in atlas (19 boarding edges, 15 boarding areas); `geometry` is null.
- 141 of 598 tier-bern edges have coordinates rounded to whole metres (`coord_rounded`).
- 170 tier-bern edges have no compass direction, 375 no public designation (kerbs without a letter).
- 47 tier-bern edges are not referenced by either timetable.
- 4 foreign stations have no Swiss SLOID (Berlin Ostbahnhof, Freiburg (Breisgau) Hbf, Domodossola, Pontarlier).
- fp2027 has no trips at Bern, Kunstmuseum and Bern, Waisenhausplatz (and at the two temporary stops of March 2026).
- No line geometry in the source (no `shapes.txt`): segments and lines are straight lines between stops, flagged `inferred`.

## Blocked

- GTFS-RT: needs a personal opentransportdata.swiss API key. None is configured here, so it was not fetched.
  `scripts/gtfs_rt.py` documents the plug-in point and has never been run against the live endpoint.

## In progress

Nothing.

## Rebuild

```
python scripts/run_all.py              # 16 downloads (about 560 MB) into .cache/, then build and validate
python scripts/run_all.py --skip-fetch # reuse .cache/, about 2.5 minutes
```

Python 3.11, standard library only. `node` is optional (one cross-check of the JS reader).
