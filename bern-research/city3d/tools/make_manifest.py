"""Write SOURCES.json (inputs, with sha256) and OUTPUTS.json (derived files) for bern-research/city3d.

Usage: python -I make_manifest.py <city3d dir>
"""
import datetime, glob, hashlib, json, os, sys

root = sys.argv[1]
cache = os.path.join(root, ".cache")
SWISSTOPO_LIC = ("swisstopo Open Government Data: free use incl. commercial, source attribution required "
                 "('© swisstopo'). STAC licence field: 'proprietary'. Terms: "
                 "https://www.swisstopo.admin.ch/en/terms-of-use-free-geodata-and-geoservices")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def mtime(p):
    return datetime.datetime.fromtimestamp(os.path.getmtime(p)).astimezone().isoformat(timespec="seconds")


def entry(p, **kw):
    return {"file": os.path.relpath(p, root).replace("\\", "/"), "bytes": os.path.getsize(p), "sha256": sha(p),
            "retrieved": mtime(p), **kw}


inputs = []
for p in sorted(glob.glob(os.path.join(cache, "swissalti3d", "*.tif"))):
    b = os.path.basename(p); item = b.rsplit("_", 3)[0]
    inputs.append(entry(p, name=f"swissALTI3D 2 m tile {b.split('_')[2]} ({b.split('_')[1]})",
                        url=f"https://data.geo.admin.ch/ch.swisstopo.swissalti3d/{item}/{b}",
                        publisher="swisstopo", licence=SWISSTOPO_LIC,
                        crs="EPSG:2056 LV95 / LN02 heights, 2 m grid, float32 metres",
                        used_for="terrain tiles z8-15, building ground fallback, bridge clearance, edge validation"))
for p in sorted(glob.glob(os.path.join(cache, "swissalti3d_05", "*.tif"))):
    b = os.path.basename(p); item = b.rsplit("_", 3)[0]
    inputs.append(entry(p, name=f"swissALTI3D 0.5 m tile {b.split('_')[2]} ({b.split('_')[1]})",
                        url=f"https://data.geo.admin.ch/ch.swisstopo.swissalti3d/{item}/{b}",
                        publisher="swisstopo", licence=SWISSTOPO_LIC,
                        crs="EPSG:2056 LV95 / LN02 heights, 0.5 m grid, float32 metres",
                        used_for="terrain tiles z16-17 (central sample)"))
for p in sorted(glob.glob(os.path.join(cache, "swissbuildings3d", "*.zip"))):
    b = os.path.basename(p); item = b.rsplit("_", 2)[0]
    used = "not used: FileGDB TIN geometry unreadable with pip GDAL; CityGML of the same sheet used" if ".gdb." in b \
        else "buildings footprints + heights; central LOD2 GLB"
    inputs.append(entry(p, name=f"swissBUILDINGS3D 3.0 Beta sheet {b.split('_')[4]} edition {b.split('_')[3]}",
                        url=f"https://data.geo.admin.ch/ch.swisstopo.swissbuildings3d_3_0/{item}/{b}",
                        publisher="swisstopo", licence=SWISSTOPO_LIC,
                        crs="EPSG:2056 LV95 / LN02, CityGML 2.0 LOD2", used_for=used))
for p in sorted(glob.glob(os.path.join(cache, "swisstlm3d", "*.zip"))):
    b = os.path.basename(p)
    inputs.append(entry(p, name="swissTLM3D 2026-02 GeoPackage (whole Switzerland)",
                        url=f"https://data.geo.admin.ch/ch.swisstopo.swisstlm3d/swisstlm3d_2026-02/{b}",
                        publisher="swisstopo", licence=SWISSTOPO_LIC,
                        crs="EPSG:2056 LV95 / LN02, 3D lines", used_for="paths, stairs, roads, rail, bridges"))
p = os.path.join(cache, "osm", "overpass_paths_bridges.json")
if os.path.exists(p):
    d = json.load(open(p, encoding="utf-8"))
    inputs.append(entry(p, name="OpenStreetMap paths/bridges/elevators via Overpass", url=d.get("_mirror"),
                        query=d.get("_query"), osm3s=d.get("osm3s"), publisher="OpenStreetMap contributors",
                        licence="ODbL 1.0 (https://opendatacommons.org/licenses/odbl/), attribution "
                                "'© OpenStreetMap contributors'", crs="EPSG:4326",
                        used_for="network/osm_paths_bridges.geojson"))
p = os.path.join(cache, "bern_boundary_find.json")
if os.path.exists(p):
    inputs.append(entry(p, name="swissBOUNDARIES3D municipality Bern (BFS 351), all years",
                        url="https://api3.geo.admin.ch/rest/services/api/MapServer/find?layer=ch.swisstopo."
                            "swissboundaries3d-gemeinde-flaeche.fill&searchText=351&searchField=gde_nr&returnGeometry="
                            "true&geometryFormat=geojson&sr=2056&contains=false",
                        publisher="swisstopo", licence=SWISSTOPO_LIC, crs="EPSG:2056",
                        used_for="in_municipality_bern flag (feature id 351 = year 2026)"))
terr = sorted(glob.glob(os.path.join(cache, "terrarium", "*.png")))
if terr:
    inputs.append({"name": "AWS Terrain Tiles (Tilezen/Mapzen, terrarium encoding)",
                   "url": "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png",
                   "files": [os.path.basename(t) for t in terr], "bytes": sum(os.path.getsize(t) for t in terr),
                   "sha256": {os.path.basename(t): sha(t) for t in terr}, "retrieved": mtime(terr[0]),
                   "publisher": "Tilezen / Mapzen on AWS Open Data",
                   "licence": "open; attribution per https://github.com/tilezen/joerd/blob/master/docs/attribution.md",
                   "used_for": "padding of terrain tile pixels outside the swissALTI3D box only (z8-15 margins)"})

json.dump({"folder": "bern-research/city3d", "generated": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
           "inputs": inputs}, open(os.path.join(root, "SOURCES.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---- outputs ---------------------------------------------------------------
outs = []
for p in sorted(glob.glob(os.path.join(root, "data", "**", "*"), recursive=True)):
    if os.path.isdir(p) or os.sep + "terrain" + os.sep in p:
        continue
    e = {"file": os.path.relpath(p, root).replace("\\", "/"), "bytes": os.path.getsize(p), "sha256": sha(p)}
    if p.endswith(".geojson"):
        d = json.load(open(p, encoding="utf-8"))
        e["features"] = len(d["features"])
    outs.append(e)
tiles = sorted(glob.glob(os.path.join(root, "data", "terrain", "*", "*", "*.webp")))
h = hashlib.sha256()
per_z = {}
for t in tiles:
    rel = os.path.relpath(t, root).replace("\\", "/")
    h.update(rel.encode() + b"\0" + sha(t).encode() + b"\n")
    z = rel.split("/")[2]
    per_z.setdefault(z, [0, 0]); per_z[z][0] += 1; per_z[z][1] += os.path.getsize(t)
outs.append({"file": "data/terrain/{z}/{x}/{y}.webp", "tiles": len(tiles), "bytes": sum(v[1] for v in per_z.values()),
             "per_zoom": {z: {"tiles": v[0], "bytes": v[1]} for z, v in sorted(per_z.items(), key=lambda kv: int(kv[0]))},
             "sha256_of_listing": h.hexdigest(),
             "sha256_of_listing_how": "sha256 over lines '<relpath>\\0<sha256 of file>\\n' in sorted path order"})
json.dump({"folder": "bern-research/city3d", "outputs": outs}, open(os.path.join(root, "OUTPUTS.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(len(inputs), "inputs;", len(outs), "outputs;", len(tiles), "terrain tiles")
