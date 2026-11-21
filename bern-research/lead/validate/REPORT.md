# Validation report

Run 2026-11-21T02:19:46+01:00 on HEAD `2487027`, folders: transit, city3d, stations, references, lead.

**0 FAIL, 17 WARN, 103 OK**

## transit

- **WARN** transit/data/MANIFEST.json: 1 manifest entries, missing {'url': 1, 'licence': 1, 'retrieved': 1, 'sha256': 1}
- **WARN** transit/data/fp2026/lines.geojson: 762 of 3535 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/fp2026/segments.geojson: 4 vertices outside Switzerland (expected only for stations on through trips)
- **WARN** transit/data/fp2026/segments.geojson: 4700 of 11922 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/fp2027/lines.geojson: 705 of 3244 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/fp2027/segments.geojson: 2492 of 7494 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/sectors.geojson: 1540 of 1803 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/edges.geojson: 1381 of 3222 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **WARN** transit/data/stations.geojson: 2 vertices outside Switzerland (expected only for stations on through trips)
- **WARN** transit/data/stations.geojson: 355 of 1123 vertices outside the Bern box (7.2, 46.85, 7.7, 47.1)
- **OK** 47 files, 73.1 MB would be committed
- **OK** transit/SOURCES.json: 16 manifest entries, all with url, licence, date, checksum
- **OK** transit/data/fp2026/lines.geojson: 266 features, 3535 vertices, 0 SLOID values
- **OK** transit/data/fp2026/segments.geojson: 5961 features, 11922 vertices, 22406 SLOID values
- **OK** transit/data/fp2027/lines.geojson: 220 features, 3244 vertices, 0 SLOID values
- **OK** transit/data/fp2027/segments.geojson: 3747 features, 7494 vertices, 13840 SLOID values
- **OK** transit/data/sectors.geojson: 1803 features, 1803 vertices, 5409 SLOID values
- **OK** transit/data/edges.geojson: 3483 features, 3222 vertices, 7753 SLOID values
- **OK** transit/data/stations.geojson: 1123 features, 1123 vertices, 1119 SLOID values

## city3d

- **WARN** city3d/data/buildings/bern_buildings_extrude.geojson: 46946 of 46946 features have no `source`
- **WARN** city3d/data/buildings/bern_buildings_extrude.geojson: 46946 of 46946 features have no `inferred` flag
- **OK** 755 files, 138.4 MB would be committed
- **OK** city3d/SOURCES.json: 217 manifest entries, all with url, licence, date, checksum
- **OK** city3d/data/buildings/bern_buildings_extrude.geojson: 46946 features, 510421 vertices, 0 SLOID values
- **OK** city3d/data/buildings/bern_buildings_municipality.geojson: 20925 features, 248068 vertices, 0 SLOID values
- **OK** city3d/data/buildings/bern_buildings_ring.geojson: 26021 features, 262353 vertices, 0 SLOID values
- **OK** city3d/data/network/bridges_deck_approx.geojson: 3854 features, 19270 vertices, 0 SLOID values
- **OK** city3d/data/network/bridges_tlm.geojson: 632 features, 2987 vertices, 0 SLOID values
- **OK** city3d/data/network/osm_paths_bridges.geojson: 27531 features, 172189 vertices, 0 SLOID values
- **OK** city3d/data/network/tlm_paths_3d.geojson: 13297 features, 152593 vertices, 0 SLOID values
- **OK** city3d/data/network/tlm_rail_3d.geojson: 1489 features, 14262 vertices, 0 SLOID values
- **OK** city3d/data/network/tlm_roads_3d.geojson: 17031 features, 112412 vertices, 0 SLOID values

## stations

- **WARN** no HANDOFF.md yet
- **OK** 264 files, 16.2 MB would be committed
- **OK** stations/SOURCES.json: 89 manifest entries, all with url, licence, date, checksum
- **OK** stations/data/boarding_edges.geojson: 1095 features, 9747 vertices, 2286 SLOID values
- **OK** stations/data/focus/8504104-thoerishaus-station.geojson: 31 features, 453 vertices, 13 SLOID values
- **OK** stations/data/focus/8504105-niederwangen.geojson: 64 features, 537 vertices, 30 SLOID values
- **OK** stations/data/focus/8504106-bern-buempliz-sued.geojson: 77 features, 711 vertices, 26 SLOID values
- **OK** stations/data/focus/8504108-bern-europaplatz.geojson: 93 features, 1406 vertices, 30 SLOID values
- **OK** stations/data/focus/8504117-oberwangen.geojson: 28 features, 352 vertices, 10 SLOID values
- **OK** stations/data/focus/8504488-bern-riedbach.geojson: 23 features, 113 vertices, 12 SLOID values
- **OK** stations/data/focus/8504489-bern-buempliz-nord.geojson: 76 features, 716 vertices, 18 SLOID values
- **OK** stations/data/focus/8507002-ostermundigen.geojson: 34 features, 215 vertices, 24 SLOID values
- **OK** stations/data/focus/8507003-guemligen.geojson: 84 features, 640 vertices, 70 SLOID values
- **OK** stations/data/focus/8507050-bern-egghoelzli.geojson: 48 features, 650 vertices, 26 SLOID values
- **OK** stations/data/focus/8507060-bern-helvetiaplatz.geojson: 68 features, 669 vertices, 23 SLOID values
- **OK** stations/data/focus/8507061-bern-brunnadernstrasse.geojson: 67 features, 849 vertices, 22 SLOID values
- **OK** stations/data/focus/8507062-muri-bei-bern.geojson: 19 features, 149 vertices, 11 SLOID values
- **OK** stations/data/focus/8507067-deisswil.geojson: 21 features, 115 vertices, 8 SLOID values
- **OK** stations/data/focus/8507068-bolligen.geojson: 47 features, 284 vertices, 17 SLOID values
- **OK** stations/data/focus/8507069-ittigen-bei-bern.geojson: 47 features, 226 vertices, 16 SLOID values
- **OK** stations/data/focus/8507077-kehrsatz.geojson: 31 features, 299 vertices, 10 SLOID values
- **OK** stations/data/focus/8507078-wabern-bei-bern.geojson: 57 features, 304 vertices, 24 SLOID values
- **OK** stations/data/focus/8507079-bern-weissenbuehl.geojson: 51 features, 419 vertices, 20 SLOID values
- **OK** stations/data/focus/8507083-koeniz.geojson: 51 features, 341 vertices, 37 SLOID values
- **OK** stations/data/focus/8507084-moos.geojson: 17 features, 185 vertices, 7 SLOID values
- **OK** stations/data/focus/8507085-gasel.geojson: 14 features, 212 vertices, 9 SLOID values
- **OK** stations/data/focus/8507091-liebefeld.geojson: 24 features, 207 vertices, 19 SLOID values
- **OK** stations/data/focus/8507093-kehrsatz-nord.geojson: 21 features, 236 vertices, 8 SLOID values
- **OK** stations/data/focus/8507096-papiermuehle.geojson: 35 features, 297 vertices, 12 SLOID values
- **OK** stations/data/focus/8508051-bern-felsenau.geojson: 58 features, 735 vertices, 20 SLOID values
- **OK** stations/data/focus/8508052-bern-tiefenau.geojson: 105 features, 929 vertices, 10 SLOID values
- **OK** stations/data/focus/8508053-steinibach.geojson: 55 features, 196 vertices, 15 SLOID values
- **OK** stations/data/focus/8508054-worblaufen.geojson: 88 features, 389 vertices, 34 SLOID values
- **OK** stations/data/focus/8508055-unterzollikofen.geojson: 29 features, 106 vertices, 12 SLOID values
- **OK** stations/data/focus/8508070-oberzollikofen.geojson: 45 features, 140 vertices, 16 SLOID values
- **OK** stations/data/focus/8516154-bern-bruennen-westside.geojson: 65 features, 911 vertices, 16 SLOID values
- **OK** stations/data/focus/8571342-bern-inselplatz.geojson: 40 features, 572 vertices, 8 SLOID values
- **OK** stations/data/focus/8571393-bern-eigerplatz.geojson: 52 features, 783 vertices, 20 SLOID values
- **OK** stations/data/focus/8571412-liebefeld-hessstrasse.geojson: 35 features, 243 vertices, 16 SLOID values
- **OK** stations/data/focus/8571413-koeniz-bruehlplatz.geojson: 28 features, 234 vertices, 12 SLOID values
- **OK** stations/data/focus/8571436-bern-bachmaetteli.geojson: 47 features, 787 vertices, 12 SLOID values
- **OK** stations/data/focus/8576990-bern-guisanplatz-expo.geojson: 17 features, 153 vertices, 25 SLOID values
- **OK** stations/data/focus/8576999-bern-upd-waldau.geojson: 13 features, 91 vertices, 14 SLOID values
- **OK** stations/data/focus/8577002-ostermundigen-waldeck.geojson: 20 features, 133 vertices, 12 SLOID values
- **OK** stations/data/focus/8579896-bern-hirschengraben.geojson: 142 features, 2798 vertices, 103 SLOID values
- **OK** stations/data/focus/8579897-bern-kocherpark.geojson: 61 features, 610 vertices, 10 SLOID values
- **OK** stations/data/focus/8579898-bern-buempliz-unterfuehrung.geojson: 56 features, 451 vertices, 17 SLOID values
- **OK** stations/data/focus/8579900-bern-buempliz-post.geojson: 60 features, 844 vertices, 24 SLOID values
- **OK** stations/data/focus/8587479-bern-schosshalde.geojson: 44 features, 662 vertices, 10 SLOID values
- **OK** stations/data/focus/8588562-wabern-gurtenbahn.geojson: 33 features, 246 vertices, 10 SLOID values
- **OK** stations/data/focus/8588988-bern-aegertenstrasse.geojson: 44 features, 632 vertices, 14 SLOID values
- **OK** stations/data/focus/8588991-bern-breitfeld.geojson: 69 features, 758 vertices, 11 SLOID values
- **OK** stations/data/focus/8589003-bern-thunplatz.geojson: 21 features, 481 vertices, 14 SLOID values
- **OK** stations/data/focus/8589991-bern-monbijou.geojson: 48 features, 694 vertices, 16 SLOID values
- **OK** stations/data/focus/8589992-bern-sulgenau.geojson: 73 features, 944 vertices, 10 SLOID values
- **OK** stations/data/focus/8589993-bern-wander.geojson: 46 features, 678 vertices, 10 SLOID values
- **OK** stations/data/focus/8589996-spiegel-spiegel.geojson: 26 features, 123 vertices, 16 SLOID values
- **OK** stations/data/focus/8590014-bern-fischermaetteli.geojson: 57 features, 513 vertices, 18 SLOID values
- **OK** stations/data/focus/8590021-bern-viktoriaplatz.geojson: 51 features, 796 vertices, 16 SLOID values
- **OK** stations/data/focus/8590041-bern-loryplatz.geojson: 65 features, 430 vertices, 18 SLOID values
- **OK** stations/data/focus/bern-bahnhof.geojson: 1189 features, 13579 vertices, 798 SLOID values
- **OK** stations/data/focus/wankdorf.geojson: 238 features, 1899 vertices, 202 SLOID values
- **OK** stations/data/focus/zytglogge.geojson: 346 features, 5824 vertices, 35 SLOID values
- **OK** stations/data/station_features.geojson: 700 features, 3769 vertices, 1333 SLOID values
- **OK** stations/data/stations.geojson: 442 features, 442 vertices, 442 SLOID values

## references

- **WARN** no source manifest (SOURCES.json / source.json / manifest.json) among committable files
- **OK** 96 files, 28.7 MB would be committed

## lead

- **OK** 6 files, 0.0 MB would be committed

## joins

- **WARN** transit stations: 4 stations have no SLOID (foreign stations on through trips: ['Berlin Ostbahnhof', 'Freiburg(Breisgau) Hbf', 'Domodossola (I)', 'Pontarlier'])
- **WARN** transit: of 208 tier-bern stations, 2 have no boarding edge and 24 have fewer than two
- **WARN** references stations.json: 359 stations, 1 not in transit stations (e.g. [8571420])
- **OK** transit: 3483 edges, 0 without a parent in stations.geojson
- **OK** transit: stations by tier {'connected': 529, 'bern': 208, 'ring': 386}; tier bern has 619 edges/areas, 34 without geometry, 147 with rounded coordinates, 375 without a public designation
- **OK** transit edge_lookup: 5229 references, 0 point at an edge that is not in edges.geojson
- **OK** transit stop map fp2026: 3415 GTFS stop ids, 0 with an unknown edge, 0 with an unknown station, 8 resolve to neither (foreign or unmatched)
- **OK** transit stop map fp2027: 3084 GTFS stop ids, 0 with an unknown edge, 0 with an unknown station, 4 resolve to neither (foreign or unmatched)
- **OK** focus 8507000 Bern (rail): 34 edges/areas in transit, 27 with coordinates
- **OK** focus 8576646 Bern, Bahnhof (tram/bus): 25 edges/areas in transit, 23 with coordinates
- **OK** focus 8507110 Bern, Zytglogge: 14 edges/areas in transit, 14 with coordinates
- **OK** focus 8516161 Bern Wankdorf (rail): 10 edges/areas in transit, 6 with coordinates
- **OK** focus 8588699 Bern, Wankdorf Center: 2 edges/areas in transit, 2 with coordinates
- **OK** stations boarding_edges: 1095 features, 0 with an edge SLOID unknown to transit
- **OK** stations boarding_edges: 0 lie more than 15 m from the atlas edge point, 0 more than 50 m
- **OK** stations boarding_edges: 0 tier-bern boarding platforms from transit have no geometry feature in stations
- **OK** stations stations.geojson: 442 stations, 0 not in transit stations
- **OK** stations focus/bern-bahnhof: 1189 features, 485 flagged inferred; passage 241, building_part 119, sector_board 116, sector_marker 98, boarding_edge 90, access_point 83, stairs_outline 71, building_footprint 53
- **OK** stations focus/zytglogge: 346 features, 61 flagged inferred; building_part 88, building_footprint 84, stairs_outline 64, access_point 35, passage 21, underpass_outline 20, boarding_edge 14, platform_surface 5
- **OK** stations focus/wankdorf: 238 features, 122 flagged inferred; sector_board 27, access_point 23, boarding_edge 22, sector_marker 19, shelter 17, passage 17, building_part 16, stairs 16
