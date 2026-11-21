"""Slim render file for fill-extrusion: every building in the box, 6 dp coordinates, minimal properties.

Usage: python -I make_extrude.py <buildings dir>
Writes <buildings dir>/bern_buildings_extrude.geojson with properties:
  h  = height_m (m above GELAENDEPUNKT / terrain; see the full files), c = 1 if the building is in central_lod2.glb,
  m  = 1 if inside Bern municipality, e = EGID (or null)
Geometry rounded to 6 decimals (~0.1 m). Use the full bern_buildings_*.geojson files for data work.
"""
import json, os, sys

d = sys.argv[1]
feats = []


def rnd(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], 6), round(c[1], 6)]
    return [rnd(x) for x in c]


for n in ("bern_buildings_municipality.geojson", "bern_buildings_ring.geojson"):
    for f in json.load(open(os.path.join(d, n), encoding="utf-8"))["features"]:
        p = f["properties"]
        feats.append({"type": "Feature", "properties": {"h": p["height_m"], "c": int(p["in_central_glb"]),
                                                        "m": int(p["in_municipality_bern"]), "e": p["egid"]},
                      "geometry": {"type": f["geometry"]["type"], "coordinates": rnd(f["geometry"]["coordinates"])}})
fc = {"type": "FeatureCollection", "name": "bern_buildings_extrude",
      "note": "Render-only slim copy of bern_buildings_municipality + _ring (swissBUILDINGS3D 3.0 2021, © swisstopo). "
              "h = height_m in metres above terrain point; c = in central_lod2.glb; m = in Bern municipality; e = EGID. "
              "WGS84, 6 decimals.", "features": feats}
out = os.path.join(d, "bern_buildings_extrude.geojson")
json.dump(fc, open(out, "w", encoding="utf-8"), separators=(",", ":"))
print(len(feats), os.path.getsize(out))
