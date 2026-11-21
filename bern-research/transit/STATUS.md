# transit/ status

Updated 2026-11-21 01:50 Europe/Zurich. Owner thread: Bern Transit GTFS and DiDok Data.

## Ready to read (ids are final, other folders can join on them now)

| Path | Content | Records |
|---|---|---|
| `data/stations.geojson` | Stations (atlas service points) with `sloid`, `number`, `tier`, WGS84 + LV95, height | 1,116 (202 bern, 382 ring, 532 connected) |
| `data/edges.geojson` | Boarding edges and boarding areas: edge `sloid`, `designation`, `designation_operational`, `station_sloid`, `station_number`, WGS84 + LV95, `height_m`, `type`, `compass_direction_deg`, `coord_rounded` | 3,411 (bern: 585 edges + 21 areas) |
| `data/edge_lookup.json` | `number -> designation -> [edge sloid]`, plus `by_designation_operational` and `by_gtfs_platform_code` | stations with at least one edge |
| `data/gtfs_stop_map_fp2026.json` | GTFS `stop_id -> edge_sloid / station_sloid`, `kind`, `stop_times_rows`, shares | 3,378 stop ids |
| `data/gtfs_stop_map_fp2027.json` | same for the 2027 feed | 3,049 stop ids |
| `data/coverage_stops.json` | Coverage logic and counts, machine readable | |

Schemas may still gain properties; none will be renamed or removed.

Tiers: `bern` = atlas `fsoNumber` 351 and `stopPoint=true`; `ring` = atlas stop point at most 5 km outside the
municipal boundary; `connected` = any other station on a trip that serves a `bern` stop.

Share of stop_times that reference an edge SLOID (fp2026, trips serving Bern): 95.9 % overall, 97.9 % at `bern`
stops. The rest reference the station SLOID (4.1 %) or a foreign station without SLOID (0.03 %).

## In progress

- Timetable: lossless GTFS subset per feed and a compact pattern-encoded JSON (routes, trips, service days, times above 24:00).
- Validation report, sample departures (Bern Bahnhof, Zytglogge, Wankdorf), provenance manifest.

## Feeds

| Feed | File | Valid | Trips serving Bern | stop_times |
|---|---|---|---|---|
| fp2026 | `gtfs_fp2026_20261118.zip` | 2025-12-14 to 2026-12-12 | 139,485 | 2,040,458 |
| fp2027 | `gtfs_fp2027_20261118.zip` | 2026-12-13 to 2027-12-11 | 32,126 | 436,092 |

## Blocked

- GTFS-RT: needs an opentransportdata.swiss API key. None is configured on this machine, so it is skipped; the plug-in point will be documented.

## Rebuild

```
python scripts/fetch_sources.py
python scripts/extract_gtfs.py --feed fp2026
python scripts/extract_gtfs.py --feed fp2027
python scripts/build_stops.py
```

Python 3.11, standard library only. Raw downloads and intermediates live in `.cache/` (git-ignored).
