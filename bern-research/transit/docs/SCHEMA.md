# transit/ schemas

All files are UTF-8 JSON or GeoJSON. Geometry is WGS84 (EPSG:4326), lon/lat, 7 decimals. LV95 (EPSG:2056) is kept
as `lv95_e` / `lv95_n` where the source has it. Heights are metres as published by atlas (LN02 according to atlas;
`null` when atlas holds no height, which atlas stores as 0). Times are `Europe/Zurich`.

Every feature or record carries `source` (dataset and file) and `inferred` (`true` only when a value was derived,
matched or estimated here), with `inferred_how`. Files that are derived as a whole say so in their header.

## Identifiers

| Id | Example | Where it comes from | Used as |
|---|---|---|---|
| station SLOID | `ch:1:sloid:7110` | atlas service point | `sloid` in stations, `station_sloid` elsewhere |
| station number | `8507110` | atlas `number` (DiDok / UIC), also the id of transport.opendata.ch and the GTFS `didok` column | `number`, `station_number` |
| edge SLOID | `ch:1:sloid:7110:0:4` | atlas traffic point (boarding platform) | `sloid` in edges, `edge_sloid` elsewhere |
| designation | `A`, `7` | atlas `designation`: the public letter or track | `designation` |
| operational designation | `04` | atlas `designationOperational` | `designation_operational` |
| GTFS stop_id | `ch:1:sloid:7110:0:4`, `ch:1:sloid:7000_gen:ch:1:sloid:7000:3:5_pf:5A-C`, `Parentch:1:sloid:7110` | GTFS `stops.txt`, verbatim | `stop_id` |
| GTFS trip_id | `.ojp-91-29-Y.1.TA.38.j26` | GTFS `trips.txt`, verbatim; valid within one feed version | `trip_id` |
| journey id (SJYID) | `ch:1:sjyid:100001:1343-002` | GTFS `original_trip_id`, verbatim | `original_trip_id`, `oid` |
| service_id | `TA+00000` | GTFS, verbatim | `services.ids` |
| route_id | `91-9-j26-1` | GTFS, verbatim | `routes[][0]` |

In the current feeds most GTFS stop ids are already the atlas edge SLOID. `gtfs_stop_map_<feed>.json` gives the
resolution for every stop id, including the generated sector variants and the stops that only name the station.

## Tiers

| `tier` | Rule |
|---|---|
| `bern` | atlas service point with `fsoNumber` 351 (municipality of Bern) that is a stop point, or an operating point that owns a boarding edge (`stop_point: false`; four of them) |
| `ring` | the same outside Bern, coordinate at most 5 km from the municipal boundary (swisstopo polygon); listed whether or not a Bern trip calls there |
| `connected` | any other station called at by a trip that serves a `bern` stop in fp2026 or fp2027 |

Stops and edges that atlas does not hold as valid on the retrieval date but that were valid at some point of the
current or next timetable year (temporary stops, stops opening on 2026-12-13) are included with
`valid_today: false`.

## data/stations.geojson

One Point feature per station. `id` = station SLOID (or `didok:<number>` for four foreign stations).

| Property | Type | Meaning |
|---|---|---|
| `sloid` | string, null | station SLOID; null for foreign stations atlas does not hold |
| `number` | int | DiDok / UIC number |
| `name`, `name_long`, `abbreviation` | string | atlas `designationOfficial`, `designationLong`, `abbreviation` |
| `tier` | string | see above |
| `municipality`, `fso_number`, `canton`, `country` | | atlas attributes |
| `means_of_transport` | string[] | atlas: `TRAIN`, `TRAM`, `BUS`, `CABLE_RAILWAY`, `ELEVATOR`, ... |
| `stop_point`, `stop_point_type` | bool, string | atlas `stopPoint`, `stopPointType` |
| `operator_abbr`, `operator_sboid` | string | responsible business organisation |
| `lv95_e`, `lv95_n`, `height_m` | number | LV95 coordinates and height |
| `coord_rounded`, `coord_rounded_how` | bool, string | true when atlas holds the coordinate only to whole metres or coarser |
| `edge_count`, `boarding_area_count` | int | boarding platforms and boarding areas in `edges.geojson` |
| `valid_from`, `valid_to`, `valid_today`, `edition_date`, `status` | | atlas version fields |
| `dist_to_bern_boundary_m` | int | distance to the municipal boundary, negative inside (derived, generalised polygon) |
| `inside_boundary_polygon` | bool | point-in-polygon cross-check (derived) |
| `in_gtfs_fp2026`, `in_gtfs_fp2027` | bool | station occurs in the Bern subset of that feed |

## data/edges.geojson

One feature per atlas traffic point of the stations above: boarding platforms (kerbs, tracks) and boarding areas.
`geometry` is `null` when atlas has no coordinate (`has_geometry: false`).

| Property | Type | Meaning |
|---|---|---|
| `sloid` | string | edge SLOID |
| `type` | string | `BOARDING_PLATFORM` (the edge a vehicle stops at) or `BOARDING_AREA` (a platform body that groups edges) |
| `designation`, `designation_operational` | string, null | public letter or track; operational code |
| `station_sloid`, `station_number`, `station_name` | | atlas parent service point (always present in `stations.geojson`) |
| `area_sloid` | string, null | atlas `parentSloid`: the boarding area this edge belongs to |
| `tier` | string | tier of the parent station |
| `compass_direction_deg` | number, null | atlas `compassDirection` |
| `length_m`, `boarding_area_height_cm` | number, null | atlas `length`, `boardingAreaHeight` |
| `lv95_e`, `lv95_n`, `height_m` | number, null | |
| `has_geometry`, `coord_rounded`, `coord_rounded_how` | | geometry present; coordinate rounded to whole metres or coarser |
| `valid_from`, `valid_to`, `valid_today`, `edition_date`, `status` | | atlas version fields |
| `in_gtfs_fp2026`, `in_gtfs_fp2027` | bool | a stop_time of that feed references this edge |
| `inferred` | bool | true for 14 edges (4 of them tier `bern`) whose atlas row carries no parent service point because the stop is not valid today; the station was taken from the edge's own `number` |

`compass_direction_deg` agrees with the direction vehicles leave in: for the 379 Bern edges where both are known
and departures leave one way, 305 are within 45 degrees of the timetable-derived bearing and 9 are opposite.

## data/edge_lookup.json

`stations[<number>]` = `{ sloid, name, tier, by_designation, by_designation_operational, by_gtfs_platform_code }`.
Each map goes from a code to a list of edge SLOIDs.

- `by_designation`: atlas public designation. This is the platform string transport.opendata.ch returns for
  trams and buses (`"A"`) and for tracks (`"7"`). A code can map to several edges (Bern track 5 has two, Zytglogge
  `K` has two).
- `by_gtfs_platform_code`: the `platform_code` of GTFS stops, which includes sector strings (`"12A-C"`, `"5E-H"`)
  and resolves most of those ambiguities, because it names the one edge the timetable uses.
- Lookup order for an API platform string: `by_gtfs_platform_code`, then `by_designation`, then the station.

In the validation run the platform string of 1,562 stationboard departures matched the platform of the
timetable 1,562 times.

## data/gtfs_stop_map_<feed>.json

Header: `feed`, `scope`, `kinds`, `summary_all_stops`, `summary_tier_bern`, `summary_tier_bern_and_ring`
(`stop_times_rows`, `rows_by_kind`, `share_edge_sloid`, `share_station_sloid_only`, `share_no_sloid`),
`stop_count_by_kind`. Then `stops[]`:

| Field | Meaning |
|---|---|
| `stop_id` | GTFS stop id, verbatim |
| `kind` | `edge`, `edge_sector_variant`, `edge_by_designation`, `edge_unresolved`, `station`, `station_not_in_atlas`, `parent_station` |
| `edge_sloid` | atlas edge, or null |
| `edge_station_sloid` | atlas parent of that edge (differs from `station_sloid` for Bern Europaplatz, whose edges atlas files under Bern Europaplatz Süd) |
| `station_sloid`, `number`, `tier`, `stop_name` | station of the GTFS stop |
| `platform_code`, `parent_station`, `original_stop_id` | GTFS columns, verbatim |
| `lon`, `lat` | GTFS coordinate |
| `stop_times_rows` | stop_times of the Bern subset that reference this stop id |
| `inferred`, `inferred_how` | true for `edge_by_designation` (GTFS names an edge atlas does not hold; matched by platform code = designation within the station) |

## data/accessibility_edges.json, data/accessibility_stations.json

`edges[<edge sloid>]` = `{ station_sloid, station_number, designation, designation_operational, tier,
atlas_platform?, bfr_wheelchair? }`. `stations[<station sloid>]` = `{ number, name, tier, atlas_stop_point?,
reference_points?, toilets?, parking_lots?, contact_points?, relations?, bfr_wheelchair? }`.

- `atlas_platform`, `atlas_stop_point` and the list items are atlas rows with field names turned into snake_case
  and empty cells left out. Enumerations are as published (`YES`, `NO`, `PARTIALLY`, `TO_BE_COMPLETED`,
  `NOT_APPLICABLE`, `PLATFORM_ACCESS_WITHOUT_ASSISTANCE`, `PLATFORM_ACCESS_WITH_ASSISTANCE`,
  `PLATFORM_NOT_WHEELCHAIR_ACCESSIBLE`, ...). Lengths and heights in `atlas_platform` are centimetres as in atlas.
- `relations[]`: `element_sloid` (edge, toilet, parking lot or contact point), `reference_point_sloid`,
  `reference_point_element_type`, `step_free_access` (`YES`, `YES_WITH_LIFT`, `YES_WITH_RAMP`, `NO`, ...),
  `tactile_visual_marks`, `contrasting_areas`.
- `bfr_wheelchair[]`: `{ sg[], ug[], valid_from, valid_to, valid_today }` with the flags `Autonomie`,
  `Rampeneinsatz`, `Voranmeldung`, `Ersatztransport`, `keinZugang`, `keineInfo` as published. The prefixes `sg` and
  `ug` are the publisher's. In the data they line up with track-bound vehicles (train, tram) and vehicles that are
  not track-bound (bus); that reading is ours, the dataset page does not define them.
- Reference points, toilets, parking lots and contact points have no coordinates in atlas.

## data/sectors.geojson

One Point per platform sector. Properties: `sloid`, `type` (`SECTOR`), `designation` (`A`, `B`, ...),
`edge_sloid`, `edge_designation`, `station_sloid`, `station_number`, `station_name`, `tier`, `lv95_e`, `lv95_n`,
`length_m`, `height_m` (both null: atlas publishes 0), `valid_from`, `valid_to`, `edition_date`, `status`.
Atlas gives one point per sector and no extent, so a sector's span has to be taken from the neighbouring points.

## data/<feed>/gtfs_bern_<feed>.zip

A valid GTFS feed with the ten source tables (`agency`, `routes`, `trips`, `stop_times`, `stops`, `calendar`,
`calendar_dates`, `frequencies`, `transfers`, `feed_info`). It contains every trip that calls at a `bern` stop,
complete from first to last stop, and every row those trips reference. Rows are byte-for-byte the source rows,
including the extra columns `original_stop_id`, `didok` (stops) and `original_trip_id`, `hints` (trips).
`agency_timezone` is `Europe/Berlin` in the source and is left as it is; it has the same offset and DST dates as
`Europe/Zurich`.

## data/<feed>/timetable.json

The same timetable as the zip, pattern-encoded. `scripts/validate.py` decodes it and compares it with the zip
row by row and column by column (trips and stop_times), so nothing is lost.

```
meta        feed, source, source_sha256, feed_version, feed_start_date, feed_end_date, timezone, counts
agencies    [[agency_id, name, url]]
routes      [[route_id, agency index, short_name, long_name, desc, route_type]]
stations    { "<number>": [station sloid | null, name, tier] }
stops       [[stop_id, number, edge sloid | null, platform_code | null, lon, lat]]
services    { ids: [service_id], masks: ["<hex>"] }
headsigns   [string]            hints  [string]
patterns    [{ r, d, h, s, q?, pu?, do?, p, t }]
frequencies [[pattern index, trip index, start_s, end_s, headway_s, exact_times]]
```

Pattern fields:

| Field | Meaning |
|---|---|
| `r` | index into `routes` |
| `d` | GTFS `direction_id` (0 or 1) |
| `h` | index into `headsigns` (GTFS `trip_headsign`) |
| `s` | stop sequence as indexes into `stops` |
| `q` | original `stop_sequence` values, only when they are not 1..n |
| `pu`, `do` | `pickup_type`, `drop_off_type` per stop, only when not all 0 |
| `p` | time profiles: `[arr0, dep0, arr1, dep1, ...]` in seconds relative to the first departure |
| `t.st` | first departure of each trip, seconds after service-day midnight |
| `t.id`, `t.sv`, `t.pf` | `trip_id`, index into `services`, index into `p` |
| `t.sn`, `t.oid`, `t.hi`, `t.bl` | `trip_short_name`, `original_trip_id`, index into `hints`, `block_id` (only when set) |

Time of trip `k` at stop `j`: arrival `t.st[k] + p[t.pf[k]][2j]`, departure `t.st[k] + p[t.pf[k]][2j+1]`.
Values of 86400 and more are after midnight of the next calendar day (GTFS `24:00:00` and later; the latest is
`29:45:00`). A service day starts at noon minus 12 hours, which only matters on the two DST-change days.

Service days: `masks[i]` is a hexadecimal integer. Bit `n`, counted from the least significant bit, is set when
service `i` runs on `feed_start_date + n` days. The masks already contain `calendar.txt` and every
`calendar_dates.txt` exception.

`frequencies` holds the two trips of the Marzili funicular, which the feed describes by headway instead of
single departures; the readers skip them unless asked.

## data/fp2026/timetable_<from>_<to>.json

A window of `timetable.json` with the same structure: only the trips whose service runs on a day from `<from>` to
`<to>` (and on the day before `<from>`, for trips still running after midnight). `meta.window` = `{ from, to,
note, derived_from }`; `meta.counts` is recomputed. Service masks are unchanged. Outside the window the file is
incomplete. Built by `scripts/slice_timetable.py`; the validation checks that it holds exactly those trips with
identical stop_times.

## data/<feed>/edge_directions.json  (derived, `inferred: true`)

`stops[]` for every GTFS stop in tiers `bern` and `ring`: `stop_id`, `edge_sloid`, `station_sloid`, `number`,
`stop_name`, `platform_code`, `tier`, `routes[]`, `trip_days`, `terminating_only`, `bearing_mean_deg`,
`bearing_concentration`, `next[]` (`route`, `headsign`, `next_number`, `next_name`, `bearing_deg`, `trip_days`;
at most 12, most frequent first). `trip_days` = trips times operating days in the feed. Bearings are straight
lines from this stop to the next stop.

## data/<feed>/segments.geojson, lines.geojson  (derived, `inferred: true`)

`segments`: one LineString per ordered pair of consecutive stops: `from_stop_id`, `to_stop_id`,
`from_edge_sloid`, `to_edge_sloid`, `from_station_sloid`, `to_station_sloid`, `from_number`, `to_number`,
`from_name`, `to_name`, `from_tier`, `to_tier`, `routes[]`, `route_types[]`, `trips`, `trip_days`,
`run_time_s_median`, `length_m_straight`.

`lines`: one LineString per line (operator, short name, category) and `direction_id`, the stop sequence with the
most trip-days: `route_short_name`, `route_desc`, `route_type`, `agency_id`, `agency_name`, `direction_id`,
`headsign`, `first_stop`, `last_stop`, `stop_ids[]`, `stop_numbers[]`, `stops_in_bern`, `route_ids[]`,
`pattern_trip_days`, `line_trip_days`, `line_pattern_count`.

Both are straight lines between stop coordinates. They are not track or road alignments.

## data/<feed>/transfers.json

`columns` + `rows`: `from_stop_id`, `to_stop_id`, `from_number`, `to_number`, `transfer_type`,
`min_transfer_time` (seconds), `from_route_id`, `to_route_id`, `from_trip_id`, `to_trip_id`. Stop-to-stop rules
between `bern` and `ring` stops (type 2) and all trip-to-trip rules of the subset (type 4, in-seat transfer).
The full table is in the zip.

## route_type values in these feeds

Extended GTFS route types: 102 long distance (IC, EC, ICE), 103 inter-regional (IR), 106 regional (RE), 109
suburban (S), 117 special (EXT), 700 bus (B, EV = rail replacement), 705 night bus (BN), 900 tram (T), 1303
elevator (ASC, the Matte lift), 1400 funicular (FUN, Marzilibahn). `route_desc` carries the Swiss category code.
