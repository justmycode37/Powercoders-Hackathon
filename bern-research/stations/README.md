# Bern station geometry and 3D station models

Georeferenced, app-ingestible geometry of public transport stops in and around Bern, built only from open
data, with the origin and reliability of every feature written on the feature.

- **Citywide:** one line (or point) per atlas boarding edge for 446 stations, plus platform surfaces, shelters,
  sectors, surveyed kerb candidates and the official step-free access register.
- **59 focus stations:** level-aware geometry (platforms, passages, stairs, escalators, lifts, entrances, access
  points, surveyed underground outlines, buildings), a pedestrian graph and a light GLB model each. Three are the
  priority stations (Bern Bahnhof, Zytglogge, Wankdorf); 56 more are picked by rule.
- **Fallback for every other stop:** four generic GLB pieces and a placement table for every edge that has a line.

Numbers and limits are in [HANDOFF.md](HANDOFF.md); the current state is in [STATUS.md](STATUS.md).

## Files

| Path | Content |
|---|---|
| `data/boarding_edges.geojson` | one feature per atlas boarding edge (`id` = edge SLOID), `LineString`, `Point` or `null` geometry |
| `data/station_features.geojson` | `platform_surface`, `shelter`, `sector_marker`, `sector_board`, `sector_span`, `surveyed_kerb_candidate`, linked to station and edge |
| `data/stations.geojson` | one point per station with edge counts, best geometry tier and bbox |
| `data/accessibility.json` | atlas register of named access points per station and step-free access to each platform |
| `data/edge_placements.json` | position, rotation and scale for placing a generic stop model on each edge |
| `data/focus/index.json` | list of focus stations: tier, stations inside, level table, counts |
| `data/focus/<slug>.geojson` | all features of one focus station, with `level` |
| `data/focus/<slug>.walk_graph.json` | pedestrian graph of that station (nodes, edges, levels) |
| `models/<slug>.glb`, `models/<slug>.model.json` | 3D model of a focus station and its sidecar |
| `models/archetypes/*.glb` | generic stop pieces: `tram_stop`, `bus_stop`, `bus_stop_pole`, `rail_platform` |
| `SOURCES.json` | every input: url, publisher, licence, retrieved, bytes, sha256, used_for |
| `references.json` | operator plans used for checks (links only) and what was read off them |
| `validation/report.md`, `report.json` | result of `tools/validate.py` |
| `tools/` | acquisition and build scripts (Python 3.11, standard library only) |

Slugs: `bern-bahnhof`, `zytglogge`, `wankdorf`, and `<station number>-<name>` for the rule-based ones, for example
`8504108-bern-europaplatz`.

## Conventions

- GeoJSON, WGS84, lon/lat, 7 decimals. Where the source has LV95 (EPSG:2056) it is kept as `lv95_e`, `lv95_n`.
  Conversion is done in `tools/geo.py` with the rigorous swisstopo formulas (checked against 1,082 atlas coordinate
  pairs, largest difference 1.6 cm).
- Heights are metres above sea level. atlas heights are used as published and assumed to be LN02;
  `terrain_height_ln02_m` is swissALTI3D terrain from the swisstopo height service.
- `station_sloid` and `station_number` (string, for example `"8507110"`) are on every feature that belongs to a
  stop; `edge_sloid` on everything that belongs to a boarding edge.
- Levels follow OSM numbering: 0 is the street or main platform level, negative is below.

### Honesty fields (on every feature)

| Field | Meaning |
|---|---|
| `source`, `source_id`, `source_url` | dataset and record the geometry comes from |
| `licence` | licence of that source; OSM-derived features say ODbL |
| `geometry_quality` | `surveyed` (Stadt Bern cadastral survey, SBB kerb points), `official_point` (atlas or SBB register coordinate), `official_city_point` (Stadt Bern kerb point), `community` (OSM), `approximate` (constructed by this project), `missing` |
| `inferred`, `inferred_how` | `true` when the geometry or a link was derived, matched by proximity, estimated or drawn, with the method |
| `dim_quality`, `height_quality`, `width_quality`, `length_quality`, `clear_height_quality` | `surveyed`, `source_derived`, `approximate` or `missing` for that dimension, with a `*_note` where a nominal value was used |
| `verified_against` | list of independent sources that confirm the feature, each with the match rule and a distance |
| `plan_check` | focus stations only: result of reading the operator's kerb plan (letter present, street, position class) |

## `data/boarding_edges.geojson`

One feature per atlas `BOARDING_PLATFORM`. `geometry_method` says how the line was obtained:

| `geometry_method` | `geometry_quality` | Geometry |
|---|---|---|
| `sbb_behig_kerb_points` | `surveyed` | SBB's kerb points (1 m spacing, LV95) chained into a line; linked to the atlas edge by equal track number and proximity. `kerb_height_profile` gives the SBB height class along the line |
| `av_bahnsteig_outline` | `surveyed` | long side of a platform outline (`Bahnsteig`) from the Stadt Bern cadastral survey, nearest to the atlas point; rail edges only, used where SBB has no kerb points |
| `osm_platform` | `community` | OSM platform way, or one long side of an OSM platform polygon: the side that has the platform on the right of the atlas direction of travel, else the side nearest to the atlas point. Matched within 15 m (rail 30 m), preferring the same `ref` letter (`osm_ref_check`). A tram or bus edge never takes a railway platform or a line longer than 100 m; a line contested by two different edges goes to the nearer one (`osm_platforms_left_to_a_nearer_edge` on the other) |
| `constructed` | `approximate` | straight line through the atlas point; bearing from atlas `compassDirection`, else the nearest OSM track or road; length from atlas, else a nominal 42 m (tram) or 18 m (bus) |
| `point_only` | `official_point` | the atlas coordinate; no bearing could be derived |
| `city_kerb_point` | `official_city_point` | point of the one Stadt Bern kerb whose label equals the edge's designation or operational designation, for edges without an atlas coordinate (rule in place; no edge qualifies at present) |
| `none` | `missing` | atlas publishes no coordinate for this edge; `geometry` is `null` and `no_geometry_reason` says why no city kerb could be matched |

Main properties: `designation` (public letter or track), `designation_operational`, `parent_area_sloid`,
`station_modes`, `mode_guess`, `atlas_height_m`, `atlas_length_m`, `atlas_boarding_height_cm`,
`atlas_compass_direction_deg`, `atlas_lon`, `atlas_lat`, `lv95_e`, `lv95_n`, `length_m`, `axis_bearing_deg`,
`dist_atlas_to_geometry_m`, `platform_side_bearing_deg` (bearing pointing from the kerb into the waiting area) with
`platform_side_how`, `lines_at_kerb` (lines and destinations of the paired Stadt Bern kerb point: paired by station
number and kerb letter, else the city kerb nearest to the edge line within 6 m when the edge is also that kerb's
nearest edge; the pairing is in `verified_against`), `city_kerb_letter` (the city's letter for an edge without an
atlas letter; never overwrites `designation`), `city_kerb_candidate` and `no_geometry_reason` (edges without an
atlas coordinate), `prm` (atlas
accessibility attributes of the edge), `step_free_access` (list: named atlas reference point, its type, and
`YES`, `YES_WITH_LIFT`, `YES_WITH_RAMP`, `NO` or `TO_BE_COMPLETED`), `surveyed_kerb_candidate` (pointer to the
candidate feature with its mean offset), `sbb_partial_coverage`, `in_transit_edges`, `transit_tier`, `atlas_valid_today`,
`atlas_position_conflict` (text, when the atlas coordinate lies on a different SBB track than its track number).

## `data/station_features.geojson`

| `feature_type` | Geometry | Source | Notes |
|---|---|---|---|
| `platform_surface` | Polygon | OSM | `edge_sloids` it serves, `length_m`, `width_m`, `area_m2` measured on the polygon |
| `shelter` | Polygon or Point | Stadt Bern cadastral survey (`Unterstand`), OSM outside the city | footprint surveyed; `height_m` 3.0 is nominal (`height_quality: approximate`) |
| `sector_marker` | Point | atlas sectors | `sector`, `sector_sloid`, `edge_sloid`, `chainage_on_edge_m` |
| `sector_board` | Point | SBB `sektortafel` | `sector_front`, `sector_back`, `track`, linked to the edge by track number |
| `sector_span` | LineString | derived from SBB sector boards and the edge line | stretch of the edge between two consecutive boards that both show the letter; `sector`, `from_chainage_m`, `to_chainage_m`; `inferred: true` (Bern and Bern Wankdorf only, where SBB publishes boards) |

| `surveyed_kerb_candidate` | LineString | Stadt Bern cadastral survey, land cover `Trottoir` / `Verkehrsinsel` | stretch of a surveyed pavement or traffic-island boundary that runs within 3.5 m of a tram/bus edge line for at least 60 % of its length; `mean_offset_m`, `max_offset_m`, `offset_direction`, `share_of_edge_matched`. The survey does not say whether it is the boarding kerb or the back of the pavement, so it is a candidate and never replaces the edge geometry |

## `data/accessibility.json`

Per station (31 rail stations that have reference points in atlas): `reference_points` (named access points such
as "Hauptzugang via Bahnhofplatz", with type and `main`), `relations` (reference point to platform, toilet, parking
or contact point with `step_free_access`, `tactile_visual_marks`, `contrasting_areas`) and `stop_point` (assistance,
ticket machines, dynamic information). Official atlas PRM data, `inferred: false`. atlas publishes the reference
points without coordinates, so they are not on the map; the relations are also copied onto each boarding edge.

## `data/focus/<slug>.geojson`

`metadata` holds `stations` (role `primary` or `adjacent`), `levels` (the level table) and `tier`. Every feature has
`focus_zone`: `station_core` (within 45 m of a public boarding edge of the primary stations) or `surroundings`.

| `feature_type` | Geometry | Source | Level |
|---|---|---|---|
| `boarding_edge`, `platform_surface`, `shelter`, `sector_marker`, `sector_board`, `sector_span`, `surveyed_kerb_candidate` | as above | as above | from the OSM platform level tag, else assumed 0 (`level_source`) |
| `passage` | LineString or Polygon | OSM footways that are tunnel, indoor, covered, on a bridge or on a level other than 0 | OSM `level`; for untagged tunnels with a negative `layer` the layer is used (`level_source: inferred`) |
| `stairs`, `escalator`, `ramp_or_link`, `moving_walkway` | LineString | OSM | `levels` plus `from_level` and `to_level` along the line direction where the ends could be resolved |
| `lift` | Point or Polygon (shaft) | OSM | `levels` served |
| `entrance` | Point | OSM entrance nodes on the station building or on a passage; `entrance_class` | OSM `level`, else 0 |
| `access_point` | Point | derived: end node of a tunnel, indoor or stair way that also lies on an open-air way | 0; `connects_levels`, `leads_to` |
| `underground_structure`, `underpass_outline`, `stairs_outline`, `bridge_outline`, `canopy` | Polygon or LineString | Stadt Bern cadastral survey | not recorded in the survey (`level: null`), except canopies |
| `building_footprint` | Polygon | Stadt Bern cadastral survey | ground outline, no height (`height_quality: missing`) |
| `building_part`, `roof` | Polygon | OSM | `height_m` from the OSM height tag, else storeys x 3.5 m (approximate), else missing |
| `ticket_machine`, `clock` | Point | SBB registers | not recorded |

Level table (`metadata.levels`), in this order of preference, with the method written in `elevation_source`:
1. median atlas height of the boarding edges on that level (`elevation_quality: source_derived`);
2. median measured height of swissTLM3D footpaths that run within 3.5 m of the OSM features of that level
   (`source_derived`; needs `../city3d/data/network/tlm_paths_3d.geojson`, read-only; only heights at least 2 m
   above or below level 0 count, so the ground under a bridge is ignored);
3. interpolation between two known levels, or a nominal 4.5 m per level from the nearest known level on the
   level-0 side (`approximate`). Each feature repeats its level's value in `level_elevation_m` and
`level_elevation_quality`. Street-level edges, entrances and access points also carry `terrain_height_ln02_m`.

`walk_graph_node` on a boarding edge is the nearest graph node on the same level (an inferred link).

## `data/focus/<slug>.walk_graph.json`

`nodes`: `id` (OSM node id, or `c<lon>,<lat>` for road vertices whose extract carries no ids), `lon`, `lat`, `kind`
(`lift`, `entrance`, `access_point` or null), `levels` (lifts).
`edges`: `id`, `a`, `b`, `way` (OSM way id), `kind` (`walk`, `stairs`, `escalator`, `moving_walkway`, `street`),
`street_class`, `levels` (null = street level), `length_m`, `tunnel`, `indoor`, `covered`, `conveying`, `wheelchair`,
`name`, `coords`. OSM-derived, ODbL. `street` edges are road centrelines, walkable along a pavement that OSM does not
map separately; crossing a road is only modelled where OSM has a footway across it. The graph covers the focus
radius and has not been checked against a routing engine; connectivity per station is in `validation/report.md`.

## 3D models

Frame of every GLB (also in `asset.extras.frame` and in the sidecar): metres, right-handed, **+Y up, +X east,
+Z south**. Origin = (`origin_lv95_e`, `origin_lv95_n`, `origin_height_m`), so for a vertex (x, y, z):
`E = origin_lv95_e + x`, `N = origin_lv95_n - z`, `height = origin_height_m + y`. `origin_wgs84` is given too.

One glTF node per feature type and level (`passage@-1`, `boarding_edge@0`, `lift@-1..0`), so a level or a type can
be hidden. No normals or textures; materials are double-sided flat colours. The sidecar `<slug>.model.json` lists
`feature_index` (feature id, node, first index, index count) for picking, `approximations` (what was drawn with a
nominal dimension and how often) and `skipped` (features left out because they have no level or height).

Fallback for stops without a focus model:

1. `data/edge_placements.json` has one row per edge with a line: `archetype`, `lon`, `lat`, `height_m`,
   `rotation_y_deg`, `scale_x`. Load `models/archetypes/<archetype>.glb`, rotate about +Y, scale X.
   Archetype frame: +X along the kerb, +Z from the kerb into the platform, origin on the kerb line at mid length,
   y = 0 at the platform top. Archetypes are generic shapes (CC0), not measured.
2. Or build a per-station model from the citywide data: `python tools/build_models.py 8507110` (or `--all`) writes
   `.cache/models/<number>.glb` (not committed; all 400-odd stations take a few seconds).

In MapLibre the GeoJSON can be drawn directly: `level_elevation_m` and `height_m` are ready for
`fill-extrusion-base` and `fill-extrusion-height` after subtracting the terrain height.

## Rebuild

```
python tools/fetch_sources.py      # downloads into .cache/ (about 130 MB), rewrites SOURCES.json
python tools/build_geometry.py     # data/boarding_edges, station_features, stations, build-report
python tools/build_focus.py        # data/focus/*   (--no-network uses cached terrain heights)
python tools/build_models.py       # models/*, data/edge_placements.json
python tools/validate.py           # validation/report.md, exit code 1 on FAIL
```

Two optional read-only inputs from sibling folders: `build_geometry.py` reads `../transit/data/edges.geojson` to
add atlas edges of other validity dates and to set `in_transit_edges`; `build_focus.py` reads
`../city3d/data/network/tlm_paths_3d.geojson` (swissTLM3D, swisstopo) for measured level heights. Without them the
build still runs: fewer edges, and those levels fall back to nominal heights. Overpass and ArcGIS answers are live query results, so a later fetch
can differ from the files hashed in `SOURCES.json`.

## Attribution

- atlas / DiDok data: opentransportdata.swiss (SBB, Systemaufgaben Kundeninformation).
- SBB open data (data.sbb.ch).
- Geoinformation Stadt Bern (Amtliche Vermessung, OeV-Haltestellen).
- (c) OpenStreetMap contributors, ODbL 1.0. Files that contain OSM-derived features are a derived database under
  ODbL: `boarding_edges.geojson`, `station_features.geojson`, everything in `data/focus/`, the focus GLBs.
- (c) swisstopo (terrain heights).
