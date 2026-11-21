# transit/ handoff

Owner thread: Bern Transit GTFS and DiDok Data. State of 2026-11-21, 02:40 Europe/Zurich. Nothing is staged or
committed by this thread; everything is inside `bern-research/transit/`.

## What you get

Official scheduled data for every public transport stop in the municipality of Bern, with every boarding edge
and its direction, every trip that serves Bern (kept whole, first to last stop), all calendars, and accessibility
attributes. All of it joins on atlas SLOIDs and DiDok numbers. Two timetable years are built: fp2026 (valid
2025-12-14 to 2026-12-12, today is in it) and fp2027 (valid 2026-12-13 to 2027-12-11).

| Path | Content | Records |
|---|---|---|
| `data/stations.geojson` | stations: `sloid`, `number`, `tier`, WGS84 + LV95, height | 1,123: 208 bern, 386 ring, 529 connected |
| `data/edges.geojson` | boarding edges and areas: `sloid`, `designation`, `designation_operational`, `station_sloid`, WGS84 + LV95, `height_m`, `type`, `compass_direction_deg`, `coord_rounded` | 3,483; bern: 598 edges + 21 areas |
| `data/edge_lookup.json` | `number -> designation -> [edge sloid]` | 1,117 stations |
| `data/gtfs_stop_map_<feed>.json` | GTFS `stop_id -> edge_sloid / station_sloid` with shares | 3,415 (fp2026), 3,084 (fp2027) |
| `data/accessibility_edges.json` | atlas platform-v2 and BfR wheelchair class per edge | 2,902; bern 575 |
| `data/accessibility_stations.json` | atlas stop-point-v2, reference points, toilets, parking, contact points, relations | 1,112; bern 205 |
| `data/sectors.geojson` | platform sectors with coordinates | 1,803; bern 117 on 20 edges |
| `data/<feed>/gtfs_bern_<feed>.zip` | lossless GTFS subset (valid GTFS, source rows verbatim) | fp2026: 140,500 trips, 2,066,447 stop_times, 166 routes, 8,839 services. fp2027: 32,473 trips, 444,996 stop_times, 123 routes, 1,858 services |
| `data/<feed>/timetable.json` | the same timetable, compact; decodes to the zip exactly | fp2026: 11,941 patterns. fp2027: 2,577 patterns |
| `data/fp2026/timetable_2026-11-21_2026-12-12.json` | the same schema, only the trips that run on the 22 days left in the 2026 timetable year; 4.8 MB instead of 19.4 MB | 35,443 trips, 501,227 stop_times |
| `data/<feed>/edge_directions.json` | derived: lines and next stops per edge | 1,294 / 1,174 stops |
| `data/<feed>/segments.geojson` | derived: every stop-to-stop hop | 5,961 / 3,747 |
| `data/<feed>/lines.geojson` | derived: one stop sequence per line and direction | 266 / 220 |
| `data/<feed>/transfers.json` | minimum transfer times, in-seat transfers | 48,383 / 7,219 |
| `data/coverage_stops.json`, `data/coverage_accessibility.json` | coverage logic, counts, known gaps | |
| `SOURCES.json`, `data/MANIFEST.json` | provenance of inputs and outputs (sha256, bytes, licence) | 16 inputs, 25 outputs |
| `validation/` | `report.md`, `report.json`, `sample_departures.md`, `sample_departures.json` | 79 checks |
| `scripts/`, `web/bern-transit.js` | pipeline and a thin reader | 12 scripts |

Total 81 MB, largest file 19.4 MB. Field-level schemas are in `docs/SCHEMA.md`.

fp2027 has a quarter of the trip records of fp2026 but the same service per day (median Tuesday: 8,910 trips in
fp2026, 9,141 in fp2027). The 2026 feed carries a year of construction-site variants as separate trips.

## Coverage logic

1. **Stops.** A stop is in Bern when atlas attributes its service point to municipality FSO number 351. That gives
   204 stop points, plus 4 operating points that own a boarding edge (Bern Europaplatz Süd, Bern Fischermätteli,
   Bern Stöckacker, Bern, Engehalde; `stop_point: false`). All 208 lie inside the swisstopo municipal polygon.
   Three of them are not valid today and come from the atlas timetable-years file (`valid_today: false`): two
   temporary stops of March 2026 and Bern, Engehalde.
2. **Edges.** Every atlas traffic point of those stations: 598 boarding edges and 21 boarding areas in Bern.
3. **Trips.** Every GTFS trip with at least one stop_time at a Bern stop, kept complete. One border stop that
   atlas files under Ostermundigen (Ostermundigen, Waldeck) has an edge inside the polygon; trips serving it are
   included as well.
4. **Adjacent stops.** `ring` = every atlas stop within 5 km of the municipal boundary (386; 295 of them are on a
   Bern trip in fp2026). `connected` = every other station on a Bern trip (529, as far as the through-trains go:
   Berlin, Chur, Romanshorn). Filter on `tier` to get the area you want.
5. **Timetable to edge.** In fp2026, 95.95 % of the 2,066,447 stop_times reference an atlas edge SLOID (97.87 %
   at Bern stops), 4.02 % reference the station only, 0.03 % are foreign stations without a Swiss SLOID.
   In fp2027: 94.29 %, 5.69 %, 0.02 %.
6. **Service days.** Each feed covers all 364 days of its timetable year. All 204 Bern stop points have trips in
   fp2026; 200 in fp2027 (missing: Bern, Kunstmuseum; Bern, Waisenhausplatz; the two temporary stops).

## Validation

`python scripts/validate.py --online --node`: 79 checks, 75 pass, 4 warnings, 0 failed. Highlights:

- `timetable.json` decodes to exactly the stop_times (2,066,447 and 444,996 rows, all 7 columns) and trips
  (all 9 columns) of the GTFS subset, for both feeds.
- Service-day bitmasks equal `calendar.txt` plus `calendar_dates.txt` for all 8,839 and 1,858 services
  (1,154,155 and 227,829 exceptions).
- Times never run backwards; 123,886 stop_times at or after 24:00:00 are kept, the latest is 29:45:00.
- Independent cross-check against `transport.opendata.ch/v1/stationboard` (the API the team app uses), 105
  boards: the five focus stations at five date/times and a seeded random sample of 40 Bern stops in each feed.
  3,898 of 3,898 API departures were found at the same minute and line (fp2026: 2,041, fp2027: 1,857), none of
  ours was absent from the API list, and the platform string equals ours for 1,562 of 1,562.
- GTFS stop coordinates and atlas edge coordinates agree: median 0.18 m, 95 % within 0.4 m, maximum 0.5 m.
- `web/bern-transit.js` returns the same 1,294 departures as `scripts/timetable.py` over 25 queries.
- The window file holds exactly the trips that run from 2026-11-21 to 2026-12-12, with identical stop_times.
- The join section of `bern-research/lead/validate/validate.py` reports no failure for this folder.

The four warnings are known and harmless: two border stops whose edges fall inside the generalised polygon;
tracks 49 and 50 of Bern station are 427 and 445 m from the station point;
14 atlas accessibility relations name an edge that atlas traffic-point-v2 does not hold; four Bern stops have no
trips in fp2027.

## Sample departures

Tuesday 2026-11-24 from 08:00, fp2026. Full boards (five stations, five date/time cases, both feeds) are in
`validation/sample_departures.md`.

**Bern (rail, 8507000)**

| Time | Line | Headsign | Track | Edge SLOID |
|---|---|---|---|---|
| 08:00 | IR15 | Luzern | 10 | ch:1:sloid:7000:5:10 |
| 08:00 | S3 | Biel/Bienne | 12A-C | ch:1:sloid:7000:6:12 |
| 08:00 | S7 | Worb Dorf | 23 | ch:1:sloid:7000:501:23 |
| 08:01 | S9 | Unterzollikofen | 22 | ch:1:sloid:7000:500:22 |
| 08:02 | IC8 | Romanshorn | 2 | ch:1:sloid:7000:1:2 |

**Bern, Bahnhof (tram and bus, 8576646)**

| Time | Line | Headsign | Kerb | Edge SLOID |
|---|---|---|---|---|
| 08:00 | 10 | Ostermundigen, Rüti | L | ch:1:sloid:76646:0:19 |
| 08:00 | 12 | Bern, Holligen | D | ch:1:sloid:76646:0:7 |
| 08:00 | 20 | Bern, Länggasse | F | ch:1:sloid:76646:0:15 |
| 08:00 | 6 | Bern, Fischermätteli | C | ch:1:sloid:76646:0:3 |
| 08:01 | 10 | Schliern, Bus-Endstation | I | ch:1:sloid:76646:0:11 |

**Bern, Zytglogge (8507110)**

| Time | Line | Headsign | Kerb | Edge SLOID |
|---|---|---|---|---|
| 08:00 | 10 | Ostermundigen, Rüti | B | ch:1:sloid:7110:0:3 |
| 08:00 | 10 | Schliern, Bus-Endstation | A | ch:1:sloid:7110:0:4 |
| 08:00 | 7 | Bern, Bümpliz | E | ch:1:sloid:7110:0:2 |
| 08:00 | 8 | Bern, Saali | F | ch:1:sloid:7110:0:1 |
| 08:01 | 12 | Bern, Holligen | C | ch:1:sloid:7110:0:6 |

**Bern Wankdorf (rail, 8516161)**

| Time | Line | Headsign | Track | Edge SLOID |
|---|---|---|---|---|
| 08:03 | S3 | Biel/Bienne | 7 | ch:1:sloid:16161:3:5 |
| 08:05 | S44 | Thun | 5 | ch:1:sloid:16161:2:3 |
| 08:08 | S1 | Fribourg/Freiburg | 1 | ch:1:sloid:16161:0:0 |
| 08:09 | S31 | Belp | 5 | ch:1:sloid:16161:2:3 |
| 08:14 | S2 | Laupen BE | 1 | ch:1:sloid:16161:0:0 |

**Bern Wankdorf, Bahnhof (tram and bus, 8590129)**

| Time | Line | Headsign | Kerb | Edge SLOID |
|---|---|---|---|---|
| 08:00 | 20 | Bern, Länggasse | C | ch:1:sloid:90129:0:2 |
| 08:03 | 9 | Wabern, Tram-Endstation | A | ch:1:sloid:90129:0:10 |
| 08:04 | 20 | Bern, Länggasse | C | ch:1:sloid:90129:0:2 |

**After midnight: Bern (rail), Sunday 2026-11-22 from 00:30.** These trips belong to service day Saturday 21 and
carry GTFS times above 24:00:00.

| Wall clock | GTFS time | Service day | Line | Headsign | Track |
|---|---|---|---|---|---|
| 01:06 | 25:06:00 | 2026-11-21 | IC8 | Zürich HB | 9 |
| 01:09 | 25:09:00 | 2026-11-21 | IC61 | Interlaken West | 7 |
| 01:12 | 25:12:00 | 2026-11-21 | IR65 | Biel/Bienne | 49 |
| 03:00 | 03:00:00 | 2026-11-22 | N1 | Winterthur | 9 |

A calendar exception you can demo: Monday 2026-11-23 is the Zibelemärit. 10,509 trips run that day against 9,127
on the Monday before.

## What is approximate, inferred or missing

- **Line geometry does not exist in the source.** The Swiss GTFS has no `shapes.txt`. `segments.geojson`,
  `lines.geojson`, the bearings in `edge_directions.json` and `vehiclesAt()` use straight lines between stop
  coordinates. All are flagged `inferred: true`. For a 3D scene a tram will cut corners unless the geometry
  threads supply track alignments; segments carry both edge SLOIDs so an alignment can be attached per hop.
- **Edges without coordinates:** 34 in Bern (19 boarding edges, 15 boarding areas), 261 over all tiers. Geometry
  is null, not guessed. The list is in `coverage_stops.json` under `known_gaps`.
- **Rounded coordinates:** 141 of 598 Bern edges are held in atlas to whole metres (`coord_rounded: true`).
- **No public letter:** 375 of 598 Bern edges have no `designation`; they have `designation_operational` only.
- **No compass direction:** 170 of 598 Bern edges. `edge_directions.json` gives a timetable-derived bearing for
  the edges that have departures.
- **Two Bern stations have no edge at all:** Bern Matte and Bern Münsterplattform (the Matte lift).
- **47 Bern edges are not used by either timetable** (`in_gtfs_fp2026` and `in_gtfs_fp2027` both false).
- **14 edges** (4 in Bern) have `inferred: true`: atlas dropped their parent link because the stop is not valid
  today, so the station was taken from the edge's own number.
- **Heights** are atlas values. Atlas describes them as heights above sea level; the LN02 datum is the Swiss
  default and was not verified independently here. 19 Bern edges have no height.
- **Sectors** are single points without extent. Reference points, toilets, parking and contact points have no
  coordinates in atlas.
- **Time zone:** the feed says `Europe/Berlin` for every agency. Offsets and DST dates are identical to
  `Europe/Zurich`; the compact outputs say `Europe/Zurich`, the zip keeps the source value.
- **Frequency-based service:** the Marzili funicular is published as a headway, not as departures; the readers
  skip it unless asked (`include_frequency`).
- **Boundary polygon** is swisstopo's generalised web geometry. It is used only for checks and the 5 km ring; the
  Bern tier itself comes from the atlas municipality attribute.
- **BfR wheelchair columns:** the meaning of the `sg` / `ug` prefixes (track-bound / not track-bound) is our
  reading of the data, not a statement of the publisher.
- **Realtime is not included.** GTFS-RT needs a personal API key; none is configured on this machine.
  `scripts/gtfs_rt.py` is written but has never been run against the live endpoint. `trip_id` and `stop_id` are
  kept verbatim so the join is direct once a key exists. A realtime feed belongs to one static feed version, so
  rebuild when the static file changes (Wednesdays and Saturdays).
- **Trip ids are stable only within one feed version.** `original_trip_id` (SJYID) is the stable journey id.
- **No official line ids (SLNID).** atlas publishes a line directory (`line-v2`), but joining it to GTFS routes by
  operator and line number is ambiguous for PostAuto and long-distance lines (95 of 139 lines match uniquely), so
  it was left out rather than guessed. Lines are identified by operator, `route_short_name` and `route_desc`.

## How to rebuild

```
cd bern-research/transit
python scripts/run_all.py              # 16 downloads (about 560 MB) into .cache/, then build and validate
python scripts/run_all.py --skip-fetch # rebuild from .cache/ in about 2.5 minutes; checked: the outputs come out byte-identical
```

Python 3.11, standard library only. No key or login is needed for any input. A fresh download gives newer
source versions (GTFS on Wednesdays and Saturdays, atlas every night), so counts will move; the versions behind
the committed files are pinned by sha256 in `SOURCES.json`. atlas download links change with every nightly
publication. `fetch_sources.py` therefore finds the current link on the dataset page by file name
(`--resolve-only` shows the links without downloading; two had already changed during this session).

Freshness, checked at 02:23 on 2026-11-21: the inputs are the GTFS release of 2026-11-18 (still the newest one
behind the permalink) and the atlas publication of 2026-11-20. The atlas publication of 2026-11-21 came out
during the session; compared row by row for the stations and edges in coverage it differs in one row only (the
end date of one edge at Bärau, Schärischachen, tier `connected`), so the files were not rebuilt.

## How to load

- **Maps:** `stations.geojson`, `edges.geojson`, `sectors.geojson`, `<feed>/segments.geojson` and
  `<feed>/lines.geojson` are plain GeoJSON sources. Filter `tier == 'bern'` for the municipality.
- **Departures and vehicles:** `web/bern-transit.js` sets `window.BERN_TRANSIT` (same pattern as `events.js`).
  `BERN_TRANSIT.load(url)` returns `{ departures(number, date, time, limit), vehiclesAt(date, time), runs(), meta }`.
  `scripts/timetable.py` is the Python twin.
- **Placing a live departure on its edge:** the team app calls `transport.opendata.ch`. Take `station.id` and
  `stop.platform` from a stationboard entry and look up
  `edge_lookup.stations[id].by_gtfs_platform_code[platform]`, then `.by_designation[platform]`. The edge SLOID
  leads to the coordinate, height and compass direction in `edges.geojson` and to `accessibility_edges.json`.
- **Any GTFS tool:** `data/<feed>/gtfs_bern_<feed>.zip` is a standard feed.
- **Choosing the feed:** dates up to 2026-12-12 use `fp2026`, from 2026-12-13 use `fp2027`.
- **Lighter load in a browser:** for dates from 2026-11-21 to 2026-12-12 load
  `data/fp2026/timetable_2026-11-21_2026-12-12.json` (4.8 MB) instead of the full year (19.4 MB). Same reader,
  same results for those dates. `python scripts/slice_timetable.py --feed <feed> --from <date> --to <date>` cuts
  any other window.

## Suggested commit set

Everything under `bern-research/transit/` except `.cache/` (already ignored by `transit/.gitignore`):
`README.md`, `STATUS.md`, `HANDOFF.md`, `SOURCES.json`, `.gitignore`, `docs/`, `scripts/`, `web/`, `validation/`,
`data/`. No file exceeds 25 MB.

Attribution to carry into any published use: "Source: opentransportdata.swiss".
