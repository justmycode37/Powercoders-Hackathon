"""Re-download every input listed in SOURCES.json into .cache/ and check sha256; extract the Bern boundary.

Usage: python -I fetch_sources.py <city3d dir> [--skip-tlm]
Files already present with the right sha256 are skipped. The swissTLM3D zip (4.8 GB) is unzipped afterwards.
OSM is not re-downloaded here (it changes daily): run fetch_osm.py.
"""
import hashlib, json, os, sys, urllib.request, zipfile

root = sys.argv[1]
skip_tlm = "--skip-tlm" in sys.argv
src = json.load(open(os.path.join(root, "SOURCES.json"), encoding="utf-8"))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


for e in src["inputs"]:
    if "file" not in e or "overpass" in e["file"]:
        continue
    if skip_tlm and "swisstlm3d" in e["file"]:
        continue
    p = os.path.join(root, e["file"])
    if os.path.exists(p) and sha(p) == e["sha256"]:
        continue
    os.makedirs(os.path.dirname(p), exist_ok=True)
    print("get", e["url"])
    urllib.request.urlretrieve(e["url"], p)
    if sha(p) != e["sha256"]:
        print("  sha256 differs from manifest (source re-published?)", p)

for e in src["inputs"]:
    if e.get("name", "").startswith("AWS Terrain"):
        d = os.path.join(root, ".cache", "terrarium"); os.makedirs(d, exist_ok=True)
        for f in e["files"]:
            p = os.path.join(d, f)
            if not os.path.exists(p):
                z, x, y = f[:-4].split("_")
                urllib.request.urlretrieve(e["url"].format(z=z, x=x, y=y), p)

tlm = os.path.join(root, ".cache", "swisstlm3d")
if not skip_tlm and os.path.isdir(tlm):
    for z in os.listdir(tlm):
        if z.endswith(".gpkg.zip"):
            zf = zipfile.ZipFile(os.path.join(tlm, z))
            for n in zf.namelist():
                if not os.path.exists(os.path.join(tlm, n)):
                    print("unzip", n); zf.extract(n, tlm)

bf = os.path.join(root, ".cache", "bern_boundary_find.json")
d = json.load(open(bf, encoding="utf-8"))
r = [r for r in d["results"] if str(r["id"]) == "351"][0]  # id 351 = current year (2026)
json.dump({"type": "Feature", "properties": {**r["properties"], "crs": "EPSG:2056",
           "source": "swissBOUNDARIES3D via api3.geo.admin.ch find, layer ch.swisstopo.swissboundaries3d-gemeinde-flaeche.fill, id 351"},
           "geometry": r["geometry"]}, open(os.path.join(root, ".cache", "bern_boundary_lv95.geojson"), "w"))
print("ok")
