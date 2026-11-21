# Validation report

Run 2026-11-21T02:03:40+01:00 on HEAD `930c519`, folders: transit, city3d, stations, references, lead.

**1 FAIL, 19 WARN, 40 OK**

## transit

- **WARN** no HANDOFF.md yet
- **WARN** transit/data/edges.geojson: 1381 of 3217 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/fp2026/lines.geojson: 762 of 3535 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/fp2026/segments.geojson: 4 vertices outside Switzerland (expected only for stations on through trips)
- **WARN** transit/data/fp2026/segments.geojson: 4700 of 11922 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/fp2027/lines.geojson: 705 of 3244 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/fp2027/segments.geojson: 2492 of 7494 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/stations.geojson: 2 vertices outside Switzerland (expected only for stations on through trips)
- **WARN** transit/data/stations.geojson: 355 of 1120 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** no source manifest (SOURCES.json / source.json / manifest.json) among committable files
- **OK** 34 files, 68.6 MB would be committed
- **OK** transit/data/edges.geojson: 3478 features, 3217 vertices, 7743 SLOID values
- **OK** transit/data/fp2026/lines.geojson: 266 features, 3535 vertices, 0 SLOID values
- **OK** transit/data/fp2026/segments.geojson: 5961 features, 11922 vertices, 22406 SLOID values
- **OK** transit/data/fp2027/lines.geojson: 220 features, 3244 vertices, 0 SLOID values
- **OK** transit/data/fp2027/segments.geojson: 3747 features, 7494 vertices, 13840 SLOID values
- **OK** transit/data/stations.geojson: 1120 features, 1120 vertices, 1116 SLOID values

## city3d

- **WARN** no HANDOFF.md yet
- **WARN** no source manifest (SOURCES.json / source.json / manifest.json) among committable files
- **OK** 552 files, 120.8 MB would be committed
- **OK** city3d/data/buildings/bern_buildings_municipality.geojson: 20925 features, 388367 vertices, 0 SLOID values
- **OK** city3d/data/buildings/bern_buildings_ring.geojson: 26021 features, 356844 vertices, 0 SLOID values
- **OK** city3d/data/network/bridges_deck_approx.geojson: 3854 features, 19270 vertices, 0 SLOID values
- **OK** city3d/data/network/bridges_tlm.geojson: 632 features, 2987 vertices, 0 SLOID values
- **OK** city3d/data/network/osm_paths_bridges.geojson: 27531 features, 172189 vertices, 0 SLOID values
- **OK** city3d/data/network/tlm_paths_3d.geojson: 13297 features, 152593 vertices, 0 SLOID values
- **OK** city3d/data/network/tlm_rail_3d.geojson: 1489 features, 14262 vertices, 0 SLOID values
- **OK** city3d/data/network/tlm_roads_3d.geojson: 17031 features, 112412 vertices, 0 SLOID values

## stations

- **WARN** no HANDOFF.md yet
- **WARN** no source manifest (SOURCES.json / source.json / manifest.json) among committable files
- **OK** 34 files, 8.0 MB would be committed
- **OK** stations/data/boarding_edges.geojson: 1083 features, 9566 vertices, 2260 SLOID values
- **OK** stations/data/focus/bern-bahnhof.geojson: 1188 features, 13577 vertices, 796 SLOID values
- **OK** stations/data/focus/wankdorf.geojson: 238 features, 1899 vertices, 202 SLOID values
- **OK** stations/data/focus/zytglogge.geojson: 346 features, 5824 vertices, 35 SLOID values
- **OK** stations/data/station_features.geojson: 697 features, 3738 vertices, 1327 SLOID values
- **OK** stations/data/stations.geojson: 436 features, 436 vertices, 436 SLOID values

## references

- **WARN** no source manifest (SOURCES.json / source.json / manifest.json) among committable files
- **OK** 89 files, 14.4 MB would be committed

## lead

- **OK** 6 files, 0.0 MB would be committed

## joins

- **FAIL** stations boarding_edges: 1083 features, 1 with an edge SLOID unknown to transit ([('ch:1:sloid:7081:0:640619', 'Bern Fischermätteli')])
- **WARN** transit stations: 4 stations have no SLOID (foreign stations on through trips: ['Berlin Ostbahnhof', 'Freiburg(Breisgau) Hbf', 'Domodossola (I)', 'Pontarlier'])
- **WARN** transit: of 205 tier-bern stations, 2 have no boarding edge and 23 have fewer than two
- **WARN** stations boarding_edges: 8 tier-bern boarding platforms from transit have no geometry feature in stations (e.g. ['ch:1:sloid:7082:0:833632', 'ch:1:sloid:7082:0:562230', 'ch:1:sloid:11982:0:1471'])
- **WARN** references stations.json: 359 stations, 1 not in transit stations (e.g. [8571420])
- **OK** transit: 3478 edges, 0 without a parent in stations.geojson
- **OK** transit: stations by tier {'connected': 529, 'bern': 205, 'ring': 386}; tier bern has 614 edges/areas, 34 without geometry, 145 with rounded coordinates, 373 without a public designation
- **OK** transit edge_lookup: 5221 references, 0 point at an edge that is not in edges.geojson
- **OK** transit stop map fp2026: 3415 GTFS stop ids, 0 with an unknown edge, 0 with an unknown station, 8 resolve to neither (foreign or unmatched)
- **OK** transit stop map fp2027: 3084 GTFS stop ids, 0 with an unknown edge, 0 with an unknown station, 4 resolve to neither (foreign or unmatched)
- **OK** focus 8507000 Bern (rail): 34 edges/areas in transit, 27 with coordinates
- **OK** focus 8576646 Bern, Bahnhof (tram/bus): 25 edges/areas in transit, 23 with coordinates
- **OK** focus 8507110 Bern, Zytglogge: 14 edges/areas in transit, 14 with coordinates
- **OK** focus 8516161 Bern Wankdorf (rail): 10 edges/areas in transit, 6 with coordinates
- **OK** focus 8588699 Bern, Wankdorf Center: 2 edges/areas in transit, 2 with coordinates
- **OK** stations boarding_edges: 0 lie more than 15 m from the atlas edge point, 0 more than 50 m
- **OK** stations stations.geojson: 436 stations, 0 not in transit stations
- **OK** stations focus/bern-bahnhof: 1188 features, 474 flagged inferred; passage 241, building_part 119, sector_board 116, sector_marker 98, boarding_edge 89, access_point 83, stairs_outline 71, building_footprint 53
- **OK** stations focus/zytglogge: 346 features, 58 flagged inferred; building_part 88, building_footprint 84, stairs_outline 64, access_point 35, passage 21, underpass_outline 20, boarding_edge 14, platform_surface 5
- **OK** stations focus/wankdorf: 238 features, 102 flagged inferred; sector_board 27, access_point 23, boarding_edge 22, sector_marker 19, shelter 17, passage 17, building_part 16, stairs 16
