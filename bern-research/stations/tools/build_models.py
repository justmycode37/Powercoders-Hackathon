#!/usr/bin/env python3
"""Parametric 3D builder: station GeoJSON -> lightweight binary glTF (GLB).

Pure standard library.  The same routines build

  models/<slug>.glb + models/<slug>.model.json      focus stations, by level
  models/archetypes/*.glb                            generic stop pieces (fallback)
  data/edge_placements.json                          where/how to place an archetype for every boarding edge
  .cache/models/<number>.glb  (--station N | --all)  per-station fallback models built from the citywide data

Model frame (stated again in every sidecar and in the glTF asset.extras):
  units metres, right-handed, +Y up, +X = east, +Z = south (-Z = north);
  origin = (origin_lv95_e, origin_lv95_n, origin_height_m).  So for a vertex (x, y, z):
  E = origin_e + x,  N = origin_n - z,  height = origin_height + y.

Everything that is not measured is listed under "approximations" in the sidecar.

Usage: python tools/build_models.py [--focus] [--archetypes] [--placements] [--station N ...] [--all]
       (no arguments = --focus --archetypes --placements)
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import os
import struct
import sys

import geo
from common import DATA, ROOT

NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
MODELS = os.path.join(ROOT, "models")

# nominal dimensions (metres) used only where the data has none - all reported as approximate
NOM = dict(
    kerb_rail=0.55, kerb_street=0.25, platform_width=dict(rail=6.0, tram=3.0, bus=2.5, other=2.5),
    shelter_h=3.0, canopy_h=4.5, roof_t=0.15, passage_w_tunnel=4.0, passage_w_open=2.5, floor_t=0.12,
    stairs_w=2.2, escalator_w=1.2, lift=2.2, storey_clear=2.6, marker=(1.2, 0.25, 2.3), post=(0.12, 2.6),
)
COLOR = {      # RGBA
    "platform_surface": (0.62, 0.62, 0.64, 1), "platform_body": (0.70, 0.70, 0.72, 1), "boarding_edge": (0.93, 0.80, 0.16, 1),
    "shelter": (0.25, 0.55, 0.85, 0.75), "canopy": (0.35, 0.65, 0.90, 0.6), "roof": (0.45, 0.72, 0.92, 0.5),
    "passage": (0.20, 0.42, 0.78, 1), "stairs": (0.15, 0.62, 0.30, 1), "escalator": (0.35, 0.85, 0.35, 1),
    "ramp_or_link": (0.10, 0.60, 0.60, 1), "moving_walkway": (0.35, 0.85, 0.65, 1), "lift": (0.55, 0.25, 0.75, 0.85),
    "entrance": (0.10, 0.10, 0.10, 1), "access_point": (0.95, 0.55, 0.10, 1), "sector_board": (0.95, 0.75, 0.10, 1),
    "building_part": (0.84, 0.82, 0.78, 1), "building_footprint": (0.78, 0.76, 0.72, 1), "post": (0.3, 0.3, 0.3, 1),
}


class Builder:
    def __init__(self, e0, n0, h0):
        self.e0, self.n0, self.h0 = e0, n0, h0
        self.groups = collections.OrderedDict()      # key -> dict(pos=[], idx=[], feats=[])
        self.approx = collections.Counter()
        self.skipped = collections.Counter()

    def _g(self, key):
        return self.groups.setdefault(key, dict(pos=[], idx=[], feats=[]))

    def _v(self, g, p, h):
        g["pos"].append((p[0] - self.e0, h - self.h0, -(p[1] - self.n0)))
        return len(g["pos"]) - 1

    def begin(self, key, fid):
        g = self._g(key)
        g["_start"] = len(g["idx"])
        g["_fid"] = fid
        return g

    def end(self, g):
        n = len(g["idx"]) - g["_start"]
        if n:
            g["feats"].append([g["_fid"], g["_start"], n])

    def prism(self, g, ring, y0, y1):
        ring = [p for i, p in enumerate(ring) if i == 0 or geo.dist(p, ring[i - 1]) > 0.01]
        if len(ring) > 3 and geo.dist(ring[0], ring[-1]) < 0.01:
            ring = ring[:-1]
        if len(ring) > 24:
            ring = geo.simplify(ring + [ring[0]], 0.08)[:-1]
        if len(ring) < 3:
            return
        tris = geo.triangulate(ring)
        top = [self._v(g, p, y1) for p in ring]
        bot = [self._v(g, p, y0) for p in ring]
        for a, b, c in tris:
            g["idx"] += [top[a], top[b], top[c], bot[a], bot[c], bot[b]]
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            g["idx"] += [top[i], bot[i], bot[j], top[i], bot[j], top[j]]

    def ribbon(self, g, line, width, y_a, y_b, thick, offset=0.0):
        """Strip along a polyline; top height runs linearly from y_a to y_b; offset shifts it sideways (+ = left)."""
        if len(line) < 2:
            return
        L = geo.line_length(line) or 1.0
        run, lt, rt, lb, rb = 0.0, [], [], [], []
        for i, p in enumerate(line):
            a, b = line[max(0, i - 1)], line[min(len(line) - 1, i + 1)]
            d = geo.dist(a, b) or 1.0
            nx, ny = -(b[1] - a[1]) / d, (b[0] - a[0]) / d
            if i:
                run += geo.dist(line[i - 1], p)
            y = y_a + (y_b - y_a) * run / L
            pl = (p[0] + nx * (offset + width / 2), p[1] + ny * (offset + width / 2))
            pr = (p[0] + nx * (offset - width / 2), p[1] + ny * (offset - width / 2))
            lt.append(self._v(g, pl, y))
            rt.append(self._v(g, pr, y))
            lb.append(self._v(g, pl, y - thick))
            rb.append(self._v(g, pr, y - thick))
        for i in range(len(line) - 1):
            j = i + 1
            g["idx"] += [lt[i], rt[i], rt[j], lt[i], rt[j], lt[j],          # top
                         lb[i], rb[j], rb[i], lb[i], lb[j], rb[j],          # bottom
                         lt[i], lt[j], lb[j], lt[i], lb[j], lb[i],          # left
                         rt[i], rb[j], rt[j], rt[i], rb[i], rb[j]]          # right
        g["idx"] += [lt[0], lb[0], rb[0], lt[0], rb[0], rt[0], lt[-1], rb[-1], lb[-1], lt[-1], rt[-1], rb[-1]]

    def box(self, g, centre, brg, length, width, y0, y1):
        self.prism(g, geo.rect(centre, brg, length, width), y0, y1)

    # ---- output ---------------------------------------------------------------------------------
    def write(self, path, title, extras, sidecar_extra=None):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        bin_parts, views, accessors, meshes, nodes, materials, mat_index = [], [], [], [], [], [], {}
        offset = 0
        feature_index = []
        for key, g in self.groups.items():
            if not g["idx"]:
                continue
            ftype = key.split("@")[0]
            col = COLOR.get(ftype, (0.6, 0.6, 0.6, 1))
            if ftype not in mat_index:
                mat_index[ftype] = len(materials)
                m = dict(name=ftype, doubleSided=True,
                         pbrMetallicRoughness=dict(baseColorFactor=list(col), metallicFactor=0.0, roughnessFactor=0.9))
                if col[3] < 1:
                    m["alphaMode"] = "BLEND"
                materials.append(m)
            pos = struct.pack(f"<{len(g['pos']) * 3}f", *[c for v in g["pos"] for c in v])
            idx = struct.pack(f"<{len(g['idx'])}I", *g["idx"])
            xs, ys, zs = zip(*g["pos"])
            for blob, target in ((pos, 34962), (idx, 34963)):
                pad = (-len(blob)) % 4
                views.append(dict(buffer=0, byteOffset=offset, byteLength=len(blob), target=target))
                bin_parts.append(blob + b"\0" * pad)
                offset += len(blob) + pad
            f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]   # noqa: E731
            accessors.append(dict(bufferView=len(views) - 2, componentType=5126, count=len(g["pos"]), type="VEC3",
                                  min=[f32(min(xs)), f32(min(ys)), f32(min(zs))],
                                  max=[f32(max(xs)), f32(max(ys)), f32(max(zs))]))
            accessors.append(dict(bufferView=len(views) - 1, componentType=5125, count=len(g["idx"]), type="SCALAR"))
            meshes.append(dict(name=key, primitives=[dict(attributes=dict(POSITION=len(accessors) - 2),
                                                          indices=len(accessors) - 1, material=mat_index[ftype])]))
            lvl = key.split("@")[1] if "@" in key else None
            nodes.append(dict(name=key, mesh=len(meshes) - 1,
                              extras=dict(feature_type=ftype, level=lvl, features=len(g["feats"]))))
            for fid, start, n in g["feats"]:
                feature_index.append(dict(id=fid, node=key, first_index=start, index_count=n))
        frame = dict(units="metre", up="+Y", x="east", z="south", handedness="right",
                     origin_lv95_e=self.e0, origin_lv95_n=self.n0, origin_height_m=self.h0, height_datum="LN02",
                     origin_wgs84=[round(c, 7) for c in geo.lv95_to_wgs84(self.e0, self.n0)],
                     to_lv95="E = origin_lv95_e + x; N = origin_lv95_n - z; height = origin_height_m + y")
        gltf = dict(asset=dict(version="2.0", generator="bern-research/stations/tools/build_models.py",
                               extras=dict(title=title, frame=frame, generated_utc=NOW, **extras)),
                    scene=0, scenes=[dict(name=title, nodes=list(range(len(nodes))))], nodes=nodes, meshes=meshes,
                    materials=materials, accessors=accessors, bufferViews=views, buffers=[dict(byteLength=offset)])
        js = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
        js += b" " * ((-len(js)) % 4)
        binb = b"".join(bin_parts)
        with open(path, "wb") as f:
            f.write(struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(binb)))
            f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
            f.write(struct.pack("<II", len(binb), 0x004E4942) + binb)
        tris = sum(len(g["idx"]) for g in self.groups.values()) // 3
        side = dict(title=title, glb=os.path.basename(path), generated_utc=NOW, frame=frame, bytes=os.path.getsize(path),
                    triangles=tris, vertices=sum(len(g["pos"]) for g in self.groups.values()),
                    nodes=[dict(name=n["name"], **n["extras"]) for n in nodes],
                    nominal_dimensions_m=NOM,
                    approximations={k: v for k, v in sorted(self.approx.items())},
                    skipped={k: v for k, v in sorted(self.skipped.items())},
                    feature_index_note="index ranges into each node's single primitive, for picking a feature id",
                    **extras, **(sidecar_extra or {}), feature_index=feature_index)
        with open(os.path.splitext(path)[0] + ".model.json", "w", encoding="utf-8") as f:
            json.dump(side, f, ensure_ascii=False, separators=(",", ":"))
        return side


def xy(c):
    return geo.wgs84_to_lv95(c[0], c[1])


def geom_xy(g):
    if g["type"] == "Point":
        return [xy(g["coordinates"])]
    if g["type"] == "LineString":
        return [xy(c) for c in g["coordinates"]]
    return [xy(c) for c in g["coordinates"][0]]


def add_features(b: Builder, feats, level_elev, default_elev):
    """Turn features into geometry.  level_elev: {level: elevation}; default_elev for level-less data."""
    surfaced, seen_ids = set(), set()
    for f in feats:
        p = f["properties"]
        if p["feature_type"] == "platform_surface":
            for s in p.get("edge_sloids") or ([p["edge_sloid"]] if p.get("edge_sloid") else []):
                surfaced.add(s)
    # the cadastral survey and OSM can both hold the same platform: draw the surveyed one only
    survey_rings = [geom_xy(f["geometry"]) for f in feats if f["properties"]["feature_type"] == "platform_surface"
                    and f["properties"].get("geometry_quality") == "surveyed" and f["geometry"]["type"] == "Polygon"]

    def duplicate_of_survey(f):
        if f["properties"].get("geometry_quality") == "surveyed" or f["geometry"]["type"] != "Polygon":
            return False
        c = geo.ring_centroid(geom_xy(f["geometry"]))
        return any(geo.point_in_ring(c, r) for r in survey_rings)

    def elev(p, lv=None):
        lv = p.get("level") if lv is None else lv
        if lv is not None and lv in level_elev and level_elev[lv] is not None:
            return level_elev[lv]
        return default_elev

    def top_of(p):
        z = elev(p)
        h = p.get("atlas_height_m")
        if h is not None and abs(h - z) <= 3.0:
            return h
        return z

    for f in feats:
        p, g = f["properties"], f["geometry"]
        if g is None:
            continue
        ft, pts = p["feature_type"], geom_xy(g)
        lv = p.get("level")
        key = f"{ft}@{lv if lv is not None else 'x'}"
        if ft == "boarding_edge":
            rail = "TRAIN" in (p.get("station_modes") or "")
            bh = p.get("atlas_boarding_height_cm")
            kerb = (bh / 100.0) if bh else (NOM["kerb_rail"] if rail else NOM["kerb_street"])
            if not bh:
                b.approx["kerb height nominal (no atlas boardingAreaHeight)"] += 1
            top = top_of(p)
            if g["type"] != "LineString":
                gg = b.begin(f"post@{lv}", f["id"])
                b.box(gg, pts[0], 0, NOM["post"][0], NOM["post"][0], top, top + NOM["post"][1])
                b.end(gg)
                b.approx["stop shown as a post only (no edge line)"] += 1
                continue
            gg = b.begin(key, f["id"])
            b.ribbon(gg, pts, 0.35, top + 0.02, top + 0.02, kerb + 0.02)
            b.end(gg)
            if p["edge_sloid"] not in surfaced:      # no platform polygon: nominal body beside the kerb line
                mode = p.get("mode_guess") or "other"
                w = NOM["platform_width"].get(mode, 2.5)
                side = p.get("platform_side_bearing_deg")
                off = 0.0
                if side is not None:
                    fwd = geo.bearing(pts[0], pts[-1])
                    left = (fwd - 90) % 360
                    off = (w / 2) if geo.angle_diff(side, left) < 90 else -(w / 2)
                else:
                    b.approx["platform side unknown: nominal body centred on the edge line"] += 1
                gg = b.begin(f"platform_body@{lv}", f["id"])
                b.ribbon(gg, pts, w, top, top, kerb, offset=off)
                b.end(gg)
                b.approx[f"platform body of nominal width beside the kerb line ({p.get('geometry_method')})"] += 1
        elif ft == "platform_surface" and g["type"] == "Polygon":
            if duplicate_of_survey(f):
                b.skipped["OSM platform polygon covered by a surveyed platform outline"] += 1
                continue
            z = elev(p)
            gg = b.begin(key, f["id"])
            b.prism(gg, pts, z - (NOM["kerb_rail"] if p.get("length_m", 0) > 90 else NOM["kerb_street"]), z)
            b.end(gg)
            b.approx["platform slab thickness nominal"] += 1
        elif ft in ("shelter", "canopy", "roof"):
            z = elev(p) if lv is not None else default_elev
            h = p.get("height_m") or (NOM["canopy_h"] if ft != "shelter" else NOM["shelter_h"])
            if p.get("height_quality") != "source_derived":
                b.approx[f"{ft} roof height nominal"] += 1
            gg = b.begin(key, f["id"])
            if g["type"] == "Polygon":
                b.prism(gg, pts, z + h - NOM["roof_t"], z + h)
                r = geo.min_rect(pts)
                if ft != "roof" and r["length"] < 60:
                    for c in r["corners"]:
                        q = (c[0] + (r["centre"][0] - c[0]) * 0.08, c[1] + (r["centre"][1] - c[1]) * 0.08)
                        b.box(gg, q, r["bearing"], 0.12, 0.12, z, z + h - NOM["roof_t"])
            else:
                b.box(gg, pts[0], 0, 4.0, 1.6, z + h - NOM["roof_t"], z + h)
                b.approx["shelter drawn as a nominal 4 x 1.6 m roof (point only)"] += 1
            b.end(gg)
        elif ft in ("passage", "ramp_or_link", "moving_walkway", "stairs", "escalator"):
            fl, tl = p.get("from_level"), p.get("to_level")
            if fl is not None and tl is not None:
                za, zb = elev(p, fl), elev(p, tl)
            elif lv is not None:
                za = zb = elev(p)
            elif p.get("levels"):
                za = zb = elev(p, min(p["levels"]))
                b.approx[f"{ft} drawn flat at its lowest level (end levels unresolved)"] += 1
            else:
                if ft in ("stairs", "escalator") or p.get("tunnel") or p.get("indoor"):
                    b.skipped[f"{ft} without level information"] += 1
                    continue
                za = zb = default_elev
            w = p.get("width_m")
            if not w:
                w = (NOM["escalator_w"] if ft == "escalator" else NOM["stairs_w"] if ft == "stairs"
                     else NOM["passage_w_tunnel"] if (p.get("tunnel") or p.get("indoor")) else NOM["passage_w_open"])
                b.approx[f"{ft} width nominal"] += 1
            gg = b.begin(key, f["id"])
            if g["type"] == "Polygon":
                b.prism(gg, pts, za - NOM["floor_t"], za)
            else:
                b.ribbon(gg, pts, w, za, zb, NOM["floor_t"])
            b.end(gg)
        elif ft == "lift":
            lvs = p.get("levels") or ([lv] if lv is not None else [])
            if not lvs:
                b.skipped["lift without level information"] += 1
                continue
            z0, z1 = elev(p, min(lvs)), elev(p, max(lvs)) + NOM["storey_clear"]
            gg = b.begin(f"lift@{min(lvs)}..{max(lvs)}", f["id"])
            if g["type"] == "Polygon":
                b.prism(gg, pts, z0, z1)
            else:
                b.box(gg, pts[0], 0, NOM["lift"], NOM["lift"], z0, z1)
                b.approx["lift car drawn as a nominal 2.2 m box (point only)"] += 1
            b.end(gg)
        elif ft in ("entrance", "access_point"):
            z = elev(p)
            gg = b.begin(key, f["id"])
            b.box(gg, pts[0], 0, NOM["marker"][0], NOM["marker"][1], z, z + NOM["marker"][2])
            b.end(gg)
        elif ft == "sector_board":
            z = elev(p)
            gg = b.begin(key, f["id"])
            b.box(gg, pts[0], 0, NOM["post"][0], NOM["post"][0], z, z + NOM["post"][1])
            b.box(gg, pts[0], 0, 0.6, 0.06, z + NOM["post"][1], z + NOM["post"][1] + 0.4)
            b.end(gg)
        elif ft == "building_part" and g["type"] == "Polygon":
            h = p.get("height_m")
            if not h:
                b.skipped["building_part without any height information"] += 1
                continue
            if p.get("height_quality") != "source_derived":
                b.approx["building height from storey count x 3.5 m"] += 1
            z = default_elev
            gg = b.begin("building_part@x", f["id"])
            b.prism(gg, pts, z + (p.get("min_height_m") or 0), z + h)
            b.end(gg)
        elif ft == "building_footprint" and g["type"] == "Polygon" and p.get("role") == "station_building":
            gg = b.begin("building_footprint@0", f["id"])
            b.prism(gg, pts, default_elev - 0.05, default_elev + 0.05)
            b.end(gg)


def build_focus():
    out = []
    slugs = [f["slug"] for f in json.load(open(os.path.join(DATA, "focus", "index.json"), encoding="utf-8"))["focus"]]
    for old in os.listdir(MODELS) if os.path.isdir(MODELS) else []:
        if os.path.isfile(os.path.join(MODELS, old)) and old.split(".")[0] not in slugs:
            os.remove(os.path.join(MODELS, old))
    for slug in slugs:
        fc = json.load(open(os.path.join(DATA, "focus", f"{slug}.geojson"), encoding="utf-8"))
        meta = fc["metadata"]
        levels = {l["level"]: l["elevation_m"] for l in meta["levels"]}
        e0, n0 = geo.wgs84_to_lv95(*meta["centre"])
        h0 = levels.get(0) or 540.0
        b = Builder(round(e0, 2), round(n0, 2), h0)
        add_features(b, fc["features"], levels, h0)
        side = b.write(os.path.join(MODELS, f"{slug}.glb"), meta["title"],
                       dict(focus=slug, stations=meta["stations"], source_geojson=f"data/focus/{slug}.geojson",
                            licence="mixed: derived from the features in the source GeoJSON (see their 'licence'); "
                                    "contains OSM-derived geometry (ODbL)"),
                       dict(levels=meta["levels"]))
        out.append((slug, side["bytes"], side["triangles"]))
    print(f"  {len(out)} focus models, {sum(o[1] for o in out)} bytes, {sum(o[2] for o in out)} triangles; "
          f"largest {max(out, key=lambda o: o[1])}")
    return out


def build_station(number, edges, feats, out_dir):
    es = [f for f in edges if f["properties"]["station_number"] == number and f["geometry"]]
    if not es:
        return None
    fs = [f for f in feats if f["properties"]["station_number"] == number]
    hs = [f["properties"]["atlas_height_m"] for f in es if f["properties"].get("atlas_height_m")]
    h0 = min(hs) if hs else 540.0
    pts = [q for f in es for q in geom_xy(f["geometry"])]
    e0 = round(sum(p[0] for p in pts) / len(pts), 2)
    n0 = round(sum(p[1] for p in pts) / len(pts), 2)
    b = Builder(e0, n0, h0)
    for f in es + fs:
        f["properties"].setdefault("level", 0)
    add_features(b, es + fs, {0: h0}, h0)
    name = es[0]["properties"]["station_name"]
    return b.write(os.path.join(out_dir, f"{number}.glb"), name,
                   dict(station_number=number, station_sloid=es[0]["properties"]["station_sloid"],
                        source_geojson="data/boarding_edges.geojson + data/station_features.geojson",
                        model_tier="fallback: single level, edges + platforms + shelters only",
                        licence="mixed: derived from the cited features; may contain OSM-derived geometry (ODbL)"))


def build_archetypes():
    """Generic stop pieces.  Local frame: +X along the kerb, +Z from the kerb into the platform, +Y up,
    origin on the kerb line at mid length, y = 0 at the platform top."""
    specs = {
        "tram_stop": dict(length=42.0, width=3.0, kerb=0.27, shelter=(10.0, 1.8), note="42 m platform, one shelter"),
        "bus_stop": dict(length=18.0, width=2.5, kerb=0.22, shelter=(4.0, 1.6), note="18 m kerb, one shelter"),
        "bus_stop_pole": dict(length=12.0, width=2.0, kerb=0.16, shelter=None, note="12 m kerb, sign post only"),
        "rail_platform": dict(length=150.0, width=6.0, kerb=0.55, shelter=(40.0, 4.5), note="150 m side platform with canopy"),
    }
    out = []
    for name, s in specs.items():
        b = Builder(0.0, 0.0, 0.0)
        L, W = s["length"], s["width"]
        # local +X -> east, local +Z -> south, so the platform lies south of the kerb line (y = N = 0)
        g = b.begin("platform_body@0", "platform")
        b.prism(g, [(-L / 2, 0), (L / 2, 0), (L / 2, -W), (-L / 2, -W)], -s["kerb"], 0.0)
        b.end(g)
        g = b.begin("boarding_edge@0", "kerb")
        b.ribbon(g, [(-L / 2, -0.175), (L / 2, -0.175)], 0.35, 0.02, 0.02, s["kerb"] + 0.02)
        b.end(g)
        if s["shelter"]:
            sl, sw = s["shelter"]
            h = NOM["canopy_h"] if name == "rail_platform" else NOM["shelter_h"]
            cz = -(W - sw / 2 - 0.2)
            g = b.begin("shelter@0", "shelter")
            b.prism(g, [(-sl / 2, cz + sw / 2), (sl / 2, cz + sw / 2), (sl / 2, cz - sw / 2), (-sl / 2, cz - sw / 2)],
                    h - NOM["roof_t"], h)
            for sx in (-sl / 2 + 0.2, sl / 2 - 0.2):
                for sz in (cz + sw / 2 - 0.2, cz - sw / 2 + 0.2):
                    b.box(g, (sx, sz), 0, 0.12, 0.12, 0.0, h - NOM["roof_t"])
            b.end(g)
        g = b.begin("post@0", "sign_post")
        b.box(g, (L / 2 - 1.0, -0.8), 0, 0.1, 0.1, 0.0, 2.6)
        b.box(g, (L / 2 - 1.0, -0.8), 0, 0.5, 0.06, 2.6, 3.0)
        b.end(g)
        side = b.write(os.path.join(MODELS, "archetypes", f"{name}.glb"), f"archetype: {name}",
                       dict(archetype=name, nominal=s, licence="CC0 1.0 (generic shapes made by this project, no third-party data)",
                            local_frame="+X along the kerb, +Z from the kerb into the platform, +Y up; origin on the kerb line "
                                        "at mid length; y = 0 is the platform top",
                            scaling="scale X by edge length / nominal length; do not scale Y"))
        out.append((name, side["bytes"]))
        print(f"  archetypes/{name}.glb: {side['bytes']} bytes")
    return specs


def build_placements(edges):
    rows = []
    for f in edges:
        p, g = f["properties"], f["geometry"]
        if not g or g["type"] != "LineString":
            continue
        pts = geom_xy(g)
        L = geo.line_length(pts)
        mid = geo.line_interpolate(pts, L / 2)
        fwd = geo.line_bearing_at(pts, L / 2)
        side = p.get("platform_side_bearing_deg")
        xb = (side - 90) % 360 if side is not None else fwd
        rail = "TRAIN" in (p.get("station_modes") or "")
        mode = "rail" if rail else p.get("mode_guess")
        arche = "rail_platform" if rail else "tram_stop" if mode == "tram" else "bus_stop" if L >= 14 else "bus_stop_pole"
        nominal = dict(rail_platform=150.0, tram_stop=42.0, bus_stop=18.0, bus_stop_pole=12.0)[arche]
        ll = geo.lv95_to_wgs84(*mid)
        rows.append(dict(
            edge_sloid=p["edge_sloid"], station_sloid=p["station_sloid"], station_number=p["station_number"],
            designation=p.get("designation"), archetype=arche, lon=round(ll[0], 7), lat=round(ll[1], 7),
            lv95_e=round(mid[0], 2), lv95_n=round(mid[1], 2), height_m=p.get("atlas_height_m"),
            x_axis_bearing_deg=round(xb, 1), rotation_y_deg=round((90 - xb) % 360, 1),
            scale_x=round(L / nominal, 3), length_m=round(L, 1),
            platform_side_known=side is not None, geometry_method=p["geometry_method"],
            geometry_quality=p["geometry_quality"], inferred=True,
            inferred_how="placement derived from the edge line; archetype dimensions are nominal, not measured"))
    doc = dict(generated_utc=NOW,
               note="One row per boarding edge that has a line geometry. Put the archetype GLB at (lon, lat, height_m), "
                    "rotate it about +Y by rotation_y_deg (model frame: +X east, +Y up, +Z south) and scale X by scale_x. "
                    "The archetype then lies along the kerb with its platform on the waiting side.",
               height_note="height_m is the atlas edge height (metres above sea level, LN02 assumed)",
               archetypes="models/archetypes/<archetype>.glb", count=len(rows),
               by_archetype=dict(collections.Counter(r["archetype"] for r in rows)), placements=rows)
    with open(os.path.join(DATA, "edge_placements.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  edge_placements.json: {len(rows)} placements {doc['by_archetype']}")


def main() -> int:
    args = sys.argv[1:]
    default = not args
    edges = json.load(open(os.path.join(DATA, "boarding_edges.geojson"), encoding="utf-8"))["features"]
    feats = json.load(open(os.path.join(DATA, "station_features.geojson"), encoding="utf-8"))["features"]
    if default or "--focus" in args:
        build_focus()
    if default or "--archetypes" in args:
        build_archetypes()
    if default or "--placements" in args:
        build_placements(edges)
    numbers = [a for a in args if a.isdigit()]
    if "--all" in args:
        numbers = sorted({f["properties"]["station_number"] for f in edges if f["geometry"]})
    if numbers:
        out_dir = os.path.join(ROOT, ".cache", "models")
        total = n = 0
        for num in numbers:
            side = build_station(num, edges, feats, out_dir)
            if side:
                n += 1
                total += side["bytes"]
        print(f"  {n} station models in {out_dir} ({total} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
