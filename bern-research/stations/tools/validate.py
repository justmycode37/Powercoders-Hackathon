#!/usr/bin/env python3
"""Validate the station outputs and write validation/report.md + report.json.

Checks schema and honesty flags, coordinates, distances of edge-linked geometry
to the atlas edge point, independent cross-checks between sources (SBB kerb
points vs OSM platforms, atlas vs Stadt Bern kerb letters, atlas vs SBB lengths),
level tables, walk graphs and the GLB files.

Usage: python tools/validate.py      (exit code 1 if any check FAILs)
"""
from __future__ import annotations

import collections
import datetime as dt
import glob
import json
import os
import struct
import sys

import geo
from common import DATA, ROOT, osm_rings, read_json

BOX = (7.30, 46.88, 7.56, 47.01)       # lon/lat box all features must lie in
MAX_EDGE_OFFSET = 15.0                 # stated limit: edge geometry vs atlas edge point (m)
REQ = ("id", "feature_type", "source", "inferred")
results = []


def check(level, name, detail, data=None):
    results.append(dict(level=level, check=name, detail=detail, data=data))


def pct(v, q):
    v = sorted(v)
    return round(v[min(len(v) - 1, int(len(v) * q))], 2) if v else None


def coords(g):
    if g is None:
        return []
    c = g["coordinates"]
    if g["type"] == "Point":
        return [c]
    if g["type"] == "LineString":
        return c
    if g["type"] == "Polygon":
        return [p for r in c for p in r]
    return []


def lv(c):
    return geo.wgs84_to_lv95(c[0], c[1])


def schema(path, feats, need_station=True):
    name = os.path.relpath(path, ROOT).replace("\\", "/")
    ids = collections.Counter(f.get("id") for f in feats)
    dup = [k for k, v in ids.items() if v > 1]
    check("FAIL" if dup else "OK", f"{name}: unique ids", f"{len(feats)} features, {len(dup)} duplicate ids", dup[:5])
    miss = collections.Counter()
    bad_inf = bad_box = bad_dec = no_lic = no_station = bad_geom = 0
    for f in feats:
        p = f["properties"]
        for k in REQ:
            if p.get(k) is None:
                miss[k] += 1
        if p.get("inferred") is True and not p.get("inferred_how"):
            bad_inf += 1
        if not p.get("licence"):
            no_lic += 1
        if need_station and not (p.get("station_sloid") and p.get("station_number")):
            no_station += 1
        g = f["geometry"]
        if g is not None and g["type"] not in ("Point", "LineString", "Polygon"):
            bad_geom += 1
        if g is not None and g["type"] == "Polygon" and any(r[0] != r[-1] or len(r) < 4 for r in g["coordinates"]):
            bad_geom += 1
        for c in coords(g):
            if not (BOX[0] <= c[0] <= BOX[2] and BOX[1] <= c[1] <= BOX[3]):
                bad_box += 1
            if any(round(x, 7) != x for x in c[:2]):
                bad_dec += 1
    check("FAIL" if miss else "OK", f"{name}: required properties {REQ}", f"missing: {dict(miss) or 'none'}")
    check("FAIL" if bad_inf else "OK", f"{name}: inferred=true carries inferred_how", f"{bad_inf} without")
    check("FAIL" if no_lic else "OK", f"{name}: licence on every feature", f"{no_lic} without")
    if need_station:
        check("FAIL" if no_station else "OK", f"{name}: station_sloid + station_number", f"{no_station} without")
    check("FAIL" if bad_box or bad_geom else "OK", f"{name}: geometry valid and inside the Bern box {BOX}",
          f"{bad_box} vertices outside, {bad_geom} invalid geometries")
    check("FAIL" if bad_dec else "OK", f"{name}: coordinates rounded to 7 decimals", f"{bad_dec} vertices with more")
    osm_bad = sum(1 for f in feats if "OpenStreetMap" in (f["properties"].get("source") or "")
                  and "ODbL" not in (f["properties"].get("licence") or ""))
    check("FAIL" if osm_bad else "OK", f"{name}: OSM-derived features say ODbL", f"{osm_bad} without")


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    edges = load(os.path.join(DATA, "boarding_edges.geojson"))["features"]
    feats = load(os.path.join(DATA, "station_features.geojson"))["features"]
    stations = load(os.path.join(DATA, "stations.geojson"))["features"]
    schema(os.path.join(DATA, "boarding_edges.geojson"), edges)
    schema(os.path.join(DATA, "station_features.geojson"), feats)
    schema(os.path.join(DATA, "stations.geojson"), stations)

    # ---- every edge has a station; edge-linked geometry is close to the atlas point ----------------
    st_ids = {s["properties"]["station_sloid"] for s in stations}
    orphan = [e["id"] for e in edges if e["properties"]["station_sloid"] not in st_ids]
    check("FAIL" if orphan else "OK", "every boarding edge has its station in stations.geojson", f"{len(orphan)} orphans", orphan[:5])
    by_method = collections.defaultdict(list)
    far, unflagged_far = [], []
    for e in edges:
        p = e["properties"]
        if e["geometry"] is None or p.get("lv95_e") is None:
            continue
        P = (p["lv95_e"], p["lv95_n"])
        cs = [lv(c) for c in coords(e["geometry"])]
        d = geo.dist(P, cs[0]) if len(cs) == 1 else geo.line_project(P, cs)[0]
        by_method[p["geometry_method"]].append(d)
        if d > MAX_EDGE_OFFSET and not p.get("atlas_position_conflict"):
            unflagged_far.append((e["id"], round(d, 1)))
        if abs(d - p["dist_atlas_to_geometry_m"]) > 0.05:
            far.append((e["id"], "stored distance differs from recomputed", round(d, 2)))
        if d > 5.0:
            far.append((e["id"], p["station_name"], p.get("designation"), round(d, 1),
                        p.get("atlas_position_conflict") or p["geometry_method"]))
    check("FAIL" if unflagged_far else "OK",
          f"edge geometry lies within {MAX_EDGE_OFFSET} m of the atlas edge point, except edges flagged "
          f"atlas_position_conflict (recomputed from the GeoJSON); unflagged beyond: {len(unflagged_far)}",
          "; ".join(f"{m}: n={len(v)}, median {pct(v, .5)} m, p95 {pct(v, .95)} m, max {round(max(v), 2)} m"
                    for m, v in sorted(by_method.items())),
          dict(edges_over_5m=[f for f in far if len(f) == 5]))
    n5 = sum(1 for f in far if len(f) == 5)
    check("WARN" if n5 else "OK", "edges more than 5 m from their atlas point", f"{n5} edges (listed in report.json)")
    conflicts = [e for e in edges if e["properties"].get("atlas_position_conflict")]
    check("WARN" if conflicts else "OK", "atlas coordinate sits on a different SBB track than its track number",
          f"{len(conflicts)} edges: " + ", ".join(
              f"{e['properties']['station_name']} {e['properties']['designation']} ({e['id']}, "
              f"{e['properties']['dist_atlas_to_geometry_m']} m)" for e in conflicts))
    nogeo = [e["id"] for e in edges if e["geometry"] is None]
    check("WARN" if nogeo else "OK", "edges without any geometry (atlas publishes no coordinates)", f"{len(nogeo)} edges", nogeo)
    meth = collections.Counter(e["properties"]["geometry_method"] for e in edges)
    check("OK", "boarding edges by geometry method", str(dict(meth)))

    for ft, key, lim in (("sector_marker", "dist_to_edge_m", 12.0), ("sector_board", "dist_to_edge_m", 12.0),
                         ("shelter", "dist_to_edge_m", 9.0)):
        ds = [f["properties"][key] for f in feats if f["properties"]["feature_type"] == ft and f["properties"].get(key) is not None]
        n_all = sum(1 for f in feats if f["properties"]["feature_type"] == ft)
        over = sum(1 for d in ds if d > lim)
        check("WARN" if over else "OK", f"{ft}: distance to the linked edge line <= {lim} m",
              f"{len(ds)} of {n_all} linked; median {pct(ds, .5)} m, p95 {pct(ds, .95)} m, max {max(ds) if ds else None} m; {over} over")
    edge_ids = {e["id"] for e in edges}
    dangling = [f["id"] for f in feats for s in ([f["properties"].get("edge_sloid")] + (f["properties"].get("edge_sloids") or []))
                if s and s not in edge_ids]
    check("FAIL" if dangling else "OK", "edge_sloid references in station_features resolve to boarding_edges", f"{len(dangling)} dangling", dangling[:5])

    # ---- independent cross-checks ---------------------------------------------------------------------
    # (a) SBB surveyed kerb line vs the nearest OSM rail platform polygon boundary
    try:
        polys = []
        for el in read_json("osm/city-transit.json")["elements"]:
            t = el.get("tags", {})
            if t.get("railway") == "platform" and el["type"] != "node":
                polys += osm_rings(el)
        ds = []
        for e in edges:
            if e["properties"]["geometry_method"] != "sbb_behig_kerb_points":
                continue
            line = [lv(c) for c in coords(e["geometry"])]
            L = geo.line_length(line)
            for k in range(1, 10):
                q = geo.line_interpolate(line, L * k / 10)
                best = min((geo.line_project(q, r + [r[0]])[0] for r in polys
                            if abs(r[0][0] - q[0]) < 600 and abs(r[0][1] - q[1]) < 600), default=None)
                if best is not None and best < 25:
                    ds.append(best)
        check("OK" if ds and pct(ds, .5) <= 1.0 else "WARN",
              "SBB surveyed kerb lines agree with OSM rail platform outlines (two independent sources)",
              f"{len(ds)} sample points: median {pct(ds, .5)} m, p90 {pct(ds, .9)} m, p99 {pct(ds, .99)} m between the "
              f"SBB kerb line and the nearest OSM platform boundary")
    except FileNotFoundError:
        check("WARN", "SBB vs OSM platform cross-check", "skipped: .cache extracts not present")

    # (b) kerb letters: atlas vs Stadt Bern
    ver = [v for e in edges for v in (e["properties"].get("verified_against") or [])]
    same = [v["dist_m"] for v in ver if "kerb letter" in v["match"]]
    lettered_city = sum(1 for e in edges if e["properties"].get("designation") and e["properties"].get("transit_tier") == "bern"
                        and "TRAIN" not in (e["properties"].get("station_modes") or ""))
    check("OK", "kerb letters confirmed by Stadt Bern kerb points (same station number and letter)",
          f"{len(same)} edges confirmed (of {lettered_city} lettered tram/bus edges in the municipality); distance atlas point to "
          f"city kerb point: median {pct(same, .5)} m, p95 {pct(same, .95)} m, max {max(same) if same else None} m")

    # (b2) surveyed pavement boundaries next to OSM-based and constructed edges
    kc = [f["properties"] for f in feats if f["properties"]["feature_type"] == "surveyed_kerb_candidate"]
    for m in ("osm_platform", "constructed"):
        v = [k["mean_offset_m"] for k in kc if k["edge_geometry_method"] == m]
        n_m = sum(1 for e in edges if e["properties"]["geometry_method"] == m)
        check("OK", f"surveyed pavement boundary found next to {m} edges (cadastral survey, city of Bern only)",
              f"{len(v)} of {n_m} edges; mean offset between the edge line and the surveyed boundary: median {pct(v, .5)} m, "
              f"p90 {pct(v, .9)} m" + (f"; {sum(1 for x in v if x <= 1.0)} within 1 m" if m == "osm_platform" else ""))

    # (c) edge length: geometry vs atlas length
    ratios = [(e["properties"]["length_m"] / e["properties"]["atlas_length_m"], e["id"]) for e in edges
              if e["properties"]["geometry_method"] == "sbb_behig_kerb_points" and e["properties"].get("atlas_length_m")]
    off = [(i, round(r, 2)) for r, i in ratios if abs(r - 1) > 0.1]
    check("WARN" if off else "OK", "surveyed edge length vs atlas length (within 10 %)",
          f"{len(ratios)} edges compared, {len(off)} differ by more than 10 %", off)

    # ---- focus stations -----------------------------------------------------------------------------------
    for path in sorted(glob.glob(os.path.join(DATA, "focus", "*.geojson"))):
        slug = os.path.basename(path)[:-8]
        fc = load(path)
        ff = fc["features"]
        schema(path, ff, need_station=False)
        lvls = fc["metadata"]["levels"]
        mono = all(a["elevation_m"] < b["elevation_m"] for a, b in zip(lvls, lvls[1:]) if a["elevation_m"] and b["elevation_m"])
        check("OK" if mono else "FAIL", f"focus/{slug}: level elevations increase with level number",
              ", ".join(f"L{l['level']}={l['elevation_m']} m ({l['elevation_quality']})" for l in lvls))
        conn = [f for f in ff if f["properties"]["feature_type"] in ("stairs", "escalator", "lift", "ramp_or_link")]
        nolevel = sum(1 for f in conn if not f["properties"].get("levels") and f["properties"].get("level") is None)
        check("WARN" if nolevel else "OK", f"focus/{slug}: vertical connectors carry level information",
              f"{len(conn)} stairs/escalators/lifts/ramps, {nolevel} without any level tag in OSM")
        ter = [(f["properties"]["terrain_height_ln02_m"] - f["properties"]["atlas_height_m"], f["id"]) for f in ff
               if f["properties"]["feature_type"] == "boarding_edge" and f["properties"].get("terrain_height_ln02_m") is not None
               and f["properties"].get("atlas_height_m") is not None]
        if ter:
            big = [(i, round(d, 1)) for d, i in ter if abs(d) > 2.0]
            check("WARN" if big else "OK", f"focus/{slug}: atlas edge height vs swissALTI3D terrain at street level (within 2 m)",
                  f"{len(ter)} level-0 edges, median difference {pct([d for d, _ in ter], .5)} m, {len(big)} beyond 2 m", big)
        cc = collections.Counter(f["properties"]["feature_type"] for f in ff if f["properties"].get("verified_against"))
        tot = collections.Counter(f["properties"]["feature_type"] for f in ff)
        check("OK", f"focus/{slug}: features confirmed by a second source",
              ", ".join(f"{k} {cc[k]}/{tot[k]}" for k in ("passage", "stairs", "escalator", "ramp_or_link", "entrance", "boarding_edge") if tot[k]))
        # walk graph
        g = load(os.path.join(DATA, "focus", f"{slug}.walk_graph.json"))
        ids = {n["id"] for n in g["nodes"]}
        bad = sum(1 for e in g["edges"] if e["a"] not in ids or e["b"] not in ids)
        parent = {i: i for i in ids}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x
        for e in g["edges"]:
            if e["a"] in ids and e["b"] in ids:
                parent[find(e["a"])] = find(e["b"])
        comp = collections.Counter(find(i) for i in ids)
        big = comp.most_common(1)[0][1] if comp else 0
        att = [f["properties"]["walk_graph_node_dist_m"] for f in ff if f["properties"].get("walk_graph_node_dist_m") is not None]
        check("FAIL" if bad else "OK", f"focus/{slug}: walk graph is consistent",
              f"{len(ids)} nodes, {len(g['edges'])} edges, {len(comp)} components, largest holds {round(100 * big / max(1, len(ids)))} % of nodes; "
              f"boarding edges attach at median {pct(att, .5)} m, max {max(att) if att else None} m")

    # ---- models -------------------------------------------------------------------------------------------------
    for path in sorted(glob.glob(os.path.join(ROOT, "models", "**", "*.glb"), recursive=True)):
        name = os.path.relpath(path, ROOT).replace("\\", "/")
        b = open(path, "rb").read()
        ok, why = True, ""
        try:
            magic, ver_, total = struct.unpack("<III", b[:12])
            jl, jt = struct.unpack("<II", b[12:20])
            gl = json.loads(b[20:20 + jl])
            bl, bt = struct.unpack("<II", b[20 + jl:28 + jl])
            binb = b[28 + jl:28 + jl + bl]
            assert magic == 0x46546C67 and ver_ == 2 and total == len(b) and jt == 0x4E4F534A and bt == 0x004E4942
            tris = 0
            for m in gl["meshes"]:
                pr = m["primitives"][0]
                pa, ia = gl["accessors"][pr["attributes"]["POSITION"]], gl["accessors"][pr["indices"]]
                iv = gl["bufferViews"][ia["bufferView"]]
                idx = struct.unpack(f"<{ia['count']}I", binb[iv["byteOffset"]:iv["byteOffset"] + ia["count"] * 4])
                assert ia["count"] % 3 == 0 and max(idx) < pa["count"]
                tris += ia["count"] // 3
            side = load(os.path.splitext(path)[0] + ".model.json")
            assert side["triangles"] == tris and "frame" in side and "origin_lv95_e" in side["frame"]
            why = f"{len(b)} bytes, {tris} triangles, {len(gl['nodes'])} nodes; sidecar states frame, origin and {len(side['approximations'])} kinds of approximation"
            if side.get("source_geojson", "").startswith("data/focus/"):
                gj_ids = {f["id"] for f in load(os.path.join(ROOT, side["source_geojson"]))["features"]}
                missing = [x["id"] for x in side["feature_index"] if x["id"] not in gj_ids]
                assert not missing, f"{len(missing)} feature ids not in the GeoJSON"
        except Exception as ex:  # noqa: BLE001
            ok, why = False, f"invalid: {ex}"
        check("OK" if ok else "FAIL", f"{name}: valid GLB 2.0 with sidecar", why)

    # ---- sizes, manifest ---------------------------------------------------------------------------------------------
    big = []
    for dp, dn, fn in os.walk(ROOT):
        dn[:] = [d for d in dn if d not in (".cache", "__pycache__")]
        for f in fn:
            sz = os.path.getsize(os.path.join(dp, f))
            if sz > 25 * 1024 * 1024:
                big.append((os.path.relpath(os.path.join(dp, f), ROOT), sz))
    check("FAIL" if big else "OK", "no committable file above 25 MB", f"{len(big)} too large", big)
    src_path = os.path.join(ROOT, "SOURCES.json")
    if os.path.exists(src_path):
        src = load(src_path)["sources"]
        need = ("name", "url", "publisher", "licence", "retrieved", "bytes", "sha256", "used_for")
        bad = [s.get("name") for s in src if any(not s.get(k) for k in need)]
        check("FAIL" if bad else "OK", "SOURCES.json: every input has " + ", ".join(need), f"{len(src)} inputs, {len(bad)} incomplete", bad)
    else:
        check("FAIL", "SOURCES.json exists", "missing")

    # ---- write --------------------------------------------------------------------------------------------------------
    counts = collections.Counter(r["level"] for r in results)
    out = os.path.join(ROOT, "validation")
    os.makedirs(out, exist_ok=True)
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(os.path.join(out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(dict(generated_utc=now, summary=dict(counts), results=results), f, indent=1, ensure_ascii=False)
    with open(os.path.join(out, "report.md"), "w", encoding="utf-8") as f:
        f.write(f"# stations/ validation report\n\nGenerated {now} by `python tools/validate.py`. "
                f"**{counts.get('FAIL', 0)} FAIL, {counts.get('WARN', 0)} WARN, {counts.get('OK', 0)} OK.** "
                f"Lists that are cut short here are complete in `report.json`.\n\n")
        for r in results:
            f.write(f"- **{r['level']}** {r['check']}: {r['detail']}\n")
    print(f"{counts.get('FAIL', 0)} FAIL, {counts.get('WARN', 0)} WARN, {counts.get('OK', 0)} OK -> validation/report.md")
    for r in results:
        if r["level"] != "OK":
            print(f"  {r['level']} {r['check']}: {r['detail']}"[:400])
    return 1 if counts.get("FAIL") else 0


if __name__ == "__main__":
    sys.exit(main())
