#!/usr/bin/env python3
"""Detailed, level-aware geometry for the focus stations.

Reads the cached extracts plus the citywide outputs of build_geometry.py and
writes, per focus station (bern-bahnhof, zytglogge, wankdorf):

  data/focus/<slug>.geojson           all features, each with level + provenance
  data/focus/<slug>.walk_graph.json   pedestrian graph (nodes, edges, levels)
  data/focus/index.json               stations, level table, counts

Source ranking: Stadt Bern cadastral survey and SBB kerb points are "surveyed",
atlas/SBB point registers "official_point", OSM "community"; everything this
script derives is flagged inferred=true with inferred_how.

Usage: python tools/build_focus.py [--no-network]   (network = swisstopo heights)
"""
from __future__ import annotations

import collections
import concurrent.futures
import datetime as dt
import json
import os
import statistics
import sys
import urllib.request

import geo
from common import (DATA, EXTRACT, LICENCE, focus_areas, Grid, closed_ring, esri_paths, feature, gj_line, gj_point,
                    gj_polygon, osm_id, osm_point, osm_rings, osm_url, osm_way_xy, parse_levels, read_json,
                    write_geojson)

NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
HEIGHT_CACHE = os.path.join(EXTRACT, "swisstopo-heights.json")
HEIGHT_URL = "https://api3.geo.admin.ch/rest/services/height?easting={e:.1f}&northing={n:.1f}&sr=2056"
STOREY = 4.5        # nominal level spacing (m) used only where no height source exists
CORE_M = 45.0       # "station_core" = within this distance of a public boarding edge of the primary stations
BUILDING_M = 30.0   # buildings kept when this close to a primary boarding edge
WALK = ("footway", "steps", "pedestrian", "path", "corridor")
AV_SRC = "Stadt Bern Amtliche Vermessung"


# --- terrain heights (swisstopo height service, swissALTI3D, LN02) --------------
def terrain_heights(points, network=True):
    cache = {}
    if os.path.exists(HEIGHT_CACHE):
        with open(HEIGHT_CACHE, encoding="utf-8") as f:
            cache = json.load(f)
    keys = {f"{round(p[0], 1)},{round(p[1], 1)}": p for p in points}
    todo = [k for k in keys if k not in cache]

    def one(k):
        p = keys[k]
        try:
            req = urllib.request.Request(HEIGHT_URL.format(e=p[0], n=p[1]), headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return k, float(json.loads(r.read())["height"])
        except Exception:  # noqa: BLE001
            return k, None

    if todo and network:
        with concurrent.futures.ThreadPoolExecutor(6) as ex:
            for k, h in ex.map(one, todo):
                if h is not None:
                    cache[k] = h
        with open(HEIGHT_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, separators=(",", ":"))
    return {keys[k]: cache.get(k) for k in keys}


def _plan_checks():
    path = os.path.join(os.path.dirname(DATA), "references.json")
    if not os.path.exists(path):
        return {}, {}
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return {c["station_number"]: c for c in d["plan_checks"]}, {p["id"]: p for p in d["plans"]}


PLAN_CHECKS, PLANS = _plan_checks()


STREETS = ("living_street", "residential", "unclassified", "tertiary", "secondary", "primary",
           "tertiary_link", "secondary_link", "primary_link", "pedestrian")
_ROADS = None


def roads():
    """Citywide OSM road centrelines (no node ids in that extract; joined to the graph by coordinate)."""
    global _ROADS
    if _ROADS is None:
        _ROADS = Grid(100)
        try:
            els = read_json("osm/city-roads.json")["elements"]
        except FileNotFoundError:
            els = []
        for el in els:
            geom = [g for g in el.get("geometry", []) if g]
            xy = osm_way_xy(el)
            if len(xy) >= 2 and len(xy) == len(geom):
                _ROADS.add(dict(id=el["id"], tags=el.get("tags", {}), xy=xy,
                                keys=[(round(g["lon"], 7), round(g["lat"], 7)) for g in geom]), xy)
    return _ROADS


TLM_PATH = os.path.join(os.path.dirname(DATA), "..", "city3d", "data", "network", "tlm_paths_3d.geojson")
TLM_NOTE = "swissTLM3D 3D path heights, LN02 (read from bern-research/city3d/data/network/tlm_paths_3d.geojson)"
_TLM = None


def tlm_paths():
    """swissTLM3D footpaths with measured Z (LN02), if the city3d folder has built them; else an empty index."""
    global _TLM
    if _TLM is None:
        _TLM = Grid(60)
        if os.path.exists(TLM_PATH):
            with open(TLM_PATH, encoding="utf-8") as f:
                for ft in json.load(f)["features"]:
                    g = ft["geometry"]
                    if g["type"] != "LineString":
                        continue
                    cs = [c for c in g["coordinates"] if len(c) > 2]
                    if len(cs) < 2:
                        continue
                    xy = [geo.wgs84_to_lv95(c[0], c[1]) for c in cs]
                    _TLM.add(dict(xy=xy, z=[c[2] for c in cs], id=ft["properties"].get("id"),
                                  kunstbaute=ft["properties"].get("kunstbaute")), xy)
    return _TLM


def tlm_height(q, r=3.5):
    """Measured path height at point q -> list of (z, tlm id) for every TLM path passing within r metres."""
    out = []
    for t in tlm_paths().near(q, r):
        d, _, pt, i = geo.line_project(q, t["xy"])
        if d > r:
            continue
        a, b = t["xy"][i], t["xy"][i + 1]
        seg = geo.dist(a, b) or 1.0
        k = min(1.0, max(0.0, geo.dist(a, pt) / seg))
        out.append((t["z"][i] + k * (t["z"][i + 1] - t["z"][i]), t["id"]))
    return out


def infer_level(t):
    """Level for a walkway that has no OSM level tag but is a tunnel (or a bridge with a layer tag).
    Returns (level, reason) or None.  Steps are handled from the ways at their ends instead."""
    if t.get("level") is not None or t.get("highway") == "steps":
        return None
    try:
        lay = int(t.get("layer"))
    except (TypeError, ValueError):
        lay = None
    if t.get("tunnel") == "yes":
        if lay is not None and lay < 0:
            # OSM layer is a drawing order, not a storey count: any negative layer becomes level -1
            return (-1, f"OSM tunnel=yes with layer={lay}, no level tag: assumed one level below street level")
        return None      # tunnel=yes alone is also used for arcades in the old town: do not guess
    if t.get("bridge") in ("yes", "viaduct") and lay is not None and lay > 0:
        return (1, f"OSM bridge=yes with layer={lay}, no level tag: assumed one level above street level")
    return None


def tags(el):
    return el.get("tags", {})


def el_xy(el):
    if el["type"] == "node":
        return [osm_point(el)]
    if el["type"] == "way":
        return osm_way_xy(el)
    return [p for m in el.get("members", []) if m.get("geometry") for p in osm_way_xy(m)]


def centroid(xy):
    return (sum(p[0] for p in xy) / len(xy), sum(p[1] for p in xy) / len(xy))


def one_level(levels):
    return levels[0] if len(levels) == 1 else None


def inside_any(p, polys):
    return any(geo.point_in_ring(p, r) for r in polys)


def share_inside(line, polys, step=2.0):
    """Share of a polyline (sampled every `step` m) that lies inside any polygon."""
    n = max(2, int(geo.line_length(line) / step) + 1)
    L = geo.line_length(line)
    hits = sum(1 for i in range(n) if inside_any(geo.line_interpolate(line, L * i / (n - 1)), polys))
    return hits / n


def build(slug, cfg, edges_all, feats_all, network):
    lat, lon = cfg["centre_wgs"]
    C = geo.wgs84_to_lv95(lon, lat)
    R = cfg["radius"]
    osm = read_json(f"osm/detail-{slug}.json")["elements"]
    nodes = {e["id"]: e for e in osm if e["type"] == "node"}
    out, rep = [], collections.Counter()

    def near(xy, r=R):
        return min(geo.dist(p, C) for p in xy) <= r

    # ---- stations and their boarding edges (copied from the citywide build) -------------
    st_in = {}
    for f in edges_all:
        p = f["properties"]
        if p.get("lv95_e") is None:
            continue
        if p["station_number"] in cfg["numbers"] or geo.dist((p["lv95_e"], p["lv95_n"]), C) <= R:
            st_in.setdefault(p["station_number"], dict(number=p["station_number"], sloid=p["station_sloid"],
                                                       name=p["station_name"],
                                                       role="primary" if p["station_number"] in cfg["numbers"] else "adjacent"))
    primary = set(cfg["numbers"])
    edges = [f for f in edges_all if f["properties"]["station_number"] in st_in]

    # OSM platforms with level tags, to give every boarding edge a level
    plat = []
    for el in osm:
        t = tags(el)
        if (t.get("public_transport") == "platform" or t.get("railway") in ("platform", "platform_edge")
                or t.get("highway") == "platform") and el["type"] != "node":
            refs = {x.strip() for k in ("local_ref", "ref") for x in str(t.get(k, "")).split(";") if x.strip()}
            rings = osm_rings(el)
            for xy in (rings or [osm_way_xy(el)]):
                if len(xy) >= 2:
                    plat.append(dict(el=el, xy=xy, poly=bool(rings), refs=refs, levels=parse_levels(t.get("level"))))

    core_lines = Grid(60)
    n_core = 0
    for f in edges:
        p = f["properties"]
        P = (p["lv95_e"], p["lv95_n"]) if p.get("lv95_e") else None
        lvl, lvl_src = 0, "assumed street level (no level information)"
        if P:
            best = None
            for c in plat:
                if not c["levels"]:
                    continue
                d = geo.ring_distance(P, c["xy"]) if c["poly"] else geo.line_project(P, c["xy"])[0]
                ref_ok = bool(p.get("designation")) and p["designation"] in c["refs"]
                if d <= (25 if ref_ok else 4) and (best is None or (not ref_ok, d) < best[0]):
                    best = ((not ref_ok, d), c)
            if best:
                lvl = best[1]["levels"][0]
                lvl_src = f"OSM level tag of platform {osm_id(best[1]['el'])} (" + (
                    "same ref" if not best[0][0] else "nearest") + ")"
            elif p.get("osm_level"):
                lvl, lvl_src = parse_levels(p["osm_level"])[0], "OSM level tag of the matched platform"
        q = dict(p)
        q.update(level=lvl, level_source=lvl_src, focus_role=st_in[p["station_number"]]["role"])
        pc = PLAN_CHECKS.get(p["station_number"])
        if pc and p.get("designation"):
            on = p["designation"] in pc["letters_on_plan"]
            res = pc.get("position_check_result", {})
            pos = next((k for k in ("strict_match", "same_place_other_name", "same_junction_only") if p["designation"] in res.get(k, [])), None)
            q["plan_check"] = dict(plan=PLANS[pc["plan"]]["title"], plan_url=PLANS[pc["plan"]]["url"], checked="2026-11-21",
                                   letter_on_plan=on, street_on_plan=pc["streets"].get(p["designation"]), position=pos,
                                   how="kerb letter read off the operator's published kerb plan (schematic, not georeferenced); "
                                       "position = nearest named OSM street to the atlas point compared with the plan's street")
        out.append(dict(type="Feature", id=f["id"], geometry=f["geometry"], properties=q))
        rep["boarding_edge"] += 1
        if p["station_number"] in primary and f["geometry"] and p.get("designation"):
            cs = f["geometry"]["coordinates"]
            cs = [cs, cs] if f["geometry"]["type"] == "Point" else cs
            ln = [geo.wgs84_to_lv95(c[0], c[1]) for c in cs]
            core_lines.add(ln, ln)
            n_core += 1
    edge_level = {f["id"]: f["properties"]["level"] for f in out}

    # station core = within CORE_M of a public (designated) boarding edge of the primary stations
    def edge_dist(p, r):
        return min((geo.line_project(p, ln)[0] for ln in core_lines.near(p, r)), default=1e9)

    def in_core(p, r=CORE_M):
        if not n_core:
            return geo.dist(p, C) <= 120
        return edge_dist(p, r) <= r

    def zone(xy, r=CORE_M):
        step = max(1, len(xy) // 12)
        return "station_core" if in_core(centroid(xy), r) or any(in_core(q, r) for q in xy[::step]) else "surroundings"

    for f in feats_all:      # platform surfaces, shelters, sector markers and boards
        p = f["properties"]
        if p["station_number"] not in st_in:
            continue
        q = dict(p)
        if q.get("level") is None:
            lv = edge_level.get(p.get("edge_sloid") or (p.get("edge_sloids") or [None])[0])
            q["level"] = lv if lv is not None else 0
            q["level_source"] = "level of the linked boarding edge" if lv is not None else "assumed street level"
        q["focus_role"] = st_in[p["station_number"]]["role"]
        out.append(dict(type="Feature", id=f["id"], geometry=f["geometry"], properties=q))
        rep[p["feature_type"]] += 1

    # ---- cadastral survey (surveyed outlines) -------------------------------------------------
    av_under, av_tunnel, av_stairs, av_build = [], [], [], []
    bern_ok = os.path.exists(os.path.join(EXTRACT, "bern", "av-eo_unterirdisch.json"))
    if bern_ok:
        for f in read_json("bern/av-eo_unterirdisch.json")["features"]:
            for ring in esri_paths(f):
                ring = closed_ring(ring) or ring
                if len(ring) >= 3 and near(ring) and zone(ring) == "station_core":
                    a = f["attributes"]
                    av_under.append(ring)
                    out.append(feature(
                        gj_polygon(ring), id=f"{slug}:underground_structure:av-eo-{a['Objectid']}",
                        feature_type="underground_structure", focus_zone=zone(ring), level=None,
                        level_note="the cadastral survey records the outline only, not the storey; see OSM passages inside it",
                        area_m2=round(abs(geo.ring_area(ring)), 1), egid=a.get("U_egid"),
                        dim_quality="surveyed", geometry_quality="surveyed",
                        source=f"{AV_SRC}, Einzelobjekt 'Unterirdisches Gebaeude'", source_id=f"Objectid {a['Objectid']}",
                        licence=LICENCE["bern"], inferred=False))
                    rep["underground_structure"] += 1
        kinds = {"Tunnel, Unterführung, Galerie": "underpass_outline", "Wichtige Treppe": "stairs_outline",
                 "Unterstand": "canopy", "Bahnsteig": "platform_surface", "Brücke, Passerelle": "bridge_outline"}
        for name in ("av-eo_flaeche_linie", "av-eo_flaeche_bahnbruecke"):
            for f in read_json(f"bern/{name}.json")["features"]:
                a = f["attributes"]
                ft = kinds.get(a.get("Art_beschrieb"))
                if not ft:
                    continue
                for path in esri_paths(f):
                    if len(path) < 2 or not near(path):
                        continue
                    ring = closed_ring(path)
                    fid = f"{slug}:{ft}:av-eo-{a['Objectid']}"
                    if any(o["id"] == fid for o in out[-40:]):
                        fid += f"-{len(out)}"
                    z = zone(ring or path)
                    if z != "station_core":
                        continue
                    if ft == "canopy" and any(o["properties"].get("source_id") == f"Objectid {a['Objectid']}" for o in out):
                        continue          # already present as a stop shelter
                    props = dict(id=fid, feature_type=ft, focus_zone=z, level=None,
                                 level_note="storey not recorded in the cadastral survey",
                                 geometry_quality="surveyed", dim_quality="surveyed",
                                 source=f"{AV_SRC}, Einzelobjekt '{a['Art_beschrieb']}'",
                                 source_id=f"Objectid {a['Objectid']}", licence=LICENCE["bern"], inferred=False)
                    if ring:
                        r = geo.min_rect(ring)
                        props.update(area_m2=round(abs(geo.ring_area(ring)), 1), length_m=round(r["length"], 1),
                                     width_m=round(r["width"], 1))
                        if ft == "underpass_outline":
                            av_tunnel.append(ring)
                        if ft == "stairs_outline":
                            av_stairs.append(ring)
                        if ft == "canopy":
                            props.update(level=0, level_note=None, level_source="assumed street level", height_m=3.5,
                                         height_quality="approximate", height_note="nominal roof height, not measured")
                        if ft == "platform_surface":
                            props.update(level=0, level_note=None, level_source="assumed (open-air platform)")
                            linked = []           # boarding edges that run along this surveyed platform outline
                            closed = ring + [ring[0]]
                            for ef in out:
                                ep = ef["properties"]
                                if ep["feature_type"] != "boarding_edge" or not ef["geometry"] or ef["geometry"]["type"] != "LineString":
                                    continue
                                ln = [geo.wgs84_to_lv95(c[0], c[1]) for c in ef["geometry"]["coordinates"]]
                                LL = geo.line_length(ln)
                                ds = sorted(geo.line_project(geo.line_interpolate(ln, LL * k), closed)[0] for k in (0.25, 0.5, 0.75))
                                if ds[1] <= 2.0:
                                    linked.append(ep["edge_sloid"])
                            if linked:
                                props.update(edge_sloids=linked, edge_link_how="edge lines that run within 2 m of this outline")
                        out.append(feature(gj_polygon(ring), **props))
                    else:
                        props["length_m"] = round(geo.line_length(path), 1)
                        out.append(feature(gj_line(path), **props))
                    rep[ft] += 1
        for f in read_json("bern/av-bb_gebaeude.json")["features"]:
            a = f["attributes"]
            rings = [closed_ring(r) or r for r in esri_paths(f)]
            if not rings or not near(rings[0], R * 0.75):
                continue
            av_build.append(dict(ring=rings[0], oid=a["Objectid"], egid=a.get("EGID"), holes=rings[1:]))

    # ---- OSM: buildings (height tags), entrances, passages, stairs, lifts ---------------------
    station_buildings, bnodes = [], set()
    for el in osm:
        t = tags(el)
        if el["type"] == "way" and (t.get("building") in ("train_station", "transportation") or
                                    t.get("public_transport") == "station" or t.get("amenity") == "bus_station"):
            xy = osm_way_xy(el)
            if xy and near(xy, R * 0.8):
                station_buildings.append(dict(el=el, xy=xy))
                bnodes |= set(el.get("nodes", []))
    for b in av_build:
        role = None
        for sb in station_buildings:
            if geo.point_in_ring(centroid(sb["xy"]), b["ring"]) or geo.point_in_ring(centroid(b["ring"]), sb["xy"]):
                role = "station_building"
        z = zone(b["ring"], BUILDING_M)
        if z != "station_core" and not role:
            continue
        out.append(feature(
            gj_polygon(b["ring"], b["holes"]), id=f"{slug}:building_footprint:av-bb-{b['oid']}",
            feature_type="building_footprint", role=role, focus_zone=z, level=0, level_source="ground floor outline",
            egid=b["egid"], area_m2=round(abs(geo.ring_area(b["ring"])), 1), height_m=None, height_quality="missing",
            height_note="take roof heights from swissBUILDINGS3D (city3d folder) or the OSM building_part features",
            dim_quality="surveyed", geometry_quality="surveyed", source=f"{AV_SRC}, Bodenbedeckung 'Gebaeude'",
            source_id=f"Objectid {b['oid']}", licence=LICENCE["bern"], inferred=False))
        rep["building_footprint"] += 1

    for el in osm:
        t = tags(el)
        if el["type"] == "node" or not (t.get("building") or t.get("building:part")):
            continue
        for ring in osm_rings(el):
            if not near(ring, R * 0.75) or zone(ring, BUILDING_M) != "station_core":
                continue
            h = None
            try:
                h = float(str(t.get("height", "")).replace("m", "").strip())
            except ValueError:
                pass
            lv = None
            try:
                lv = float(t.get("building:levels"))
            except (TypeError, ValueError):
                pass
            hq = "source_derived" if h else ("approximate" if lv else "missing")
            is_roof = t.get("building") == "roof" or t.get("building:part") == "roof"
            mn = None
            try:
                mn = float(t.get("min_height"))
            except (TypeError, ValueError):
                pass
            out.append(feature(
                gj_polygon(ring), id=f"{slug}:{'roof' if is_roof else 'building_part'}:{osm_id(el)}",
                feature_type="roof" if is_roof else "building_part", focus_zone="station_core",
                building=t.get("building"), building_part=t.get("building:part"), name=t.get("name"),
                level=(parse_levels(t.get("level")) or [0])[0],
                level_source="OSM level tag" if t.get("level") else "assumed ground",
                height_m=h if h else (round(lv * 3.5, 1) if lv else None), min_height_m=mn,
                building_levels=lv, height_quality=hq,
                height_note=("OSM height tag" if h else "OSM building:levels x 3.5 m (nominal)" if lv else "no height in OSM"),
                roof_shape=t.get("roof:shape"), area_m2=round(abs(geo.ring_area(ring)), 1),
                geometry_quality="community", source="OpenStreetMap", source_id=osm_id(el), source_url=osm_url(el),
                licence=LICENCE["osm"], inferred=bool(lv and not h),
                inferred_how="height estimated from the OSM storey count" if (lv and not h) else None))
            rep["roof" if is_roof else "building_part"] += 1

    # walkable ways -> passages / stairs / escalators + graph
    walk = []
    for el in osm:
        t = tags(el)
        if el["type"] == "way" and t.get("highway") in WALK and t.get("access") not in ("private", "no"):
            xy = osm_way_xy(el)
            if len(xy) >= 2 and near(xy):
                walk.append(dict(el=el, xy=xy, t=t, levels=parse_levels(t.get("level")), inf=infer_level(t)))
    use = collections.Counter()
    for w in walk:
        for nid in w["el"].get("nodes", []):
            use[nid] += 1
    open_nodes = set()          # nodes on open-air, single-level surface ways
    for w in walk:
        t = w["t"]
        if not t.get("tunnel") and not t.get("indoor") and t.get("covered") in (None, "no") \
                and t.get("highway") != "steps" and w["levels"] in ([], [0]):
            open_nodes |= set(w["el"].get("nodes", []))

    node_levels = collections.defaultdict(set)
    for w in walk:
        t = w["t"]
        lv = w["levels"]
        if len(lv) == 1:
            single = lv[0]
        elif not lv and w["inf"]:
            single = w["inf"][0]
        elif not lv and not t.get("tunnel") and not t.get("indoor") and t.get("bridge") is None and t.get("highway") != "steps":
            single = 0          # untagged open-air way: street level
        else:
            continue
        for nid in w["el"].get("nodes", []):
            node_levels[nid].add(single)

    def orient(w):
        """Which end of a two-level way is on which level -> (from_level, to_level, how) along the line."""
        lv, ids = w["levels"], w["el"].get("nodes", [])
        if not lv and ids and w["t"].get("highway") == "steps":       # untagged steps: take the levels of both ends
            a, b = node_levels.get(ids[0], set()), node_levels.get(ids[-1], set())
            if len(a) == 1 and len(b) == 1 and a != b:
                return (min(a), min(b), "no level tag on the steps; levels taken from the ways at both ends "
                                        "(tagged, or inferred for tunnels and open-air ways)")
            return None
        if len(lv) != 2 or not ids:
            return None
        a = node_levels.get(ids[0], set()) & set(lv)
        b = node_levels.get(ids[-1], set()) & set(lv)
        if len(a) == 1 and len(b) == 1 and a != b:
            return (min(a), min(b), "both ends touch single-level OSM ways")
        if len(a) == 1 and len(b) != 1:
            x = min(a)
            return (x, lv[1] if x == lv[0] else lv[0], "start touches a single-level OSM way; the other end takes the other level")
        if len(b) == 1 and len(a) != 1:
            x = min(b)
            return (lv[1] if x == lv[0] else lv[0], x, "end touches a single-level OSM way; the other end takes the other level")
        inc = w["t"].get("incline")
        if inc in ("up", "down"):
            return (lv[0], lv[1], "OSM incline=up") if inc == "up" else (lv[1], lv[0], "OSM incline=down")
        return None

    def av_check(line):
        if not (av_under or av_tunnel):
            return None
        s = share_inside(line, av_under + av_tunnel)
        if s >= 0.6:
            return [dict(source=AV_SRC, match="line lies inside a surveyed underground-building or underpass outline",
                         share_inside=round(s, 2))]
        return None

    portals, struct_nodes = {}, set()
    for w in walk:
        t, xy, el = w["t"], w["xy"], w["el"]
        hw = t["highway"]
        is_area = t.get("area") == "yes" and geo.dist(xy[0], xy[-1]) < 0.01
        structural = (t.get("tunnel") in ("yes", "building_passage") or t.get("indoor") in ("yes", "corridor", "room")
                      or (w["levels"] and w["levels"] != [0]) or t.get("covered") == "yes" or t.get("bridge") == "yes"
                      or hw in ("steps", "corridor") or t.get("conveying"))
        if not structural:
            continue
        struct_nodes |= set(el.get("nodes", []))
        z = zone(xy)
        if hw == "steps":
            ft = "escalator" if t.get("conveying") else "stairs"
        elif t.get("conveying"):
            ft = "moving_walkway"
        elif len(w["levels"]) > 1:
            ft = "ramp_or_link"
        else:
            ft = "passage"
        if z != "station_core" and ft == "stairs" and not w["levels"] and not t.get("tunnel") and not t.get("indoor"):
            continue        # ordinary outdoor steps away from the station
        if z != "station_core" and ft == "passage" and not (t.get("tunnel") == "yes" or t.get("indoor") or (w["levels"] and w["levels"] != [0])):
            continue
        verified = None
        if ft in ("passage", "ramp_or_link", "moving_walkway") and (t.get("tunnel") == "yes" or (w["levels"] and min(w["levels"]) < 0)):
            verified = av_check(xy)
        if ft in ("stairs", "escalator") and av_stairs:
            c = geo.line_interpolate(xy, geo.line_length(xy) / 2)
            dmin = min(geo.ring_distance(c, r) for r in av_stairs)
            if dmin <= 2.5:
                verified = [dict(source=AV_SRC, match="midpoint within 2.5 m of a surveyed 'Wichtige Treppe' outline",
                                 dist_m=round(dmin, 1))]
        width = None
        try:
            width = float(str(t.get("width", "")).replace("m", "").strip())
        except ValueError:
            pass
        props = dict(
            id=f"{slug}:{ft}:{osm_id(el)}", feature_type=ft, focus_zone=z, name=t.get("name"),
            level=one_level(w["levels"]), levels=w["levels"] or None,
            level_source="OSM level tag" if w["levels"] else None,
            level_note=None if w["levels"] else "no level tag in OSM",
            tunnel=t.get("tunnel"), indoor=t.get("indoor"), covered=t.get("covered"), bridge=t.get("bridge"),
            conveying=t.get("conveying"), incline=t.get("incline"), step_count=t.get("step_count"),
            handrail=t.get("handrail"), ramp=t.get("ramp"), wheelchair=t.get("wheelchair"),
            surface=t.get("surface"), lit=t.get("lit"), opening_hours=t.get("opening_hours"),
            length_m=round(geo.line_length(xy), 1), width_m=width,
            width_quality="source_derived" if width else "missing",
            clear_height_m=None, clear_height_quality="missing",
            geometry_quality="community", source="OpenStreetMap", source_id=osm_id(el), source_url=osm_url(el),
            licence=LICENCE["osm"], inferred=False, verified_against=verified)
        if not w["levels"] and w["inf"]:
            props.update(level=w["inf"][0], levels=[w["inf"][0]], level_source="inferred", level_note=None,
                         inferred=True, inferred_how=w["inf"][1])
        o = orient(w) if ft in ("stairs", "escalator", "ramp_or_link", "moving_walkway") else None
        if o:
            props.update(from_level=o[0], to_level=o[1], inferred=True,
                         inferred_how=f"level at each end of the line (from_level -> to_level) derived from OSM topology: {o[2]}")
            if not w["levels"]:
                props.update(levels=sorted({o[0], o[1]}), level_source="inferred", level_note=None)
        elif len(w["levels"]) == 2:
            props["level_order_note"] = "which end is on which level could not be derived"
        if is_area:
            props["area_m2"] = round(abs(geo.ring_area(xy[:-1])), 1)
            out.append(feature(gj_polygon(xy[:-1]), **props))
        else:
            out.append(feature(gj_line(xy), **props))
        rep[ft] += 1
        # portals: where this structure meets an open-air surface way
        ids = el.get("nodes", [])
        for nid, q in ((ids[0], xy[0]), (ids[-1], xy[-1])) if ids and not is_area else ():
            if nid in open_nodes and nid not in portals:
                portals[nid] = dict(xy=q, via=ft, way=osm_id(el), name=t.get("name"), levels=w["levels"], zone=z)

    for el in osm:
        t = tags(el)
        if t.get("highway") != "elevator":
            continue
        xy = el_xy(el)
        if not xy or not near(xy):
            continue
        lv = parse_levels(t.get("level"))
        z = zone(xy)
        ring = (osm_rings(el) or [None])[0] if el["type"] != "node" else None
        out.append(feature(
            gj_polygon(ring) if ring else gj_point(centroid(xy)), id=f"{slug}:lift:{osm_id(el)}", feature_type="lift",
            focus_zone=z, name=t.get("name"), level=one_level(lv), levels=lv or None,
            level_source="OSM level tag" if lv else None, level_note=None if lv else "no level tag in OSM",
            wheelchair=t.get("wheelchair"), indoor=t.get("indoor"), operator=t.get("operator"),
            geometry_kind="shaft outline" if ring else "point",
            geometry_quality="community", source="OpenStreetMap", source_id=osm_id(el), source_url=osm_url(el),
            licence=LICENCE["osm"], inferred=False))
        rep["lift"] += 1

    av_rings = [b["ring"] for b in av_build]
    for el in osm:
        t = tags(el)
        if el["type"] != "node":
            continue
        rail_ent = t.get("railway") in ("train_station_entrance", "subway_entrance")
        ent = t.get("entrance")
        if not rail_ent and ent not in ("main", "yes", "exit", "entrance", "staircase"):
            continue
        if t.get("access") in ("private", "no", "customers"):
            continue
        P = osm_point(el)
        if geo.dist(P, C) > R:
            continue
        on_station = el["id"] in bnodes
        on_walk = el["id"] in struct_nodes
        if not (rail_ent or on_station or (on_walk and in_core(P))):
            continue
        verified = None
        if av_rings:
            dmin = min(geo.line_project(P, list(r) + [r[0]])[0] for r in av_rings)
            if dmin <= 1.5:
                verified = [dict(source=AV_SRC, match="within 1.5 m of a surveyed building outline", dist_m=round(dmin, 2))]
        lv = parse_levels(t.get("level"))
        out.append(feature(
            gj_point(P), id=f"{slug}:entrance:{osm_id(el)}", feature_type="entrance",
            focus_zone="station_core" if in_core(P) else "surroundings",
            entrance_class="station_entrance" if rail_ent else ent, name=t.get("name"), ref=t.get("ref"),
            on_station_building=on_station or None, on_passage_or_stairs=on_walk or None, level=one_level(lv) if lv else 0, levels=lv or None,
            level_source="OSM level tag" if lv else "assumed street level",
            wheelchair=t.get("wheelchair"), door=t.get("door"), automatic_door=t.get("automatic_door"),
            lv95_e=round(P[0], 2), lv95_n=round(P[1], 2),
            geometry_quality="community", source="OpenStreetMap", source_id=osm_id(el), source_url=osm_url(el),
            licence=LICENCE["osm"], inferred=False, verified_against=verified))
        rep["entrance"] += 1
    for nid, pt in portals.items():
        if any(o["properties"].get("source_id") == f"osm-node-{nid}" for o in out):
            continue
        lv = pt["levels"]
        out.append(feature(
            gj_point(pt["xy"]), id=f"{slug}:access_point:osm-node-{nid}", feature_type="access_point",
            focus_zone=pt["zone"], leads_to=pt["via"], leads_to_way=pt["way"], name=pt["name"],
            level=0, level_source="open-air end of the connecting way", connects_levels=lv or None,
            lv95_e=round(pt["xy"][0], 2), lv95_n=round(pt["xy"][1], 2),
            geometry_quality="community", source="OpenStreetMap", source_id=f"osm-node-{nid}",
            source_url=f"https://www.openstreetmap.org/node/{nid}", licence=LICENCE["osm"], inferred=True,
            inferred_how="derived from OSM topology: end node of a tunnel/indoor/stair way that also lies on an open-air surface way"))
        rep["access_point"] += 1

    # SBB point furniture (ticket machines, clocks) inside the radius
    for ds, ft, key in (("billetautomat", "ticket_machine", "id_automat"), ("haltestelle-uhr", "clock", "fid")):
        for r in read_json(f"sbb/{ds}.json"):
            if not r.get("geopos"):
                continue
            P = geo.wgs84_to_lv95(r["geopos"]["lon"], r["geopos"]["lat"])
            if geo.dist(P, C) > R:
                continue
            out.append(feature(
                gj_point(P), id=f"{slug}:{ft}:sbb-{r.get(key)}", feature_type=ft,
                focus_zone="station_core" if in_core(P) else "surroundings", level=None,
                level_note="the SBB register has no storey", kind=r.get("typ_text") or r.get("montage_an"),
                geometry_quality="official_point", source=f"SBB {ds}", source_id=str(r.get(key)),
                source_url=f"https://data.sbb.ch/explore/dataset/{ds}/", licence=LICENCE["sbb"], inferred=False))
            rep[ft] += 1

    # ---- level table ---------------------------------------------------------------------------------
    by_level = collections.defaultdict(list)
    for f in out:
        p = f["properties"]
        if p["feature_type"] == "boarding_edge" and p.get("atlas_height_m") and p.get("level") is not None \
                and (p["station_number"] in primary or in_core((p["lv95_e"], p["lv95_n"]))):
            by_level[p["level"]].append(p["atlas_height_m"])
    all_levels = sorted({lv for f in out for lv in ([f["properties"].get("level")] + (f["properties"].get("levels") or []))
                         if lv is not None})
    table = {}
    for lv in all_levels:
        if by_level.get(lv):
            hs = by_level[lv]
            table[lv] = dict(level=lv, elevation_m=round(statistics.median(hs), 1), elevation_min_m=min(hs),
                             elevation_max_m=max(hs), n_samples=len(hs), elevation_quality="source_derived",
                             elevation_source="median atlas height of the boarding edges on this level (LN02 assumed)")
    rejected = {}
    if 0 in table:
        z0 = table[0]["elevation_m"]
        for lv in list(table):
            z = table[lv]["elevation_m"]
            if (lv > 0 and z < z0 + 1.5 * lv) or (lv < 0 and z > z0 + 1.5 * lv):
                rejected[lv] = f"atlas heights of {table[lv]['n_samples']} edges on this level (median {z} m) rejected: not consistent with level 0 at {z0} m"
                del table[lv]
    # levels without usable atlas heights: measured heights of swissTLM3D paths that run along features of the
    # level (only heights on the right side of level 0 count, so a path on the ground under a bridge is ignored)
    if 0 in table:
        z0 = table[0]["elevation_m"]
        for lv in all_levels:
            if lv in table or lv == 0:
                continue
            zs, ids = [], set()
            for f in out:
                pr = f["properties"]
                if pr.get("level") != lv or pr["feature_type"] not in ("passage", "platform_surface", "boarding_edge") \
                        or not f["geometry"] or pr.get("level_source") == "inferred":
                    continue
                g = f["geometry"]
                cs = g["coordinates"] if g["type"] == "LineString" else (g["coordinates"][0] if g["type"] == "Polygon" else [g["coordinates"]])
                ln = [geo.wgs84_to_lv95(c[0], c[1]) for c in cs]
                L = geo.line_length(ln)
                for k in range(max(1, int(L / 5.0)) + 1):
                    q = geo.line_interpolate(ln, min(L, k * 5.0))
                    for z, tid in tlm_height(q):
                        if (lv > 0 and z >= z0 + 2.0) or (lv < 0 and z <= z0 - 2.0):
                            zs.append(z)
                            ids.add(tid)
            if len(zs) >= 3:
                table[lv] = dict(level=lv, elevation_m=round(statistics.median(zs), 1), elevation_min_m=round(min(zs), 1),
                                 elevation_max_m=round(max(zs), 1), n_samples=len(zs), elevation_quality="source_derived",
                                 elevation_source=f"median of {len(zs)} height samples on {len(ids)} paths: {TLM_NOTE}; "
                                                  "matched to the OSM features of this level within 3.5 m")
        # keep the table monotonic: a measured level that is not above the measured level below it is dropped
        for lv in sorted(k for k in table if k > 0):
            below = [table[k]["elevation_m"] for k in table if k < lv]
            if below and table[lv]["elevation_m"] <= max(below) + 1.0:
                del table[lv]
        for lv in sorted((k for k in table if k < 0), reverse=True):
            above = [table[k]["elevation_m"] for k in table if k > lv]
            if above and table[lv]["elevation_m"] >= min(above) - 1.0:
                del table[lv]
    known = sorted(table)
    for lv in all_levels:
        if lv in table:
            continue
        lower = [k for k in known if k < lv]
        upper = [k for k in known if k > lv]
        why = f". {rejected[lv]}" if lv in rejected else ""
        a, b = (max(lower), min(upper)) if lower and upper else (None, None)
        # between two known levels: interpolate, but only if they are ordinary storeys apart (2.5 to 7 m per level);
        # the deep RBS station two levels below the SBB tracks is not
        if a is not None and 2.5 <= (table[b]["elevation_m"] - table[a]["elevation_m"]) / (b - a) <= 7.0:
            za, zb = table[a]["elevation_m"], table[b]["elevation_m"]
            table[lv] = dict(level=lv, elevation_m=round(za + (zb - za) * (lv - a) / (b - a), 1), n_samples=0,
                             elevation_quality="approximate",
                             elevation_source=f"interpolated between level {a} ({za} m) and level {b} ({zb} m); not measured" + why)
        elif known:
            toward0 = [k for k in known if (lv < k <= 0) or (0 <= k < lv)]     # anchor on the level-0 side
            ref = min(toward0 or known, key=lambda k: abs(k - lv))
            table[lv] = dict(level=lv, elevation_m=round(table[ref]["elevation_m"] + (lv - ref) * STOREY, 1), n_samples=0,
                             elevation_quality="approximate",
                             elevation_source=f"nominal {STOREY} m per level from level {ref}; not measured" + why)
        else:
            table[lv] = dict(level=lv, elevation_m=None, n_samples=0, elevation_quality="missing", elevation_source=None)

    # terrain height (LN02) under open-air street-level points
    want = {}
    for f in out:
        p = f["properties"]
        if p["feature_type"] in ("boarding_edge", "entrance", "access_point") and p.get("lv95_e") and p.get("level") == 0:
            want[f["id"]] = (p["lv95_e"], p["lv95_n"])
    hts = terrain_heights(list(want.values()), network)
    for f in out:
        if f["id"] in want and hts.get(want[f["id"]]) is not None:
            f["properties"]["terrain_height_ln02_m"] = hts[want[f["id"]]]
            f["properties"]["terrain_height_source"] = "swisstopo height service (swissALTI3D DTM, LN02); terrain, not structure"
    for f in out:
        p = f["properties"]
        lv = p.get("level")
        if lv is not None and lv in table and table[lv]["elevation_m"] is not None:
            p["level_elevation_m"] = table[lv]["elevation_m"]
            p["level_elevation_quality"] = table[lv]["elevation_quality"]
        p["focus"] = slug

    # ---- walk graph -----------------------------------------------------------------------------------
    special = {f["properties"]["source_id"].split("-")[-1]: f["properties"]["feature_type"] for f in out
               if f["properties"].get("source_id", "").startswith("osm-node-")}
    # Graph ways: (1) OSM walkways of the detail extract, (2) service roads of the detail extract that are not
    # private, (3) public streets from the citywide road extract.  Streets make the graph connected where people
    # walk along or across a road; they are labelled kind="street" so a router can weight them.
    def ckey(g):
        return (round(g["lon"], 7), round(g["lat"], 7))

    gways, key2id = [], {}
    for w in walk:
        geom = [g for g in w["el"].get("geometry", []) if g]
        ids, t = w["el"].get("nodes", []), w["t"]
        if len(ids) != len(geom) or len(geom) != len(w["xy"]):
            continue
        ks = [ckey(g) for g in geom]
        key2id.update(zip(ks, ids))
        kind = ("escalator" if t.get("conveying") else "stairs") if t["highway"] == "steps" else (
            "moving_walkway" if t.get("conveying") else "walk")
        gways.append(dict(way=w["el"]["id"], keys=ks, xy=w["xy"], kind=kind, levels=w["levels"] or None, t=t))
    have_way = {g["way"] for g in gways}
    for el in osm:
        t = tags(el)
        if el["type"] == "way" and t.get("highway") == "service" and t.get("access") not in ("private", "no") \
                and t.get("foot") != "no" and el["id"] not in have_way:
            geom = [g for g in el.get("geometry", []) if g]
            xy = osm_way_xy(el)
            if len(geom) == len(xy) == len(el.get("nodes", [])) and len(xy) >= 2 and near(xy):
                ks = [ckey(g) for g in geom]
                key2id.update(zip(ks, el["nodes"]))
                gways.append(dict(way=el["id"], keys=ks, xy=xy, kind="street", levels=None, t=t))
                have_way.add(el["id"])
    for rd in roads().near(C, R + 50):
        if rd["tags"].get("highway") not in STREETS or rd["id"] in have_way or not near(rd["xy"]):
            continue
        gways.append(dict(way=rd["id"], keys=rd["keys"], xy=rd["xy"], kind="street", levels=None, t=rd["tags"]))
        have_way.add(rd["id"])
    usek = collections.Counter(k for g in gways for k in g["keys"])
    lift_ids = {nid for nid, n in nodes.items() if tags(n).get("highway") == "elevator"}

    def node_id(k):
        return key2id.get(k) or f"c{k[0]:.7f},{k[1]:.7f}"

    gn, ge = {}, []
    for g in gways:
        ks, xy, t = g["keys"], g["xy"], g["t"]
        start = 0
        for i in range(1, len(ks)):
            nid = node_id(ks[i])
            if i == len(ks) - 1 or usek[ks[i]] > 1 or str(nid) in special or nid in lift_ids:
                seg = xy[start:i + 1]
                for k in (ks[start], ks[i]):
                    n_id = node_id(k)
                    if n_id not in gn:
                        nt = tags(nodes.get(n_id, {})) if isinstance(n_id, int) else {}
                        gn[n_id] = dict(id=n_id, lon=k[0], lat=k[1],
                                        kind="lift" if nt.get("highway") == "elevator" else special.get(str(n_id)),
                                        levels=parse_levels(nt.get("level")) or None)
                ge.append(dict(id=f"{g['way']}:{start}", a=node_id(ks[start]), b=nid, way=g["way"], kind=g["kind"],
                               street_class=t.get("highway") if g["kind"] == "street" else None,
                               levels=g["levels"], length_m=round(geo.line_length(seg), 1),
                               tunnel=t.get("tunnel"), indoor=t.get("indoor"), covered=t.get("covered"),
                               conveying=t.get("conveying"), wheelchair=t.get("wheelchair"), name=t.get("name"),
                               coords=[list(k) for k in ks[start:i + 1]]))
                start = i
    # attach boarding edges to their nearest graph node
    gnodes = list(gn.values())
    gxy = {n["id"]: geo.wgs84_to_lv95(n["lon"], n["lat"]) for n in gnodes}
    for f in out:
        p = f["properties"]
        if p["feature_type"] != "boarding_edge" or not p.get("lv95_e") or not gnodes:
            continue
        P = (p["lv95_e"], p["lv95_n"])
        lv = p.get("level")
        cands = [n for n in gnodes if lv is None or n["levels"] is None or lv in n["levels"]]
        # prefer nodes whose incident edges are on the same level
        lvl_nodes = {e[k] for e in ge for k in ("a", "b") if (e["levels"] or [0]) == [lv]} if lv is not None else set()
        pool = [n for n in cands if n["id"] in lvl_nodes] or cands
        n = min(pool, key=lambda n: geo.dist(P, gxy[n["id"]]))
        p["walk_graph_node"] = n["id"]
        p["walk_graph_node_dist_m"] = round(geo.dist(P, gxy[n["id"]]), 1)
        p["walk_graph_node_how"] = "nearest walk-graph node on the same level (inferred link, not a surveyed access)"
    graph = dict(
        focus=slug, generated_utc=NOW, licence=LICENCE["osm"], source="OpenStreetMap ways: " + ", ".join(WALK) + "; streets: service, " + ", ".join(STREETS),
        note="Community data. Edges are OSM way stretches between junctions; 'levels' is the OSM level tag "
             "(two values on stairs/escalators/ramps = connects those levels; null = street level). Lift nodes carry "
             "their levels. kind 'street' = road centreline (street_class), walkable along a pavement that OSM does "
             "not map separately; crossing a road is only modelled where OSM has a footway crossing it. Node ids are "
             "OSM node ids, or 'c<lon>,<lat>' where the road extract carries no ids.",
        nodes=gnodes, edges=ge)
    with open(os.path.join(DATA, "focus", f"{slug}.walk_graph.json"), "w", encoding="utf-8") as fh:
        json.dump(graph, fh, ensure_ascii=False, separators=(",", ":"))

    # de-duplicate ids, write
    seen = collections.Counter()
    for f in out:
        seen[f["id"]] += 1
        if seen[f["id"]] > 1:
            f["id"] = f["properties"]["id"] = f"{f['id']}#{seen[f['id']]}"
    centre = geo.lv95_to_wgs84(*C)
    meta = dict(focus=slug, title=cfg["title"], tier=cfg["tier"], generated_utc=NOW, centre=[round(centre[0], 7), round(centre[1], 7)],
                radius_m=R, stations=list(st_in.values()), levels=[table[k] for k in sorted(table)],
                level_convention="OSM level numbers: 0 = street/main platform level, negative = below",
                heights="metres above sea level, LN02 (atlas heights assumed LN02; terrain from swissALTI3D)",
                crs="EPSG:4326 (lon, lat); LV95 kept as properties where the source has it",
                licence="mixed per feature (see 'licence'); OSM-derived features are ODbL",
                builder="bern-research/stations/tools/build_focus.py")
    write_geojson(os.path.join(DATA, "focus", f"{slug}.geojson"), out, meta)
    by_lvl = collections.Counter()
    for f in out:
        p = f["properties"]
        by_lvl[(p["feature_type"], "none" if p.get("level") is None and not p.get("levels") else
                str(p.get("level") if p.get("level") is not None else p.get("levels")))] += 1
    quality = collections.Counter(f["properties"].get("geometry_quality", "?") for f in out)
    verified = collections.Counter(f["properties"]["feature_type"] for f in out if f["properties"].get("verified_against"))
    return dict(slug=slug, title=cfg["title"], stations=list(st_in.values()), levels=[table[k] for k in sorted(table)],
                features=len(out), by_type=dict(rep), by_geometry_quality=dict(quality),
                cross_checked_by_type=dict(verified), inferred=sum(1 for f in out if f["properties"].get("inferred")),
                walk_graph=dict(nodes=len(gnodes), edges=len(ge)),
                by_type_and_level={f"{k[0]}@{k[1]}": v for k, v in sorted(by_lvl.items())})


def main() -> int:
    network = "--no-network" not in sys.argv
    edges_all = json.load(open(os.path.join(DATA, "boarding_edges.geojson"), encoding="utf-8"))["features"]
    feats_all = json.load(open(os.path.join(DATA, "station_features.geojson"), encoding="utf-8"))["features"]
    os.makedirs(os.path.join(DATA, "focus"), exist_ok=True)
    areas = focus_areas()
    for old in os.listdir(os.path.join(DATA, "focus")):        # drop outputs of areas no longer selected
        if old.split(".")[0] not in areas and old != "index.json":
            os.remove(os.path.join(DATA, "focus", old))
    index = dict(generated_utc=NOW, selection=dict(
        tier_1="priority stations set by hand: " + ", ".join(k for k, v in areas.items() if v["tier"] == 1),
        tier_2="rule: every atlas rail station in the study area and every tram/bus stop with at least 4 lettered kerbs, "
               "unless it already lies inside another focus area (see tools/common.py focus_areas)"),
        focus=[dict(build(slug, cfg, edges_all, feats_all, network), tier=cfg["tier"],
                    selected_because=cfg.get("selected_because", "priority station")) for slug, cfg in areas.items()])
    with open(os.path.join(DATA, "focus", "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1, ensure_ascii=False)
    for s in index["focus"]:
        print(f"{s['tier']} {s['slug']}: {s['features']} features, levels {[l['level'] for l in s['levels']]}, "
              f"{s['by_geometry_quality']}, graph {s['walk_graph']['nodes']} nodes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
