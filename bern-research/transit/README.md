# Bern transit feeds

Official Swiss public transport data for the municipality of Bern, cut down to files an app can load directly:
every stop, every boarding edge (kerb or platform) with its direction, the full scheduled timetable of every
trip that serves Bern, the calendars behind it, and accessibility attributes. Built on 2026-11-21 from
opentransportdata.swiss (GTFS static and atlas / DiDok master data).

- What is where, with record counts: [STATUS.md](STATUS.md)
- Field-level schemas: [docs/SCHEMA.md](docs/SCHEMA.md)
- Handoff for the lead (coverage, gaps, integration): [HANDOFF.md](HANDOFF.md)
- Inputs with licence and checksums: [SOURCES.json](SOURCES.json); outputs: [data/MANIFEST.json](data/MANIFEST.json)
- Validation: [validation/report.md](validation/report.md), samples: [validation/sample_departures.md](validation/sample_departures.md)

## Layout

```
data/
  stations.geojson            stations (atlas sloid + number), tiers bern / ring / connected
  edges.geojson               boarding edges and areas (edge sloid, designation, direction, height)
  edge_lookup.json            number -> designation -> edge sloid
  gtfs_stop_map_<feed>.json   GTFS stop_id -> edge / station sloid
  accessibility_edges.json    accessibility per edge      accessibility_stations.json  per station
  sectors.geojson             platform sectors
  coverage_stops.json         coverage logic, counts, known gaps
  fp2026/  fp2027/            one folder per timetable year:
    gtfs_bern_<feed>.zip        lossless GTFS subset
    timetable.json              compact timetable
    timetable_<from>_<to>.json  the same for a date window (fp2026: the days left in 2026, 4.8 MB)
    edge_directions.json  segments.geojson  lines.geojson  transfers.json
    inferred_edges.json         inferred edge for stop times that name only the station (separate, with back-test)
scripts/                      pipeline (Python 3.11, standard library only)
web/bern-transit.js           thin reader for timetable.json (browser and node)
validation/                   report and sample departures
.cache/                       raw downloads and intermediates (git-ignored)
```

## Which feed

| Date of travel | Folder |
|---|---|
| up to and including Saturday 2026-12-12 | `data/fp2026/` |
| from Sunday 2026-12-13 (timetable change) | `data/fp2027/` |

## Read it

Python:

```python
import sys; sys.path.insert(0, "bern-research/transit/scripts")
from timetable import Timetable
tt = Timetable.load("fp2026")
for d in tt.departures(8507110, "2026-11-24", "08:00:00", limit=5):      # Bern, Zytglogge
    print(d["time"], d["route"], d["headsign"], d["platform"], d["edge_sloid"])
```

Browser (same conventions as `events.js`: a plain script that sets one global):

```html
<script src="bern-research/transit/web/bern-transit.js"></script>
<script>
  BERN_TRANSIT.load('bern-research/transit/data/fp2026/timetable.json').then((tt) => {
    tt.departures(8507110, '2026-11-24', '08:00:00', 5);   // next departures at a station number
    tt.vehiclesAt('2026-11-24', '08:00:00');               // vehicles under way, on the straight line between stops
  });
</script>
```

`stations.geojson`, `edges.geojson`, `sectors.geojson`, `segments.geojson` and `lines.geojson` load as MapLibre
GeoJSON sources as they are.

## Rebuild

```
python scripts/run_all.py              # download, build, validate
python scripts/run_all.py --skip-fetch # reuse .cache/
```

Building takes about two and a half minutes after the downloads. Steps: `fetch_sources.py` (16 downloads, about 560 MB; atlas links change every night, so they are looked up on the dataset page by file name) -> `extract_gtfs.py --feed <feed>` (one streaming pass over
the national feed) -> `build_stops.py` -> `build_accessibility.py` -> `build_timetable.py --feed <feed>` ->
`build_inferred_edges.py --feed <feed>` -> `slice_timetable.py --feed fp2026` -> `write_manifest.py` -> `validate.py --online --node`.

A rebuild picks up whatever the publisher has released by then (GTFS twice a week, atlas daily), so counts move.
The exact inputs of the committed files are pinned by sha256 in `SOURCES.json`.

## Licence and attribution

Timetable and atlas data: opentransportdata.swiss terms of use, free reuse, source must be cited as
"opentransportdata.swiss". Municipal boundary (used for checks only, not redistributed): swisstopo free geodata
terms, "© swisstopo". The exact wording per input is in `SOURCES.json`.
