# city3d/ status

Updated 2026-11-21 02:20 Europe/Zurich. Owner thread: Bern 3D City Basemap Data and Scene.
Full description, schemas, checks and rebuild steps: `HANDOFF.md`. Provenance: `SOURCES.json` (217 inputs, sha256)
and `OUTPUTS.json` (all outputs, sha256, counts).

Coverage box: LV95 E 2589000–2606000, N 1194000–1205000 (contains all of Bern, BFS 351). Central sample:
E 2599000–2602000 / N 1198500–1201000 (terrain z16–17, 0.5 m) and E 2599600–2601800 / N 1199100–1200400 (LOD2 GLB).
Heights LN02 metres everywhere; GeoJSON WGS84, 7 dp.

## Done — ready for the lead to validate and commit

| Path | Content | Count | Size |
|---|---|---|---|
| `.gitignore` | ignores `.cache/` and `__pycache__/` | | |
| `HANDOFF.md`, `STATUS.md`, `SOURCES.json`, `OUTPUTS.json` | docs and manifests | 217 inputs | 0.2 MB |
| `index.html` | thin sample loader (MapLibre 4.7.1 + three.js custom layer), serve `bern-research/` | | 13 KB |
| `tools/*.py` | `fetch_sources`, `fetch_osm`, `make_terrain`, `make_buildings`, `make_extrude`, `make_network`, `validate_edges`, `make_manifest`, `dem` | 9 files | |
| `data/terrain/` | Terrain-RGB WebP pyramid from swissALTI3D 2025 (2 m; 0.5 m at z16–17 centre) | 725 tiles | 14.6 MB |
| `data/buildings/bern_buildings_municipality.geojson` | swissBUILDINGS3D 3.0 (2021) footprints, EGID, LN02 heights | 20,925 | 19.4 MB |
| `data/buildings/bern_buildings_ring.geojson` | same, rest of the box | 26,021 | 22.8 MB |
| `data/buildings/central_lod2.glb` + `.meta.json` | LOD2 roofs and walls, central sample | 2,933 buildings, 351 k triangles | 21.1 MB + 0.5 MB |
| `data/buildings/central_lod2.meshopt.glb` | same, meshopt + quantized, render only (scene default) | 2,933 | 1.5 MB |
| `data/buildings/bern_buildings_extrude.geojson` | slim render copy for fill-extrusion (scene default) | 46,946 | 16.1 MB |
| `data/network/tlm_paths_3d.geojson` | swissTLM3D 2026-02 paths, stairs (1,134), squares, lifts, 3D | 13,297 | 14.6 MB |
| `data/network/tlm_roads_3d.geojson` | swissTLM3D roads, 3D | 17,031 | 16.4 MB |
| `data/network/tlm_rail_3d.geojson` | swissTLM3D rail and tram, 3D | 1,489 | 1.5 MB |
| `data/network/bridges_tlm.geojson` | bridge segments with deck height and clearance | 632 | 0.6 MB |
| `data/network/bridges_deck_approx.geojson` | deck polygons for rendering, `inferred: true` | 3,854 | 2.8 MB |
| `data/network/osm_paths_bridges.geojson` | OSM footways, steps, crossings, elevators, bridges (ODbL) | 27,531 | 12.3 MB |
| `data/validation/edge_terrain_heights.json` | atlas edge height vs terrain | 1,112 edges | 0.6 MB |
| `data/*/*_stats.json` | step counts | | |

No file is above 25 MB; nothing is excluded. Total ≈ 145 MB. Tile pyramid bounded at 725 files.
The 0-byte `data/terrain/12/2132/1442.webp` the lead saw was a file caught mid-write; the pyramid has since been
regenerated twice and `find data/terrain -type f -size 0` is empty.

## Join with transit

atlas edge `height_m` vs swissALTI3D at the edge: 1,112 edges, **92.2 % within ±1.0 m**, median diff +0.09 m,
p95 |diff| 1.71 m. 88 outliers listed with SLOID; 13 explained by structures (RBS underground −23.5 m etc.), and
65 of the remaining 75 have `coord_rounded` set in transit. Edges input: `../transit/data/edges.geojson` as of 02:09.

## In progress

- Nothing running.

## Blocked / not done

- swissBUILDINGS3D FileGDB unreadable with pip GDAL (TIN Z); CityGML used instead (same data).
- Buildings in a ≈ 380 m strip at the far west (sheets 1166-11/13/31/33) not downloaded; mostly forest.
- No vector tiles (tippecanoe not installed); GeoJSON only.
- The root team app is not modified; integration steps are in `HANDOFF.md`.
