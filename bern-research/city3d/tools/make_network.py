"""swissTLM3D (3D lines, LV95/LN02) + OSM (ODbL) -> Bern paths, stairs, bridges.

Usage:
  python -I make_network.py <SWISSTLM3D_*.gpkg> <overpass.json> <swissalti3d dir> <out dir>

Outputs (out dir):
  tlm_paths_3d.geojson         swissTLM3D paths (1m/2m Weg), stairs, squares, lifts; LineString Z (lon, lat, LN02 m)
  tlm_roads_3d.geojson         swissTLM3D roads and motorways, same schema
  tlm_rail_3d.geojson          swissTLM3D rail and tram centrelines, same schema
                               all with kunstbaute (bridge/stairs/tunnel...), stufe, nominal width
  bridges_tlm.geojson          bridge segments only, with deck height and clearance above swissALTI3D terrain
  bridges_deck_approx.geojson  bridge decks as ~10 m polygon pieces (line buffered by nominal width), with
                               base/top above terrain for fill-extrusion; inferred: true
  osm_paths_bridges.geojson    OSM footways/paths/steps/crossings/bridges/elevators (ODbL)
"""
import json, math, os, re, sys
import numpy as np
import pyogrio
from pyproj import Transformer
from shapely.geometry import LineString, mapping
from shapely import wkb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dem import Dem

BOX = (2589000, 1194000, 2606000, 1205000)
gpkg, overpass, alti, out = sys.argv[1:5]
os.makedirs(out, exist_ok=True)
dem = Dem(alti)
tr = Transformer.from_crs("EPSG:2056", "EPSG:4326", always_xy=True)
TLM_SRC = "swissTLM3D 2026-02 (swisstopo), file SWISSTLM3D_2026_LV95_LN02.gpkg"
LIC_TLM = "swisstopo OGD, attribution '© swisstopo'"
BRIDGE = {"Bruecke", "Bruecke mit Treppe", "Gedeckte Bruecke", "Steg"}
STAIRS = {"Treppe", "Bruecke mit Treppe", "Unterfuehrung mit Treppe"}
TUNNEL = {"Tunnel", "Unterfuehrung", "Unterfuehrung mit Treppe", "Galerie"}

# nominal width per swissTLM3D objektart (class names encode the width class); others are estimates
WIDTH = {"Autobahn": 12.0, "Autostrasse": 10.0, "Ausfahrt": 5.0, "Einfahrt": 5.0, "Zufahrt": 4.0,
         "Dienstzufahrt": 4.0, "Verbindung": 4.0, "Platz": 6.0, "Raststaette": 6.0,
         "Normalspur": 4.5, "Schmalspur": 3.5, "Schmalspur mit Normalspur": 4.5, "Lift": 2.0}


def nominal_width(oa):
    m = re.match(r"^(\d+)m ", oa or "")
    if m:
        return float(m.group(1)), "swissTLM3D width class in objektart"
    if oa in WIDTH:
        return WIDTH[oa], "estimate per objektart (not in source)"
    return 3.0, "default estimate (not in source)"


def to_wgs_coords(c):
    lon, lat = tr.transform(c[:, 0], c[:, 1])
    return [[round(float(a), 7), round(float(b), 7), round(float(h), 2)] for a, b, h in zip(lon, lat, c[:, 2])]


def read(layer):
    meta, fids, geoms, fields = pyogrio.raw.read(gpkg, layer=layer, bbox=BOX)
    names = meta["fields"]
    rows = []
    for i in range(len(geoms)):
        rec = {}
        for j, n in enumerate(names):
            v = fields[j][i]
            if isinstance(v, (np.floating,)) and np.isnan(v):
                v = None
            elif isinstance(v, np.generic):
                v = v.item()
            if hasattr(v, "isoformat"):
                v = str(v)
            if isinstance(v, str) and v == "NaT":
                v = None
            rec[n] = v
        rows.append((rec, wkb.loads(bytes(geoms[i]))))
    return rows


feats, bridges, decks = [], [], []
stats = {}
for layer, kind in (("tlm_strassen_strasse", "road_or_path"), ("tlm_oev_eisenbahn", "rail"),
                    ("tlm_oev_uebrige_bahn", "other_rail")):
    rows = read(layer)
    stats[layer] = len(rows)
    for rec, g in rows:
        geoms = list(getattr(g, "geoms", [g]))
        for gi, line in enumerate(geoms):
            c = np.asarray(line.coords)
            if c.shape[1] < 3 or len(c) < 2:
                continue
            terr = dem.sample(c[:, 0], c[:, 1])
            above = c[:, 2] - terr
            oa = rec.get("objektart")
            kb = rec.get("kunstbaute") or "Keine"
            w, w_how = nominal_width(oa)
            seg2d = np.hypot(np.diff(c[:, 0]), np.diff(c[:, 1]))
            length3d = float(np.sum(np.sqrt(seg2d ** 2 + np.diff(c[:, 2]) ** 2)))
            cls = ("stairs" if kb in STAIRS else
                   "path" if oa in ("1m Weg", "2m Weg", "1m Wegfragment", "2m Wegfragment", "Markierte Spur") else
                   "motorway" if oa in ("Autobahn", "Autostrasse", "Ausfahrt", "Einfahrt") else
                   "square" if oa == "Platz" else
                   "rail" if layer == "tlm_oev_eisenbahn" and rec.get("verkehrsmittel") != "Tram" else
                   "tram" if layer == "tlm_oev_eisenbahn" else
                   "lift" if layer == "tlm_oev_uebrige_bahn" else "road")
            props = {
                "id": f"swisstlm3d:{rec['uuid'].strip('{}')}" + (f":{gi}" if len(geoms) > 1 else ""),
                "tlm_layer": layer, "class": cls, "objektart": oa, "kunstbaute": kb,
                "is_bridge": kb in BRIDGE, "is_stairs": kb in STAIRS, "is_tunnel": kb in TUNNEL,
                "stufe": rec.get("stufe"), "name": rec.get("name"), "strassenname": rec.get("strassenname"),
                "belagsart": rec.get("belagsart"), "wanderweg": rec.get("wanderwege") == "Wanderweg",
                "befahrbarkeit": rec.get("befahrbarkeit"), "verkehrsbeschraenkung": rec.get("verkehrsbeschraenkung"),
                "verkehrsmittel": rec.get("verkehrsmittel"), "standseilbahn": rec.get("standseilbahn"),
                "length_3d_m": round(length3d, 1),
                "z_min_m": round(float(c[:, 2].min()), 2), "z_max_m": round(float(c[:, 2].max()), 2),
                "above_terrain_max_m": round(float(np.nanmax(above)), 2) if np.isfinite(above).any() else None,
                "above_terrain_min_m": round(float(np.nanmin(above)), 2) if np.isfinite(above).any() else None,
                "width_nominal_m": w, "width_inferred": w_how != "swissTLM3D width class in objektart",
                "capture_year": rec.get("herkunft_jahr"), "revision_year": rec.get("revision_jahr"),
                "source": TLM_SRC, "inferred": False,
            }
            f = {"type": "Feature", "properties": props,
                 "geometry": {"type": "LineString", "coordinates": to_wgs_coords(c)}}
            feats.append(f)
            if props["is_bridge"]:
                bridges.append(f)
                # deck pieces of <= 10 m along the line, each with its own height above terrain
                L = LineString(c[:, :2])
                n = max(1, int(math.ceil(L.length / 10.0)))
                zs = np.interp(np.linspace(0, L.length, n + 1), np.concatenate([[0], np.cumsum(seg2d)]), c[:, 2])
                for k in range(n):
                    a, b = L.length * k / n, L.length * (k + 1) / n
                    pa, pb = L.interpolate(a), L.interpolate(b)
                    piece = LineString([pa, pb]) if a != b else None
                    if piece is None or piece.length < 0.1:
                        continue
                    poly = piece.buffer(w / 2, cap_style=2)
                    mid = piece.interpolate(0.5, normalized=True)
                    deck = float((zs[k] + zs[k + 1]) / 2)
                    t = float(dem.sample([mid.x], [mid.y])[0])
                    if not np.isfinite(t):
                        continue
                    top = max(deck - t, 0.0)
                    lon, lat = tr.transform(*np.asarray(poly.exterior.coords).T)
                    decks.append({"type": "Feature", "properties": {
                        "bridge_id": props["id"], "name": props["name"], "class": cls, "objektart": oa,
                        "deck_z_m": round(deck, 2), "terrain_z_m": round(t, 2),
                        "top_above_terrain_m": round(top, 2),
                        "base_above_terrain_m": round(max(top - (1.5 if cls in ("rail", "road", "motorway") else 0.8), 0), 2),
                        "width_m": w, "source": TLM_SRC + " + swissALTI3D 2 m", "inferred": True,
                        "inferred_how": "deck outline = TLM centreline buffered by nominal width (" + w_how +
                                        "); deck thickness assumed 1.5 m road/rail, 0.8 m path; heights from TLM Z"},
                        "geometry": {"type": "Polygon", "coordinates": [[[round(x, 7), round(y, 7)] for x, y in zip(lon, lat)]]}})

hdr = lambda name: {"type": "FeatureCollection", "name": name,
                    "crs_note": "WGS84 lon/lat (7 dp); third coordinate and *_z_m = LN02 metres (swissTLM3D LV95/LN02). "
                                "above_terrain_* = line Z minus swissALTI3D 2 m terrain (bare earth, so under a bridge it is "
                                "the ground or river surface).",
                    "licence": LIC_TLM, "coverage_lv95": BOX}
PATHS = {"path", "stairs", "square", "lift"}
ROADS = {"road", "motorway"}
for name, fs in (("tlm_paths_3d", [f for f in feats if f["properties"]["class"] in PATHS]),
                 ("tlm_roads_3d", [f for f in feats if f["properties"]["class"] in ROADS]),
                 ("tlm_rail_3d", [f for f in feats if f["properties"]["class"] in ("rail", "tram")]),
                 ("bridges_tlm", bridges), ("bridges_deck_approx", decks)):
    fc = hdr(name); fc["features"] = fs
    json.dump(fc, open(os.path.join(out, name + ".geojson"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

# ---- OSM ---------------------------------------------------------------------
d = json.load(open(overpass, encoding="utf-8"))
KEEP = ["highway", "footway", "sidewalk", "crossing", "name", "bridge", "bridge:name", "bridge:structure", "tunnel",
        "layer", "level", "surface", "incline", "wheelchair", "step_count", "handrail", "ramp", "lit", "railway",
        "man_made", "covered", "indoor", "conveying", "foot", "bicycle", "access", "width", "ele"]
of = []
for e in d["elements"]:
    t = e.get("tags", {})
    p = {"id": f"osm:{e['type']}/{e['id']}", **{k: t[k] for k in KEEP if k in t},
         "source": f"OpenStreetMap via {d.get('_mirror')} retrieved {d.get('_retrieved')}", "licence": "ODbL 1.0",
         "inferred": False}
    if e["type"] == "node":
        g = {"type": "Point", "coordinates": [round(e["lon"], 7), round(e["lat"], 7)]}
    else:
        pts = [[round(q["lon"], 7), round(q["lat"], 7)] for q in e.get("geometry", []) if q]
        if len(pts) < 2:
            continue
        closed = pts[0] == pts[-1] and len(pts) >= 4
        area = closed and (t.get("man_made") == "bridge" or t.get("area") == "yes" or t.get("highway") == "pedestrian" and t.get("area") == "yes")
        g = {"type": "Polygon", "coordinates": [pts]} if area else {"type": "LineString", "coordinates": pts}
    of.append({"type": "Feature", "properties": p, "geometry": g})
fc = {"type": "FeatureCollection", "name": "osm_paths_bridges",
      "crs_note": "WGS84 lon/lat (7 dp). OSM has no heights; 'layer' is relative stacking only.",
      "licence": "© OpenStreetMap contributors, ODbL 1.0 (https://opendatacommons.org/licenses/odbl/)",
      "query": d.get("_query"), "features": of}
json.dump(fc, open(os.path.join(out, "osm_paths_bridges.geojson"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

import collections
cc = collections.Counter(f["properties"]["class"] for f in feats)
stats.update({"tlm_features": len(feats), "tlm_by_class": dict(cc), "bridges_tlm": len(bridges),
              "bridge_deck_pieces": len(decks), "osm_features": len(of),
              "osm_by_highway": dict(collections.Counter(f["properties"].get("highway", "-") for f in of).most_common(20)),
              "osm_bridges": sum(1 for f in of if f["properties"].get("bridge") not in (None, "no")),
              "stairs_tlm": sum(1 for f in feats if f["properties"]["is_stairs"])})
json.dump(stats, open(os.path.join(out, "network_stats.json"), "w"), indent=1, ensure_ascii=False)
print(json.dumps(stats, indent=1, ensure_ascii=False))
