# stations/ HANDOFF

Thread: Bern Station Geometry and 3D Models. State of 2026-11-21, 03:08 Europe/Zurich. Formats and schemas are in
[README.md](README.md); this file gives coverage, limits, findings, and how to rebuild and load.

## What is here

| Output | Path | Size |
|---|---|---|
| Boarding edges, citywide | `data/boarding_edges.geojson` | 1,105 features, 2.4 MB |
| Platform surfaces, shelters, sectors, kerb candidates | `data/station_features.geojson` | 1,238 features, 1.4 MB |
| Stations | `data/stations.geojson` | 446 features |
| Step-free access register | `data/accessibility.json` | 31 stations, 35 access points, 193 relations |
| Focus stations, by level | `data/focus/<slug>.geojson`, `.walk_graph.json`, `index.json` | 59 stations, 4,830 features, 11.9 MB (5.6 MB of it walk graphs) |
| 3D models | `models/<slug>.glb` + `.model.json` | 59 models, 2.7 MB of GLB, 124,164 triangles |
| Fallback | `models/archetypes/*.glb`, `data/edge_placements.json` | 4 pieces, 1,073 placements |
| Provenance | `SOURCES.json`, `references.json` | 90 inputs, 5 plans |
| Checks | `validation/report.md`, `report.json` | 0 FAIL, 49 WARN, 767 OK |

Study area: LV95 E 2591500-2605800, N 1194000-1205200 (the city of Bern and the inner ring). All 598 `bern` tier
boarding edges of the transit folder and all 503 `ring` tier edges that fall in this box are present (checked
against `transit/data/edges.geojson` at 02:45); the `connected` tier (stations elsewhere in Switzerland) is not
covered.

## Coverage

**Boarding edges (1,105).** Every edge carries its atlas edge SLOID, station SLOID and number.

| Geometry | Edges | How good |
|---|---|---|
| Surveyed line, SBB kerb points | 63 | 1 m point spacing in LV95; median 0.25 m from the atlas point; agrees with OSM platform outlines at a median of 0.17 m |
| Surveyed platform outline, Stadt Bern cadastral survey | 3 | Bern track 3 and Bern Stoeckacker 1 and 2, where SBB has no kerb points |
| OSM platform line or polygon side | 511 | community data; median 2.1 m, 95 % within 6.8 m, all within 15 m of the atlas point. 221 of them are confirmed by a surveyed pavement boundary within a mean of 1 m. A tram or bus edge never takes a railway platform, and a platform line contested by two different edges goes to the nearer one (28 such claims resolved) |
| Constructed straight line | 496 | approximate: passes through the atlas point, bearing from atlas or the nearest road/track; length is nominal (42 m tram, 18 m bus) unless atlas gives one |
| Point only | 9 | atlas coordinate, no bearing derivable |
| No geometry | 23 | atlas publishes no coordinate (`geometry: null`); none could be matched to a Stadt Bern kerb by label, each says why in `no_geometry_reason` |

Also on the edges: platform side for 1,055 (for tram and bus edges with an atlas direction of travel it is the
right-hand side of that direction, 731 of 749 consistent; the other 18 follow their OSM platform polygon); atlas accessibility attributes (`prm`) for 1,049; official step-free
access from named station entrances (`step_free_access`) for 92 rail edges; lines served (`lines_at_kerb`, Stadt Bern
kerb layer) for 662 (60 paired by station number and kerb letter, 602 by position: the city kerb nearest to the
edge line within 6 m, mutual). Only 356 edges have a public letter or track number in atlas at all. 20 edges are not in the
atlas "actual date" file this folder downloaded (other validity dates); their rows come from the transit folder and
say so in `atlas_record_origin`.

**Station features (1,238).** 219 platform polygons (216 OSM, 37 of those confirmed by an SBB kerb line along their
boundary; 3 surveyed), 240 shelters (140 surveyed footprints from the cadastral survey, 100 from OSM), 126 atlas
sector markers, 152 SBB sector boards, 103 derived sector spans (Bern and Bern Wankdorf), 398
surveyed kerb candidates (pavement or traffic-island boundaries next to tram/bus edges in the city of Bern).

**Focus stations (59).** Three priority stations and 56 picked by rule: every further atlas rail station in the box
(28) and every tram/bus stop with at least four lettered kerbs (28).

| Station | Features | Levels | Notes |
|---|---|---|---|
| Bern Bahnhof (`bern-bahnhof`) | 1,328 | -2 to 5 | SBB tracks 1, 2, 5-10, 12, 13, 49, 50 from SBB kerb points; track 3 from the cadastral platform outline; track 4 from OSM (SBB publishes only part of it); RBS tracks 21-24 on level -2 (OSM); kerbs A-N, Q, Z, K1, K2; PostAuto kerbs R-W on level 2 (X and Y have no OSM platform: constructed lines, level is the assumed 0); 241 passages, 53 stairs, 30 escalators, 48 lifts, 12 entrances, 83 access points, 84 sector spans, 13 surveyed underground outlines; walk graph 1,659 nodes |
| Bern, Zytglogge (`zytglogge`) | 352 | -1 to 1 | kerbs A-H and K; no rail, no lifts; mostly old-town context (surveyed building and arcade outlines); walk graph 347 nodes |
| Bern Wankdorf (`wankdorf`) | 268 | -1 to 1 | tracks 1-3, 5-7 from SBB kerb points; tram/bus kerbs A-D and E-G; 9 lifts, 16 stairs; walk graph 474 nodes |
| 56 rule-based stations | 2,882 | mostly 0 or -1/0 | same structure; outside the city there is no cadastral data, so OSM plus atlas only |

Across all 59: 450 passages, 246 stairs, 33 escalators, 11 ramps, 77 lifts, 23 entrances, 492 access points, 99
surveyed underground structures, 47 underpass outlines, 232 stair outlines, 499 building footprints, 916 OSM building
parts. By geometry quality: 1,442 surveyed (302 of them are stretches selected along a surveyed line: sector spans
and kerb candidates), 395 official points, 2,852 community, 130 approximate, 11 missing.
Confirmed by a second independent source: 104 passages (inside a surveyed underground or underpass outline), 81
stairs and 18 escalators (at a surveyed stair outline), 11 entrances (on a surveyed building outline), 43 platforms.
Walk graphs: 11,520 nodes and 13,971 edges in total.

## What is approximate or missing

Every item below is labelled on the feature, not only here.

- **Levels come from OSM.** Of the vertical connectors, 46 stairs, 31 escalators and 50 lifts have an OSM level tag;
  174 stairs, 2 escalators and 27 lifts have none (mostly at small stations) and carry `level_note`. 128 passages and
  26 stairs have an inferred level (`level_source: inferred`): tunnels with a negative OSM layer are put on level -1.
- **Level elevations.** Of the 114 station levels, 62 take their elevation from atlas edge heights, 5 from measured
  swissTLM3D footpath heights (read from the city3d folder) and 47 are nominal (4.5 m per level,
  `elevation_quality: approximate`). Bern Bahnhof: level -2 = 517.0 m and level 0 = 540.8 m (atlas), level 1 =
  547.8 m (Welle and Schanzenstrasse, 194 height samples) and level 2 = 549.1 m (PostAuto deck, 83 samples) from
  swissTLM3D; levels -1, 3, 4, 5 are nominal. No open source gives the floor height of the station underpasses.
- **Dimensions.** Passage widths, clear heights, stair widths, shelter and canopy heights are not measured anywhere in
  the open data: widths are `missing` unless OSM has a width tag, shelter height is a nominal 3.0 m. Building heights
  are in the city3d folder (swissBUILDINGS3D); here they come from OSM tags and are missing for 587 of 916 parts.
- **Underground outlines have no storey.** The cadastral survey gives the surveyed outline of underground buildings,
  underpasses and stairs but not their level (`level: null`).
- **Entrances.** Only 23 OSM entrance nodes qualify as station entrances. The 492 `access_point` features are derived
  from topology (where a tunnel, indoor or stair way meets an open-air way) and are `inferred: true`. The 35 official
  atlas access points (`data/accessibility.json`) have names and step-free information but no coordinates.
- **Kerb candidates are candidates.** The cadastral survey does not say which pavement boundary is the boarding
  kerb. Use `mean_offset_m` and `offset_direction`; the main edge geometry is never replaced by them.
- **SBB plans not checked.** The SBB station plans answer HTTP 403 to scripts, so names of SBB passages and entrances
  are OSM names without a plan check. BERNMOBIL kerb plans were read (see `references.json`).
- **Constructed edges.** 496 edges are straight nominal-length lines. Their position is the atlas point; their
  length and exact alignment are not measured (115 of them have a surveyed kerb candidate nearby). 24 of them are
  constructed because the only OSM platform nearby belongs to a nearer edge (`osm_platforms_left_to_a_nearer_edge`).
- **3D models** are diagrammatic: flat-coloured slabs, ribbons and boxes on nominal level heights. Each sidecar lists
  what was drawn with a nominal dimension (`approximations`) and what was left out (`skipped`: 174 stairs, 55
  passages, 27 lifts without a level; 587 building parts without a height).
- **Walk graph** is OSM topology with levels, plus road centrelines (`kind: street`) where OSM maps no separate
  pavement. Not tested in a router. Share of nodes in the largest connected component: Bern Bahnhof 99 %, Zytglogge
  100 %, Wankdorf 96 %; median over the 59 stations 98 %; 7 stations are below 90 % (lowest: Oberzollikofen 49 %).
  Crossing a road is only modelled where OSM has a footway across it.
- **RBS, BLS and bus operators** publish no kerb survey; only SBB infrastructure has surveyed kerb points.

## Stadt Bern kerb points as a second official position source (lead request of 03:05)

The city layer has 873 kerb points at 422 stops. Only 58 of them carry a kerb letter (at the 12 stops with lettered
kerbs); none carries a number. Full lists are in `data/build-report.json` under `city_kerb_check`; the code is
`tools/city_kerbs.py`.

**1. Edges without atlas coordinates: 0 of 23 filled.** The rule was: exactly one city kerb of the same stop carries
the edge's `designation` or `designation_operational`. It matches nowhere:
- 20 edges: the stop's city kerbs (1 to 4 of them) carry no letter and no number, and the edge has only an
  operational number, so there is no label to match. This includes Ostermundigen Rueti, the only one of the 23 with a
  public letter (B): its single city kerb is unlettered.
- 3 edges (Bern Bahnhof operational 66 and 80, Thunplatz operational 12): the city kerbs are lettered, the edges
  have no letter.
All 23 stay `geometry: null` and now say why in `no_geometry_reason`. One of them, `ch:1:sloid:82210:0:618032` (Bern,
Untermattweg, operational 02), carries a `city_kerb_candidate` property: it is the stop's only edge without a
coordinate and the city has exactly one kerb there that no located edge is nearest to. That is elimination, not a
label match, so it is a property and not geometry.

**2. City kerb letters added: 0.** Only 7 located edges without a public letter are at stops where the city has
letters (4 at Zytglogge, 3 at Bern Bahnhof, all operational extras). Their nearest lettered city kerb is 25 to 141 m
away, far beyond "a few metres" (limit used: 6 m, mutual nearest). atlas `designation` is untouched everywhere.

**3. Independent accuracy check of the atlas coordinates.**

| Pairing | Pairs | atlas point to city kerb point | city kerb point to my edge line |
|---|---|---|---|
| same station number and kerb letter (independent of position) | 60 | median 10.2 m, p75 16.5, p90 20.7, p95 23.3, max 34.3 m; 8 within 5 m, 30 within 10 m, 54 within 20 m | median 1.2 m, p90 4.4, max 21.2 m |
| by position: city kerb nearest to the edge line (at most 6 m), and the edge is that kerb's nearest edge | 602 | median 7.1 m, p75 11.3, p90 16.4, p95 21.5, max 42.2 m | median 1.8 m, p90 4.7, max 11.1 m (bounded by the rule) |

Reading: atlas and the city agree on which kerb is which, but their points usually mark different places along the
same kerb, about 10 m apart. The city points lie on the edge lines of this folder (1.2 m median), which is an
independent confirmation of those lines. So an atlas coordinate is good for "which kerb", not for "where along it".

Worst ten of the letter pairs (atlas point to city kerb point, then city kerb point to edge line):

| Stop | Kerb | atlas to city | city to edge line | Edge |
|---|---|---|---|---|
| Bern, Viktoriaplatz | B | 34.3 m | 4.4 m | `ch:1:sloid:90021:0:1` |
| Bern, Bahnhof | E | 25.6 m | 0.8 m | `ch:1:sloid:76646:0:1427` |
| Bern, Buempliz Unterfuehrung | D | 23.3 m | 0.2 m | `ch:1:sloid:79898:0:15` |
| Bern, Bahnhof | E | 23.2 m | 0.8 m | `ch:1:sloid:76646:0:13` |
| Bern, Bahnhof | C | 21.7 m | 1.2 m | `ch:1:sloid:76646:0:3` |
| Bern, Bahnhof | G | 20.7 m | 5.2 m | `ch:1:sloid:76646:0:28` |
| Bern, Hirschengraben | C | 19.4 m | 1.2 m | `ch:1:sloid:79896:0:4` |
| Bern, Bahnhof | B | 19.2 m | 1.3 m | `ch:1:sloid:76646:0:1` |
| Bern, Buempliz Unterfuehrung | B | 18.8 m | 0.5 m | `ch:1:sloid:79898:0:17` |
| Bern, Zytglogge | F | 18.2 m | 0.2 m | `ch:1:sloid:7110:0:1` |

Worst of the position pairs: Bern Kursaal 42.2 m, Guemligen Hofgut 35.9 m, Bern Wankdorf Center 35.3 m, Bern Hasler
31.3 m, Bern Helvetiaplatz 31.1 m (each with the city point within 2.1 m of the edge line).
261 located edges at stops the city layer knows stay unpaired (no city kerb within the limit, or the nearest kerb
belongs to another edge); 72 of them are more than 40 m from any city kerb of their stop.

**Letter disagreements: none.** No atlas-lettered edge has another lettered city kerb more than 5 m nearer than its
own letter. Naming differences only:
- Bern, Bahnhof: atlas `K1` is the city's `K` (2.6 m). Letters only in atlas: K2, N, Q, Z.
- Letters only in atlas elsewhere: Zytglogge K; Bern Hauptbahnhof (PostAuto) R, W, X, Y (the city has S, T, U, V);
  Hirschengraben N; Wankdorf Bahnhof B; Wankdorf Bahnhof Nord G. No letter exists only in the city layer.

**Side effect, a correction.** `lines_at_kerb` (lines and destinations per kerb) used to come from the city kerb
nearest to the atlas point within 12 m. Because atlas and city points sit about 10 m apart along a kerb, that rule
had picked the kerb across the street for 18 edges (for example Bern Pestalozzi and Inselspital, where the two
directions were swapped). It is replaced by the position pairing above. `lines_at_kerb` is now on 662 edges (60 by
letter, 602 by position; before: 470), each with the pairing in `verified_against`.

## Findings worth acting on

1. **atlas coordinates on the wrong track.** Bern Wankdorf tracks 2, 3, 5, 7 and Bern `ch:1:sloid:7000:6:32` have an
   atlas coordinate that lies on a neighbouring track (offsets 7.9, 10.0, 85.5, 14.4, 10.1 m). SBB kerb points, SBB
   sector boards, OSM and atlas's own platform grouping agree with each other. The geometry follows the track number;
   the features carry `atlas_position_conflict`. An app that snaps to the raw atlas coordinate would send passengers
   for Wankdorf track 5 to the island of tracks 2/3.
2. **atlas heights are not always platform heights.** The PostAuto deck edges at Bern Bahnhof carry 540.0 m (track
   level) although swissTLM3D measures the deck at 549.1 m; RBS edges carry 517.0 m, which is plausible.
3. **Stated tolerance for the cross-folder test:** edge geometry lies within 15 m of the atlas edge point unless the
   feature carries `atlas_position_conflict` (5 edges, one of them 85.5 m). 50 edges are more than 5 m away; they
   are listed in `validation/report.json`.
4. **OSM platform geometry in the city is good.** For 283 OSM-based edges the cadastral survey has a pavement
   boundary alongside; the mean offset is 0.58 m in the median and under 1.6 m for 90 %.
5. Sector data: SBB boards stand at sector boundaries and show the sector on each side; atlas sector points sit at
   the same places. `sector_span` uses that to give the stretch of each sector.
6. SBB publishes no kerb points for Bern track 3 and only 179 m of track 4.
7. **atlas points and Stadt Bern kerb points mark different places along a kerb**, about 10 m apart in the median
   (60 pairs matched by letter). Both identify the same kerb; neither is a reliable position along it.

## How to rebuild

Python 3.11, standard library only, network needed for the first step and for terrain heights. From
`bern-research/stations/`:

```
python tools/fetch_sources.py      # atlas, SBB, Stadt Bern, OSM into .cache/ ; rewrites SOURCES.json
python tools/build_geometry.py     # citywide edges, station features, accessibility (reads ../transit/data/edges.geojson if present)
python tools/build_focus.py        # 59 focus stations (fetches terrain heights; --no-network uses the cache; reads ../city3d swissTLM3D paths if present)
python tools/build_models.py       # GLBs, archetypes, edge_placements.json
python tools/validate.py           # validation/report.md ; exit code 1 on FAIL
```

A full run takes a few minutes, mostly downloads; the three build steps plus validation take under a minute.
`python tools/build_models.py --all` writes a fallback GLB for each of the 440-odd stations with edges into
`.cache/models/` (about 4 MB, under a second, not committed). To add a focus station by hand, add it to `PRIORITY`
in `tools/common.py`; the rule for tier 2 is in `focus_areas()`.

## How to load

GeoJSON in MapLibre (the team app's library):

```js
map.addSource('edges', { type: 'geojson', data: 'bern-research/stations/data/boarding_edges.geojson' });
map.addLayer({ id: 'edges', type: 'line', source: 'edges',
  paint: { 'line-width': 3, 'line-color': ['match', ['get', 'geometry_quality'],
    'surveyed', '#0a7', 'community', '#27c', 'approximate', '#e80', '#999'] } });

// one level of a focus station
map.addSource('bhf', { type: 'geojson', data: 'bern-research/stations/data/focus/bern-bahnhof.geojson' });
map.addLayer({ id: 'bhf-passages', type: 'line', source: 'bhf',
  filter: ['all', ['==', ['get', 'feature_type'], 'passage'], ['==', ['get', 'level'], -1]] });
```

Features that span levels (`stairs`, `escalator`, `lift`, `ramp_or_link`) have `levels` (array) and, where resolved,
`from_level` and `to_level`; filter with `['in', -1, ['get', 'levels']]`.

GLB: any glTF 2.0 loader. Frame: metres, +Y up, +X east, +Z south, origin in `asset.extras.frame` and in the
sidecar. To place a model in a local scene whose origin is LV95 (E0, N0, H0): translate by
`(origin_lv95_e - E0, origin_height_m - H0, -(origin_lv95_n - N0))`. Node names are `<feature_type>@<level>`.

Stops without a focus model: for each row of `data/edge_placements.json` load
`models/archetypes/<archetype>.glb`, set position from `lon`, `lat`, `height_m`, rotate about +Y by
`rotation_y_deg`, scale X by `scale_x`.

Joins: `station_number` (string) and `station_sloid` to the transit stations; `edge_sloid` (= feature `id` in
`boarding_edges.geojson`) to the transit edges; reference images in `bern-research/references/` by station number.

## Licences

Per feature in `licence`; per input in `SOURCES.json`. In short: atlas (opentransportdata.swiss terms, name the
source), SBB open data (name the source), Geoinformation Stadt Bern (opendata.swiss terms_open), OpenStreetMap (ODbL
1.0: files with OSM-derived features are a derived database and must stay under ODbL with attribution), swisstopo
(terrain heights, name the source). Archetype GLBs are CC0. No operator plan or photo is in this folder; the plans
used for checks are linked in `references.json`.

## Not done

- Named SBB passages and entrances against the SBB station plan (needs a browser, see above).
- Surveyed geometry for RBS and BLS platforms and a decision, kerb by kerb, on which cadastral pavement boundary is
  the boarding kerb. A request to BERNMOBIL or the Stadt Bern Tiefbauamt for kerb lines would close the largest gap
  (496 constructed edges).
- Roof and floor heights of station structures from swissBUILDINGS3D (available in the city3d folder, not joined).
- A routing test of the walk graphs.
