# city3d/ handoff: Bern 3D terrain, buildings, bridges and paths

Owner thread: Bern 3D City Basemap Data and Scene. Written 2026-11-21 ~02:15 Europe/Zurich.
Machine-readable provenance: `SOURCES.json` (217 inputs with url, publisher, licence, retrieved, bytes, sha256,
used_for) and `OUTPUTS.json` (every output with bytes, sha256, feature or tile counts).

## Coverage

| Area | Definition | What it has |
|---|---|---|
| **Box** | LV95 E 2589000–2606000, N 1194000–1205000 (17 × 11 km); WGS84 lon 7.29401–7.51751, lat 46.89702–46.99603 | terrain z8–15 (2 m), all buildings, TLM paths/roads/rail/bridges, OSM |
| **Municipality** | Bern, BFS 351, swissBOUNDARIES3D 2026 (E 2589008–2604334, N 1196443–1204344, 51.6 km²); lies fully inside the box | `in_municipality_bern` flag on buildings |
| **Central sample** | terrain: LV95 E 2599000–2602000, N 1198500–1201000; LOD2 GLB: E 2599600–2601800, N 1199100–1200400 (Bahnhof, Altstadt, Bundeshaus, Kirchenfeld/Kornhaus bridges, Nydegg, Bärengraben) | terrain z16–17 from 0.5 m; full LOD2 roofs and walls |

Known gap: buildings in a ≈ 380 m strip at the far west of the box (lon 7.2940–7.2990, sheets 1166-11/13/31/33, mostly
forest at Riedbach) were not downloaded. The municipality boundary reaches E 2589008, so a few farm buildings there
are missing.

## Datum, units, CRS (all outputs)

- Horizontal: GeoJSON is WGS84 (EPSG:4326) lon/lat with 7 decimals; LV95 (EPSG:2056) is kept as `lv95_e`/`lv95_n` where useful.
- Vertical: **LN02** metres above sea level for every height (swissALTI3D, swissBUILDINGS3D and swissTLM3D are all
  delivered as `_2056_5728` = LV95 + LN02). No ellipsoidal heights anywhere: GNSS/ellipsoidal heights in Bern are
  roughly 50 m higher and must be converted before comparing.
- GLB: local metric frame, origin LV95 E 2600700, N 1199750, LN02 H 500 (lon 7.4478274, lat 46.9488337).
  Axes: glTF +X = East, +Y = Up, +Z = South. Units metres. Meridian convergence and LV95 scale at Bern are
  negligible (< 1 m over the 2 km sample; the projection origin is in Bern).

## Outputs

| Path | Content | Count | Size |
|---|---|---|---|
| `data/terrain/{z}/{x}/{y}.webp` | MapLibre `raster-dem`, Mapbox Terrain-RGB encoding `h = -10000 + (R·65536 + G·256 + B)·0.1` m, lossless WebP, 256 px, XYZ | 725 tiles (z8 1, z9 1, z10 2, z11 4, z12 12, z13 28, z14 96, z15 330, z16 56, z17 195) | 14.6 MB |
| `data/buildings/bern_buildings_municipality.geojson` | footprint polygon per building, EGID, heights | 20,925 | 19.4 MB |
| `data/buildings/bern_buildings_ring.geojson` | same schema, buildings in the box outside the municipality | 26,021 | 22.8 MB |
| `data/buildings/central_lod2.glb` | triangulated LOD2 roofs (122,611 tris) + walls (228,671 tris), per-vertex `_BUILDING_INDEX` | 2,933 buildings | 21.1 MB |
| `data/buildings/central_lod2.meshopt.glb` | same mesh, gltfpack `-cc -vp 16`: EXT_meshopt_compression + KHR_mesh_quantization, positions quantized to ≈ 3.4 cm, vertices welded; **render only** (no `_BUILDING_INDEX`, no extras) | 2,933 buildings | 1.5 MB |
| `data/buildings/bern_buildings_extrude.geojson` | render copy of both building files: `h` height_m, `c` in GLB, `m` in municipality, `e` EGID; 6 dp | 46,946 | 16.1 MB (3.1 MB gzip) |
| `data/buildings/central_lod2.meta.json` | GLB origin/axes/units + table index → id, EGID, objektart, height | 2,933 rows | 0.5 MB |
| `data/network/tlm_paths_3d.geojson` | swissTLM3D 1m/2m Weg, stairs, squares, lifts; LineString Z | 13,297 | 14.6 MB |
| `data/network/tlm_roads_3d.geojson` | swissTLM3D roads + motorways; LineString Z | 17,031 | 16.4 MB |
| `data/network/tlm_rail_3d.geojson` | swissTLM3D rail (1,197) + tram (292) centrelines; LineString Z | 1,489 | 1.5 MB |
| `data/network/bridges_tlm.geojson` | bridge segments only (road, path, rail, tram), with deck heights and clearance | 632 | 0.6 MB |
| `data/network/bridges_deck_approx.geojson` | bridge decks as ≤ 10 m polygon pieces for `fill-extrusion` (**inferred**) | 3,854 | 2.8 MB |
| `data/network/osm_paths_bridges.geojson` | OSM footways (16,947), steps (2,891), paths, crossings, elevators (108), 808 bridge ways (**ODbL**) | 27,531 | 12.3 MB |
| `data/validation/edge_terrain_heights.json` | atlas edge height vs terrain, summary + outliers + all rows | 1,112 edges | 0.6 MB |
| `*_stats.json` | counts per build step | | |

Every file is < 25 MB; nothing needs to be excluded. Total committed data ≈ 145 MB (terrain 14.6, buildings 81.6,
network 48.3, validation 0.6). If that is too much for the repo, drop `bern_buildings_ring.geojson` and
`tlm_roads_3d.geojson` first; both rebuild from the cache in under two minutes.

### Building schema (`bern_buildings_*.geojson`)

`id` (`swissbuildings3d:<uuid>`), `egid` (federal building register, null for 4 % — walls, tanks, roofs without a
register entry), `objektart` (swisstopo class, e.g. `Gebaeude Einzelhaus`, `Hochhaus`, `Sakrales Gebaeude`,
`Offenes Gebaeude`, `Flugdach`), `terrain_point_z_m` (source `GELAENDEPUNKT`), `terrain_z_m` (swissALTI3D 2 m at the
footprint point), `ground_surface_z_m` (source GroundSurface — **not** ground level, see below), `roof_min_z_m`,
`roof_max_z_m` (`DACH_MIN`/`DACH_MAX`), `height_m` (roof_max minus `height_base`), `height_base`,
`footprint_area_m2`, `footprint_from` (`GroundSurface` or `RoofSurface projection`), `n_roof`, `n_wall`,
`capture_year`, `revision_year`, `lv95_e`, `lv95_n`, `in_municipality_bern`, `in_central_glb`, `sheet`, `source`,
`inferred`, `inferred_how`.

Checks done: Berner Münster `height_m` = 100.53 (published tower height 100.6 m). `GELAENDEPUNKT` minus
swissALTI3D: median +0.01 m, p5/p95 −0.71/+0.79 m (sheet 1166-42, 11,110 buildings).
**swissBUILDINGS3D 3.0 extends walls and GroundSurface about 3.4 m below the terrain** (median −3.37 m vs
`GELAENDEPUNKT`), so `ground_surface_z_m` must not be used as the ground. `height_m` uses `GELAENDEPUNKT` (19,638 of
20,925 in the municipality) or the DEM (1,287, flagged `inferred`).

### Network schema (`tlm_*_3d.geojson`, `bridges_tlm.geojson`)

Coordinates `[lon, lat, h_LN02]`. `id` (`swisstlm3d:<uuid>`), `tlm_layer`, `class` (`path`, `stairs`, `square`,
`lift`, `road`, `motorway`, `rail`, `tram`), `objektart`, `kunstbaute` (`Bruecke`, `Treppe`, `Tunnel`,
`Unterfuehrung`, `Steg`, …), `is_bridge`, `is_stairs`, `is_tunnel`, `stufe` (TLM level −2…4), `name`,
`strassenname`, `belagsart`, `wanderweg`, `befahrbarkeit`, `verkehrsbeschraenkung`, `verkehrsmittel`,
`standseilbahn`, `length_3d_m`, `z_min_m`, `z_max_m`, `above_terrain_min_m`/`above_terrain_max_m` (line Z minus
bare-earth DTM; under a bridge this is the clearance over ground or water), `width_nominal_m`, `width_inferred`,
`capture_year`, `revision_year`, `source`, `inferred`.
Checks done: Kirchenfeldbrücke deck 540–550 m, up to 47 m above the Aare; Kornhausbrücke and Lorrainebrücke
(rail) 33–36 m; Felsenauviadukt 60 m.

`bridges_deck_approx.geojson`: `bridge_id`, `deck_z_m`, `terrain_z_m`, `top_above_terrain_m`,
`base_above_terrain_m`, `width_m`, `inferred: true`. Outline = TLM centreline buffered to the nominal width (the
width comes from the TLM class name such as `6m Strasse`; for motorways and rail it is an estimate). Deck thickness
is assumed (1.5 m road/rail, 0.8 m path).

## Join with transit (boarding edges)

`data/validation/edge_terrain_heights.json`: diff = atlas `height_m` minus swissALTI3D 2 m bilinear at atlas
`lv95_e/lv95_n`, tolerance **±1.0 m**. 1,112 edges compared (585 bern, 523 ring, 4 connected):
**92.2 % within ±1 m**, 84 % within ±0.5 m, 96 % within ±2 m; median +0.09 m, median |diff| 0.16 m, p95 |diff| 1.71 m.
88 outliers: 13 are explained by structures (RBS underground station Bern tracks 21–24 at −23.5 m; bus edges
`Bern, Hauptbahnhof` R and Y, +9–10 m, where TLM has paths `in/auf Gebaeude` at stufe 2 above the station tracks;
Bern Europaplatz platforms 3 and 4, +6 m, under a roof and next to a TLM bridge with stairs at stufe 1; the
structure is inferred from proximity, not verified on site), and 65 of the 75 unexplained
outliers carry transit's `coord_rounded` flag (the atlas coordinate is rounded, so the DEM is sampled off-position
on a slope). Each outlier row has `explained` and `explanation`.

## Sources and rights

| Dataset | Edition used | Licence as stated |
|---|---|---|
| swissALTI3D 2 m (187 tiles) and 0.5 m (9 central tiles) | 2025 for every tile used | swisstopo OGD: free use, attribution `© swisstopo` (STAC field `proprietary`, terms https://www.swisstopo.admin.ch/en/terms-of-use-free-geodata-and-geoservices) |
| swissBUILDINGS3D 3.0 Beta, CityGML | 2021 edition, 16 LK25 sheets 1166-12…44, 1167-11…33; buildings captured 2021 | same |
| swissTLM3D | 2026-02 GeoPackage (`SWISSTLM3D_2026_LV95_LN02.gpkg`); Bern features revised 2024 | same |
| swissBOUNDARIES3D (via api3.geo.admin.ch) | 2026 | same |
| OpenStreetMap via overpass.osm.ch | retrieved 2026-11-21 | ODbL 1.0, `© OpenStreetMap contributors`; the OSM file is a derived database and stays ODbL |
| AWS Terrain Tiles (Tilezen, terrarium) | live | open, attribution per tilezen/joerd; only pads terrain pixels outside the box at z8–15 |

The swissBUILDINGS3D FileGDB of sheet 1166-42 was also downloaded but cannot be read with the GDAL in pip wheels
(TIN Z geometry, type 1016). The CityGML of the same sheet and edition was used instead.

### Hosted alternatives, checked but not used as data

- `https://3d.geo.admin.ch/ch.swisstopo.swissbuildings3d.3d/v1/tileset.json`: 3D Tiles 1.0, nested tilesets, `b3dm`
  leaves (version 20260520). Streams all of Switzerland with roofs, but needs CesiumJS or deck.gl `Tile3DLayer`.
  MapLibre cannot draw it natively.
- `https://3d.geo.admin.ch/ch.swisstopo.terrain.3d/v1/layer.json`: quantized-mesh 1.0, z0–18, Cesium only.
- `vectortiles.geo.admin.ch` `ch.swisstopo.base.vt` layer `building` has `render_height`/`render_min_height` to z14.
  The scene uses it for zero-download extrusions everywhere (flat roofs).

## Approximate or missing

- Bridge decks are approximate (`inferred: true`): nominal width, assumed thickness, no piers or arches. Deck height
  is real (TLM Z).
- OSM has no heights; `layer` is only stacking order.
- Terrain: z8–15 are resampled bilinearly from the 2 m grid. At z ≥ 16 outside the central box MapLibre overzooms
  z15 (≈ 3.3 m/px). Under bridges the DTM is the ground or river (bare earth, as intended).
- Building footprints are simplified at 5 cm. The GLB omits GroundSurface and normals (compute flat normals on load).
- No interiors, station levels or platform geometry: those belong to `stations/`. TLM `Perron` polygons (67 in the
  box) were left to that folder.

## Performance (measured headless Chrome, SwiftShader software GL, localhost)

- Map with terrain, streamed extrusions, paths, bridges and 3,217 edges: fully rendered within the 15–30 s wait used
  for the screenshots. Time to first render was not measured separately.
- `central_lod2.meshopt.glb` (default in the scene) is 1.5 MB and loads in 1.2–2.1 s; `central_lod2.glb` (21 MB,
  `?lod2=full`) in 2.6–4.2 s. 351 k triangles either way; `?lod2=0` drops it.
- `bern_buildings_extrude.geojson` (16 MB, 3.1 MB gzipped over HTTP) drives the extrusions for all 46,946 buildings;
  `?buildings=vt` uses swisstopo's streamed vector tiles instead (no download, flat roofs, overlaps the LOD2 sample).
- Terrain: one 256 px WebP per tile, ≈ 20 KB each; a typical city view fetches 20–40 tiles.
- The GeoJSONs (12–23 MB) are data deliverables, not for direct mobile display. For the app, build vector tiles
  (tippecanoe → PMTiles) from them; tippecanoe is not installed on this machine.

## Smallest repro / how to load

```
cd bern-research
python -m http.server 8000
# open http://localhost:8000/city3d/                (terrain + LOD2 + bridges + paths + transit edges)
#      http://localhost:8000/city3d/?lod2=0         (no GLB, lighter for phones)
#      http://localhost:8000/city3d/?lod2=full      (uncompressed GLB with the per-building index)
#      http://localhost:8000/city3d/?buildings=vt   (streamed swisstopo extrusions instead of bern_buildings_extrude)
#      http://localhost:8000/city3d/?edges=<any GeoJSON points URL>
```

`index.html` is a thin loader: MapLibre 4.7.1 (same as the team app), swisstopo light basemap, `raster-dem` terrain,
`fill-extrusion` (filter `c == 0` so the GLB buildings are not drawn twice), and a three.js 0.169 custom layer with
the meshopt decoder for the GLB. The custom layer subtracts
`map.transform.elevation` from the absolute LN02 origin, because MapLibre renders terrain relative to the elevation
of the camera centre. Verified visually: LOD2 roofs sit on the terrain and the Kirchenfeldbrücke deck floats above
the Aare.

## Integration into the team app (`index.html` at the repo root)

Not done here; the root app belongs to the team. Steps:

1. Copy (or serve) `bern-research/city3d/data/terrain/` next to the app.
2. After `map.on('load')`:
   ```js
   map.addSource('bern-dem', { type: 'raster-dem', tiles: [location.origin + '/<path>/terrain/{z}/{x}/{y}.webp'],
     tileSize: 256, encoding: 'mapbox', minzoom: 8, maxzoom: 17, bounds: [7.29401, 46.89702, 7.51751, 46.99603] });
   map.setTerrain({ source: 'bern-dem', exaggeration: 1 });
   map.addLayer({ id: 'bld3d', type: 'fill-extrusion', source: 'base_v1.0.0', 'source-layer': 'building', minzoom: 13,
     paint: { 'fill-extrusion-color': '#e7e2da', 'fill-extrusion-height': ['coalesce', ['get', 'render_height'], 6],
              'fill-extrusion-base': ['coalesce', ['get', 'render_min_height'], 0] } });
   ```
   The app derives its dark style from the light style; the source name `base_v1.0.0` is the same in both.
3. Allow pitch (`maxPitch: 80`) and add a pitch gesture/control. Markers are DOM markers and follow terrain
   automatically.
4. Optional: bridges via `bridges_deck_approx.geojson` (`fill-extrusion-base` / `-height` =
   `base_above_terrain_m` / `top_above_terrain_m`); LOD2 via the `lod2Layer()` function in `city3d/index.html`.
5. Attribution: `© swisstopo`, plus `© OpenStreetMap contributors` if the OSM layer is shown.

## Rebuild

Python 3.11 venv with `numpy rasterio pyproj pillow shapely pyogrio lxml mapbox_earcut` (pip wheels; no system GDAL).
Raw downloads go to `city3d/.cache/` (git-ignored, ≈ 16 GB including the unzipped 10.8 GB swissTLM3D GeoPackage).
URLs are in `SOURCES.json`; DEM URL lists are in `.cache/swissalti3d/urls_all.txt` and `.cache/swissalti3d_05/urls.txt`.

```
cd bern-research/city3d
python -I tools/fetch_sources.py .          # every SOURCES.json input -> .cache/ (sha256 checked), unzips TLM, boundary
python -I tools/fetch_osm.py .cache/osm/overpass_paths_bridges.json
python -I tools/make_terrain.py .cache/swissalti3d data/terrain .cache/terrarium .cache/swissalti3d_05     # ~1.5 min
python -I tools/make_buildings.py .cache/swissbuildings3d .cache/bern_boundary_lv95.geojson data/buildings .cache/work  # ~1.5 min
python -I tools/make_network.py .cache/swisstlm3d/SWISSTLM3D_2026_LV95_LN02.gpkg .cache/osm/overpass_paths_bridges.json .cache/swissalti3d data/network  # ~10 s
python -I tools/make_extrude.py data/buildings
npx gltfpack@0.21.0 -i data/buildings/central_lod2.glb -o data/buildings/central_lod2.meshopt.glb -cc -vp 16 -ke -kn -km
python -I tools/validate_edges.py ../transit/data/edges.geojson .cache/swissalti3d data/buildings data/network data/validation/edge_terrain_heights.json
python -I tools/make_manifest.py .
```

`fetch_sources.py` also writes `.cache/bern_boundary_lv95.geojson` from `.cache/bern_boundary_find.json` (feature
id `351`, year 2026). A fresh OSM fetch will differ from the committed file; the query is stored in the file header.
