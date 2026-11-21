#!/usr/bin/env python3
"""Citywide boarding-edge geometry for the Bern study area.

For every atlas boarding edge (traffic point element) this picks the best
available line geometry and says where it came from:

  surveyed     SBB BehiG kerb points (1 m spacing, LV95) chained into a line
  community    OSM platform way/polygon matched by proximity (+ ref letter)
  constructed  line of default length through the atlas point along the atlas
               compass direction (or the nearest track) - approximate
  point_only   nothing but the atlas coordinate

Outputs (data/): boarding_edges.geojson, station_features.geojson (platform
surfaces, shelters, sector markers), stations.geojson, build-report.json.

Usage: python tools/build_geometry.py
"""
from __future__ import annotations

import collections
import datetime as dt
import json
import math
import os

import geo
from common import (DATA, LICENCE, ROOT, Grid, closed_ring, esri_paths, feature, fnum, gj_line, gj_point,
                    gj_polygon, osm_id, osm_point, osm_rings, osm_url, osm_way_xy, parse_levels,
                    read_csv, read_json, strip_html, write_geojson)

NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Defaults used only for constructed (approximate) geometry.  Vehicle lengths:
# BERNMOBIL trams are about 42 m, articulated buses 18 m; values are nominal.
DEFAULT_LEN = {"tram": 42.0, "bus": 18.0, "rail": 150.0, "other": 15.0}
DEFAULT_WIDTH = {"tram": 3.0, "bus": 2.5, "rail": 6.0, "other": 2.5}
MATCH_RADIUS_STREET = 15.0
MATCH_RADIUS_RAIL = 30.0


def chain_points(pts):
    """Order unordered edge points (1 m spacing) into a polyline: greedy nearest
    neighbour starting from one end of the principal axis."""
    xy = sorted(set(pts))
    if len(xy) < 2:
        return xy
    r = geo.min_rect(xy)
    b = math.radians(r["bearing"])
    ux, uy = math.sin(b), math.cos(b)
    start = min(xy, key=lambda p: p[0] * ux + p[1] * uy)
    left = set(xy)
    left.discard(start)
    line = [start]
    while left:
        cur = line[-1]
        nxt = min(left, key=lambda p: (p[0] - cur[0]) ** 2 + (p[1] - cur[1]) ** 2)
        left.discard(nxt)
        line.append(nxt)
    return line


def polygon_side(ring, ref_pt):
    """Split a platform polygon at the two ends of its long axis and return the
    side (chain of boundary vertices) nearest to ref_pt."""
    r = geo.min_rect(ring)
    b = math.radians(r["bearing"])
    ux, uy = math.sin(b), math.cos(b)
    proj = [p[0] * ux + p[1] * uy for p in ring]
    i0, i1 = proj.index(min(proj)), proj.index(max(proj))
    n = len(ring)

    def walk(a, z):
        out, i = [ring[a]], a
        while i != z:
            i = (i + 1) % n
            out.append(ring[i])
        return out

    a, b_ = walk(i0, i1), walk(i1, i0)[::-1]
    da = geo.line_project(ref_pt, a)[0] if len(a) > 1 else 1e9
    db = geo.line_project(ref_pt, b_)[0] if len(b_) > 1 else 1e9
    return (a, da, db) if da <= db else (b_, db, da)


def main() -> int:
    sp_rows = read_csv("atlas/service-point.csv")
    sp = {r["sloid"]: r for r in sp_rows}
    tp = read_csv("atlas/traffic-point.csv")
    sectors = read_csv("atlas/sectors.csv")
    prm = {r["sloid"]: r for r in read_csv("atlas/prm-platform.csv")}
    areas = {r["sloid"]: r for r in tp if r["trafficPointElementType"] == "BOARDING_AREA"}

    # Reconcile with the transit folder's edge list when it is there (read-only).  Edges it has for
    # stations in our area that our atlas download lacks (other validity dates) are added as rows.
    transit, transit_path = {}, os.path.join(ROOT, "..", "transit", "data", "edges.geojson")
    if os.path.exists(transit_path):
        have = {r["sloid"] for r in tp}
        for f in json.load(open(transit_path, encoding="utf-8"))["features"]:
            q = f["properties"]
            transit[q["sloid"]] = q
            if q["sloid"] in have or q.get("type") != "BOARDING_PLATFORM" or q.get("tier") != "bern":
                continue
            if q["station_sloid"] not in sp:
                sp[q["station_sloid"]] = dict(
                    sloid=q["station_sloid"], number=str(q["station_number"]), designationOfficial=q["station_name"],
                    meansOfTransport="", stopPoint="unknown", abbreviation="", businessOrganisationAbbreviationDe="",
                    municipalityName="", lv95East=q.get("lv95_e") or "", lv95North=q.get("lv95_n") or "", height="",
                    _from_transit=True)
                sp_rows.append(sp[q["station_sloid"]])
            ll = geo.lv95_to_wgs84(q["lv95_e"], q["lv95_n"]) if q.get("lv95_e") else (None, None)
            tp.append(dict(
                sloid=q["sloid"], trafficPointElementType="BOARDING_PLATFORM", parentSloidServicePoint=q["station_sloid"],
                designation=q.get("designation") or "", designationOperational=q.get("designation_operational") or "",
                parentSloid=q.get("area_sloid") or "", lv95East=q.get("lv95_e") or "", lv95North=q.get("lv95_n") or "",
                wgs84East=ll[0] or "", wgs84North=ll[1] or "", height=q.get("height_m") or "",
                length=q.get("length_m") or "", boardingAreaHeight=q.get("boarding_area_height_cm") or "",
                compassDirection=q.get("compass_direction_deg") if q.get("compass_direction_deg") is not None else "",
                validFrom=q.get("valid_from") or "", editionDate=q.get("edition_date") or "", _from_transit=True))

    # ---- SBB surveyed kerb lines ------------------------------------------------
    groups = collections.defaultdict(list)
    for p in read_json("sbb/21196_behig-haltekantepunkt.json"):
        groups[int(p["haltekante_fid"])].append(p)
    sbb_lines = []
    for fid, ps in groups.items():
        cls = {(round(p["e"], 2), round(p["n"], 2)): p["konformitaet"].split(" /")[0].strip() for p in ps}
        chained = chain_points(list(cls))
        parts, cur = [], chained[:1]
        for q in chained[1:]:            # a published edge can consist of separate stretches
            if geo.dist(cur[-1], q) > 5.0:
                parts.append(cur)
                cur = []
            cur.append(q)
        parts.append(cur)
        parts = [pt for pt in parts if len(pt) >= 2]
        for k, line in enumerate(parts):
            prof, run = [], 0.0          # kerb height class along the edge
            for i, q in enumerate(line):
                if i:
                    run += geo.dist(line[i - 1], q)
                c = cls[q]
                if prof and prof[-1]["class"] == c:
                    prof[-1]["to_m"] = round(run, 1)
                else:
                    prof.append({"from_m": round(run, 1), "to_m": round(run, 1), "class": c})
            gaps = [geo.dist(line[i], line[i + 1]) for i in range(len(line) - 1)]
            sbb_lines.append(dict(fid=fid, part=k + 1, parts=len(parts), track=str(ps[0]["kundengleisnr"]),
                                  bps=ps[0]["bps"], abk=ps[0]["bps_abk"], line=geo.simplify(line, 0.03),
                                  raw_n=len(line), max_gap=max(gaps), hk_len=ps[0]["haltekante_laenge"], profile=prof))
    g_sbb = Grid(100)
    for s in sbb_lines:
        g_sbb.add(s, s["line"])

    # ---- OSM platforms, tracks, stop positions, shelters ----------------------------
    osm = read_json("osm/city-transit.json")["elements"]
    g_plat, g_track, g_stoppos, g_osm_shelter = Grid(50), Grid(50), Grid(50), Grid(50)
    n_plat = 0
    for el in osm:
        t = el.get("tags", {})
        is_plat = (t.get("public_transport") == "platform" or t.get("railway") in ("platform", "platform_edge")
                   or t.get("highway") == "platform")
        if is_plat and el["type"] in ("way", "relation"):
            rings = osm_rings(el)
            if rings:
                for ring in rings:
                    g_plat.add(dict(el=el, kind="polygon", xy=ring), ring)
                    n_plat += 1
            elif el["type"] == "way":
                xy = osm_way_xy(el)
                if len(xy) >= 2:
                    g_plat.add(dict(el=el, kind="line", xy=xy), xy)
                    n_plat += 1
        if el["type"] == "way" and t.get("railway") in ("tram", "rail", "light_rail", "narrow_gauge"):
            xy = osm_way_xy(el)
            if len(xy) >= 2:
                g_track.add(dict(kind=t["railway"], xy=xy), xy)
        if el["type"] == "node" and t.get("public_transport") == "stop_position":
            g_stoppos.add(dict(xy=osm_point(el), tags=t), [osm_point(el)])
        if t.get("amenity") == "shelter" and t.get("shelter_type", "public_transport") == "public_transport":
            if el["type"] == "node":
                g_osm_shelter.add(dict(el=el, xy=[osm_point(el)], kind="point"), [osm_point(el)])
            else:
                for ring in osm_rings(el):
                    g_osm_shelter.add(dict(el=el, xy=ring, kind="polygon"), ring)

    g_road = Grid(50)
    for el in read_json("osm/city-roads.json")["elements"]:
        xy = osm_way_xy(el)
        if len(xy) >= 2:
            g_road.add(dict(kind=el["tags"].get("highway"), xy=xy), xy)

    def nearest_road(p, r=14.0):
        best = None
        for rd in g_road.near(p, r):
            d, s, q, _ = geo.line_project(p, rd["xy"])
            d_eff = d + (4.0 if rd["kind"] in ("service", "pedestrian") else 0.0)   # prefer real carriageways
            if d <= r and (best is None or d_eff < best[0]):
                best = (d_eff, rd["kind"], geo.line_bearing_at(rd["xy"], s), q, d)
        return best

    def nearest_track(p, r=15.0, kinds=None):
        best = None
        for tr in g_track.near(p, r):
            if kinds and tr["kind"] not in kinds:
                continue
            d, s, q, _ = geo.line_project(p, tr["xy"])
            if d <= r and (best is None or d < best[0]):
                best = (d, tr["kind"], geo.line_bearing_at(tr["xy"], s), q)
        return best

    # ---- Stadt Bern kerb points and cadastral shelters / platforms ------------------
    bern_kerbs = collections.defaultdict(list)
    for f in read_json("bern/haltestellen.json")["features"]:
        a = f["attributes"]
        bern_kerbs[str(a.get("Id_opendata") or "")].append(
            dict(xy=(f["geometry"]["x"], f["geometry"]["y"]), kante=(a.get("Kante") or "").strip(),
                 lines=strip_html(a.get("Nummer_nach")), oid=a["Objectid"], name=a.get("Punktname")))
    g_av_shelter, av_bahnsteig = Grid(50), []
    for f in read_json("bern/av-eo_flaeche_linie.json")["features"]:
        art = f["attributes"].get("Art_beschrieb")
        if art not in ("Unterstand", "Bahnsteig"):
            continue
        for path in esri_paths(f):
            ring = closed_ring(path)
            if not ring:
                continue
            item = dict(oid=f["attributes"]["Objectid"], xy=ring, art=art)
            if art == "Unterstand":
                g_av_shelter.add(item, ring)
            else:
                av_bahnsteig.append(item)

    # ---- one feature per atlas boarding edge ----------------------------------------------
    edges_out, feats_out, report = [], [], collections.Counter()
    station_edges = collections.defaultdict(list)
    used_surfaces, used_shelters = {}, {}
    dist_stats = []
    for t in tp:
        if t["trafficPointElementType"] != "BOARDING_PLATFORM":
            continue
        st = sp.get(t["parentSloidServicePoint"])
        if not st:
            continue
        e, n = fnum(t["lv95East"]), fnum(t["lv95North"])
        base = dict(
            id=t["sloid"], feature_type="boarding_edge",
            station_sloid=st["sloid"], station_number=st["number"], station_name=st["designationOfficial"],
            edge_sloid=t["sloid"], designation=t["designation"] or None,
            designation_operational=t["designationOperational"] or None,
            parent_area_sloid=t["parentSloid"] or None,
            parent_area_designation=(areas.get(t["parentSloid"]) or {}).get("designation"),
            station_modes=st["meansOfTransport"] or None,
            atlas_height_m=fnum(t["height"]), atlas_height_note="atlas 'height', metres above sea level as published (LN02 assumed)",
            atlas_length_m=fnum(t["length"]), atlas_boarding_height_cm=fnum(t["boardingAreaHeight"]),
            atlas_compass_direction_deg=fnum(t["compassDirection"]),
            atlas_valid_from=t["validFrom"], atlas_edition=t["editionDate"])
        if transit:
            tq = transit.get(t["sloid"])
            base.update(in_transit_edges=tq is not None, transit_tier=(tq or {}).get("tier"),
                        atlas_valid_today=(tq or {}).get("valid_today"))
            if t.get("_from_transit"):
                base["atlas_record_origin"] = ("row taken from bern-research/transit/data/edges.geojson: not in the "
                                               "'actual date' atlas file this folder downloaded (other validity dates)")
            elif tq is None:
                base["atlas_record_origin"] = ("in this folder's 'actual date' atlas download, not in "
                                               "bern-research/transit/data/edges.geojson")
        if e is None:
            report["edges_without_atlas_coordinates"] += 1
            edges_out.append(feature(None, **base, geometry_method="none", geometry_quality="missing",
                                     source="atlas traffic-point", licence=LICENCE["atlas"], inferred=False,
                                     note="atlas publishes no coordinates for this edge"))
            station_edges[st["sloid"]].append(edges_out[-1])
            continue
        P = (e, n)
        base.update(lv95_e=round(e, 3), lv95_n=round(n, 3),
                    atlas_lon=fnum(t["wgs84East"]), atlas_lat=fnum(t["wgs84North"]))
        # rail edge: station serves trains, or an operating point without modes whose edge has a published length
        is_rail = "TRAIN" in (st["meansOfTransport"] or "") or (
            not st["meansOfTransport"] and fnum(t["length"]) is not None and (t["designation"] or "").strip().isdigit())
        desig = (t["designation"] or "").strip()
        line = method = quality = src = src_id = src_url = lic = how = None
        inferred, extra, surface = False, {}, None

        # 1) SBB surveyed kerb line (rail)
        if is_rail:
            cands = []
            for s in g_sbb.near(P, MATCH_RADIUS_RAIL):
                d, ch, _, _ = geo.line_project(P, s["line"])
                if d <= MATCH_RADIUS_RAIL:
                    cands.append((0 if s["track"] == desig else 1, d, ch, s))
            if cands:
                same, d, ch, s = min(cands, key=lambda c: (c[0], c[1]))
                if same == 0:
                    line = s["line"]
                    full = geo.line_length(line)
                    alen = fnum(t["length"])
                    method, quality = "sbb_behig_kerb_points", "surveyed"
                    src, src_id = "SBB 21196_behig-haltekantepunkt", f"haltekante_fid {s['fid']}"
                    src_url = "https://data.sbb.ch/explore/dataset/21196_behig-haltekantepunkt/"
                    lic = LICENCE["sbb"]
                    inferred = True
                    how = ("geometry is the operator's surveyed kerb points chained in order; "
                           + ("linked to this atlas edge by equal track number and proximity"
                              if same == 0 else "linked to this atlas edge by proximity only (track numbers differ)"))
                    extra = dict(sbb_track=s["track"], sbb_station=s["bps"], sbb_haltekante_length_m=s["hk_len"],
                                 sbb_points=s["raw_n"], sbb_part=f"{s['part']}/{s['parts']}" if s["parts"] > 1 else None,
                                 kerb_height_profile=s["profile"], kerb_height_profile_note=(
                                     "SBB BehiG class along the line from its first vertex; 'P 55' = 55 cm above rail"),
                                 track_number_match=True)
                    near_any = min(((geo.line_project(P, o["line"])[0], o["track"]) for o in g_sbb.near(P, MATCH_RADIUS_RAIL)),
                                   default=None)
                    if near_any and near_any[1] != s["track"] and near_any[0] + 2.0 < d:
                        extra["atlas_position_conflict"] = (
                            f"atlas point is {d:.1f} m from SBB track {s['track']} but {near_any[0]:.1f} m from "
                            f"SBB track {near_any[1]}; geometry follows the track number, not the atlas coordinate")
                    if alen and alen < 0.8 * full:
                        line = geo.line_substring(line, ch - alen / 2, ch + alen / 2)
                        how += f"; clipped to the atlas length ({alen:g} m) centred on the atlas point"
                        extra["clipped_from_m"] = round(full, 1)

        # 2) OSM platform (line or polygon)
        if line is None:
            rad = MATCH_RADIUS_RAIL if is_rail else MATCH_RADIUS_STREET
            cands = []
            for c in g_plat.near(P, rad):
                tg = c["el"].get("tags", {})
                d = geo.ring_distance(P, c["xy"]) if c["kind"] == "polygon" else geo.line_project(P, c["xy"])[0]
                if d > rad:
                    continue
                refs = {x.strip() for k in ("local_ref", "ref") for x in str(tg.get(k, "")).replace(",", ";").split(";") if x.strip()}
                ref_state = "match" if desig and desig in refs else ("conflict" if desig and refs else "none")
                cands.append((d + {"match": -8, "none": 0, "conflict": 12}[ref_state], d, ref_state, c))
            if cands:
                _, d, ref_state, c = min(cands, key=lambda x: x[0])
                tg = c["el"].get("tags", {})
                if ref_state != "conflict" or d < 3.0:
                    method, quality = "osm_platform", "community"
                    src, src_id, src_url, lic = "OpenStreetMap", osm_id(c["el"]), osm_url(c["el"]), LICENCE["osm"]
                    inferred = True
                    extra = dict(osm_ref=tg.get("local_ref") or tg.get("ref"), osm_name=tg.get("name"),
                                 osm_ref_check=ref_state, osm_level=tg.get("level"))
                    if c["kind"] == "line":
                        line = c["xy"]
                        how = "OSM platform way matched to the atlas edge by proximity" + (
                            " and equal ref letter" if ref_state == "match" else "")
                    else:
                        ref_pt, side_how = P, "the atlas point"
                        if d < 0.5:      # atlas point lies on the platform: use the vehicle side instead
                            cand = [(geo.dist(P, s["xy"]), s["xy"]) for s in g_stoppos.near(P, 12)]
                            tr = nearest_track(P, 12)
                            if tr:
                                cand.append((tr[0], tr[3]))
                            if cand:
                                ref_pt, side_how = min(cand)[1], "the nearest OSM stop position / track"
                                extra["side_ambiguous"] = False
                            else:
                                extra["side_ambiguous"] = True
                        line, d_near, d_far = polygon_side(c["xy"], ref_pt)
                        how = ("kerb line = long side of the OSM platform polygon nearest to " + side_how
                               + "; polygon matched to the atlas edge by proximity"
                               + (" and equal ref letter" if ref_state == "match" else ""))
                        surface = c

        # 3) constructed line
        mode = "rail" if is_rail else "bus"
        tr = nearest_track(P, 7.0, kinds=("tram",)) if not is_rail else None
        if tr:
            mode = "tram"
        if "TRAM" not in (st["meansOfTransport"] or "") and "BUS" not in (st["meansOfTransport"] or "") and not is_rail:
            mode = "other"
        if line is None:
            brg = fnum(t["compassDirection"])
            brg_src = "atlas compassDirection (direction of travel)"
            if brg is None:
                trk = nearest_track(P, 15.0)
                if trk:
                    brg, brg_src = trk[2], f"bearing of the nearest OSM {trk[1]} track ({trk[0]:.1f} m away)"
                else:
                    rd = nearest_road(P)
                    if rd:
                        brg, brg_src = rd[2], f"bearing of the nearest OSM road centreline ({rd[1]}, {rd[4]:.1f} m away)"
            if brg is not None:
                length = fnum(t["length"]) or DEFAULT_LEN[mode]
                line = [geo.offset_point(P, brg, -length / 2), geo.offset_point(P, brg, length / 2)]
                method, quality = "constructed", "approximate"
                src, lic = "atlas traffic-point + project defaults", LICENCE["constructed"]
                inferred = True
                how = (f"straight line through the atlas point, bearing from {brg_src}, "
                       + (f"length from atlas ({length:g} m)" if fnum(t["length"]) else
                          f"nominal {mode} stop length {length:g} m (not measured)"))
                extra = dict(length_quality="source_derived" if fnum(t["length"]) else "approximate")
            else:
                method, quality = "point_only", "official_point"
                src, lic = "atlas traffic-point", LICENCE["atlas"]

        # Stadt Bern kerb cross-check (letter + lines served)
        kerbs = bern_kerbs.get(st["number"], [])
        chk = None
        same = [k for k in kerbs if desig and k["kante"] == desig]
        if same:
            k = min(same, key=lambda k: geo.dist(P, k["xy"]))
            chk = dict(source="Stadt Bern Haltestellen", match="same station number and kerb letter", kante=k["kante"],
                       dist_m=round(geo.dist(P, k["xy"]), 1), objectid=k["oid"])
            base["lines_at_kerb"] = k["lines"]
            base["lines_at_kerb_source"] = "Stadt Bern Haltestellen (Nummer_nach)"
        elif kerbs and not desig:
            k = min(kerbs, key=lambda k: geo.dist(P, k["xy"]))
            if geo.dist(P, k["xy"]) <= 12:
                chk = dict(source="Stadt Bern Haltestellen", match="same station number, nearest kerb point (atlas has no letter)",
                           kante=k["kante"] or None, dist_m=round(geo.dist(P, k["xy"]), 1), objectid=k["oid"])
                base["lines_at_kerb"] = k["lines"]
                base["lines_at_kerb_source"] = "Stadt Bern Haltestellen (Nummer_nach), matched by proximity"

        pr = prm.get(t["sloid"])
        prm_out = None
        if pr:
            keep = ("height", "inclination", "inclinationLongitudinal", "inclinationWidth", "superElevation",
                    "levelAccessWheelchair", "vehicleAccess", "boardingDevice", "tactileSystems", "contrastingAreas",
                    "dynamicAudio", "dynamicVisual", "wheelChairAreaLength", "wheelChairAreaWidth", "partialElevation")
            prm_out = {k: pr[k] for k in keep if pr.get(k) not in (None, "", "TO_BE_COMPLETED")} or None

        side = side_how = None
        if line is not None:
            d_geom, ch, _, _ = geo.line_project(P, line)
            length = geo.line_length(line)
            geom = gj_line(line)
            fwd = geo.line_bearing_at(line, ch)
            brg_axis = round(fwd % 180, 1)
            # which side of the kerb line is the platform (bearing pointing from the kerb into the waiting area)
            mid = geo.line_interpolate(line, length / 2)
            if surface is not None:
                c = geo.ring_centroid(surface["xy"])
                q = geo.line_project(c, line)[2]
                if geo.dist(c, q) > 0.3:
                    side, side_how = geo.bearing(q, c), "towards the centroid of the matched OSM platform polygon"
            if side is None:
                veh = nearest_track(mid, 9.0, kinds=("tram", "rail", "light_rail", "narrow_gauge") if (is_rail or mode == "tram") else None)
                vq, vname = (veh[3], f"OSM {veh[1]} track") if veh else (None, None)
                if vq is None and not is_rail:
                    rd = nearest_road(mid, 12.0)
                    if rd and rd[4] > 0.8:
                        vq, vname = rd[3], f"OSM road centreline ({rd[1]})"
                if vq is not None and geo.dist(vq, geo.line_project(vq, line)[2]) > 0.5:
                    q = geo.line_project(vq, line)[2]
                    side, side_how = (geo.bearing(q, vq) + 180) % 360, f"away from the nearest {vname}"
            if side is None and fnum(t["compassDirection"]) is not None and not is_rail:
                side = (fnum(t["compassDirection"]) + 90) % 360
                side_how = "right-hand side of the atlas direction of travel (doors on the right)"
            if side is not None:        # snap to the perpendicular of the line
                perp = [(fwd + 90) % 360, (fwd + 270) % 360]
                side = round(min(perp, key=lambda b: geo.angle_diff(b, side)), 1)
        else:
            d_geom, length, geom, brg_axis = 0.0, None, gj_point(P), None
        dist_stats.append((method, d_geom))
        ft = feature(geom, **base, mode_guess=mode,
                     mode_guess_how="station modes from atlas; tram if an OSM tram track runs within 7 m of the atlas point",
                     geometry_method=method, geometry_quality=quality,
                     length_m=round(length, 1) if length else None, axis_bearing_deg=brg_axis,
                     platform_side_bearing_deg=side, platform_side_how=side_how,
                     dist_atlas_to_geometry_m=round(d_geom, 2),
                     source=src, source_id=src_id, source_url=src_url, licence=lic,
                     inferred=inferred, inferred_how=how, verified_against=[chk] if chk else None,
                     prm=prm_out, prm_source="atlas PRM platform" if prm_out else None, **extra)
        ft["_line"], ft["_P"], ft["_mode"] = line, P, mode
        edges_out.append(ft)
        station_edges[st["sloid"]].append(ft)
        report[f"edges_{method}"] += 1

        # platform surface polygon that belongs to this edge
        if surface is not None:
            key = (osm_id(surface["el"]), round(surface["xy"][0][0], 1))
            if key not in used_surfaces:
                tg = surface["el"].get("tags", {})
                r = geo.min_rect(surface["xy"])
                used_surfaces[key] = feature(
                    gj_polygon(surface["xy"]), id=f"{st['number']}:platform_surface:{osm_id(surface['el'])}",
                    feature_type="platform_surface", station_sloid=st["sloid"], station_number=st["number"],
                    station_name=st["designationOfficial"], edge_sloids=[t["sloid"]],
                    level=(parse_levels(tg.get("level")) or [None])[0], level_source="OSM level tag" if tg.get("level") else None,
                    length_m=round(r["length"], 1), width_m=round(r["width"], 1), area_m2=round(abs(geo.ring_area(surface["xy"])), 1),
                    dim_quality="source_derived", dim_note="dimensions measured on the OSM polygon (bounding rectangle)",
                    covered=tg.get("covered"), shelter=tg.get("shelter"), surface=tg.get("surface"),
                    wheelchair=tg.get("wheelchair"), tactile_paving=tg.get("tactile_paving"),
                    geometry_quality="community", source="OpenStreetMap", source_id=osm_id(surface["el"]),
                    source_url=osm_url(surface["el"]), licence=LICENCE["osm"], inferred=True,
                    inferred_how="OSM platform polygon linked to the atlas edge(s) by proximity")
            else:
                used_surfaces[key]["properties"]["edge_sloids"].append(t["sloid"])

        # shelters next to the edge: cadastral 'Unterstand' first, OSM otherwise
        ref_line = line or [P, P]
        found = False
        for s in g_av_shelter.near(P, 60):
            c = geo.ring_centroid(s["xy"])
            d = geo.line_project(c, ref_line)[0] if line else geo.dist(c, P)
            if d <= 9.0:
                found = True
                prev = used_shelters.get(("av", s["oid"]))
                if prev is None or d < prev[0]:
                    used_shelters[("av", s["oid"])] = (d, s, ft)
        if not found:
            for s in g_osm_shelter.near(P, 40):
                c = geo.ring_centroid(s["xy"]) if s["kind"] == "polygon" else s["xy"][0]
                d = geo.line_project(c, ref_line)[0] if line else geo.dist(c, P)
                if d <= 9.0:
                    prev = used_shelters.get(("osm", s["el"]["id"]))
                    if prev is None or d < prev[0]:
                        used_shelters[("osm", s["el"]["id"])] = (d, s, ft)

    feats_out += list(used_surfaces.values())
    for (kind, key), (d, s, ft) in used_shelters.items():
        p = ft["properties"]
        common = dict(feature_type="shelter", station_sloid=p["station_sloid"], station_number=p["station_number"],
                      station_name=p["station_name"], edge_sloid=p["edge_sloid"], dist_to_edge_m=round(d, 1),
                      level=0, level_source="assumed street level",
                      height_m=3.0, height_quality="approximate",
                      height_note="nominal shelter roof height, not measured", inferred=True)
        if kind == "av":
            r = geo.min_rect(s["xy"])
            feats_out.append(feature(
                gj_polygon(s["xy"]), id=f"{p['station_number']}:shelter:av-eo-{s['oid']}", **common,
                length_m=round(r["length"], 1), width_m=round(r["width"], 1), area_m2=round(abs(geo.ring_area(s["xy"])), 1),
                dim_quality="surveyed", dim_note="footprint from the cadastral survey; height nominal",
                geometry_quality="surveyed", source="Stadt Bern Amtliche Vermessung, Einzelobjekt 'Unterstand'",
                source_id=f"Objectid {s['oid']}", licence=LICENCE["bern"],
                inferred_how="surveyed roof outline; linked to the nearest boarding edge within 9 m; height nominal"))
            report["shelters_surveyed"] += 1
        else:
            el = s["el"]
            geom = gj_polygon(s["xy"]) if s["kind"] == "polygon" else gj_point(s["xy"][0])
            feats_out.append(feature(
                geom, id=f"{p['station_number']}:shelter:{osm_id(el)}", **common,
                dim_quality="source_derived" if s["kind"] == "polygon" else "missing",
                geometry_quality="community", source="OpenStreetMap", source_id=osm_id(el), source_url=osm_url(el),
                licence=LICENCE["osm"],
                inferred_how="OSM shelter linked to the nearest boarding edge within 9 m; height nominal"))
            report["shelters_osm"] += 1

    # ---- sector markers ---------------------------------------------------------------------------
    edge_by_sloid = {f["properties"]["edge_sloid"]: f for f in edges_out}
    for s in sectors:
        ed = edge_by_sloid.get(s["trafficPointSloid"])
        e, n = fnum(s["lv95East"]), fnum(s["lv95North"])
        if not ed or e is None:
            continue
        p = ed["properties"]
        ch = None
        if ed.get("_line"):
            dd, ch, _, _ = geo.line_project((e, n), ed["_line"])
        feats_out.append(feature(
            gj_point((e, n)), id=s["sloid"], feature_type="sector_marker", sector=s["designation"],
            sector_sloid=s["sloid"], station_sloid=p["station_sloid"], station_number=p["station_number"],
            station_name=p["station_name"], edge_sloid=p["edge_sloid"], edge_designation=p.get("designation"),
            lv95_e=e, lv95_n=n, chainage_on_edge_m=round(ch, 1) if ch is not None else None,
            dist_to_edge_m=round(dd, 1) if ch is not None else None,
            geometry_quality="official_point", source="atlas sectors-and-sector-groups", licence=LICENCE["atlas"],
            inferred=False))
        report["sector_markers_atlas"] += 1
    num_to_station = {r["number"]: r for r in sp_rows}
    for b in read_json("sbb/sektortafel.json"):
        st = num_to_station.get(str(b.get("bpuic")))
        if not st or not b.get("geopos"):
            continue
        P = geo.wgs84_to_lv95(b["geopos"]["lon"], b["geopos"]["lat"])
        track = str(b.get("kundengleisnummer") or "")
        cands = [f for f in station_edges[st["sloid"]] if f.get("_line") and f["properties"].get("designation") == track]
        ed = min(cands, key=lambda f: geo.line_project(P, f["_line"])[0]) if cands else None
        dd = ch = None
        if ed:
            dd, ch, _, _ = geo.line_project(P, ed["_line"])
        feats_out.append(feature(
            gj_point(P), id=f"{st['number']}:sector_board:sbb-{b['fid']}", feature_type="sector_board",
            sector_front=b.get("sektor_vorderseite"), sector_back=b.get("sektor_ruckseiter"), track=track or None,
            mounting=b.get("montage_an"), station_sloid=st["sloid"], station_number=st["number"],
            station_name=st["designationOfficial"], edge_sloid=ed["properties"]["edge_sloid"] if ed else None,
            chainage_on_edge_m=round(ch, 1) if ch is not None else None,
            dist_to_edge_m=round(dd, 1) if dd is not None else None,
            lv95_e=round(P[0], 2), lv95_n=round(P[1], 2),
            geometry_quality="official_point", source="SBB sektortafel", source_id=f"fid {b['fid']}",
            source_url="https://data.sbb.ch/explore/dataset/sektortafel/", licence=LICENCE["sbb"],
            inferred=bool(ed), inferred_how="board position is published by SBB; linked to the atlas edge by equal track number and nearest line" if ed else None))
        report["sector_boards_sbb"] += 1

    # ---- stations -----------------------------------------------------------------------------------------
    stations = []
    for r in sp_rows:
        eds = station_edges.get(r["sloid"], [])
        if r["stopPoint"] != "true" and not eds:
            continue
        e, n = fnum(r["lv95East"]), fnum(r["lv95North"])
        if e is None:
            continue
        methods = collections.Counter(f["properties"]["geometry_method"] for f in eds)
        tier = ("surveyed" if methods.get("sbb_behig_kerb_points") else "community" if methods.get("osm_platform")
                else "approximate" if methods.get("constructed") else "point_only")
        pts = [q for f in eds if f.get("_line") for q in f["_line"]] + [(e, n)]
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        sw, ne = geo.lv95_to_wgs84(min(xs), min(ys)), geo.lv95_to_wgs84(max(xs), max(ys))
        stations.append(feature(
            gj_point((e, n)), id=r["sloid"], feature_type="station", station_sloid=r["sloid"], station_number=r["number"],
            station_name=r["designationOfficial"], abbreviation=r["abbreviation"] or None,
            atlas_stop_point=r["stopPoint"], station_note=(
                "operating point that owns boarding edges but is not an atlas stop point" if r["stopPoint"] == "false" else
                "station attributes incomplete: record taken from the transit folder" if r.get("_from_transit") else None),
            modes=r["meansOfTransport"] or None, operator=r["businessOrganisationAbbreviationDe"] or None,
            municipality=r["municipalityName"] or None, lv95_e=e, lv95_n=n, atlas_height_m=fnum(r["height"]),
            n_edges=len(eds), edges_by_method=dict(methods), best_geometry_tier=tier,
            bbox=[round(sw[0], 7), round(sw[1], 7), round(ne[0], 7), round(ne[1], 7)],
            source="atlas service-point", licence=LICENCE["atlas"], inferred=False))
        report["stations"] += 1
        report[f"stations_tier_{tier}"] += 1

    for f in edges_out:
        for k in ("_line", "_P", "_mode"):
            f.pop(k, None)
    meta = dict(generated_utc=NOW, crs="EPSG:4326 (lon, lat); LV95 values kept as properties",
                heights="metres above sea level as published by the source (atlas: LN02 assumed)",
                builder="bern-research/stations/tools/build_geometry.py")
    # edges the transit folder does not list go to a side file so that every edge in the main file joins
    side = [f for f in edges_out if f["properties"].get("in_transit_edges") is False]
    edges_out = [f for f in edges_out if f["properties"].get("in_transit_edges") is not False]
    side_path = os.path.join(DATA, "boarding_edges_not_in_transit.geojson")
    if side:
        write_geojson(side_path, side, dict(
            meta, licence="mixed per feature: see 'licence' and 'source'; OSM-derived features are ODbL",
            note="atlas edges present in this folder's 'actual date' download but absent from "
                 "bern-research/transit/data/edges.geojson; same schema as boarding_edges.geojson"))
    elif os.path.exists(side_path):
        os.remove(side_path)
    report["edges_in_side_file_not_in_transit"] = len(side)
    write_geojson(os.path.join(DATA, "boarding_edges.geojson"), edges_out,
                  dict(meta, licence="mixed per feature: see 'licence' and 'source'; OSM-derived features are ODbL",
                       transit_reconciled=bool(transit)))
    write_geojson(os.path.join(DATA, "station_features.geojson"), feats_out,
                  dict(meta, licence="mixed per feature: see 'licence' and 'source'; OSM-derived features are ODbL"))
    write_geojson(os.path.join(DATA, "stations.geojson"), stations, dict(meta, licence=LICENCE["atlas"]))

    by_m = collections.defaultdict(list)
    for m, d in dist_stats:
        by_m[m].append(d)
    rep = dict(generated_utc=NOW, counts=dict(report), osm_platform_candidates=n_plat, sbb_kerb_lines=len(sbb_lines),
               sbb_kerb_line_max_point_gap_m=round(max(s["max_gap"] for s in sbb_lines), 2),
               atlas_position_conflicts=[dict(edge_sloid=f["properties"]["edge_sloid"], station=f["properties"]["station_name"],
                                              note=f["properties"]["atlas_position_conflict"])
                                         for f in edges_out if f["properties"].get("atlas_position_conflict")],
               dist_atlas_to_geometry_m={m: dict(n=len(v), median=round(sorted(v)[len(v) // 2], 2), p95=round(sorted(v)[int(len(v) * .95)], 2),
                                                 max=round(max(v), 2)) for m, v in by_m.items()},
               feature_types=dict(collections.Counter(f["properties"]["feature_type"] for f in feats_out)))
    with open(os.path.join(DATA, "build-report.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps(rep, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
