"""Compare atlas boarding-edge heights (transit/data/edges.geojson, LN02) with swissALTI3D 2 m terrain.

Usage:
  python -I validate_edges.py <edges.geojson> <swissalti3d dir> <buildings dir> <network dir> <out.json>

For every edge with LV95 coordinates and a height inside the DEM box: terrain = bilinear swissALTI3D at (lv95_e, lv95_n),
diff = height_m - terrain. Context flags explain outliers: inside a swissBUILDINGS3D footprint, within 15 m of a
swissTLM3D bridge / tunnel segment, or within 15 m of a rail line at stufe != 0.
"""
import json, os, sys
import numpy as np
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dem import Dem

TOL = 1.0  # metres
edges_p, alti, bdir, ndir, out = sys.argv[1:6]
dem = Dem(alti)
E = json.load(open(edges_p, encoding="utf-8"))["features"]

bld = []
for n in ("bern_buildings_municipality.geojson", "bern_buildings_ring.geojson"):
    for f in json.load(open(os.path.join(bdir, n), encoding="utf-8"))["features"]:
        bld.append((shape(f["geometry"]), f["properties"]))
btree = STRtree([g for g, _ in bld])

struct = []
for n in ("tlm_roads_3d.geojson", "tlm_paths_3d.geojson", "tlm_rail_3d.geojson"):
    for f in json.load(open(os.path.join(ndir, n), encoding="utf-8"))["features"]:
        p = f["properties"]
        if p["is_bridge"] or p["is_tunnel"] or (p.get("stufe") not in (None, "0")):
            struct.append((shape({"type": "LineString", "coordinates": [c[:2] for c in f["geometry"]["coordinates"]]}), p))
stree = STRtree([g for g, _ in struct])
DEG15 = 15 / 111000  # ~15 m in degrees latitude (lon scaled below)

rows = []
for f in E:
    p = f["properties"]
    if p.get("lv95_e") is None or p.get("height_m") is None or f.get("geometry") is None:
        continue
    t = float(dem.sample([p["lv95_e"]], [p["lv95_n"]])[0])
    if not np.isfinite(t):
        continue
    lon, lat = f["geometry"]["coordinates"][:2]
    pt = Point(lon, lat)
    inside = [bld[i][1] for i in btree.query(pt, predicate="within")] if True else []
    near = [struct[i][1] for i in stree.query(pt.buffer(DEG15 * 1.5))
            if struct[i][0].distance(pt) < DEG15 * 1.2]
    d = p["height_m"] - t
    rows.append({
        "sloid": p["sloid"], "station_sloid": p.get("station_sloid"), "station_name": p.get("station_name"),
        "designation": p.get("designation"), "tier": p.get("tier"), "type": p.get("type"),
        "lv95_e": p["lv95_e"], "lv95_n": p["lv95_n"], "atlas_height_m": p["height_m"],
        "terrain_m": round(t, 2), "diff_m": round(d, 2), "within_tolerance": abs(d) <= TOL,
        "dem_tile_year": dem.year_at(p["lv95_e"], p["lv95_n"]),
        "inside_building": [{"id": b["id"], "egid": b.get("egid"), "objektart": b.get("objektart")} for b in inside][:2],
        "near_structure": sorted({f"{s['class']}:{s['kunstbaute']}:stufe{s.get('stufe')}" for s in near})[:4],
        "coord_rounded": p.get("coord_rounded"),
    })

d = np.array([r["diff_m"] for r in rows])
ad = np.abs(d)
expl = lambda r: bool(r["inside_building"] or r["near_structure"])
out_rows = [r for r in rows if not r["within_tolerance"]]
for r in out_rows:
    r["explained"] = expl(r)
    r["explanation"] = ("near swissTLM3D tunnel/underpass or stufe<0 (below terrain)" if any(
        ":Tunnel" in x or ":Unterfuehrung" in x or "stufe-" in x for x in r["near_structure"]) and r["diff_m"] < 0
        else "inside building footprint or near bridge/raised structure" if expl(r)
        else "unexplained: check atlas height or coordinate")
summary = {
    "method": "diff = atlas height_m (LN02) - swissALTI3D 2 m bilinear terrain (LN02) at atlas lv95_e/lv95_n",
    "tolerance_m": TOL,
    "edges_compared": len(rows),
    "edges_by_tier": {t: sum(1 for r in rows if r["tier"] == t) for t in ("bern", "ring", "connected")},
    "within_tolerance": int((ad <= TOL).sum()),
    "share_within_tolerance": round(float((ad <= TOL).mean()), 4) if len(rows) else None,
    "within_0_5_m": int((ad <= 0.5).sum()), "within_2_m": int((ad <= 2).sum()),
    "median_diff_m": round(float(np.median(d)), 2), "mean_diff_m": round(float(d.mean()), 2),
    "median_abs_diff_m": round(float(np.median(ad)), 2), "p95_abs_diff_m": round(float(np.percentile(ad, 95)), 2),
    "outliers": len(out_rows),
    "outliers_explained_by_structure": sum(1 for r in out_rows if expl(r)),
    "outliers_unexplained": sum(1 for r in out_rows if not expl(r)),
    "outliers_unexplained_with_coord_rounded": sum(1 for r in out_rows if not expl(r) and r.get("coord_rounded")),
    "outliers_by_tier": {t: sum(1 for r in out_rows if r["tier"] == t) for t in ("bern", "ring", "connected")},
    "note": "swissALTI3D is bare-earth terrain: edges on bridges, in underground stations (e.g. RBS Bern) or on "
            "raised platforms differ by design. 'inside_building' and 'near_structure' flag such cases.",
}
res = {"summary": summary,
       "outliers": sorted(out_rows, key=lambda r: -abs(r["diff_m"])),
       "all": rows}
os.makedirs(os.path.dirname(out), exist_ok=True)
json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(summary, indent=1))
for r in res["outliers"][:25]:
    print(r["diff_m"], r["station_name"], r["designation"], r["sloid"], r["inside_building"][:1], r["near_structure"])
